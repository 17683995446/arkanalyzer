#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 路径查找问题调试器
"""

import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "arkanalyzer"))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer


def debug_path_finding():
    """调试路径查找"""
    print("=" * 80)
    print("路径查找问题调试")
    print("=" * 80)

    # 创建测试图谱
    graph = KnowledgeGraph(graph_name="调试图谱")
    entities = []

    print("\n1. 创建实体:")
    for i in range(5):
        entity = Entity(entity_name=f"节点_{i}", entity_type="概念")
        entities.append(entity)
        graph.add_entity(entity)
        print(f"   实体 {i}: ID={entity.entity_id}, 名称={entity.entity_name}")

    print("\n2. 创建关系:")
    for i in range(4):
        relation = Relation(
            source_entity_id=entities[i].entity_id,
            target_entity_id=entities[i+1].entity_id,
            relation_type="连接"
        )
        graph.add_relation(relation)
        print(f"   关系 {i}: {entities[i].entity_name} ({entities[i].entity_id[:8]}...) -> {entities[i+1].entity_name} ({entities[i+1].entity_id[:8]}...)")

    print("\n3. 创建分析器:")
    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)

    print(f"   实体数量: {len(analyzer.entities)}")
    print(f"   关系数量: {len(analyzer.relations)}")
    print(f"   entity_map大小: {len(analyzer.entity_map)}")
    print(f"   adjacency_list大小: {len(analyzer.adjacency_list)}")
    print(f"   degree_map大小: {len(analyzer.degree_map)}")

    print("\n4. 邻接列表内容:")
    for node_id, neighbors in analyzer.adjacency_list.items():
        entity = analyzer.entity_map.get(node_id)
        entity_name = entity.entity_name if entity else "UNKNOWN"
        neighbor_names = []
        for n_id in neighbors:
            n_entity = analyzer.entity_map.get(n_id)
            neighbor_names.append(n_entity.entity_name if n_entity else "UNKNOWN")
        print(f"   {entity_name} ({node_id[:8]}...) -> {neighbor_names}")

    print(f"\n5. 尝试查找路径:")
    source_id = entities[0].entity_id
    target_id = entities[4].entity_id
    print(f"   源节点: {entities[0].entity_name} ({source_id[:8]}...)")
    print(f"   目标节点: {entities[4].entity_name} ({target_id[:8]}...)")

    try:
        path = analyzer.find_shortest_path(source_id, target_id)
        print(f"   查找结果: {path}")

        if path:
            print("   路径节点:")
            for node_id in path:
                entity = analyzer.entity_map.get(node_id)
                name = entity.entity_name if entity else "UNKNOWN"
                print(f"      - {name}")
        else:
            print("   ❌ 路径为None!")
    except Exception as e:
        print(f"   ❌ 异常: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())

    print("\n6. 尝试查找所有路径:")
    try:
        all_paths = analyzer.find_all_paths(source_id, target_id, max_depth=10)
        print(f"   找到 {len(all_paths)} 条路径")
        for i, path in enumerate(all_paths):
            print(f"   路径 {i+1}: {path}")
    except Exception as e:
        print(f"   ❌ 异常: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())


def debug_analyzer_initialization():
    """调试分析器初始化"""
    print("\n" + "=" * 80)
    print("分析器初始化调试")
    print("=" * 80)

    graph = KnowledgeGraph(graph_name="调试初始化")

    e1 = Entity(entity_name="A", entity_type="概念")
    e2 = Entity(entity_name="B", entity_type="概念")
    e3 = Entity(entity_name="C", entity_type="概念")
    graph.add_entity(e1)
    graph.add_entity(e2)
    graph.add_entity(e3)

    r1 = Relation(source_entity_id=e1.entity_id, target_entity_id=e2.entity_id, relation_type="相关")
    r2 = Relation(source_entity_id=e2.entity_id, target_entity_id=e3.entity_id, relation_type="相关")
    graph.add_relation(r1)
    graph.add_relation(r2)

    print("\n实体列表:")
    for e in graph.entities:
        print(f"   {e.entity_name}: {e.entity_id}")

    print("\n关系列表:")
    for r in graph.relations:
        print(f"   {r.source_entity_id} -> {r.target_entity_id}")

    print("\n创建分析器:")
    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)

    print(f"\nentity_map:")
    for id, entity in analyzer.entity_map.items():
        print(f"   {id}: {entity.entity_name}")

    print(f"\nadacency_list:")
    for id, neighbors in analyzer.adjacency_list.items():
        entity = analyzer.entity_map[id]
        neighbor_names = [analyzer.entity_map[n].entity_name for n in neighbors]
        print(f"   {entity.entity_name}: {neighbor_names}")

    print("\n尝试 A -> C 路径:")
    try:
        path = analyzer.find_shortest_path(e1.entity_id, e3.entity_id)
        print(f"   路径: {path}")

        if path:
            print(f"   路径名称: {[analyzer.entity_map[id].entity_name for id in path]}")
    except Exception as e:
        print(f"   异常: {str(e)}")


def main():
    debug_path_finding()
    debug_analyzer_initialization()


if __name__ == "__main__":
    main()
