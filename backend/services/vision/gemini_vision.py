"""
Gemini Pro Vision Processor

Implements Vision LLM analysis using Google's Gemini Pro Vision model.
"""

import json
import logging
from typing import Optional

from services.vision.base import VisionProcessor, VisionResult, DiagramType

logger = logging.getLogger(__name__)


class GeminiVisionProcessor(VisionProcessor):
    """
    Vision processor using Google Gemini Pro Vision.

    Gemini Pro Vision provides:
    - Strong multimodal understanding
    - Good performance on diagrams and technical content
    - Cost-effective alternative to GPT-4o
    """

    ANALYSIS_PROMPT = """Analyze this image as a technical diagram expert.

Provide your analysis in JSON format with these fields:
{
    "description": "Detailed description of what the image shows",
    "diagram_type": "flowchart|architecture|chart|sequence|uml|schematic|screenshot|photo|document_scan|unknown",
    "entities": ["list", "of", "key", "entities", "or", "components"],
    "relationships": ["entity1 connects to entity2", "data flows from A to B"],
    "text_content": "Any visible text labels or annotations",
    "confidence": 0.85
}

Focus on:
1. What the image represents semantically
2. Key components and their roles
3. How elements relate to each other
4. Any visible text that provides context"""

    def __init__(self, model: str = "gemini-1.5-pro"):
        """
        Initialize Gemini Vision processor.

        Args:
            model: Model to use (default: gemini-1.5-pro)
        """
        self.model = model

    def is_available(self) -> bool:
        """Check if Google API is configured."""
        try:
            import google.generativeai as genai
            # Check if API key is configured
            # Gemini uses GOOGLE_API_KEY environment variable
            import os
            return bool(os.environ.get('GOOGLE_API_KEY'))
        except ImportError:
            return False

    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        prompt: Optional[str] = None,
    ) -> VisionResult:
        """
        Analyze image using Gemini Pro Vision.

        Args:
            image_bytes: Raw image data
            filename: Original filename
            prompt: Optional custom prompt

        Returns:
            VisionResult with description and metadata
        """
        try:
            import google.generativeai as genai
        except ImportError:
            raise RuntimeError("google-generativeai package not installed")

        if not self.is_available():
            raise RuntimeError("Google API key not configured")

        # Determine MIME type
        mime_type = self._get_mime_type(filename)

        # Build prompt
        user_prompt = prompt or self.ANALYSIS_PROMPT
        user_prompt = f"{user_prompt}\n\nFilename: {filename}"

        try:
            model = genai.GenerativeModel(self.model)

            # Create image part for Gemini
            image_part = {
                "mime_type": mime_type,
                "data": image_bytes
            }

            response = await model.generate_content_async([
                user_prompt,
                image_part
            ])

            content = response.text

            # Parse response
            result = self._parse_response(content, filename)

            logger.info(
                f"[GeminiVision] Analyzed {filename}: "
                f"type={result.diagram_type.value}, "
                f"entities={len(result.entities)}"
            )

            return result

        except Exception as e:
            logger.error(f"[GeminiVision] Analysis failed for {filename}: {e}")
            raise

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename."""
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        mime_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
        }
        return mime_map.get(ext, 'image/png')

    def _parse_response(self, content: str, filename: str) -> VisionResult:
        """Parse Gemini response into VisionResult."""
        try:
            # Try to extract JSON from response
            if '```json' in content:
                json_str = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                json_str = content.split('```')[1].split('```')[0].strip()
            else:
                json_str = content.strip()

            data = json.loads(json_str)

            # Map diagram type
            diagram_type_str = data.get('diagram_type', 'unknown').lower()
            try:
                diagram_type = DiagramType(diagram_type_str)
            except ValueError:
                diagram_type = DiagramType.UNKNOWN

            return VisionResult(
                description=data.get('description', ''),
                diagram_type=diagram_type,
                entities=data.get('entities', []),
                relationships=data.get('relationships', []),
                text_content=data.get('text_content'),
                confidence=float(data.get('confidence', 0.85)),
                model_used=self.model,
                metadata={'filename': filename},
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"[GeminiVision] Failed to parse JSON response: {e}")
            return VisionResult(
                description=content,
                diagram_type=DiagramType.UNKNOWN,
                confidence=0.7,
                model_used=self.model,
                metadata={'filename': filename, 'parse_error': str(e)},
            )
