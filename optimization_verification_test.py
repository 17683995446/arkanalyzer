#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化效果验证测试 - 对比优化前后的性能
"""

import os
import sys
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph


def main():
    print("="*80)
    print("⚡ 优化效果验证测试")
    print("="*80)
    
    test_sizes = [1000, 5000, 10000, 25000, 50000]
    
    for num_entities in test_sizes:
        print(f"\n📊 测试规模: {num_entities} 实体")
        
        # 创建测试图谱
        graph = KnowledgeGraph(graph_name=f"PerfTest_{num_entities}")
        
        for i in range(num_entities):
            entity = Entity(entity_name=f"Entity_{i}", entity_type="概念")
            graph.add_entity(entity)
            
        for i in range(num_entities * 3):
            if len(graph.entities) >= 2:
                s = random.randint(0, len(graph.entities)-1)
                t = random.randint(0, len(graph.entities)-1)
                while t == s:
                    t = random.randint(0, len(graph.entities)-1)
                graph.add_relation(Relation(
                    source_entity_id=graph.entities[s].entity_id,
                    target_entity_id=graph.entities[t].entity_id,
                    relation_type="相关"
                ))
        
        # 测试1: 单个实体查找
        target = graph.entities[-1].entity_id
        start = time.time()
        for _ in range(10000):
            graph.get_entity_by_id(target)
        single_time = time.time() - start
        print(f"  单个查找(10000次): {single_time:.4f}s ({single_time/10000*1000000:.2f}μs/次)")
        
        # 测试2: 邻居查找
        center = graph.entities[0].entity_id
        start = time.time()
        for _ in range(1000):
            graph.get_neighbors(center)
        neighbor_time = time.time() - start
        print(f"  邻居查找(1000次): {neighbor_time:.4f}s ({neighbor_time/1000*1000:.2f}ms/次)")
        
        # 验证邻居数量
        neighbors = graph.get_neighbors(center)
        print(f"  邻居数量: {len(neighbors)}")
        
        # 测试3: 多次查找不同实体
        test_ids = [graph.entities[i].entity_id for i in random.sample(range(num_entities), min(1000, num_entities))]
        start = time.time()
        for eid in test_ids * 10:
            graph.get_entity_by_id(eid)
        multi_time = time.time() - start
        print(f"  多样查找(10x{len(test_ids)}次): {multi_time:.4f}s")
        
    print("\n" + "="*80)
    print("✅ 优化验证完成！")
    print("="*80)


if __name__ == "__main__":
    main()
