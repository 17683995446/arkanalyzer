#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON序列化问题验证测试
"""

import json
import sys
import tempfile
import shutil
import random

sys.path.insert(0, '/workspace/arkanalyzer')

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


def test_json_serialization():
    print("=" * 80)
    print("🔍 JSON序列化问题测试")
    print("=" * 80)
    
    temp_dir = tempfile.mkdtemp()
    db_path = f"{temp_dir}/json_test.db"
    config = DatabaseConnectionConfig(db_path=db_path)
    initialize_database(config)
    repo = KnowledgeRepository()
    
    all_passed = True
    
    try:
        # 测试1: 基本功能
        print("\n1️⃣  基本图谱测试...")
        graph = KnowledgeGraph(graph_name="Basic-Test", description="基本测试")
        entity = Entity(entity_name="Test-Entity", entity_type="概念")
        graph.add_entity(entity)
        repo.save_graph(graph)
        retrieved = repo.get_graph(graph.graph_id)
        assert retrieved is not None, "读取失败"
        print("   ✅ 基本图谱正常")
        
        # 测试2: 各种数据类型
        print("\n2️⃣  多种数据类型测试...")
        graph2 = KnowledgeGraph(graph_name="Data-Types")
        
        # 各种可序列化和不可序列化的类型
        test_props = {
            "string": "hello",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"key": "value"},
            "deep_dict": {"a": {"b": 2}},
        }
        
        # 不添加不可序列化的类型
        entity2 = Entity(
            entity_name="Data-Type-Test",
            entity_type="概念",
            properties=test_props,
            description="测试各种属性类型"
        )
        graph2.add_entity(entity2)
        
        # 尝试保存
        try:
            repo.save_graph(graph2)
            retrieved2 = repo.get_graph(graph2.graph_id)
            assert retrieved2 is not None
            print("   ✅ 标准数据类型正常")
        except Exception as e:
            print(f"   ❌ 数据类型测试失败: {e}")
            all_passed = False
        
        # 测试3: 长文本
        print("\n3️⃣  长文本测试...")
        graph3 = KnowledgeGraph(graph_name="Long-Text")
        long_text = "x" * 10000
        entity3 = Entity(
            entity_name="Long-Text-Test",
            entity_type="概念",
            description=long_text,
            properties={"long_str": long_text}
        )
        graph3.add_entity(entity3)
        
        try:
            repo.save_graph(graph3)
            retrieved3 = repo.get_graph(graph3.graph_id)
            assert retrieved3 is not None
            print("   ✅ 长文本正常")
        except Exception as e:
            print(f"   ❌ 长文本测试失败: {e}")
            all_passed = False
        
        # 测试4: 特殊字符
        print("\n4️⃣  特殊字符测试...")
        graph4 = KnowledgeGraph(graph_name="Special-Chars")
        special_entity = Entity(
            entity_name="测试实体！@#￥%",
            entity_type="概念",
            description="包含\n换行和\t制表符"
        )
        graph4.add_entity(special_entity)
        
        try:
            repo.save_graph(graph4)
            retrieved4 = repo.get_graph(graph4.graph_id)
            assert retrieved4 is not None
            print("   ✅ 特殊字符正常")
        except Exception as e:
            print(f"   ❌ 特殊字符测试失败: {e}")
            all_passed = False
        
        # 测试5: 大量图操作
        print("\n5️⃣  大量操作稳定性...")
        graphs_created = []
        for i in range(10):
            g = KnowledgeGraph(graph_name=f"Batch-Test-{i}")
            for j in range(5):
                e = Entity(entity_name=f"E-{i}-{j}", entity_type="概念")
                g.add_entity(e)
            repo.save_graph(g)
            graphs_created.append(g.graph_id)
        
        print(f"   ✅ 成功创建 {len(graphs_created)} 个图谱")
        
        # 清理
        for gid in graphs_created:
            repo.delete_graph(gid)
        
        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 JSON序列化测试全部通过！")
            return 0
        else:
            print("⚠️  JSON序列化测试发现问题！")
            return 1
            
    finally:
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(test_json_serialization())
