#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超长时间稳定性和压力测试
遵循慢工出细活原则，细致地测试系统稳定性
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
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph, KnowledgeGraphManager
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class LongTermStabilityTest:
    """长时间稳定性测试"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "long_term_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path, pool_size=10)
        initialize_database(config)
        self.repo = KnowledgeRepository()
        self.errors = []
        self.operations_count = 0
        self.start_time = None
        
    def log_error(self, operation: str, error: Exception, details: Dict = None):
        """记录错误"""
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'error': str(error),
            'details': details or {}
        }
        self.errors.append(error_info)
        print(f"⚠️ 错误: {operation} - {error}")
        
    def test_single_graph_lifecycle(self, graph_index: int) -> bool:
        """测试单个图谱的完整生命周期"""
        try:
            manager = KnowledgeGraphManager()
            
            # 创建图谱
            graph = manager.create_graph(
                f"测试图谱 {graph_index}",
                f"这是第 {graph_index} 个用于稳定性测试的图谱"
            )
            
            # 添加实体
            num_entities = random.randint(20, 100)
            entities = []
            for i in range(num_entities):
                entity = Entity(
                    entity_name=f"实体_{graph_index}_{i}",
                    entity_type=random.choice(['概念', '人物', '地点', '组织', '事件']),
                    description=f"这是第 {i} 个实体，用于稳定性测试",
                    properties={
                        'index': i,
                        'graph': graph_index,
                        'created_at': datetime.now().isoformat()
                    }
                )
                entities.append(entity)
                graph.add_entity(entity)
            
            # 添加关系
            num_relations = random.randint(int(num_entities * 0.5), int(num_entities * 3))
            for i in range(num_relations):
                if len(entities) < 2:
                    break
                src_idx = random.randint(0, len(entities) - 1)
                tgt_idx = random.randint(0, len(entities) - 1)
                
                if tgt_idx == src_idx:
                    tgt_idx = (tgt_idx + 1) % len(entities)
                
                relation = Relation(
                    source_entity_id=entities[src_idx].entity_id,
                    target_entity_id=entities[tgt_idx].entity_id,
                    relation_type=random.choice(['相关', '包含', '属于', '关联', '引用']),
                    weight=random.random()
                )
                graph.add_relation(relation)
            
            # 保存
            save_start = time.time()
            success = self.repo.save_graph(graph)
            save_time = time.time() - save_start
            
            if not success:
                self.log_error("save_graph", Exception("保存失败"), {"graph_id": graph.graph_id})
                return False
            
            # 读取
            read_start = time.time()
            retrieved = self.repo.get_graph(graph.graph_id)
            read_time = time.time() - read_start
            
            if not retrieved:
                self.log_error("get_graph", Exception("读取失败"), {"graph_id": graph.graph_id})
                return False
            
            # 验证数据完整性
            if len(retrieved.entities) != num_entities:
                self.log_error("data_integrity", Exception(f"实体数量不匹配: 期望{num_entities}, 实际{len(retrieved.entities)}"))
            
            # 搜索
            search_keyword = f"实体_{graph_index}_1"
            search_results = self.repo.search_entities(search_keyword, graph.graph_id)
            if not search_results:
                self.log_error("search", Exception(f"搜索失败，关键词: {search_keyword}"))
            
            # 获取统计
            stats = self.repo.get_graph_statistics(graph.graph_id)
            
            # 分析
            analyzer = KnowledgeGraphAnalyzer(retrieved.entities, retrieved.relations)
            analyzer.calculate_statistics()
            analyzer.find_key_entities(10)
            analyzer.detect_communities_bfs()
            
            # 删除
            delete_start = time.time()
            self.repo.delete_graph(graph.graph_id)
            delete_time = time.time() - delete_start
            
            self.operations_count += 1
            if self.operations_count % 50 == 0:
                print(f"⏱️ 已完成 {self.operations_count} 个完整的图谱生命周期测试...")
            
            return True
            
        except Exception as e:
            self.log_error("graph_lifecycle", e)
            return False
    
    def test_mixed_operations(self, num_operations: int = 500):
        """混合操作测试"""
        print(f"\n📊 开始混合操作测试: {num_operations} 次...")
        
        manager = KnowledgeGraphManager()
        active_graphs = []
        
        for i in range(num_operations):
            try:
                # 随机选择操作
                operation_type = random.choice([
                    'create', 'save', 'read', 'search', 'analyze', 'delete'
                ])
                
                if operation_type == 'create' or len(active_graphs) == 0:
                    # 创建新图谱
                    graph = manager.create_graph(
                        f"混合操作图谱 {i}",
                        f"混合操作测试 - 第 {i} 个"
                    )
                    
                    # 随机添加一些实体和关系
                    for j in range(random.randint(5, 30)):
                        entity = Entity(
                            entity_name=f"混合实体_{i}_{j}",
                            entity_type=random.choice(['概念', '人物', '地点'])
                        )
                        graph.add_entity(entity)
                    
                    for j in range(random.randint(3, 20)):
                        if len(graph.entities) >= 2:
                            src = random.choice(graph.entities)
                            tgt = random.choice([e for e in graph.entities if e.entity_id != src.entity_id])
                            graph.add_relation(Relation(
                                source_entity_id=src.entity_id,
                                target_entity_id=tgt.entity_id,
                                relation_type="相关"
                            ))
                    
                    active_graphs.append(graph.graph_id)
                    self.repo.save_graph(graph)
                
                elif operation_type == 'save' and active_graphs:
                    # 保存现有图谱
                    graph_id = random.choice(active_graphs)
                    graph = self.repo.get_graph(graph_id)
                    if graph:
                        # 修改一些内容
                        graph.graph_name = f"修改的图谱 - {datetime.now().isoformat()}"
                        self.repo.save_graph(graph)
                
                elif operation_type == 'read' and active_graphs:
                    # 读取
                    graph_id = random.choice(active_graphs)
                    self.repo.get_graph(graph_id)
                
                elif operation_type == 'search':
                    # 搜索
                    keyword = f"混合实体_{random.randint(0, num_operations)}"
                    self.repo.search_entities(keyword)
                
                elif operation_type == 'analyze' and active_graphs:
                    # 分析
                    graph_id = random.choice(active_graphs)
                    graph = self.repo.get_graph(graph_id)
                    if graph:
                        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
                        analyzer.find_key_entities(5)
                
                elif operation_type == 'delete' and active_graphs and len(active_graphs) > 10:
                    # 删除
                    graph_id = active_graphs.pop(0)
                    self.repo.delete_graph(graph_id)
                
                self.operations_count += 1
                
                if self.operations_count % 100 == 0:
                    print(f"✅ 已完成 {self.operations_count} 次混合操作...")
                
                # 短时间休眠，模拟真实场景
                time.sleep(0.01)
                
            except Exception as e:
                self.log_error("mixed_operations", e, {"operation_index": i})
    
    def test_concurrent_operations(self):
        """并发操作测试"""
        print("\n🔀 开始并发操作测试...")
        
        num_threads = 8
        operations_per_thread = 50
        errors_in_threads = []
        
        def thread_worker(worker_id: int):
            try:
                for i in range(operations_per_thread):
                    # 每个线程独立工作
                    manager = KnowledgeGraphManager()
                    graph = manager.create_graph(
                        f"并发图谱_{worker_id}_{i}",
                        f"线程 {worker_id} 创建的第 {i} 个图谱"
                    )
                    
                    for j in range(10):
                        graph.add_entity(Entity(
                            entity_name=f"并发实体_{worker_id}_{i}_{j}",
                            entity_type="概念"
                        ))
                    
                    self.repo.save_graph(graph)
                    self.repo.get_graph(graph.graph_id)
                    self.repo.delete_graph(graph.graph_id)
                    
                    time.sleep(0.005)
                
            except Exception as e:
                errors_in_threads.append(f"线程 {worker_id}: {str(e)}")
        
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=thread_worker, args=(i,))
            threads.append(t)
        
        print(f"启动 {num_threads} 个线程...")
        start = time.time()
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        elapsed = time.time() - start
        
        if errors_in_threads:
            for err in errors_in_threads:
                self.log_error("concurrent", Exception(err))
        
        print(f"并发测试完成，耗时 {elapsed:.2f} 秒")
    
    def test_memory_stability(self):
        """内存稳定性测试"""
        print("\n💾 开始内存稳定性测试...")
        
        try:
            import psutil
            process = psutil.Process()
            
            gc.collect()
            initial_memory = process.memory_info().rss / 1024 / 1024
            print(f"初始内存: {initial_memory:.2f} MB")
            
            # 执行大量操作，检查内存
            for i in range(200):
                self.test_single_graph_lifecycle(i)
                
                if i % 20 == 0:
                    gc.collect()
                    current_memory = process.memory_info().rss / 1024 / 1024
                    print(f"迭代 {i}: 当前内存 {current_memory:.2f} MB")
            
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024
            
            memory_growth = final_memory - initial_memory
            print(f"内存增长: {memory_growth:.2f} MB")
            
            if memory_growth > 100:
                self.log_error("memory", Exception(f"内存增长过多: {memory_growth:.2f} MB"))
        
        except ImportError:
            print("psutil不可用，跳过内存测试")
    
    def run_all(self):
        """运行所有测试"""
        print("="*80)
        print("⚡ 超长时间稳定性测试")
        print("="*80)
        self.start_time = datetime.now()
        
        print(f"开始时间: {self.start_time.isoformat()}")
        
        # 1. 单个图谱生命周期测试
        print("\n" + "="*80)
        print("1️⃣ 单个图谱生命周期测试")
        print("="*80)
        
        for i in range(100):
            self.test_single_graph_lifecycle(i)
        
        # 2. 混合操作测试
        print("\n" + "="*80)
        print("2️⃣ 混合操作测试")
        print("="*80)
        
        self.test_mixed_operations(num_operations=1000)
        
        # 3. 并发操作测试
        print("\n" + "="*80)
        print("3️⃣ 并发操作测试")
        print("="*80)
        
        self.test_concurrent_operations()
        
        # 4. 内存稳定性测试
        print("\n" + "="*80)
        print("4️⃣ 内存稳定性测试")
        print("="*80)
        
        self.test_memory_stability()
        
        # 总结
        self.print_summary()
        
        return len(self.errors) == 0
    
    def print_summary(self):
        """打印测试总结"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("📊 长时间稳定性测试总结")
        print("="*80)
        print(f"测试时长: {duration:.1f} 秒")
        print(f"总操作数: {self.operations_count}")
        print(f"发现错误: {len(self.errors)}")
        
        if self.errors:
            print("\n⚠️ 错误详情:")
            for idx, error in enumerate(self.errors[:20]):  # 只显示前20个
                print(f"  {idx+1}. [{error['timestamp']}] {error['operation']}: {error['error']}")
            
            if len(self.errors) > 20:
                print(f"  ... 还有 {len(self.errors)-20} 个错误")
        else:
            print("\n🎉 太棒了！没有发现任何错误！")
        
        print("="*80)
    
    def cleanup(self):
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    tester = LongTermStabilityTest()
    try:
        success = tester.run_all()
        return 0 if success else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
