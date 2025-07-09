"""Configuration settings for RegionAI."""

from dataclasses import dataclass, field
import torch


@dataclass
class VisualizationConfig:
    """Configuration for visualization settings."""
    
    default_alpha: float = 0.3
    selection_color: str = 'red'
    contained_color: str = 'green'
    overlap_color: str = 'yellow'
    default_color: str = 'blue'
    
    # Plot settings
    figsize: tuple[int, int] = (10, 10)
    dpi: int = 100
    grid: bool = True
    
    # Interaction settings
    highlight_alpha: float = 0.6
    highlight_linewidth: float = 3.0


@dataclass
class Config:
    """Main configuration class."""
    
    viz: VisualizationConfig = field(default_factory=VisualizationConfig)
    device: str = field(default_factory=lambda: 'cuda' if torch.cuda.is_available() else 'cpu')
    
    def __post_init__(self):
        if self.device == 'cuda' and not torch.cuda.is_available():
            print("Warning: CUDA requested but not available. Using CPU.")
            self.device = 'cpu'