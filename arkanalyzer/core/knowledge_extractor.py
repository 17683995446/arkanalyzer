#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 知识图谱抽取核心模块
从文本、URL等来源自动抽取实体和关系，构建知识图谱
"""

import re
import uuid
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from .knowledge_graph_core import Entity, Relation, KnowledgeGraph, EntityType, RelationType
from .llm_connector import LLMConnector, create_llm_connector


@dataclass
class ExtractionResult:
    """抽取结果数据模型"""
    extraction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_text: str = ""
    source_url: str = ""
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'extraction_id': self.extraction_id,
            'source_text': self.source_text,
            'source_url': self.source_url,
            'entities': [e.to_dict() for e in self.entities],
            'relations': [r.to_dict() for r in self.relations],
            'summary': self.summary,
            'keywords': self.keywords,
            'created_at': self.created_at.isoformat(),
            'processing_time': self.processing_time,
            'confidence': self.confidence,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionResult':
        """从字典创建"""
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'entities' in data:
            data['entities'] = [Entity.from_dict(e) for e in data['entities']]
        if 'relations' in data:
            data['relations'] = [Relation.from_dict(r) for r in data['relations']]
        return cls(**data)


class TextPreprocessor:
    """文本预处理模块"""

    @staticmethod
    def clean_text(text: str) -> str:
        """清洗文本"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        text = text.strip()
        return text

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """分割句子"""
        sentence_endings = r'[。！？\.!?]+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """提取URL"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)

    @staticmethod
    def truncate_text(text: str, max_length: int = 5000) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."


class KnowledgeExtractor:
    """知识抽取器核心类"""

    def __init__(self, llm_connector: Optional[LLMConnector] = None):
        self.llm_connector = llm_connector or create_llm_connector()
        self.preprocessor = TextPreprocessor()
        self.entity_cache: Dict[str, List[Entity]] = {}
        self.relation_cache: Dict[str, List[Relation]] = {}

    def extract_from_text(self, text: str, graph_name: str = "新图谱",
                         entity_types: Optional[List[str]] = None,
                         relation_types: Optional[List[str]] = None,
                         enable_cache: bool = True) -> Tuple[ExtractionResult, KnowledgeGraph]:
        """从文本抽取知识"""
        import time
        start_time = time.time()

        cleaned_text = self.preprocessor.clean_text(text)
        truncated_text = self.preprocessor.truncate_text(cleaned_text)

        cache_key = hash(truncated_text)
        if enable_cache and cache_key in self.entity_cache:
            entities = [Entity.from_dict(e.to_dict()) for e in self.entity_cache[cache_key]]
            relations = [Relation.from_dict(r.to_dict()) for r in self.relation_cache.get(cache_key, [])]
        else:
            llm_result = self.llm_connector.extract_entities_and_relations(
                truncated_text,
                entity_types or [et.value for et in EntityType],
                relation_types or [rt.value for rt in RelationType]
            )

            entities = self._parse_entities(llm_result.get('entities', []))
            relations = self._parse_relations(llm_result.get('relations', []), entities)

            if enable_cache:
                self.entity_cache[cache_key] = entities
                self.relation_cache[cache_key] = relations

        entity_map = {e.entity_name: e.entity_id for e in entities}
        for relation in relations:
            if relation.source_entity_id not in entity_map.values():
                for entity in entities:
                    if entity.entity_name == relation.source_entity_id:
                        relation.source_entity_id = entity.entity_id
                        break
            if relation.target_entity_id not in entity_map.values():
                for entity in entities:
                    if entity.entity_name == relation.target_entity_id:
                        relation.target_entity_id = entity.entity_id
                        break

        summary = self.llm_connector.summarize(truncated_text, max_length=200)

        extraction_result = ExtractionResult(
            source_text=truncated_text,
            entities=entities,
            relations=relations,
            summary=summary,
            keywords=self._extract_keywords(truncated_text),
            processing_time=time.time() - start_time,
            confidence=len(entities) / max(1, len(truncated_text) / 100)
        )

        knowledge_graph = KnowledgeGraph(
            graph_name=graph_name,
            description=summary,
            entities=entities,
            relations=relations,
            metadata={
                'source': 'text',
                'extraction_id': extraction_result.extraction_id,
                'extraction_time': extraction_result.created_at.isoformat()
            }
        )

        return extraction_result, knowledge_graph

    def _parse_entities(self, entity_list: List[Dict[str, Any]]) -> List[Entity]:
        """解析实体列表"""
        entities = []
        seen_names = set()

        for entity_data in entity_list:
            name = entity_data.get('name', '')
            if not name or name in seen_names:
                continue

            entity = Entity(
                entity_name=name,
                entity_type=entity_data.get('type', EntityType.CONCEPT.value),
                properties=entity_data.get('properties', {}),
                source='llm_extraction',
                confidence=entity_data.get('confidence', 0.9)
            )

            if entity_data.get('description'):
                entity.description = entity_data['description']

            entities.append(entity)
            seen_names.add(name)

        return entities

    def _parse_relations(self, relation_list: List[Dict[str, Any]],
                         entities: List[Entity]) -> List[Relation]:
        """解析关系列表"""
        relations = []
        entity_names = {e.entity_name for e in entities}

        for rel_data in relation_list:
            source_name = rel_data.get('source', '')
            target_name = rel_data.get('target', '')

            if not source_name or not target_name:
                continue

            if source_name not in entity_names or target_name not in entity_names:
                continue

            relation = Relation(
                source_entity_id=source_name,
                target_entity_id=target_name,
                relation_type=rel_data.get('type', RelationType.RELATED_TO.value),
                properties=rel_data.get('properties', {}),
                weight=rel_data.get('weight', 1.0),
                confidence=rel_data.get('confidence', 0.9)
            )

            if rel_data.get('description'):
                relation.description = rel_data['description']

            relations.append(relation)

        return relations

    def _extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """提取关键词"""
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', text)
        word_freq = {}
        for word in words:
            if len(word) >= 2:
                word_freq[word] = word_freq.get(word, 0) + 1

        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:top_n]]

    def extract_batch(self, texts: List[str], graph_name: str = "批量图谱") -> List[Tuple[ExtractionResult, KnowledgeGraph]]:
        """批量抽取"""
        results = []
        for i, text in enumerate(texts):
            result, graph = self.extract_from_text(
                text,
                graph_name=f"{graph_name}-{i+1}"
            )
            results.append((result, graph))
        return results

    def enrich_graph(self, knowledge_graph: KnowledgeGraph,
                    additional_texts: List[str]) -> KnowledgeGraph:
        """丰富图谱"""
        for text in additional_texts:
            result, temp_graph = self.extract_from_text(text)
            for entity in temp_graph.entities:
                if not knowledge_graph.get_entity_by_name(entity.entity_name):
                    knowledge_graph.add_entity(entity)

            for relation in temp_graph.relations:
                source_entity = knowledge_graph.get_entity_by_name(relation.source_entity_id)
                target_entity = knowledge_graph.get_entity_by_name(relation.target_entity_id)
                if source_entity and target_entity:
                    relation.source_entity_id = source_entity.entity_id
                    relation.target_entity_id = target_entity.entity_id
                    knowledge_graph.add_relation(relation)

        return knowledge_graph

    def get_extraction_statistics(self) -> Dict[str, Any]:
        """获取抽取统计信息"""
        return {
            'total_extractions': len(self.entity_cache),
            'cached_entities': sum(len(entities) for entities in self.entity_cache.values()),
            'cached_relations': sum(len(relations) for relations in self.relation_cache.values()),
            'llm_stats': self.llm_connector.get_statistics()
        }

    def clear_cache(self):
        """清空缓存"""
        self.entity_cache.clear()
        self.relation_cache.clear()


