"""
URL utility functions.

Shared utilities for URL detection and parsing across the codebase.
"""

import re
from typing import List, Optional

# YouTube URL patterns for detection
# Supports: watch?v=, youtu.be/, embed/, shorts/
YOUTUBE_URL_PATTERNS: List[str] = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
]


def is_youtube_url(url: str) -> bool:
    """
    Check if a URL is a YouTube video URL.
    
    Detects standard YouTube URL formats:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID  
    - youtube.com/embed/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    
    Args:
        url: URL string to check
        
    Returns:
        True if the URL is a YouTube video URL, False otherwise
    """
    if not url:
        return False
    return any(re.match(pattern, url) for pattern in YOUTUBE_URL_PATTERNS)


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract the video ID from a YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        11-character video ID or None if not a valid YouTube URL
    """
    if not url:
        return None
    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return None
