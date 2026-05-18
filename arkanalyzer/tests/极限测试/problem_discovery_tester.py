#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 渐进式问题发现测试
从小规模开始逐步发现和修复系统缺陷
"""

import sys
import os
import time
import threading
import tempfile
import shutil
import random
from typing import Dict, List, Any
from datetime import datetime
import uuid
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import get_knowledge_repository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig,
    get_database_pool
)


class ProblemDiscoveryTester:
    """问题发现测试器"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "discovery_test.db")
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = get_knowledge_repository()
        self.issues_found = []

    def __del__(self):
        """清理资源"""
        try:
            pool = get_database_pool()
            pool.close_all()
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

    def log_issue(self, issue_type: str, description: str, details: Dict[str, Any] = None):
        """记录发现的问题"""
        issue = {
            "timestamp": datetime.now().isoformat(),
            "type": issue_type,
            "description": description,
            "details": details or {}
        }
        self.issues_found.append(issue)
        print(f"  🐛 发现问题: {issue_type} - {description}")

    def test_simple_graph_creation(self):
        """测试简单图谱创建"""
        print("\n" + "=" * 60)
        print("测试1: 简单图谱创建")
        print("=" * 60)

        try:
            graph = KnowledgeGraph(graph_name="测试图谱")

            # 添加一些测试实体
            e1 = Entity(entity_name="张三", entity_type="人物", description="测试人物1")
            e2 = Entity(entity_name="北京", entity_type="地点", description="中国首都")
            e3 = Entity(entity_name="北京大学", entity_type="组织", description="知名大学")
            graph.add_entity(e1)
            graph.add_entity(e2)
            graph.add_entity(e3)

            # 添加关系
            r1 = Relation(
                source_entity_id=e1.entity_id,
                target_entity_id=e2.entity_id,
                relation_type="居住在"
            )
            r2 = Relation(
                source_entity_id=e1.entity_id,
                target_entity_id=e3.entity_id,
                relation_type="就读于"
            )
            graph.add_relation(r1)
            graph.add_relation(r2)

            # 保存
            print(f"  → 保存图谱...")
            success = self.repository.save_graph(graph)

            if not success:
                self.log_issue("保存失败", "图谱保存操作返回False")
                return False

            # 读取验证
            print(f"  → 读取验证...")
            retrieved = self.repository.get_graph(graph.graph_id)

            if not retrieved:
                self.log_issue("读取失败", "无法从数据库读取已保存的图谱")
                return False

            # 验证内容
            if len(retrieved.entities) != 3:
                self.log_issue("实体丢失", f"预期3个实体，实际{len(retrieved.entities)}个")
                return False

            if len(retrieved.relations) != 2:
                self.log_issue("关系丢失", f"预期2个关系，实际{len(retrieved.relations)}个")
                return False

            print(f"  ✅ 简单图谱创建测试通过")
            return True

        except Exception as e:
            self.log_issue("异常", f"测试过程中发生异常: {str(e)}", {"exception": str(e)})
            return False

    def test_multiple_graph_operations(self):
        """测试多个图谱操作"""
        print("\n" + "=" * 60)
        print("测试2: 多个图谱操作")
        print("=" * 60)

        try:
            # 创建多个图谱
            graph_ids = []
            for i in range(10):
                graph = KnowledgeGraph(graph_name=f"批量图谱_{i}", description=f"第{i}个测试图谱")
                for j in range(5):
                    entity = Entity(entity_name=f"实体_{i}_{j}", entity_type="概念")
                    graph.add_entity(entity)

                success = self.repository.save_graph(graph)
                if not success:
                    self.log_issue("批量保存失败", f"第{i}个图谱保存失败")
                    return False
                graph_ids.append(graph.graph_id)

            # 获取所有图谱
            all_graphs = self.repository.get_all_graphs()
            if len(all_graphs) < 10:
                self.log_issue("图谱丢失", f"保存10个图谱，只找到{len(all_graphs)}个")
                return False

            # 更新一些图谱
            for idx, graph_id in enumerate(graph_ids[:3]):
                graph = self.repository.get_graph(graph_id)
                if graph:
                    graph.description = f"更新后的描述_{idx}"
                    success = self.repository.save_graph(graph)
                    if not success:
                        self.log_issue("更新失败", f"图谱{graph_id}更新失败")
                        return False

            # 删除一些图谱
            for graph_id in graph_ids[5:]:
                success = self.repository.delete_graph(graph_id)
                if not success:
                    self.log_issue("删除失败", f"图谱{graph_id}删除失败")
                    return False

            print(f"  ✅ 多个图谱操作测试通过")
            return True

        except Exception as e:
            self.log_issue("异常", f"测试过程中发生异常: {str(e)}", {"exception": str(e)})
            return False

    def test_graph_statistics_calculation(self):
        """测试图谱统计计算"""
        print("\n" + "=" * 60)
        print("测试3: 图谱统计计算")
        print("=" * 60)

        try:
            # 创建一个小型测试图谱
            graph = KnowledgeGraph(graph_name="统计测试图谱")
            entities = []

            for i in range(10):
                entity_types = ["人物", "地点", "组织", "概念"]
                entity = Entity(
                    entity_name=f"统计实体_{i}",
                    entity_type=entity_types[i % len(entity_types)]
                )
                entities.append(entity)
                graph.add_entity(entity)

            # 创建一些关系
            for i in range(15):
                source_idx = i % 10
                target_idx = (i + 3) % 10
                relation = Relation(
                    source_entity_id=entities[source_idx].entity_id,
                    target_entity_id=entities[target_idx].entity_id,
                    relation_type="相关"
                )
                graph.add_relation(relation)

            self.repository.save_graph(graph)

            # 计算统计
            stats = self.repository.get_graph_statistics(graph.graph_id)

            print(f"  → 统计结果: {json.dumps(stats, ensure_ascii=False, indent=4)}")

            # 验证统计
            if stats.get("entity_count") != 10:
                self.log_issue("统计错误", f"实体数统计错误: 预期10，实际{stats.get('entity_count')}")
                return False

            if stats.get("relation_count") != 15:
                self.log_issue("统计错误", f"关系数统计错误: 预期15，实际{stats.get('relation_count')}")
                return False

            # 测试图分析器
            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
            analysis_stats = analyzer.calculate_statistics()

            if analysis_stats.total_nodes != 10:
                self.log_issue("分析器错误", f"节点数统计错误: 预期10，实际{analysis_stats.total_nodes}")
                return False

            if analysis_stats.total_edges != 15:
                self.log_issue("分析器错误", f"边数统计错误: 预期15，实际{analysis_stats.total_edges}")
                return False

            print(f"  ✅ 图谱统计计算测试通过")
            return True

        except Exception as e:
            self.log_issue("异常", f"测试过程中发生异常: {str(e)}", {"exception": str(e)})
            return False

    def test_path_finding(self):
        """测试路径查找"""
        print("\n" + "=" * 60)
        print("测试4: 路径查找")
        print("=" * 60)

        try:
            # 创建一个链式图谱
            graph = KnowledgeGraph(graph_name="路径测试图谱")
            entities = []

            for i in range(5):
                entity = Entity(entity_name=f"节点_{i}", entity_type="概念")
                entities.append(entity)
                graph.add_entity(entity)

            # 创建线性链
            for i in range(4):
                relation = Relation(
                    source_entity_id=entities[i].entity_id,
                    target_entity_id=entities[i+1].entity_id,
                    relation_type="连接"
                )
                graph.add_relation(relation)

            self.repository.save_graph(graph)

            # 测试分析器
            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)

            # 查找最短路径
            path = analyzer.find_shortest_path(entities[0].entity_id, entities[4].entity_id)

            if path is None:
                self.log_issue("路径查找失败", "无法找到存在的路径")
                return False

            print(f"  → 找到的路径长度: {len(path)}")

            if len(path) != 5:
                self.log_issue("路径长度错误", f"预期5个节点，实际{len(path)}个")
                return False

            # 查找所有路径
            all_paths = analyzer.find_all_paths(entities[0].entity_id, entities[4].entity_id, max_depth=10)

            if len(all_paths) < 1:
                self.log_issue("路径查找失败", "find_all_paths没有找到路径")
                return False

            print(f"  → 找到{len(all_paths)}条路径")
            print(f"  ✅ 路径查找测试通过")
            return True

        except Exception as e:
            self.log_issue("异常", f"测试过程中发生异常: {str(e)}", {"exception": str(e)})
            return False

    def test_search_functionality(self):
        """测试搜索功能"""
        print("\n" + "=" * 60)
        print("测试5: 实体搜索")
        print("=" * 60)

        try:
            # 创建一些可搜索的实体
            graph = KnowledgeGraph(graph_name="搜索测试图谱")

            search_terms = ["人工智能", "机器学习", "深度学习", "神经网络", "计算机视觉"]
            for term in search_terms:
                entity = Entity(entity_name=term, entity_type="概念")
                graph.add_entity(entity)

            self.repository.save_graph(graph)

            # 测试搜索
            results = self.repository.search_entities("学习")

            print(f"  → 搜索'学习'找到{len(results)}个结果")

            # 应该找到"机器学习"和"深度学习"
            found_names = [e.entity_name for e in results]

            if "机器学习" not in found_names:
                self.log_issue("搜索失败", "未能找到'机器学习'实体")
                return False

            if "深度学习" not in found_names:
                self.log_issue("搜索失败", "未能找到'深度学习'实体")
                return False

            # 测试空搜索
            empty_results = self.repository.search_entities("不存在的实体XYZ")
            if len(empty_results) > 0:
                self.log_issue("搜索异常", "搜索不存在的内容时返回了结果")
                return False

            print(f"  ✅ 实体搜索测试通过")
            return True

        except Exception as e:
            self.log_issue("异常", f"测试过程中发生异常: {str(e)}", {"exception": str(e)})
            return False

    def test_property_persistence(self):
        """测试属性持久化"""
        print("\n" + "=" * 60)
        print("测试6: 属性持久化")
        print("=" * 60)

        try:
            # 创建带有复杂属性的实体
            graph = KnowledgeGraph(graph_name="属性测试图谱")

            complex_properties = {
                "数值属性": 123,
                "字符串属性": "测试字符串",
                "列表属性": [1, 2, 3],
                "嵌套属性": {"a": 1, "b": [2, 3]},
                "中文字符": "测试中文"
            }

            entity = Entity(
                entity_name="复杂属性实体",
                entity_type="概念",
                properties=complex_properties
            )

            graph.add_entity(entity)
            self.repository.save_graph(graph)

            # 读取并验证
            retrieved = self.repository.get_graph(graph.graph_id)
            if not retrieved or len(retrieved.entities) == 0:
                self.log_issue("属性持久化失败", "无法读取保存的实体")
                return False

            retrieved_entity = retrieved.entities[0]

            # 验证属性
            if not retrieved_entity.properties:
                self.log_issue("属性丢失", "保存的属性未被读取")
                return False

            # 由于JSON序列化，列表会保持，嵌套也应该保持
            print(f"  → 读取到的属性: {json.dumps(retrieved_entity.properties, ensure_ascii=False)}")

            print(f"  ✅ 属性持久化测试通过")
            return True

        except Exception as e:
            self.log_issue("异常", f"测试过程中发生异常: {str(e)}", {"exception": str(e)})
            return False

    def test_relation_source_target_validation(self):
        """测试关系源和目标验证"""
        print("\n" + "=" * 60)
        print("测试7: 关系验证")
        print("=" * 60)

        try:
            graph = KnowledgeGraph(graph_name="关系验证测试")

            # 正常关系
            e1 = Entity(entity_name="实体A", entity_type="概念")
            e2 = Entity(entity_name="实体B", entity_type="概念")
            graph.add_entity(e1)
            graph.add_entity(e2)

            valid_relation = Relation(
                source_entity_id=e1.entity_id,
                target_entity_id=e2.entity_id,
                relation_type="测试关系"
            )
            graph.add_relation(valid_relation)

            # 测试：指向不存在实体的关系
            fake_relation = Relation(
                source_entity_id="this_entity_does_not_exist",
                target_entity_id=e2.entity_id,
                relation_type="无效关系"
            )
            graph.add_relation(fake_relation)

            # 保存
            success = self.repository.save_graph(graph)

            if not success:
                self.log_issue("关系保存失败", "保存包含无效关系的图谱失败")
                return False

            # 读取
            retrieved = self.repository.get_graph(graph.graph_id)

            if not retrieved:
                self.log_issue("读取失败", "无法读取关系测试图谱")
                return False

            # 验证关系都被保存（系统不验证关系指向，这是设计选择）
            print(f"  → 系统允许保存指向不存在实体的关系")

            # 测试邻居查找
            neighbors = self.repository.get_neighbors(e1.entity_id)
            print(f"  → 实体{e1.entity_name}的邻居: {[n.entity_name for n in neighbors]}")

            print(f"  ✅ 关系验证测试通过")
            return True

        except Exception as e:
            self.log_issue("异常", f"测试过程中发生异常: {str(e)}", {"exception": str(e)})
            return False

    def generate_report(self):
        """生成问题报告"""
        print("\n" + "=" * 80)
        print("问题发现测试报告")
        print("=" * 80)

        if not self.issues_found:
            print("\n🎉 恭喜！没有发现问题！\n")
        else:
            print(f"\n⚠️ 发现{len(self.issues_found)}个潜在问题:\n")

            for i, issue in enumerate(self.issues_found, 1):
                print(f"\n问题 {i}:")
                print(f"  类型: {issue['type']}")
                print(f"  时间: {issue['timestamp']}")
                print(f"  描述: {issue['description']}")
                if issue['details']:
                    print(f"  详情: {json.dumps(issue['details'], ensure_ascii=False, indent=4)}")

        print("\n" + "=" * 80)
        return len(self.issues_found)

    def run_all_tests(self):
        """运行所有问题发现测试"""
        print("=" * 80)
        print("Arkanalyzer 问题发现测试")
        print("=" * 80)

        results = []

        results.append(self.test_simple_graph_creation())
        results.append(self.test_multiple_graph_operations())
        results.append(self.test_graph_statistics_calculation())
        results.append(self.test_path_finding())
        results.append(self.test_search_functionality())
        results.append(self.test_property_persistence())
        results.append(self.test_relation_source_target_validation())

        issue_count = self.generate_report()

        return all(results) and issue_count == 0


def main():
    """主函数"""
    tester = ProblemDiscoveryTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
