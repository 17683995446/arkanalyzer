# -*- coding: utf-8 -*-
"""
Arkanalyzer 核心模块包
"""

from .knowledge_graph_core import (
    Entity,
    Relation,
    KnowledgeGraph,
    KnowledgeGraphManager,
    EntityType,
    RelationType
)

from .knowledge_extractor import (
    KnowledgeExtractor,
    TextPreprocessor,
    GraphAnalyzer,
    ExtractionResult
)

from .knowledge_repository import (
    KnowledgeRepository,
    get_knowledge_repository
)

from .llm_connector import (
    LLMConnector,
    create_llm_connector,
    LLMCache,
    LLMResponse
)

from .knowledge_graph_analyzer import (
    KnowledgeGraphAnalyzer,
    VisualizationDataGenerator,
    analyze_knowledge_graph,
    GraphStatistics,
    PathAnalysisResult,
    CommunityDetectionResult
)

__version__ = "1.0.0"
__all__ = [
    'Entity',
    'Relation',
    'KnowledgeGraph',
    'KnowledgeGraphManager',
    'EntityType',
    'RelationType',
    'KnowledgeExtractor',
    'TextPreprocessor',
    'GraphAnalyzer',
    'ExtractionResult',
    'KnowledgeRepository',
    'get_knowledge_repository',
    'LLMConnector',
    'create_llm_connector',
    'LLMCache',
    'LLMResponse',
    'KnowledgeGraphAnalyzer',
    'VisualizationDataGenerator',
    'analyze_knowledge_graph',
    'GraphStatistics',
    'PathAnalysisResult',
    'CommunityDetectionResult'
]
