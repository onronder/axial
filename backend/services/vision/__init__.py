"""
Vision LLM Description Layer

Provides semantic understanding of images and diagrams using Vision LLMs.
Integrates with GPT-4o and Gemini Pro Vision for intelligent image analysis.

Components:
- base.py: Abstract VisionProcessor interface
- openai_vision.py: GPT-4o implementation
- gemini_vision.py: Gemini Pro Vision implementation
- circuit.py: Vision-specific circuit breakers
"""

from services.vision.base import DiagramType, VisionProcessor, VisionResult
from services.vision.gemini_vision import GeminiVisionProcessor
from services.vision.openai_vision import GPT4VisionProcessor

__all__ = [
    'VisionProcessor',
    'VisionResult',
    'DiagramType',
    'GPT4VisionProcessor',
    'GeminiVisionProcessor',
]
