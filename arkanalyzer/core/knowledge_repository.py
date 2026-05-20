#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 知识存储仓库模块
提供知识图谱的持久化存储和查询功能
"""

import json
import uuid
import time
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Iterator, Generator
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from collections import OrderedDict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph, EntityType, RelationType
from database.database_connection_manager import (
    initialize_database,
    get_database_pool,
    get_database_connection,
    get_db_cursor
)


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, capacity: int = 10):
        self.cache = OrderedDict()
        self.capacity = capacity
        self._lock = None  # 简化版，不使用锁
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        if key not in self.cache:
            return None
        # 移动到末尾（最近使用）
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any):
        """放入缓存项"""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.capacity:
                # 删除最旧的项
                self.cache.popitem(last=False)
        self.cache[key] = value
    
    def invalidate(self, key: str):
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)


def with_retry(max_retries: int = 5, base_delay: float = 0.1):
    """重试装饰器 - 处理数据库锁定问题"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    if "database is locked" in error_str or "locked" in error_str or "busy" in error_str:
                        retries += 1
                        if retries >= max_retries:
                            break
                        
                        # 指数退避 + 抖动
                        delay = base_delay * (2 ** (retries - 1)) + random.uniform(0, 0.1)
                        time.sleep(delay)
                    else:
                        # 不是锁定问题，直接抛出
                        raise
            
            raise last_exception
        return wrapper
    return decorator


