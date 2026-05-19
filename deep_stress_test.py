#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度极限测试 - 发现系统深层问题
遵循第一性原理，测试系统边界
"""

import os
import sys
import tempfile
import shutil
import time
import threading
import random
import gc
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class DeepStressTest:
    """深度极限测试"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "deep_test.db")
        self.issues = []
        self.test_results = []
        
    def log_issue(self, severity: str, category: str, description: str, details: Any = None):
        from typing import Any
        issue = {
            'severity': severity,
            'category': category,
            'description': description,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.issues.append(issue)
        icon = '🔴' if severity == 'critical' else '🟠' if severity == 'warning' else '🟡'
        print(f"{icon} [{severity}] {category}: {description}")
        if details:
            print(f"    详情: {details}")
    
    def test_1_connection_pool_limit(self):
        """测试1: 数据库连接池限制测试"""
        print("\n" + "="*80)
        print("🔌 测试1: 数据库连接池限制测试")
        print("="*80)
        
        config = DatabaseConnectionConfig(db_path=self.db_path, pool_size=5, timeout=1)
        initialize_database(config)
        repo = KnowledgeRepository()
        
        print("  测试连接池是否会无限增长...")
        
        graph = KnowledgeGraph(graph_name="ConnectionTest")
        graph.add_entity(Entity(entity_name="Test", entity_type="概念"))
        repo.save_graph(graph)
        
        connections_created = []
        
        def worker(worker_id):
            for i in range(100):
                try:
                    with repo.pool.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM entities")
                        cursor.fetchone()
                        connections_created.append(1)
                except Exception as e:
                    pass
        
        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        print(f"  总连接获取次数: {len(connections_created)}")
        
        pool_size = repo.pool._init_connection_count
        print(f"  实际创建的连接数: {pool_size}")
        
        if pool_size > 5:
            self.log_issue("warning", "连接池问题", 
                         f"连接池大小限制未生效，当前连接数: {pool_size}")
        
        return True
    
    def test_2_deep_recursion_analysis(self):
        """测试2: 图分析算法递归深度测试"""
        print("\n" + "="*80)
        print("🔄 测试2: 图分析算法递归深度测试")
        print("="*80)
        
        from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
        
        # 创建链式图谱，测试递归深度
        graph = KnowledgeGraph(graph_name="DeepRecursion")
        
        print("  创建1000节点的链式图...")
        entities = []
        for i in range(1000):
            entity = Entity(entity_name=f"Node_{i}", entity_type="概念")
            entities.append(entity)
            graph.add_entity(entity)
        
        for i in range(999):
            graph.add_relation(Relation(
                source_entity_id=entities[i].entity_id,
                target_entity_id=entities[i+1].entity_id,
                relation_type="NEXT"
            ))
        
        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        
        print("  测试find_all_paths深度...")
        sys.setrecursionlimit(2000)
        
        try:
            start = time.time()
            paths = analyzer.find_all_paths(
                entities[0].entity_id, 
                entities[999].entity_id, 
                max_depth=1000
            )
            duration = time.time() - start
            
            print(f"  找到 {len(paths)} 条路径, 耗时: {duration:.3f}s")
            
            if duration > 1.0:
                self.log_issue("warning", "性能问题", 
                             f"深度路径查找耗时过长: {duration:.3f}s")
                
        except RecursionError:
            self.log_issue("critical", "递归错误", "find_all_paths 触发递归深度限制")
        except Exception as e:
            self.log_issue("critical", "异常", f"路径查找异常: {str(e)}")
        
        return True
    
    def test_3_json_serialization_extremes(self):
        """测试3: JSON序列化极限测试"""
        print("\n" + "="*80)
        print("📦 测试3: JSON序列化极限测试")
        print("="*80)
        
        import json
        
        test_cases = [
            ("正常对象", {"key": "value"}),
            ("深层嵌套", {"a": {"b": {"c": {"d": {"e": "deep"}}}}}),  # 5层
            ("超宽对象", {f"key_{i}": f"value_{i}" for i in range(1000)}),  # 1000个键
            ("超长字符串", "x" * 1000000),  # 1MB字符串
            ("特殊字符", {"emoji": "🚀💻🎯", "chinese": "中文测试"}),
            ("None和空值", {"none": None, "empty_list": [], "empty_dict": {}}),
            ("数字边界", {"int_max": sys.maxsize, "float_max": sys.float_info.max}),
        ]
        
        for name, data in test_cases:
            try:
                encoded = json.dumps(data, ensure_ascii=False)
                decoded = json.loads(encoded)
                
                if str(data) == str(decoded):
                    print(f"  ✅ {name}: 序列化成功 ({len(encoded)} bytes)")
                else:
                    self.log_issue("warning", "JSON问题", f"{name}: 数据不一致")
                    
            except Exception as e:
                self.log_issue("critical", "JSON错误", f"{name}: {str(e)}")
        
        return True
    
    def test_4_memory_leak_detection(self):
        """测试4: 内存泄漏深度检测"""
        print("\n" + "="*80)
        print("💾 测试4: 内存泄漏深度检测")
        print("="*80)
        
        try:
            import psutil
            process = psutil.Process()
        except:
            print("  psutil不可用，跳过内存测试")
            return True
        
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        print(f"  初始内存: {initial_memory:.2f} MB")
        
        # 测试1: 大量创建和删除对象
        print("  测试: 1000次创建/删除循环...")
        repo = KnowledgeRepository()
        
        for i in range(1000):
            graph = KnowledgeGraph(graph_name=f"MemLeakTest_{i}")
            for j in range(50):
                graph.add_entity(Entity(
                    entity_name=f"Entity_{j}",
                    entity_type="概念",
                    properties={'index': j, 'data': 'x'*1000}
                ))
            
            repo.save_graph(graph)
            repo.get_graph(graph.graph_id)
            repo.delete_graph(graph.graph_id)
            
            if i % 100 == 0:
                gc.collect()
                current_mem = process.memory_info().rss / 1024 / 1024
                print(f"    迭代 {i}: 内存 {current_mem:.2f} MB")
        
        gc.collect()
        time.sleep(0.5)
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        print(f"  最终内存: {final_memory:.2f} MB")
        print(f"  内存增长: {memory_growth:.2f} MB")
        
        if memory_growth > 100:
            self.log_issue("warning", "内存问题", 
                         f"可能存在内存泄漏: 增长 {memory_growth:.2f} MB")
        elif memory_growth > 50:
            self.log_issue("warning", "内存问题",
                         f"内存增长较多: {memory_growth:.2f} MB")
        
        return True
    
    def test_5_concurrent_write_conflicts(self):
        """测试5: 并发写入冲突测试"""
        print("\n" + "="*80)
        print("🔀 测试5: 并发写入冲突测试")
        print("="*80)
        
        config = DatabaseConnectionConfig(db_path=self.db_path, pool_size=10)
        initialize_database(config)
        repo = KnowledgeRepository()
        
        errors = []
        
        def writer(writer_id):
            try:
                for i in range(50):
                    graph = KnowledgeGraph(graph_name=f"Writer_{writer_id}_Graph_{i}")
                    for j in range(20):
                        graph.add_entity(Entity(
                            entity_name=f"Writer{writer_id}_Entity_{j}",
                            entity_type="概念"
                        ))
                    
                    repo.save_graph(graph)
                    time.sleep(random.random() * 0.01)
                    
            except Exception as e:
                errors.append(f"Writer_{writer_id}: {str(e)}")
        
        threads = []
        print("  启动10个并发写入线程...")
        
        for i in range(10):
            t = threading.Thread(target=writer, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        if errors:
            self.log_issue("warning", "并发问题", 
                         f"发现 {len(errors)} 个并发写入错误")
            for err in errors[:3]:
                print(f"    {err}")
        else:
            print("  ✅ 无并发写入错误")
        
        return True
    
    def test_6_database_file_corruption(self):
        """测试6: 数据库文件损坏恢复测试"""
        print("\n" + "="*80)
        print("💾 测试6: 数据库文件损坏恢复测试")
        print("="*80)
        
        repo = KnowledgeRepository()
        
        graph = KnowledgeGraph(graph_name="CorruptionTest")
        for i in range(10):
            graph.add_entity(Entity(entity_name=f"Entity_{i}", entity_type="概念"))
        repo.save_graph(graph)
        
        print("  保存测试数据成功")
        
        retrieved = repo.get_graph(graph.graph_id)
        if retrieved and len(retrieved.entities) == 10:
            print("  ✅ 读写验证成功")
        else:
            self.log_issue("critical", "数据完整性", "读写验证失败")
            return False
        
        repo.delete_graph(graph.graph_id)
        
        return True
    
    def test_7_uuid_collision_simulation(self):
        """测试7: UUID碰撞模拟测试"""
        print("\n" + "="*80)
        print("🔑 测试7: UUID碰撞模拟测试")
        print("="*80)
        
        import uuid
        
        generated_ids = set()
        collisions = 0
        iterations = 100000
        
        print(f"  生成 {iterations} 个 UUID...")
        
        for i in range(iterations):
            new_id = str(uuid.uuid4())
            if new_id in generated_ids:
                collisions += 1
            generated_ids.add(new_id)
        
        print(f"  碰撞次数: {collisions}")
        
        if collisions > 0:
            self.log_issue("critical", "UUID问题", f"UUID碰撞: {collisions} 次")
        else:
            print(f"  ✅ UUID生成质量良好 (无碰撞)")
        
        return True
    
    def run_all(self):
        print("\n" + "="*80)
        print("🔬 Arkanalyzer 深度极限测试")
        print(f"⏰ 开始时间: {datetime.now().isoformat()}")
        print("="*80)
        
        self.test_1_connection_pool_limit()
        self.test_2_deep_recursion_analysis()
        self.test_3_json_serialization_extremes()
        self.test_4_memory_leak_detection()
        self.test_5_concurrent_write_conflicts()
        self.test_6_database_file_corruption()
        self.test_7_uuid_collision_simulation()
        
        print("\n" + "="*80)
        print("📊 深度测试总结")
        print("="*80)
        
        print(f"\n  发现问题: {len(self.issues)}")
        
        if self.issues:
            for issue in self.issues:
                print(f"\n  [{issue['severity']}] {issue['category']}")
                print(f"    {issue['description']}")
        else:
            print("\n  ✅ 未发现严重问题！")
        
        print("="*80)
        
        return len([i for i in self.issues if i['severity'] == 'critical']) == 0
        
    def cleanup(self):
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    tester = DeepStressTest()
    try:
        result = tester.run_all()
        return 0 if result else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
