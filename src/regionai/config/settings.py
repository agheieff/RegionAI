"""Configuration settings for RegionAI."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os
import json
import yaml
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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualizationConfig':
        """Create config from dictionary."""
        # Handle nested color config
        if 'colors' in data:
            colors = data.pop('colors')
            data.update({
                'default_color': colors.get('default', 'blue'),
                'selection_color': colors.get('selection', 'red'),
                'contained_color': colors.get('contained', 'green'),
                'overlap_color': colors.get('overlap', 'yellow')
            })
        
        # Handle figure settings
        if 'figure' in data:
            fig = data.pop('figure')
            data['figsize'] = (fig.get('width', 10), fig.get('height', 10))
            data['dpi'] = fig.get('dpi', 100)
        
        # Filter to valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)


@dataclass
class ComputationConfig:
    """Configuration for computation settings."""
    
    device: str = field(default_factory=lambda: 'cuda' if torch.cuda.is_available() else 'cpu')
    precision: str = 'float32'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComputationConfig':
        """Create config from dictionary."""
        device = data.get('device', 'auto')
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        return cls(
            device=device,
            precision=data.get('precision', 'float32')
        )


@dataclass
class Config:
    """Main configuration class."""
    
    viz: VisualizationConfig = field(default_factory=VisualizationConfig)
    computation: ComputationConfig = field(default_factory=ComputationConfig)
    
    @property
    def device(self) -> str:
        """Backward compatibility property."""
        return self.computation.device
    
    def __post_init__(self):
        if self.computation.device == 'cuda' and not torch.cuda.is_available():
            print("Warning: CUDA requested but not available. Using CPU.")
            self.computation.device = 'cpu'
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> 'Config':
        """Load configuration from file.
        
        Args:
            path: Path to config file (YAML or JSON). If None, looks for
                  config.yaml or config.json in standard locations.
                  
        Returns:
            Loaded configuration
        """
        if path is None:
            # Look for config in standard locations
            search_paths = [
                'config.yaml',
                'config.json',
                os.path.join(os.path.dirname(__file__), 'config.yaml'),
                os.path.join(os.path.dirname(__file__), 'config.json'),
                os.path.expanduser('~/.regionai/config.yaml'),
                os.path.expanduser('~/.regionai/config.json'),
            ]
            
            for search_path in search_paths:
                if os.path.exists(search_path):
                    path = search_path
                    break
            else:
                # No config file found, use defaults
                return cls()
        
        # Load the config file
        with open(path, 'r') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        # Create config from data
        viz_data = data.get('visualization', {})
        comp_data = data.get('computation', {})
        
        return cls(
            viz=VisualizationConfig.from_dict(viz_data),
            computation=ComputationConfig.from_dict(comp_data)
        )
    
    def save(self, path: str) -> None:
        """Save configuration to file.
        
        Args:
            path: Output path (YAML or JSON based on extension)
        """
        data = {
            'visualization': {
                'default_alpha': self.viz.default_alpha,
                'highlight_alpha': self.viz.highlight_alpha,
                'colors': {
                    'default': self.viz.default_color,
                    'selection': self.viz.selection_color,
                    'contained': self.viz.contained_color,
                    'overlap': self.viz.overlap_color,
                },
                'figure': {
                    'width': self.viz.figsize[0],
                    'height': self.viz.figsize[1],
                    'dpi': self.viz.dpi,
                },
                'show_grid': self.viz.grid,
                'highlight_linewidth': self.viz.highlight_linewidth,
            },
            'computation': {
                'device': self.computation.device,
                'precision': self.computation.precision,
            }
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                yaml.dump(data, f, default_flow_style=False)
            else:
                json.dump(data, f, indent=2)