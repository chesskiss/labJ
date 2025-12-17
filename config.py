"""
Configuration management for the lab assistant.
Environment-backed settings loader 

This module handles loading and managing configuration settings for audio,
speech-to-text, NLP, visualization, and UI components.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Project root (folder containing this file)
BASE_DIR = Path(__file__).resolve().parent

# Load base vars then override with secrets
load_dotenv(BASE_DIR / ".env", override=True)


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    p = Path(value)
    if not p.is_absolute():
        p = BASE_DIR / p
    return p


# STT and audio config
STT_SAMPLE_RATE: int = _int("STT_SAMPLE_RATE", 16000)
STT_MODEL_SIZE: str = os.getenv("STT_MODEL_SIZE", "tiny")
STT_DURATION: int = _int("STT_DURATION", 50)  # seconds, used in __main__ test
CHUNK_SIZE: int = _int("CHUNK_SIZE", 4096)

# Streaming STT tuning
STT_WINDOW_SEC: float = _float("STT_WINDOW_SEC", 3.0)
STT_OVERLAP_SEC: float = _float("STT_OVERLAP_SEC", 0.7)

# Noise / text filters
STT_MIN_WINDOW_RMS: float = _float("STT_MIN_WINDOW_RMS", 0.005)
STT_MIN_TEXT_CHARS: int = _int("STT_MIN_TEXT_CHARS", 5)

# Data paths
DATA_DIR: Path = _path("DATA_DIR", BASE_DIR / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH: Path = _path("DB_PATH", DATA_DIR / "journal.sqlite")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Legacy compatibility: expose ROOT similar to old env_config
ROOT: Path = BASE_DIR



# import os
# from pathlib import Path
# from typing import Dict, Any, Optional
# from dataclasses import dataclass, field


# @dataclass
# class AudioConfig:
#     """Configuration for audio input."""
#     sample_rate: int = 16000
#     channels: int = 1
#     chunk_size: int = 4096
#     device: Optional[int] = None  # None for default device
#     dtype: str = "float32"
    
#     # TODO: Add audio preprocessing options
#     # noise_reduction: bool = False
#     # gain: float = 1.0


# @dataclass
# class STTConfig:
#     """Configuration for speech-to-text."""
#     model_type: str = "faster-whisper"  # or "vosk"
#     model_size: str = "base"  # tiny, base, small, medium, large
#     model_path: Optional[str] = None  # Path to local model
#     language: Optional[str] = None  # None for auto-detect
#     device: str = "cpu"  # cpu or cuda
#     compute_type: str = "int8"  # float16, int8, int8_float16
    
#     # TODO: Add Vosk-specific config
#     # vosk_model_path: Optional[str] = None


# @dataclass
# class NLPConfig:
#     """Configuration for natural language processing."""
#     llm_provider: str = "openai"  # openai, local, anthropic, etc.
#     model_name: str = "gpt-3.5-turbo"
#     api_key: Optional[str] = None
#     temperature: float = 0.7
#     max_tokens: int = 1000
    
#     # TODO: Add local LLM config
#     # local_model_path: Optional[str] = None
#     # use_gpu: bool = False


# @dataclass
# class VisualizationConfig:
#     """Configuration for visualization generation."""
#     default_chart_type: str = "line"
#     chart_backend: str = "matplotlib"  # matplotlib, plotly
#     output_format: str = "png"  # png, svg, html
#     output_dir: Path = field(default_factory=lambda: Path("data/charts"))
#     dpi: int = 300
#     style: str = "seaborn"  # matplotlib style
    
#     # TODO: Add chart customization options
#     # default_colors: List[str] = None
#     # figure_size: Tuple[int, int] = (10, 6)


# @dataclass
# class UIConfig:
#     """Configuration for UI components."""
#     ui_type: str = "streamlit"  # streamlit, terminal, tkinter
#     streamlit_port: int = 8501
#     streamlit_host: str = "localhost"
#     show_audio_levels: bool = True
#     show_transcription: bool = True
    
#     # TODO: Add terminal UI config
#     # terminal_width: int = 80
#     # use_colors: bool = True


# @dataclass
# class Config:
#     """Main configuration class."""
#     audio: AudioConfig = field(default_factory=AudioConfig)
#     stt: STTConfig = field(default_factory=STTConfig)
#     nlp: NLPConfig = field(default_factory=NLPConfig)
#     visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
#     ui: UIConfig = field(default_factory=UIConfig)
    
#     # Data directories
#     data_dir: Path = field(default_factory=lambda: Path("data"))
#     logs_dir: Path = field(default_factory=lambda: Path("data/logs"))
#     charts_dir: Path = field(default_factory=lambda: Path("data/charts"))
#     experiments_dir: Path = field(default_factory=lambda: Path("data/experiments"))
    
#     def __post_init__(self):
#         """Initialize configuration and load from environment."""
#         # Load API keys from environment
#         self.nlp.api_key = os.getenv("OPENAI_API_KEY", self.nlp.api_key)
        
#         # Create data directories
#         self.data_dir.mkdir(exist_ok=True)
#         self.logs_dir.mkdir(parents=True, exist_ok=True)
#         self.charts_dir.mkdir(parents=True, exist_ok=True)
#         self.experiments_dir.mkdir(parents=True, exist_ok=True)
        
#         # Set STT model path if not specified
#         if self.stt.model_path is None:
#             # TODO: Set default model path based on model_type and model_size
#             pass
        
#         # TODO: Load configuration from YAML file if exists
#         # self.load_from_yaml("config.yaml")
    
#     def load_from_yaml(self, yaml_path: str):
#         """
#         Load configuration from a YAML file.
        
#         Args:
#             yaml_path: Path to YAML configuration file
        
#         TODO: Implement YAML configuration loading
#         """
#         # TODO: Implement YAML loading
#         pass
    
#     def save_to_yaml(self, yaml_path: str):
#         """
#         Save current configuration to a YAML file.
        
#         Args:
#             yaml_path: Path to save YAML configuration file
        
#         TODO: Implement YAML configuration saving
#         """
#         # TODO: Implement YAML saving
#         pass

