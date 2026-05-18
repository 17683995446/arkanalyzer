#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 增强版 - 高级功能模块
提供更强大的图谱管理和分析功能
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from core.knowledge_repository import KnowledgeRepository


class EnhancedKnowledgeRepository(KnowledgeRepository):
    """增强版知识仓库"""

    def __init__(self):
        super().__init__()

    def get_graph_summary(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """获取图谱摘要"""
        graph = self.get_graph(graph_id)
        if not graph:
            return None

        stats = self.get_graph_statistics(graph_id)

        # 获取实体类型分布
        entity_types = defaultdict(int)
        for entity in graph.entities:
            entity_types[entity.entity_type] += 1

        # 获取关系类型分布
        relation_types = defaultdict(int)
        for rel in graph.relations:
            relation_types[rel.relation_type] += 1

        return {
            "graph_id": graph_id,
            "name": graph.graph_name,
            "description": graph.description,
            "created_at": graph.created_at.isoformat(),
            "updated_at": graph.updated_at.isoformat(),
            "version": graph.version,
            "entity_count": stats.get("entity_count", 0),
            "relation_count": stats.get("relation_count", 0),
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "top_entities": self._get_top_entities(graph),
        }

    def _get_top_entities(self, graph: KnowledgeGraph, top_n: int = 5) -> List[Dict[str, Any]]:
        """获取最重要的实体"""
        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        importance = analyzer.calculate_node_importance()

        sorted_entities = sorted(
            graph.entities,
            key=lambda e: importance.get(e.entity_id, {}).get('importance_score', 0),
            reverse=True
        )[:top_n]

        return [
            {
                "id": e.entity_id,
                "name": e.entity_name,
                "type": e.entity_type,
                "importance": importance.get(e.entity_id, {}).get('importance_score', 0)
            }
            for e in sorted_entities
        ]

    def find_related_entities(self, entity_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """查找相关实体"""
        from database.database_connection_manager import get_database_connection

        with get_database_connection() as conn:
            cursor = conn.cursor()

            # 获取实体详情
            entity = self.get_entity_by_id(entity_id)
            if not entity:
                return {"error": "Entity not found"}

            # 查找关系
            relations = []
            neighbors = defaultdict(int)

            cursor.execute("""
                SELECT source_entity_id, target_entity_id, relation_type, weight
                FROM relations
                WHERE source_entity_id = ? OR target_entity_id = ?
            """, (entity_id, entity_id))

            for row in cursor.fetchall():
                source, target, rel_type, weight = row
                relations.append({
                    "source": source,
                    "target": target,
                    "type": rel_type,
                    "weight": weight
                })

                if source != entity_id:
                    neighbors[source] += 1
                if target != entity_id:
                    neighbors[target] += 1

            # 获取邻居详情
            neighbor_entities = []
            for neighbor_id in neighbors:
                ne = self.get_entity_by_id(neighbor_id)
                if ne:
                    neighbor_entities.append({
                        "id": ne.entity_id,
                        "name": ne.entity_name,
                        "type": ne.entity_type,
                        "connections": neighbors[neighbor_id]
                    })

            return {
                "entity": {
                    "id": entity.entity_id,
                    "name": entity.entity_name,
                    "type": entity.entity_type,
                    "description": entity.description
                },
                "relations": relations,
                "neighbors": neighbor_entities
            }

    def merge_graphs(self, graph_ids: List[str], merged_name: str,
                     merged_description: str = "") -> Optional[KnowledgeGraph]:
        """合并多个图谱"""
        if not graph_ids:
            return None

        merged = KnowledgeGraph(
            graph_name=merged_name,
            description=merged_description
        )

        entity_map = {}  # name -> new_entity

        for graph_id in graph_ids:
            graph = self.get_graph(graph_id)
            if graph:
                # 合并实体
                for entity in graph.entities:
                    if entity.entity_name not in entity_map:
                        new_entity = Entity(
                            entity_name=entity.entity_name,
                            entity_type=entity.entity_type,
                            properties=entity.properties,
                            description=entity.description
                        )
                        entity_map[entity.entity_name] = new_entity
                        merged.add_entity(new_entity)
                    # else: 可以添加属性合并逻辑

                # 合并关系
                for relation in graph.relations:
                    source_graph = self.get_entity_by_id(relation.source_entity_id)
                    target_graph = self.get_entity_by_id(relation.target_entity_id)

                    if source_graph and target_graph:
                        source = entity_map.get(source_graph.entity_name)
                        target = entity_map.get(target_graph.entity_name)

                        if source and target:
                            new_rel = Relation(
                                source_entity_id=source.entity_id,
                                target_entity_id=target.entity_id,
                                relation_type=relation.relation_type,
                                weight=relation.weight,
                                properties=relation.properties
                            )
                            merged.add_relation(new_rel)

        if merged.entities:
            self.save_graph(merged)
            return merged

        return None

    def export_graph(self, graph_id: str, format: str = "json") -> Optional[str]:
        """导出图谱"""
        graph = self.get_graph(graph_id)
        if not graph:
            return None

        if format == "json":
            return json.dumps(graph.to_dict(), ensure_ascii=False, indent=2)
        elif format == "graphml":
            return self._export_to_graphml(graph)
        else:
            return None

    def _export_to_graphml(self, graph: KnowledgeGraph) -> str:
        """导出为GraphML格式"""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
                 '  <graph id="G" edgedefault="undirected">']

        # 添加节点
        for entity in graph.entities:
            lines.append(f'    <node id="{entity.entity_id}">')
            lines.append(f'      <data key="name">{entity.entity_name}</data>')
            lines.append(f'      <data key="type">{entity.entity_type}</data>')
            lines.append(f'    </node>')

        # 添加边
        for relation in graph.relations:
            lines.append(f'    <edge source="{relation.source_entity_id}" target="{relation.target_entity_id}">')
            lines.append(f'      <data key="label">{relation.relation_type}</data>')
            lines.append(f'      <data key="weight">{relation.weight}</data>')
            lines.append(f'    </edge>')

        lines.append('  </graph>')
        lines.append('</graphml>')
        return '\n'.join(lines)


class AdvancedKnowledgeGraphAnalyzer(KnowledgeGraphAnalyzer):
    """高级图谱分析器"""

    def __init__(self, entities: List[Entity], relations: List[Relation]):
        super().__init__(entities, relations)

    def get_centrality_measures(self) -> Dict[str, Dict[str, float]]:
        """获取各种中心性度量"""
        measures = {}

        # 计算度中心性
        degree_centrality = {}
        max_degree = max(self.degree_map.values(), default=1)

        for entity_id, degree in self.degree_map.items():
            degree_centrality[entity_id] = degree / max_degree

        measures["degree"] = degree_centrality

        # 计算中介中心性（简化版）
        betweenness = self._calculate_betweenness()
        measures["betweenness"] = betweenness

        return measures

    def _calculate_betweenness(self) -> Dict[str, float]:
        """计算中介中心性（简化版）"""
        betweenness = {e.entity_id: 0 for e in self.entities}

        # 对每个节点对，找最短路径，计数节点在中间的次数
        for i, source in enumerate(self.entities):
            for j, target in enumerate(self.entities):
                if i < j:
                    path = self.find_shortest_path(source.entity_id, target.entity_id)
                    if path and len(path) > 2:
                        # 排除首尾
                        for node in path[1:-1]:
                            betweenness[node] += 1

        # 标准化
        max_between = max(betweenness.values(), default=1)
        for node in betweenness:
            betweenness[node] /= max_between

        return betweenness

    def detect_communities_modularity(self) -> List[List[str]]:
        """基于模块度的社区检测（简化版）"""
        # 这是一个简化的实现，实际可以使用更复杂的算法
        # 这里我们使用简单的连通分量
        communities = self.detect_communities_bfs().communities
        return communities

    def get_advanced_analytics(self) -> Dict[str, Any]:
        """获取高级分析"""
        stats = self.calculate_statistics()
        centrality = self.get_centrality_measures()
        communities = self.detect_communities_modularity()
        key_entities = self.find_key_entities(10)

        # 计算实体类型分布
        type_distribution = defaultdict(int)
        for entity in self.entities:
            type_distribution[entity.entity_type] += 1

        # 计算关系类型分布
        rel_type_distribution = defaultdict(int)
        for relation in self.relations:
            rel_type_distribution[relation.relation_type] += 1

        return {
            "basic_statistics": {
                "node_count": stats.total_nodes,
                "edge_count": stats.total_edges,
                "density": stats.density,
                "avg_degree": stats.average_degree,
                "connected_components": stats.connected_components
            },
            "entity_type_distribution": dict(type_distribution),
            "relation_type_distribution": dict(rel_type_distribution),
            "centrality": centrality,
            "communities": communities,
            "communities_count": len(communities),
            "key_entities": key_entities
        }


def create_demo_knowledge_graph(repo: EnhancedKnowledgeRepository) -> str:
    """创建一个演示知识图谱"""
    print("创建演示知识图谱...")

    graph = KnowledgeGraph(
        graph_name="人工智能知识图谱",
        description="展示人工智能领域的知识结构"
    )

    entities_data = [
        ("人工智能", "概念", "人工智能（AI）是模拟、扩展人类智能的技术"),
        ("机器学习", "概念", "机器学习是AI的子领域，让计算机从数据中学习"),
        ("深度学习", "概念", "深度学习是机器学习的分支，基于神经网络"),
        ("神经网络", "概念", "受生物神经元网络启发的计算模型"),
        ("Transformer", "概念", "Transformer架构在2017年提出，革新了NLP"),
        ("自然语言处理", "概念", "使计算机理解、处理人类语言的技术"),
        ("计算机视觉", "概念", "使计算机从图像或视频中获取信息的技术"),
        ("GPT", "物体", "OpenAI开发的大语言模型系列"),
        ("GPT-4", "物体", "GPT系列的第四代模型"),
        ("OpenAI", "组织", "美国AI研究公司"),
        ("Claude", "物体", "Anthropic开发的AI助手"),
        ("Anthropic", "组织", "AI安全和研究公司"),
        ("监督学习", "概念", "使用标注数据训练模型的机器学习方法"),
        ("强化学习", "概念", "通过与环境交互学习的机器学习方法"),
    ]

    entities = []
    for name, etype, desc in entities_data:
        entity = Entity(
            entity_name=name,
            entity_type=etype,
            description=desc
        )
        entities.append(entity)
        graph.add_entity(entity)

    # 关系数据 (source_idx, target_idx, relation_type)
    relations_data = [
        (0, 1, "包含"),
        (1, 2, "包含"),
        (2, 3, "基于"),
        (2, 4, "使用"),
        (4, 5, "应用"),
        (2, 6, "应用"),
        (9, 7, "开发"),
        (7, 8, "包含"),
        (8, 4, "基于"),
        (11, 10, "开发"),
        (1, 12, "包含"),
        (1, 13, "包含"),
    ]

    for source_idx, target_idx, rel_type in relations_data:
        relation = Relation(
            source_entity_id=entities[source_idx].entity_id,
            target_entity_id=entities[target_idx].entity_id,
            relation_type=rel_type
        )
        graph.add_relation(relation)

    repo.save_graph(graph)
    print(f"演示图谱已创建！包含 {len(entities)} 个实体，{len(relations_data)} 个关系。")
    return graph.graph_id


def analyze_demo_graph(repo: EnhancedKnowledgeRepository, graph_id: str):
    """分析演示图谱"""
    print("\n分析演示图谱...")

    summary = repo.get_graph_summary(graph_id)
    if summary:
        print(f"\n图谱摘要:")
        print(f"  名称: {summary['name']}")
        print(f"  实体: {summary['entity_count']}")
        print(f"  关系: {summary['relation_count']}")
        print(f"  版本: {summary['version']}")

        print(f"\n关键实体:")
        for entity in summary.get("top_entities", []):
            print(f"  - {entity['name']} ({entity['type']})")

    graph = repo.get_graph(graph_id)
    if graph:
        analyzer = AdvancedKnowledgeGraphAnalyzer(graph.entities, graph.relations)
        analytics = analyzer.get_advanced_analytics()

        print(f"\n高级分析:")
        print(f"  连通分量: {analytics['basic_statistics']['connected_components']}")
        print(f"  社区数: {analytics['communities_count']}")
        print(f"  密度: {analytics['basic_statistics']['density']:.4f}")

        print(f"\n实体类型分布:")
        for etype, count in analytics['entity_type_distribution'].items():
            print(f"  {etype}: {count}")


def main():
    """主函数"""
    print("=" * 80)
    print("Arkanalyzer 增强系统")
    print("=" * 80)

    from database.database_connection_manager import initialize_database
    initialize_database()

    repo = EnhancedKnowledgeRepository()

    # 创建演示数据
    graph_id = create_demo_knowledge_graph(repo)

    # 分析演示数据
    analyze_demo_graph(repo, graph_id)

    print("\n" + "=" * 80)
    print("增强系统初始化完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
