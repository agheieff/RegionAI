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
# NLPExtractor replaced by pure functions in nlp_utils
from .doc_generator import DocumentationGenerator

# Import pure function modules  
from . import grammar_utils
from . import nlp_utils

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
    # Documentation
    'DocumentationGenerator',
    # Pure function modules
    'grammar_utils',
    'nlp_utils',
]