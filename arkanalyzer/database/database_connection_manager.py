#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer SQLite 数据库连接管理器模块
提供数据库连接管理、模式定义和迁移功能
"""

import sqlite3
import threading
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import Queue, Empty
import time


@dataclass
class DatabaseConnectionConfig:
    """数据库连接配置"""
    db_path: str = "data/arkanalyzer.db"
    pool_size: int = 10
    timeout: int = 30
    check_same_thread: bool = False
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    cache_size: int = -64000
    foreign_keys: bool = True


class DatabaseConnectionPool:
    """数据库连接池"""

    def __init__(self, config: DatabaseConnectionConfig):
        self.config = config
        self._pool: Queue = Queue(maxsize=config.pool_size)
        self._lock = threading.Lock()
        self._init_connection_count = 0
        self._max_connections = config.pool_size
        self._ensure_database_directory()

    def _ensure_database_directory(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.config.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _create_connection(self) -> sqlite3.Connection:
        """创建新连接"""
        conn = sqlite3.connect(
            self.config.db_path,
            timeout=self.config.timeout,
            check_same_thread=self.config.check_same_thread
        )
        conn.row_factory = sqlite3.Row
        self._apply_pragmas(conn)
        return conn

    def _apply_pragmas(self, conn: sqlite3.Connection):
        """应用数据库配置"""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA journal_mode={self.config.journal_mode}")
        cursor.execute(f"PRAGMA synchronous={self.config.synchronous}")
        cursor.execute(f"PRAGMA cache_size={self.config.cache_size}")
        cursor.execute(f"PRAGMA foreign_keys={'ON' if self.config.foreign_keys else 'OFF'}")
        cursor.execute("PRAGMA temp_store=MEMORY")
        conn.commit()

    def get_connection(self) -> sqlite3.Connection:
        """获取连接"""
        try:
            conn = self._pool.get_nowait()
            return conn
        except Empty:
            with self._lock:
                if self._init_connection_count < self._max_connections:
                    self._init_connection_count += 1
                    return self._create_connection()
                else:
                    return self._create_connection()

    def return_connection(self, conn: sqlite3.Connection):
        """归还连接"""
        try:
            conn.rollback()
            self._pool.put_nowait(conn)
        except:
            conn.close()

    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


class DatabaseSchemaManager:
    """数据库模式管理器"""

    def __init__(self, pool: DatabaseConnectionPool):
        self.pool = pool
        self._schema_initialized = False

    def initialize_schema(self):
        """初始化数据库模式"""
        if self._schema_initialized:
            return

        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_graphs (
                    graph_id TEXT PRIMARY KEY,
                    graph_name TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    version INTEGER DEFAULT 1,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    entity_id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    properties TEXT,
                    description TEXT,
                    source TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (graph_id) REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    relation_id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    properties TEXT,
                    weight REAL DEFAULT 1.0,
                    confidence REAL DEFAULT 1.0,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (graph_id) REFERENCES knowledge_graphs(graph_id) ON DELETE CASCADE,
                    FOREIGN KEY (source_entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
                    FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extraction_history (
                    extraction_id TEXT PRIMARY KEY,
                    source_text TEXT,
                    source_url TEXT,
                    summary TEXT,
                    keywords TEXT,
                    processing_time REAL,
                    confidence REAL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_level TEXT NOT NULL,
                    log_message TEXT NOT NULL,
                    log_source TEXT,
                    log_data TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_graph_id ON entities(graph_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(entity_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_relations_graph_id ON relations(graph_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_entity_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_entity_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_created_at ON system_logs(created_at)
            """)

            conn.commit()
            self._schema_initialized = True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.return_connection(conn)

    def reset_schema(self):
        """重置数据库模式"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS relations")
            cursor.execute("DROP TABLE IF EXISTS entities")
            cursor.execute("DROP TABLE IF EXISTS extraction_history")
            cursor.execute("DROP TABLE IF EXISTS knowledge_graphs")
            cursor.execute("DROP TABLE IF EXISTS system_logs")
            conn.commit()
            self._schema_initialized = False
        finally:
            self.pool.return_connection(conn)


class DatabaseMigrationManager:
    """数据库迁移管理器"""

    def __init__(self, pool: DatabaseConnectionPool):
        self.pool = pool
        self.migrations = []

    def add_migration(self, version: int, description: str, migration_func):
        """添加迁移"""
        self.migrations.append({
            'version': version,
            'description': description,
            'func': migration_func
        })
        self.migrations.sort(key=lambda x: x['version'])

    def run_migrations(self):
        """运行迁移"""
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT,
                    applied_at TEXT NOT NULL
                )
            """)
            conn.commit()

            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            applied_versions = set(row['version'] for row in cursor.fetchall())

            for migration in self.migrations:
                if migration['version'] not in applied_versions:
                    migration['func'](conn)
                    cursor.execute(
                        "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?)",
                        (migration['version'], migration['description'], datetime.now().isoformat())
                    )
                    conn.commit()

        finally:
            self.pool.return_connection(conn)


