"""Template utilities."""

import os
from pathlib import Path
from typing import Dict, Optional, Any

from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

def load_template(template_name: str) -> str:
    """Load a template by name.
    
    Args:
        template_name: Template name or path
        
    Returns:
        Template content
    """
    # Check if template_name is a path
    if os.path.exists(template_name):
        template_path = Path(template_name)
    else:
        # Check if template has extension
        if not template_name.endswith('.txt'):
            template_name = f"{template_name}.txt"
        
        # Check built-in templates
        template_path = settings.templates_dir / template_name
        
        # Check user templates
        if not template_path.exists():
            user_template_path = settings.config_dir / "templates" / template_name
            if user_template_path.exists():
                template_path = user_template_path
    
    # Load template
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")
    
    with open(template_path, 'r') as f:
        return f.read()

def save_template(template_name: str, content: str) -> Path:
    """Save a template.
    
    Args:
        template_name: Template name
        content: Template content
        
    Returns:
        Template path
    """
    # Ensure template has extension
    if not template_name.endswith('.txt'):
        template_name = f"{template_name}.txt"
    
    # Save to user templates directory
    template_dir = settings.config_dir / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    
    template_path = template_dir / template_name
    
    with open(template_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Template saved to {template_path}")
    return template_path

def list_templates() -> Dict[str, Path]:
    """List available templates.
    
    Returns:
        Dictionary of template names and paths
    """
    templates = {}
    
    # Built-in templates
    for path in settings.templates_dir.glob('*.txt'):
        templates[path.stem] = path
    
    # User templates
    user_template_dir = settings.config_dir / "templates"
    if user_template_dir.exists():
        for path in user_template_dir.glob('*.txt'):
            templates[path.stem] = path
    
    return templates