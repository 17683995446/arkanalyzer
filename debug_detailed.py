#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更精确的调试
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer

def print_debug_info():
    """详细调试"""
    print("="*80)
    print("详细调试信息")
    print("="*80)
    
    # 测试Entity创建
    print("\n1. 测试Entity创建:")
    e1 = Entity("节点0", "概念")
    print(f"  e1.entity_id: {e1.entity_id}")
    print(f"  e1.entity_name: {e1.entity_name}")
    print(f"  e1.entity_type: {e1.entity_type}")
    
    # 用关键字参数创建
    e2 = Entity(entity_name="节点1", entity_type="概念")
    print(f"\n  e2.entity_id: {e2.entity_id}")
    print(f"  e2.entity_name: {e2.entity_name}")
    
    # 测试Relation创建
    print("\n2. 测试Relation创建:")
    rel = Relation(source_entity_id=e1.entity_id, target_entity_id=e2.entity_id, relation_type="连接")
    print(f"  rel.relation_id: {rel.relation_id}")
    print(f"  rel.source_entity_id: {rel.source_entity_id}")
    print(f"  rel.target_entity_id: {rel.target_entity_id}")
    print(f"  rel.relation_type: {rel.relation_type}")
    
    # 创建完整图谱并测试
    print("\n3. 创建完整图谱:")
    graph = KnowledgeGraph("调试图谱", "测试用")
    
    entities = []
    for i in range(5):
        e = Entity(entity_name=f"实体{i}", entity_type="概念")
        entities.append(e)
        graph.add_entity(e)
    
    for i in range(4):
        rel = Relation(
            source_entity_id=entities[i].entity_id,
            target_entity_id=entities[i+1].entity_id,
            relation_type="连接"
        )
        graph.add_relation(rel)
        print(f"  关系: {rel.source_entity_id} -> {rel.target_entity_id}")
    
    print(f"\n  实体数: {len(graph.entities)}")
    print(f"  关系数: {len(graph.relations)}")
    
    # 打印所有实体
    print("\n4. 所有实体:")
    for e in graph.entities:
        print(f"  {e.entity_name} - ID: {e.entity_id}")
    
    # 打印所有关系
    print("\n5. 所有关系:")
    for r in graph.relations:
        print(f"  {r.source_entity_id} -> {r.target_entity_id}, type: {r.relation_type}")
    
    # 构建分析器
    print("\n6. 构建分析器:")
    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
    
    print(f"  entity_map keys: {list(analyzer.entity_map.keys())}")
    print(f"  adjacency_list: {dict(analyzer.adjacency_list)}")
    
    # 查找路径
    print(f"\n7. 查找从 {entities[0].entity_name} 到 {entities[-1].entity_name} 的路径:")
    path = analyzer.find_shortest_path(entities[0].entity_id, entities[-1].entity_id)
    
    print(f"  结果: {path}")
    
    if path:
        print("\n  路径上的实体:")
        for node_id in path:
            for e in graph.entities:
                if e.entity_id == node_id:
                    print(f"    - {e.entity_name}")

if __name__ == "__main__":
    print_debug_info()
