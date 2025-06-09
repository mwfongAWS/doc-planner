"""Content planning workflow."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from doc_tools.bedrock.client import BedrockClient
from doc_tools.bedrock.knowledge_base import KnowledgeBaseClient
from doc_tools.core.content_plan import ContentPlan
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger
from doc_tools.utils.templates import load_template

logger = get_logger(__name__)

class ContentPlanningWorkflow:
    """Content planning workflow."""
    
    def __init__(
        self,
        kb_id: Optional[str] = None,
        model_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
        workspace_path: Optional[Union[str, Path]] = None,
    ):
        """Initialize the content planning workflow.
        
        Args:
            kb_id: Knowledge base ID
            model_id: Model ID to use
            profile_name: AWS profile name
            region: AWS region
            workspace_path: Workspace path
        """
        self.kb_id = kb_id
        self.model_id = model_id or settings.bedrock.default_model_id
        self.profile_name = profile_name or settings.user.aws_profile
        self.region = region or settings.bedrock.region
        self.workspace_path = Path(workspace_path or settings.user.workspace_path or Path.cwd())
        
        # Initialize clients
        self.content_plan = ContentPlan(
            kb_id=self.kb_id,
            model_id=self.model_id,
            profile_name=self.profile_name,
            region=self.region
        )
        
        self.kb_client = KnowledgeBaseClient(
            profile_name=self.profile_name,
            region=self.region
        )
        
        # Workflow state
        self.current_plan = {}
        self.plan_path = None
    
    def create_knowledge_base(
        self,
        name: str,
        description: str,
        s3_bucket_name: str,
        s3_prefix: str = "knowledge-base/",
    ) -> str:
        """Create a knowledge base.
        
        Args:
            name: Knowledge base name
            description: Knowledge base description
            s3_bucket_name: S3 bucket name
            s3_prefix: S3 prefix
            
        Returns:
            Knowledge base ID
        """
        response = self.kb_client.create_knowledge_base(
            name=name,
            description=description,
            s3_bucket_name=s3_bucket_name,
            s3_prefix=s3_prefix
        )
        
        self.kb_id = response["knowledgeBaseId"]
        return self.kb_id
    
    def upload_resources(self, file_paths: List[Union[str, Path]]) -> List[Dict[str, Any]]:
        """Upload resources to the knowledge base.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            List of upload responses
        """
        if not self.kb_id:
            raise ValueError("Knowledge base ID not set")
        
        responses = []
        for file_path in file_paths:
            response = self.kb_client.upload_document(
                kb_id=self.kb_id,
                file_path=file_path
            )
            responses.append(response)
        
        return responses
    
    def generate_content_plan(
        self,
        template_name: str,
        context: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Generate a content plan.
        
        Args:
            template_name: Template name
            context: Context variables
            output_path: Output path
            
        Returns:
            Content plan data
        """
        if not output_path:
            output_path = self.workspace_path / f"content_plan_{template_name}.json"
        
        self.plan_path = Path(output_path)
        self.current_plan = self.content_plan.generate_content_plan(
            prompt_template=template_name,
            context=context,
            output_path=self.plan_path
        )
        
        return self.current_plan
    
    def refine_content_plan(
        self,
        feedback: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Refine the content plan.
        
        Args:
            feedback: User feedback
            output_path: Output path
            
        Returns:
            Refined content plan
        """
        if not self.current_plan:
            raise ValueError("No content plan to refine")
        
        if not output_path and self.plan_path:
            output_path = self.plan_path
        
        self.current_plan = self.content_plan.refine_content_plan(
            feedback=feedback,
            output_path=output_path
        )
        
        return self.current_plan
    
    def load_content_plan(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a content plan.
        
        Args:
            file_path: File path
            
        Returns:
            Content plan data
        """
        self.plan_path = Path(file_path)
        self.current_plan = self.content_plan.load_content_plan(file_path)
        return self.current_plan
    
    def save_content_plan(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save the content plan.
        
        Args:
            file_path: File path
        """
        if not self.current_plan:
            raise ValueError("No content plan to save")
        
        if not file_path and self.plan_path:
            file_path = self.plan_path
        elif not file_path:
            file_path = self.workspace_path / "content_plan.json"
        
        self.plan_path = Path(file_path)
        self.content_plan.save_content_plan(file_path)
