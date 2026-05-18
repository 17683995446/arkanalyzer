#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer 系统启动脚本
启动后端API服务器
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import init_config, get_config
from core.knowledge_repository import get_knowledge_repository
from database.database_connection_manager import initialize_database
from api.app import create_app


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Arkanalyzer 知识图谱分析系统')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--config', default=None, help='配置文件路径')
    return parser.parse_args()


def initialize_system():
    """初始化系统"""
    print("=" * 80)
    print("🚀 Arkanalyzer 知识图谱分析系统启动中...")
    print("=" * 80)

    config = init_config()
    print(f"✅ 配置加载完成")

    initialize_database()
    print(f"✅ 数据库初始化完成")

    repository = get_knowledge_repository()
    print(f"✅ 知识仓库初始化完成")

    print(f"\n📊 系统统计:")
    graphs = repository.get_all_graphs()
    print(f"   - 图谱数量: {len(graphs)}")
    total_entities = sum(len(g.entities) for g in graphs)
    total_relations = sum(len(g.relations) for g in graphs)
    print(f"   - 实体总数: {total_entities}")
    print(f"   - 关系总数: {total_relations}")

    print("\n" + "=" * 80)
    print("系统初始化完成！")
    print("=" * 80)

    return config


def start_server(host='0.0.0.0', port=5000, debug=True):
    """启动服务器"""
    app = create_app()

    print(f"\n🌐 启动API服务器...")
    print(f"   地址: http://{host}:{port}")
    print(f"   API文档: http://{host}:{port}/api/health")
    print(f"\n按 Ctrl+C 停止服务器\n")

    app.run(host=host, port=port, debug=debug)


def main():
    """主函数"""
    args = parse_arguments()

    config = initialize_system()

    start_server(
        host=args.host,
        port=args.port,
        debug=args.debug or config.api_config.debug
    )


if __name__ == '__main__':
    main()
