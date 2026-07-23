"""
file: config.py
description: 全局配置文件
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
from buildtime import buildTime

dbName = "Records.db"
appName = f"ScanFlow 扫码流水线 by IYATT-yx {buildTime}"
registryKeyName = "ScanFlowAutoStart"