"""
file: dialog_product.py
description: 产品档案管理弹窗窗口
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox


class ProductManagerDialog(tk.Toplevel):
    """产品增删改查管理弹窗"""

    def __init__(self, parent, dbManager, onUpdateCallback):
        super().__init__(parent)
        self.parent = parent
        self.dbManager = dbManager
        self.onUpdateCallback = onUpdateCallback

        self.title("产品信息管理")
        self.geometry("750x500")

        self.transient(parent)
        self.attributes("-topmost", True)
        self.grab_set()

        self.selectedProductId = None
        self.buildUi()
        self.loadProductData()

        self.protocol("WM_DELETE_WINDOW", self.onClose)

    def buildUi(self):
        formFrame = ttk.LabelFrame(self, text=" 产品编辑/新增 ", padding=10)
        formFrame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(formFrame, text="图号:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.dwgVar = tk.StringVar()
        ttk.Entry(formFrame, textvariable=self.dwgVar, width=15).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(formFrame, text="品名:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        self.nameVar = tk.StringVar()
        ttk.Entry(formFrame, textvariable=self.nameVar, width=20).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(formFrame, text="备注:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.E)
        self.remarkVar = tk.StringVar()
        ttk.Entry(formFrame, textvariable=self.remarkVar, width=25).grid(row=0, column=5, padx=5, pady=5)

        btnFrame = ttk.Frame(formFrame)
        btnFrame.grid(row=1, column=0, columnspan=6, pady=10)

        ttk.Button(btnFrame, text="新增产品", command=self.addProduct).pack(side=tk.LEFT, padx=5)
        ttk.Button(btnFrame, text="保存修改", command=self.updateProduct).pack(side=tk.LEFT, padx=5)
        ttk.Button(btnFrame, text="删除选中", command=self.deleteProduct).pack(side=tk.LEFT, padx=5)
        ttk.Button(btnFrame, text="清空输入", command=self.clearForm).pack(side=tk.LEFT, padx=5)

        tableFrame = ttk.Frame(self, padding=10)
        tableFrame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tableFrame, columns=("ID", "DWG", "Name", "Remark"), show="headings")
        self.tree.heading("ID", text="唯一ID")
        self.tree.heading("DWG", text="图号")
        self.tree.heading("Name", text="品名")
        self.tree.heading("Remark", text="备注")

        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("DWG", width=120, anchor="center")
        self.tree.column("Name", width=180, anchor="w")
        self.tree.column("Remark", width=300, anchor="w")

        scrollBar = ttk.Scrollbar(tableFrame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollBar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollBar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.onSelectRow)

    def loadProductData(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for row in self.dbManager.getAllProductsDesc():
            self.tree.insert("", tk.END, values=row)

    def onSelectRow(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        self.selectedProductId = values[0]
        self.dwgVar.set(values[1])
        self.nameVar.set(values[2])
        self.remarkVar.set(values[3] if values[3] else "")

    def clearForm(self):
        self.selectedProductId = None
        self.dwgVar.set("")
        self.nameVar.set("")
        self.remarkVar.set("")

    def addProduct(self):
        dwg = self.dwgVar.get().strip()
        name = self.nameVar.get().strip()
        remark = self.remarkVar.get().strip()

        if not dwg or not name:
            messagebox.showwarning("提示", "图号和品名不能为空！", parent=self)
            return

        try:
            self.dbManager.addProduct(dwg, name, remark)
            self.loadProductData()
            self.clearForm()
            self.onUpdateCallback()
        except sqlite3.IntegrityError:
            messagebox.showerror("错误", "图号已被注册，请检查！", parent=self)

    def updateProduct(self):
        if not self.selectedProductId:
            messagebox.showwarning("提示", "请先选择需要修改的产品！", parent=self)
            return

        dwg = self.dwgVar.get().strip()
        name = self.nameVar.get().strip()
        remark = self.remarkVar.get().strip()

        if not dwg or not name:
            messagebox.showwarning("提示", "图号和品名不能为空！", parent=self)
            return

        self.dbManager.updateProduct(self.selectedProductId, dwg, name, remark)
        self.loadProductData()
        self.clearForm()
        self.onUpdateCallback()

    def deleteProduct(self):
        if not self.selectedProductId:
            messagebox.showwarning("提示", "请选择要删除的产品！", parent=self)
            return

        if messagebox.askyesno("确认", "确定删除该产品？（关联的历史日志不会被彻底删除，但会显示为未注册状态）", parent=self):
            self.dbManager.deleteProduct(self.selectedProductId)
            self.loadProductData()
            self.clearForm()
            self.onUpdateCallback()

    def onClose(self):
        self.grab_release()
        self.destroy()