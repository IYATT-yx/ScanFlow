"""
file: ScanFlow.py
description: 应用程序入口及主窗口UI界面
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""

import csv
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import appName
from database import DatabaseManager
from dialog_settings import SettingsDialog
from dialog_product import ProductManagerDialog
import sys
import os

class MainApp(tk.Tk):
    """主程序类"""

    def __init__(self):
        super().__init__()

        self.dbManager = DatabaseManager()
        self.timer = None
        self.flashTimer = None  # 存储闪烁定时器句柄
        self.productList = []
        self.defaultBg = self.cget("bg")
        self.flashCount = 8  # 默认闪烁次数

        self.title(appName)
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)

        iconDir = os.path.dirname(__file__) if sys.argv[0].endswith('.py') else os.path.dirname(sys.argv[0])
        iconPath = os.path.join(iconDir, "icon.ico")
        self.iconbitmap(iconPath)

        # ⚡ 关键点 1：配置 Combobox 弹出下拉选项列表框的字体大小为 24
        self.option_add("*TCombobox*Listbox.font", ("Microsoft YaHei", 24))

        self.reloadFlashCountConfig()
        self.buildUi()
        self.reloadProductList()
        self.loadLogsToTree()

        # 绑定扫码输入框获取焦点事件：触发强制切英文
        self.barcodeText.bind("<FocusIn>", lambda e: self.switchToEnglishIme())

        # 启动时先强制切一次英文
        self.after(100, self.switchToEnglishIme)

        # 启动日期时间及输入法状态的实时刷新
        self.updateSystemStatus()

    def switchToEnglishIme(self):
        """利用 Win32 API 强制加载并切换当前窗口至美式英语 (00000409) 布局"""
        try:
            import ctypes
            user32 = ctypes.windll.user32

            # 常量定义
            KLF_ACTIVATE = 0x00000001
            KLF_SETFORPROCESS = 0x00000100
            SPI_SETDEFAULTINPUTLANG = 0x005A
            SPIF_SENDCHANGE = 0x0002
            WM_INPUTLANGCHANGEREQUEST = 0x0050
            INPUTLANGCHANGE_FORWARD = 0x0002

            # 1. 动态加载美式英语键盘布局 ("00000409")
            hKlEnglish = user32.LoadKeyboardLayoutW("00000409", KLF_ACTIVATE)

            if hKlEnglish:
                # 2. 改变系统未来新窗口的默认语言
                user32.SystemParametersInfoW(
                    SPI_SETDEFAULTINPUTLANG, 
                    0, 
                    ctypes.byref(ctypes.c_void_p(hKlEnglish)), 
                    SPIF_SENDCHANGE
                )

                # 3. 获取当前真正处于活跃状态的顶层窗口
                hWndFore = user32.GetForegroundWindow()

                if hWndFore:
                    # 4. 向当前活跃窗口直接投递语言切换请求
                    user32.SendMessageW(
                        hWndFore, 
                        WM_INPUTLANGCHANGEREQUEST, 
                        INPUTLANGCHANGE_FORWARD, 
                        hKlEnglish
                    )

                    # 5. 激活当前进程的布局（双重保险）
                    user32.ActivateKeyboardLayout(hKlEnglish, KLF_SETFORPROCESS)
        except Exception as e:
            print(f"切换输入法异常: {e}")

    def reloadFlashCountConfig(self):
        """刷新闪烁次数设置，防止设置后不生效"""
        self.flashCount = self.dbManager.getSavedFlashCount()

    def buildUi(self):
        # 顶部工具栏
        topControlFrame = ttk.Frame(self, padding=5)
        topControlFrame.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(topControlFrame, text=appName, font=("Microsoft YaHei", 12, "bold")).pack(side=tk.LEFT)

        # 新增：顶部工具栏中用于显示【日期时间】与【输入法状态】的标签
        self.sysStatusLabel = ttk.Label(
            topControlFrame, 
            text="系统时间加载中... | 输入法检测中...", 
            font=("Microsoft YaHei", 10, "bold")
        )
        self.sysStatusLabel.pack(side=tk.LEFT, padx=20)

        ttk.Button(topControlFrame, text="退出系统", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(topControlFrame, text="系统设置", command=self.openSettings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(topControlFrame, text="导出 CSV", command=self.exportCsv).pack(side=tk.RIGHT, padx=5)
        ttk.Button(topControlFrame, text="产品档案管理", command=self.openProductManager).pack(side=tk.RIGHT, padx=5)

        # ---------------- 满宽度产品选择器 ----------------
        productFrame = ttk.LabelFrame(self, text=" 选择/自动匹配产品 (支持单选下拉，整行覆盖) ", padding=10)
        productFrame.pack(fill=tk.X, padx=15, pady=5)

        self.productComboVar = tk.StringVar()
        # ⚡ 关键点 2：将输入框显示的字体设置为 24 号
        self.productCombo = ttk.Combobox(
            productFrame, 
            textvariable=self.productComboVar, 
            font=("Microsoft YaHei", 24), 
            state="readonly"
        )
        self.productCombo.pack(fill=tk.X, expand=True)
        # 完成自动选择后默认归还焦点到录入框
        self.productCombo.bind("<<ComboboxSelected>>", lambda e: self.barcodeText.focus_set())

        # ---------------- 扫码输入区域 ----------------
        scanFrame = ttk.Frame(self, padding=10)
        scanFrame.pack(fill=tk.X, padx=15)

        scanLabelFrame = ttk.Frame(scanFrame)
        scanLabelFrame.pack(fill=tk.X)

        ttk.Label(
            scanLabelFrame, 
            text="请扫描追溯条码（支持多行/换行输入，任意键自动聚焦）:", 
            font=("Microsoft YaHei", 14, "bold")
        ).pack(side=tk.LEFT)

        ttk.Label(scanLabelFrame, text="无回车提交延迟(ms):", font=("Microsoft YaHei", 10)).pack(side=tk.RIGHT, padx=(10, 2))
        self.delayMsVar = tk.StringVar(value="300")
        delayEntry = ttk.Entry(scanLabelFrame, textvariable=self.delayMsVar, width=6, font=("Microsoft YaHei", 10))
        delayEntry.pack(side=tk.RIGHT)

        # ---------------- 带有独立滚动条的 Text 容器 ----------------
        textContainer = ttk.Frame(scanFrame)
        textContainer.pack(fill=tk.X, pady=5)

        # 1. 垂直滚动条
        scanScroll = ttk.Scrollbar(textContainer, orient=tk.VERTICAL)
        scanScroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 2. Text 控件（配置 yscrollcommand）
        self.barcodeText = tk.Text(
            textContainer, 
            height=3, 
            font=("Microsoft YaHei", 16),
            yscrollcommand=scanScroll.set
        )
        self.barcodeText.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 3. 滚动条联动 Text
        scanScroll.config(command=self.barcodeText.yview)

        self.barcodeText.bind("<KeyRelease>", self.onKeyRelease)
        self.bind_all("<Key>", self.onGlobalKeypress)

        # ---------------- 🎯 巨幅醒目状态提示卡片 ----------------
        self.statusFrame = tk.Frame(self, bg="#28a745", pady=10)
        self.statusFrame.pack(fill=tk.X, padx=15, pady=5)

        self.statusLabel = tk.Label(
            self.statusFrame,
            text="【系统就绪】请选择产品或开始扫码",
            font=("Microsoft YaHei", 24, "bold"),
            bg="#28a745",
            fg="white"
        )
        self.statusLabel.pack()

        # ---------------- 实时表格预览 ----------------
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 11, "bold"))
        style.configure("Treeview", font=("Microsoft YaHei", 11), rowheight=28)

        columns = ("ID", "DWG", "Name", "Remark", "Barcode", "Date", "Time")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")

        self.tree.heading("ID", text="唯一ID")
        self.tree.heading("DWG", text="图号")
        self.tree.heading("Name", text="名字")
        self.tree.heading("Remark", text="备注")
        self.tree.heading("Barcode", text="追溯码")
        self.tree.heading("Date", text="日期")
        self.tree.heading("Time", text="时间")

        self.tree.column("ID", width=70, anchor="center")
        self.tree.column("DWG", width=140, anchor="center")
        self.tree.column("Name", width=180, anchor="w")
        self.tree.column("Remark", width=220, anchor="w")
        self.tree.column("Barcode", width=320, anchor="w")
        self.tree.column("Date", width=120, anchor="center")
        self.tree.column("Time", width=120, anchor="center")

        treeScroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=treeScroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0), pady=10)
        treeScroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15), pady=10)

        self.barcodeText.focus_set()

    def getImeStatus(self):
        """实时检测当前窗口的输入法中英文输入模式 (兼容 Win7 - Win11)"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            imm32 = ctypes.windll.imm32

            # 1. 获取当前焦点/前台窗口句柄
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return "未知"

            # 2. 检查系统键盘布局，如果是纯英文键盘 (如 US 0x0409)
            thread_id = user32.GetWindowThreadProcessId(hwnd, None)
            klid = user32.GetKeyboardLayout(thread_id)
            lang_id = klid & 0xFFFF
            if lang_id == 0x0409:
                return "英文 [EN]"

            # 3. 获取输入法上下文 (hIMC)
            hIMC = imm32.ImmGetContext(hwnd)
            if not hIMC:
                # 无法获取上下文（如纯英文输入状态或不支持 IME 的控件）
                return "英文 [EN]"

            try:
                # 检查输入法开启状态 (OpenStatus: True 为开启，False 为关闭/英文直接输入)
                open_status = imm32.ImmGetOpenStatus(hIMC)
                if not open_status:
                    return "英文 [EN]"

                # 获取转换模式标志 (Conversion Status)
                conversion = ctypes.c_ulong()
                sentence = ctypes.c_ulong()
                if imm32.ImmGetConversionStatus(hIMC, ctypes.byref(conversion), ctypes.byref(sentence)):
                    # IME_CMODE_NATIVE (0x0001): 1 表示中文模式，0 表示输入法内部的英文模式
                    if conversion.value & 0x0001:
                        return "中文 [中]"
                    else:
                        return "英文 [英]"

                return "中文 [中]" if open_status else "英文 [EN]"
            finally:
                # 必须释放上下文，防止句柄泄漏
                imm32.ImmReleaseContext(hwnd, hIMC)

        except Exception:
            return "未知"

    def updateSystemStatus(self):
        """定时刷新界面顶部的当前日期、时间以及输入法状态"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ime_str = self.getImeStatus()
        
        self.sysStatusLabel.config(text=f"📅 {now_str}  |  ⌨️ 语言模式: {ime_str}")
        # 每 200ms 高频刷新一次，保证按下 Shift 切换模式时响应迅速
        self.after(200, self.updateSystemStatus)

    def reloadProductList(self):
        self.productList = self.dbManager.getAllProducts()

        displayList = []
        for p in self.productList:
            remarkStr = f" | {p[3]}" if p[3] else ""
            displayList.append(f"[{p[1]}] {p[2]}{remarkStr}  (ID:{p[0]})")

        self.productCombo["values"] = displayList
        if displayList:
            self.productCombo.current(0)

    def openSettings(self):
        SettingsDialog(self, self.dbManager)

    def openProductManager(self):
        ProductManagerDialog(self, self.dbManager, self.onProductDataChanged)

    def onProductDataChanged(self):
        self.reloadProductList()
        self.loadLogsToTree()

    def getSelectedProductId(self):
        idx = self.productCombo.current()
        if idx != -1 and idx < len(self.productList):
            return self.productList[idx][0]
        return None

    def matchProductIdFromBarcode(self, rawBarcode):
        match = re.search(r'(DWG-\d{4})', rawBarcode, re.IGNORECASE)
        if match:
            matchedDwg = match.group(1).upper()
            for p in self.productList:
                if p[1].upper() == matchedDwg:
                    return p[0]
        return None

    def cancelFlash(self):
        """立即中断取消正在进行的背景闪烁，恢复默认背景色"""
        if self.flashTimer:
            self.after_cancel(self.flashTimer)
            self.flashTimer = None
        self.config(bg=self.defaultBg)

    def flashWindow(self, count=6, color1="#ff3333", color2="#ffcccc"):
        """全屏双色交替闪烁警示效果（支持随时打断）"""
        if count <= 0:
            self.cancelFlash()
            return

        currentColor = color1 if count % 2 == 0 else color2
        self.config(bg=currentColor)
        self.flashTimer = self.after(100, lambda: self.flashWindow(count - 1, color1, color2))

    def onGlobalKeypress(self, event):
        focused = None
        isPopdownActive = False

        # 1. 尝试获取焦点，捕获并处理 KeyError: 'popdown'
        try:
            focused = self.focus_get()
        except KeyError:
            # 触发 KeyError 意味着当前焦点必定落在 Combobox 的展开下拉列表 (popdown) 上
            isPopdownActive = True

        # 2. 如果焦点在系统的其他独立子弹窗（如设置对话框、产品管理弹窗）中，不要抢焦点
        if focused and focused.winfo_toplevel() != self:
            return

        if focused == self.barcodeText or isinstance(focused, ttk.Entry):
            return

        # 4. 如果按键是可打印字符（扫码枪数据或正常键盘输入）
        if event.char and len(event.char) == 1 and event.char.isprintable():
            # 如果下拉列表处于展开状态（或焦点在 productCombo 上），先发送 Escape 键收起下拉框
            if isPopdownActive or focused == self.productCombo:
                self.productCombo.event_generate("<Escape>")

            # 1. 先将焦点切到输入框
            self.barcodeText.focus_set()
            # 2. 强制切换为英文输入法
            self.switchToEnglishIme()
            # 3. 手动将丢失的第一个字符插入输入框末尾
            self.barcodeText.insert(tk.END, event.char)
            # 4. 手动触发按键释放的倒计时逻辑（防止漏触发）
            self.onKeyRelease(event)

    def onKeyRelease(self, event):
        rawText = self.barcodeText.get("1.0", tk.END)

        # 只要有正在倒计时的定时器，先取消，重新计时
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None

        try:
            delayMs = int(self.delayMsVar.get().strip())
        except ValueError:
            delayMs = 300

        # 只要框内有非空内容，就重新启动倒计时
        if rawText.strip():
            self.timer = self.after(delayMs, self.submitBarcode)

    def submitBarcode(self):
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None

        # 获取全部文本并仅剥离【末尾】的换行符与空白（保留内部可能的多行结构）
        rawText = self.barcodeText.get("1.0", tk.END)
        barcode = rawText.rstrip("\r\n").strip()

        if not barcode:
            return

        # ⚡ 核心逻辑：有新录入时，立即清空停止上一轮的闪烁！
        self.cancelFlash()

        isDuplicate = self.dbManager.checkBarcodeExists(barcode)

        productId = self.matchProductIdFromBarcode(barcode)
        if not productId:
            productId = self.getSelectedProductId()

        now = datetime.now()
        dateStr = now.strftime("%Y-%m-%d")
        timeStr = now.strftime("%H:%M:%S")

        self.dbManager.insertScanLog(productId, barcode, f"{dateStr} {timeStr}")

        # 清空输入框并重置焦点
        self.barcodeText.delete("1.0", tk.END)
        self.barcodeText.focus_set()

        # 刷新列表显示
        self.loadLogsToTree()

        cleanBarcodeDisplay = barcode.replace("\n", " ").replace("\r", "")

        if isDuplicate:
            self.statusFrame.config(bg="#ff9800")
            self.statusLabel.config(
                text=f"⚠️ [重复条码] 录入成功: {cleanBarcodeDisplay}",
                bg="#ff9800",
                fg="black"
            )
            self.flashWindow(count=self.flashCount)
        else:
            self.statusFrame.config(bg="#28a745")
            self.statusLabel.config(
                text=f"✓ 录入成功: {cleanBarcodeDisplay}",
                bg="#28a745",
                fg="white"
            )

    def loadLogsToTree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        rows = self.dbManager.getAllLogsDesc()
        for r in rows:
            pId, dwg, name, remark, barcode, createdAt = r
            datePart, timePart = "", ""
            if createdAt:
                parts = createdAt.split(" ")
                datePart = parts[0]
                timePart = parts[1] if len(parts) > 1 else ""

            cleanBarcode = barcode.replace("\n", "\\n").replace("\r", "")
            self.tree.insert("", tk.END, values=(pId if pId else "-", dwg, name, remark, cleanBarcode, datePart, timePart))

    def exportCsv(self):
        filePath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            title="导出扫码记录"
        )
        if not filePath:
            return

        rows = self.dbManager.getAllLogsAsc()

        try:
            with open(filePath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["唯一ID", "图号", "名字", "备注", "追溯码", "日期", "时间"])

                for r in rows:
                    pId, dwg, name, remark, barcode, createdAt = r
                    datePart, timePart = "", ""
                    if createdAt:
                        parts = createdAt.split(" ")
                        datePart = parts[0]
                        timePart = parts[1] if len(parts) > 1 else ""

                    writer.writerow([pId if pId else "", dwg, name, remark, barcode, datePart, timePart])

            messagebox.showinfo("成功", f"数据已成功导出至:\n{filePath}")
        except Exception as e:
            messagebox.showerror("导出失败", f"文件保存错误: {str(e)}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(sys.argv[0]))
    app = MainApp()
    app.mainloop()