class DatabaseConnection:
    """数据库连接上下文管理器"""

    def __init__(self, pool: DatabaseConnectionPool):
        self.pool = pool
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self.conn = self.pool.get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.pool.return_connection(self.conn)


class DatabaseBackupManager:
    """数据库备份管理器"""

    def __init__(self, pool: DatabaseConnectionPool):
        self.pool = pool

    def backup(self, backup_path: Optional[str] = None) -> str:
        """创建备份"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"arkanalyzer_backup_{timestamp}.db")

        source_conn = self.pool.get_connection()
        try:
            backup_conn = sqlite3.connect(backup_path)
            source_conn.backup(backup_conn)
            backup_conn.close()
            return backup_path
        finally:
            self.pool.return_connection(source_conn)

    def restore(self, backup_path: str):
        """恢复备份"""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            for table in tables:
                cursor.execute(f"DELETE FROM {table[0]}")

            backup_conn = sqlite3.connect(backup_path, read_only=True)
            source_conn.backup(conn)
            backup_conn.close()

            conn.commit()
        finally:
            self.pool.return_connection(conn)


class DatabaseQueryBuilder:
    """数据库查询构建器"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.conditions: List[str] = []
        self.params: List[Any] = []
        self.order_by_clause: str = ""
        self.limit_clause: int = 0
        self.offset_clause: int = 0

    def select(self, columns: str = "*") -> 'DatabaseQueryBuilder':
        """选择列"""
        self._columns = columns
        return self

    def where(self, condition: str, *params) -> 'DatabaseQueryBuilder':
        """添加WHERE条件"""
        if self.conditions:
            self.conditions.append(f"AND {condition}")
        else:
            self.conditions.append(condition)
        self.params.extend(params)
        return self

    def order_by(self, column: str, direction: str = "ASC") -> 'DatabaseQueryBuilder':
        """排序"""
        self.order_by_clause = f"ORDER BY {column} {direction}"
        return self

    def limit(self, limit: int) -> 'DatabaseQueryBuilder':
        """限制数量"""
        self.limit_clause = limit
        return self

    def offset(self, offset: int) -> 'DatabaseQueryBuilder':
        """偏移量"""
        self.offset_clause = offset
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """构建查询"""
        query = f"SELECT {self._columns} FROM {self.table_name}"

        if self.conditions:
            query += " WHERE " + " ".join(self.conditions)

        if self.order_by_clause:
            query += f" {self.order_by_clause}"

        if self.limit_clause:
            query += f" LIMIT {self.limit_clause}"

        if self.offset_clause:
            query += f" OFFSET {self.offset_clause}"

        return query, self.params


# 全局连接池实例
_global_pool: Optional[DatabaseConnectionPool] = None
_global_schema_manager: Optional[DatabaseSchemaManager] = None


def initialize_database(config: Optional[DatabaseConnectionConfig] = None) -> Tuple[DatabaseConnectionPool, DatabaseSchemaManager]:
    """初始化数据库"""
    global _global_pool, _global_schema_manager

    if config is None:
        config = DatabaseConnectionConfig()

    _global_pool = DatabaseConnectionPool(config)
    _global_schema_manager = DatabaseSchemaManager(_global_pool)
    _global_schema_manager.initialize_schema()

    return _global_pool, _global_schema_manager


def get_database_pool() -> DatabaseConnectionPool:
    """获取数据库连接池"""
    global _global_pool
    if _global_pool is None:
        initialize_database()
    return _global_pool


def get_database_connection() -> DatabaseConnection:
    """获取数据库连接"""
    pool = get_database_pool()
    return DatabaseConnection(pool)


@contextmanager
def get_db_cursor():
    """获取数据库游标的上下文管理器"""
    with get_database_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        except Exception as e:
            conn.rollback()
            raise e