class KnowledgeRepository:
    """知识存储仓库 - 优化版"""

    def __init__(self, cache_size: int = 20):
        self.pool = get_database_pool()
        self._graph_cache = LRUCache(capacity=cache_size)
        self._stats_cache = LRUCache(capacity=100)

    def _save_graph_internal(self, knowledge_graph: KnowledgeGraph) -> bool:
        """内部保存方法 - 实际的数据库操作"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            try:
                # 暂时禁用外键检查以避免级联约束问题
                cursor.execute("PRAGMA foreign_keys = OFF")
                
                # 优化：使用WAL模式提高写入性能
                cursor.execute("PRAGMA journal_mode = WAL")
                
                # 禁用同步以提高性能（生产环境可考虑安全和性能平衡）
                cursor.execute("PRAGMA synchronous = OFF")
                
                # 开始显式事务（比自动提交更快）
                conn.execute("BEGIN TRANSACTION")

                existing = cursor.execute(
                    "SELECT version FROM knowledge_graphs WHERE graph_id = ?",
                    (knowledge_graph.graph_id,)
                ).fetchone()

                if existing:
                    knowledge_graph.version = existing[0] + 1
                else:
                    knowledge_graph.version = 1

                # 保存图谱本身
                cursor.execute("""
                    INSERT OR REPLACE INTO knowledge_graphs
                    (graph_id, graph_name, description, metadata, version, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    knowledge_graph.graph_id,
                    knowledge_graph.graph_name,
                    knowledge_graph.description,
                    json.dumps(knowledge_graph.metadata, ensure_ascii=False),
                    knowledge_graph.version,
                    json.dumps(knowledge_graph.tags, ensure_ascii=False),
                    knowledge_graph.created_at.isoformat(),
                    knowledge_graph.updated_at.isoformat()
                ))

                # 先删除旧的关系，避免依赖问题
                cursor.execute("DELETE FROM relations WHERE graph_id = ?", (knowledge_graph.graph_id,))
                
                # 删除旧的实体
                cursor.execute("DELETE FROM entities WHERE graph_id = ?", (knowledge_graph.graph_id,))

                # 批量保存所有实体
                if knowledge_graph.entities:
                    entity_data = [
                        (
                            entity.entity_id,
                            knowledge_graph.graph_id,
                            entity.entity_name,
                            entity.entity_type,
                            json.dumps(entity.properties, ensure_ascii=False),
                            entity.description,
                            entity.source,
                            entity.confidence,
                            entity.created_at.isoformat(),
                            entity.updated_at.isoformat()
                        )
                        for entity in knowledge_graph.entities
                    ]
                    cursor.executemany("""
                        INSERT OR REPLACE INTO entities
                        (entity_id, graph_id, entity_name, entity_type, properties, description, source, confidence, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, entity_data)

                # 批量保存所有关系
                if knowledge_graph.relations:
                    relation_data = [
                        (
                            relation.relation_id,
                            knowledge_graph.graph_id,
                            relation.source_entity_id,
                            relation.target_entity_id,
                            relation.relation_type,
                            json.dumps(relation.properties, ensure_ascii=False),
                            relation.weight,
                            relation.confidence,
                            relation.description,
                            relation.created_at.isoformat()
                        )
                        for relation in knowledge_graph.relations
                    ]
                    cursor.executemany("""
                        INSERT OR REPLACE INTO relations
                        (relation_id, graph_id, source_entity_id, target_entity_id, relation_type, properties, weight, confidence, description, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, relation_data)

                # 重新启用外键检查
                cursor.execute("PRAGMA foreign_keys = ON")
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                raise e

    @with_retry(max_retries=5, base_delay=0.1)
    def save_graph(self, knowledge_graph: KnowledgeGraph) -> bool:
        """保存知识图谱（使用批量插入优化性能 + 重试机制 + 缓存更新）"""
        try:
            result = self._save_graph_internal(knowledge_graph)
            if result:
                self._graph_cache.put(knowledge_graph.graph_id, knowledge_graph)
                self._stats_cache.invalidate(knowledge_graph.graph_id)
            return result
        except Exception as e:
            print(f"保存图谱失败: {e}")
            return False

    def get_graph(self, graph_id: str, use_cache: bool = True) -> Optional[KnowledgeGraph]:
        """获取知识图谱（带缓存优化）"""
        if use_cache:
            cached = self._graph_cache.get(graph_id)
            if cached is not None:
                return cached
        
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_graphs WHERE graph_id = ?", (graph_id,))
            row = cursor.fetchone()

            if not row:
                return None

            entities = self._get_entities_by_graph(cursor, graph_id)
            relations = self._get_relations_by_graph(cursor, graph_id)

            graph = KnowledgeGraph(
                graph_id=row['graph_id'],
                graph_name=row['graph_name'],
                description=row['description'] or "",
                metadata=json.loads(row['metadata'] or '{}'),
                version=row['version'],
                tags=json.loads(row['tags'] or '[]'),
                entities=entities,
                relations=relations,
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
            
            if use_cache:
                self._graph_cache.put(graph_id, graph)
            
            return graph

    def _get_entities_by_graph(self, cursor, graph_id: str) -> List[Entity]:
        """获取图谱的所有实体"""
        cursor.execute("SELECT * FROM entities WHERE graph_id = ?", (graph_id,))
        entities = []
        for row in cursor.fetchall():
            entities.append(Entity(
                entity_id=row['entity_id'],
                entity_name=row['entity_name'],
                entity_type=row['entity_type'],
                properties=json.loads(row['properties'] or '{}'),
                description=row['description'] or "",
                source=row['source'] or "",
                confidence=row['confidence'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            ))
        return entities

    def _get_relations_by_graph(self, cursor, graph_id: str) -> List[Relation]:
        """获取图谱的所有关系"""
        cursor.execute("SELECT * FROM relations WHERE graph_id = ?", (graph_id,))
        relations = []
        for row in cursor.fetchall():
            relations.append(Relation(
                relation_id=row['relation_id'],
                source_entity_id=row['source_entity_id'],
                target_entity_id=row['target_entity_id'],
                relation_type=row['relation_type'],
                properties=json.loads(row['properties'] or '{}'),
                weight=row['weight'],
                confidence=row['confidence'],
                description=row['description'] or "",
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        return relations

    def get_all_graphs(self) -> List[KnowledgeGraph]:
        """获取所有知识图谱"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT graph_id FROM knowledge_graphs ORDER BY updated_at DESC")
            graph_ids = [row['graph_id'] for row in cursor.fetchall()]

            graphs = []
            for graph_id in graph_ids:
                graph = self.get_graph(graph_id)
                if graph:
                    graphs.append(graph)

            return graphs

    def delete_graph(self, graph_id: str) -> bool:
        """删除知识图谱（清除缓存）"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM knowledge_graphs WHERE graph_id = ?", (graph_id,))
                conn.commit()
                self._graph_cache.invalidate(graph_id)
                self._stats_cache.invalidate(graph_id)
                return True
            except Exception as e:
                conn.rollback()
                print(f"删除图谱失败: {e}")
                return False

    def update_graph_metadata(self, graph_id: str, metadata: Dict[str, Any]) -> bool:
        """更新图谱元数据（清除缓存）"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE knowledge_graphs
                    SET metadata = ?, updated_at = ?
                    WHERE graph_id = ?
                """, (json.dumps(metadata, ensure_ascii=False), datetime.now().isoformat(), graph_id))
                conn.commit()
                self._graph_cache.invalidate(graph_id)
                self._stats_cache.invalidate(graph_id)
                return True
            except Exception as e:
                conn.rollback()
                print(f"更新元数据失败: {e}")
                return False

    def search_entities(self, keyword: str, graph_id: Optional[str] = None) -> List[Entity]:
        """搜索实体"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            if graph_id:
                cursor.execute("""
                    SELECT * FROM entities
                    WHERE graph_id = ? AND (entity_name LIKE ? OR description LIKE ?)
                """, (graph_id, f'%{keyword}%', f'%{keyword}%'))
            else:
                cursor.execute("""
                    SELECT * FROM entities
                    WHERE entity_name LIKE ? OR description LIKE ?
                """, (f'%{keyword}%', f'%{keyword}%'))

            entities = []
            for row in cursor.fetchall():
                entities.append(Entity(
                    entity_id=row['entity_id'],
                    entity_name=row['entity_name'],
                    entity_type=row['entity_type'],
                    properties=json.loads(row['properties'] or '{}'),
                    description=row['description'] or "",
                    source=row['source'] or "",
                    confidence=row['confidence'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            return entities

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return Entity(
                entity_id=row['entity_id'],
                entity_name=row['entity_name'],
                entity_type=row['entity_type'],
                properties=json.loads(row['properties'] or '{}'),
                description=row['description'] or "",
                source=row['source'] or "",
                confidence=row['confidence'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )

    def get_neighbors(self, entity_id: str) -> List[Entity]:
        """获取实体的邻居"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT e.* FROM entities e
                JOIN relations r ON (
                    (r.source_entity_id = ? AND r.target_entity_id = e.entity_id) OR
                    (r.target_entity_id = ? AND r.source_entity_id = e.entity_id)
                )
            """, (entity_id, entity_id))

            entities = []
            for row in cursor.fetchall():
                if row['entity_id'] != entity_id:
                    entities.append(Entity(
                        entity_id=row['entity_id'],
                        entity_name=row['entity_name'],
                        entity_type=row['entity_type'],
                        properties=json.loads(row['properties'] or '{}'),
                        description=row['description'] or "",
                        source=row['source'] or "",
                        confidence=row['confidence'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        updated_at=datetime.fromisoformat(row['updated_at'])
                    ))
            return entities

    def get_relations_between(self, source_id: str, target_id: str) -> List[Relation]:
        """获取两个实体之间的关系"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM relations
                WHERE (source_entity_id = ? AND target_entity_id = ?) OR
                      (source_entity_id = ? AND target_entity_id = ?)
            """, (source_id, target_id, target_id, source_id))

            relations = []
            for row in cursor.fetchall():
                relations.append(Relation(
                    relation_id=row['relation_id'],
                    source_entity_id=row['source_entity_id'],
                    target_entity_id=row['target_entity_id'],
                    relation_type=row['relation_type'],
                    properties=json.loads(row['properties'] or '{}'),
                    weight=row['weight'],
                    confidence=row['confidence'],
                    description=row['description'] or "",
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            return relations

    def get_graph_statistics(self, graph_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """获取图谱统计信息（带缓存优化）"""
        if use_cache:
            cached = self._stats_cache.get(graph_id)
            if cached is not None:
                return cached
        
        with get_database_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM entities WHERE graph_id = ?", (graph_id,))
            entity_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM relations WHERE graph_id = ?", (graph_id,))
            relation_count = cursor.fetchone()['count']

            cursor.execute("""
                SELECT entity_type, COUNT(*) as count
                FROM entities WHERE graph_id = ?
                GROUP BY entity_type
            """, (graph_id,))
            entity_types = {row['entity_type']: row['count'] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT relation_type, COUNT(*) as count
                FROM relations WHERE graph_id = ?
                GROUP BY relation_type
            """, (graph_id,))
            relation_types = {row['relation_type']: row['count'] for row in cursor.fetchall()}

            density = relation_count / max(1, entity_count * (entity_count - 1) / 2)

            stats = {
                'graph_id': graph_id,
                'entity_count': entity_count,
                'relation_count': relation_count,
                'entity_types': entity_types,
                'relation_types': relation_types,
                'density': density
            }
            
            if use_cache:
                self._stats_cache.put(graph_id, stats)
            
            return stats

    def get_entities_paginated(self, graph_id: str, offset: int = 0, 
                              limit: int = 100) -> List[Entity]:
        """分页获取实体（优化大数据集）"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM entities WHERE graph_id = ? LIMIT ? OFFSET ?",
                (graph_id, limit, offset)
            )
            
            entities = []
            for row in cursor.fetchall():
                entities.append(Entity(
                    entity_id=row['entity_id'],
                    entity_name=row['entity_name'],
                    entity_type=row['entity_type'],
                    properties=json.loads(row['properties'] or '{}'),
                    description=row['description'] or "",
                    source=row['source'] or "",
                    confidence=row['confidence'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            return entities

    def get_relations_paginated(self, graph_id: str, offset: int = 0, 
                                limit: int = 100) -> List[Relation]:
        """分页获取关系（优化大数据集）"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM relations WHERE graph_id = ? LIMIT ? OFFSET ?",
                (graph_id, limit, offset)
            )
            
            relations = []
            for row in cursor.fetchall():
                relations.append(Relation(
                    relation_id=row['relation_id'],
                    source_entity_id=row['source_entity_id'],
                    target_entity_id=row['target_entity_id'],
                    relation_type=row['relation_type'],
                    properties=json.loads(row['properties'] or '{}'),
                    weight=row['weight'],
                    confidence=row['confidence'],
                    description=row['description'] or "",
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            return relations

    def iter_entities(self, graph_id: str, batch_size: int = 500) -> Generator[Entity, None, None]:
        """迭代器方式获取实体（流式加载，优化内存）"""
        offset = 0
        while True:
            entities = self.get_entities_paginated(graph_id, offset, batch_size)
            if not entities:
                break
            for entity in entities:
                yield entity
            offset += batch_size

    def iter_relations(self, graph_id: str, batch_size: int = 500) -> Generator[Relation, None, None]:
        """迭代器方式获取关系（流式加载，优化内存）"""
        offset = 0
        while True:
            relations = self.get_relations_paginated(graph_id, offset, batch_size)
            if not relations:
                break
            for relation in relations:
                yield relation
            offset += batch_size

    def save_extraction_history(self, extraction_data: Dict[str, Any]) -> bool:
        """保存抽取历史"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO extraction_history
                    (extraction_id, source_text, source_url, summary, keywords, processing_time, confidence, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    extraction_data.get('extraction_id', str(uuid.uuid4())),
                    extraction_data.get('source_text', ''),
                    extraction_data.get('source_url', ''),
                    extraction_data.get('summary', ''),
                    json.dumps(extraction_data.get('keywords', []), ensure_ascii=False),
                    extraction_data.get('processing_time', 0.0),
                    extraction_data.get('confidence', 1.0),
                    json.dumps(extraction_data.get('metadata', {}), ensure_ascii=False),
                    datetime.now().isoformat()
                ))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"保存抽取历史失败: {e}")
                return False

    def get_extraction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取抽取历史"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM extraction_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            history = []
            for row in cursor.fetchall():
                history.append({
                    'extraction_id': row['extraction_id'],
                    'source_text': row['source_text'],
                    'source_url': row['source_url'],
                    'summary': row['summary'],
                    'keywords': json.loads(row['keywords'] or '[]'),
                    'processing_time': row['processing_time'],
                    'confidence': row['confidence'],
                    'created_at': row['created_at']
                })
            return history

    def log_system_event(self, level: str, message: str, source: str = "", data: Optional[Dict] = None):
        """记录系统日志"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO system_logs (log_level, log_message, log_source, log_data, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    level,
                    message,
                    source,
                    json.dumps(data, ensure_ascii=False) if data else None,
                    datetime.now().isoformat()
                ))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"记录日志失败: {e}")

    def get_recent_logs(self, level: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        with get_database_connection() as conn:
            cursor = conn.cursor()
            if level:
                cursor.execute("""
                    SELECT * FROM system_logs
                    WHERE log_level = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (level, limit))
            else:
                cursor.execute("""
                    SELECT * FROM system_logs
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'log_id': row['log_id'],
                    'level': row['log_level'],
                    'message': row['log_message'],
                    'source': row['log_source'],
                    'data': json.loads(row['log_data'] or '{}'),
                    'created_at': row['created_at']
                })
            return logs


# 全局仓库实例
_repository_instance: Optional[KnowledgeRepository] = None


def get_knowledge_repository() -> KnowledgeRepository:
    """获取知识仓库实例"""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = KnowledgeRepository()
    return _repository_instance
