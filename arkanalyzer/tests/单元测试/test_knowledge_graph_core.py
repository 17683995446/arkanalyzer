#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 核心模块单元测试套件
测试知识图谱核心功能、LLM连接器、抽取器和分析器
"""

import unittest
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.knowledge_graph_core import (
    Entity, Relation, KnowledgeGraph, KnowledgeGraphManager,
    EntityType, RelationType
)
from core.llm_connector import LLMConnector, LLMCache
from core.knowledge_extractor import KnowledgeExtractor, TextPreprocessor, GraphAnalyzer
from core.knowledge_graph_analyzer import (
    KnowledgeGraphAnalyzer, VisualizationDataGenerator,
    GraphStatistics
)


class TestKnowledgeGraphCore(unittest.TestCase):
    """测试知识图谱核心功能"""

    def setUp(self):
        """测试前准备"""
        self.entity1 = Entity(
            entity_name="人工智能",
            entity_type="概念",
            description="AI学科"
        )
        self.entity2 = Entity(
            entity_name="机器学习",
            entity_type="概念",
            description="ML学科"
        )
        self.entity3 = Entity(
            entity_name="深度学习",
            entity_type="概念",
            description="DL技术"
        )

    def test_entity_creation(self):
        """测试实体创建"""
        self.assertEqual(self.entity1.entity_name, "人工智能")
        self.assertEqual(self.entity1.entity_type, "概念")
        self.assertIsNotNone(self.entity1.entity_id)
        self.assertIsInstance(self.entity1.created_at, datetime)

    def test_entity_to_dict(self):
        """测试实体序列化"""
        entity_dict = self.entity1.to_dict()
        self.assertIsInstance(entity_dict, dict)
        self.assertEqual(entity_dict['entity_name'], "人工智能")
        self.assertEqual(entity_dict['entity_type'], "概念")
        self.assertIn('entity_id', entity_dict)

    def test_entity_from_dict(self):
        """测试实体反序列化"""
        entity_dict = {
            'entity_id': 'test-id',
            'entity_name': '测试实体',
            'entity_type': '概念',
            'properties': {},
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'source': 'test',
            'confidence': 1.0,
            'description': '测试'
        }
        entity = Entity.from_dict(entity_dict)
        self.assertEqual(entity.entity_name, '测试实体')
        self.assertEqual(entity.entity_id, 'test-id')

    def test_relation_creation(self):
        """测试关系创建"""
        relation = Relation(
            source_entity_id=self.entity1.entity_id,
            target_entity_id=self.entity2.entity_id,
            relation_type="包含",
            weight=0.9
        )
        self.assertEqual(relation.relation_type, "包含")
        self.assertEqual(relation.weight, 0.9)
        self.assertIsNotNone(relation.relation_id)

    def test_knowledge_graph_creation(self):
        """测试知识图谱创建"""
        graph = KnowledgeGraph(
            graph_name="测试图谱",
            description="这是一个测试图谱"
        )
        self.assertEqual(graph.graph_name, "测试图谱")
        self.assertEqual(len(graph.entities), 0)
        self.assertEqual(len(graph.relations), 0)

    def test_add_entity_to_graph(self):
        """测试添加实体到图谱"""
        graph = KnowledgeGraph(graph_name="测试")
        graph.add_entity(self.entity1)
        self.assertEqual(len(graph.entities), 1)
        self.assertEqual(graph.get_entity_by_id(self.entity1.entity_id), self.entity1)

    def test_add_relation_to_graph(self):
        """测试添加关系到图谱"""
        graph = KnowledgeGraph(graph_name="测试")
        graph.add_entity(self.entity1)
        graph.add_entity(self.entity2)
        relation = Relation(
            source_entity_id=self.entity1.entity_id,
            target_entity_id=self.entity2.entity_id,
            relation_type="包含"
        )
        graph.add_relation(relation)
        self.assertEqual(len(graph.relations), 1)

    def test_get_neighbors(self):
        """测试获取邻居实体"""
        graph = KnowledgeGraph(graph_name="测试")
        graph.add_entity(self.entity1)
        graph.add_entity(self.entity2)
        relation = Relation(
            source_entity_id=self.entity1.entity_id,
            target_entity_id=self.entity2.entity_id,
            relation_type="包含"
        )
        graph.add_relation(relation)
        neighbors = graph.get_neighbors(self.entity1.entity_id)
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0].entity_id, self.entity2.entity_id)

    def test_graph_statistics(self):
        """测试图谱统计"""
        graph = KnowledgeGraph(graph_name="测试")
        graph.add_entity(self.entity1)
        graph.add_entity(self.entity2)
        graph.add_entity(self.entity3)
        relation = Relation(
            source_entity_id=self.entity1.entity_id,
            target_entity_id=self.entity2.entity_id,
            relation_type="包含"
        )
        graph.add_relation(relation)
        stats = graph.get_statistics()
        self.assertEqual(stats['total_entities'], 3)
        self.assertEqual(stats['total_relations'], 1)

    def test_knowledge_graph_manager(self):
        """测试图谱管理器"""
        manager = KnowledgeGraphManager()
        graph = manager.create_graph("新图谱", "测试描述")
        self.assertIsNotNone(graph.graph_id)
        self.assertEqual(graph.graph_name, "新图谱")
        all_graphs = manager.get_all_graphs()
        self.assertGreaterEqual(len(all_graphs), 1)


class TestLLMConnector(unittest.TestCase):
    """测试LLM连接器"""

    def setUp(self):
        """测试前准备"""
        self.api_key = "sk-test-key"
        self.connector = LLMConnector(
            api_key=self.api_key,
            base_url="https://api.siliconflow.cn/v1",
            model="Qwen/Qwen2.5-7B-Instruct",
            cache_enabled=False
        )

    def test_connector_initialization(self):
        """测试连接器初始化"""
        self.assertEqual(self.connector.api_key, self.api_key)
        self.assertEqual(self.connector.model, "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(self.connector.temperature, 0.7)

    def test_cache_operations(self):
        """测试缓存操作"""
        connector = LLMConnector(
            api_key=self.api_key,
            cache_enabled=True
        )
        connector.cache.set("test", "model", {"result": "test_value"})
        result = connector.cache.get("test", "model")
        self.assertIsNotNone(result)
        connector.cache.clear()
        result = connector.cache.get("test", "model")
        self.assertIsNone(result)

    def test_set_model(self):
        """测试设置模型"""
        self.connector.set_model("Qwen/Qwen2.5-14B-Instruct")
        self.assertEqual(self.connector.model, "Qwen/Qwen2.5-14B-Instruct")

    def test_set_temperature(self):
        """测试设置温度"""
        self.connector.set_temperature(0.5)
        self.assertEqual(self.connector.temperature, 0.5)
        self.connector.set_temperature(3.0)
        self.assertEqual(self.connector.temperature, 2.0)

    def test_get_statistics(self):
        """测试获取统计"""
        stats = self.connector.get_statistics()
        self.assertIn('request_count', stats)
        self.assertIn('total_tokens', stats)
        self.assertEqual(stats['model'], self.connector.model)


class TestKnowledgeExtractor(unittest.TestCase):
    """测试知识抽取器"""

    def setUp(self):
        """测试前准备"""
        self.preprocessor = TextPreprocessor()

    def test_clean_text(self):
        """测试文本清洗"""
        text = "这是   一个   测试\n\n文本"
        cleaned = self.preprocessor.clean_text(text)
        self.assertNotIn('\n', cleaned)
        self.assertNotIn('   ', cleaned)

    def test_split_sentences(self):
        """测试句子分割"""
        text = "这是第一个句子。这是第二个句子！这是第三个句子？"
        sentences = self.preprocessor.split_sentences(text)
        self.assertEqual(len(sentences), 3)

    def test_extract_urls(self):
        """测试URL提取"""
        text = "请访问 https://example.com 和 http://test.com 了解更多信息"
        urls = self.preprocessor.extract_urls(text)
        self.assertEqual(len(urls), 2)
        self.assertIn("https://example.com", urls)

    def test_truncate_text(self):
        """测试文本截断"""
        long_text = "a" * 6000
        truncated = self.preprocessor.truncate_text(long_text, max_length=5000)
        self.assertEqual(len(truncated), 5003)
        self.assertTrue(truncated.endswith("..."))


class TestGraphAnalyzer(unittest.TestCase):
    """测试图谱分析器"""

    def setUp(self):
        """测试前准备"""
        self.entity1 = Entity(entity_name="A", entity_type="概念")
        self.entity2 = Entity(entity_name="B", entity_type="概念")
        self.entity3 = Entity(entity_name="C", entity_type="概念")
        self.entity4 = Entity(entity_name="D", entity_type="概念")

        self.relation1 = Relation(
            source_entity_id=self.entity1.entity_id,
            target_entity_id=self.entity2.entity_id,
            relation_type="连接"
        )
        self.relation2 = Relation(
            source_entity_id=self.entity2.entity_id,
            target_entity_id=self.entity3.entity_id,
            relation_type="连接"
        )
        self.relation3 = Relation(
            source_entity_id=self.entity3.entity_id,
            target_entity_id=self.entity4.entity_id,
            relation_type="连接"
        )

        self.analyzer = KnowledgeGraphAnalyzer(
            [self.entity1, self.entity2, self.entity3, self.entity4],
            [self.relation1, self.relation2, self.relation3]
        )

    def test_calculate_statistics(self):
        """测试统计计算"""
        stats = self.analyzer.calculate_statistics()
        self.assertIsInstance(stats, GraphStatistics)
        self.assertEqual(stats.total_nodes, 4)
        self.assertEqual(stats.total_edges, 3)
        self.assertGreater(stats.density, 0)
        self.assertGreater(stats.average_degree, 0)

    def test_find_shortest_path(self):
        """测试最短路径查找"""
        path = self.analyzer.find_shortest_path(
            self.entity1.entity_id,
            self.entity4.entity_id
        )
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 4)
        self.assertEqual(path[0], self.entity1.entity_id)
        self.assertEqual(path[-1], self.entity4.entity_id)

    def test_find_all_paths(self):
        """测试查找所有路径"""
        paths = self.analyzer.find_all_paths(
            self.entity1.entity_id,
            self.entity4.entity_id,
            max_depth=5
        )
        self.assertIsInstance(paths, list)
        self.assertGreater(len(paths), 0)

    def test_detect_communities(self):
        """测试社区检测"""
        result = self.analyzer.detect_communities_bfs()
        self.assertIsNotNone(result.communities)
        self.assertGreater(len(result.communities), 0)

    def test_calculate_node_importance(self):
        """测试节点重要性计算"""
        importance = self.analyzer.calculate_node_importance()
        self.assertIsInstance(importance, dict)
        self.assertEqual(len(importance), 4)
        for entity_id, scores in importance.items():
            self.assertIn('degree_centrality', scores)
            self.assertIn('importance_score', scores)

    def test_find_key_entities(self):
        """测试关键实体查找"""
        key_entities = self.analyzer.find_key_entities(top_n=2)
        self.assertEqual(len(key_entities), 2)
        for entity_id, score in key_entities:
            self.assertIsInstance(entity_id, str)
            self.assertIsInstance(score, float)


class TestVisualizationDataGenerator(unittest.TestCase):
    """测试可视化数据生成器"""

    def setUp(self):
        """测试前准备"""
        self.entity1 = Entity(entity_name="节点A", entity_type="概念")
        self.entity2 = Entity(entity_name="节点B", entity_type="人物")
        self.relation = Relation(
            source_entity_id=self.entity1.entity_id,
            target_entity_id=self.entity2.entity_id,
            relation_type="关联"
        )
        self.analyzer = KnowledgeGraphAnalyzer(
            [self.entity1, self.entity2],
            [self.relation]
        )

    def test_generate_force_directed_data(self):
        """测试力导向图数据生成"""
        generator = VisualizationDataGenerator(self.analyzer)
        data = generator.generate_force_directed_data()
        self.assertIn('nodes', data)
        self.assertIn('edges', data)
        self.assertEqual(data['type'], 'force_directed')
        self.assertEqual(len(data['nodes']), 2)
        self.assertEqual(len(data['edges']), 1)

    def test_generate_hierarchical_data(self):
        """测试分层图数据生成"""
        generator = VisualizationDataGenerator(self.analyzer)
        data = generator.generate_hierarchical_data()
        self.assertIn('nodes', data)
        self.assertIn('edges', data)
        self.assertEqual(data['type'], 'hierarchical')


def run_tests():
    """运行所有测试"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    print("=" * 80)
    print("Arkanalyzer 单元测试套件")
    print("=" * 80)
    run_tests()
