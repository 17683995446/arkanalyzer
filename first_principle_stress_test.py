#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一性原理极限测试 - 深度发现真实问题
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

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class FirstPrincipleStressTest:
    """遵循第一性原理的极限测试"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "fp_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repo = KnowledgeRepository()
        self.issues_found = []
        self.test_results = []
        
    def log_issue(self, severity: str, category: str, description: str, details: Any = None):
        """记录真实问题"""
        issue = {
            'severity': severity,
            'category': category,
            'description': description,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.issues_found.append(issue)
        icon = '🔴' if severity == 'critical' else '🟠' if severity == 'warning' else '🟡'
        print(f"{icon} [{severity}] {category}: {description}")
        
    def log_test(self, name: str, passed: bool, duration: float = 0, details: Any = None):
        self.test_results.append((name, passed, duration, details))
        icon = "✅" if passed else "❌"
        print(f"\n{icon} {name}")
        if details:
            print(f"  详情: {details}")
        if duration > 0:
            print(f"  耗时: {duration:.2f}s")
        
    def test_1_linear_search_performance(self):
        """测试1: 线性搜索性能问题 - O(n) vs O(1)"""
        print("\n" + "="*80)
        print("🔍 测试1: 核心搜索性能问题")
        print("="*80)
        
        test_sizes = [1000, 5000, 10000, 25000, 50000]
        results = []
        
        for num_entities in test_sizes:
            graph = KnowledgeGraph(graph_name=f"SearchTest_{num_entities}")
            
            for i in range(num_entities):
                entity = Entity(
                    entity_name=f"Entity_{i}",
                    entity_type="概念"
                )
                graph.add_entity(entity)
            
            target_id = graph.entities[-1].entity_id
            
            # 测试100次取平均
            start = time.time()
            for _ in range(100):
                graph.get_entity_by_id(target_id)
            avg_time = (time.time() - start) / 100
            
            results.append((num_entities, avg_time))
            print(f"  {num_entities:6}个实体: {avg_time*1000:8.4f}ms/次")
            
            if avg_time > 0.01 and num_entities >= 50000:
                self.log_issue("warning", "性能问题", 
                               f"线性搜索在 {num_entities} 实体时太慢: {avg_time*1000:.2f}ms")
        
        # 验证：时间是否呈线性增长
        if len(results) >= 3:
            ratio = results[-1][1] / results[0][1]
            size_ratio = results[-1][0] / results[0][0]
            if ratio / size_ratio > 0.5:
                self.log_issue("warning", "算法问题", 
                              f"搜索时间随数据量呈线性增长（O(n)）")
        
        return True
        
    def test_2_memory_usage_with_many_entities(self):
        """测试2: 内存占用测试"""
        print("\n" + "="*80)
        print("💾 测试2: 内存占用测试")
        print("="*80)
        
        try:
            import psutil
            process = psutil.Process()
        except:
            print("  psutil不可用，跳过")
            return True
        
        test_sizes = [1000, 5000, 10000, 25000]
        
        for num_entities in test_sizes:
            gc.collect()
            mem_before = process.memory_info().rss / 1024 / 1024
            
            graph = KnowledgeGraph(graph_name=f"MemTest_{num_entities}")
            for i in range(num_entities):
                entity = Entity(entity_name=f"Entity_{i}", entity_type="概念",
                              properties={'index': i, 'data': 'x'*100})
                graph.add_entity(entity)
                
            for i in range(num_entities * 3):
                if len(graph.entities) >= 2:
                    s = random.randint(0, len(graph.entities)-1)
                    t = random.randint(0, len(graph.entities)-1)
                    while t == s:
                        t = random.randint(0, len(graph.entities)-1)
                    graph.add_relation(Relation(
                        source_entity_id=graph.entities[s].entity_id,
                        target_entity_id=graph.entities[t].entity_id,
                        relation_type="相关"
                    ))
            
            gc.collect()
            mem_after = process.memory_info().rss / 1024 / 1024
            
            mem_used = mem_after - mem_before
            per_entity_kb = (mem_used * 1024) / num_entities
            
            print(f"  {num_entities:6}实体: {mem_used:8.2f} MB ({per_entity_kb:.2f}KB/个)")
            
            if per_entity_kb > 2:
                self.log_issue("warning", "内存问题", f"实体内存占用过高: {per_entity_kb:.2f}KB/个")
        
        gc.collect()
        return True
        
    def test_3_neighbors_search_efficiency(self):
        """测试3: 邻居查找效率"""
        print("\n" + "="*80)
        print("🔗 测试3: 邻居查找效率")
        print("="*80)
        
        graph = KnowledgeGraph(graph_name="NeighborsTest")
        num_entities = 5000
        
        for i in range(num_entities):
            graph.add_entity(Entity(entity_name=f"Entity_{i}", entity_type="概念"))
        
        for i in range(1, num_entities):
            graph.add_relation(Relation(
                source_entity_id=graph.entities[0].entity_id,
                target_entity_id=graph.entities[i].entity_id,
                relation_type="相关"
            ))
        
        start = time.time()
        neighbors = graph.get_neighbors(graph.entities[0].entity_id)
        duration = time.time() - start
        
        print(f"  邻居数量: {len(neighbors)}, 耗时: {duration*1000:.4f}ms")
        
        if len(neighbors) != num_entities - 1:
            self.log_issue("critical", "功能问题", 
                          f"邻居数量不对！期望 {num_entities-1}, 实际 {len(neighbors)}")
        
        return len(neighbors) == num_entities - 1
        
    def test_4_extreme_property_sizes(self):
        """测试4: 极端属性大小"""
        print("\n" + "="*80)
        print("🏋️ 测试4: 极端属性大小")
        print("="*80)
        
        test_cases = [
            ("1KB属性", 'x' * 1000),
            ("100KB属性", 'x' * 100000),
            ("1MB属性", 'x' * 1000000),
            ("超大嵌套对象", {'a': {'b': {'c': ['x'*1000 for _ in range(100)]}}})
        ]
        
        all_passed = True
        for name, value in test_cases:
            try:
                start = time.time()
                entity = Entity(entity_name="Test", entity_type="概念",
                              properties={'big': value})
                
                graph = KnowledgeGraph(graph_name="BigPropTest")
                graph.add_entity(entity)
                
                self.repo.save_graph(graph)
                retrieved = self.repo.get_graph(graph.graph_id)
                
                if retrieved and len(retrieved.entities) == 1:
                    self.log_test(f"极端属性 - {name}", True, time.time()-start)
                else:
                    all_passed = False
                    self.log_issue("critical", "数据完整性", f"{name} 保存后未正确恢复")
                    
                self.repo.delete_graph(graph.graph_id)
                
            except Exception as e:
                all_passed = False
                self.log_issue("critical", "异常", f"{name}: {str(e)}")
        
        return all_passed
        
    def test_5_thread_safety_analysis(self):
        """测试5: 图分析器并发安全"""
        print("\n" + "="*80)
        print("🔀 测试5: 图分析器并发安全")
        print("="*80)
        
        graph = KnowledgeGraph(graph_name="ThreadTest")
        entities = []
        
        for i in range(2000):
            entity = Entity(entity_name=f"ThreadTest_{i}", entity_type="概念")
            entities.append(entity)
            graph.add_entity(entity)
        
        for i in range(6000):
            s = random.randint(0, len(entities)-1)
            t = random.randint(0, len(entities)-1)
            while t == s:
                t = random.randint(0, len(entities)-1)
            graph.add_relation(Relation(
                source_entity_id=entities[s].entity_id,
                target_entity_id=entities[t].entity_id,
                relation_type="相关"
            ))
        
        errors = []
        num_threads = 10
        ops_per_thread = 50
        
        def analyze_task(worker_id):
            try:
                for _ in range(ops_per_thread):
                    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
                    analyzer.calculate_statistics()
                    analyzer.find_key_entities(5)
                    analyzer.detect_communities_bfs()
            except Exception as e:
                errors.append(str(e))
        
        print(f"  启动 {num_threads} 个线程进行图分析...")
        start = time.time()
        threads = []
        
        for i in range(num_threads):
            t = threading.Thread(target=analyze_task, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        total_time = time.time() - start
        
        if len(errors) == 0:
            self.log_test("并发图分析安全", True, total_time, 
                        f"{num_threads}线程×{ops_per_thread}次分析")
            return True
        else:
            self.log_issue("critical", "并发安全", f"发现 {len(errors)} 个并发错误")
            return False
        
    def run_all(self):
        print("\n" + "="*80)
        print("⚡ 第一性原理极限测试开始")
        print(f"⏰ 开始时间: {datetime.now().isoformat()}")
        print("="*80)
        
        self.test_1_linear_search_performance()
        self.test_2_memory_usage_with_many_entities()
        self.test_3_neighbors_search_efficiency()
        self.test_4_extreme_property_sizes()
        self.test_5_thread_safety_analysis()
        
        print("\n" + "="*80)
        print("📊 极限测试总结")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed = sum(1 for name, success, _, _ in self.test_results if success)
        
        print(f"\n  总测试: {total_tests}")
        print(f"  通过: {passed}")
        print(f"  发现问题: {len(self.issues_found)}")
        
        if self.issues_found:
            print(f"\n🟡 发现的问题:")
            for issue in self.issues_found:
                print(f"  [{issue['severity']}] {issue['category']}: {issue['description']}")
        
        print("="*80)
        
        return len(self.issues_found) == 0
        
    def cleanup(self):
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    tester = FirstPrincipleStressTest()
    try:
        result = tester.run_all()
        return 0 if result else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
