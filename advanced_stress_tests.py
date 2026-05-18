#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级压力测试 - 真实发现问题
"""
import sys
import os
import time
import tempfile
import shutil
import random
import json
import threading
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig
)


class StressTestReporter:
    """压力测试报告生成器"""
    
    def __init__(self):
        self.test_results: List[Dict] = []
        self.issues: List[Dict] = []
        self.start_time = time.time()
    
    def log_test(self, name, success, duration, details=None):
        self.test_results.append({
            'name': name,
            'success': success,
            'duration': duration,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })
        status = "✅" if success else "❌"
        print(f"{status} {name} - {duration:.3f}s")
    
    def log_issue(self, issue_type, desc, details=None):
        self.issues.append({
            'type': issue_type,
            'description': desc,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })
        print(f"  🐛 {issue_type}: {desc}")
    
    def generate_report(self):
        print("\n" + "="*80)
        print("压力测试报告")
        print("="*80)
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['success'])
        print(f"\n总测试: {total}, 通过: {passed}, 失败: {total - passed}")
        print(f"总耗时: {time.time() - self.start_time:.2f}秒")
        
        if self.issues:
            print(f"\n发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n{i}. {issue['type']}")
                print(f"   描述: {issue['description']}")
                if issue['details']:
                    print(f"   细节: {json.dumps(issue['details'], ensure_ascii=False)}")
        else:
            print("\n🎉 恭喜！没有发现问题！")
        
        print("\n" + "="*80)


def test_1_extremely_large_graph():
    """测试1: 超大规模图谱"""
    print("\n" + "="*80)
    print("测试1: 超大规模图谱 (5000实体 + 15000关系)")
    print("="*80)
    
    start = time.time()
    graph = KnowledgeGraph(
        graph_name="极限大规模图谱",
        description="用于压力测试的超大规模图谱"
    )
    
    # 创建实体
    entities = []
    print("\n  创建实体...")
    for i in range(5000):
        e = Entity(
            entity_name=f"实体_{i}_{random.randint(1000, 9999)}",
            entity_type=random.choice(["概念", "人物", "地点", "组织", "事件"])
        )
        entities.append(e)
        graph.add_entity(e)
        if (i+1) % 1000 == 0:
            print(f"    已创建 {i+1} 个实体")
    
    # 创建关系
    print("\n  创建关系...")
    for i in range(15000):
        src_idx = random.randint(0, 4999)
        dst_idx = random.randint(0, 4999)
        while dst_idx == src_idx:
            dst_idx = random.randint(0, 4999)
        
        rel = Relation(
            source_entity_id=entities[src_idx].entity_id,
            target_entity_id=entities[dst_idx].entity_id,
            relation_type=random.choice(["相关", "包含", "属于", "关联"])
        )
        graph.add_relation(rel)
        if (i+1) % 3000 == 0:
            print(f"    已创建 {i+1} 个关系")
    
    # 保存
    print("\n  保存图谱...")
    save_start = time.time()
    result = repo.save_graph(graph)
    save_time = time.time() - save_start
    print(f"    保存耗时: {save_time:.2f}秒")
    
    # 读取
    print("\n  读取图谱...")
    load_start = time.time()
    loaded = repo.get_graph(graph.graph_id)
    load_time = time.time() - load_start
    print(f"    读取耗时: {load_time:.2f}秒")
    
    # 验证
    if not loaded:
        reporter.log_issue("读取失败", "无法读取保存的超大规模图谱")
        return False
    
    if len(loaded.entities) != 5000:
        reporter.log_issue("实体数量不符", f"期望5000,实际{len(loaded.entities)}",
                            {'expected': 5000, 'actual': len(loaded.entities)})
        return False
    
    if len(loaded.relations) != 15000:
        reporter.log_issue("关系数量不符", f"期望15000,实际{len(loaded.relations)}",
                            {'expected': 15000, 'actual': len(loaded.relations)})
        return False
    
    # 分析性能
    print("\n  图分析性能...")
    analyzer = KnowledgeGraphAnalyzer(loaded.entities, loaded.relations)
    stats = analyzer.calculate_statistics()
    print(f"    节点: {stats.total_nodes}, 边: {stats.total_edges}")
    print(f"    连通分量: {stats.connected_components}")
    
    if save_time > 10:
        reporter.log_issue("性能警告", f"保存过慢: {save_time:.2f}秒")
    
    reporter.log_test("超大规模图谱", True, time.time() - start,
                      {'entities': 5000, 'relations': 15000, 'save': save_time, 'load': load_time})
    return True


def test_2_concurrent_operations():
    """测试2: 并发操作"""
    print("\n" + "="*80)
    print("测试2: 并发操作 (20线程同时读写)")
    print("="*80)
    
    start = time.time()
    errors: List[Dict] = []
    lock = threading.Lock()
    
    def worker(thread_id, count):
        for i in range(count):
            try:
                # 创建
                g = KnowledgeGraph(
                    graph_name=f"并发测试_{thread_id}_{i}",
                    description="测试用"
                )
                for j in range(10):
                    g.add_entity(Entity(
                        entity_name=f"t{thread_id}_e{i}_{j}",
                        entity_type="概念"
                    ))
                repo.save_graph(g)
                
                # 读取
                repo.get_graph(g.graph_id)
                
                # 删除
                repo.delete_graph(g.graph_id)
                
            except Exception as e:
                with lock:
                    errors.append({'thread': thread_id, 'i': i, 'error': str(e)})
                    if len(errors) < 10:
                        print(f"    线程{thread_id}错误: {e}")
    
    print("\n  启动并发线程...")
    threads = []
    num_threads = 20
    per_thread_ops = 20
    for t in range(num_threads):
        thread = threading.Thread(target=worker, args=(t, per_thread_ops))
        threads.append(thread)
        thread.start()
    
    print("  等待线程完成...")
    for thread in threads:
        thread.join()
    
    duration = time.time() - start
    
    if errors:
        reporter.log_issue("并发错误", f"发现{len(errors)}个并发异常", errors[:10])
        success = False
    else:
        success = True
    
    reporter.log_test("并发操作", success, duration,
                      {'threads': num_threads, 'operations': num_threads*per_thread_ops, 'errors': len(errors)})
    return success


def test_3_memory_stability():
    """测试3: 内存稳定性"""
    print("\n" + "="*80)
    print("测试3: 内存稳定性 (重复创建/删除 100次)")
    print("="*80)
    
    start = time.time()
    
    try:
        for i in range(100):
            graph = KnowledgeGraph(graph_name=f"内存测试_{i}", description="测试用")
            
            for j in range(100):
                graph.add_entity(Entity(entity_name=f"e{i}_{j}", entity_type="概念"))
            
            for j in range(50):
                src_idx = random.randint(0, 99)
                dst_idx = random.randint(0, 99)
                if src_idx != dst_idx:
                    graph.add_relation(Relation(
                        source_entity_id=graph.entities[src_idx].entity_id,
                        target_entity_id=graph.entities[dst_idx].entity_id,
                        relation_type="相关"
                    ))
            
            repo.save_graph(graph)
            repo.delete_graph(graph.graph_id)
            
            if (i+1) % 20 == 0:
                print(f"    已执行 {i+1} 轮")
        
        reporter.log_test("内存稳定性", True, time.time()-start, {'cycles': 100})
        return True
        
    except Exception as e:
        reporter.log_issue("内存错误", f"内存测试失败: {e}")
        return False


def test_4_edge_cases():
    """测试4: 极端边界条件"""
    print("\n" + "="*80)
    print("测试4: 极端边界条件")
    print("="*80)
    
    start = time.time()
    
    # 空图谱
    print("\n  测试空图谱...")
    empty = KnowledgeGraph(graph_name="空", description="")
    if not repo.save_graph(empty):
        reporter.log_issue("空图谱保存", "空图谱无法保存")
        return False
    
    # 单个实体
    print("\n  测试单个实体...")
    single = KnowledgeGraph("单个实体", "只有一个实体")
    e = Entity(entity_name="孤独实体", entity_type="概念")
    single.add_entity(e)
    if not repo.save_graph(single):
        reporter.log_issue("单个实体", "单个实体无法保存")
        return False
    
    # 超长字符串
    print("\n  测试超长字符串...")
    long_name = "这是一个超长的实体名称_" * 1000
    long_desc = "这是一个超长的实体描述_" * 2000
    long_graph = KnowledgeGraph("长字符串测试", "")
    e_long = Entity(entity_name=long_name, entity_type="概念", description=long_desc)
    long_graph.add_entity(e_long)
    if not repo.save_graph(long_graph):
        reporter.log_issue("超长字符串", "包含超长长字符串的实体无法保存")
        return False
    
    # 特殊字符
    print("\n  测试特殊字符...")
    special = KnowledgeGraph("特殊字符测试", "")
    specials = [
        "🚀表情符号😀",
        '包含"引号的实体',
        '包含\'引号的实体',
        "换行\n的实体",
        "\t制表符",
        "<script>alert('xss')</script>",
        "null\x00字符"
    ]
    for s in specials:
        special.add_entity(Entity(entity_name=s, entity_type="概念"))
    if not repo.save_graph(special):
        reporter.log_issue("特殊字符", "包含特殊字符的实体无法保存")
        return False
    
    # 自环关系
    print("\n  测试自环关系...")
    self_loop = KnowledgeGraph("自环测试", "")
    e_self = Entity("测试节点", "概念")
    self_loop.add_entity(e_self)
    self_loop.add_relation(Relation(
        source_entity_id=e_self.entity_id,
        target_entity_id=e_self.entity_id,
        relation_type="自环"
    ))
    if not repo.save_graph(self_loop):
        reporter.log_issue("自环关系", "自环关系无法保存")
        return False
    
    repo.delete_graph(empty.graph_id)
    repo.delete_graph(single.graph_id)
    repo.delete_graph(long_graph.graph_id)
    repo.delete_graph(special.graph_id)
    repo.delete_graph(self_loop.graph_id)
    
    print("  ✅ 所有边界条件处理正常")
    reporter.log_test("边界条件测试", True, time.time()-start)
    return True


def test_5_analyzer_stress():
    """测试5: 分析器压力"""
    print("\n" + "="*80)
    print("测试5: 分析器压力")
    print("="*80)
    
    start = time.time()
    
    print("\n  创建测试图谱...")
    graph = KnowledgeGraph("分析器压力测试", "")
    
    entities = []
    for i in range(200):
        entities.append(Entity(entity_name=f"a_{i}", entity_type="概念"))
        graph.add_entity(entities[-1])
    
    # 随机连接
    for i in range(600):
        s = random.randint(0, 199)
        d = random.randint(0, 199)
        if s != d:
            graph.add_relation(Relation(
                source_entity_id=entities[s].entity_id,
                target_entity_id=entities[d].entity_id,
                relation_type="连接"
            ))
    
    print("  保存...")
    repo.save_graph(graph)
    
    print("\n  开始分析...")
    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
    
    test_cases = [
        ("统计", lambda: analyzer.calculate_statistics()),
        ("路径查找", lambda: analyzer.find_shortest_path(entities[0].entity_id, entities[-1].entity_id)),
        ("社区检测", lambda: analyzer.detect_communities_bfs()),
        ("关键实体", lambda: analyzer.find_key_entities(10)),
        ("邻居数", lambda: [len(analyzer.adjacency_list[e.entity_id]) for e in graph.entities])
    ]
    
    for name, fn in test_cases:
        case_start = time.time()
        result = fn()
        case_time = time.time() - case_start
        print(f"    {name}: {case_time:.3f}秒")
        
        if case_time > 2:
            reporter.log_issue("性能警告", f"{name}过慢: {case_time:.3f}秒")
    
    reporter.log_test("分析器压力", True, time.time()-start)
    return True


def main():
    global temp_dir, repo, reporter
    
    temp_dir = tempfile.mkdtemp()
    config = DatabaseConnectionConfig(db_path=os.path.join(temp_dir, "stress.db"))
    initialize_database(config)
    repo = KnowledgeRepository()
    
    reporter = StressTestReporter()
    
    print("="*80)
    print("ARKANALYZER 极端压力测试")
    print("="*80)
    
    success = True
    
    # 运行所有测试
    success &= test_1_extremely_large_graph()
    success &= test_2_concurrent_operations()
    success &= test_3_memory_stability()
    success &= test_4_edge_cases()
    success &= test_5_analyzer_stress()
    
    # 清理
    try:
        from database.database_connection_manager import get_database_pool
        pool = get_database_pool()
        pool.close_all()
    except:
        pass
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    reporter.generate_report()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
