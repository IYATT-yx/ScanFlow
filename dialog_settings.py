"""
file: dialog_settings.py
description: 系统设置弹窗窗口
author: IYATT-yx
copyright:   Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from config import registryKeyName

try:
    import winreg
except ImportError:
    winreg = None


class SettingsDialog(tk.Toplevel):
    """系统设置弹窗（支持开机自启动设置与重复闪烁次数设置）"""

    def __init__(self, parent, dbManager):
        super().__init__(parent)
        self.parent = parent
        self.dbManager = dbManager

        self.title("系统设置")
        self.geometry("420x330")
        self.resizable(False, False)

        # 强制设置最顶层，避免全屏主窗口遮挡
        self.transient(parent)
        self.attributes("-topmost", True)
        self.grab_set()

        self.autoStartVar = tk.BooleanVar(value=self.isAutoStartEnabled())

        # 从数据库中读取已保存的闪烁次数，默认最小 6 次
        currentFlashCount = self.dbManager.getSavedFlashCount()
        self.flashCountVar = tk.IntVar(value=currentFlashCount)

        self.buildUi()
        self.protocol("WM_DELETE_WINDOW", self.onClose)

    def _getAppCommand(self):
        """获取启动当前程序所需的完整命令字符串"""
        # 判断是否被 Nuitka 或其他工具打包成可执行文件
        isPackaged = not sys.argv[0].endswith('.py')
        
        if isPackaged:
            return f'"{sys.argv[0]}"'
        else:
            return f'"{sys.executable}" "{sys.argv[0]}"'

    def buildUi(self):
        # ---------------- 启动选项 ----------------
        frameStart = ttk.LabelFrame(self, text=" 启动选项 ", padding=15)
        frameStart.pack(fill=tk.X, padx=15, pady=(15, 5))

        chkAutoStart = ttk.Checkbutton(
            frameStart,
            text="开机自动启动 (Windows 注册表)",
            variable=self.autoStartVar,
            command=self.toggleAutoStart
        )
        chkAutoStart.pack(anchor=tk.W, pady=5)

        lblTip = ttk.Label(
            frameStart,
            text="提示：勾选后系统开机将自动运行本软件。",
            font=("Microsoft YaHei", 8),
            foreground="#666666"
        )
        lblTip.pack(anchor=tk.W)

        # ---------------- 警示提醒设置 ----------------
        frameAlert = ttk.LabelFrame(self, text=" 警示提醒设置 ", padding=15)
        frameAlert.pack(fill=tk.X, padx=15, pady=5)

        flashRow = ttk.Frame(frameAlert)
        flashRow.pack(fill=tk.X)

        ttk.Label(flashRow, text="重复条码闪烁次数:").pack(side=tk.LEFT, padx=(0, 10))

        spnFlash = ttk.Spinbox(
            flashRow,
            from_=6,
            to=100,
            textvariable=self.flashCountVar,
            width=8
        )
        spnFlash.pack(side=tk.LEFT)

        lblFlashTip = ttk.Label(
            frameAlert,
            text="提示：重复扫码时全屏双色交替闪烁的次数，不得少于 6 次。",
            font=("Microsoft YaHei", 8),
            foreground="#666666"
        )
        lblFlashTip.pack(anchor=tk.W, pady=(5, 0))

        # ---------------- 底部按钮 ----------------
        btnFrame = ttk.Frame(self)
        btnFrame.pack(pady=10)

        btnSave = ttk.Button(btnFrame, text="保存设置", command=self.saveSettings)
        btnSave.pack(side=tk.LEFT, padx=5)

        btnClose = ttk.Button(btnFrame, text="取消/关闭", command=self.onClose)
        btnClose.pack(side=tk.LEFT, padx=5)

    def isAutoStartEnabled(self):
        """检测注册表是否已开启自启"""
        if not winreg:
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            val, _ = winreg.QueryValueEx(key, registryKeyName)
            winreg.CloseKey(key)
            return bool(val)
        except Exception:
            return False

    def toggleAutoStart(self):
        """同步修改 Windows 注册表项"""
        if not winreg:
            messagebox.showerror("错误", "非 Windows 系统或缺失 winreg 模块！", parent=self)
            return

        keyPath = r"Software\Microsoft\Windows\CurrentVersion\Run"
        enable = self.autoStartVar.get()

        try:
            if enable:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath, 0, winreg.KEY_SET_VALUE)
                appCommand = self._getAppCommand()
                winreg.SetValueEx(key, registryKeyName, 0, winreg.REG_SZ, appCommand)
                winreg.CloseKey(key)
                messagebox.showinfo("成功", "已成功设置开机自启动！", parent=self)
            else:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath, 0, winreg.KEY_SET_VALUE)
                try:
                    winreg.DeleteValue(key, registryKeyName)
                except FileNotFoundError:
                    pass
                winreg.CloseKey(key)
                messagebox.showinfo("成功", "已取消开机自启动！", parent=self)
        except Exception as e:
            # 如果出错，恢复多选框状态
            self.autoStartVar.set(not enable)
            messagebox.showerror("设置失败", f"无法修改注册表: {str(e)}", parent=self)

    def saveSettings(self):
        """校验并保存设置"""
        try:
            count = self.flashCountVar.get()
        except tk.TclError:
            messagebox.showwarning("格式错误", "闪烁次数必须为有效的整数数字！", parent=self)
            return

        if count < 6:
            messagebox.showwarning("限制提醒", "重复闪烁次数不能少于 6 次，已自动调整为 6 次！", parent=self)
            count = 6
            self.flashCountVar.set(6)

        self.dbManager.saveFlashCount(count)
        self.parent.reloadFlashCountConfig()
        messagebox.showinfo("成功", "设置保存成功！", parent=self)
        self.onClose()

    def onClose(self):
        self.grab_release()
        self.destroy()