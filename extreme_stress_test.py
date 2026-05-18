#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 极限压力测试套件
测试系统在极端条件下的稳定性和性能表现
"""

import sys
import os
import time
import threading
import tempfile
import shutil
import gc
import random
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from typing import Dict, List, Any
from datetime import datetime
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import get_knowledge_repository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig,
    get_database_pool
)


class StressTestReporter:
    """压力测试报告生成器"""

    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = time.time()

    def record_result(self, test_name: str, success: bool, duration: float, details: Dict[str, Any] = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"[{status}] {test_name} - {duration:.3f}s")

    def generate_report(self):
        """生成测试报告"""
        end_time = time.time()
        total_duration = end_time - self.start_time

        success_count = sum(1 for r in self.test_results if r["success"])
        total_count = len(self.test_results)

        print("\n" + "=" * 80)
        print("极限压力测试报告")
        print("=" * 80)
        print(f"总测试数: {total_count}")
        print(f"通过: {success_count}")
        print(f"失败: {total_count - success_count}")
        print(f"总耗时: {total_duration:.2f}s")
        print("\n详细结果:")

        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['test_name']} - {result['duration']:.3f}s")


class ExtremeScenarioTester:
    """极端场景测试器"""

    def __init__(self):
        self.reporter = StressTestReporter()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "stress_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = get_knowledge_repository()

    def __del__(self):
        """清理资源"""
        try:
            pool = get_database_pool()
            pool.close_all()
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

    def test_extremely_large_graph_creation(self):
        """测试超大规模图谱创建 - 10000个实体，50000个关系"""
        test_name = "超大规模图谱创建测试"
        start_time = time.time()
        success = False

        try:
            graph = KnowledgeGraph(graph_name="极限压力测试图谱")

            print(f"  → 创建10000个实体...")
            entities = []
            for i in range(10000):
                entity_types = ["人物", "地点", "组织", "事件", "概念", "物体"]
                entity = Entity(
                    entity_name=f"极限测试实体_{i}_{uuid.uuid4().hex[:8]}",
                    entity_type=random.choice(entity_types),
                    description=f"这是一个用于压力测试的实体，序号为{i}",
                    properties={"index": i, "test_type": "stress_test"}
                )
                entities.append(entity)
                graph.add_entity(entity)
                if i % 1000 == 0:
                    print(f"    已创建{i}个实体...")

            print(f"  → 创建50000个关系...")
            for i in range(50000):
                source_idx = random.randint(0, 9999)
                target_idx = random.randint(0, 9999)
                while target_idx == source_idx:
                    target_idx = random.randint(0, 9999)

                relation_types = ["相关", "连接", "包含", "属于", "关联"]
                relation = Relation(
                    source_entity_id=entities[source_idx].entity_id,
                    target_entity_id=entities[target_idx].entity_id,
                    relation_type=random.choice(relation_types),
                    weight=random.random(),
                    properties={"index": i}
                )
                graph.add_relation(relation)
                if i % 5000 == 0:
                    print(f"    已创建{i}个关系...")

            print(f"  → 保存到数据库...")
            save_start = time.time()
            success = self.repository.save_graph(graph)
            save_duration = time.time() - save_start

            print(f"  → 验证结果...")
            retrieved = self.repository.get_graph(graph.graph_id)

            duration = time.time() - start_time
            details = {
                "entities_count": len(graph.entities),
                "relations_count": len(graph.relations),
                "save_duration": save_duration,
                "verify_success": retrieved is not None and len(retrieved.entities) == 10000
            }

            self.reporter.record_result(test_name, success, duration, details)

        except Exception as e:
            duration = time.time() - start_time
            self.reporter.record_result(test_name, False, duration, {"error": str(e)})
            print(f"    错误: {e}")
            import traceback
            traceback.print_exc()

    def test_concurrent_graph_operations(self):
        """测试高并发图谱操作"""
        test_name = "高并发图谱操作测试"
        start_time = time.time()
        success = True
        errors = []

        try:
            num_threads = 20
            operations_per_thread = 50
            graphs_created = []

            def worker(thread_id):
                for i in range(operations_per_thread):
                    try:
                        graph = KnowledgeGraph(
                            graph_name=f"并发测试_{thread_id}_{i}_{uuid.uuid4().hex[:6]}",
                            description=f"线程{thread_id}的第{i}个测试图谱"
                        )

                        for j in range(10):
                            entity = Entity(
                                entity_name=f"并发实体_{thread_id}_{i}_{j}",
                                entity_type=random.choice(["概念", "人物", "地点"])
                            )
                            graph.add_entity(entity)

                        self.repository.save_graph(graph)
                        graphs_created.append(graph.graph_id)

                        if (i + 1) % 10 == 0:
                            print(f"    线程{thread_id}完成{i + 1}个操作...")

                    except Exception as e:
                        errors.append(f"线程{thread_id}在第{i}个操作失败: {e}")
                        import traceback
                        print(f"    线程{thread_id}错误: {e}")
                        print(traceback.format_exc())

            print(f"  → 启动{num_threads}个线程，每个执行{operations_per_thread}个操作...")

            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            if errors:
                print(f"  → 发现{len(errors)}个错误:")
                for error in errors[:5]:
                    print(f"    - {error}")
                success = False

            total_ops = num_threads * operations_per_thread
            success_rate = (total_ops - len(errors)) / total_ops if total_ops > 0 else 0

            duration = time.time() - start_time
            details = {
                "total_operations": total_ops,
                "errors_count": len(errors),
                "success_rate": success_rate,
                "graphs_created": len(graphs_created)
            }

            self.reporter.record_result(test_name, success, duration, details)

        except Exception as e:
            duration = time.time() - start_time
            self.reporter.record_result(test_name, False, duration, {"error": str(e)})
            print(f"    错误: {e}")
            import traceback
            traceback.print_exc()

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        test_name = "内存使用稳定性测试"
        start_time = time.time()
        success = True

        try:
            if HAS_PSUTIL:
                process = psutil.Process()
                initial_memory = process.memory_info().rss / (1024 * 1024)

                print(f"  → 初始内存使用: {initial_memory:.2f}MB")
                print(f"  → 执行100次图谱创建和删除循环...")

                memory_usage_history = []
                for i in range(100):
                    graph = KnowledgeGraph(graph_name=f"内存测试_{i}")

                    for j in range(100):
                        entity = Entity(entity_name=f"mem_test_{i}_{j}", entity_type="概念")
                        graph.add_entity(entity)

                    self.repository.save_graph(graph)
                    self.repository.delete_graph(graph.graph_id)

                    if (i + 1) % 10 == 0:
                        current_memory = process.memory_info().rss / (1024 * 1024)
                        memory_usage_history.append(current_memory)
                        print(f"    第{i + 1}轮，内存: {current_memory:.2f}MB")

                gc.collect()
                final_memory = process.memory_info().rss / (1024 * 1024)
                memory_growth = final_memory - initial_memory

                print(f"  → 最终内存使用: {final_memory:.2f}MB")
                print(f"  → 内存增长: {memory_growth:.2f}MB")

                if memory_growth > 10:  # 超过10MB视为异常增长
                    success = False
                    print(f"  ⚠️ 警告: 内存增长超过10MB，可能存在泄漏!")

                details = {
                    "initial_memory_mb": initial_memory,
                    "final_memory_mb": final_memory,
                    "memory_growth_mb": memory_growth,
                    "peak_memory_mb": max(memory_usage_history) if memory_usage_history else final_memory
                }
            else:
                print(f"  → psutil模块未安装，跳过内存测试，执行简化操作...")
                for i in range(50):
                    graph = KnowledgeGraph(graph_name=f"内存测试_{i}")
                    for j in range(50):
                        entity = Entity(entity_name=f"mem_test_{i}_{j}", entity_type="概念")
                        graph.add_entity(entity)
                    self.repository.save_graph(graph)
                    self.repository.delete_graph(graph.graph_id)
                details = {"psutil_available": False, "note": "内存监控跳过"}

            duration = time.time() - start_time
            self.reporter.record_result(test_name, success, duration, details)

        except Exception as e:
            duration = time.time() - start_time
            self.reporter.record_result(test_name, False, duration, {"error": str(e)})
            print(f"    错误: {e}")
            import traceback
            traceback.print_exc()

    def test_large_graph_analysis_performance(self):
        """测试大规模图谱分析性能"""
        test_name = "大规模图谱分析性能测试"
        start_time = time.time()
        success = True

        try:
            print(f"  → 创建中等规模图谱(2000实体，8000关系)...")
            graph = KnowledgeGraph(graph_name="分析性能测试图谱")

            entities = []
            for i in range(2000):
                entity = Entity(
                    entity_name=f"分析实体_{i}",
                    entity_type=random.choice(["概念", "人物", "组织", "事件"])
                )
                entities.append(entity)
                graph.add_entity(entity)

            for i in range(8000):
                source_idx = random.randint(0, 1999)
                target_idx = random.randint(0, 1999)
                while target_idx == source_idx:
                    target_idx = random.randint(0, 1999)

                relation = Relation(
                    source_entity_id=entities[source_idx].entity_id,
                    target_entity_id=entities[target_idx].entity_id,
                    relation_type=random.choice(["相关", "关联", "连接"]),
                    weight=random.random()
                )
                graph.add_relation(relation)

            print(f"  → 保存图谱...")
            self.repository.save_graph(graph)

            print(f"  → 执行图谱分析...")
            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)

            stat_time = time.time()
            stats = analyzer.calculate_statistics()
            stat_duration = time.time() - stat_time

            print(f"    统计计算耗时: {stat_duration:.3f}s")

            path_time = time.time()
            if len(graph.entities) >= 2:
                path = analyzer.find_shortest_path(
                    graph.entities[0].entity_id,
                    graph.entities[-1].entity_id
                )
            path_duration = time.time() - path_time

            print(f"    路径查找耗时: {path_duration:.3f}s")

            comm_time = time.time()
            communities = analyzer.detect_communities_bfs()
            comm_duration = time.time() - comm_time

            print(f"    社区检测耗时: {comm_duration:.3f}s")

            key_time = time.time()
            key_entities = analyzer.find_key_entities(20)
            key_duration = time.time() - key_time

            print(f"    关键实体识别耗时: {key_duration:.3f}s")

            total_analysis_duration = time.time() - start_time
            success = all([
                stat_duration < 1.0,
                path_duration < 2.0,
                comm_duration < 5.0,
                key_duration < 1.0
            ])

            if not success:
                print(f"  ⚠️ 警告: 部分分析操作超过预期时间!")

            duration = time.time() - start_time
            details = {
                "graph_size": {
                    "entities": 2000,
                    "relations": 8000
                },
                "analysis_times": {
                    "statistics": stat_duration,
                    "path": path_duration,
                    "communities": comm_duration,
                    "key_entities": key_duration
                },
                "total_analysis": total_analysis_duration
            }

            self.reporter.record_result(test_name, success, duration, details)

        except Exception as e:
            duration = time.time() - start_time
            self.reporter.record_result(test_name, False, duration, {"error": str(e)})
            print(f"    错误: {e}")
            import traceback
            traceback.print_exc()

    def test_extreme_edge_cases(self):
        """测试各种极端边缘情况"""
        test_name = "极端边缘情况测试"
        start_time = time.time()

        edge_cases = []

        try:
            print(f"  → 测试空图谱...")
            empty_graph = KnowledgeGraph(graph_name="空图谱测试")
            success_empty = self.repository.save_graph(empty_graph)
            edge_cases.append(("空图谱保存", success_empty))

            print(f"  → 测试单实体图谱...")
            single_graph = KnowledgeGraph(graph_name="单实体图谱")
            single_graph.add_entity(Entity(entity_name="孤独的实体", entity_type="概念"))
            success_single = self.repository.save_graph(single_graph)
            edge_cases.append(("单实体图谱", success_single))

            print(f"  → 测试重复关系图谱...")
            dup_graph = KnowledgeGraph(graph_name="重复关系图谱")
            e1 = Entity(entity_name="起点", entity_type="概念")
            e2 = Entity(entity_name="终点", entity_type="概念")
            dup_graph.add_entity(e1)
            dup_graph.add_entity(e2)
            for i in range(100):
                dup_graph.add_relation(Relation(
                    source_entity_id=e1.entity_id,
                    target_entity_id=e2.entity_id,
                    relation_type="重复关系"
                ))
            success_dup = self.repository.save_graph(dup_graph)
            edge_cases.append(("重复关系图谱", success_dup))

            print(f"  → 测试超长实体名...")
            long_graph = KnowledgeGraph(graph_name="超长名图谱")
            super_long_name = "这是一个非常长的实体名，长度超过了1000字符" * 20
            long_entity = Entity(
                entity_name=super_long_name,
                entity_type="概念",
                description=super_long_name * 10
            )
            long_graph.add_entity(long_entity)
            success_long = self.repository.save_graph(long_graph)
            edge_cases.append(("超长名称实体", success_long))

            print(f"  → 测试特殊字符实体...")
            special_graph = KnowledgeGraph(graph_name="特殊字符图谱")
            special_names = [
                "🚀测试🤖",
                '实体\'包含"引号',
                "\n换行\n实体",
                "😎表情符号实体😎",
                "<script>alert('xss')</script>"
            ]
            for name in special_names:
                special_graph.add_entity(Entity(entity_name=name, entity_type="概念"))
            success_special = self.repository.save_graph(special_graph)
            edge_cases.append(("特殊字符实体", success_special))

            all_success = all(case[1] for case in edge_cases)

            duration = time.time() - start_time
            details = {
                "cases": edge_cases,
                "passing_cases": sum(1 for case in edge_cases if case[1]),
                "total_cases": len(edge_cases)
            }

            self.reporter.record_result(test_name, all_success, duration, details)

        except Exception as e:
            duration = time.time() - start_time
            self.reporter.record_result(test_name, False, duration, {"error": str(e)})
            print(f"    错误: {e}")
            import traceback
            traceback.print_exc()

    def run_all_tests(self):
        """运行所有压力测试"""
        print("=" * 80)
        print("Arkanalyzer 极限压力测试开始")
        print("=" * 80)

        self.test_extremely_large_graph_creation()
        self.test_concurrent_graph_operations()
        self.test_memory_usage_stability()
        self.test_large_graph_analysis_performance()
        self.test_extreme_edge_cases()

        self.reporter.generate_report()


def main():
    """主函数"""
    tester = ExtremeScenarioTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
