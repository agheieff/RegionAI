"""
Training pipeline for the Language Bridge projection models.

This module orchestrates the training process that teaches neural networks
to map natural language descriptions to semantic code behaviors.
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from typing import List, Tuple, Optional, Dict, Any
import os
from datetime import datetime

from .vectorizer import DatasetVectorizer
from .projection_model import ProjectionModel, create_projection_model, ModelCheckpoint
from tier1.semantic.fingerprint import SemanticFingerprint, DocumentedFingerprint
from tier1.semantic.db import SemanticDB


class LanguageBridgeDataset(Dataset):
    """
    PyTorch dataset for Language Bridge training.
    
    Handles the documented fingerprints and provides them as
    training examples for the projection model.
    """
    
    def __init__(self, text_embeddings: torch.Tensor, fingerprint_vectors: torch.Tensor):
        """
        Initialize the dataset.
        
        Args:
            text_embeddings: Pre-computed text embeddings
            fingerprint_vectors: Corresponding fingerprint multi-hot vectors
        """
        assert len(text_embeddings) == len(fingerprint_vectors)
        self.text_embeddings = text_embeddings
        self.fingerprint_vectors = fingerprint_vectors
    
    def __len__(self) -> int:
        return len(self.text_embeddings)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.text_embeddings[idx], self.fingerprint_vectors[idx]


class ProjectionTrainer:
    """
    Orchestrates the training of projection models.
    
    This class handles the complete training pipeline including data preparation,
    model training, validation, and checkpointing.
    """
    
    def __init__(self, model: nn.Module, vectorizer: DatasetVectorizer,
                 learning_rate: float = 1e-3, device: Optional[str] = None):
        """
        Initialize the trainer.
        
        Args:
            model: The projection model to train
            vectorizer: Dataset vectorizer for data preprocessing
            learning_rate: Learning rate for optimization
            device: Device to train on ('cuda', 'cpu', or None for auto)
        """
        self.model = model
        self.vectorizer = vectorizer
        self.learning_rate = learning_rate
        
        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Move model to device
        self.model.to(self.device)
        
        # Initialize optimizer and loss function
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.BCELoss()  # Binary cross-entropy for multi-label
        
        # Training history
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')
    
    def prepare_data(self, documented_fingerprints: List[DocumentedFingerprint],
                    val_split: float = 0.2) -> Tuple[DataLoader, DataLoader]:
        """
        Prepare training and validation data loaders.
        
        Args:
            documented_fingerprints: List of documented fingerprints
            val_split: Fraction of data to use for validation
            
        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Extract documentation and fingerprints
        training_pairs = []
        for doc_fp in documented_fingerprints:
            if doc_fp.nl_context.has_documentation():
                doc_text = doc_fp.nl_context.get_text_content()
                training_pairs.append((doc_text, doc_fp.fingerprint))
        
        if not training_pairs:
            raise ValueError("No documented fingerprints found for training")
        
        # Vectorize all data
        text_embeddings, fingerprint_vectors = self.vectorizer.prepare_training_data(training_pairs)
        
        # Split into train and validation
        n_samples = len(text_embeddings)
        n_val = int(n_samples * val_split)
        
        # Shuffle indices
        indices = torch.randperm(n_samples)
        val_indices = indices[:n_val]
        train_indices = indices[n_val:]
        
        # Create datasets
        train_dataset = LanguageBridgeDataset(
            text_embeddings[train_indices],
            fingerprint_vectors[train_indices]
        )
        val_dataset = LanguageBridgeDataset(
            text_embeddings[val_indices],
            fingerprint_vectors[val_indices]
        )
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
        
        return train_loader, val_loader
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        """
        Train for one epoch.
        
        Args:
            train_loader: Training data loader
            
        Returns:
            Average training loss for the epoch
        """
        self.model.train()
        total_loss = 0
        n_batches = 0
        
        for text_emb, fingerprint in train_loader:
            # Move to device
            text_emb = text_emb.to(self.device)
            fingerprint = fingerprint.to(self.device)
            
            # Forward pass
            predictions = self.model(text_emb)
            loss = self.criterion(predictions, fingerprint)
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
            n_batches += 1
        
        return total_loss / n_batches
    
    def validate(self, val_loader: DataLoader) -> Tuple[float, Dict[str, float]]:
        """
        Validate the model.
        
        Args:
            val_loader: Validation data loader
            
        Returns:
            Tuple of (average_loss, metrics_dict)
        """
        self.model.eval()
        total_loss = 0
        n_batches = 0
        
        # Metrics
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for text_emb, fingerprint in val_loader:
                # Move to device
                text_emb = text_emb.to(self.device)
                fingerprint = fingerprint.to(self.device)
                
                # Forward pass
                predictions = self.model(text_emb)
                loss = self.criterion(predictions, fingerprint)
                
                total_loss += loss.item()
                n_batches += 1
                
                # Store for metrics
                all_predictions.append(predictions.cpu())
                all_targets.append(fingerprint.cpu())
        
        avg_loss = total_loss / n_batches
        
        # Calculate metrics
        all_predictions = torch.cat(all_predictions)
        all_targets = torch.cat(all_targets)
        
        # Precision, recall, F1 at threshold 0.5
        predicted_binary = (all_predictions > 0.5).float()
        true_positives = (predicted_binary * all_targets).sum().item()
        predicted_positives = predicted_binary.sum().item()
        actual_positives = all_targets.sum().item()
        
        precision = true_positives / (predicted_positives + 1e-7)
        recall = true_positives / (actual_positives + 1e-7)
        f1 = 2 * precision * recall / (precision + recall + 1e-7)
        
        metrics = {
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
        
        return avg_loss, metrics
    
    def train(self, documented_fingerprints: List[DocumentedFingerprint],
             epochs: int = 100, val_split: float = 0.2,
             checkpoint_dir: Optional[str] = None,
             early_stopping_patience: int = 10) -> Dict[str, Any]:
        """
        Train the model on documented fingerprints.
        
        Args:
            documented_fingerprints: Training data
            epochs: Number of training epochs
            val_split: Validation split fraction
            checkpoint_dir: Directory to save checkpoints
            early_stopping_patience: Epochs to wait before early stopping
            
        Returns:
            Dictionary with training results and metrics
        """
        print(f"Training on device: {self.device}")
        print(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        
        # Prepare data
        train_loader, val_loader = self.prepare_data(documented_fingerprints, val_split)
        print(f"Training samples: {len(train_loader.dataset)}")
        print(f"Validation samples: {len(val_loader.dataset)}")
        
        # Training loop
        patience_counter = 0
        best_model_state = None
        
        for epoch in range(epochs):
            # Train
            train_loss = self.train_epoch(train_loader)
            self.train_losses.append(train_loss)
            
            # Validate
            val_loss, val_metrics = self.validate(val_loader)
            self.val_losses.append(val_loss)
            
            # Print progress
            print(f"Epoch {epoch+1}/{epochs}: "
                  f"Train Loss: {train_loss:.4f}, "
                  f"Val Loss: {val_loss:.4f}, "
                  f"F1: {val_metrics['f1']:.4f}")
            
            # Check for improvement
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                patience_counter = 0
                best_model_state = self.model.state_dict().copy()
                
                # Save checkpoint
                if checkpoint_dir:
                    self._save_checkpoint(checkpoint_dir, epoch, val_loss, val_metrics)
            else:
                patience_counter += 1
                
            # Early stopping
            if patience_counter >= early_stopping_patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
        
        # Restore best model
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
        
        # Final validation
        final_loss, final_metrics = self.validate(val_loader)
        
        return {
            'final_loss': final_loss,
            'final_metrics': final_metrics,
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'epochs_trained': epoch + 1
        }
    
    def _save_checkpoint(self, checkpoint_dir: str, epoch: int, 
                        val_loss: float, val_metrics: Dict[str, float]):
        """Save a model checkpoint."""
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"projection_model_epoch{epoch}_loss{val_loss:.4f}_{timestamp}.pt"
        filepath = os.path.join(checkpoint_dir, filename)
        
        metadata = {
            'epoch': epoch,
            'val_loss': val_loss,
            'val_metrics': val_metrics,
            'learning_rate': self.learning_rate,
            'device': str(self.device)
        }
        
        ModelCheckpoint.save(self.model, filepath, metadata)
        print(f"Saved checkpoint: {filename}")


class LanguageBridgeTrainer:
    """
    High-level trainer that handles the complete Language Bridge training pipeline.
    
    This class provides a simple interface for training projection models
    from a SemanticDB populated with documented fingerprints.
    """
    
    def __init__(self, model_type: str = "standard", device: Optional[str] = None):
        """
        Initialize the Language Bridge trainer.
        
        Args:
            model_type: Type of projection model to use
            device: Training device
        """
        self.model_type = model_type
        self.device = device
        self.vectorizer = DatasetVectorizer()
        self.model = None
        self.trainer = None
    
    def train_from_semantic_db(self, semantic_db: SemanticDB,
                              epochs: int = 100,
                              checkpoint_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Train a projection model from a SemanticDB.
        
        Args:
            semantic_db: Database containing documented fingerprints
            epochs: Number of training epochs
            checkpoint_dir: Directory for saving checkpoints
            
        Returns:
            Training results dictionary
        """
        # Extract training candidates
        training_entries = semantic_db.find_training_candidates()
        if not training_entries:
            raise ValueError("No suitable training candidates found in SemanticDB")
        
        # Convert to documented fingerprints
        documented_fingerprints = []
        for entry in training_entries:
            if entry.documented_fingerprint:
                documented_fingerprints.append(entry.documented_fingerprint)
        
        print(f"Found {len(documented_fingerprints)} training examples")
        
        # Get model dimensions
        text_dim, fingerprint_dim = self.vectorizer.get_dimensions()
        
        # Create model
        self.model = create_projection_model(
            text_dim, fingerprint_dim, 
            model_type=self.model_type
        )
        
        # Create trainer
        self.trainer = ProjectionTrainer(
            self.model, self.vectorizer, device=self.device
        )
        
        # Train
        results = self.trainer.train(
            documented_fingerprints,
            epochs=epochs,
            checkpoint_dir=checkpoint_dir
        )
        
        return results
    
    def predict(self, text: str, threshold: float = 0.5) -> SemanticFingerprint:
        """
        Predict semantic fingerprint from text.
        
        Args:
            text: Natural language description
            threshold: Threshold for behavior activation
            
        Returns:
            Predicted semantic fingerprint
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        # Vectorize text
        text_embedding = self.vectorizer.text_vectorizer.vectorize_single(text)
        # Get device from model parameters
        device = next(self.model.parameters()).device
        text_embedding = text_embedding.unsqueeze(0).to(device)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(text_embedding)
        
        # Decode to fingerprint
        fingerprint = self.vectorizer.fingerprint_vectorizer.decode(
            prediction.cpu(), threshold
        )
        
        return fingerprint
    
    def save_model(self, filepath: str):
        """Save the trained model."""
        if self.model is None:
            raise ValueError("No model to save")
        ModelCheckpoint.save(self.model, filepath)
    
    def load_model(self, filepath: str):
        """Load a trained model."""
        # Determine model class based on saved config
        checkpoint = torch.load(filepath, map_location='cpu')
        config = checkpoint.get('model_config', {})
        
        # Create appropriate model class
        if hasattr(self, 'model_type'):
            model_class = type(create_projection_model(
                config['text_embedding_dim'],
                config['fingerprint_dim'],
                model_type=self.model_type
            ))
        else:
            model_class = ProjectionModel
        
        self.model = ModelCheckpoint.load(model_class, filepath)
        if self.device:
            self.model.to(self.device)