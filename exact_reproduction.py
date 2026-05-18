#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确复现直接测试中的问题
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "arkanalyzer"))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer


def exact_reproduction():
    """精确复现直接测试中的测试4"""
    print("=" * 80)
    print("精确复现测试4")
    print("=" * 80)

    graph = KnowledgeGraph(graph_name="分析测试图谱")
    entities = []

    print("\n创建实体:")
    for i in range(10):
        entity = Entity(entity_name=f"分析节点_{i}", entity_type="概念")
        entities.append(entity)
        graph.add_entity(entity)
        print(f"  {i}: {entity.entity_name} - {entity.entity_id}")

    print("\n创建关系:")
    for i in range(8):
        relation = Relation(
            source_entity_id=entities[i].entity_id,
            target_entity_id=entities[i+1].entity_id,
            relation_type="连接"
        )
        graph.add_relation(relation)
        print(f"  {i}: {entities[i].entity_name} -> {entities[i+1].entity_name}")

    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)

    print("\n验证 entity_map:")
    for i, entity in enumerate(entities):
        if entity.entity_id not in analyzer.entity_map:
            print(f"  ❌ 实体 {entity.entity_name} 不在 entity_map 中!")

    print("\n邻接列表:")
    for entity_id, neighbors in analyzer.adjacency_list.items():
        entity = analyzer.entity_map[entity_id]
        neighbor_names = []
        for n_id in neighbors:
            n_entity = analyzer.entity_map.get(n_id)
            neighbor_names.append(n_entity.entity_name if n_entity else "UNKNOWN")
        print(f"  {entity.entity_name}: {neighbor_names}")

    print(f"\n查找路径: {entities[0].entity_name} -> {entities[9].entity_name}")

    source_id = entities[0].entity_id
    target_id = entities[9].entity_id

    print(f"源存在吗? {source_id in analyzer.entity_map}")
    print(f"目标存在吗? {target_id in analyzer.entity_map}")

    print("\n实体0的邻居:")
    for neighbor in analyzer.adjacency_list[source_id]:
        entity = analyzer.entity_map.get(neighbor)
        print(f"  - {entity.entity_name if entity else neighbor}")

    try:
        path = analyzer.find_shortest_path(source_id, target_id)
        print(f"\n路径查找结果: {path}")

        if path:
            print("路径节点:")
            for node_id in path:
                entity = analyzer.entity_map.get(node_id)
                name = entity.entity_name if entity else "UNKNOWN"
                print(f"  - {name}")

            print(f"\n✅ 成功找到路径，长度: {len(path)}")
        else:
            print("\n❌ 路径为 None")

    except Exception as e:
        print(f"\n❌ 异常: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())


def test_extreme_cases():
    """测试一些极端情况"""
    print("\n" + "=" * 80)
    print("极端情况测试")
    print("=" * 80)

    # 测试1: 孤立节点
    print("\n1. 孤立节点测试:")
    graph = KnowledgeGraph(graph_name="孤立测试")
    e1 = Entity(entity_name="孤立1", entity_type="概念")
    e2 = Entity(entity_name="孤立2", entity_type="概念")
    graph.add_entity(e1)
    graph.add_entity(e2)

    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
    path = analyzer.find_shortest_path(e1.entity_id, e2.entity_id)
    print(f"   路径: {path} (应该为 None)")

    # 测试2: 自身
    print("\n2. 自身路径测试:")
    path = analyzer.find_shortest_path(e1.entity_id, e1.entity_id)
    print(f"   路径: {path} (应该为 [e1_id])")

    # 测试3: 多跳
    print("\n3. 多跳测试:")
    graph = KnowledgeGraph(graph_name="多跳")
    entities = []
    for i in range(5):
        entity = Entity(entity_name=f"节点{i}", entity_type="概念")
        entities.append(entity)
        graph.add_entity(entity)

    for i in range(4):
        rel = Relation(
            source_entity_id=entities[i].entity_id,
            target_entity_id=entities[i+1].entity_id,
            relation_type="连接"
        )
        graph.add_relation(rel)

    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
    path = analyzer.find_shortest_path(entities[0].entity_id, entities[4].entity_id)
    print(f"   路径长度: {len(path) if path else 0} (应该为 5)")
    if path:
        print(f"   路径: {path}")


def main():
    exact_reproduction()
    test_extreme_cases()


if __name__ == "__main__":
    main()
