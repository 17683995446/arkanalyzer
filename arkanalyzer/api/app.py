#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arkanalyzer Flask API 应用主入口模块
提供RESTful API接口，整合所有核心功能模块
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import init_config, get_config
from core.knowledge_graph_core import KnowledgeGraph, Entity, Relation, KnowledgeGraphManager
from core.knowledge_extractor import KnowledgeExtractor, GraphAnalyzer
from core.knowledge_repository import get_knowledge_repository, KnowledgeRepository
from core.knowledge_graph_analyzer import KnowledgeGraphAnalyzer, VisualizationDataGenerator, analyze_knowledge_graph
from core.llm_connector import create_llm_connector
from database.database_connection_manager import initialize_database


app = Flask(__name__)
config = get_config()

if config.api_config.cors_enabled:
    CORS(app, resources={r"/api/*": {"origins": "*"}})

repository = get_knowledge_repository()
llm_connector = create_llm_connector()
extractor = KnowledgeExtractor(llm_connector)


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.route('/api/graphs', methods=['GET'])
def get_all_graphs():
    """获取所有知识图谱"""
    try:
        graphs = repository.get_all_graphs()
        return jsonify({
            'success': True,
            'data': [g.to_dict() for g in graphs]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/graphs', methods=['POST'])
def create_graph():
    """创建新知识图谱"""
    try:
        data = request.get_json()
        graph_name = data.get('graph_name', '新图谱')
        description = data.get('description', '')

        manager = KnowledgeGraphManager()
        graph = manager.create_graph(graph_name, description)
        repository.save_graph(graph)

        return jsonify({
            'success': True,
            'data': graph.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/graphs/<graph_id>', methods=['GET'])
def get_graph(graph_id):
    """获取指定知识图谱"""
    try:
        graph = repository.get_graph(graph_id)
        if not graph:
            return jsonify({'success': False, 'error': '图谱不存在'}), 404

        return jsonify({
            'success': True,
            'data': graph.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/graphs/<graph_id>', methods=['PUT'])
def update_graph(graph_id):
    """更新知识图谱"""
    try:
        data = request.get_json()
        graph = repository.get_graph(graph_id)

        if not graph:
            return jsonify({'success': False, 'error': '图谱不存在'}), 404

        if 'graph_name' in data:
            graph.graph_name = data['graph_name']
        if 'description' in data:
            graph.description = data['description']
        if 'metadata' in data:
            graph.metadata = data['metadata']

        repository.save_graph(graph)

        return jsonify({
            'success': True,
            'data': graph.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/graphs/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id):
    """删除知识图谱"""
    try:
        success = repository.delete_graph(graph_id)
        if not success:
            return jsonify({'success': False, 'error': '图谱不存在'}), 404

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/graphs/<graph_id>/statistics', methods=['GET'])
def get_graph_statistics(graph_id):
    """获取图谱统计信息"""
    try:
        stats = repository.get_graph_statistics(graph_id)
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/extract/text', methods=['POST'])
def extract_from_text():
    """从文本抽取知识"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        graph_name = data.get('graph_name', '文本抽取图谱')

        if not text:
            return jsonify({'success': False, 'error': '文本不能为空'}), 400

        extraction_result, knowledge_graph = extractor.extract_from_text(
            text,
            graph_name=graph_name
        )

        repository.save_graph(knowledge_graph)
        repository.save_extraction_history(extraction_result.to_dict())

        return jsonify({
            'success': True,
            'data': {
                'extraction': extraction_result.to_dict(),
                'graph': knowledge_graph.to_dict()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/extract/batch', methods=['POST'])
def extract_batch():
    """批量抽取知识"""
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        graph_name = data.get('graph_name', '批量抽取图谱')

        if not texts:
            return jsonify({'success': False, 'error': '文本列表不能为空'}), 400

        results = extractor.extract_batch(texts, graph_name)

        graphs = []
        for extraction_result, graph in results:
            repository.save_graph(graph)
            repository.save_extraction_history(extraction_result.to_dict())
            graphs.append(graph.to_dict())

        return jsonify({
            'success': True,
            'data': graphs
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze/graph/<graph_id>', methods=['GET'])
def analyze_graph(graph_id):
    """分析知识图谱"""
    try:
        graph = repository.get_graph(graph_id)
        if not graph:
            return jsonify({'success': False, 'error': '图谱不存在'}), 404

        analysis = analyze_knowledge_graph(graph.entities, graph.relations)

        return jsonify({
            'success': True,
            'data': analysis
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze/path', methods=['POST'])
def analyze_path():
    """分析路径"""
    try:
        data = request.get_json()
        graph_id = data.get('graph_id')
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        max_depth = data.get('max_depth', 5)

        graph = repository.get_graph(graph_id)
        if not graph:
            return jsonify({'success': False, 'error': '图谱不存在'}), 404

        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        path_result = analyzer.analyze_path(source_id, target_id, max_depth)

        return jsonify({
            'success': True,
            'data': {
                'source': path_result.source_id,
                'target': path_result.target_id,
                'paths': path_result.paths,
                'shortest_length': path_result.shortest_path_length,
                'all_paths_found': path_result.all_paths_found
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/visualize/graph/<graph_id>', methods=['GET'])
def visualize_graph(graph_id):
    """获取图谱可视化数据"""
    try:
        graph = repository.get_graph(graph_id)
        if not graph:
            return jsonify({'success': False, 'error': '图谱不存在'}), 404

        analyzer = KnowledgeGraphAnalyzer(graph.entities, graph.relations)
        viz_generator = VisualizationDataGenerator(analyzer)

        layout = request.args.get('layout', 'force_directed')
        if layout == 'hierarchical':
            viz_data = viz_generator.generate_hierarchical_data()
        else:
            viz_data = viz_generator.generate_force_directed_data()

        return jsonify({
            'success': True,
            'data': viz_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/entities/search', methods=['GET'])
def search_entities():
    """搜索实体"""
    try:
        keyword = request.args.get('keyword', '')
        graph_id = request.args.get('graph_id')

        if not keyword:
            return jsonify({'success': False, 'error': '关键词不能为空'}), 400

        entities = repository.search_entities(keyword, graph_id)

        return jsonify({
            'success': True,
            'data': [e.to_dict() for e in entities]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/entities/<entity_id>', methods=['GET'])
def get_entity(entity_id):
    """获取实体详情"""
    try:
        entity = repository.get_entity_by_id(entity_id)
        if not entity:
            return jsonify({'success': False, 'error': '实体不存在'}), 404

        neighbors = repository.get_neighbors(entity_id)

        return jsonify({
            'success': True,
            'data': {
                'entity': entity.to_dict(),
                'neighbors': [n.to_dict() for n in neighbors]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history/extractions', methods=['GET'])
def get_extraction_history():
    """获取抽取历史"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = repository.get_extraction_history(limit)

        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system/stats', methods=['GET'])
def get_system_stats():
    """获取系统统计"""
    try:
        llm_stats = llm_connector.get_statistics()
        extractor_stats = extractor.get_extraction_statistics()

        graphs = repository.get_all_graphs()
        total_entities = sum(len(g.entities) for g in graphs)
        total_relations = sum(len(g.relations) for g in graphs)

        return jsonify({
            'success': True,
            'data': {
                'llm': llm_stats,
                'extraction': extractor_stats,
                'graphs': {
                    'total': len(graphs),
                    'total_entities': total_entities,
                    'total_relations': total_relations
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({'success': False, 'error': '资源不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({'success': False, 'error': '服务器内部错误'}), 500


@app.errorhandler(Exception)
def handle_exception(error):
    """通用异常处理"""
    repository.log_system_event('ERROR', str(error), 'API')
    return jsonify({'success': False, 'error': str(error)}), 500


def create_app():
    """创建Flask应用"""
    initialize_database()
    init_config()
    return app


if __name__ == '__main__':
    initialize_database()
    init_config()

    app.run(
        host=config.api_config.host,
        port=config.api_config.port,
        debug=config.api_config.debug
    )
