#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速问题发现测试
专注于发现关键性能瓶颈和潜在bug
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import random
import threading
import gc
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from arkanalyzer.core.knowledge_graph_core import (
    Entity, Relation, KnowledgeGraph,
    EntityType, RelationType
)
from arkanalyzer.core.knowledge_repository import KnowledgeRepository
from arkanalyzer.database.database_connection_manager import initialize_database


class QuickIssueDiscovery:
    """快速问题发现"""
    
    def __init__(self):
        self.issues = []
        initialize_database()
        self.repo = KnowledgeRepository()
    
    def log_issue(self, severity: str, issue_type: str, description: str, details: Any = None):
        """记录问题"""
        issue = {
            'severity': severity,
            'type': issue_type,
            'description': description,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.issues.append(issue)
        
        symbol = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }.get(severity, '⚪')
        
        print(f"{symbol} [{severity}] {issue_type}: {description}")
        if details:
            print(f"    详情: {details}")
    
    def test_database_lock_performance(self):
        """测试数据库锁定性能"""
        print("\n" + "="*80)
        print("📊 测试1: 数据库锁定性能")
        print("="*80)
        
        lock_errors = []
        total_operations = 0
        
        def intensive_writes(thread_id: int):
            nonlocal total_operations
            for i in range(30):
                try:
                    start = time.time()
                    
                    graph = KnowledgeGraph(graph_name=f"lock_test_{thread_id}_{i}")
                    for j in range(20):
                        entity = Entity(
                            entity_name=f"entity_{thread_id}_{i}_{j}",
                            entity_type=EntityType.CONCEPT.value
                        )
                        graph.add_entity(entity)
                    
                    self.repo.save_graph(graph)
                    
                    elapsed = time.time() - start
                    total_operations += 1
                    
                    if elapsed > 1.0:  # 单次操作超过1秒
                        self.log_issue(
                            'MEDIUM',
                            '写入延迟',
                            f"单次写入耗时 {elapsed:.2f}秒",
                            f"Thread-{thread_id}, Graph-{i}"
                        )
                        
                except Exception as e:
                    error_str = str(e).lower()
                    if 'locked' in error_str:
                        lock_errors.append(str(e))
        
        print("\n运行30个并发线程的密集写入测试...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(intensive_writes, i) for i in range(30)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    lock_errors.append(str(e))
        
        elapsed = time.time() - start_time
        
        print(f"\n📈 结果:")
        print(f"  - 总操作数: {total_operations}")
        print(f"  - 总耗时: {elapsed:.2f}秒")
        print(f"  - 操作/秒: {total_operations / elapsed:.2f}")
        print(f"  - 锁定错误数: {len(lock_errors)}")
        
        if lock_errors:
            self.log_issue(
                'HIGH',
                '数据库锁定',
                f"高并发写入产生 {len(lock_errors)} 个锁定错误",
                f"锁定率: {len(lock_errors) / total_operations * 100:.1f}%"
            )
            
            # 分析锁定模式
            unique_errors = set(lock_errors[:10])
            for error in unique_errors:
                self.log_issue('LOW', '锁定详情', error)
        
        # 清理
        print("\n清理测试数据...")
        try:
            graphs = self.repo.get_all_graphs()
            for graph in graphs:
                if graph.graph_name.startswith('lock_test_'):
                    self.repo.delete_graph(graph.graph_id)
        except:
            pass
    
    def test_memory_under_load(self):
        """测试负载下的内存使用"""
        print("\n" + "="*80)
        print("📊 测试2: 内存使用测试")
        print("="*80)
        
        import tracemalloc
        tracemalloc.start()
        
        # 测试大量数据加载
        print("\n创建包含5000个实体和25000个关系的图谱...")
        test_graph = KnowledgeGraph(graph_name="memory_test")
        
        for i in range(5000):
            entity = Entity(
                entity_name=f"mem_entity_{i}",
                entity_type=EntityType.CONCEPT.value,
                properties={
                    'data': 'x' * 100,
                    'index': i
                }
            )
            test_graph.add_entity(entity)
        
        for i in range(25000):
            src_idx = random.randint(0, 4999)
            tgt_idx = random.randint(0, 4999)
            
            if src_idx != tgt_idx:
                relation = Relation(
                    source_entity_id=test_graph.entities[src_idx].entity_id,
                    target_entity_id=test_graph.entities[tgt_idx].entity_id,
                    relation_type=RelationType.RELATED_TO.value,
                    properties={'index': i}
                )
                test_graph.add_relation(relation)
        
        # 保存
        print("保存到数据库...")
        self.repo.save_graph(test_graph)
        
        # 加载并测量
        print("从数据库加载...")
        current1, peak1 = tracemalloc.get_traced_memory()
        
        loaded_graph = self.repo.get_graph(test_graph.graph_id)
        
        current2, peak2 = tracemalloc.get_traced_memory()
        
        print(f"\n📈 内存使用:")
        print(f"  - 保存前峰值: {peak1 / 1024 / 1024:.2f} MB")
        print(f"  - 加载后峰值: {peak2 / 1024 / 1024:.2f} MB")
        print(f"  - 内存增长: {(peak2 - peak1) / 1024 / 1024:.2f} MB")
        
        if peak2 > 100:  # 超过100MB
            self.log_issue(
                'MEDIUM',
                '内存使用过高',
                f"加载5000实体+25000关系消耗 {peak2 / 1024 / 1024:.2f} MB内存",
                '考虑优化内存使用或增加分页加载'
            )
        
        # 多次加载测试
        print("\n多次加载测试...")
        load_times = []
        for i in range(10):
            start = time.time()
            loaded = self.repo.get_graph(test_graph.graph_id)
            elapsed = time.time() - start
            load_times.append(elapsed)
        
        avg_load_time = sum(load_times) / len(load_times)
        max_load_time = max(load_times)
        
        print(f"\n📈 加载性能:")
        print(f"  - 平均加载时间: {avg_load_time * 1000:.2f} ms")
        print(f"  - 最大加载时间: {max_load_time * 1000:.2f} ms")
        
        if avg_load_time > 0.5:  # 超过500ms
            self.log_issue(
                'MEDIUM',
                '加载性能慢',
                f"平均加载时间 {avg_load_time * 1000:.2f} ms",
                '考虑添加缓存或分页加载'
            )
        
        # 清理
        self.repo.delete_graph(test_graph.graph_id)
        tracemalloc.stop()
    
    def test_search_performance(self):
        """测试搜索性能"""
        print("\n" + "="*80)
        print("📊 测试3: 搜索性能测试")
        print("="*80)
        
        # 创建测试数据
        print("\n创建测试数据...")
        test_graph = KnowledgeGraph(graph_name="search_test")
        
        for i in range(2000):
            entity = Entity(
                entity_name=f"search_entity_{i}",
                entity_type=EntityType.CONCEPT.value,
                properties={'index': i}
            )
            test_graph.add_entity(entity)
        
        self.repo.save_graph(test_graph)
        
        # 搜索性能测试
        print("\n执行1000次搜索...")
        search_times = []
        
        for i in range(1000):
            keyword = f"search_entity_{random.randint(0, 1999)}"
            start = time.time()
            results = self.repo.search_entities(keyword)
            elapsed = time.time() - start
            search_times.append(elapsed)
        
        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)
        p95_search_time = sorted(search_times)[int(len(search_times) * 0.95)]
        
        print(f"\n📈 搜索性能:")
        print(f"  - 平均搜索时间: {avg_search_time * 1000:.2f} ms")
        print(f"  - P95搜索时间: {p95_search_time * 1000:.2f} ms")
        print(f"  - 最大搜索时间: {max_search_time * 1000:.2f} ms")
        
        if avg_search_time > 0.1:  # 超过100ms
            self.log_issue(
                'MEDIUM',
                '搜索性能慢',
                f"平均搜索时间 {avg_search_time * 1000:.2f} ms",
                '考虑添加搜索索引或使用全文搜索'
            )
        
        # 清理
        self.repo.delete_graph(test_graph.graph_id)
    
    def test_concurrent_read_consistency(self):
        """测试并发读取一致性"""
        print("\n" + "="*80)
        print("📊 测试4: 并发读取一致性测试")
        print("="*80)
        
        # 创建测试数据
        test_graph = KnowledgeGraph(graph_name="consistency_test")
        for i in range(100):
            entity = Entity(
                entity_name=f"consistency_entity_{i}",
                entity_type=EntityType.PERSON.value,
                properties={'value': i}
            )
            test_graph.add_entity(entity)
        
        self.repo.save_graph(test_graph)
        
        # 并发读取
        inconsistencies = []
        
        def concurrent_read(thread_id: int):
            for i in range(50):
                try:
                    graph = self.repo.get_graph(test_graph.graph_id)
                    if graph:
                        entity_count = len(graph.entities)
                        if entity_count != 100:
                            inconsistencies.append(
                                f"Thread-{thread_id}: 实体数量不一致: {entity_count} != 100"
                            )
                except Exception as e:
                    inconsistencies.append(f"Thread-{thread_id}: {str(e)}")
        
        print("\n启动20个线程进行并发读取...")
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(concurrent_read, i) for i in range(20)]
            for future in as_completed(futures):
                try:
                    future.result()
                except:
                    pass
        
        print(f"\n📈 结果:")
        print(f"  - 总读取次数: 1000")
        print(f"  - 不一致次数: {len(inconsistencies)}")
        
        if inconsistencies:
            self.log_issue(
                'HIGH',
                '并发一致性问题',
                f"并发读取发现 {len(inconsistencies)} 个不一致",
                inconsistencies[0] if inconsistencies else None
            )
        else:
            print("  ✅ 并发读取一致性良好")
        
        # 清理
        self.repo.delete_graph(test_graph.graph_id)
    
    def test_connection_pool_efficiency(self):
        """测试连接池效率"""
        print("\n" + "="*80)
        print("📊 测试5: 连接池效率测试")
        print("="*80)
        
        pool = self.repo.pool
        initial_pool_size = 0
        
        try:
            initial_pool_size = pool._init_connection_count
            print(f"\n初始连接数: {initial_pool_size}")
            
            # 快速创建和关闭连接
            print("\n执行100次快速连接操作...")
            connection_times = []
            
            for i in range(100):
                start = time.time()
                conn = pool.get_connection()
                elapsed = time.time() - start
                connection_times.append(elapsed)
                pool.return_connection(conn)
            
            avg_conn_time = sum(connection_times) / len(connection_times)
            print(f"平均连接获取时间: {avg_conn_time * 1000:.2f} ms")
            
            final_pool_size = pool._init_connection_count
            print(f"最终连接数: {final_pool_size}")
            
            if final_pool_size > initial_pool_size * 2:
                self.log_issue(
                    'LOW',
                    '连接池扩展',
                    f"连接池从 {initial_pool_size} 扩展到 {final_pool_size}",
                    '连接池根据负载自动扩展'
                )
                
        except Exception as e:
            self.log_issue('HIGH', '连接池测试失败', str(e))
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*80)
        print("⚡ Quick Issue Discovery - 快速问题发现测试")
        print("="*80)
        
        start_time = time.time()
        
        # 运行所有测试
        self.test_database_lock_performance()
        gc.collect()
        
        self.test_memory_under_load()
        gc.collect()
        
        self.test_search_performance()
        gc.collect()
        
        self.test_concurrent_read_consistency()
        gc.collect()
        
        self.test_connection_pool_efficiency()
        
        elapsed = time.time() - start_time
        
        # 生成报告
        print("\n" + "="*80)
        print("📊 问题发现报告")
        print("="*80)
        
        print(f"\n⏱️  测试耗时: {elapsed:.2f} 秒")
        
        # 分类统计
        by_severity = {}
        for issue in self.issues:
            severity = issue['severity']
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        print(f"\n🐛 问题统计:")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = by_severity.get(severity, 0)
            if count > 0:
                print(f"  - {severity}: {count}")
        
        if self.issues:
            print(f"\n📋 问题详情:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n  {i}. [{issue['severity']}] {issue['type']}")
                print(f"     {issue['description']}")
                if issue['details']:
                    print(f"     详情: {issue['details']}")
        
        print("\n" + "="*80)
        
        critical_count = by_severity.get('CRITICAL', 0) + by_severity.get('HIGH', 0)
        
        if critical_count > 0:
            print("❌ 发现严重问题，系统需要修复")
            return 1
        elif len(self.issues) > 0:
            print("⚠️  发现一些中等优先级问题，建议优化")
            return 2
        else:
            print("✅ 测试通过，系统表现良好")
            return 0


def main():
    """主函数"""
    tester = QuickIssueDiscovery()
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