class GraphAnalyzer:
    """图谱分析器"""

    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.graph = knowledge_graph

    def calculate_node_importance(self) -> Dict[str, float]:
        """计算节点重要性（基于度数）"""
        degrees = {}
        for entity in self.graph.entities:
            degree = sum(1 for r in self.graph.relations
                        if r.source_entity_id == entity.entity_id or
                        r.target_entity_id == entity.entity_id)
            degrees[entity.entity_id] = degree

        max_degree = max(degrees.values()) if degrees else 1
        for entity_id in degrees:
            degrees[entity_id] /= max_degree

        return degrees

    def find_paths(self, source_id: str, target_id: str,
                  max_depth: int = 3) -> List[List[str]]:
        """查找路径"""
        paths = []
        visited = set()

        def dfs(current: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current == target_id:
                paths.append(path.copy())
                return

            visited.add(current)
            for relation in self.graph.relations:
                if relation.source_entity_id == current and relation.target_entity_id not in visited:
                    path.append(relation.target_entity_id)
                    dfs(relation.target_entity_id, path, depth + 1)
                    path.pop()
                elif relation.target_entity_id == current and relation.source_entity_id not in visited:
                    path.append(relation.source_entity_id)
                    dfs(relation.source_entity_id, path, depth + 1)
                    path.pop()

            visited.discard(current)

        dfs(source_id, [source_id], 0)
        return paths

    def detect_communities(self) -> List[List[str]]:
        """社区检测（简单实现）"""
        visited = set()
        communities = []

        for entity in self.graph.entities:
            if entity.entity_id not in visited:
                community = []
                queue = [entity.entity_id]

                while queue:
                    current = queue.pop(0)
                    if current in visited:
                        continue

                    visited.add(current)
                    community.append(current)

                    for relation in self.graph.relations:
                        if relation.source_entity_id == current:
                            if relation.target_entity_id not in visited:
                                queue.append(relation.target_entity_id)
                        elif relation.target_entity_id == current:
                            if relation.source_entity_id not in visited:
                                queue.append(relation.source_entity_id)

                if community:
                    communities.append(community)

        return communities

    def get_graph_metrics(self) -> Dict[str, Any]:
        """获取图谱度量指标"""
        node_importance = self.calculate_node_importance()
        communities = self.detect_communities()

        return {
            'node_count': len(self.graph.entities),
            'edge_count': len(self.graph.relations),
            'density': self.graph.get_statistics().get('density', 0),
            'avg_degree': sum(node_importance.values()) / max(1, len(node_importance)),
            'communities': len(communities),
            'node_importance': node_importance
        }


# 导出主要类
__all__ = [
    'ExtractionResult',
    'TextPreprocessor',
    'KnowledgeExtractor',
    'GraphAnalyzer'
]
