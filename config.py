"""
Configuration management for the lab assistant.

This module handles loading and managing configuration settings for audio,
speech-to-text, NLP, visualization, and UI components.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class AudioConfig:
    """Configuration for audio input."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 4096
    device: Optional[int] = None  # None for default device
    dtype: str = "float32"
    
    # TODO: Add audio preprocessing options
    # noise_reduction: bool = False
    # gain: float = 1.0


@dataclass
class STTConfig:
    """Configuration for speech-to-text."""
    model_type: str = "faster-whisper"  # or "vosk"
    model_size: str = "base"  # tiny, base, small, medium, large
    model_path: Optional[str] = None  # Path to local model
    language: Optional[str] = None  # None for auto-detect
    device: str = "cpu"  # cpu or cuda
    compute_type: str = "int8"  # float16, int8, int8_float16
    
    # TODO: Add Vosk-specific config
    # vosk_model_path: Optional[str] = None


@dataclass
class NLPConfig:
    """Configuration for natural language processing."""
    llm_provider: str = "openai"  # openai, local, anthropic, etc.
    model_name: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    
    # TODO: Add local LLM config
    # local_model_path: Optional[str] = None
    # use_gpu: bool = False


@dataclass
class VisualizationConfig:
    """Configuration for visualization generation."""
    default_chart_type: str = "line"
    chart_backend: str = "matplotlib"  # matplotlib, plotly
    output_format: str = "png"  # png, svg, html
    output_dir: Path = field(default_factory=lambda: Path("data/charts"))
    dpi: int = 300
    style: str = "seaborn"  # matplotlib style
    
    # TODO: Add chart customization options
    # default_colors: List[str] = None
    # figure_size: Tuple[int, int] = (10, 6)


@dataclass
class UIConfig:
    """Configuration for UI components."""
    ui_type: str = "streamlit"  # streamlit, terminal, tkinter
    streamlit_port: int = 8501
    streamlit_host: str = "localhost"
    show_audio_levels: bool = True
    show_transcription: bool = True
    
    # TODO: Add terminal UI config
    # terminal_width: int = 80
    # use_colors: bool = True


@dataclass
class Config:
    """Main configuration class."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    nlp: NLPConfig = field(default_factory=NLPConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Data directories
    data_dir: Path = field(default_factory=lambda: Path("data"))
    logs_dir: Path = field(default_factory=lambda: Path("data/logs"))
    charts_dir: Path = field(default_factory=lambda: Path("data/charts"))
    experiments_dir: Path = field(default_factory=lambda: Path("data/experiments"))
    
    def __post_init__(self):
        """Initialize configuration and load from environment."""
        # Load API keys from environment
        self.nlp.api_key = os.getenv("OPENAI_API_KEY", self.nlp.api_key)
        
        # Create data directories
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        
        # Set STT model path if not specified
        if self.stt.model_path is None:
            # TODO: Set default model path based on model_type and model_size
            pass
        
        # TODO: Load configuration from YAML file if exists
        # self.load_from_yaml("config.yaml")
    
    def load_from_yaml(self, yaml_path: str):
        """
        Load configuration from a YAML file.
        
        Args:
            yaml_path: Path to YAML configuration file
        
        TODO: Implement YAML configuration loading
        """
        # TODO: Implement YAML loading
        pass
    
    def save_to_yaml(self, yaml_path: str):
        """
        Save current configuration to a YAML file.
        
        Args:
            yaml_path: Path to save YAML configuration file
        
        TODO: Implement YAML configuration saving
        """
        # TODO: Implement YAML saving
        pass

