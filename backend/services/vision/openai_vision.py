"""
GPT-4o Vision Processor

Implements Vision LLM analysis using OpenAI's GPT-4o model.
"""

import base64
import logging
import json
from typing import Optional

from services.vision.base import VisionProcessor, VisionResult, DiagramType

logger = logging.getLogger(__name__)


class GPT4VisionProcessor(VisionProcessor):
    """
    Vision processor using OpenAI GPT-4o.

    GPT-4o provides excellent multimodal understanding with:
    - High accuracy on technical diagrams
    - Good text extraction from images
    - Structured analysis capabilities
    """

    SYSTEM_PROMPT = """You are an expert at analyzing technical images and diagrams.
Your task is to provide detailed, accurate descriptions that capture the semantic meaning
of images for use in a knowledge retrieval system.

For each image, you should:
1. Describe what the image shows in detail
2. Identify the type of diagram/image (flowchart, architecture, chart, screenshot, photo, etc.)
3. List key entities, components, or concepts visible
4. Describe relationships or data flows between elements
5. Extract any visible text labels

Output your analysis in JSON format with these fields:
{
    "description": "Detailed description of the image",
    "diagram_type": "flowchart|architecture|chart|sequence|uml|schematic|screenshot|photo|document_scan|unknown",
    "entities": ["list", "of", "key", "entities"],
    "relationships": ["entity1 connects to entity2", "..."],
    "text_content": "Any visible text in the image",
    "confidence": 0.0-1.0
}"""

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize GPT-4o Vision processor.

        Args:
            model: Model to use (default: gpt-4o)
        """
        self.model = model

    def is_available(self) -> bool:
        """Check if OpenAI API is configured."""
        from core.config import settings
        return bool(settings.OPENAI_API_KEY)

    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        prompt: Optional[str] = None,
    ) -> VisionResult:
        """
        Analyze image using GPT-4o Vision.

        Args:
            image_bytes: Raw image data
            filename: Original filename
            prompt: Optional custom prompt

        Returns:
            VisionResult with description and metadata
        """
        from openai import AsyncOpenAI
        from core.config import settings

        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        # Determine MIME type from filename
        mime_type = self._get_mime_type(filename)

        # Build user prompt
        user_prompt = prompt or self.get_default_prompt()
        user_prompt = f"{user_prompt}\n\nFilename: {filename}"

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}",
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=1500,
                temperature=0.3,  # Lower temperature for more consistent analysis
            )

            content = response.choices[0].message.content

            # Parse JSON response
            result = self._parse_response(content, filename)

            logger.info(
                f"[GPT4Vision] Analyzed {filename}: "
                f"type={result.diagram_type.value}, "
                f"entities={len(result.entities)}"
            )

            return result

        except Exception as e:
            logger.error(f"[GPT4Vision] Analysis failed for {filename}: {e}")
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
        """Parse GPT-4o response into VisionResult."""
        try:
            # Try to extract JSON from response
            # Sometimes the model wraps JSON in markdown code blocks
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
                confidence=float(data.get('confidence', 0.9)),
                model_used=self.model,
                metadata={'filename': filename, 'raw_response': content[:500]},
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"[GPT4Vision] Failed to parse JSON response: {e}")
            # Fall back to treating the entire response as description
            return VisionResult(
                description=content,
                diagram_type=DiagramType.UNKNOWN,
                confidence=0.7,
                model_used=self.model,
                metadata={'filename': filename, 'parse_error': str(e)},
            )
