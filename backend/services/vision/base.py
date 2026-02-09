"""
Vision Processor Base Classes

Abstract base class and data structures for Vision LLM processors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class DiagramType(str, Enum):
    """Types of diagrams that can be detected."""
    FLOWCHART = "flowchart"
    ARCHITECTURE = "architecture"
    SEQUENCE = "sequence"
    ER_DIAGRAM = "er_diagram"
    UML = "uml"
    CHART = "chart"
    GRAPH = "graph"
    SCHEMATIC = "schematic"
    INFOGRAPHIC = "infographic"
    SCREENSHOT = "screenshot"
    PHOTO = "photo"
    DOCUMENT_SCAN = "document_scan"
    UNKNOWN = "unknown"


@dataclass
class VisionResult:
    """
    Result from Vision LLM analysis.

    Attributes:
        description: Detailed semantic description of the image
        diagram_type: Type of diagram/image detected
        entities: Key entities, concepts, or objects identified
        relationships: Relationships between entities (if applicable)
        text_content: Any visible text in the image
        confidence: Confidence score (0.0 - 1.0)
        model_used: Name of the model that produced this result
        metadata: Additional metadata from the analysis
    """
    description: str
    diagram_type: DiagramType | None = DiagramType.UNKNOWN
    entities: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    text_content: str | None = None
    confidence: float = 0.0
    model_used: str = "unknown"
    metadata: dict = field(default_factory=dict)

    def to_searchable_text(self) -> str:
        """
        Convert the vision result to searchable text for embedding.

        Combines description, entities, relationships, and text content
        into a cohesive text representation.
        """
        parts = []

        # Add diagram type context
        if self.diagram_type and self.diagram_type != DiagramType.UNKNOWN:
            parts.append(f"[{self.diagram_type.value.replace('_', ' ').title()}]")

        # Add main description
        if self.description:
            parts.append(self.description)

        # Add entities
        if self.entities:
            parts.append(f"Key elements: {', '.join(self.entities)}")

        # Add relationships
        if self.relationships:
            parts.append(f"Relationships: {'; '.join(self.relationships)}")

        # Add text content
        if self.text_content and self.text_content.strip():
            parts.append(f"Visible text: {self.text_content}")

        return "\n\n".join(parts)


class VisionProcessor(ABC):
    """
    Abstract base class for Vision LLM processors.

    Implementations should handle image analysis and return
    structured VisionResult objects.
    """

    @abstractmethod
    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        prompt: str | None = None,
    ) -> VisionResult:
        """
        Analyze an image and return semantic description.

        Args:
            image_bytes: Raw image data
            filename: Original filename (for context)
            prompt: Optional custom prompt for analysis

        Returns:
            VisionResult with description and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this processor is available (API key configured, etc.)."""
        pass

    def get_default_prompt(self) -> str:
        """Get the default analysis prompt."""
        return """Analyze this image as a technical diagram expert.

Provide:
1. A detailed description of what the image shows
2. The type of diagram or image (flowchart, architecture, chart, screenshot, etc.)
3. Key entities, components, or objects visible
4. Relationships or connections between elements
5. Any visible text labels or annotations

Format your response as structured analysis that would be useful for search and retrieval."""
