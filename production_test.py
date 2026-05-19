#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 真实场景压力测试 - 生产环境模拟
模拟真实用户操作，发现系统中的问题
"""

import os
import sys
import tempfile
import shutil
import random
import json
import time
import threading
import gc
from datetime import datetime, timedelta
from typing import Dict, List, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class ProductionTestReporter:
    """生产环境测试报告器"""
    
    def __init__(self):
        self.test_cases = []
        self.issues = []
        self.start_time = time.time()
        self.memory_samples = []
    
    def log_test(self, name, success, duration, details=None):
        result = {
            'name': name,
            'success': success,
            'duration': duration,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.test_cases.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {name} - {duration:.3f}s")
        if details:
            for k, v in details.items():
                print(f"  {k}: {v}")
    
    def log_issue(self, issue_type: str, description: str, severity: str = "medium", details: dict = None):
        self.issues.append({
            'type': issue_type,
            'description': description,
            'severity': severity,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })
        print(f"  🐛 [{severity.upper()}] {issue_type}: {description}")
    
    def log_memory(self, label: str):
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_samples.append({'label': label, 'memory_mb': memory_mb, 'timestamp': datetime.now().isoformat()})
            print(f"  💾 Memory: {memory_mb:.2f} MB")
        except Exception:
            pass
    
    def generate_report(self):
        total = len(self.test_cases)
        passed = sum(1 for tc in self.test_cases if tc['success'])
        print(f"\n{'='*80}")
        print("📊 PRODUCTION TEST REPORT")
        print(f"{'='*80}")
        print(f"Total Tests: {total}, Passed: {passed}, Failed: {total-passed}")
        print(f"Total Time: {time.time()-self.start_time:.2f}s")
        
        if self.issues:
            print(f"\n🔴 Found {len(self.issues)} issues:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n{i}. [{issue['severity'].upper()}] {issue['type']}")
                print(f"   {issue['description']}")
                if issue.get('details'):
                    print(f"   Details: {issue['details']}")
        else:
            print("\n🎉 No issues found!")
        
        if self.memory_samples:
            print(f"\n📈 Memory Usage History:")
            for sample in self.memory_samples:
                print(f"  {sample['label']}: {sample['memory_mb']:.2f} MB")
        
        print(f"\n{'='*80}")


def create_test_graph_with_data(name, num_entities=20, num_relations=40):
    """创建测试用的图谱（包含数据）"""
    graph = KnowledgeGraph(graph_name=name, description=f"Test graph with {num_entities} entities")
    entities = []
    
    for i in range(num_entities):
        et = random.choice(["概念", "人物", "地点", "组织", "事件", "物体"])
        entity = Entity(entity_name=f"{name}实体{i}", entity_type=et, description=f"测试实体{i}的描述")
        entities.append(entity)
        graph.add_entity(entity)
    
    for i in range(num_relations):
        s = random.randint(0, num_entities-1)
        t = random.randint(0, num_entities-1)
        while t == s:
            t = random.randint(0, num_entities-1)
        
        rel = Relation(
            source_entity_id=entities[s].entity_id,
            target_entity_id=entities[t].entity_id,
            relation_type=random.choice(["相关", "包含", "属于", "关联"]),
            description=f"{name}关系{i}"
        )
        graph.add_relation(rel)
    
    return graph


def test_basic_operations():
    """测试基本操作"""
    print("\n" + "="*80)
    print("🧪 Test 1: Basic Operations (Create, Save, Load, Delete)")
    print("="*80)
    start = time.time()
    
    try:
        # 1. 创建新图谱
        graph = create_test_graph_with_data("BasicTestGraph", 10, 20)
        print(f"  Created graph with {len(graph.entities)} entities, {len(graph.relations)} relations")
        
        # 2. 保存图谱
        save_start = time.time()
        result = repo.save_graph(graph)
        save_time = time.time()-save_start
        if not result:
            reporter.log_issue("SaveFailed", "Failed to save graph", "critical")
            return False
        
        # 3. 读取图谱
        load_start = time.time()
        loaded = repo.get_graph(graph.graph_id)
        load_time = time.time()-load_start
        if not loaded:
            reporter.log_issue("LoadFailed", "Failed to load graph after save", "critical")
            return False
        
        # 4. 验证数据
        assert len(loaded.entities) == len(graph.entities), "Entity count mismatch"
        assert len(loaded.relations) == len(graph.relations), "Relation count mismatch"
        
        # 5. 获取所有图谱
        all_graphs = repo.get_all_graphs()
        assert len(all_graphs) > 0, "Should have at least one graph"
        
        # 6. 删除图谱
        delete_result = repo.delete_graph(graph.graph_id)
        assert delete_result, "Delete should succeed"
        
        # Verify it's gone
        assert repo.get_graph(graph.graph_id) is None, "Graph should be deleted"
        
        reporter.log_test("Basic Operations", True, time.time()-start, {
            "entities": len(graph.entities),
            "relations": len(graph.relations),
            "save_time": f"{save_time:.4f}s",
            "load_time": f"{load_time:.4f}s"
        })
        return True
    except Exception as e:
        reporter.log_issue("BasicOpsError", f"Basic operations failed: {str(e)}", "critical")
        import traceback
        traceback.print_exc()
        return False


def test_entity_search():
    """测试实体搜索"""
    print("\n" + "="*80)
    print("🔍 Test 2: Entity Search")
    print("="*80)
    start = time.time()
    
    try:
        # 1. 创建一个搜索测试图谱
        graph = KnowledgeGraph(graph_name="SearchTestGraph", description="Test graph for search")
        search_terms = ["苹果", "Apple", "banana", "🍌", "测试"]
        for term in search_terms:
            graph.add_entity(Entity(entity_name=f"测试{term}实体", entity_type="概念", description=f"关于{term}的描述"))
        
        repo.save_graph(graph)
        
        # 2. 测试各种搜索
        test_cases = [
            ("测试", "Expected to find all entities"),
            ("Apple", "Expected to find Apple"),
            ("🍌", "Expected to find banana"),
            ("nonexistentterm12345", "Should return nothing"),
        ]
        
        all_passed = True
        for keyword, description in test_cases:
            results = repo.search_entities(keyword, graph_id=graph.graph_id)
            if keyword == "测试" and len(results) != len(search_terms):
                reporter.log_issue("SearchResultsMismatch", f"For '{keyword}' expected {len(search_terms)}, got {len(results)}", "medium")
                all_passed = False
        
        repo.delete_graph(graph.graph_id)
        
        reporter.log_test("Entity Search", all_passed, time.time()-start)
        return all_passed
    except Exception as e:
        reporter.log_issue("SearchError", f"Search test failed: {str(e)}", "medium")
        return False


def test_graph_statistics():
    """测试图谱统计"""
    print("\n" + "="*80)
    print("📈 Test 3: Graph Statistics")
    print("="*80)
    start = time.time()
    
    try:
        graph = create_test_graph_with_data("StatsTestGraph", 30, 60)
        repo.save_graph(graph)
        
        # 1. 测试 repository 统计
        repo_stats = repo.get_graph_statistics(graph.graph_id)
        
        # 2. 测试分析器
        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        analyzer_stats = analyzer.calculate_statistics()
        
        assert repo_stats['entity_count'] == 30, f"Expected 30 entities, got {repo_stats['entity_count']}"
        assert repo_stats['relation_count'] == 60, f"Expected 60 relations, got {repo_stats['relation_count']}"
        
        repo.delete_graph(graph.graph_id)
        reporter.log_test("Graph Statistics", True, time.time()-start, {
            "entity_types_count": len(repo_stats['entity_types']),
            "density": f"{repo_stats['density']:.4f}"
        })
        return True
    except Exception as e:
        reporter.log_issue("StatsError", f"Statistics test failed: {str(e)}", "medium")
        return False


def test_multiple_graphs():
    """测试多个图谱"""
    print("\n" + "="*80)
    print("📚 Test 4: Multiple Graph Operations")
    print("="*80)
    start = time.time()
    
    try:
        # 1. 创建 5 个图谱
        num_graphs = 5
        graph_ids = []
        for i in range(num_graphs):
            graph = create_test_graph_with_data(f"MultiGraph{i}", 10, 20)
            repo.save_graph(graph)
            graph_ids.append(graph.graph_id)
        
        # 2. 获取所有图谱
        all_graphs = repo.get_all_graphs()
        assert len(all_graphs) >= num_graphs, f"Expected at least {num_graphs}"
        
        # 3. 删除所有创建的
        for gid in graph_ids:
            assert repo.delete_graph(gid), f"Should delete graph {gid}"
        
        # Verify deletion
        for gid in graph_ids:
            assert repo.get_graph(gid) is None, f"Graph {gid} should be deleted"
        
        reporter.log_test("Multiple Graphs", True, time.time()-start, {"num_graphs": num_graphs})
        return True
    except Exception as e:
        reporter.log_issue("MultiGraphError", f"Multiple graphs test failed: {str(e)}", "high")
        import traceback
        traceback.print_exc()
        return False


def test_edge_cases():
    """测试边界条件"""
    print("\n" + "="*80)
    print("🚧 Test 5: Edge Cases")
    print("="*80)
    start = time.time()
    
    try:
        # 空图谱
        empty_graph = KnowledgeGraph(graph_name="EmptyGraph", description="")
        repo.save_graph(empty_graph)
        assert len(repo.get_graph(empty_graph.graph_id).entities) == 0
        
        # 仅有一个实体的图谱
        single = KnowledgeGraph("SingleEntity", "")
        single_entity = Entity(entity_name="Lonely", entity_type="概念")
        single.add_entity(single_entity)
        repo.save_graph(single)
        
        # 重复关系（同样的 source 和 target）
        double_rel = KnowledgeGraph("DoubleRel", "")
        e1 = Entity("A", "概念")
        e2 = Entity("B", "概念")
        double_rel.add_entity(e1)
        double_rel.add_entity(e2)
        double_rel.add_relation(Relation(source_entity_id=e1.entity_id, target_entity_id=e2.entity_id, relation_type="相关"))
        double_rel.add_relation(Relation(source_entity_id=e1.entity_id, target_entity_id=e2.entity_id, relation_type="关联"))
        repo.save_graph(double_rel)
        
        # 特殊字符
        special = KnowledgeGraph("SpecialChars", "")
        special.add_entity(Entity(entity_name='测试"引号', entity_type="概念"))
        special.add_entity(Entity(entity_name='测试\'单引号', entity_type="概念"))
        special.add_entity(Entity(entity_name='测试\n换行', entity_type="概念"))
        repo.save_graph(special)
        
        repo.delete_graph(empty_graph.graph_id)
        repo.delete_graph(single.graph_id)
        repo.delete_graph(double_rel.graph_id)
        repo.delete_graph(special.graph_id)
        
        reporter.log_test("Edge Cases", True, time.time()-start)
        return True
    except Exception as e:
        reporter.log_issue("EdgeCaseError", f"Edge case test failed: {str(e)}", "high")
        return False


def test_analyzer_operations():
    """测试图分析器"""
    print("\n" + "="*80)
    print("🔬 Test 6: Graph Analyzer")
    print("="*80)
    start = time.time()
    
    try:
        # 创建有环的图
        graph = create_test_graph_with_data("AnalyzerTest", 20, 50)
        
        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        
        # 测试各种分析功能
        stats = analyzer.calculate_statistics()
        assert stats.total_nodes == 20
        
        # 找关键实体
        key_entities = analyzer.find_key_entities(5)
        
        # 社区检测
        communities = analyzer.detect_communities_bfs()
        
        # 路径查找
        if len(graph.entities) >= 2:
            src = graph.entities[0].entity_id
            tgt = graph.entities[-1].entity_id
            path_result = analyzer.find_shortest_path(src, tgt)
        
        reporter.log_test("Graph Analyzer", True, time.time()-start, {
            "connected_components": stats.connected_components,
            "communities_found": len(communities.communities),
            "key_entities_found": len(key_entities)
        })
        return True
    except Exception as e:
        reporter.log_issue("AnalyzerError", f"Analyzer test failed: {str(e)}", "medium")
        import traceback
        traceback.print_exc()
        return False


def test_memory_leak():
    """测试长时间运行 - 内存泄漏检测"""
    print("\n" + "="*80)
    print("⏱️ Test 7: Long Running & Memory Leak Detection")
    print("="*80)
    start = time.time()
    
    try:
        num_iterations = 50
        reporter.log_memory("Before Leak Test")
        
        for i in range(num_iterations):
            # 创建很多对象并删除
            graph = create_test_graph_with_data(f"MemoryTest{i}", 25, 50)
            repo.save_graph(graph)
            repo.get_graph(graph.graph_id)
            repo.delete_graph(graph.graph_id)
            gc.collect()
            
            if (i+1) % 10 == 0:
                print(f"  Completed iteration {i+1}/{num_iterations}")
                reporter.log_memory(f"Iteration {i+1}")
        
        reporter.log_memory("After Leak Test")
        
        # 简单检查内存增长
        if len(reporter.memory_samples) >= 2:
            first = reporter.memory_samples[0]['memory_mb']
            last = reporter.memory_samples[-1]['memory_mb']
            if last > first * 1.5:
                reporter.log_issue("MemoryGrowth", f"Memory increased {last-first:.2f}MB, possible leak", "medium")
        
        reporter.log_test("Memory Stability", True, time.time()-start, {"iterations": num_iterations})
        return True
    except Exception as e:
        reporter.log_issue("MemoryTestError", f"Memory test failed: {str(e)}", "medium")
        return False


def test_concurrent_requests():
    """测试并发访问"""
    print("\n" + "="*80)
    print("🔄 Test 8: Concurrent Access")
    print("="*80)
    start = time.time()
    
    errors = []
    lock = threading.Lock()
    
    def worker(worker_id: int, num_ops: int):
        for i in range(num_ops):
            try:
                # 每个 worker 做一些操作
                graph = create_test_graph_with_data(f"Thread{worker_id}Op{i}", 10, 20)
                repo.save_graph(graph)
                repo.get_graph(graph.graph_id)
                repo.get_all_graphs()
                repo.delete_graph(graph.graph_id)
            except Exception as e:
                with lock:
                    errors.append({"worker": worker_id, "error": str(e)})
    
    num_workers = 4
    ops_per_worker = 10
    threads = []
    
    for i in range(num_workers):
        t = threading.Thread(target=worker, args=(i, ops_per_worker))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    if errors:
        reporter.log_issue("ConcurrencyError", f"Concurrency issues found: {len(errors)} errors", "high", errors[:3])
        reporter.log_test("Concurrent Access", False, time.time()-start, {"errors": len(errors)})
        return False
    
    reporter.log_test("Concurrent Access", True, time.time()-start, {
        "workers": num_workers,
        "ops_per_worker": ops_per_worker
    })
    return True


def test_extraction_history():
    """测试抽取历史"""
    print("\n" + "="*80)
    print("📜 Test 9: Extraction History")
    print("="*80)
    start = time.time()
    
    try:
        # 添加一些抽取历史
        for i in range(5):
            repo.save_extraction_history({
                "extraction_id": f"extraction{i}",
                "source_text": f"测试文本{i}",
                "summary": f"摘要{i}",
                "keywords": [f"词{i}", f"测试{i}"],
                "processing_time": 0.5,
                "confidence": 0.8
            })
        
        # 获取历史
        history = repo.get_extraction_history(limit=3)
        assert len(history) <= 3
        
        reporter.log_test("Extraction History", True, time.time()-start, {"history_count": len(history)})
        return True
    except Exception as e:
        reporter.log_issue("ExtractionHistoryError", f"Extraction history failed: {str(e)}", "medium")
        return False


def main():
    global temp_dir, repo, reporter
    
    # 准备测试环境
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "arkanalyzer_test.db")
    config = DatabaseConnectionConfig(db_path=db_path)
    initialize_database(config)
    repo = KnowledgeRepository()
    reporter = ProductionTestReporter()
    
    print("="*80)
    print("🏭 ARKANALYZER PRODUCTION STRESS TEST")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Started: {datetime.now().isoformat()}")
    
    all_passed = True
    tests = [
        ("Basic Ops", test_basic_operations),
        ("Entity Search", test_entity_search),
        ("Graph Stats", test_graph_statistics),
        ("Multiple Graphs", test_multiple_graphs),
        ("Edge Cases", test_edge_cases),
        ("Graph Analyzer", test_analyzer_operations),
        ("Memory Leak", test_memory_leak),
        ("Concurrency", test_concurrent_requests),
        ("Extraction History", test_extraction_history),
    ]
    
    for name, test_func in tests:
        passed = test_func()
        if not passed:
            all_passed = False
    
    # 清理
    try:
        from database.database_connection_manager import get_database_pool
        pool = get_database_pool()
        pool.close_all()
    except Exception:
        pass
    
    shutil.rmtree(temp_dir, ignore_errors=True)
    reporter.generate_report()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
