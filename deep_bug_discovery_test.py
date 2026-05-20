#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深入Bug发现测试脚本
目标：发现系统在极端情况下的bug和性能问题
包括：
- 边界条件测试
- 并发冲突测试
- 内存泄漏检测
- 数据库锁定深度测试
- 超大属性数据测试
- 索引失效场景
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import random
import threading
import gc
import tracemalloc
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref

from arkanalyzer.core.knowledge_graph_core import (
    Entity, Relation, KnowledgeGraph, KnowledgeGraphManager,
    EntityType, RelationType
)
from arkanalyzer.core.knowledge_repository import KnowledgeRepository
from arkanalyzer.database.database_connection_manager import initialize_database


class BugDiscoveryMetrics:
    """Bug发现测试指标"""
    
    def __init__(self):
        self.bugs_found = []
        self.warnings = []
        self.performance_issues = []
        self.memory_leaks = []
        self.deadlocks = []
        self._lock = threading.Lock()
    
    def record_bug(self, bug_type: str, description: str, severity: str, location: str):
        """记录发现的bug"""
        with self._lock:
            self.bugs_found.append({
                'type': bug_type,
                'description': description,
                'severity': severity,
                'location': location,
                'timestamp': datetime.now().isoformat()
            })
            print(f"🐛 [BUG-{severity}] {bug_type}: {description}")
            print(f"   位置: {location}")
    
    def record_warning(self, warning_type: str, description: str):
        """记录警告"""
        with self._lock:
            self.warnings.append({
                'type': warning_type,
                'description': description,
                'timestamp': datetime.now().isoformat()
            })
            print(f"⚠️  [警告] {warning_type}: {description}")
    
    def record_performance_issue(self, issue_type: str, description: str, metric: float):
        """记录性能问题"""
        with self._lock:
            self.performance_issues.append({
                'type': issue_type,
                'description': description,
                'metric': metric,
                'timestamp': datetime.now().isoformat()
            })
            print(f"📉 [性能问题] {issue_type}: {description} (指标: {metric})")
    
    def record_memory_leak(self, leak_type: str, description: str, memory_mb: float):
        """记录内存泄漏"""
        with self._lock:
            self.memory_leaks.append({
                'type': leak_type,
                'description': description,
                'memory_mb': memory_mb,
                'timestamp': datetime.now().isoformat()
            })
            print(f"💾 [内存泄漏] {leak_type}: {description} (泄漏: {memory_mb:.2f} MB)")
    
    def get_report(self) -> Dict[str, Any]:
        """获取完整报告"""
        return {
            'bugs': self.bugs_found,
            'warnings': self.warnings,
            'performance_issues': self.performance_issues,
            'memory_leaks': self.memory_leaks,
            'total_bugs': len(self.bugs_found),
            'critical_bugs': len([b for b in self.bugs_found if b['severity'] == 'CRITICAL']),
            'total_warnings': len(self.warnings),
            'total_performance_issues': len(self.performance_issues),
            'total_memory_leaks': len(self.memory_leaks)
        }


