#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 知识图谱分析系统 - 核心模块
提供知识抽取、存储、分析和可视化的完整功能
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class EntityType(Enum):
    """实体类型枚举"""
    PERSON = "人物"
    LOCATION = "地点"
    ORGANIZATION = "组织"
    EVENT = "事件"
    CONCEPT = "概念"
    OBJECT = "物体"
    TIME = "时间"
    CUSTOM = "自定义"


class RelationType(Enum):
    """关系类型枚举"""
    BELONGS_TO = "属于"
    LOCATED_IN = "位于"
    RELATED_TO = "相关"
    CAUSES = "导致"
    CONSISTS_OF = "组成"
    WORKS_FOR = "工作于"
    PARTICIPATES_IN = "参与"
    BEFORE = "之前"
    AFTER = "之后"
    CUSTOM = "自定义"


@dataclass
class Entity:
    """实体数据模型"""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_name: str = ""
    entity_type: str = EntityType.CONCEPT.value
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source: str = ""
    confidence: float = 1.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """从字典创建"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class Relation:
    """关系数据模型"""
    relation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str = ""
    target_entity_id: str = ""
    relation_type: str = RelationType.RELATED_TO.value
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relation':
        """从字典创建"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class KnowledgeGraph:
    """知识图谱数据模型"""
    graph_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    graph_name: str = ""
    description: str = ""
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    tags: List[str] = field(default_factory=list)
    
    # 缓存和索引（运行时优化，不持久化）
    _entity_index: Dict[str, Entity] = field(default_factory=dict, init=False, repr=False)
    _neighbor_cache: Dict[str, List[Entity]] = field(default_factory=dict, init=False, repr=False)
    _relation_index: Dict[str, List[Relation]] = field(default_factory=dict, init=False, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'graph_id': self.graph_id,
            'graph_name': self.graph_name,
            'description': self.description,
            'entities': [e.to_dict() for e in self.entities],
            'relations': [r.to_dict() for r in self.relations],
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'version': self.version,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGraph':
        """从字典创建"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if 'entities' in data:
            data['entities'] = [Entity.from_dict(e) for e in data['entities']]
        if 'relations' in data:
            data['relations'] = [Relation.from_dict(r) for r in data['relations']]
        graph = cls(**data)
        graph._rebuild_indices()  # 重建索引
        return graph

    def _rebuild_indices(self):
        """重建所有索引（用于初始化和大量修改后）"""
        self._entity_index.clear()
        self._neighbor_cache.clear()
        self._relation_index.clear()
        
        for entity in self.entities:
            self._entity_index[entity.entity_id] = entity
            
        for relation in self.relations:
            src = relation.source_entity_id
            tgt = relation.target_entity_id
            
            if src not in self._relation_index:
                self._relation_index[src] = []
            self._relation_index[src].append(relation)
            
            if tgt not in self._relation_index:
                self._relation_index[tgt] = []
            self._relation_index[tgt].append(relation)
    
    def add_entity(self, entity: Entity):
        """添加实体"""
        self.entities.append(entity)
        self._entity_index[entity.entity_id] = entity
        self._neighbor_cache.clear()  # 缓存失效
        self.updated_at = datetime.now()

    def add_relation(self, relation: Relation):
        """添加关系"""
        self.relations.append(relation)
        
        src = relation.source_entity_id
        tgt = relation.target_entity_id
        
        if src not in self._relation_index:
            self._relation_index[src] = []
        self._relation_index[src].append(relation)
        
        if tgt not in self._relation_index:
            self._relation_index[tgt] = []
        self._relation_index[tgt].append(relation)
        
        self._neighbor_cache.clear()
        self.updated_at = datetime.now()

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体（O(1)查找）"""
        if not self._entity_index:
            self._rebuild_indices()
        return self._entity_index.get(entity_id)

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """根据名称获取实体"""
        for entity in self.entities:
            if entity.entity_name == name:
                return entity
        return None

    def get_neighbors(self, entity_id: str) -> List[Entity]:
        """获取相邻实体（使用缓存优化）"""
        if entity_id in self._neighbor_cache:
            return self._neighbor_cache[entity_id]
            
        if not self._relation_index:
            self._rebuild_indices()
            
        neighbors = []
        neighbor_ids = set()
        
        if entity_id in self._relation_index:
            for relation in self._relation_index[entity_id]:
                if relation.source_entity_id == entity_id:
                    neighbor_ids.add(relation.target_entity_id)
                else:
                    neighbor_ids.add(relation.source_entity_id)
        
        for n_id in neighbor_ids:
            entity = self.get_entity_by_id(n_id)
            if entity:
                neighbors.append(entity)
        
        self._neighbor_cache[entity_id] = neighbors
        return neighbors

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        entity_types = {}
        relation_types = {}

        for entity in self.entities:
            entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1

        for relation in self.relations:
            relation_types[relation.relation_type] = relation_types.get(relation.relation_type, 0) + 1

        return {
            'total_entities': len(self.entities),
            'total_relations': len(self.relations),
            'entity_types': entity_types,
            'relation_types': relation_types,
            'density': len(self.relations) / max(1, len(self.entities) * (len(self.entities) - 1) / 2),
            'version': self.version
        }


class KnowledgeGraphManager:
    """知识图谱管理器"""

    def __init__(self, storage_path: str = "data/knowledge_graphs.json"):
        self.storage_path = storage_path
        self.graphs: Dict[str, KnowledgeGraph] = {}
        self._ensure_storage_path()
        self._load_graphs()

    def _ensure_storage_path(self):
        """确保存储路径存在"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_graphs(self):
        """从存储加载图谱"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for graph_data in data.get('graphs', []):
                        graph = KnowledgeGraph.from_dict(graph_data)
                        self.graphs[graph.graph_id] = graph
            except Exception as e:
                print(f"加载图谱失败: {e}")

    def _save_graphs(self):
        """保存图谱到存储"""
        try:
            data = {
                'graphs': [graph.to_dict() for graph in self.graphs.values()]
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存图谱失败: {e}")

    def create_graph(self, graph_name: str, description: str = "") -> KnowledgeGraph:
        """创建新图谱"""
        graph = KnowledgeGraph(
            graph_name=graph_name,
            description=description
        )
        self.graphs[graph.graph_id] = graph
        self._save_graphs()
        return graph

    def get_graph(self, graph_id: str) -> Optional[KnowledgeGraph]:
        """获取图谱"""
        return self.graphs.get(graph_id)

    def get_all_graphs(self) -> List[KnowledgeGraph]:
        """获取所有图谱"""
        return list(self.graphs.values())

    def update_graph(self, graph: KnowledgeGraph):
        """更新图谱"""
        graph.updated_at = datetime.now()
        graph.version += 1
        self.graphs[graph.graph_id] = graph
        self._save_graphs()

    def delete_graph(self, graph_id: str) -> bool:
        """删除图谱"""
        if graph_id in self.graphs:
            del self.graphs[graph_id]
            self._save_graphs()
            return True
        return False

    def add_entity_to_graph(self, graph_id: str, entity: Entity) -> bool:
        """向图谱添加实体"""
        graph = self.get_graph(graph_id)
        if graph:
            graph.add_entity(entity)
            self.update_graph(graph)
            return True
        return False

    def add_relation_to_graph(self, graph_id: str, relation: Relation) -> bool:
        """向图谱添加关系"""
        graph = self.get_graph(graph_id)
        if graph:
            graph.add_relation(relation)
            self.update_graph(graph)
            return True
        return False

    def merge_graphs(self, graph_id1: str, graph_id2: str, merged_name: str) -> Optional[KnowledgeGraph]:
        """合并两个图谱"""
        graph1 = self.get_graph(graph_id1)
        graph2 = self.get_graph(graph_id2)

        if not graph1 or not graph2:
            return None

        merged = self.create_graph(merged_name)
        merged.entities = graph1.entities + graph2.entities
        merged.relations = graph1.relations + graph2.relations
        self.update_graph(merged)

        return merged

    def search_graphs(self, keyword: str) -> List[KnowledgeGraph]:
        """搜索图谱"""
        results = []
        for graph in self.graphs.values():
            if (keyword.lower() in graph.graph_name.lower() or
                keyword.lower() in graph.description.lower()):
                results.append(graph)
        return results


# 导出核心类和枚举
__all__ = [
    'EntityType',
    'RelationType',
    'Entity',
    'Relation',
    'KnowledgeGraph',
    'KnowledgeGraphManager'
]
