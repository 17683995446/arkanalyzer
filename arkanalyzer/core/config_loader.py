#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 配置管理模块
提供系统配置的加载、验证和管理功能
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class LLMConfig:
    """大语言模型配置"""
    api_key: str = "sk-uqelhavcdhfxjzjesdenxpbtqombamjniazzjtbssmdcwdvg"
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    retry_times: int = 3


@dataclass
class DatabaseConfig:
    """数据库配置"""
    db_path: str = "data/arkanalyzer.db"
    pool_size: int = 10
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class APIConfig:
    """API服务配置"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = True
    cors_enabled: bool = True
    rate_limit: str = "100/minute"


@dataclass
class VisualizationConfig:
    """可视化配置"""
    graph_layout: str = "force-directed"
    node_size_range: tuple = (20, 60)
    edge_width_range: tuple = (1, 5)
    animation_duration: int = 300
    max_nodes_display: int = 500


@dataclass
class SystemConfig:
    """系统配置"""
    log_level: str = "INFO"
    log_path: str = "logs/arkanalyzer.log"
    cache_enabled: bool = True
    cache_ttl: int = 3600
    backup_enabled: bool = True
    backup_interval: int = 86400
    environment: str = "development"


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_path()
        self.config: Dict[str, Any] = {}
        self.llm_config = LLMConfig()
        self.db_config = DatabaseConfig()
        self.api_config = APIConfig()
        self.viz_config = VisualizationConfig()
        self.sys_config = SystemConfig()
        self._load_config()

    def _get_default_config_path(self) -> str:
        """获取默认配置路径"""
        return os.getenv("ARKANALYZER_CONFIG", "config/settings.json")

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self._apply_config()
            except Exception as e:
                print(f"加载配置文件失败: {e}, 使用默认配置")
                self._use_default_config()
        else:
            self._use_default_config()
            self._create_default_config()

    def _apply_config(self):
        """应用配置到各个配置对象"""
        if 'llm' in self.config:
            llm_cfg = self.config['llm']
            self.llm_config = LLMConfig(
                api_key=llm_cfg.get('api_key', self.llm_config.api_key),
                base_url=llm_cfg.get('base_url', self.llm_config.base_url),
                model=llm_cfg.get('model', self.llm_config.model),
                temperature=llm_cfg.get('temperature', self.llm_config.temperature),
                max_tokens=llm_cfg.get('max_tokens', self.llm_config.max_tokens),
                timeout=llm_cfg.get('timeout', self.llm_config.timeout),
                retry_times=llm_cfg.get('retry_times', self.llm_config.retry_times)
            )

        if 'database' in self.config:
            db_cfg = self.config['database']
            self.db_config = DatabaseConfig(
                db_path=db_cfg.get('db_path', self.db_config.db_path),
                pool_size=db_cfg.get('pool_size', self.db_config.pool_size),
                pool_recycle=db_cfg.get('pool_recycle', self.db_config.pool_recycle),
                echo=db_cfg.get('echo', self.db_config.echo)
            )

        if 'api' in self.config:
            api_cfg = self.config['api']
            self.api_config = APIConfig(
                host=api_cfg.get('host', self.api_config.host),
                port=api_cfg.get('port', self.api_config.port),
                debug=api_cfg.get('debug', self.api_config.debug),
                cors_enabled=api_cfg.get('cors_enabled', self.api_config.cors_enabled),
                rate_limit=api_cfg.get('rate_limit', self.api_config.rate_limit)
            )

        if 'visualization' in self.config:
            viz_cfg = self.config['visualization']
            self.viz_config = VisualizationConfig(
                graph_layout=viz_cfg.get('graph_layout', self.viz_config.graph_layout),
                node_size_range=tuple(viz_cfg.get('node_size_range', self.viz_config.node_size_range)),
                edge_width_range=tuple(viz_cfg.get('edge_width_range', self.viz_config.edge_width_range)),
                animation_duration=viz_cfg.get('animation_duration', self.viz_config.animation_duration),
                max_nodes_display=viz_cfg.get('max_nodes_display', self.viz_config.max_nodes_display)
            )

        if 'system' in self.config:
            sys_cfg = self.config['system']
            self.sys_config = SystemConfig(
                log_level=sys_cfg.get('log_level', self.sys_config.log_level),
                log_path=sys_cfg.get('log_path', self.sys_config.log_path),
                cache_enabled=sys_cfg.get('cache_enabled', self.sys_config.cache_enabled),
                cache_ttl=sys_cfg.get('cache_ttl', self.sys_config.cache_ttl),
                backup_enabled=sys_cfg.get('backup_enabled', self.sys_config.backup_enabled),
                backup_interval=sys_cfg.get('backup_interval', self.sys_config.backup_interval),
                environment=sys_cfg.get('environment', self.sys_config.environment)
            )

    def _use_default_config(self):
        """使用默认配置"""
        self._ensure_directories()

    def _create_default_config(self):
        """创建默认配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            default_config = {
                'llm': {
                    'api_key': self.llm_config.api_key,
                    'base_url': self.llm_config.base_url,
                    'model': self.llm_config.model,
                    'temperature': self.llm_config.temperature,
                    'max_tokens': self.llm_config.max_tokens,
                    'timeout': self.llm_config.timeout,
                    'retry_times': self.llm_config.retry_times
                },
                'database': {
                    'db_path': self.db_config.db_path,
                    'pool_size': self.db_config.pool_size,
                    'pool_recycle': self.db_config.pool_recycle,
                    'echo': self.db_config.echo
                },
                'api': {
                    'host': self.api_config.host,
                    'port': self.api_config.port,
                    'debug': self.api_config.debug,
                    'cors_enabled': self.api_config.cors_enabled,
                    'rate_limit': self.api_config.rate_limit
                },
                'visualization': {
                    'graph_layout': self.viz_config.graph_layout,
                    'node_size_range': list(self.viz_config.node_size_range),
                    'edge_width_range': list(self.viz_config.edge_width_range),
                    'animation_duration': self.viz_config.animation_duration,
                    'max_nodes_display': self.viz_config.max_nodes_display
                },
                'system': {
                    'log_level': self.sys_config.log_level,
                    'log_path': self.sys_config.log_path,
                    'cache_enabled': self.sys_config.cache_enabled,
                    'cache_ttl': self.sys_config.cache_ttl,
                    'backup_enabled': self.sys_config.backup_enabled,
                    'backup_interval': self.sys_config.backup_interval,
                    'environment': self.sys_config.environment
                }
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"创建默认配置文件失败: {e}")

    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            os.path.dirname(self.db_config.db_path),
            os.path.dirname(self.sys_config.log_path),
            "data",
            "logs",
            "backups"
        ]
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置"""
        return self.llm_config

    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self.db_config

    def get_api_config(self) -> APIConfig:
        """获取API配置"""
        return self.api_config

    def get_visualization_config(self) -> VisualizationConfig:
        """获取可视化配置"""
        return self.viz_config

    def get_system_config(self) -> SystemConfig:
        """获取系统配置"""
        return self.sys_config

    def update_config(self, key: str, value: Any):
        """更新配置项"""
        if '.' in key:
            section, item = key.split('.', 1)
            if section not in self.config:
                self.config[section] = {}
            self.config[section][item] = value
        else:
            self.config[key] = value

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")

    def validate_config(self) -> bool:
        """验证配置的有效性"""
        try:
            if not self.llm_config.api_key:
                raise ValueError("LLM API密钥不能为空")
            if not self.llm_config.base_url.startswith("http"):
                raise ValueError("LLM API URL必须以http或https开头")
            if self.api_config.port < 1 or self.api_config.port > 65535:
                raise ValueError("API端口必须在1-65535之间")
            if self.sys_config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                raise ValueError("日志级别无效")
            return True
        except ValueError as e:
            print(f"配置验证失败: {e}")
            return False


# 全局配置实例
_config_instance: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance


def init_config(config_file: Optional[str] = None) -> ConfigLoader:
    """初始化配置"""
    global _config_instance
    _config_instance = ConfigLoader(config_file)
    return _config_instance