class DeepBugDiscoveryTest:
    """深度Bug发现测试"""
    
    def __init__(self):
        self.metrics = BugDiscoveryMetrics()
        self.errors = []
        initialize_database()
        self.repo = KnowledgeRepository()
        
    def test_boundary_conditions(self):
        """测试边界条件"""
        print("\n" + "="*80)
        print("🔬 测试1: 边界条件测试")
        print("="*80)
        
        # 测试空数据
        print("\n1.1 测试空数据...")
        try:
            empty_graph = KnowledgeGraph(graph_name="empty_test")
            self.repo.save_graph(empty_graph)
            retrieved = self.repo.get_graph(empty_graph.graph_id)
            
            if retrieved and len(retrieved.entities) == 0:
                print("  ✅ 空图谱创建和检索正常")
            else:
                self.metrics.record_bug("空数据处理", "空图谱数据异常", "LOW", "KnowledgeRepository")
        except Exception as e:
            self.metrics.record_bug("空数据异常", str(e), "HIGH", "KnowledgeRepository.save_graph")
        
        # 测试超长名称
        print("\n1.2 测试超长名称...")
        try:
            long_name = "x" * 10000
            long_graph = KnowledgeGraph(graph_name=long_name, description="超长名称测试")
            self.repo.save_graph(long_graph)
            
            # 检查数据库是否正确处理
            retrieved = self.repo.get_graph(long_graph.graph_id)
            if retrieved and len(retrieved.graph_name) == 10000:
                print("  ✅ 超长名称处理正常")
            else:
                self.metrics.record_warning("超长名称", f"名称可能被截断: {len(retrieved.graph_name) if retrieved else 'None'}")
        except Exception as e:
            self.metrics.record_bug("超长名称异常", str(e), "MEDIUM", "KnowledgeGraph")
        
        # 测试特殊字符
        print("\n1.3 测试特殊字符...")
        try:
            special_names = ["emoji_🎉_test", "中文_测试", "空白\t\n", "NULL\x00value", "SQL'INJECTION"]
            for name in special_names:
                try:
                    graph = KnowledgeGraph(graph_name=name)
                    self.repo.save_graph(graph)
                    retrieved = self.repo.get_graph(graph.graph_id)
                    if not retrieved or retrieved.graph_name != name:
                        self.metrics.record_bug("特殊字符处理", f"名称 '{name}' 未正确保存/检索", "MEDIUM", "KnowledgeGraph")
                except Exception as e:
                    self.metrics.record_bug("特殊字符异常", f"名称 '{name}': {str(e)}", "HIGH", "Entity/Relation")
        except Exception as e:
            self.metrics.record_bug("特殊字符批量测试异常", str(e), "MEDIUM", "KnowledgeRepository")
        
        # 测试超大属性数据
        print("\n1.4 测试超大属性数据...")
        try:
            huge_entity = Entity(
                entity_name="huge_properties_test",
                entity_type=EntityType.CONCEPT.value,
                properties={
                    'large_data': 'x' * 1_000_000,  # 1MB数据
                    'nested': {'level1': {'level2': {'level3': 'x' * 10000}}}
                }
            )
            
            graph = KnowledgeGraph(graph_name="huge_props_test")
            graph.add_entity(huge_entity)
            self.repo.save_graph(graph)
            
            retrieved = self.repo.get_graph(graph.graph_id)
            if retrieved and retrieved.entities:
                retrieved_entity = retrieved.entities[0]
                if 'large_data' in retrieved_entity.properties:
                    if len(retrieved_entity.properties['large_data']) == 1_000_000:
                        print("  ✅ 超大属性数据处理正常")
                    else:
                        self.metrics.record_warning("超大属性", f"数据长度不匹配: {len(retrieved_entity.properties.get('large_data', ''))}")
                else:
                    self.metrics.record_bug("属性丢失", "超大属性数据丢失", "HIGH", "KnowledgeRepository")
        except Exception as e:
            self.metrics.record_bug("超大属性异常", str(e), "HIGH", "KnowledgeRepository")
        
        # 清理
        self.repo.delete_graph(graph.graph_id)
        self.repo.delete_graph(long_graph.graph_id)
    
    def test_concurrent_modification_bugs(self):
        """测试并发修改bug"""
        print("\n" + "="*80)
        print("🔬 测试2: 并发修改冲突测试")
        print("="*80)
        
        # 创建测试图谱
        test_graph = KnowledgeGraph(graph_name="concurrent_test")
        test_entity = Entity(
            entity_name="concurrent_entity",
            entity_type=EntityType.PERSON.value,
            properties={'value': 0}
        )
        test_graph.add_entity(test_entity)
        self.repo.save_graph(test_graph)
        
        errors = []
        update_times = []
        
        def concurrent_update(thread_id: int):
            """并发更新操作"""
            try:
                for i in range(10):
                    start = time.time()
                    
                    # 读取-修改-写入
                    graph = self.repo.get_graph(test_graph.graph_id)
                    if graph and graph.entities:
                        graph.entities[0].properties['value'] = thread_id * 100 + i
                        graph.entities[0].updated_at = datetime.now()
                        self.repo.save_graph(graph)
                    
                    elapsed = time.time() - start
                    update_times.append(elapsed)
                    
            except Exception as e:
                errors.append(f"Thread-{thread_id}: {str(e)}")
        
        print("\n2.1 测试并发读写冲突...")
        threads = []
        for i in range(20):
            t = threading.Thread(target=concurrent_update, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        if errors:
            self.metrics.record_bug("并发冲突", f"发现 {len(errors)} 个并发错误", "HIGH", "KnowledgeRepository")
            for error in errors[:5]:
                print(f"   {error}")
        
        # 检查最终数据一致性
        final_graph = self.repo.get_graph(test_graph.graph_id)
        if final_graph and final_graph.entities:
            final_value = final_graph.entities[0].properties.get('value')
            print(f"  最终值: {final_value} (预期: 0-999)")
        
        # 测试索引失效
        print("\n2.2 测试索引失效场景...")
        try:
            # 大量添加后直接查询
            large_graph = KnowledgeGraph(graph_name="index_test")
            for i in range(5000):
                entity = Entity(
                    entity_name=f"index_test_{i}",
                    entity_type=EntityType.CONCEPT.value,
                    properties={'index': i}
                )
                large_graph.add_entity(entity)
            
            self.repo.save_graph(large_graph)
            
            # 测试查找性能
            start = time.time()
            for i in range(100):
                search_name = f"index_test_{random.randint(0, 4999)}"
                results = self.repo.search_entities(search_name)
            search_time = time.time() - start
            
            if search_time > 1.0:  # 100次搜索超过1秒
                self.metrics.record_performance_issue("搜索性能", f"100次搜索耗时 {search_time:.2f}秒", search_time)
            else:
                print(f"  ✅ 搜索性能正常: {search_time:.2f}秒")
            
            self.repo.delete_graph(large_graph.graph_id)
        except Exception as e:
            self.metrics.record_bug("索引测试异常", str(e), "MEDIUM", "search_entities")
    
    def test_memory_leak_detection(self):
        """测试内存泄漏"""
        print("\n" + "="*80)
        print("🔬 测试3: 内存泄漏检测")
        print("="*80)
        
        tracemalloc.start()
        
        # 测试1: 频繁创建删除图谱
        print("\n3.1 测试图谱创建/删除内存泄漏...")
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        for i in range(100):
            graph = KnowledgeGraph(graph_name=f"mem_test_{i}")
            for j in range(100):
                entity = Entity(
                    entity_name=f"entity_{j}",
                    entity_type=EntityType.CONCEPT.value
                )
                graph.add_entity(entity)
            
            self.repo.save_graph(graph)
            self.repo.delete_graph(graph.graph_id)
            
            if i % 20 == 0:
                gc.collect()
        
        gc.collect()
        final_memory = tracemalloc.get_traced_memory()[0]
        memory_growth = (final_memory - initial_memory) / 1024 / 1024
        
        if memory_growth > 10:  # 增长超过10MB
            self.metrics.record_memory_leak(
                "图谱生命周期",
                f"100次创建/删除后内存增长 {memory_growth:.2f} MB",
                memory_growth
            )
        else:
            print(f"  ✅ 图谱生命周期内存正常: 增长 {memory_growth:.2f} MB")
        
        # 测试2: 大对象引用泄漏
        print("\n3.2 测试对象引用泄漏...")
        initial_count = len(gc.get_objects())
        
        test_graph = KnowledgeGraph(graph_name="ref_test")
        entity = Entity(entity_name="ref_entity", entity_type=EntityType.PERSON.value)
        test_graph.add_entity(entity)
        
        weak_ref = weakref.ref(test_graph)
        del test_graph
        
        gc.collect()
        
        if weak_ref() is not None:
            self.metrics.record_memory_leak(
                "对象引用",
                "图谱对象未被正确释放",
                0
            )
        else:
            print("  ✅ 对象引用正常释放")
        
        final_count = len(gc.get_objects())
        object_growth = final_count - initial_count
        
        if object_growth > 1000:
            self.metrics.record_memory_leak(
                "对象累积",
                f"对象数量增长 {object_growth}",
                0
            )
        
        # 测试3: 数据库连接泄漏
        print("\n3.3 测试数据库连接泄漏...")
        initial_connections = len(self.repo.pool._pool.queue) if hasattr(self.repo.pool, '_pool') else 0
        
        for i in range(50):
            graph = self.repo.get_graph("concurrent_test")
            if graph:
                pass  # 只读取
        
        gc.collect()
        final_connections = len(self.repo.pool._pool.queue) if hasattr(self.repo.pool, '_pool') else 0
        
        if final_connections < initial_connections:
            self.metrics.record_warning("连接池", f"连接未正确归还: {initial_connections} -> {final_connections}")
        else:
            print(f"  ✅ 连接池管理正常")
        
        tracemalloc.stop()
    
    def test_database_locking_deep(self):
        """深度测试数据库锁定"""
        print("\n" + "="*80)
        print("🔬 测试4: 数据库锁定深度测试")
        print("="*80)
        
        lock_errors = []
        timeout_count = 0
        
        def intensive_write(thread_id: int):
            """密集写入操作"""
            for i in range(20):
                try:
                    graph = KnowledgeGraph(graph_name=f"lock_test_{thread_id}_{i}")
                    entity = Entity(
                        entity_name=f"entity_{thread_id}_{i}",
                        entity_type=EntityType.CONCEPT.value,
                        properties={'thread': thread_id, 'iteration': i}
                    )
                    graph.add_entity(entity)
                    
                    start = time.time()
                    self.repo.save_graph(graph)
                    
                    # 不删除，让数据库积累数据
                    
                except Exception as e:
                    error_str = str(e).lower()
                    if 'locked' in error_str or 'timeout' in error_str:
                        lock_errors.append(f"Thread-{thread_id}: {str(e)}")
        
        print("\n4.1 测试密集写入锁定...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(intensive_write, i) for i in range(30)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    lock_errors.append(f"Future错误: {str(e)}")
        
        elapsed = time.time() - start_time
        
        if len(lock_errors) > 10:
            self.metrics.record_bug(
                "数据库锁定",
                f"30个线程密集写入产生 {len(lock_errors)} 个锁定错误",
                "HIGH",
                "DatabaseConnectionPool"
            )
            print(f"  ⚠️  锁定错误率: {len(lock_errors) / 600 * 100:.1f}%")
        else:
            print(f"  ✅ 数据库锁定处理正常: {elapsed:.2f}秒, {len(lock_errors)} 个锁定错误")
        
        # 清理测试数据
        print("\n4.2 清理测试数据...")
        try:
            graphs = self.repo.get_all_graphs()
            for graph in graphs:
                if graph.graph_name.startswith('lock_test_') or graph.graph_name.startswith('concurrent_test'):
                    self.repo.delete_graph(graph.graph_id)
        except Exception as e:
            print(f"  清理失败: {e}")
    
    def test_index_corruption(self):
        """测试索引损坏场景"""
        print("\n" + "="*80)
        print("🔬 测试5: 索引和数据一致性测试")
        print("="*80)
        
        # 创建测试数据
        print("\n5.1 测试索引一致性...")
        test_graph = KnowledgeGraph(graph_name="consistency_test")
        
        for i in range(1000):
            entity = Entity(
                entity_name=f"consistency_entity_{i}",
                entity_type=EntityType.CONCEPT.value,
                properties={'index': i}
            )
            test_graph.add_entity(entity)
        
        self.repo.save_graph(test_graph)
        
        # 验证实体数量
        retrieved = self.repo.get_graph(test_graph.graph_id)
        if retrieved:
            if len(retrieved.entities) != 1000:
                self.metrics.record_bug(
                    "索引不一致",
                    f"实体数量不匹配: 期望1000, 实际{len(retrieved.entities)}",
                    "HIGH",
                    "KnowledgeRepository"
                )
            else:
                print("  ✅ 实体数量一致")
            
            # 验证实体索引
            indices = [e.properties.get('index') for e in retrieved.entities]
            if len(indices) != len(set(indices)):
                self.metrics.record_bug(
                    "数据重复",
                    "发现重复的实体索引",
                    "MEDIUM",
                    "KnowledgeGraph"
                )
            else:
                print("  ✅ 实体唯一性一致")
        
        # 测试关系完整性
        print("\n5.2 测试关系完整性...")
        test_graph2 = KnowledgeGraph(graph_name="relation_test")
        
        entities = []
        for i in range(100):
            entity = Entity(
                entity_name=f"rel_entity_{i}",
                entity_type=EntityType.PERSON.value
            )
            test_graph2.add_entity(entity)
            entities.append(entity)
        
        # 创建环形关系
        for i in range(100):
            relation = Relation(
                source_entity_id=entities[i].entity_id,
                target_entity_id=entities[(i + 1) % 100].entity_id,
                relation_type=RelationType.RELATED_TO.value
            )
            test_graph2.add_relation(relation)
        
        self.repo.save_graph(test_graph2)
        
        retrieved2 = self.repo.get_graph(test_graph2.graph_id)
        if retrieved2:
            if len(retrieved2.relations) != 100:
                self.metrics.record_bug(
                    "关系丢失",
                    f"关系数量不匹配: 期望100, 实际{len(retrieved2.relations)}",
                    "MEDIUM",
                    "KnowledgeRepository"
                )
            else:
                print("  ✅ 关系完整性正常")
        
        # 清理
        self.repo.delete_graph(test_graph.graph_id)
        self.repo.delete_graph(test_graph2.graph_id)
    
    def test_race_conditions(self):
        """测试竞态条件"""
        print("\n" + "="*80)
        print("🔬 测试6: 竞态条件测试")
        print("="*80)
        
        race_detected = []
        
        def rapid_toggle(thread_id: int):
            """快速切换操作"""
            graph = KnowledgeGraph(graph_name=f"race_test_{thread_id}")
            entity = Entity(
                entity_name=f"race_entity_{thread_id}",
                entity_type=EntityType.CONCEPT.value,
                properties={'thread': thread_id, 'value': 0}
            )
            graph.add_entity(entity)
            
            try:
                for i in range(50):
                    # 读取
                    retrieved = self.repo.get_graph(graph.graph_id)
                    if retrieved and retrieved.entities:
                        # 修改
                        retrieved.entities[0].properties['value'] = i
                        # 写回
                        self.repo.save_graph(retrieved)
                        
            except Exception as e:
                race_detected.append(f"Thread-{thread_id}: {str(e)}")
        
        print("\n6.1 测试并发读写竞态...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(rapid_toggle, i) for i in range(10)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    race_detected.append(f"Future: {str(e)}")
        
        if race_detected:
            self.metrics.record_bug(
                "竞态条件",
                f"检测到 {len(race_detected)} 个竞态相关错误",
                "MEDIUM",
                "KnowledgeRepository"
            )
        else:
            print("  ✅ 未检测到明显竞态条件")
        
        # 清理
        for i in range(10):
            try:
                self.repo.delete_graph(f"race_test_{i}")
            except:
                pass
    
    def run_all_tests(self):
        """运行所有测试"""
        print("="*80)
        print("🔍 Deep Bug Discovery Test - 深度Bug发现测试")
        print("="*80)
        
        start_time = time.time()
        
        # 执行所有测试
        self.test_boundary_conditions()
        self.test_concurrent_modification_bugs()
        self.test_memory_leak_detection()
        self.test_database_locking_deep()
        self.test_index_corruption()
        self.test_race_conditions()
        
        elapsed = time.time() - start_time
        
        # 生成报告
        print("\n" + "="*80)
        print("📊 Bug发现测试报告")
        print("="*80)
        
        report = self.metrics.get_report()
        
        print(f"\n⏱️  测试耗时: {elapsed:.2f} 秒")
        
        print(f"\n🐛 发现的问题:")
        print(f"  - 严重Bug: {report['critical_bugs']}")
        print(f"  - 总Bug数: {report['total_bugs']}")
        print(f"  - 警告数: {report['total_warnings']}")
        print(f"  - 性能问题: {report['total_performance_issues']}")
        print(f"  - 内存泄漏: {report['total_memory_leaks']}")
        
        if report['bugs']:
            print(f"\n🔴 严重Bug详情:")
            for bug in report['bugs']:
                if bug['severity'] == 'CRITICAL' or bug['severity'] == 'HIGH':
                    print(f"  - [{bug['severity']}] {bug['type']}: {bug['description']}")
                    print(f"    位置: {bug['location']}")
        
        if report['warnings']:
            print(f"\n⚠️  警告详情:")
            for warning in report['warnings'][:5]:
                print(f"  - {warning['type']}: {warning['description']}")
        
        if report['performance_issues']:
            print(f"\n📉 性能问题详情:")
            for issue in report['performance_issues']:
                print(f"  - {issue['type']}: {issue['description']} (指标: {issue['metric']})")
        
        if report['memory_leaks']:
            print(f"\n💾 内存泄漏详情:")
            for leak in report['memory_leaks']:
                print(f"  - {leak['type']}: {leak['description']}")
        
        print("\n" + "="*80)
        
        if report['critical_bugs'] > 0 or report['total_bugs'] > 5:
            print("❌ 测试发现严重问题，系统需要修复")
            return 1
        elif report['total_bugs'] > 0 or report['total_warnings'] > 0:
            print("⚠️  测试发现一些问题，建议优化")
            return 2
        else:
            print("✅ 测试通过，系统表现良好")
            return 0


def main():
    """主函数"""
    test = DeepBugDiscoveryTest()
    return test.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
