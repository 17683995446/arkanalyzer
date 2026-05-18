#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 知识图谱分析核心模块
提供图分析算法、路径查找、社区检测等高级分析功能
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import math


@dataclass
class GraphStatistics:
    """图统计信息"""
    total_nodes: int = 0
    total_edges: int = 0
    density: float = 0.0
    average_degree: float = 0.0
    max_degree: int = 0
    min_degree: int = 0
    isolated_nodes: int = 0
    connected_components: int = 0
    clustering_coefficient: float = 0.0


@dataclass
class PathAnalysisResult:
    """路径分析结果"""
    source_id: str
    target_id: str
    paths: List[List[str]]
    shortest_path_length: int
    all_paths_found: bool


@dataclass
class CommunityDetectionResult:
    """社区检测结果"""
    communities: List[List[str]]
    modularity: float
    algorithm_used: str


class KnowledgeGraphAnalyzer:
    """知识图谱分析器"""

    def __init__(self, entities: List[Any], relations: List[Any]):
        self.entities = entities
        self.relations = relations
        self.entity_map = {e.entity_id: e for e in entities}
        self.adjacency_list: Dict[str, Set[str]] = defaultdict(set)
        self.degree_map: Dict[str, int] = defaultdict(int)
        self._build_graph()

    def _build_graph(self):
        """构建图结构"""
        for relation in self.relations:
            self.adjacency_list[relation.source_entity_id].add(relation.target_entity_id)
            self.adjacency_list[relation.target_entity_id].add(relation.source_entity_id)
            self.degree_map[relation.source_entity_id] += 1
            self.degree_map[relation.target_entity_id] += 1

        for entity in self.entities:
            if entity.entity_id not in self.adjacency_list:
                self.adjacency_list[entity.entity_id] = set()
            if entity.entity_id not in self.degree_map:
                self.degree_map[entity.entity_id] = 0

    def calculate_statistics(self) -> GraphStatistics:
        """计算图统计信息"""
        stats = GraphStatistics()
        stats.total_nodes = len(self.entities)
        stats.total_edges = len(self.relations)

        if stats.total_nodes > 1:
            max_possible_edges = stats.total_nodes * (stats.total_nodes - 1) / 2
            stats.density = stats.total_edges / max_possible_edges if max_possible_edges > 0 else 0

        degrees = list(self.degree_map.values())
        if degrees:
            stats.average_degree = sum(degrees) / len(degrees)
            stats.max_degree = max(degrees)
            stats.min_degree = min(degrees)
            stats.isolated_nodes = sum(1 for d in degrees if d == 0)

        stats.connected_components = self._count_connected_components()
        stats.clustering_coefficient = self._calculate_clustering_coefficient()

        return stats

    def _count_connected_components(self) -> int:
        """计算连通分量数量"""
        visited = set()
        components = 0

        for entity in self.entities:
            if entity.entity_id not in visited:
                self._bfs_component(entity.entity_id, visited)
                components += 1

        return components

    def _bfs_component(self, start_id: str, visited: Set[str]):
        """BFS遍历连通分量"""
        queue = deque([start_id])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self.adjacency_list[current]:
                if neighbor not in visited:
                    queue.append(neighbor)

    def _calculate_clustering_coefficient(self) -> float:
        """计算聚类系数"""
        if not self.entities:
            return 0.0

        total_coefficient = 0.0
        node_count = 0

        for entity in self.entities:
            neighbors = list(self.adjacency_list[entity.entity_id])
            k = len(neighbors)

            if k < 2:
                continue

            edges_between_neighbors = 0
            for i in range(k):
                for j in range(i + 1, k):
                    if neighbors[j] in self.adjacency_list[neighbors[i]]:
                        edges_between_neighbors += 1

            possible_edges = k * (k - 1) / 2
            local_coefficient = edges_between_neighbors / possible_edges if possible_edges > 0 else 0
            total_coefficient += local_coefficient
            node_count += 1

        return total_coefficient / node_count if node_count > 0 else 0.0

    def find_shortest_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """使用BFS查找最短路径"""
        if source_id not in self.entity_map or target_id not in self.entity_map:
            return None

        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = deque([(source_id, [source_id])])

        while queue:
            current, path = queue.popleft()

            for neighbor in self.adjacency_list[current]:
                if neighbor == target_id:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def find_all_paths(self, source_id: str, target_id: str, max_depth: int = 5) -> List[List[str]]:
        """查找所有路径"""
        paths = []
        visited = set()

        def dfs(current: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current == target_id:
                paths.append(path.copy())
                return

            visited.add(current)
            for neighbor in self.adjacency_list[current]:
                if neighbor not in visited:
                    path.append(neighbor)
                    dfs(neighbor, path, depth + 1)
                    path.pop()

            visited.discard(current)

        dfs(source_id, [source_id], 0)
        return paths

    def analyze_path(self, source_id: str, target_id: str, max_depth: int = 5) -> PathAnalysisResult:
        """分析路径"""
        paths = self.find_all_paths(source_id, target_id, max_depth)
        shortest_length = min(len(p) for p in paths) if paths else 0

        return PathAnalysisResult(
            source_id=source_id,
            target_id=target_id,
            paths=paths,
            shortest_path_length=shortest_length,
            all_paths_found=shortest_length <= max_depth
        )

    def detect_communities_bfs(self) -> CommunityDetectionResult:
        """使用BFS进行社区检测"""
        visited = set()
        communities = []

        for entity in self.entities:
            if entity.entity_id not in visited:
                community = []
                queue = deque([entity.entity_id])

                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue

                    visited.add(current)
                    community.append(current)

                    for neighbor in self.adjacency_list[current]:
                        if neighbor not in visited:
                            queue.append(neighbor)

                if community:
                    communities.append(community)

        modularity = self._calculate_modularity(communities)

        return CommunityDetectionResult(
            communities=communities,
            modularity=modularity,
            algorithm_used="BFS"
        )

    def _calculate_modularity(self, communities: List[List[str]]) -> float:
        """计算模块度"""
        if not communities or not self.relations:
            return 0.0

        m = len(self.relations)
        if m == 0:
            return 0.0

        community_map = {}
        for i, community in enumerate(communities):
            for node_id in community:
                community_map[node_id] = i

        q = 0.0
        for relation in self.relations:
            source_comm = community_map.get(relation.source_entity_id, -1)
            target_comm = community_map.get(relation.target_entity_id, -1)

            if source_comm == target_comm:
                ki = self.degree_map.get(relation.source_entity_id, 0)
                kj = self.degree_map.get(relation.target_entity_id, 0)
                q += 1 - (ki * kj) / (2 * m)

        return q / (2 * m) if m > 0 else 0.0

    def calculate_node_importance(self) -> Dict[str, Dict[str, float]]:
        """计算节点重要性"""
        importance_scores = {}

        total_degree = sum(self.degree_map.values()) if self.degree_map else 1

        for entity in self.entities:
            entity_id = entity.entity_id
            degree = self.degree_map.get(entity_id, 0)

            neighbors = list(self.adjacency_list.get(entity_id, set()))
            neighbor_importance = sum(
                self.degree_map.get(n, 0) for n in neighbors
            ) / max(1, len(neighbors))

            importance_scores[entity_id] = {
                'degree_centrality': degree / max(1, len(self.entities) - 1),
                'normalized_degree': degree / max(1, total_degree),
                'neighbor_importance': neighbor_importance / max(1, len(self.entities)),
                'local_clustering': self._local_clustering(entity_id)
            }

        max_centrality = max(s['degree_centrality'] for s in importance_scores.values()) if importance_scores else 1
        for entity_id in importance_scores:
            importance_scores[entity_id]['importance_score'] = (
                importance_scores[entity_id]['degree_centrality'] / max_centrality if max_centrality > 0 else 0
            )

        return importance_scores

    def _local_clustering(self, node_id: str) -> float:
        """计算局部聚类系数"""
        neighbors = list(self.adjacency_list.get(node_id, set()))
        k = len(neighbors)

        if k < 2:
            return 0.0

        edges = 0
        for i in range(k):
            for j in range(i + 1, k):
                if neighbors[j] in self.adjacency_list.get(neighbors[i], set()):
                    edges += 1

        possible_edges = k * (k - 1) / 2
        return edges / possible_edges if possible_edges > 0 else 0.0

    def find_key_entities(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """找出关键实体"""
        importance_scores = self.calculate_node_importance()

        sorted_entities = sorted(
            importance_scores.items(),
            key=lambda x: x[1].get('importance_score', 0),
            reverse=True
        )

        return [(entity_id, scores['importance_score']) for entity_id, scores in sorted_entities[:top_n]]

    def find_bridges(self) -> List[Tuple[str, str]]:
        """查找桥接关系"""
        bridges = []

        for relation in self.relations:
            source = relation.source_entity_id
            target = relation.target_entity_id

            temp_neighbors = self.adjacency_list[source].copy()
            self.adjacency_list[source].discard(target)

            if self._count_connected_components() > 1:
                bridges.append((source, target))

            self.adjacency_list[source] = temp_neighbors

        return bridges

    def get_graph_summary(self) -> Dict[str, Any]:
        """获取图谱摘要"""
        stats = self.calculate_statistics()
        communities = self.detect_communities_bfs()
        key_entities = self.find_key_entities(5)
        bridges = self.find_bridges()

        return {
            'statistics': {
                'total_nodes': stats.total_nodes,
                'total_edges': stats.total_edges,
                'density': round(stats.density, 4),
                'average_degree': round(stats.average_degree, 2),
                'max_degree': stats.max_degree,
                'isolated_nodes': stats.isolated_nodes,
                'connected_components': stats.connected_components,
                'clustering_coefficient': round(stats.clustering_coefficient, 4)
            },
            'communities': {
                'count': len(communities.communities),
                'modularity': round(communities.modularity, 4),
                'algorithm': communities.algorithm_used,
                'details': communities.communities
            },
            'key_entities': [
                {'entity_id': eid, 'importance': round(score, 4)}
                for eid, score in key_entities
            ],
            'bridge_count': len(bridges)
        }


class VisualizationDataGenerator:
    """可视化数据生成器"""

    def __init__(self, analyzer: KnowledgeGraphAnalyzer):
        self.analyzer = analyzer

    def generate_force_directed_data(self) -> Dict[str, Any]:
        """生成力导向图数据"""
        nodes = []
        edges = []
        importance_scores = self.analyzer.calculate_node_importance()

        for entity in self.analyzer.entities:
            score = importance_scores.get(entity.entity_id, {}).get('importance_score', 0.5)
            size = 20 + score * 40

            color_map = {
                '人物': '#ff6b6b',
                '地点': '#4ecdc4',
                '组织': '#45b7d1',
                '事件': '#96ceb4',
                '概念': '#ffeaa7',
                '物体': '#dfe6e9',
                '时间': '#fd79a8',
                '自定义': '#a29bfe'
            }

            nodes.append({
                'id': entity.entity_id,
                'label': entity.entity_name,
                'type': entity.entity_type,
                'size': size,
                'color': color_map.get(entity.entity_type, '#a29bfe'),
                'description': entity.description,
                'importance': round(score, 4)
            })

        for relation in self.analyzer.relations:
            edges.append({
                'source': relation.source_entity_id,
                'target': relation.target_entity_id,
                'relation': relation.relation_type,
                'weight': relation.weight,
                'description': relation.description
            })

        return {
            'nodes': nodes,
            'edges': edges,
            'type': 'force_directed'
        }

    def generate_hierarchical_data(self) -> Dict[str, Any]:
        """生成分层图数据"""
        communities = self.analyzer.detect_communities_bfs()
        importance_scores = self.analyzer.calculate_node_importance()

        levels = {}
        for i, community in enumerate(communities.communities):
            for entity_id in community:
                importance = importance_scores.get(entity_id, {}).get('importance_score', 0)
                level = min(int(importance * 3), 2)
                if level not in levels:
                    levels[level] = []
                levels[level].append(entity_id)

        nodes = []
        edges = []

        for level, entity_ids in levels.items():
            for entity_id in entity_ids:
                entity = self.analyzer.entity_map.get(entity_id)
                if entity:
                    nodes.append({
                        'id': entity_id,
                        'label': entity.entity_name,
                        'level': level,
                        'group': level
                    })

        for relation in self.analyzer.relations:
            if relation.source_entity_id in self.analyzer.entity_map and \
               relation.target_entity_id in self.analyzer.entity_map:
                edges.append({
                    'source': relation.source_entity_id,
                    'target': relation.target_entity_id,
                    'relation': relation.relation_type
                })

        return {
            'nodes': nodes,
            'edges': edges,
            'type': 'hierarchical'
        }


def analyze_knowledge_graph(entities: List[Any], relations: List[Any]) -> Dict[str, Any]:
    """分析知识图谱的便捷函数"""
    analyzer = KnowledgeGraphAnalyzer(entities, relations)
    return analyzer.get_graph_summary()
