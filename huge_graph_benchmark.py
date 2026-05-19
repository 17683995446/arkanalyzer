#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 超大图谱与性能基准测试
测试系统在极限数据规模下的表现
"""

import os
import sys
import tempfile
import shutil
import random
import time
import gc
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class PerformanceBenchmark:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "benchmark_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repo = KnowledgeRepository()
        self.benchmark_results = []
        self.issues = []

    def log_benchmark(self, name: str, duration: float, details: Dict = None):
        result = {
            'name': name,
            'duration': duration,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.benchmark_results.append(result)
        print(f"  ⏱️  {name}: {duration:.3f}s", end="")
        if details:
            print(f" - {details}")
        else:
            print()

    def create_huge_graph(self, num_entities: int, num_relations: int) -> KnowledgeGraph:
        """创建超大图谱"""
        print(f"\n  📊 创建超大图谱: {num_entities} 实体, {num_relations} 关系...")
        
        graph = KnowledgeGraph(graph_name=f"超大图谱 {num_entities}", 
                            description=f"性能基准测试 - {num_entities} 实体")
        
        entity_types = ["概念", "人物", "地点", "组织", "事件", "物体"]
        
        # 创建实体
        entities = []
        start = time.time()
        for i in range(num_entities):
            entity = Entity(
                entity_name=f"实体_{i}",
                entity_type=random.choice(entity_types),
                description=f"这是第 {i} 个实体, 用于性能测试",
                properties={
                    'index': i,
                    'random_value': random.random(),
                    'tags': random.sample(['重要', '普通', '新', '归档'], k=random.randint(1,3))
                }
            )
            entities.append(entity)
            graph.add_entity(entity)
        entity_create_time = time.time() - start
        
        # 创建关系
        start = time.time()
        for i in range(num_relations):
            source_idx = random.randint(0, num_entities - 1)
            target_idx = random.randint(0, num_entities - 1)
            
            # 避免自环
            while target_idx == source_idx:
                target_idx = random.randint(0, num_entities - 1)
            
            relation = Relation(
                source_entity_id=entities[source_idx].entity_id,
                target_entity_id=entities[target_idx].entity_id,
                relation_type=random.choice(["相关", "包含", "属于", "关联", "引用"]),
                weight=random.random(),
                properties={'relation_index': i}
            )
            graph.add_relation(relation)
        relation_create_time = time.time() - start
        
        print(f"    实体创建: {entity_create_time:.3f}s, 关系创建: {relation_create_time:.3f}s")
        
        return graph

    def benchmark_1_huge_graph_save(self):
        """基准测试1: 超大图谱保存"""
        print("\n" + "="*80)
        print("🔥 基准测试1: 超大图谱保存")
        print("="*80)
        
        sizes = [
            (1000, 3000),    # 小规模
            (5000, 15000),   # 中规模
            (10000, 30000),  # 大规模
            (25000, 75000),  # 超大规模
        ]
        
        for num_entities, num_relations in sizes:
            gc.collect()
            start_memory = self.get_memory_usage()
            
            graph = self.create_huge_graph(num_entities, num_relations)
            
            save_start = time.time()
            success = self.repo.save_graph(graph)
            save_duration = time.time() - save_start
            
            if success:
                graph_id = graph.graph_id
                self.log_benchmark(f"保存 {num_entities} 实体", save_duration, 
                                {'relations': num_relations})
                
                # 读取回来
                load_start = time.time()
                retrieved = self.repo.get_graph(graph_id)
                load_duration = time.time() - load_start
                
                if retrieved:
                    self.log_benchmark(f"读取 {num_entities} 实体", load_duration)
                
                # 删除
                delete_start = time.time()
                self.repo.delete_graph(graph_id)
                delete_duration = time.time() - delete_start
                self.log_benchmark(f"删除 {num_entities} 实体", delete_duration)
            
            end_memory = self.get_memory_usage()
            print(f"    内存变化: {start_memory:.1f}MB -> {end_memory:.1f}MB")
            
            gc.collect()
        
        return True

    def benchmark_2_graph_analysis(self):
        """基准测试2: 图分析性能"""
        print("\n" + "="*80)
        print("🔬 基准测试2: 图分析性能")
        print("="*80)
        
        # 创建测试图谱
        graph = self.create_huge_graph(5000, 15000)
        
        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        
        # 统计分析
        start = time.time()
        stats = analyzer.calculate_statistics()
        duration = time.time() - start
        self.log_benchmark("计算统计", duration, {'nodes': stats.total_nodes, 'edges': stats.total_edges})
        
        # 关键实体
        start = time.time()
        key_entities = analyzer.find_key_entities(20)
        duration = time.time() - start
        self.log_benchmark("关键实体识别", duration, {'found': len(key_entities)})
        
        # 社区检测
        start = time.time()
        communities = analyzer.detect_communities_bfs()
        duration = time.time() - start
        self.log_benchmark("社区检测", duration, {'communities': len(communities.communities)})
        
        # 路径查找（多次）
        total_duration = 0
        path_count = 100
        for i in range(path_count):
            if len(graph.entities) >= 2:
                src_idx = random.randint(0, len(graph.entities)-1)
                tgt_idx = random.randint(0, len(graph.entities)-1)
                
                start = time.time()
                path = analyzer.find_shortest_path(
                    graph.entities[src_idx].entity_id,
                    graph.entities[tgt_idx].entity_id
                )
                total_duration += time.time() - start
        
        self.log_benchmark(f"{path_count} 次路径查找", total_duration, 
                        {'avg': f"{total_duration/path_count:.5f}s/次"})
        
        return True

    def benchmark_3_search_performance(self):
        """基准测试3: 搜索性能"""
        print("\n" + "="*80)
        print("🔍 基准测试3: 搜索性能")
        print("="*80)
        
        # 创建测试图谱
        graph = self.create_huge_graph(10000, 25000)
        self.repo.save_graph(graph)
        
        # 测试搜索
        search_terms = ["实体", "100", "5000", "9999", "不存在"]
        
        for term in search_terms:
            start = time.time()
            results = self.repo.search_entities(term, graph_id=graph.graph_id)
            duration = time.time() - start
            self.log_benchmark(f"搜索 '{term}'", duration, {'results': len(results)})
        
        self.repo.delete_graph(graph.graph_id)
        return True

    def benchmark_4_concurrent_operations(self):
        """基准测试4: 并发操作性能"""
        print("\n" + "="*80)
        print("🔀 基准测试4: 并发操作性能")
        print("="*80)
        
        import threading
        
        # 先创建一个基础图谱
        base_graph = self.create_huge_graph(1000, 3000)
        self.repo.save_graph(base_graph)
        base_graph_id = base_graph.graph_id
        
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(50):
                    # 混合操作
                    self.repo.get_graph(base_graph_id)
                    self.repo.search_entities(f"实体_{random.randint(0,999)}")
                    self.repo.get_all_graphs()
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        threads = []
        num_threads = [2, 5, 10, 20]
        
        for nt in num_threads:
            print(f"\n    测试 {nt} 线程...")
            errors.clear()
            
            start = time.time()
            for i in range(nt):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            duration = time.time() - start
            threads.clear()
            
            self.log_benchmark(f"{nt} 线程并发", duration, {'errors': len(errors)})
        
        self.repo.delete_graph(base_graph_id)
        return len(errors) == 0

    def get_memory_usage(self) -> float:
        """获取当前内存使用（MB）"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0

    def run_all(self):
        print("\n" + "="*80)
        print("⚡ Arkanalyzer 超大图谱与性能基准测试")
        print("="*80)
        print(f"  开始时间: {datetime.now().isoformat()}")
        
        print(f"\n  💾 初始内存: {self.get_memory_usage():.1f} MB")
        
        try:
            self.benchmark_1_huge_graph_save()
            self.benchmark_2_graph_analysis()
            self.benchmark_3_search_performance()
            self.benchmark_4_concurrent_operations()
            
            self.print_summary()
        except Exception as e:
            print(f"\n  ❌ 测试异常: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return len(self.issues) == 0

    def print_summary(self):
        print("\n" + "="*80)
        print("📊 性能基准测试总结")
        print("="*80)
        
        if self.benchmark_results:
            print(f"\n  所有 {len(self.benchmark_results)} 个基准测试完成:")
            
            for res in self.benchmark_results:
                print(f"    ✅ {res['name']}: {res['duration']:.3f}s")
        
        if self.issues:
            print(f"\n  ⚠️ 发现 {len(self.issues)} 个问题:")
            for issue in self.issues:
                print(f"    - {issue}")
        else:
            print(f"\n  ✨ 未发现任何问题！")
        
        print("\n" + "="*80)

    def cleanup(self):
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    benchmark = PerformanceBenchmark()
    try:
        success = benchmark.run_all()
        return 0 if success else 1
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    sys.exit(main())
