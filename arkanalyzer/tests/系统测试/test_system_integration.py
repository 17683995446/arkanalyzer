#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 系统测试套件
测试完整系统功能，包括API服务、性能测试和端到端场景
"""

import unittest
import os
import sys
import json
import time
import tempfile
import shutil
import threading
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config_loader import ConfigLoader, SystemConfig
from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from core.knowledge_extractor import KnowledgeExtractor
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig,
    get_database_pool
)


class TestSystemConfiguration(unittest.TestCase):
    """测试系统配置"""

    def test_config_loader_initialization(self):
        """测试配置加载器初始化"""
        config = ConfigLoader()
        self.assertIsNotNone(config.llm_config)
        self.assertIsNotNone(config.db_config)
        self.assertIsNotNone(config.api_config)

    def test_config_validation(self):
        """测试配置验证"""
        config = ConfigLoader()
        self.assertTrue(config.validate_config())

    def test_default_paths(self):
        """测试默认路径配置"""
        config = ConfigLoader()
        self.assertIsNotNone(config.db_config.db_path)
        self.assertIsNotNone(config.sys_config.log_path)


class TestSystemPerformance(unittest.TestCase):
    """系统性能测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'perf.db')
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = KnowledgeRepository()

    def tearDown(self):
        """测试后清理"""
        pool = get_database_pool()
        pool.close_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_large_graph_creation(self):
        """测试大规模图谱创建"""
        start_time = time.time()
        graph = KnowledgeGraph(graph_name="性能测试图谱")

        num_entities = 100
        for i in range(num_entities):
            entity = Entity(
                entity_name=f"实体{i}",
                entity_type="概念",
                description=f"这是实体{i}的描述"
            )
            graph.add_entity(entity)

        for i in range(num_entities // 2):
            relation = Relation(
                source_entity_id=graph.entities[i].entity_id,
                target_entity_id=graph.entities[(i + 1) % num_entities].entity_id,
                relation_type="连接"
            )
            graph.add_relation(relation)

        end_time = time.time()
        creation_time = end_time - start_time

        print(f"\n创建 {num_entities} 个实体耗时: {creation_time:.3f}s")
        self.assertLess(creation_time, 5.0, "图谱创建时间应小于5秒")

    def test_graph_statistics_performance(self):
        """测试图谱统计性能"""
        graph = KnowledgeGraph(graph_name="统计性能测试")

        for i in range(50):
            entity = Entity(entity_name=f"实体{i}", entity_type="概念")
            graph.add_entity(entity)

        for i in range(30):
            relation = Relation(
                source_entity_id=graph.entities[i].entity_id,
                target_entity_id=graph.entities[(i + 1) % 50].entity_id,
                relation_type="连接"
            )
            graph.add_relation(relation)

        start_time = time.time()
        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        stats = analyzer.calculate_statistics()
        end_time = time.time()

        stats_time = end_time - start_time
        print(f"\n统计计算耗时: {stats_time:.3f}s")
        self.assertLess(stats_time, 1.0, "统计计算应小于1秒")

    def test_database_operations_performance(self):
        """测试数据库操作性能"""
        graph = KnowledgeGraph(graph_name="数据库性能测试")

        for i in range(20):
            entity = Entity(entity_name=f"实体{i}", entity_type="概念")
            graph.add_entity(entity)

        start_time = time.time()
        self.repository.save_graph(graph)
        retrieval_time = time.time() - start_time

        print(f"\n数据库保存和检索耗时: {retrieval_time:.3f}s")
        self.assertLess(retrieval_time, 2.0, "数据库操作应小于2秒")

    def test_concurrent_database_access(self):
        """测试并发数据库访问"""
        graph = KnowledgeGraph(graph_name="并发测试图谱")
        for i in range(10):
            graph.add_entity(Entity(entity_name=f"实体{i}", entity_type="概念"))

        def save_graph():
            test_graph = KnowledgeGraph(graph_name=f"并发图谱{threading.current_thread().name}")
            for i in range(5):
                test_graph.add_entity(Entity(entity_name=f"并发实体{i}", entity_type="概念"))
            self.repository.save_graph(test_graph)

        threads = []
        num_threads = 5

        start_time = time.time()
        for i in range(num_threads):
            t = threading.Thread(target=save_graph, name=f"Thread-{i}")
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        end_time = time.time()
        concurrent_time = end_time - start_time

        print(f"\n{num_threads}个线程并发操作耗时: {concurrent_time:.3f}s")
        self.assertLess(concurrent_time, 5.0, "并发操作应能在5秒内完成")


class TestSystemReliability(unittest.TestCase):
    """系统可靠性测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'reliability.db')
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = KnowledgeRepository()

    def tearDown(self):
        """测试后清理"""
        pool = get_database_pool()
        pool.close_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_graph_handling(self):
        """测试空图谱处理"""
        graph = KnowledgeGraph(graph_name="空图谱")
        self.repository.save_graph(graph)

        retrieved = self.repository.get_graph(graph.graph_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved.entities), 0)
        self.assertEqual(len(retrieved.relations), 0)

    def test_graph_with_special_characters(self):
        """测试包含特殊字符的图谱"""
        graph = KnowledgeGraph(
            graph_name="特殊字符图谱-测试!@#$%",
            description="包含特殊字符的描述：中文、English、🎉🎊"
        )

        entity = Entity(
            entity_name="特殊实体'\"&<>",
            entity_type="概念",
            description="特殊描述\n\t\r"
        )
        graph.add_entity(entity)

        success = self.repository.save_graph(graph)
        self.assertTrue(success)

        retrieved = self.repository.get_graph(graph.graph_id)
        self.assertIsNotNone(retrieved)

    def test_long_text_handling(self):
        """测试长文本处理"""
        graph = KnowledgeGraph(graph_name="长文本图谱")
        long_description = "A" * 10000

        entity = Entity(
            entity_name="长文本实体",
            entity_type="概念",
            description=long_description,
            properties={"long_field": long_description}
        )
        graph.add_entity(entity)

        success = self.repository.save_graph(graph)
        self.assertTrue(success)

        retrieved = self.repository.get_graph(graph.graph_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved.entities[0].description), 10000)

    def test_graph_versioning(self):
        """测试图谱版本控制"""
        graph = KnowledgeGraph(graph_name="版本测试")
        self.assertEqual(graph.version, 1)

        entity = Entity(entity_name="实体", entity_type="概念")
        graph.add_entity(entity)
        self.repository.save_graph(graph)

        retrieved_v1 = self.repository.get_graph(graph.graph_id)
        self.assertEqual(retrieved_v1.version, 1)

        retrieved_v1.description = "更新描述"
        self.repository.save_graph(retrieved_v1)

        retrieved_v2 = self.repository.get_graph(graph.graph_id)
        self.assertEqual(retrieved_v2.version, 2)


class TestSystemIntegration(unittest.TestCase):
    """系统集成测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'integration.db')
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = KnowledgeRepository()

    def tearDown(self):
        """测试后清理"""
        pool = get_database_pool()
        pool.close_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_workflow(self):
        """测试完整工作流"""
        graph = KnowledgeGraph(
            graph_name="完整工作流测试",
            description="测试从创建到分析的全流程"
        )

        entities = []
        for i, name in enumerate(["人工智能", "机器学习", "深度学习", "神经网络"]):
            entity = Entity(
                entity_name=name,
                entity_type="概念",
                description=f"{name}相关知识"
            )
            entities.append(entity)
            graph.add_entity(entity)

        relations = [
            Relation(source_entity_id=entities[0].entity_id,
                     target_entity_id=entities[1].entity_id, relation_type="包含"),
            Relation(source_entity_id=entities[1].entity_id,
                     target_entity_id=entities[2].entity_id, relation_type="包含"),
            Relation(source_entity_id=entities[2].entity_id,
                     target_entity_id=entities[3].entity_id, relation_type="基于")
        ]

        for relation in relations:
            graph.add_relation(relation)

        self.repository.save_graph(graph)

        retrieved = self.repository.get_graph(graph.graph_id)
        self.assertIsNotNone(retrieved)

        stats = self.repository.get_graph_statistics(graph.graph_id)
        self.assertEqual(stats['entity_count'], 4)
        self.assertEqual(stats['relation_count'], 3)

        entities_result = self.repository.search_entities("学习")
        self.assertGreaterEqual(len(entities_result), 2)

        analyzer = KnowledgeGraphAnalyzer(retrieved.entities, retrieved.relations)
        summary = analyzer.get_graph_summary()

        self.assertIn('statistics', summary)
        self.assertIn('communities', summary)
        self.assertIn('key_entities', summary)

    def test_multiple_graph_operations(self):
        """测试多图谱操作"""
        graphs = []

        for i in range(10):
            graph = KnowledgeGraph(graph_name=f"多图谱{i}")
            for j in range(5):
                graph.add_entity(Entity(entity_name=f"实体{j}", entity_type="概念"))
            self.repository.save_graph(graph)
            graphs.append(graph)

        all_graphs = self.repository.get_all_graphs()
        self.assertGreaterEqual(len(all_graphs), 10)

        for graph in graphs:
            stats = self.repository.get_graph_statistics(graph.graph_id)
            self.assertEqual(stats['entity_count'], 5)

        for graph in graphs[:5]:
            self.repository.delete_graph(graph.graph_id)

        remaining = self.repository.get_all_graphs()
        self.assertGreaterEqual(len(remaining), 5)


