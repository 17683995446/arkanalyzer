#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 主配置文件
"""

import os

API_KEY = "REDACTED_API_KEY"
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

DB_PATH = "data/arkanalyzer.db"

API_HOST = "0.0.0.0"
API_PORT = 5000

LOG_LEVEL = "INFO"
LOG_PATH = "logs/arkanalyzer.log"

CACHE_ENABLED = True
CACHE_TTL = 3600
