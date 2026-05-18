#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 集成测试套件
测试核心模块间的集成功能，包括API端点、数据库操作和工作流程
"""

import unittest
import os
import sys
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_extractor import KnowledgeExtractor
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer, analyze_knowledge_graph
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig,
    get_database_pool
)


class TestDatabaseIntegration(unittest.TestCase):
    """测试数据库集成"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = KnowledgeRepository()

    def tearDown(self):
        """测试后清理"""
        pool = get_database_pool()
        pool.close_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_retrieve_graph(self):
        """测试图谱保存和检索"""
        graph = KnowledgeGraph(
            graph_name="测试图谱",
            description="集成测试图谱"
        )
        entity = Entity(
            entity_name="测试实体",
            entity_type="概念",
            description="测试"
        )
        graph.add_entity(entity)

        success = self.repository.save_graph(graph)
        self.assertTrue(success)

        retrieved_graph = self.repository.get_graph(graph.graph_id)
        self.assertIsNotNone(retrieved_graph)
        self.assertEqual(retrieved_graph.graph_name, "测试图谱")
        self.assertEqual(len(retrieved_graph.entities), 1)
        self.assertEqual(retrieved_graph.entities[0].entity_name, "测试实体")

    def test_update_graph_metadata(self):
        """测试更新图谱元数据"""
        graph = KnowledgeGraph(graph_name="原图谱", description="原描述")
        self.repository.save_graph(graph)

        new_metadata = {"key": "value", "count": 10}
        success = self.repository.update_graph_metadata(graph.graph_id, new_metadata)
        self.assertTrue(success)

        updated_graph = self.repository.get_graph(graph.graph_id)
        self.assertEqual(updated_graph.metadata['key'], "value")
        self.assertEqual(updated_graph.metadata['count'], 10)

    def test_delete_graph(self):
        """测试删除图谱"""
        graph = KnowledgeGraph(graph_name="待删除图谱")
        self.repository.save_graph(graph)

        success = self.repository.delete_graph(graph.graph_id)
        self.assertTrue(success)

        deleted_graph = self.repository.get_graph(graph.graph_id)
        self.assertIsNone(deleted_graph)

    def test_get_all_graphs(self):
        """测试获取所有图谱"""
        for i in range(3):
            graph = KnowledgeGraph(graph_name=f"图谱{i}")
            self.repository.save_graph(graph)

        graphs = self.repository.get_all_graphs()
        self.assertGreaterEqual(len(graphs), 3)

    def test_search_entities(self):
        """测试搜索实体"""
        graph = KnowledgeGraph(graph_name="搜索测试")
        entity1 = Entity(entity_name="人工智能", entity_type="概念")
        entity2 = Entity(entity_name="机器学习", entity_type="概念")
        entity3 = Entity(entity_name="深度学习", entity_type="概念")
        graph.add_entity(entity1)
        graph.add_entity(entity2)
        graph.add_entity(entity3)
        self.repository.save_graph(graph)

        results = self.repository.search_entities("学习", graph.graph_id)
        self.assertEqual(len(results), 2)

    def test_get_neighbors(self):
        """测试获取邻居实体"""
        graph = KnowledgeGraph(graph_name="邻居测试")
        entity1 = Entity(entity_name="A")
        entity2 = Entity(entity_name="B")
        entity3 = Entity(entity_name="C")
        graph.add_entity(entity1)
        graph.add_entity(entity2)
        graph.add_entity(entity3)

        relation = Relation(
            source_entity_id=entity1.entity_id,
            target_entity_id=entity2.entity_id,
            relation_type="连接"
        )
        graph.add_relation(relation)
        self.repository.save_graph(graph)

        neighbors = self.repository.get_neighbors(entity1.entity_id)
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0].entity_name, "B")

    def test_graph_statistics(self):
        """测试图谱统计"""
        graph = KnowledgeGraph(graph_name="统计测试")
        for i in range(5):
            graph.add_entity(Entity(entity_name=f"实体{i}", entity_type="概念"))

        for i in range(3):
            relation = Relation(
                source_entity_id=graph.entities[i].entity_id,
                target_entity_id=graph.entities[i+1].entity_id,
                relation_type="连接"
            )
            graph.add_relation(relation)

        self.repository.save_graph(graph)
        stats = self.repository.get_graph_statistics(graph.graph_id)

        self.assertEqual(stats['entity_count'], 5)
        self.assertEqual(stats['relation_count'], 3)
        self.assertIn('概念', stats['entity_types'])

    def test_extraction_history(self):
        """测试抽取历史记录"""
        history_data = {
            'extraction_id': 'test-extraction-001',
            'source_text': '测试文本内容',
            'summary': '这是一个测试摘要',
            'keywords': ['测试', '关键词'],
            'processing_time': 2.5,
            'confidence': 0.95
        }

        success = self.repository.save_extraction_history(history_data)
        self.assertTrue(success)

        history = self.repository.get_extraction_history(limit=10)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]['source_text'], '测试文本内容')


