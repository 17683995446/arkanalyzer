#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 综合测试、问题发现与优化系统
"""

import sys
import os
import time
import random
import threading
import tempfile
import shutil
import json
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "arkanalyzer"))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from core.llm_connector import LLMCache
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig,
    get_database_pool
)


class OptimizationTester:
    """综合测试与优化系统"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.issues = []
        self.performance_metrics = {}
        self.database_path = os.path.join(self.temp_dir, "optimization_test.db")

    def __del__(self):
        try:
            pool = get_database_pool()
            pool.close_all()
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

    def log_issue(self, category: str, description: str, details: Dict = None):
        """记录问题"""
        issue = {
            "category": category,
            "description": description,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.issues.append(issue)
        print(f"[⚠️ {category}] {description}")

    def log_performance(self, test_name: str, elapsed: float, description: str = ""):
        """记录性能指标"""
        self.performance_metrics[test_name] = elapsed
        print(f"[⏱️ {test_name}] {elapsed:.4f}s {description}")

    def reset_database(self):
        """重置数据库"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        config = DatabaseConnectionConfig(db_path=self.database_path)
        initialize_database(config)

    def test_1_large_graph_creation_and_query(self):
        """测试1: 大规模图谱的创建和查询性能"""
        print("\n" + "=" * 80)
        print("测试1: 大规模图谱的创建和查询")
        print("=" * 80)

        self.reset_database()
        repo = KnowledgeRepository()

        print("\n创建图谱...")
        graph = KnowledgeGraph(graph_name="大规模性能测试图谱")

        num_entities = 1000
        num_relations = 3000

        entities = []
        start = time.time()
        for i in range(num_entities):
            entity_types = ["人物", "地点", "组织", "事件", "概念", "物体"]
            entity = Entity(
                entity_name=f"高性能实体_{i}_{random.randint(1000, 9999)}",
                entity_type=random.choice(entity_types),
                properties={"index": i, "group": random.randint(0, 10)},
                description=f"用于性能测试的实体 {i}"
            )
            entities.append(entity)
            graph.add_entity(entity)

        entity_time = time.time() - start
        self.log_performance("实体创建", entity_time, f"创建了 {num_entities} 个实体")

        start = time.time()
        for i in range(num_relations):
            source_idx = random.randint(0, num_entities - 1)
            target_idx = random.randint(0, num_entities - 1)
            while target_idx == source_idx:
                target_idx = random.randint(0, num_entities - 1)

            relation_types = ["相关", "包含", "属于", "引用", "导致", "相似"]
            relation = Relation(
                source_entity_id=entities[source_idx].entity_id,
                target_entity_id=entities[target_idx].entity_id,
                relation_type=random.choice(relation_types),
                weight=random.random(),
                confidence=random.random()
            )
            graph.add_relation(relation)

        relation_time = time.time() - start
        self.log_performance("关系创建", relation_time, f"创建了 {num_relations} 个关系")

        start = time.time()
        success = repo.save_graph(graph)
        save_time = time.time() - start
        self.log_performance("保存到数据库", save_time)

        if not success:
            self.log_issue("保存问题", "save_graph返回False")

        # 测试查询
        start = time.time()
        retrieved = repo.get_graph(graph.graph_id)
        load_time = time.time() - start
        self.log_performance("从数据库加载", load_time)

        if not retrieved:
            self.log_issue("加载问题", "无法从数据库加载图谱")
            return

        if len(retrieved.entities) != num_entities:
            self.log_issue("数据完整性", f"实体丢失: 期望 {num_entities}, 实际 {len(retrieved.entities)}")

        if len(retrieved.relations) != num_relations:
            self.log_issue("数据完整性", f"关系丢失: 期望 {num_relations}, 实际 {len(retrieved.relations)}")

        # 测试搜索性能
        start = time.time()
        results = repo.search_entities("高性能实体")
        search_time = time.time() - start
        self.log_performance("搜索", search_time, f"找到 {len(results)} 个结果")

        # 测试分析性能
        start = time.time()
        analyzer = KnowledgeGraphAnalyzer(retrieved.entities, retrieved.relations)
        stats = analyzer.calculate_statistics()
        analysis_time = time.time() - start
        self.log_performance("完整分析", analysis_time, f"节点: {stats.total_nodes}, 边: {stats.total_edges}")

        if stats.total_nodes != num_entities:
            self.log_issue("分析问题", f"分析器统计的节点数错误: {stats.total_nodes}")

        # 测试路径查找性能
        if num_entities > 2:
            start = time.time()
            path = analyzer.find_shortest_path(entities[0].entity_id, entities[min(50, num_entities-1)].entity_id)
            path_time = time.time() - start
            self.log_performance("路径查找", path_time, f"找到路径长度: {len(path) if path else 0}")

        total_time = entity_time + relation_time + save_time + load_time + analysis_time
        self.log_performance("测试1总耗时", total_time)

    def test_2_concurrent_operations(self):
        """测试2: 并发操作性能"""
        print("\n" + "=" * 80)
        print("测试2: 并发操作")
        print("=" * 80)

        self.reset_database()
        repo = KnowledgeRepository()

        num_threads = 5
        operations_per_thread = 20

        errors = []

        def worker(thread_id):
            for i in range(operations_per_thread):
                try:
                    graph = KnowledgeGraph(graph_name=f"并发测试_{thread_id}_{i}_{datetime.now().microsecond}")
                    for j in range(5):
                        entity = Entity(entity_name=f"实体_{thread_id}_{i}_{j}", entity_type="概念")
                        graph.add_entity(entity)
                    repo.save_graph(graph)
                except Exception as e:
                    errors.append(f"Thread {thread_id}: {str(e)}")

        start = time.time()
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        concurrent_time = time.time() - start
        self.log_performance("并发操作", concurrent_time, f"{num_threads} 线程，每个 {operations_per_thread} 操作")

        if errors:
            self.log_issue("并发问题", f"发生 {len(errors)} 个错误", {"sample": errors[:5]})

        all_graphs = repo.get_all_graphs()
        expected_graphs = num_threads * operations_per_thread

        if len(all_graphs) < expected_graphs * 0.9:  # 允许一些损失
            self.log_issue("并发问题", f"图谱数量异常: 期望 {expected_graphs}, 实际 {len(all_graphs)}")

    def test_3_memory_usage(self):
        """测试3: 内存使用情况"""
        print("\n" + "=" * 80)
        print("测试3: 内存使用（简化版）")
        print("=" * 80)

        self.reset_database()
        repo = KnowledgeRepository()

        # 循环创建和删除图谱，观察是否有问题
        start = time.time()
        for round in range(10):
            graph = KnowledgeGraph(graph_name=f"内存测试_{round}")
            for i in range(100):
                entity = Entity(entity_name=f"内存实体_{round}_{i}", entity_type="概念")
                graph.add_entity(entity)

            repo.save_graph(graph)
            repo.delete_graph(graph.graph_id)

        mem_test_time = time.time() - start
        self.log_performance("内存操作循环", mem_test_time, "10个循环")

    def test_4_edge_cases(self):
        """测试4: 各种边界情况"""
        print("\n" + "=" * 80)
        print("测试4: 边界情况")
        print("=" * 80)

        self.reset_database()
        repo = KnowledgeRepository()

        # 测试空图谱
        print("\n测试空图谱...")
        empty_graph = KnowledgeGraph(graph_name="空测试")
        success = repo.save_graph(empty_graph)
        if not success:
            self.log_issue("边界情况", "空图谱保存失败")

        retrieved = repo.get_graph(empty_graph.graph_id)
        if not retrieved:
            self.log_issue("边界情况", "空图谱加载失败")
        elif len(retrieved.entities) != 0 or len(retrieved.relations) != 0:
            self.log_issue("边界情况", "空图谱数据错误")

        # 测试只有一个实体
        print("\n测试单个实体...")
        single_entity_graph = KnowledgeGraph(graph_name="单实体")
        e = Entity(entity_name="孤独的实体", entity_type="概念")
        single_entity_graph.add_entity(e)
        repo.save_graph(single_entity_graph)
        retrieved = repo.get_graph(single_entity_graph.graph_id)
        if not retrieved or len(retrieved.entities) != 1:
            self.log_issue("边界情况", "单个实体图谱异常")

        # 测试复杂属性
        print("\n测试复杂属性...")
        complex_graph = KnowledgeGraph(graph_name="复杂属性")
        complex_entity = Entity(
            entity_name="复杂属性测试",
            entity_type="概念",
            properties={
                "nested": {"a": 1, "b": [2, 3, 4]},
                "special_chars": '!@#$%^&*()',
                "unicode": "测试中文",
                "large": "x" * 1000
            }
        )
        complex_graph.add_entity(complex_entity)
        repo.save_graph(complex_graph)

        retrieved = repo.get_graph(complex_graph.graph_id)
        if not retrieved or not retrieved.entities:
            self.log_issue("边界情况", "复杂属性加载失败")
        elif retrieved.entities[0].properties.get("nested", {}).get("a") != 1:
            self.log_issue("边界情况", "嵌套属性读取错误")

        # 测试超大数据
        print("\n测试超大数据...")
        large_graph = KnowledgeGraph(graph_name="大数据")
        for i in range(500):
            entity = Entity(
                entity_name=f"大量实体_{i}",
                entity_type="概念",
                description="x" * 2000
            )
            large_graph.add_entity(entity)

        start = time.time()
        success = repo.save_graph(large_graph)
        save_time = time.time() - start
        self.log_performance("大数据保存", save_time, f"{len(large_graph.entities)} 个实体")

        if not success:
            self.log_issue("边界情况", "大数据保存失败")

        start = time.time()
        retrieved = repo.get_graph(large_graph.graph_id)
        load_time = time.time() - start
        self.log_performance("大数据加载", load_time)

    def test_5_analyzer_edge_cases(self):
        """测试5: 分析器边界情况"""
        print("\n" + "=" * 80)
        print("测试5: 分析器边界情况")
        print("=" * 80)

        # 完全空的图
        print("\n测试空图分析...")
        try:
            analyzer = KnowledgeGraphAnalyzer([], [])
            stats = analyzer.calculate_statistics()
            if stats.total_nodes != 0 or stats.total_edges != 0:
                self.log_issue("分析器", "空图统计错误")
        except Exception as e:
            self.log_issue("分析器", f"空图异常: {str(e)}")

        # 只有孤立节点的图
        print("\n测试孤立节点图...")
        entities = []
        for i in range(5):
            entities.append(Entity(entity_name=f"孤立_{i}", entity_type="概念"))

        try:
            analyzer = KnowledgeGraphAnalyzer(entities, [])
            stats = analyzer.calculate_statistics()

            if stats.isolated_nodes != 5:
                self.log_issue("分析器", f"孤立节点统计错误: {stats.isolated_nodes}")

            # 路径查找应该返回None
            path = analyzer.find_shortest_path(entities[0].entity_id, entities[1].entity_id)
            if path is not None:
                self.log_issue("分析器", "孤立节点间应该没有路径")

        except Exception as e:
            self.log_issue("分析器", f"孤立节点图异常: {str(e)}")

        # 完全连接图
        print("\n测试完全连接图...")
        entities = []
        for i in range(5):
            entities.append(Entity(entity_name=f"节点_{i}", entity_type="概念"))

        relations = []
        for i in range(5):
            for j in range(i + 1, 5):
                relations.append(Relation(
                    source_entity_id=entities[i].entity_id,
                    target_entity_id=entities[j].entity_id,
                    relation_type="连接"
                ))

        try:
            analyzer = KnowledgeGraphAnalyzer(entities, relations)
            stats = analyzer.calculate_statistics()

            path = analyzer.find_shortest_path(entities[0].entity_id, entities[4].entity_id)
            if path and len(path) != 2:
                self.log_issue("分析器", f"完全图最短路径应该是2, 实际是{len(path)}")

        except Exception as e:
            self.log_issue("分析器", f"完全连接图异常: {str(e)}")

    def test_6_llm_cache(self):
        """测试6: LLM缓存功能"""
        print("\n" + "=" * 80)
        print("测试6: LLM缓存")
        print("=" * 80)

        try:
            cache = LLMCache(max_size=5, ttl=3600)

            cache.set("prompt1", "modelA", "response1")
            cache.set("prompt2", "modelA", "response2")

            result = cache.get("prompt1", "modelA")
            if result != "response1":
                self.log_issue("缓存", "缓存读取失败")

            cache.clear()
            result = cache.get("prompt1", "modelA")
            if result is not None:
                self.log_issue("缓存", "缓存清除失败")

            for i in range(10):
                cache.set(f"prompt{i}", "modelA", f"response{i}")

            print(f"   缓存大小测试完成")

        except Exception as e:
            self.log_issue("缓存", f"缓存测试异常: {str(e)}")

    def run_optimizations(self):
        """运行优化"""
        print("\n" + "=" * 80)
        print("优化建议")
        print("=" * 80)

        print("\n基于测试的优化建议:")

        # 根据性能指标给出建议
        for test_name, elapsed in self.performance_metrics.items():
            if elapsed > 1.0:
                print(f"  ⏱️ {test_name}: {elapsed:.4f}s - 建议优化")
            else:
                print(f"  ✅ {test_name}: {elapsed:.4f}s - 性能良好")

        if self.issues:
            print(f"\n发现 {len(self.issues)} 个问题:")
            for issue in self.issues:
                print(f"  - [{issue['category']}] {issue['description']}")
        else:
            print("\n🎉 完美！没有发现问题。")

    def generate_report(self):
        """生成最终报告"""
        print("\n" + "=" * 80)
        print("最终报告")
        print("=" * 80)

        report = {
            "timestamp": datetime.now().isoformat(),
            "issues": self.issues,
            "performance": self.performance_metrics,
            "summary": {}
        }

        total_tests = 6
        issues_count = len(self.issues)

        report["summary"] = {
            "total_tests": total_tests,
            "issues_found": issues_count,
            "performance_metrics_count": len(self.performance_metrics)
        }

        print(f"\n执行的测试: {total_tests}")
        print(f"发现的问题: {issues_count}")
        print(f"性能指标: {len(self.performance_metrics)}")

        if issues_count == 0:
            print("\n✅ 所有测试通过，系统运行良好！")
        else:
            print("\n⚠️ 系统需要关注，建议优先修复发现的问题。")

        return report

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("Arkanalyzer 综合测试与优化系统")
        print("=" * 80)

        self.test_1_large_graph_creation_and_query()
        self.test_2_concurrent_operations()
        self.test_3_memory_usage()
        self.test_4_edge_cases()
        self.test_5_analyzer_edge_cases()
        self.test_6_llm_cache()

        self.run_optimizations()
        return self.generate_report()


def main():
    tester = OptimizationTester()
    report = tester.run_all_tests()
    print("\n完成！")


if __name__ == "__main__":
    main()
