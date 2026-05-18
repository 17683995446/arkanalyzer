#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 系统问题发现测试
轻量级测试，不依赖完整项目结构
"""
import sys
import os
import tempfile
import shutil
import json
from datetime import datetime
import random
import threading

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'arkanalyzer'))

from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
from core.knowledge_repository import KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
from database.database_connection_manager import (
    initialize_database,
    DatabaseConnectionConfig
)

class SystemIssue:
    """表示发现的问题"""
    def __init__(self, issue_type, description, details=None):
        self.issue_type = issue_type
        self.description = description
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

class SystemTester:
    """系统测试器"""
    
    def __init__(self):
        self.issues = []
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        config = DatabaseConnectionConfig(db_path=self.db_path)
        initialize_database(config)
        self.repository = KnowledgeRepository()
        print("="*80)
        print("Arkanalyzer 系统问题发现测试")
        print("="*80)
    
    def __del__(self):
        """清理"""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
    
    def log_issue(self, issue_type, description, details=None):
        """记录发现的问题"""
        issue = SystemIssue(issue_type, description, details)
        self.issues.append(issue)
        print(f"  ❌ 问题发现: {issue_type} - {description}")
    
    def test_entity_creation(self):
        """测试实体创建"""
        print("\n1. 测试实体创建")
        try:
            entity = Entity(
                entity_name="测试实体",
                entity_type="概念",
                description="这是一个测试实体",
                properties={"test": "value"}
            )
            if not entity.entity_id:
                self.log_issue("实体ID缺失", "创建的实体没有ID")
                return False
            print("  ✅ 实体创建正常")
            return True
        except Exception as e:
            self.log_issue("实体创建异常", str(e))
            return False
    
    def test_relation_creation(self):
        """测试关系创建"""
        print("\n2. 测试关系创建")
        try:
            e1 = Entity(entity_name="A", entity_type="概念")
            e2 = Entity(entity_name="B", entity_type="概念")
            rel = Relation(
                source_entity_id=e1.entity_id,
                target_entity_id=e2.entity_id,
                relation_type="连接"
            )
            if rel.relation_id is not None:
                print("  ✅ 关系创建正常")
                return True
            else:
                self.log_issue("关系ID缺失", "创建的关系没有ID")
                return False
        except Exception as e:
            self.log_issue("关系创建异常", str(e))
            return False
    
    def test_graph_save_load(self):
        """测试图谱保存和加载"""
        print("\n3. 测试图谱保存和加载")
        try:
            # 创建测试图谱
            graph = KnowledgeGraph(graph_name="测试图谱", description="用于测试的图谱")
            e1 = Entity(entity_name="实体1", entity_type="人物")
            e2 = Entity(entity_name="实体2", entity_type="地点")
            graph.add_entity(e1)
            graph.add_entity(e2)
            graph.add_relation(Relation(
                source_entity_id=e1.entity_id, 
                target_entity_id=e2.entity_id, 
                relation_type="相关"))
            
            # 保存
            save_result = self.repository.save_graph(graph)
            if not save_result:
                self.log_issue("保存失败", "save_graph返回False")
                return False
            
            # 读取
            loaded = self.repository.get_graph(graph.graph_id)
            if not loaded:
                self.log_issue("读取失败", "无法读取已保存的图谱")
                return False
            
            # 验证
            if len(loaded.entities) != 2:
                self.log_issue("实体丢失", f"期望2个实体，实际{len(loaded.entities)}")
                return False
            
            if len(loaded.relations) != 1:
                self.log_issue("关系丢失", f"期望1个关系，实际{len(loaded.relations)}")
                return False
            
            print(f"  ✅ 图谱保存和加载正常")
            return True
        except Exception as e:
            self.log_issue("图谱保存加载异常", str(e))
            import traceback
            traceback.print_exc()
            return False
    
    def test_path_finding(self):
        """测试路径查找"""
        print("\n4. 测试路径查找")
        try:
            graph = KnowledgeGraph(graph_name="路径测试", description="测试路径查找")
            entities = []
            for i in range(5):
                e = Entity(entity_name=f"节点{i}", entity_type="概念")
                entities.append(e)
                graph.add_entity(e)
            
            # 创建链式关系
            for i in range(4):
                graph.add_relation(Relation(
                    source_entity_id=entities[i].entity_id,
                    target_entity_id=entities[i+1].entity_id,
                    relation_type="连接"
                ))
            
            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
            
            # 查找路径
            path = analyzer.find_shortest_path(entities[0].entity_id, entities[-1].entity_id)
            
            if path is None:
                self.log_issue("路径查找失败", "无法找到存在的路径")
                return False
            
            if len(path) != 5:
                self.log_issue("路径长度错误", f"期望5个节点，实际{len(path)}")
                return False
            
            print(f"  ✅ 路径查找正常: {len(path)}个节点")
            return True
        except Exception as e:
            self.log_issue("路径查找异常", str(e))
            import traceback
            traceback.print_exc()
            return False
    
    def test_community_detection(self):
        """测试社区检测"""
        print("\n5. 测试社区检测")
        try:
            graph = KnowledgeGraph(graph_name="社区测试", description="测试社区检测")
            
            # 创建两个独立的社区
            community1 = [Entity(entity_name=f"C1N{i}", entity_type="概念") for i in range(3)]
            community2 = [Entity(entity_name=f"C2N{i}", entity_type="概念") for i in range(3)]
            
            for e in community1 + community2:
                graph.add_entity(e)
            
            # 社区1内部连接
            for i in range(2):
                graph.add_relation(Relation(
                    source_entity_id=community1[i].entity_id, 
                    target_entity_id=community1[i+1].entity_id,
                    relation_type="连接"))
            
            # 社区2内部连接
            for i in range(2):
                graph.add_relation(Relation(
                    source_entity_id=community2[i].entity_id, 
                    target_entity_id=community2[i+1].entity_id,
                    relation_type="连接"))
            
            analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
            
            result = analyzer.detect_communities_bfs()
            
            if not result.communities:
                self.log_issue("社区检测失败", "没有检测到社区")
                return False
            
            print(f"  ✅ 社区检测: 发现{len(result.communities)}个社区")
            return True
        except Exception as e:
            self.log_issue("社区检测异常", str(e))
            import traceback
            traceback.print_exc()
            return False
    
    def test_large_graph(self):
        """测试大图"""
        print("\n6. 测试中等规模图谱")
        try:
            graph = KnowledgeGraph(graph_name="大规模测试", description="测试性能")
            
            # 创建100个实体
            entities = []
            for i in range(100):
                entity = Entity(
                    entity_name=f"实体{i}", 
                    entity_type=random.choice(["人物", "地点", "组织", "概念"]))
                entities.append(entity)
                graph.add_entity(entity)
            
            # 创建200个关系
            for i in range(200):
                s = random.randint(0, 99)
                t = random.randint(0, 99)
                while t == s:
                    t = random.randint(0, 99)
                graph.add_relation(Relation(
                    source_entity_id=entities[s].entity_id, 
                    target_entity_id=entities[t].entity_id,
                    relation_type="相关"))
            
            # 保存
            save_start = datetime.now()
            result = self.repository.save_graph(graph)
            save_time = (datetime.now() - save_start).total_seconds()
            
            if not result:
                self.log_issue("大图保存失败", "无法保存中等规模图谱")
                return False
            
            # 读取
            load_start = datetime.now()
            loaded = self.repository.get_graph(graph.graph_id)
            load_time = (datetime.now() - load_start).total_seconds()
            
            if not loaded:
                self.log_issue("大图读取失败", "无法读取保存的中等规模图谱")
                return False
            
            print(f"  ✅ 中等规模图谱: 保存{save_time:.2f}秒, 读取{load_time:.2f}秒")
            return True
        except Exception as e:
            self.log_issue("大图处理异常", str(e))
            import traceback
            traceback.print_exc()
            return False
    
    def test_search(self):
        """测试搜索功能"""
        print("\n7. 测试实体搜索")
        try:
            graph = KnowledgeGraph(graph_name="搜索测试", description="测试搜索")
            
            search_terms = ["人工智能", "机器学习", "深度学习", "神经网络", "计算机视觉"]
            
            for term in search_terms:
                graph.add_entity(Entity(entity_name=term, entity_type="概念"))
            
            self.repository.save_graph(graph)
            
            # 搜索包含"学习"
            results = self.repository.search_entities("学习")
            
            found_names = [e.entity_name for e in results]
            
            if "机器学习" not in found_names:
                self.log_issue("搜索失败", "搜索'机器学习'")
                return False
            
            print(f"  ✅ 搜索功能: 找到{len(results)}个结果")
            return True
        except Exception as e:
            self.log_issue("搜索异常", str(e))
            return False
    
    def test_property_persistence(self):
        """测试属性持久化"""
        print("\n8. 测试复杂属性持久化")
        try:
            graph = KnowledgeGraph(graph_name="属性测试", description="测试复杂属性")
            
            complex_properties = {
                "number": 123,
                "string": "test",
                "list": [1,2,3],
                "nested": {"a": 1, "b": [2,3]},
                "chinese": "中文测试"
            }
            
            entity = Entity(
                entity_name="属性测试实体", 
                entity_type="概念", 
                properties=complex_properties)
            graph.add_entity(entity)
            
            self.repository.save_graph(graph)
            
            loaded = self.repository.get_graph(graph.graph_id)
            
            if not loaded or len(loaded.entities) == 0:
                self.log_issue("属性持久化失败", "无法读取保存的实体")
                return False
            
            loaded_entity = loaded.entities[0]
            
            if not loaded_entity.properties:
                self.log_issue("属性丢失", "保存的属性未被读取")
                return False
            
            print("  ✅ 属性持久化正常")
            return True
        except Exception as e:
            self.log_issue("属性持久化异常", str(e))
            return False
    
    def test_empty_graph(self):
        """测试空图谱"""
        print("\n9. 测试空图谱")
        try:
            graph = KnowledgeGraph(graph_name="空测试", description="这是一个空图谱")
            result = self.repository.save_graph(graph)
            if not result:
                self.log_issue("空图谱保存失败", "无法保存空图谱")
                return False
            
            loaded = self.repository.get_graph(graph.graph_id)
            if not loaded:
                self.log_issue("空图谱读取失败", "无法读取空图谱")
                return False
            
            print("  ✅ 空图谱处理正常")
            return True
        except Exception as e:
            self.log_issue("空图谱异常", str(e))
            return False
    
    def test_get_all_graphs(self):
        """测试获取所有图谱"""
        print("\n10. 测试获取所有图谱")
        try:
            # 创建多个图谱
            for i in range(5):
                g = KnowledgeGraph(graph_name=f"列表测试{i}", description=f"测试列表{i}")
                self.repository.save_graph(g)
            
            all_graphs = self.repository.get_all_graphs()
            
            if len(all_graphs) < 5:
                self.log_issue("图谱列表不完整", f"期望至少5个，实际{len(all_graphs)}")
                return False
            
            print(f"  ✅ 列表功能: {len(all_graphs)}个图谱")
            return True
        except Exception as e:
            self.log_issue("列表异常", str(e))
            return False
    
    def report(self):
        """生成问题报告"""
        print("\n" + "="*80)
        print("问题发现报告")
        print("="*80)
        
        if not self.issues:
            print("🎉 恭喜！没有发现问题！")
            return True
        else:
            print(f"⚠️ 发现{len(self.issues)}个问题:\n")
            for i, issue in enumerate(self.issues, 1):
                print(f"\n问题{i}:")
                print(f"类型: {issue.issue_type}")
                print(f"描述: {issue.description}")
                print(f"时间: {issue.timestamp}")
                if issue.details:
                    print(f"详情: {json.dumps(issue.details, ensure_ascii=False, indent=2)}")
            return False
    
    def run_all(self):
        """运行所有测试"""
        results = []
        
        results.append(self.test_entity_creation())
        results.append(self.test_relation_creation())
        results.append(self.test_graph_save_load())
        results.append(self.test_path_finding())
        results.append(self.test_community_detection())
        results.append(self.test_large_graph())
        results.append(self.test_search())
        results.append(self.test_property_persistence())
        results.append(self.test_empty_graph())
        results.append(self.test_get_all_graphs())
        
        passed = sum(1 for r in results if r)
        total = len(results)
        
        print(f"\n测试结果: {passed}/{total}通过")
        
        self.report()
        return passed == total

def main():
    tester = SystemTester()
    success = tester.run_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
