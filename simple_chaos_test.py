#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版混乱场景测试 - 更容易发现问题
"""

import os
import sys
import tempfile
import shutil
import random
import time
import threading
import uuid
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


def main():
    print("=" * 80)
    print("🔥 简化版混乱场景测试")
    print("=" * 80)
    
    # 准备
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "simple_chaos_test.db")
    config = DatabaseConnectionConfig(db_path=db_path)
    initialize_database(config)
    repo = KnowledgeRepository()
    
    errors = []
    graph_ids = []
    
    try:
        print("\n📝 第一步: 创建测试图谱...")
        # 创建一些测试数据
        for i in range(5):
            graph = KnowledgeGraph(
                graph_name=f"Test-Graph-{i}",
                description=f"测试图谱 #{i}"
            )
            
            for j in range(10):
                entity = Entity(
                    entity_name=f"Entity-{i}-{j}",
                    entity_type="概念",
                    properties={"index": j}
                )
                graph.add_entity(entity)
            
            for j in range(8):
                if len(graph.entities) >= 2:
                    src = graph.entities[j % len(graph.entities)]
                    tgt = graph.entities[(j+1) % len(graph.entities)]
                    relation = Relation(
                        source_entity_id=src.entity_id,
                        target_entity_id=tgt.entity_id,
                        relation_type="相关"
                    )
                    graph.add_relation(relation)
            
            print(f"    保存图谱 {i}...", end=" ")
            try:
                repo.save_graph(graph)
                graph_ids.append(graph.graph_id)
                print("✅")
            except Exception as e:
                print(f"❌ 错误: {e}")
                errors.append(f"保存图谱 {i}: {e}")
        
        print(f"\n    已保存 {len(graph_ids)} 个图谱")
        
        # 测试读取
        print("\n📖 第二步: 读取测试...")
        for graph_id in graph_ids:
            try:
                graph = repo.get_graph(graph_id)
                if graph:
                    print(f"    读取图谱 {graph_id}: {len(graph.entities)} 实体, {len(graph.relations)} 关系 ✅")
                else:
                    print(f"    读取图谱 {graph_id}: ❌ 未找到")
                    errors.append(f"读取失败: {graph_id}")
            except Exception as e:
                print(f"    读取图谱 {graph_id}: ❌ {e}")
                errors.append(f"读取 {graph_id}: {e}")
        
        # 测试搜索
        print("\n🔍 第三步: 搜索测试...")
        search_queries = ["Entity", "0", "Test", "不存在"]
        for q in search_queries:
            try:
                results = repo.search_entities(q)
                print(f"    搜索 '{q}': 找到 {len(results)} 个结果 ✅")
            except Exception as e:
                print(f"    搜索 '{q}': ❌ {e}")
                errors.append(f"搜索 '{q}': {e}")
        
        # 测试统计
        print("\n📊 第四步: 统计和分析测试...")
        if graph_ids:
            test_id = graph_ids[0]
            try:
                stats = repo.get_graph_statistics(test_id)
                print(f"    统计信息: {stats} ✅")
            except Exception as e:
                print(f"    统计信息: ❌ {e}")
                errors.append(f"统计: {e}")
        
        # 混合操作测试（小并发）
        print("\n🔀 第五步: 混合操作测试...")
        ops_completed = 0
        
        def mix_worker(worker_id):
            nonlocal ops_completed
            for i in range(20):
                try:
                    op = random.choice(["read", "search", "stat"])
                    if op == "read":
                        if graph_ids:
                            repo.get_graph(random.choice(graph_ids))
                    elif op == "search":
                        repo.search_entities(f"Entity-{random.randint(0,9)}")
                    elif op == "stat":
                        if graph_ids:
                            repo.get_graph_statistics(random.choice(graph_ids))
                    ops_completed += 1
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {e}")
        
        threads = []
        for i in range(4):
            t = threading.Thread(target=mix_worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        print(f"    完成 {ops_completed} 次混合操作")
        
        # 删除测试
        print("\n🗑️  第六步: 删除测试...")
        deleted = 0
        for graph_id in graph_ids:
            try:
                repo.delete_graph(graph_id)
                deleted += 1
                print(f"    删除图谱 {graph_id}: ✅")
            except Exception as e:
                print(f"    删除图谱 {graph_id}: ❌ {e}")
                errors.append(f"删除 {graph_id}: {e}")
        
        print(f"\n    已删除 {deleted}/{len(graph_ids)} 个图谱")
        
        # 总结
        print("\n" + "=" * 80)
        print("📋 测试结果总结")
        print("=" * 80)
        
        if len(errors) == 0:
            print("\n🎉 太棒了！没有发现任何错误！")
            return 0
        else:
            print(f"\n⚠️  发现 {len(errors)} 个错误:")
            for i, err in enumerate(errors[:20]):
                print(f"    {i+1}. {err}")
            if len(errors) > 20:
                print(f"    ... 还有 {len(errors)-20} 个错误")
            return 1
            
    finally:
        print("\n" + "=" * 80)
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("🧹 测试清理完成")


if __name__ == "__main__":
    sys.exit(main())
