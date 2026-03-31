import re
from typing import Optional

def youtube_embed_url(url: str) -> str:
    """
    Converts various YouTube URL formats (watch, short, mobile) to the embed format.
    
    Args:
        url: The YouTube video URL.
        
    Returns:
        The embed URL string or the original URL if no ID could be extracted.
    """
    if not url:
        return ""
    
    # Already in embed format
    if "youtube.com/embed/" in url:
        return url
        
    video_id = None
    
    # Short links: https://youtu.be/abc
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
    
    # Regular watch links: https://www.youtube.com/watch?v=abc
    elif "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
        
    # Mobile links: https://m.youtube.com/watch?v=abc
    elif "youtube.com/v/" in url:
        video_id = url.split("youtube.com/v/")[1].split("?")[0]
        
    if video_id:
        return f"https://www.youtube.com/embed/{video_id}"
        
    return url