class TestGraphAnalysisWorkflow(unittest.TestCase):
    """测试图谱分析工作流"""

    def setUp(self):
        """测试前准备"""
        self.entities = [
            Entity(entity_name="人工智能", entity_type="概念", description="AI技术"),
            Entity(entity_name="机器学习", entity_type="概念", description="ML技术"),
            Entity(entity_name="深度学习", entity_type="概念", description="DL技术"),
            Entity(entity_name="神经网络", entity_type="概念", description="NN模型"),
            Entity(entity_name="自然语言处理", entity_type="概念", description="NLP技术")
        ]

        self.relations = [
            Relation(source_entity_id=self.entities[0].entity_id,
                     target_entity_id=self.entities[1].entity_id, relation_type="包含"),
            Relation(source_entity_id=self.entities[1].entity_id,
                     target_entity_id=self.entities[2].entity_id, relation_type="包含"),
            Relation(source_entity_id=self.entities[2].entity_id,
                     target_entity_id=self.entities[3].entity_id, relation_type="基于"),
            Relation(source_entity_id=self.entities[0].entity_id,
                     target_entity_id=self.entities[4].entity_id, relation_type="包含")
        ]

    def test_full_analysis_workflow(self):
        """测试完整分析工作流"""
        analyzer = KnowledgeGraphAnalyzer(self.entities, self.relations)

        stats = analyzer.calculate_statistics()
        self.assertGreater(stats.total_nodes, 0)
        self.assertGreater(stats.total_edges, 0)

        path_result = analyzer.analyze_path(
            self.entities[0].entity_id,
            self.entities[3].entity_id
        )
        self.assertIsNotNone(path_result)
        self.assertGreater(len(path_result.paths), 0)

        communities = analyzer.detect_communities_bfs()
        self.assertIsNotNone(communities.communities)

        importance = analyzer.calculate_node_importance()
        self.assertEqual(len(importance), len(self.entities))

        key_entities = analyzer.find_key_entities(3)
        self.assertLessEqual(len(key_entities), 3)

    def test_path_analysis(self):
        """测试路径分析"""
        analyzer = KnowledgeGraphAnalyzer(self.entities, self.relations)

        shortest = analyzer.find_shortest_path(
            self.entities[0].entity_id,
            self.entities[3].entity_id
        )
        self.assertIsNotNone(shortest)
        self.assertEqual(len(shortest), 4)

        all_paths = analyzer.find_all_paths(
            self.entities[0].entity_id,
            self.entities[3].entity_id,
            max_depth=5
        )
        self.assertIsInstance(all_paths, list)

    def test_visualization_data_generation(self):
        """测试可视化数据生成"""
        from core.knowledge_graph_analyzer import VisualizationDataGenerator

        analyzer = KnowledgeGraphAnalyzer(self.entities, self.relations)
        generator = VisualizationDataGenerator(analyzer)

        force_data = generator.generate_force_directed_data()
        self.assertEqual(len(force_data['nodes']), len(self.entities))
        self.assertEqual(len(force_data['edges']), len(self.relations))

        hierarchical_data = generator.generate_hierarchical_data()
        self.assertEqual(len(hierarchical_data['nodes']), len(self.entities))


