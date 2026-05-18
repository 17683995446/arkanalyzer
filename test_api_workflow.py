#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer API 真实场景测试
"""
import os
import sys
import tempfile
import shutil
import json
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


def test_api_workflow():
    """
    模拟真实API调用的工作流
    """
    print("\n" + "="*80)
    print("测试真实 API 工作流")
    print("="*80)
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'api_test.db')
    config = DatabaseConnectionConfig(db_path=db_path)
    initialize_database(config)
    repo = KnowledgeRepository()
    
    results = {
        "passed": 0,
        "failed": 0,
        "issues": []
    }
    
    # 1. 创建知识图谱
    try:
        graph = KnowledgeGraph(
            graph_name="API 测试图谱",
            description="用于测试API功能的真实知识图谱"
        )
        entities = [
            Entity(entity_name="Python", entity_type="编程语言"),
            Entity(entity_name="Flask", entity_type="Web框架"),
            Entity(entity_name="SQLite", entity_type="数据库"),
            Entity(entity_name="D3.js", entity_type="可视化库"),
            Entity(entity_name="Arkanalyzer", entity_type="应用程序")
        ]
        for e in entities:
            graph.add_entity(e)
        
        relations = [
            Relation(source_entity_id=entities[0].entity_id, target_entity_id=entities[1].entity_id, relation_type="使用"),
            Relation(source_entity_id=entities[0].entity_id, target_entity_id=entities[2].entity_id, relation_type="使用"),
            Relation(source_entity_id=entities[1].entity_id, target_entity_id=entities[4].entity_id, relation_type="基于"),
            Relation(source_entity_id=entities[3].entity_id, target_entity_id=entities[4].entity_id, relation_type="基于")
        ]
        for r in relations:
            graph.add_relation(r)
        
        save_start = time.time()
        save_success = repo.save_graph(graph)
        save_time = time.time() - save_start
        
        if not save_success:
            results["failed"] += 1
            results["issues"].append({"type": "SaveGraph", "message": "保存图谱失败"})
        else:
            results["passed"] += 1
            print(f"✅ 创建图谱成功，耗时: {save_time:.3f}s")
    
    except Exception as e:
        results["failed"] +=1
        results["issues"].append({"type": "CreateGraph", "message": str(e)})
        print(f"❌ 创建图谱失败: {e}")
    
    # 2. 获取所有图谱
    try:
        get_all_start = time.time()
        graphs = repo.get_all_graphs()
        get_all_time = time.time() - get_all_start
        
        if len(graphs) == 0:
            results["failed"] +=1
            results["issues"].append({"type": "GetAllGraphs", "message": "应该有至少一个图谱"})
        else:
            results["passed"] +=1
            print(f"✅ 获取所有图谱成功，找到 {len(graphs)} 个图谱，耗时: {get_all_time:.3f}s")
    
    except Exception as e:
        results["failed"] +=1
        results["issues"].append({"type": "GetAllGraphs", "message": str(e)})
        print(f"❌ 获取所有图谱失败: {e}")
    
    # 3. 统计数据
    try:
        if len(graphs) >0:
            stats = repo.get_graph_statistics(graphs[0].graph_id)
            results["passed"] +=1
            print(f"✅ 获取统计数据成功: 实体={stats['entity_count']}, 关系={stats['relation_count']}")
    
    except Exception as e:
        results["failed"] +=1
        results["issues"].append({"type": "Statistics", "message": str(e)})
    
    # 4. 搜索实体
    try:
        search_results = repo.search_entities("Python")
        if len(search_results) ==0:
            results["failed"] +=1
            results["issues"].append({"type": "Search", "message": "应该找到Python"})
        else:
            results["passed"] +=1
            print(f"✅ 搜索实体成功，找到 {len(search_results)} 个实体")
    
    except Exception as e:
        results["failed"] +=1
        results["issues"].append({"type": "Search", "message": str(e)})
    
    # 5. 获取邻居
    try:
        neighbors = repo.get_neighbors(entities[0].entity_id)
        if len(neighbors) < 1:
            results["issues"].append({"type": "Neighbors", "message": "Python应该有邻居"})
        else:
            results["passed"] +=1
            print(f"✅ 获取邻居成功，找到 {len(neighbors)} 个邻居")
    except Exception as e:
        results["failed"] +=1
        results["issues"].append({"type": "Neighbors", "message": str(e)})
    
    # 6. 删除图谱
    try:
        if len(graphs) >0:
            delete_success = repo.delete_graph(graphs[0].graph_id)
            if delete_success:
                results["passed"] +=1
                print(f"✅ 删除图谱成功")
            else:
                results["failed"] +=1
                results["issues"].append({"type": "Delete", "message": "删除图谱失败"})
    except Exception as e:
        results["failed"] +=1
        results["issues"].append({"type": "Delete", "message": str(e)})
    
    # 7. 并发测试
    print("\n🚀 并发测试...")
    errors = []
    lock = threading.Lock()
    
    def concurrent_worker(worker_id):
        try:
            g = KnowledgeGraph(graph_name=f"并发图谱{worker_id}")
            for i in range(5):
                g.add_entity(Entity(entity_name=f"并发实体{worker_id}-{i}"))
            repo.save_graph(g)
            repo.get_graph(g.graph_id)
        except Exception as e:
            with lock:
                errors.append({"worker": worker_id, "error": str(e)})
    
    num_workers = 5
    threads = []
    start_time = time.time()
    for i in range(num_workers):
        t = threading.Thread(target=concurrent_worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    if len(errors) > 0:
        results["failed"] +=1
        results["issues"].append({"type": "Concurrency", "message": f"并发测试有 {len(errors)} 个错误", "details": errors})
        print(f"❌ 并发测试有问题: {len(errors)} 个错误")
    else:
        results["passed"] +=1
        print(f"✅ 并发测试通过，耗时 {time.time()-start_time:.3f}s")
    
    # 总结
    print("\n" + "="*80)
    print("API 工作流测试总结")
    print(f"✅ 通过: {results['passed']}, ❌ 失败: {results['failed']}")
    
    if results["issues"]:
        print(f"\n发现的问题 ({len(results['issues'])}):")
        for issue in results["issues"]:
            print(f"  - {issue['type']}: {issue['message']}")
    else:
        print("\n🎉 所有API工作流测试通过！")
    
    print("="*80)
    
    # 清理
    try:
        from database.database_connection_manager import get_database_pool
        pool = get_database_pool()
        pool.close_all()
    except Exception:
        pass
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    return results


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ARKANALYZER 真实场景 API 测试")
    print("="*80)
    test_api_workflow()
