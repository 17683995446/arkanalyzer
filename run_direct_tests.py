#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 直接问题发现测试
在项目根目录直接发现和修复问题
"""

import sys
import os
import time
import random
import json
from datetime import datetime
import uuid
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "arkanalyzer"))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph, KnowledgeGraphManager
from core.knowledge_repository import KnowledgeRepository, get_knowledge_repository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig,
    get_database_pool
)


class DirectTester:
    """直接问题测试器"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "direct_test.db")
        self.issues = []

    def __del__(self):
        try:
            pool = get_database_pool()
            pool.close_all()
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

    def log_issue(self, test_name: str, description: str, error_detail: str = None):
        """记录发现的问题"""
        issue = {
            "test": test_name,
            "description": description,
            "error": error_detail,
            "timestamp": datetime.now().isoformat()
        }
        self.issues.append(issue)
        print(f"[❌] {test_name}: {description}")

    def log_pass(self, test_name: str, detail: str = ""):
        """记录通过的测试"""
        print(f"[✅] {test_name}: {detail}")

    def run_test_1_basic_save_and_load(self):
        """测试1: 基础保存和加载"""
        test_name = "基础保存和加载"
        try:
            config = DatabaseConnectionConfig(db_path=self.db_path)
            initialize_database(config)

            repo = get_knowledge_repository()

            graph = KnowledgeGraph(graph_name="测试图谱")
            e1 = Entity(entity_name="测试实体1", entity_type="概念")
            e2 = Entity(entity_name="测试实体2", entity_type="人物")
            graph.add_entity(e1)
            graph.add_entity(e2)

            rel = Relation(
                source_entity_id=e1.entity_id,
                target_entity_id=e2.entity_id,
                relation_type="相关"
            )
            graph.add_relation(rel)

            success = repo.save_graph(graph)

            if not success:
                self.log_issue(test_name, "save_graph返回False")
                return False

            retrieved = repo.get_graph(graph.graph_id)

            if not retrieved:
                self.log_issue(test_name, "无法读取已保存的图谱")
                return False

            if len(retrieved.entities) != 2:
                self.log_issue(test_name, f"实体数错误，期望2，实际{len(retrieved.entities)}")
                return False

            if len(retrieved.relations) != 1:
                self.log_issue(test_name, f"关系数错误，期望1，实际{len(retrieved.relations)}")
                return False

            self.log_pass(test_name, f"保存并读取了2个实体和1个关系")
            return True

        except Exception as e:
            self.log_issue(test_name, f"异常: {str(e)}", str(e))
            return False

    def run_test_2_version_increment(self):
        """测试2: 版本递增"""
        test_name = "版本递增"
        try:
            config = DatabaseConnectionConfig(db_path=self.db_path)
            initialize_database(config)

            repo = get_knowledge_repository()

            graph = KnowledgeGraph(graph_name="版本测试图谱")
            repo.save_graph(graph)

            retrieved1 = repo.get_graph(graph.graph_id)
            version1 = retrieved1.version

            retrieved1.description = "更新了描述"
            repo.save_graph(retrieved1)

            retrieved2 = repo.get_graph(graph.graph_id)
            version2 = retrieved2.version

            if version2 <= version1:
                self.log_issue(test_name, f"版本没有递增: {version1} -> {version2}")
                return False

            self.log_pass(test_name, f"版本正确递增: {version1} -> {version2}")
            return True

        except Exception as e:
            self.log_issue(test_name, f"异常: {str(e)}", str(e))
            return False

    def run_test_3_search(self):
        """测试3: 搜索功能"""
        test_name = "搜索功能"
        try:
            config = DatabaseConnectionConfig(db_path=self.db_path)
            initialize_database(config)

            repo = get_knowledge_repository()

            graph = KnowledgeGraph(graph_name="搜索测试图谱")
            for name in ["苹果", "香蕉", "橙子", "苹果派"]:
                entity = Entity(entity_name=name, entity_type="概念")
                graph.add_entity(entity)

            repo.save_graph(graph)

            results = repo.search_entities("苹果")

            if len(results) < 2:
                self.log_issue(test_name, f"搜索'苹果'找到结果不足，实际{len(results)}个")
                return False

            self.log_pass(test_name, f"搜索功能正常，找到{len(results)}个结果")
            return True

        except Exception as e:
            self.log_issue(test_name, f"异常: {str(e)}", str(e))
            return False

    def run_test_4_graph_analysis(self):
        """测试4: 图谱分析"""
        test_name = "图谱分析"
        try:
            graph = KnowledgeGraph(graph_name="分析测试图谱")
            entities = []

            for i in range(10):
                entity = Entity(entity_name=f"分析节点_{i}", entity_type="概念")
                entities.append(entity)
                graph.add_entity(entity)

            for i in range(8):
                relation = Relation(
                    source_entity_id=entities[i].entity_id,
                    target_entity_id=entities[i+1].entity_id,
                    relation_type="连接"
                )
                graph.add_relation(relation)

            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)

            stats = analyzer.calculate_statistics()

            if stats.total_nodes != 10:
                self.log_issue(test_name, f"节点数错误: 期望10，实际{stats.total_nodes}")
                return False

            if stats.total_edges != 8:
                self.log_issue(test_name, f"边数错误: 期望8，实际{stats.total_edges}")
                return False

            path = analyzer.find_shortest_path(entities[0].entity_id, entities[9].entity_id)

            if not path:
                self.log_issue(test_name, "路径查找失败")
                return False

            self.log_pass(test_name, f"分析功能正常，路径长度: {len(path)}")
            return True

        except Exception as e:
            self.log_issue(test_name, f"异常: {str(e)}", str(e))
            return False

    def run_test_5_multiple_graphs(self):
        """测试5: 多个图谱管理"""
        test_name = "多个图谱管理"
        try:
            config = DatabaseConnectionConfig(db_path=self.db_path)
            initialize_database(config)

            repo = get_knowledge_repository()

            # 清空可能存在的旧数据
            old_graphs = repo.get_all_graphs()
            for g in old_graphs:
                repo.delete_graph(g.graph_id)

            # 创建新图谱
            for i in range(5):
                graph = KnowledgeGraph(graph_name=f"批量图谱_{i}")
                for j in range(3):
                    entity = Entity(entity_name=f"批量实体_{i}_{j}", entity_type="概念")
                    graph.add_entity(entity)
                repo.save_graph(graph)

            all_graphs = repo.get_all_graphs()

            if len(all_graphs) != 5:
                self.log_issue(test_name, f"图谱数量错误: 期望5，实际{len(all_graphs)}")
                return False

            # 删除一个
            if all_graphs:
                repo.delete_graph(all_graphs[0].graph_id)

            remaining = repo.get_all_graphs()
            if len(remaining) != 4:
                self.log_issue(test_name, f"删除后数量错误: 期望4，实际{len(remaining)}")
                return False

            self.log_pass(test_name, "多图谱管理功能正常")
            return True

        except Exception as e:
            self.log_issue(test_name, f"异常: {str(e)}", str(e))
            return False

    def run_test_6_properties_persistence(self):
        """测试6: 属性持久化"""
        test_name = "属性持久化"
        try:
            config = DatabaseConnectionConfig(db_path=self.db_path)
            initialize_database(config)

            repo = get_knowledge_repository()

            graph = KnowledgeGraph(graph_name="属性测试图谱")

            test_props = {
                "number": 123,
                "string": "测试字符串",
                "list": [1, 2, 3],
                "nested": {"a": 1, "b": [4, 5, 6]}
            }

            entity = Entity(
                entity_name="属性测试实体",
                entity_type="概念",
                properties=test_props
            )

            graph.add_entity(entity)
            repo.save_graph(graph)

            retrieved = repo.get_graph(graph.graph_id)
            entity_retrieved = retrieved.entities[0]

            if not entity_retrieved.properties:
                self.log_issue(test_name, "属性没有被持久化")
                return False

            # 由于JSON序列化，元组会变成列表，但数值应该保持
            if entity_retrieved.properties.get("number") != 123:
                self.log_issue(test_name, "数值属性丢失或错误")
                return False

            self.log_pass(test_name, "属性持久化功能正常")
            return True

        except Exception as e:
            self.log_issue(test_name, f"异常: {str(e)}", str(e))
            return False

    def run_test_7_statistics(self):
        """测试7: 统计功能"""
        test_name = "统计功能"
        try:
            config = DatabaseConnectionConfig(db_path=self.db_path)
            initialize_database(config)

            repo = get_knowledge_repository()

            graph = KnowledgeGraph(graph_name="统计测试图谱")

            entity_types = ["人物", "地点", "组织", "概念", "事件"]
            for i in range(20):
                entity = Entity(
                    entity_name=f"统计实体_{i}",
                    entity_type=entity_types[i % 5]
                )
                graph.add_entity(entity)

            for i in range(15):
                relation = Relation(
                    source_entity_id=graph.entities[i % 15].entity_id,
                    target_entity_id=graph.entities[(i + 1) % 15].entity_id,
                    relation_type="相关"
                )
                graph.add_relation(relation)

            repo.save_graph(graph)
            stats = repo.get_graph_statistics(graph.graph_id)

            if stats.get("entity_count") != 20:
                self.log_issue(test_name, f"实体统计错误: 期望20，实际{stats.get('entity_count')}")
                return False

            if stats.get("relation_count") != 15:
                self.log_issue(test_name, f"关系统计错误: 期望15，实际{stats.get('relation_count')}")
                return False

            self.log_pass(test_name, "统计功能正常")
            return True

        except Exception as e:
            self.log_issue(test_name, f"异常: {str(e)}", str(e))
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("Arkanalyzer 直接问题发现测试")
        print("=" * 80)

        all_tests = [
            self.run_test_1_basic_save_and_load,
            self.run_test_2_version_increment,
            self.run_test_3_search,
            self.run_test_4_graph_analysis,
            self.run_test_5_multiple_graphs,
            self.run_test_6_properties_persistence,
            self.run_test_7_statistics
        ]

        passed = 0

        for test in all_tests:
            # 每个测试用新的数据库实例
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                os.makedirs(self.temp_dir, exist_ok=True)
                time.sleep(0.01)  # 确保文件系统操作完成
                if test():
                    passed += 1
            except Exception as e:
                self.log_issue("测试框架", f"测试异常: {str(e)}")

        print("\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)
        print(f"总计: {len(all_tests)} | 通过: {passed} | 失败: {len(all_tests) - passed}")

        if self.issues:
            print("\n发现的问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n{i}. {issue['test']}: {issue['description']}")
                if issue.get('error'):
                    print(f"   详情: {issue['error']}")
        else:
            print("\n🎉 完美！没有发现问题！")

        return len(self.issues) == 0


def main():
    """主函数"""
    tester = DirectTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
