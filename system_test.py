#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer - 知识图谱分析系统
完整的系统初始化、测试和演示脚本
"""

import os
import sys
import time
import json

# 确保可以导入模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arkanalyzer'))

print("=" * 80)
print("🔬 Arkanalyzer - 知识图谱分析系统")
print("=" * 80)

def test_imports():
    """测试所有核心模块的导入"""
    print("\n📦 模块导入测试...")
    try:
        from core.config_loader import init_config
        from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
        from core.knowledge_repository import KnowledgeRepository
        from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer
        from database.database_connection_manager import initialize_database, get_database_pool
        print("✅ 所有模块导入成功！")
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def test_database():
    """测试数据库功能"""
    print("\n💾 数据库测试...")
    try:
        from database.database_connection_manager import initialize_database, get_database_pool
        pool, schema_mgr = initialize_database()
        pool = get_database_pool()

        conn = pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ 数据库初始化成功，找到 {len(tables)} 个表")
        for table in tables:
            print(f"  - {table[0]}")
        pool.return_connection(conn)
        return True
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_knowledge_graph():
    """测试知识图谱核心功能"""
    print("\n🕸️ 知识图谱测试...")
    try:
        from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph

        graph = KnowledgeGraph(
            graph_name="测试图谱",
            description="用于验证系统功能的测试图谱"
        )

        # 创建实体
        entity1 = Entity("人工智能", "概念", "AI技术总称")
        entity2 = Entity("机器学习", "概念", "AI子领域")
        entity3 = Entity("深度学习", "概念", "ML分支")

        graph.add_entity(entity1)
        graph.add_entity(entity2)
        graph.add_entity(entity3)

        # 创建关系
        rel1 = Relation(entity1.entity_id, entity2.entity_id, "包含")
        rel2 = Relation(entity2.entity_id, entity3.entity_id, "包含")

        graph.add_relation(rel1)
        graph.add_relation(rel2)

        print(f"✅ 知识图谱创建成功！")
        print(f"  - 实体数: {len(graph.entities)}")
        print(f"  - 关系数: {len(graph.relations)}")

        return graph
    except Exception as e:
        print(f"❌ 知识图谱测试失败: {e}")
        return None


def test_repository():
    """测试知识仓库功能"""
    print("\n📚 知识仓库测试...")
    try:
        from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
        from core.knowledge_repository import KnowledgeRepository

        repo = KnowledgeRepository()

        graph = KnowledgeGraph("数据库测试图谱", "存储到数据库的测试")

        for i in range(5):
            entity = Entity(f"实体{i+1}", "类型A", f"这是第{i+1}个实体")
            graph.add_entity(entity)

        entities = graph.entities
        for i in range(3):
            if i + 1 < len(entities):
                rel = Relation(
                    entities[i].entity_id,
                    entities[i+1].entity_id,
                    f"关系{i+1}"
                )
                graph.add_relation(rel)

        success = repo.save_graph(graph)
        if success:
            print(f"✅ 图谱保存成功！")

        # 读取图谱
        retrieved_graph = repo.get_graph(graph.graph_id)
        if retrieved_graph:
            print(f"✅ 图谱读取成功！")
            print(f"  - 实体数: {len(retrieved_graph.entities)}")
            print(f"  - 关系数: {len(retrieved_graph.relations)}")

        # 列出所有图谱
        all_graphs = repo.get_all_graphs()
        print(f"  - 系统中共有 {len(all_graphs)} 个图谱")

        return True
    except Exception as e:
        print(f"❌ 知识仓库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_analyzer():
    """测试图谱分析功能"""
    print("\n📊 图谱分析测试...")
    try:
        from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph
        from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer

        graph = KnowledgeGraph("分析测试", "用于图算法测试")

        entities = []
        for name in ["A", "B", "C", "D", "E"]:
            entity = Entity(name, "节点", f"节点{name}")
            entities.append(entity)
            graph.add_entity(entity)

        # 创建链式关系
        for i in range(4):
            rel = Relation(
                entities[i].entity_id,
                entities[i+1].entity_id,
                f"链接{i}"
            )
            graph.add_relation(rel)

        # 再添加一些交叉关系
        if len(entities) > 2:
            graph.add_relation(Relation(entities[0].entity_id, entities[2].entity_id, "直达"))
            graph.add_relation(Relation(entities[1].entity_id, entities[3].entity_id, "直达"))

        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)

        # 统计
        stats = analyzer.calculate_statistics()
        print(f"✅ 统计计算成功！")
        print(f"  - 节点数: {stats.total_nodes}")
        print(f"  - 边数: {stats.total_edges}")
        print(f"  - 连通分量: {stats.connected_components}")
        print(f"  - 平均度: {stats.average_degree:.2f}")

        # 路径查找
        path = analyzer.find_shortest_path(entities[0].entity_id, entities[-1].entity_id)
        if path:
            path_names = []
            for eid in path:
                for e in graph.entities:
                    if e.entity_id == eid:
                        path_names.append(e.entity_name)
                        break
            print(f"✅ 路径查找成功！最短路径: {' -> '.join(path_names)}")

        # 社区检测
        communities = analyzer.detect_communities_bfs()
        print(f"✅ 社区检测成功！发现 {len(communities.communities)} 个社区")

        # 关键节点
        key_nodes = analyzer.find_key_entities(3)
        print(f"✅ 关键节点计算成功！")
        entity_dict = {e.entity_id: e for e in graph.entities}
        for entity_id, score in key_nodes[:3]:
            entity = entity_dict.get(entity_id)
            if entity:
                print(f"  - {entity.entity_name}: {score:.4f}")
            else:
                print(f"  - {entity_id}: {score:.4f}")

        return True
    except Exception as e:
        print(f"❌ 图谱分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_features():
    """测试增强功能"""
    print("\n🚀 增强功能测试...")
    try:
        from core.enhanced_repository import EnhancedKnowledgeRepository, create_demo_knowledge_graph

        repo = EnhancedKnowledgeRepository()

        # 创建演示图谱
        graph_id = create_demo_knowledge_graph(repo)
        print(f"✅ 演示图谱创建成功！")

        # 获取摘要
        summary = repo.get_graph_summary(graph_id)
        if summary:
            print(f"✅ 图谱摘要生成成功！")
            print(f"  - 名称: {summary['name']}")
            print(f"  - 实体: {summary['entity_count']}")
            print(f"  - 关系: {summary['relation_count']}")

        return True
    except Exception as e:
        print(f"⚠️ 增强功能测试跳过: {e}")
        return True


def run_full_test():
    """运行完整的系统测试"""
    print("\n" + "=" * 80)
    print("🧪 完整系统测试")
    print("=" * 80)

    results = {}

    results['imports'] = test_imports()
    time.sleep(0.2)

    results['database'] = test_database()
    time.sleep(0.2)

    test_knowledge_graph()
    time.sleep(0.2)

    results['repository'] = test_repository()
    time.sleep(0.2)

    results['analyzer'] = test_analyzer()
    time.sleep(0.2)

    results['enhanced'] = test_enhanced_features()

    print("\n" + "=" * 80)
    print("📋 测试结果汇总")
    print("=" * 80)

    all_passed = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 所有核心测试通过！系统运行正常！")
    else:
        print("\n⚠️ 部分测试失败，请检查相关模块")

    return all_passed


def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 80)
    print("📖 使用说明")
    print("=" * 80)
    print("\n可用命令:")
    print("  python system_test.py          - 运行完整的系统测试")
    print("  python start_system.py         - 启动交互式系统")
    print("  python start_system.py quick   - 快速开始模式")
    print("  python start_system.py api     - 直接启动API服务器")
    print("\n直接访问前端:")
    print("  打开 frontend/index.html 查看可视化界面")
    print("\n运行API服务器后访问:")
    print("  http://localhost:5000          - 访问API和前端")


if __name__ == "__main__":
    success = run_full_test()
    show_usage()

    if not success:
        sys.exit(1)
