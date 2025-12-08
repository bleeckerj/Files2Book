import json
import os
from pathlib import Path


def load_config(config_path=None):
    """Load configuration from config.json"""
    if config_path is None:
        # Look for config.json in the parent directory (project root)
        script_dir = Path(__file__).parent.parent
        config_path = script_dir / "config.json"
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default config if file doesn't exist
        return {
            "fonts": {
                "default_font": "FONTS/3270NerdFontMono-Regular.ttf",
                "fallback_font": None,
                "text_elements": {
                    "title": {"font": "FONTS/3270NerdFontMono-Regular.ttf", "base_size": 20},
                    "info": {"font": "FONTS/3270NerdFontMono-Regular.ttf", "base_size": 18},
                    "preview": {"font": "FONTS/3270NerdFontMono-Regular.ttf", "base_size": 12},
                    "fit": {"font": "FONTS/3270NerdFontMono-Regular.ttf", "base_size": 15}
                }
            },
            "mapbox": {
                "token_env_var": "MAPBOX_ACCESS_TOKEN"
            }
        }


def get_font_config(element_name, scale=1.0, config=None):
    """
    Get font configuration for a specific text element.
    
    Args:
        element_name: One of 'title', 'info', 'preview', 'fit'
        scale: Scale factor to apply to base font size
        config: Optional config dict (will load if None)
    
    Returns:
        dict with 'path' and 'size' keys
    """
    if config is None:
        config = load_config()
    
    # Get the project root directory (parent of util/)
    script_dir = Path(__file__).parent.parent
    
    # Get element-specific font config
    text_elements = config.get("fonts", {}).get("text_elements", {})
    element_config = text_elements.get(element_name, {})
    
    # Get font path for this element
    font_relative = element_config.get("font")
    if not font_relative:
        # Fall back to default font
        font_relative = config.get("fonts", {}).get("default_font", "FONTS/3270NerdFontMono-Regular.ttf")
    
    font_path = script_dir / font_relative
    
    # Check if font exists, fallback if needed
    if not font_path.exists():
        # Try fallback font from config
        fallback = config.get("fonts", {}).get("fallback_font")
        if fallback:
            fallback_path = script_dir / fallback
            if fallback_path.exists():
                font_path = fallback_path
        # If still doesn't exist, return the path anyway (let calling code handle)
    
    # Get scaled font size
    base_size = element_config.get("base_size", 16)  # Default to 16 if not specified
    scaled_size = int(base_size * scale)
    
    return {
        "path": font_path,
        "size": scaled_size
    }


def get_font_path(config=None):
    """Legacy function - get default font path for backward compatibility"""
    if config is None:
        config = load_config()
    
    script_dir = Path(__file__).parent.parent
    font_relative = config.get("fonts", {}).get("default_font", "FONTS/3270NerdFontMono-Regular.ttf")
    return script_dir / font_relative


def get_mapbox_token(config=None):
    """Get Mapbox token from environment variable specified in config"""
    if config is None:
        config = load_config()
    
    token_var = config.get("mapbox", {}).get("token_env_var", "MAPBOX_ACCESS_TOKEN")
    return os.getenv(token_var)
