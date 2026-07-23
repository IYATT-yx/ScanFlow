"""
file: database.py
description: 数据库管理与数据访问层
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""

import sqlite3
from config import dbName


class DatabaseManager:
    """管理 SQLite 数据库连接及所有数据表操作"""

    def __init__(self, dbPath=dbName):
        self.dbConn = sqlite3.connect(dbPath, check_same_thread=False)
        self.initDb()

    def initDb(self):
        cursor = self.dbConn.cursor()

        # 系统参数配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sys_config (
                config_key TEXT PRIMARY KEY,
                config_value TEXT
            )
        ''')

        # 产品档案表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drawing_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                remark TEXT
            )
        ''')

        # 校验并初始化默认数据
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            sampleData = [
                ("default-0001", "默认产品名称", "默认产品备注"),
            ]
            cursor.executemany(
                "INSERT INTO products (drawing_no, name, remark) VALUES (?, ?, ?)",
                sampleData
            )

        # 扫码记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                barcode TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_barcode ON scan_logs(barcode)')
        self.dbConn.commit()

    def getSavedFlashCount(self):
        """获取已保存的闪烁次数配置"""
        cursor = self.dbConn.cursor()
        cursor.execute("SELECT config_value FROM sys_config WHERE config_key = 'flash_count'")
        row = cursor.fetchone()
        if row:
            try:
                val = int(row[0])
                return max(6, val)
            except ValueError:
                pass
        return 8  # 默认 8 次

    def saveFlashCount(self, count):
        """保存闪烁次数到数据库"""
        cursor = self.dbConn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO sys_config (config_key, config_value) VALUES ('flash_count', ?)",
            (str(count),)
        )
        self.dbConn.commit()

    def getAllProducts(self):
        """获取产品列表按 ID 升序"""
        cursor = self.dbConn.cursor()
        cursor.execute("SELECT id, drawing_no, name, remark FROM products ORDER BY id ASC")
        return cursor.fetchall()

    def getAllProductsDesc(self):
        """获取产品列表按 ID 降序"""
        cursor = self.dbConn.cursor()
        cursor.execute("SELECT id, drawing_no, name, remark FROM products ORDER BY id DESC")
        return cursor.fetchall()

    def addProduct(self, dwg, name, remark):
        """新增产品记录"""
        cursor = self.dbConn.cursor()
        cursor.execute(
            "INSERT INTO products (drawing_no, name, remark) VALUES (?, ?, ?)",
            (dwg, name, remark)
        )
        self.dbConn.commit()

    def updateProduct(self, productId, dwg, name, remark):
        """更新产品记录"""
        cursor = self.dbConn.cursor()
        cursor.execute(
            "UPDATE products SET drawing_no=?, name=?, remark=? WHERE id=?",
            (dwg, name, remark, productId)
        )
        self.dbConn.commit()

    def deleteProduct(self, productId):
        """删除产品记录"""
        cursor = self.dbConn.cursor()
        cursor.execute("DELETE FROM products WHERE id=?", (productId,))
        self.dbConn.commit()

    def checkBarcodeExists(self, barcode):
        """查询是否存在重复条码"""
        cursor = self.dbConn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scan_logs WHERE barcode = ?", (barcode,))
        return cursor.fetchone()[0] > 0

    def insertScanLog(self, productId, barcode, createdAt):
        """新增一条扫码日志"""
        cursor = self.dbConn.cursor()
        cursor.execute(
            "INSERT INTO scan_logs (product_id, barcode, created_at) VALUES (?, ?, ?)",
            (productId, barcode, createdAt)
        )
        self.dbConn.commit()

    def getAllLogsDesc(self):
        """查询日志（按时间倒序）用于界面预览"""
        cursor = self.dbConn.cursor()
        query = '''
            SELECT 
                p.id,
                IFNULL(p.drawing_no, '未注册'),
                IFNULL(p.name, '未注册产品'),
                IFNULL(p.remark, ''),
                l.barcode,
                l.created_at
            FROM scan_logs l
            LEFT JOIN products p ON l.product_id = p.id
            ORDER BY l.id DESC
        '''
        cursor.execute(query)
        return cursor.fetchall()

    def getAllLogsAsc(self):
        """查询日志（按时间正序）用于导出文件"""
        cursor = self.dbConn.cursor()
        query = '''
            SELECT 
                p.id,
                IFNULL(p.drawing_no, '未注册'),
                IFNULL(p.name, '未注册产品'),
                IFNULL(p.remark, ''),
                l.barcode,
                l.created_at
            FROM scan_logs l
            LEFT JOIN products p ON l.product_id = p.id
            ORDER BY l.id ASC
        '''
        cursor.execute(query)
        return cursor.fetchall()