class TestDataIntegrity(unittest.TestCase):
    """数据完整性测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'integrity.db')
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = KnowledgeRepository()

    def tearDown(self):
        """测试后清理"""
        pool = get_database_pool()
        pool.close_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_entity_relationship_integrity(self):
        """测试实体关系完整性"""
        graph = KnowledgeGraph(graph_name="完整性测试")
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

        retrieved = self.repository.get_graph(graph.graph_id)

        retrieved_entity1 = retrieved.get_entity_by_id(entity1.entity_id)
        self.assertIsNotNone(retrieved_entity1)
        self.assertEqual(retrieved_entity1.entity_name, "A")

        neighbors = retrieved.get_neighbors(entity1.entity_id)
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0].entity_name, "B")

    def test_graph_metadata_persistence(self):
        """测试图谱元数据持久化"""
        graph = KnowledgeGraph(
            graph_name="元数据测试",
            metadata={
                "author": "test",
                "tags": ["test", "sample"],
                "settings": {"color": "#00d4ff"}
            }
        )

        self.repository.save_graph(graph)

        retrieved = self.repository.get_graph(graph.graph_id)
        self.assertEqual(retrieved.metadata['author'], "test")
        self.assertEqual(retrieved.metadata['tags'], ["test", "sample"])


def run_system_tests():
    """运行系统测试"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    print("=" * 80)
    print("Arkanalyzer 系统测试套件")
    print("=" * 80)
    run_system_tests()
