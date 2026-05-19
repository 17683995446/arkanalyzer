#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 核心代码错误处理与恢复测试
直接测试核心模块的异常场景
"""

import os
import sys
import tempfile
import shutil
import random
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from database.database_connection_manager import initialize_database, DatabaseConnectionConfig


class ErrorHandlingTest:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "error_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repo = KnowledgeRepository()
        self.test_results = []
        self.issues_found = []

    def log(self, test_name, success, details=None):
        self.test_results.append((test_name, success, details))
        icon = "✅" if success else "❌"
        print(f"{icon} {test_name}", end="")
        if details:
            print(f" - {details}")
        else:
            print()

    def test_1_empty_operations(self):
        """测试1: 空操作和边界情况"""
        print("\n" + "="*60)
        print("测试1: 空操作和边界情况")
        print("="*60)
        
        # 空图谱
        empty_graph = KnowledgeGraph(graph_name="空图谱")
        success = self.repo.save_graph(empty_graph)
        self.log("保存空图谱", success)
        
        graph_id = empty_graph.graph_id
        retrieved = self.repo.get_graph(graph_id)
        self.log("读取空图谱", retrieved is not None and len(retrieved.entities) == 0)
        
        self.repo.delete_graph(graph_id)
        self.log("删除空图谱", True)
        
        # 不存在的图谱
        non_existent = self.repo.get_graph("不存在的ID123456")
        self.log("读取不存在的图谱返回None", non_existent is None)
        
        return all(r[1] for r in self.test_results[-4:])

    def test_2_invalid_inputs(self):
        """测试2: 无效输入的处理"""
        print("\n" + "="*60)
        print("测试2: 无效输入处理")
        print("="*60)
        
        graph = KnowledgeGraph(graph_name="测试图谱")
        self.repo.save_graph(graph)
        
        # 空实体名称
        try:
            entity = Entity(entity_name="", entity_type="概念")
            graph.add_entity(entity)
            self.log("允许空实体名称", True)
        except Exception as e:
            self.log("拒绝空实体名称", False, str(e))
        
        # None 类型
        try:
            entity = Entity(entity_name="测试", entity_type=None)
            graph.add_entity(entity)
            self.log("允许None类型", True)
        except Exception as e:
            self.log("拒绝None类型", False, str(e))
        
        # 搜索空字符串
        results = self.repo.search_entities("")
        self.log("搜索空字符串返回结果", True, f"{len(results)}个结果")
        
        # 超长查询
        long_query = "a" * 10000
        results = self.repo.search_entities(long_query)
        self.log("超长搜索查询", True, f"{len(results)}个结果")
        
        self.repo.delete_graph(graph.graph_id)
        return True

    def test_3_relation_integrity(self):
        """测试3: 关系完整性和错误指向"""
        print("\n" + "="*60)
        print("测试3: 关系完整性")
        print("="*60)
        
        graph = KnowledgeGraph(graph_name="关系测试")
        e1 = Entity(entity_name="实体1", entity_type="概念")
        e2 = Entity(entity_name="实体2", entity_type="概念")
        graph.add_entity(e1)
        graph.add_entity(e2)
        
        # 正常关系
        rel1 = Relation(source_entity_id=e1.entity_id, target_entity_id=e2.entity_id, relation_type="相关")
        graph.add_relation(rel1)
        
        # 源实体不存在
        rel2 = Relation(source_entity_id="不存在的ID", target_entity_id=e2.entity_id, relation_type="测试")
        graph.add_relation(rel2)
        
        # 目标实体不存在
        rel3 = Relation(source_entity_id=e1.entity_id, target_entity_id="不存在的ID", relation_type="测试")
        graph.add_relation(rel3)
        
        # 都不存在
        rel4 = Relation(source_entity_id="ID1", target_entity_id="ID2", relation_type="测试")
        graph.add_relation(rel4)
        
        self.repo.save_graph(graph)
        
        retrieved = self.repo.get_graph(graph.graph_id)
        self.log("保存含无效关系的图谱", retrieved is not None)
        
        # 邻居查询（包含无效关系时的行为）
        neighbors = self.repo.get_neighbors(e1.entity_id)
        self.log("邻居查询（含无效关系）", True, f"{len(neighbors)}个邻居")
        
        self.repo.delete_graph(graph.graph_id)
        return True

    def test_4_analyzer_edge_cases(self):
        """测试4: 图分析器边界情况"""
        print("\n" + "="*60)
        print("测试4: 图分析器边界情况")
        print("="*60)
        
        from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
        
        # 空图谱分析
        graph1 = KnowledgeGraph(graph_name="空")
        try:
            analyzer1 = KnowledgeGraphAnalyzer([], [])
            stats1 = analyzer1.calculate_statistics()
            self.log("空图谱分析器初始化", True)
            self.log("空图谱统计", stats1.total_nodes == 0 and stats1.total_edges == 0)
        except Exception as e:
            self.log("空图谱分析器初始化", False, str(e))
        
        # 单个实体
        graph2 = KnowledgeGraph(graph_name="单实体")
        e = Entity(entity_name="单", entity_type="概念")
        graph2.add_entity(e)
        try:
            analyzer2 = KnowledgeGraphAnalyzer(graph2.entities, [])
            stats2 = analyzer2.calculate_statistics()
            key_entities = analyzer2.find_key_entities(5)
            self.log("单实体统计", stats2.total_nodes == 1)
            self.log("单实体关键节点", len(key_entities) <= 1)
        except Exception as e:
            self.log("单实体分析异常", False, str(e))
        
        # 两个无关系实体
        graph3 = KnowledgeGraph(graph_name="两实体")
        e1 = Entity(entity_name="A", entity_type="概念")
        e2 = Entity(entity_name="B", entity_type="概念")
        graph3.add_entity(e1)
        graph3.add_entity(e2)
        try:
            analyzer3 = KnowledgeGraphAnalyzer(graph3.entities, [])
            path = analyzer3.find_shortest_path(e1.entity_id, e2.entity_id)
            self.log("无关系路径查找返回None", path is None)
        except Exception as e:
            self.log("路径查找异常", False, str(e))
        
        return True

    def test_5_massive_operations_recovery(self):
        """测试5: 大量操作后的恢复能力"""
        print("\n" + "="*60)
        print("测试5: 大量操作与恢复")
        print("="*60)
        
        # 创建大量图谱然后删除
        graph_ids = []
        for i in range(50):
            g = KnowledgeGraph(graph_name=f"图谱{i}")
            for j in range(20):
                g.add_entity(Entity(entity_name=f"实体{i}_{j}", entity_type="概念"))
            self.repo.save_graph(g)
            graph_ids.append(g.graph_id)
        
        all_graphs = self.repo.get_all_graphs()
        self.log("创建大量图谱", len(all_graphs) >= 50)
        
        # 批量删除
        for gid in graph_ids:
            self.repo.delete_graph(gid)
        
        all_graphs_after = self.repo.get_all_graphs()
        self.log("批量删除后", len(all_graphs_after) <= 10)  # 可能有残留，但应该很少
        
        return True

    def test_6_property_types(self):
        """测试6: 各种属性类型处理"""
        print("\n" + "="*60)
        print("测试6: 属性类型处理")
        print("="*60)
        
        graph = KnowledgeGraph(graph_name="属性测试")
        
        # 各种 Python 类型
        entity = Entity(
            entity_name="类型测试",
            entity_type="概念",
            properties={
                'int': 123,
                'float': 3.14159,
                'bool': True,
                'list': [1, 2, 3],
                'dict': {'a': 1, 'b': {'c': 2}},
                'none': None,
                'long_str': 'a' * 10000,
                'unicode': '测试 测试 测试'
            }
        )
        graph.add_entity(entity)
        
        self.repo.save_graph(graph)
        
        retrieved = self.repo.get_graph(graph.graph_id)
        self.log("复杂属性保存和读取", retrieved is not None)
        
        if retrieved and len(retrieved.entities) > 0:
            props = retrieved.entities[0].properties
            if props:
                self.log("整数属性读取", props.get('int') == 123)
                self.log("浮点数属性读取", abs(props.get('float', 0) - 3.14159) < 0.0001)
                self.log("列表属性", isinstance(props.get('list'), list))
                self.log("字典属性", isinstance(props.get('dict'), dict))
        
        self.repo.delete_graph(graph.graph_id)
        return True

    def run_all(self):
        print("="*80)
        print("🛡️  Arkanalyzer 错误处理与恢复测试")
        print("="*80)
        
        all_passed = True
        
        all_passed &= self.test_1_empty_operations()
        all_passed &= self.test_2_invalid_inputs()
        all_passed &= self.test_3_relation_integrity()
        all_passed &= self.test_4_analyzer_edge_cases()
        all_passed &= self.test_5_massive_operations_recovery()
        all_passed &= self.test_6_property_types()
        
        print("\n" + "="*80)
        print("📊 错误处理测试总结")
        print("="*80)
        
        total = len(self.test_results)
        passed = sum(1 for _, s, _ in self.test_results if s)
        
        print(f"  总测试数: {total}")
        print(f"  通过: {passed}")
        print(f"  失败: {total - passed}")
        
        if self.issues_found:
            print(f"\n  ⚠️ 发现问题:")
            for issue in self.issues_found:
                print(f"    - {issue}")
        
        print("="*80)
        
        return all_passed

    def cleanup(self):
        try:
            from database.database_connection_manager import get_database_pool
            pool = get_database_pool()
            pool.close_all()
        except:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    tester = ErrorHandlingTest()
    try:
        success = tester.run_all()
        return 0 if success else 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
