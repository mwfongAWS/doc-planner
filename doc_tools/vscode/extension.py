"""VSCode extension integration for AWS Documentation Tools."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from doc_tools.bedrock.client import BedrockClient
from doc_tools.bedrock.knowledge_base import KnowledgeBaseClient
from doc_tools.core.content_plan import ContentPlan
from doc_tools.workflows.content_planning import ContentPlanningWorkflow
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger
from doc_tools.utils.aws_auth import check_aws_credentials, setup_aws_credentials

logger = get_logger(__name__)

class VSCodeExtension:
    """VSCode extension integration for AWS Documentation Tools."""
    
    def __init__(self):
        """Initialize the VSCode extension."""
        self.workspace_path = None
        self.current_workflow = None
        self.current_kb_id = None
        self.current_model_id = None
    
    def initialize(self, workspace_path: Union[str, Path]) -> Dict[str, Any]:
        """Initialize the extension with workspace path.
        
        Args:
            workspace_path: Path to VSCode workspace
            
        Returns:
            Initialization status
        """
        self.workspace_path = Path(workspace_path)
        settings.user.workspace_path = self.workspace_path
        settings.save()
        
        # Check if AWS credentials are configured
        has_credentials = check_aws_credentials()
        
        return {
            "initialized": True,
            "workspace_path": str(self.workspace_path),
            "has_aws_credentials": has_credentials,
            "bedrock_models": settings.bedrock.available_models,
            "default_model": settings.bedrock.default_model_id
        }
    
    def setup_aws_credentials(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """Set up AWS credentials.
        
        Args:
            profile_name: AWS profile name
            
        Returns:
            Setup status
        """
        try:
            result = setup_aws_credentials(profile_name)
            if result["success"]:
                settings.user.aws_profile = result["profile_name"]
                settings.save()
            return result
        except Exception as e:
            logger.error(f"Failed to set up AWS credentials: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """List available Bedrock models.
        
        Returns:
            List of available models
        """
        try:
            client = BedrockClient(profile_name=settings.user.aws_profile)
            models = client.list_foundation_models()
            return models
        except Exception as e:
            logger.error(f"Failed to list available models: {e}")
            return []
    
    def create_knowledge_base(
        self,
        name: str,
        description: str,
        s3_bucket_name: str,
        s3_prefix: str = "knowledge-base/"
    ) -> Dict[str, Any]:
        """Create a knowledge base.
        
        Args:
            name: Knowledge base name
            description: Knowledge base description
            s3_bucket_name: S3 bucket name
            s3_prefix: S3 prefix
            
        Returns:
            Creation status
        """
        try:
            workflow = ContentPlanningWorkflow(
                profile_name=settings.user.aws_profile,
                workspace_path=self.workspace_path
            )
            
            kb_id = workflow.create_knowledge_base(
                name=name,
                description=description,
                s3_bucket_name=s3_bucket_name,
                s3_prefix=s3_prefix
            )
            
            self.current_kb_id = kb_id
            self.current_workflow = workflow
            
            return {
                "success": True,
                "kb_id": kb_id
            }
        except Exception as e:
            logger.error(f"Failed to create knowledge base: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def upload_resources(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """Upload resources to knowledge base.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Upload status
        """
        if not self.current_workflow or not self.current_kb_id:
            return {
                "success": False,
                "error": "No active knowledge base. Create or select a knowledge base first."
            }
        
        try:
            responses = self.current_workflow.upload_resources(file_paths)
            
            return {
                "success": True,
                "uploaded_files": len(responses),
                "file_names": [Path(path).name for path in file_paths]
            }
        except Exception as e:
            logger.error(f"Failed to upload resources: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_content_plan(
        self,
        template_name: str,
        context: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Generate a content plan.
        
        Args:
            template_name: Template name
            context: Context variables
            output_path: Output path
            
        Returns:
            Generated content plan
        """
        try:
            if not self.current_workflow:
                self.current_workflow = ContentPlanningWorkflow(
                    kb_id=self.current_kb_id,
                    model_id=self.current_model_id,
                    profile_name=settings.user.aws_profile,
                    workspace_path=self.workspace_path
                )
            
            plan = self.current_workflow.generate_content_plan(
                template_name=template_name,
                context=context,
                output_path=output_path
            )
            
            return {
                "success": True,
                "plan": plan,
                "output_path": str(self.current_workflow.plan_path)
            }
        except Exception as e:
            logger.error(f"Failed to generate content plan: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def refine_content_plan(
        self,
        feedback: str,
        output_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Refine a content plan.
        
        Args:
            feedback: User feedback
            output_path: Output path
            
        Returns:
            Refined content plan
        """
        if not self.current_workflow:
            return {
                "success": False,
                "error": "No active content plan. Generate a content plan first."
            }
        
        try:
            plan = self.current_workflow.refine_content_plan(
                feedback=feedback,
                output_path=output_path
            )
            
            return {
                "success": True,
                "plan": plan,
                "output_path": str(self.current_workflow.plan_path)
            }
        except Exception as e:
            logger.error(f"Failed to refine content plan: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_content_plan(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a content plan.
        
        Args:
            file_path: File path
            
        Returns:
            Loaded content plan
        """
        try:
            if not self.current_workflow:
                self.current_workflow = ContentPlanningWorkflow(
                    kb_id=self.current_kb_id,
                    model_id=self.current_model_id,
                    profile_name=settings.user.aws_profile,
                    workspace_path=self.workspace_path
                )
            
            plan = self.current_workflow.load_content_plan(file_path)
            
            return {
                "success": True,
                "plan": plan
            }
        except Exception as e:
            logger.error(f"Failed to load content plan: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def save_content_plan(self, file_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Save a content plan.
        
        Args:
            file_path: File path
            
        Returns:
            Save status
        """
        if not self.current_workflow:
            return {
                "success": False,
                "error": "No active content plan. Generate a content plan first."
            }
        
        try:
            self.current_workflow.save_content_plan(file_path)
            
            return {
                "success": True,
                "output_path": str(self.current_workflow.plan_path)
            }
        except Exception as e:
            logger.error(f"Failed to save content plan: {e}")
            return {
                "success": False,
                "error": str(e)
            }