class TestEndToEndWorkflow(unittest.TestCase):
    """端到端工作流测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'e2e.db')
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = KnowledgeRepository()

    def tearDown(self):
        """测试后清理"""
        pool = get_database_pool()
        pool.close_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_knowledge_graph_lifecycle(self):
        """测试完整的知识图谱生命周期"""
        graph = KnowledgeGraph(
            graph_name="E2E测试图谱",
            description="端到端测试图谱"
        )

        entities = [
            Entity(entity_name="Python", entity_type="技术", description="编程语言"),
            Entity(entity_name="Flask", entity_type="框架", description="Web框架"),
            Entity(entity_name="SQLite", entity_type="数据库", description="数据库"),
            Entity(entity_name="D3.js", entity_type="库", description="可视化库")
        ]

        for entity in entities:
            graph.add_entity(entity)

        relations = [
            Relation(source_entity_id=entities[0].entity_id,
                     target_entity_id=entities[1].entity_id, relation_type="使用"),
            Relation(source_entity_id=entities[0].entity_id,
                     target_entity_id=entities[2].entity_id, relation_type="使用"),
            Relation(source_entity_id=entities[0].entity_id,
                     target_entity_id=entities[3].entity_id, relation_type="使用")
        ]

        for relation in relations:
            graph.add_relation(relation)

        success = self.repository.save_graph(graph)
        self.assertTrue(success)

        retrieved = self.repository.get_graph(graph.graph_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved.entities), 4)
        self.assertEqual(len(retrieved.relations), 3)

        analysis = analyze_knowledge_graph(retrieved.entities, retrieved.relations)
        self.assertIn('statistics', analysis)
        self.assertIn('communities', analysis)
        self.assertIn('key_entities', analysis)

        self.assertEqual(analysis['statistics']['total_nodes'], 4)
        self.assertEqual(analysis['statistics']['total_edges'], 3)

        success = self.repository.delete_graph(graph.graph_id)
        self.assertTrue(success)

        deleted = self.repository.get_graph(graph.graph_id)
        self.assertIsNone(deleted)

    def test_multiple_graphs_management(self):
        """测试多图谱管理"""
        graphs = []
        for i in range(5):
            graph = KnowledgeGraph(graph_name=f"图谱{i}", description=f"第{i}个图谱")
            for j in range(3):
                entity = Entity(entity_name=f"实体{i}-{j}", entity_type="概念")
                graph.add_entity(entity)
            self.repository.save_graph(graph)
            graphs.append(graph)

        all_graphs = self.repository.get_all_graphs()
        self.assertGreaterEqual(len(all_graphs), 5)

        for graph in graphs[:3]:
            stats = self.repository.get_graph_statistics(graph.graph_id)
            self.assertEqual(stats['entity_count'], 3)

    def test_entity_search_and_retrieval(self):
        """测试实体搜索和检索"""
        graph = KnowledgeGraph(graph_name="搜索测试图谱")

        test_entities = [
            Entity(entity_name="机器学习", entity_type="概念"),
            Entity(entity_name="深度学习", entity_type="概念"),
            Entity(entity_name="强化学习", entity_type="概念"),
            Entity(entity_name="监督学习", entity_type="概念")
        ]

        for entity in test_entities:
            graph.add_entity(entity)

        self.repository.save_graph(graph)

        results = self.repository.search_entities("学习")
        self.assertGreaterEqual(len(results), 3)

        results = self.repository.search_entities("机器")
        self.assertGreaterEqual(len(results), 1)

        results = self.repository.search_entities("深度")
        self.assertGreaterEqual(len(results), 1)


def run_integration_tests():
    """运行集成测试"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    print("=" * 80)
    print("Arkanalyzer 集成测试套件")
    print("=" * 80)
    run_integration_tests()
