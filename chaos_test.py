#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极端混乱场景测试 - 遵循慢工出细活原则
测试高并发、混合操作、大数据量等混乱场景
"""

import os
import sys
import tempfile
import shutil
import random
import time
import gc
import threading
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph, KnowledgeGraphManager
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class ChaosTest:
    """极端混乱场景测试"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "chaos_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path, pool_size=10)
        initialize_database(config)
        self.repo = KnowledgeRepository()
        self.errors = []
        self.operations = []
        self.lock = threading.Lock()
        
        # 用于测试的全局变量
        self.active_graph_ids = []
        self.stop_event = threading.Event()

    def log_error(self, category: str, error: Exception, details: Dict = None):
        """记录错误"""
        with self.lock:
            self.errors.append({
                "timestamp": datetime.now().isoformat(),
                "category": category,
                "error": str(error),
                "details": details or {}
            })
            print(f"⚠️  ERROR: [{category}] {error}")

    def log_operation(self, op_type: str, success: bool):
        """记录操作"""
        with self.lock:
            self.operations.append({
                "type": op_type,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })

    def create_random_graph(self, graph_index: int) -> Optional[KnowledgeGraph]:
        """创建随机图谱 - 混乱数据"""
        try:
            manager = KnowledgeGraphManager()
            graph = manager.create_graph(
                f"Chaos-Graph-{graph_index}-{uuid.uuid4()}",
                f"混乱场景测试图谱 #{graph_index}, 包含随机内容"
            )
            
            # 随机实体数量
            num_entities = random.randint(5, 150)
            entities = []
            
            for i in range(num_entities):
                entity_name = f"Entity-{graph_index}-{i}-{uuid.uuid4()}"
                
                # 随机属性 - 包括可能的极端值
                properties = {
                    "index": i,
                    "random": random.random(),
                    "number": random.randint(-1000000, 1000000),
                    "description": "x" * random.randint(0, 5000),  # 可能很长
                    "nested": {
                        "level1": {
                            "level2": {
                                "data": random.randbytes(random.randint(0, 500)).hex()
                            }
                        }
                    },
                    "list": [random.random() for _ in range(random.randint(0, 100))]
                }
                
                entity = Entity(
                    entity_name=entity_name,
                    entity_type=random.choice([
                        "CONCEPT", "PERSON", "PLACE", "ORGANIZATION", "EVENT", 
                        "THING", "UNKNOWN", "MIXED", "LARGE", "SMALL"
                    ]),
                    description="这是一个用于混乱测试的实体，包含随机内容。" * random.randint(0, 10),
                    properties=properties,
                    source=random.choice(["manual", "auto", "test", None, "", "chaos-source"]),
                    confidence=random.random()
                )
                entities.append(entity)
                graph.add_entity(entity)
            
            # 创建随机关系
            num_relations = random.randint(10, int(num_entities * 2.5))
            for i in range(num_relations):
                if len(entities) < 2:
                    break
                
                src_idx = random.randint(0, len(entities)-1)
                tgt_idx = random.randint(0, len(entities)-1)
                while tgt_idx == src_idx:
                    tgt_idx = random.randint(0, len(entities)-1)
                
                relation = Relation(
                    source_entity_id=entities[src_idx].entity_id,
                    target_entity_id=entities[tgt_idx].entity_id,
                    relation_type=random.choice([
                        "RELATES_TO", "CONTAINS", "PART_OF", "ASSOCIATED_WITH",
                        "REFERENCES", "DEPENDS_ON", "USES", "CAUSES", "PRECEDES",
                        "FOLLOWS", "BELONGS_TO", "EQUALS", "DIFFERENT_FROM", "CHILD_OF"
                    ]),
                    weight=random.random() * random.randint(-10, 10),  # 可能为负
                    description=f"关系 #{i} 用于混乱测试" * random.randint(0, 5),
                    properties={"random": random.random(), "index": i}
                )
                graph.add_relation(relation)
            
            return graph
        except Exception as e:
            self.log_error("create_graph", e, {"index": graph_index})
            return None

    def worker_thread(self, worker_id: int, operations_per_worker: int):
        """工作线程 - 执行随机混乱操作"""
        for i in range(operations_per_worker):
            if self.stop_event.is_set():
                break
            
            # 随机选择操作
            op_choice = random.random()
            success = False
            
            try:
                if op_choice < 0.15:
                    # 创建新图谱
                    graph = self.create_random_graph(worker_id * 1000 + i)
                    if graph:
                        self.repo.save_graph(graph)
                        with self.lock:
                            self.active_graph_ids.append(graph.graph_id)
                        success = True
                        self.log_operation("CREATE", True)
                
                elif op_choice < 0.35:
                    # 读取随机图谱
                    with self.lock:
                        if self.active_graph_ids:
                            graph_id = random.choice(self.active_graph_ids)
                            self.repo.get_graph(graph_id)
                            success = True
                            self.log_operation("READ", True)
                
                elif op_choice < 0.55:
                    # 搜索实体
                    search_query = random.choice([
                        "Entity", str(random.randint(0, 1000)), "Chaos",
                        "".join([chr(random.randint(65, 90)) for _ in range(3)]),
                        "", "*"
                    ])
                    self.repo.search_entities(search_query)
                    success = True
                    self.log_operation("SEARCH", True)
                
                elif op_choice < 0.70:
                    # 删除图谱
                    with self.lock:
                        if self.active_graph_ids:
                            graph_id = self.active_graph_ids.pop(random.randint(0, len(self.active_graph_ids)-1))
                            self.repo.delete_graph(graph_id)
                            success = True
                            self.log_operation("DELETE", True)
                
                elif op_choice < 0.85:
                    # 获取统计信息
                    with self.lock:
                        if self.active_graph_ids:
                            graph_id = random.choice(self.active_graph_ids)
                            self.repo.get_graph_statistics(graph_id)
                            success = True
                            self.log_operation("STATS", True)
                
                else:
                    # 分析操作
                    with self.lock:
                        if self.active_graph_ids:
                            graph_id = random.choice(self.active_graph_ids)
                            graph = self.repo.get_graph(graph_id)
                            if graph:
                                analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
                                analyzer.calculate_statistics()
                                analyzer.find_key_entities(random.randint(1, 10))
                                analyzer.detect_communities_bfs()
                                if len(graph.entities) >= 2:
                                    src = graph.entities[0].entity_id
                                    tgt = graph.entities[-1].entity_id
                                    analyzer.find_shortest_path(src, tgt)
                            success = True
                            self.log_operation("ANALYZE", True)
                
                # 随机延迟 - 0到200毫秒
                if random.random() < 0.2:
                    time.sleep(random.random() * 0.2)
            
            except Exception as e:
                self.log_error(f"worker_{worker_id}", e, {"iteration": i})
                self.log_operation("ERROR", False)
            
            # 随机失败后继续（模拟真实网络不稳定）
            if random.random() < 0.05:
                time.sleep(random.random() * 0.5)

    def run_chaos_test(self, num_workers: int = 20, operations_per_worker: int = 500):
        """运行混乱场景测试"""
        print("=" * 80)
        print("🔥 极端混乱场景测试开始")
        print("=" * 80)
        print(f"  开始时间: {datetime.now().isoformat()}")
        print(f"  工作线程: {num_workers}")
        print(f"  每个线程操作: {operations_per_worker}")
        print()
        
        start_time = time.time()
        
        # 先创建一些初始图谱
        print("📊 创建初始图谱...")
        for i in range(5):
            graph = self.create_random_graph(i)
            if graph:
                self.repo.save_graph(graph)
                self.active_graph_ids.append(graph.graph_id)
        print(f"  已创建 {len(self.active_graph_ids)} 个初始图谱")
        print()
        
        # 启动工作线程
        print("🚀 启动混乱测试线程...")
        threads = []
        for worker_id in range(num_workers):
            t = threading.Thread(
                target=self.worker_thread,
                args=(worker_id, operations_per_worker),
                daemon=True
            )
            threads.append(t)
            t.start()
        
        # 等待线程完成
        for t in threads:
            t.join()
        
        total_time = time.time() - start_time
        print()
        print("=" * 80)
        print("📊 混乱场景测试结果")
        print("=" * 80)
        
        # 统计结果
        with self.lock:
            total_ops = len(self.operations)
            successful_ops = sum(1 for op in self.operations if op["success"])
            error_count = len(self.errors)
            
        print(f"  总耗时: {total_time:.2f} 秒")
        print(f"  总操作数: {total_ops}")
        print(f"  成功操作: {successful_ops}")
        print(f"  发现错误: {error_count}")
        print(f"  仍然活跃的图谱: {len(self.active_graph_ids)}")
        
        if error_count > 0:
            print()
            print("⚠️  发现的错误 (前20个):")
            for i, err in enumerate(self.errors[:20]):
                print(f"  {i+1}. [{err['category']}] {err['error']}")
        
        print()
        print("=" * 80)
        
        return error_count == 0

    def run_extreme_edge_cases(self):
        """运行极端边界测试"""
        print("\n" + "=" * 80)
        print("📋 极端边界场景测试")
        print("=" * 80)
        
        edge_cases_passed = 0
        edge_cases_total = 0
        
        # 1. 空图谱
        print("\n1. 测试空图谱...")
        edge_cases_total += 1
        try:
            manager = KnowledgeGraphManager()
            empty_graph = manager.create_graph("Empty-Test", "完全空的图谱")
            self.repo.save_graph(empty_graph)
            retrieved = self.repo.get_graph(empty_graph.graph_id)
            assert retrieved is not None
            assert len(retrieved.entities) == 0
            assert len(retrieved.relations) == 0
            self.repo.delete_graph(empty_graph.graph_id)
            print("   ✅ 通过")
            edge_cases_passed += 1
        except Exception as e:
            self.log_error("empty_graph", e)
            print(f"   ❌ 失败: {e}")
        
        # 2. 只有一个实体的图谱
        print("\n2. 测试只有一个实体的图谱...")
        edge_cases_total += 1
        try:
            graph = KnowledgeGraph(graph_name="Single-Entity", description="只有一个实体")
            entity = Entity(entity_name="Only-One", entity_type="THING")
            graph.add_entity(entity)
            self.repo.save_graph(graph)
            neighbors = graph.get_neighbors(entity.entity_id)
            assert len(neighbors) == 0
            self.repo.delete_graph(graph.graph_id)
            print("   ✅ 通过")
            edge_cases_passed += 1
        except Exception as e:
            self.log_error("single_entity", e)
            print(f"   ❌ 失败: {e}")
        
        # 3. 超大属性值
        print("\n3. 测试超大属性...")
        edge_cases_total += 1
        try:
            graph = KnowledgeGraph(graph_name="Huge-Properties")
            huge_entity = Entity(
                entity_name="Huge-Data-Entity",
                entity_type="LARGE",
                properties={
                    "huge_text": "x" * 100000,  # 10万字符
                    "huge_number": 10**1000,
                    "huge_list": [i for i in range(10000)]
                }
            )
            graph.add_entity(huge_entity)
            self.repo.save_graph(graph)
            retrieved = self.repo.get_graph(graph.graph_id)
            assert retrieved is not None
            assert len(retrieved.entities) == 1
            self.repo.delete_graph(graph.graph_id)
            print("   ✅ 通过")
            edge_cases_passed += 1
        except Exception as e:
            self.log_error("huge_properties", e)
            print(f"   ❌ 失败: {e}")
        
        # 4. 深度关系链
        print("\n4. 测试深度关系链...")
        edge_cases_total += 1
        try:
            graph = KnowledgeGraph(graph_name="Deep-Chain", description="长链式结构")
            entities = []
            num_chain = 100
            
            for i in range(num_chain):
                entity = Entity(entity_name=f"Chain-{i}", entity_type="NODE")
                entities.append(entity)
                graph.add_entity(entity)
            
            for i in range(num_chain - 1):
                relation = Relation(
                    source_entity_id=entities[i].entity_id,
                    target_entity_id=entities[i+1].entity_id,
                    relation_type="NEXT"
                )
                graph.add_relation(relation)
            
            self.repo.save_graph(graph)
            
            # 分析
            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
            stats = analyzer.calculate_statistics()
            
            path = analyzer.find_shortest_path(entities[0].entity_id, entities[-1].entity_id)
            
            self.repo.delete_graph(graph.graph_id)
            print("   ✅ 通过")
            edge_cases_passed += 1
        except Exception as e:
            self.log_error("deep_chain", e)
            print(f"   ❌ 失败: {e}")
        
        # 5. 特殊字符
        print("\n5. 测试特殊字符...")
        edge_cases_total += 1
        try:
            special_name = "测试图谱！@#￥%……&*（）——+=-[]{}|;':\",./<>?\n\t\\~'"
            graph = KnowledgeGraph(graph_name=special_name, description="包含特殊字符的描述")
            special_entity = Entity(
                entity_name=special_name,
                entity_type="SPECIAL",
                description="包含特殊字符的实体：\n\t\"\\\r\n\0x00"
            )
            graph.add_entity(special_entity)
            self.repo.save_graph(graph)
            retrieved = self.repo.get_graph(graph.graph_id)
            assert retrieved is not None
            self.repo.delete_graph(graph.graph_id)
            print("   ✅ 通过")
            edge_cases_passed += 1
        except Exception as e:
            self.log_error("special_chars", e)
            print(f"   ❌ 失败: {e}")
        
        print()
        print("=" * 80)
        print(f"极端边界测试: {edge_cases_passed}/{edge_cases_total} 通过")
        
        return edge_cases_passed == edge_cases_total

    def cleanup(self):
        """清理"""
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    chaos = ChaosTest()
    
    try:
        # 先运行边界测试
        edge_success = chaos.run_extreme_edge_cases()
        
        # 然后运行混乱场景测试
        chaos_success = chaos.run_chaos_test(num_workers=25, operations_per_worker=300)
        
        # 最终结果
        print("\n" + "=" * 80)
        print("🎯 最终测试总结")
        print("=" * 80)
        print(f"  边界测试: {'✅ 通过' if edge_success else '❌ 失败'}")
        print(f"  混乱场景: {'✅ 通过' if chaos_success else '❌ 失败'}")
        
        if edge_success and chaos_success:
            print("\n🎉 太棒了！所有混乱场景测试都通过了！")
            return 0
        else:
            print("\n⚠️  发现问题，请查看上述错误")
            return 1
            
    finally:
        chaos.cleanup()


if __name__ == "__main__":
    sys.exit(main())
