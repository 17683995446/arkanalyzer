#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 完整系统启动器
整合所有功能的一站式解决方案
"""

import os
import sys
import json
import webbrowser
from datetime import datetime
from pathlib import Path
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_loader import init_config
from core.knowledge_graph_core import Entity, Relation, KnowledgeGraph, KnowledgeGraphManager
from core.knowledge_repository import KnowledgeRepository
from core.enhanced_repository import EnhancedKnowledgeRepository, create_demo_knowledge_graph
from core.llm_connector import LLMConnector
from database.database_connection_manager import initialize_database
from api.app import create_app


class ArkanalyzerSystem:
    """Arkanalyzer主系统"""

    def __init__(self):
        self._initialized = False

    def initialize(self):
        """初始化系统"""
        print("=" * 80)
        print("Arkanalyzer 知识图谱分析系统")
        print("=" * 80)

        print("\n[1/4] 初始化配置...")
        config = init_config()

        print("\n[2/4] 初始化数据库...")
        initialize_database()

        print("\n[3/4] 初始化组件...")
        self.repository = EnhancedKnowledgeRepository()
        self.manager = KnowledgeGraphManager()

        try:
            self.llm_connector = LLMConnector(api_key="REDACTED_API_KEY")
            llm_status = "✓"
        except Exception as e:
            llm_status = f"✗ ({str(e)})"

        print(f"\n[4/4] 系统检查...")
        print(f"   配置: ✓")
        print(f"   数据库: ✓")
        print(f"   LLM服务: {llm_status}")

        self._initialized = True
        print("\n✓ 系统初始化完成！")
        return True

    def show_dashboard(self):
        """显示仪表盘信息"""
        print("\n" + "=" * 80)
        print("系统概览")
        print("=" * 80)

        all_graphs = self.repository.get_all_graphs()
        total_entities = sum(len(g.entities) for g in all_graphs)
        total_relations = sum(len(g.relations) for g in all_graphs)

        print(f"\n📊 系统统计:")
        print(f"   知识图谱: {len(all_graphs)}")
        print(f"   实体总数: {total_entities}")
        print(f"   关系总数: {total_relations}")

        if all_graphs:
            print(f"\n📁 图谱列表:")
            for graph in all_graphs[:5]:
                print(f"   - {graph.graph_name} ({len(graph.entities)} 实体)")
            if len(all_graphs) > 5:
                print(f"   ...还有 {len(all_graphs) - 5} 个图谱")

        return {"graphs": len(all_graphs), "entities": total_entities, "relations": total_relations}

    def create_sample_graph(self):
        """创建示例图谱"""
        print("\n" + "=" * 80)
        print("创建示例数据")
        print("=" * 80)

        try:
            graph_id = create_demo_knowledge_graph(self.repository)

            print(f"\n✓ 示例图谱已创建！")
            return graph_id
        except Exception as e:
            print(f"\n✗ 创建失败: {str(e)}")
            return None

    def analyze_graph(self, graph_id: str = None):
        """分析图谱"""
        if not graph_id:
            graphs = self.repository.get_all_graphs()
            if graphs:
                graph_id = graphs[0].graph_id
            else:
                print("\n没有可分析的图谱！")
                return

        print("\n" + "=" * 80)
        print("图谱分析")
        print("=" * 80)

        summary = self.repository.get_graph_summary(graph_id)
        if summary:
            print(f"\n📋 图谱: {summary['name']}")
            print(f"   描述: {summary['description']}")
            print(f"   版本: {summary['version']}")
            print(f"\n📊 统计:")
            print(f"   实体: {summary['entity_count']}")
            print(f"   关系: {summary['relation_count']}")

            print(f"\n🏷️ 实体类型分布:")
            for etype, count in summary.get('entity_types', {}).items():
                print(f"   {etype}: {count}")

            print(f"\n⭐ 关键实体:")
            for entity in summary.get('top_entities', []):
                print(f"   - {entity['name']}")

    def run_interactive_mode(self):
        """运行交互模式"""
        print("\n" + "=" * 80)
        print("交互式模式")
        print("=" * 80)

        print("\n请选择操作:")
        print("1. 查看系统概览")
        print("2. 创建示例数据")
        print("3. 分析图谱")
        print("4. 管理图谱")
        print("5. 启动API服务器")
        print("0. 退出")

        while True:
            choice = input("\n请输入选项 (0-5): ").strip()

            if choice == "1":
                self.show_dashboard()
            elif choice == "2":
                self.create_sample_graph()
            elif choice == "3":
                self.analyze_graph()
            elif choice == "4":
                self.manage_graphs()
            elif choice == "5":
                self.start_api_server()
            elif choice == "0":
                print("\n再见！")
                break
            else:
                print("\n无效选项！")

    def manage_graphs(self):
        """图谱管理"""
        graphs = self.repository.get_all_graphs()

        if not graphs:
            print("\n没有图谱！创建一个吧。")
            return

        print("\n" + "=" * 80)
        print("图谱管理")
        print("=" * 80)

        for i, graph in enumerate(graphs, 1):
            print(f"{i}. {graph.graph_name} ({len(graph.entities)} 实体)")

        print("\n0. 返回")

        choice = input("\n选择图谱或返回 (0): ").strip()

        if choice == "0":
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(graphs):
                graph = graphs[idx]
                self.manage_single_graph(graph)
        except ValueError:
            print("无效输入！")

    def manage_single_graph(self, graph: KnowledgeGraph):
        """管理单个图谱"""
        print(f"\n操作: {graph.graph_name}")
        print("1. 查看详情")
        print("2. 分析")
        print("3. 删除")
        print("0. 返回")

        choice = input("\n选择操作 (0-3): ").strip()

        if choice == "1":
            self.analyze_graph(graph.graph_id)
        elif choice == "2":
            self.analyze_graph(graph.graph_id)
        elif choice == "3":
            confirm = input("确认删除？(y/n): ").lower()
            if confirm == "y":
                self.repository.delete_graph(graph.graph_id)
                print("删除成功！")
        elif choice == "0":
            return

    def start_api_server(self):
        """启动API服务器"""
        print("\n" + "=" * 80)
        print("启动 API 服务器")
        print("=" * 80)

        try:
            app = create_app()
            print("\n✓ API服务器准备就绪")
            print("🌐 访问 http://localhost:5000")
            print("\n按 Ctrl+C 停止服务器")

            # 尝试打开浏览器
            try:
                time.sleep(1.5)
                webbrowser.open('http://localhost:5000')
            except:
                pass

            app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        except Exception as e:
            print(f"\n✗ 启动失败: {str(e)}")
            print("\n提示: 如果5000端口被占用，可以使用端口5001")

    def run_quick_start(self):
        """快速开始"""
        print("\n" + "=" * 80)
        print("Arkanalyzer 快速开始")
        print("=" * 80)

        print("\n这个演示将:")
        print("1. 初始化系统")
        print("2. 创建示例图谱")
        print("3. 展示分析功能")

        input("\n按 Enter 继续...")

        self.initialize()
        self.create_sample_graph()
        self.show_dashboard()

        graph = self.repository.get_all_graphs()
        if graph:
            self.analyze_graph(graph[0].graph_id)

        print("\n" + "=" * 80)
        print("完成！")
        print("\n接下来可以:")
        print("- 运行 'python start_system.py' 使用交互模式")
        print("- 运行 'python run_api_server.py' 启动API服务器")
        print("- 打开 'frontend/index.html' 查看可视化界面")
        print("=" * 80)


def main():
    """主函数"""
    system = ArkanalyzerSystem()

    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            system.run_quick_start()
        elif sys.argv[1] == "api":
            system.initialize()
            system.start_api_server()
    else:
        if system.initialize():
            system.show_dashboard()
            system.run_interactive_mode()


if __name__ == "__main__":
    main()
