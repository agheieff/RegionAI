"""
Language understanding module for RegionAI.

This package implements the Language Bridge - neural models that learn
to map between natural language descriptions and semantic code behaviors.
"""

from .vectorizer import TextVectorizer, FingerprintVectorizer, DatasetVectorizer
from .projection_model import (
    ProjectionModel, AttentionProjectionModel, EnsembleProjectionModel,
    create_projection_model, ModelCheckpoint
)
from .trainer import ProjectionTrainer, LanguageBridgeTrainer
from .nlp_extractor import NLPExtractor
from .doc_generator import DocumentationGenerator

__all__ = [
    # Vectorizers
    'TextVectorizer',
    'FingerprintVectorizer',
    'DatasetVectorizer',
    # Models
    'ProjectionModel',
    'AttentionProjectionModel', 
    'EnsembleProjectionModel',
    'create_projection_model',
    'ModelCheckpoint',
    # Trainers
    'ProjectionTrainer',
    'LanguageBridgeTrainer',
    # NLP
    'NLPExtractor',
    # Documentation
    'DocumentationGenerator',
]