"""
Vectorization module for the Language Bridge.

This module provides tools to convert natural language text and semantic
fingerprints into numerical vectors suitable for neural network training.
"""
import torch
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional, Tuple

from tier1.semantic.fingerprint import SemanticFingerprint, Behavior


class TextVectorizer:
    """
    Encodes natural language text into high-dimensional vectors.
    
    Uses pre-trained sentence transformers to create semantically meaningful
    embeddings of documentation strings.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the text vectorizer.
        
        Args:
            model_name: Name of the sentence transformer model to use.
                       Default is 'all-MiniLM-L6-v2' which provides a good
                       balance of performance and size.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def vectorize(self, texts: List[str]) -> torch.Tensor:
        """
        Convert a list of text strings into embeddings.
        
        Args:
            texts: List of documentation strings to encode
            
        Returns:
            Tensor of shape (len(texts), embedding_dim) containing embeddings
        """
        if not texts:
            return torch.empty(0, self.embedding_dim)
        
        # Sentence transformers can handle batch encoding efficiently
        embeddings = self.model.encode(texts, convert_to_tensor=True)
        return embeddings
    
    def vectorize_single(self, text: str) -> torch.Tensor:
        """
        Convert a single text string into an embedding.
        
        Args:
            text: Documentation string to encode
            
        Returns:
            Tensor of shape (embedding_dim,) containing the embedding
        """
        return self.vectorize([text])[0]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of the text embeddings."""
        return self.embedding_dim


class FingerprintVectorizer:
    """
    Converts semantic fingerprints into multi-hot encoded vectors.
    
    Each behavior in the fingerprint is mapped to a dimension in the output
    vector, creating a binary representation of which behaviors are present.
    """
    
    def __init__(self, all_behaviors: Optional[List[Behavior]] = None):
        """
        Initialize the fingerprint vectorizer.
        
        Args:
            all_behaviors: List of all possible behaviors. If None, uses all
                          behaviors defined in the Behavior enum.
        """
        if all_behaviors is None:
            all_behaviors = list(Behavior)
        
        self.all_behaviors = all_behaviors
        self.behavior_to_idx = {behavior: i for i, behavior in enumerate(all_behaviors)}
        self.idx_to_behavior = {i: behavior for i, behavior in enumerate(all_behaviors)}
        self.num_behaviors = len(all_behaviors)
    
    def vectorize(self, fingerprints: List[SemanticFingerprint]) -> torch.Tensor:
        """
        Convert a list of fingerprints into multi-hot vectors.
        
        Args:
            fingerprints: List of semantic fingerprints to encode
            
        Returns:
            Tensor of shape (len(fingerprints), num_behaviors) with binary values
        """
        vectors = torch.zeros(len(fingerprints), self.num_behaviors)
        
        for i, fp in enumerate(fingerprints):
            for behavior in fp.behaviors:
                if behavior in self.behavior_to_idx:
                    vectors[i, self.behavior_to_idx[behavior]] = 1.0
        
        return vectors
    
    def vectorize_single(self, fingerprint: SemanticFingerprint) -> torch.Tensor:
        """
        Convert a single fingerprint into a multi-hot vector.
        
        Args:
            fingerprint: Semantic fingerprint to encode
            
        Returns:
            Tensor of shape (num_behaviors,) with binary values
        """
        return self.vectorize([fingerprint])[0]
    
    def decode(self, vector: torch.Tensor, threshold: float = 0.5) -> SemanticFingerprint:
        """
        Convert a vector back into a semantic fingerprint.
        
        Args:
            vector: Multi-hot vector of shape (num_behaviors,)
            threshold: Threshold for considering a behavior active
            
        Returns:
            SemanticFingerprint with predicted behaviors
        """
        behaviors = set()
        
        # Handle both 1D and 2D inputs
        if vector.dim() == 2:
            vector = vector.squeeze(0)
        
        for idx, value in enumerate(vector):
            if value > threshold and idx in self.idx_to_behavior:
                behaviors.add(self.idx_to_behavior[idx])
        
        return SemanticFingerprint(behaviors=behaviors)
    
    def decode_batch(self, vectors: torch.Tensor, threshold: float = 0.5) -> List[SemanticFingerprint]:
        """
        Convert a batch of vectors back into semantic fingerprints.
        
        Args:
            vectors: Multi-hot vectors of shape (batch_size, num_behaviors)
            threshold: Threshold for considering a behavior active
            
        Returns:
            List of SemanticFingerprints with predicted behaviors
        """
        return [self.decode(vec, threshold) for vec in vectors]
    
    def get_behavior_dimension(self) -> int:
        """Get the dimensionality of the fingerprint vectors."""
        return self.num_behaviors
    
    def get_behavior_names(self) -> List[str]:
        """Get ordered list of behavior names corresponding to vector dimensions."""
        return [self.idx_to_behavior[i].name for i in range(self.num_behaviors)]


class DatasetVectorizer:
    """
    Combines text and fingerprint vectorization for complete dataset processing.
    
    This class handles the conversion of documented fingerprints into
    input-output pairs suitable for model training.
    """
    
    def __init__(self, text_model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the dataset vectorizer.
        
        Args:
            text_model_name: Name of sentence transformer model for text encoding
        """
        self.text_vectorizer = TextVectorizer(text_model_name)
        self.fingerprint_vectorizer = FingerprintVectorizer()
    
    def prepare_training_data(self, documented_fingerprints: List[Tuple[str, SemanticFingerprint]]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Prepare training data from documented fingerprints.
        
        Args:
            documented_fingerprints: List of (documentation, fingerprint) pairs
            
        Returns:
            Tuple of (text_embeddings, fingerprint_vectors) tensors
        """
        if not documented_fingerprints:
            return (torch.empty(0, self.text_vectorizer.embedding_dim),
                   torch.empty(0, self.fingerprint_vectorizer.num_behaviors))
        
        docs, fingerprints = zip(*documented_fingerprints)
        
        text_embeddings = self.text_vectorizer.vectorize(list(docs))
        fingerprint_vectors = self.fingerprint_vectorizer.vectorize(list(fingerprints))
        
        return text_embeddings, fingerprint_vectors
    
    def get_dimensions(self) -> Tuple[int, int]:
        """
        Get the input and output dimensions for model architecture.
        
        Returns:
            Tuple of (text_embedding_dim, fingerprint_dim)
        """
        return (self.text_vectorizer.get_embedding_dimension(),
                self.fingerprint_vectorizer.get_behavior_dimension())


class VectorizationCache:
    """
    Caches vectorization results to avoid redundant computation.
    
    Useful when the same documentation strings appear multiple times
    in the dataset or during iterative training.
    """
    
    def __init__(self, vectorizer: TextVectorizer):
        self.vectorizer = vectorizer
        self.cache: Dict[str, torch.Tensor] = {}
    
    def vectorize(self, text: str) -> torch.Tensor:
        """
        Vectorize text with caching.
        
        Args:
            text: Documentation string to encode
            
        Returns:
            Cached or newly computed embedding
        """
        if text not in self.cache:
            self.cache[text] = self.vectorizer.vectorize_single(text)
        return self.cache[text]
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
    
    def size(self) -> int:
        """Get the number of cached embeddings."""
        return len(self.cache)