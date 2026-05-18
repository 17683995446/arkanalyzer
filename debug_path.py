#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径查找问题调试
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer

def debug_path_finding():
    """调试路径查找"""
    print("="*80)
    print("调试路径查找问题")
    print("="*80)
    
    graph = KnowledgeGraph("路径测试", "测试路径查找")
    entities = []
    
    for i in range(5):
        e = Entity(f"节点{i}", "概念")
        entities.append(e)
        graph.add_entity(e)
        print(f"添加实体: {e.entity_name} (ID: {e.entity_id})")
    
    # 创建链式关系
    print("\n创建关系:")
    for i in range(4):
        rel = Relation(
            entities[i].entity_id,
            entities[i+1].entity_id,
            "连接"
        )
        graph.add_relation(rel)
        print(f"{entities[i].entity_name} -> {entities[i+1].entity_name}")
    
    print(f"\n实体总数: {len(graph.entities)}")
    print(f"关系总数: {len(graph.relations)}")
    
    analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
    
    print(f"\n分析器初始化后:")
    print(f"entity_map: {list(analyzer.entity_map.keys())}")
    print(f"adjacency_list: {analyzer.adjacency_list}")
    
    print(f"\n查找从 {entities[0].entity_name} 到 {entities[-1].entity_name} 的路径...")
    
    path = analyzer.find_shortest_path(
        entities[0].entity_id, 
        entities[-1].entity_id
    )
    
    print(f"结果路径: {path}")
    
    if path:
        path_names = []
        for node_id in path:
            for e in graph.entities:
                if e.entity_id == node_id:
                    path_names.append(e.entity_name)
        print(f"实体名称: {' -> '.join(path_names)}")
    else:
        print("没有找到路径！")
        
        # 手动检查连通性
        print("\n手动检查图结构:")
        print("Adjacency List:")
        for k, v in analyzer.adjacency_list.items():
            for e in graph.entities:
                if e.entity_id == k:
                    name = e.entity_name
                    break
            else:
                name = k
            neighbors = []
            for n in v:
                for e in graph.entities:
                    if e.entity_id == n:
                        neighbors.append(e.entity_name)
                        break
                else:
                    neighbors.append(n)
            print(f"  {name}: {neighbors}")
    
    return path is not None

if __name__ == "__main__":
    debug_path_finding()
