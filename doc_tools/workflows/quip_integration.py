"""Quip integration workflow."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from doc_tools.utils.quip_exporter import QuipExporter
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

class QuipIntegrationWorkflow:
    """Quip integration workflow."""
    
    def __init__(
        self,
        api_token: str,
        workspace_path: Optional[Union[str, Path]] = None,
    ):
        """Initialize the Quip integration workflow.
        
        Args:
            api_token: Quip API token
            workspace_path: Workspace path
        """
        self.api_token = api_token
        self.workspace_path = Path(workspace_path or settings.user.workspace_path or Path.cwd())
        
        # Initialize Quip exporter
        self.quip_exporter = QuipExporter(api_token=self.api_token)
    
    def export_content_plan(
        self,
        content_plan_path: Union[str, Path],
        folder_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        """Export a content plan to Quip.
        
        Args:
            content_plan_path: Path to content plan
            folder_id: Quip folder ID
            title: Document title
            
        Returns:
            Quip document URL
        """
        content_plan_path = Path(content_plan_path)
        
        # Export content plan
        quip_url = self.quip_exporter.export_content_plan(
            content_plan=content_plan_path,
            folder_id=folder_id,
            title=title
        )
        
        logger.info(f"Content plan exported to Quip: {quip_url}")
        return quip_url
    
    def export_multiple_content_plans(
        self,
        content_plan_paths: List[Union[str, Path]],
        folder_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Export multiple content plans to Quip.
        
        Args:
            content_plan_paths: List of paths to content plans
            folder_id: Quip folder ID
            
        Returns:
            Dictionary mapping content plan paths to Quip URLs
        """
        results = {}
        
        for path in content_plan_paths:
            path = Path(path)
            try:
                quip_url = self.export_content_plan(
                    content_plan_path=path,
                    folder_id=folder_id
                )
                results[str(path)] = quip_url
            except Exception as e:
                logger.error(f"Failed to export content plan {path}: {e}")
                results[str(path)] = f"Error: {str(e)}"
        
        return results