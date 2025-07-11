"""
Neural projection model for the Language Bridge.

This module defines the neural network architecture that learns to map
text embeddings to semantic fingerprint vectors, enabling prediction
of code behaviors from natural language descriptions.
"""
import torch
import torch.nn as nn
from typing import Optional, Dict, Any


class ProjectionModel(nn.Module):
    """
    A neural network that maps text embeddings to semantic fingerprint vectors.
    
    This is the core of the Language Bridge - it learns the projection from
    natural language space to semantic behavior space.
    """
    
    def __init__(self, text_embedding_dim: int, fingerprint_dim: int, 
                 hidden_dim: int = 256, dropout_rate: float = 0.4):
        """
        Initialize the projection model.
        
        Args:
            text_embedding_dim: Dimension of input text embeddings
            fingerprint_dim: Dimension of output fingerprint vectors
            hidden_dim: Size of hidden layers
            dropout_rate: Dropout probability for regularization
        """
        super().__init__()
        
        self.text_embedding_dim = text_embedding_dim
        self.fingerprint_dim = fingerprint_dim
        self.hidden_dim = hidden_dim
        
        # Build the network architecture
        self.layer_stack = nn.Sequential(
            nn.Linear(text_embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim // 2, fingerprint_dim),
            nn.Sigmoid()  # Output probabilities for each behavior
        )
        
        # Initialize weights using Xavier initialization
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize model weights for better convergence."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Args:
            x: Text embeddings of shape (batch_size, text_embedding_dim)
            
        Returns:
            Predicted fingerprint vectors of shape (batch_size, fingerprint_dim)
        """
        return self.layer_stack(x)
    
    def predict_behaviors(self, x: torch.Tensor, threshold: float = 0.5) -> torch.Tensor:
        """
        Predict binary behavior presence from text embeddings.
        
        Args:
            x: Text embeddings
            threshold: Threshold for behavior activation
            
        Returns:
            Binary behavior predictions
        """
        with torch.no_grad():
            predictions = self.forward(x)
            return (predictions > threshold).float()


class AttentionProjectionModel(nn.Module):
    """
    An enhanced projection model using attention mechanisms.
    
    This model uses self-attention to better capture relationships between
    different aspects of the text when predicting behaviors.
    """
    
    def __init__(self, text_embedding_dim: int, fingerprint_dim: int,
                 hidden_dim: int = 256, num_heads: int = 4, dropout_rate: float = 0.4):
        """
        Initialize the attention-based projection model.
        
        Args:
            text_embedding_dim: Dimension of input text embeddings
            fingerprint_dim: Dimension of output fingerprint vectors
            hidden_dim: Size of hidden layers
            num_heads: Number of attention heads
            dropout_rate: Dropout probability
        """
        super().__init__()
        
        self.text_embedding_dim = text_embedding_dim
        self.fingerprint_dim = fingerprint_dim
        self.hidden_dim = hidden_dim
        
        # Project to hidden dimension
        self.input_projection = nn.Linear(text_embedding_dim, hidden_dim)
        
        # Self-attention layer
        self.attention = nn.MultiheadAttention(
            hidden_dim, 
            num_heads=num_heads,
            dropout=dropout_rate,
            batch_first=True
        )
        
        # Feed-forward network
        self.ffn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim * 2, hidden_dim)
        )
        
        # Output projection
        self.output_projection = nn.Sequential(
            nn.Linear(hidden_dim, fingerprint_dim),
            nn.Sigmoid()
        )
        
        # Layer normalization
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize model weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with attention mechanism.
        
        Args:
            x: Text embeddings of shape (batch_size, text_embedding_dim)
            
        Returns:
            Predicted fingerprint vectors
        """
        # Project to hidden dimension
        x = self.input_projection(x)
        
        # Add sequence dimension for attention (batch_size, 1, hidden_dim)
        x = x.unsqueeze(1)
        
        # Self-attention with residual connection
        attn_out, _ = self.attention(x, x, x)
        x = self.norm1(x + attn_out)
        
        # Feed-forward with residual connection
        ffn_out = self.ffn(x)
        x = self.norm2(x + ffn_out)
        
        # Remove sequence dimension and project to output
        x = x.squeeze(1)
        return self.output_projection(x)


class EnsembleProjectionModel(nn.Module):
    """
    An ensemble of projection models for improved robustness.
    
    Combines predictions from multiple models to reduce variance
    and improve generalization.
    """
    
    def __init__(self, text_embedding_dim: int, fingerprint_dim: int,
                 num_models: int = 3, model_type: str = "standard"):
        """
        Initialize the ensemble model.
        
        Args:
            text_embedding_dim: Dimension of input text embeddings
            fingerprint_dim: Dimension of output fingerprint vectors
            num_models: Number of models in the ensemble
            model_type: Type of base model ("standard" or "attention")
        """
        super().__init__()
        
        self.num_models = num_models
        self.models = nn.ModuleList()
        
        for i in range(num_models):
            if model_type == "standard":
                model = ProjectionModel(
                    text_embedding_dim, 
                    fingerprint_dim,
                    hidden_dim=256 + i * 64  # Vary architecture slightly
                )
            else:
                model = AttentionProjectionModel(
                    text_embedding_dim,
                    fingerprint_dim,
                    hidden_dim=256 + i * 64
                )
            self.models.append(model)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through ensemble.
        
        Args:
            x: Text embeddings
            
        Returns:
            Averaged predictions from all models
        """
        predictions = []
        for model in self.models:
            predictions.append(model(x))
        
        # Average predictions
        return torch.stack(predictions).mean(dim=0)


class ModelCheckpoint:
    """
    Utility class for saving and loading model checkpoints.
    """
    
    @staticmethod
    def save(model: nn.Module, filepath: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Save model checkpoint.
        
        Args:
            model: Model to save
            filepath: Path to save checkpoint
            metadata: Optional metadata to include
        """
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'model_config': {
                'text_embedding_dim': getattr(model, 'text_embedding_dim', None),
                'fingerprint_dim': getattr(model, 'fingerprint_dim', None),
                'hidden_dim': getattr(model, 'hidden_dim', None),
            }
        }
        
        if metadata:
            checkpoint['metadata'] = metadata
        
        torch.save(checkpoint, filepath)
    
    @staticmethod
    def load(model_class: type, filepath: str) -> nn.Module:
        """
        Load model from checkpoint.
        
        Args:
            model_class: Class of model to instantiate
            filepath: Path to checkpoint file
            
        Returns:
            Loaded model
        """
        checkpoint = torch.load(filepath)
        
        # Reconstruct model with saved configuration
        config = checkpoint['model_config']
        model = model_class(**{k: v for k, v in config.items() if v is not None})
        
        # Load weights
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        return model


def create_projection_model(text_embedding_dim: int, fingerprint_dim: int,
                          model_type: str = "standard", **kwargs) -> nn.Module:
    """
    Factory function to create projection models.
    
    Args:
        text_embedding_dim: Dimension of input text embeddings
        fingerprint_dim: Dimension of output fingerprint vectors
        model_type: Type of model to create ("standard", "attention", or "ensemble")
        **kwargs: Additional arguments for model construction
        
    Returns:
        Initialized projection model
    """
    if model_type == "standard":
        return ProjectionModel(text_embedding_dim, fingerprint_dim, **kwargs)
    elif model_type == "attention":
        return AttentionProjectionModel(text_embedding_dim, fingerprint_dim, **kwargs)
    elif model_type == "ensemble":
        return EnsembleProjectionModel(text_embedding_dim, fingerprint_dim, **kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")