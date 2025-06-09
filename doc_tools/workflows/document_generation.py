"""Document generation workflow."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from doc_tools.bedrock.client import BedrockClient
from doc_tools.core.document_generator import DocumentGenerator
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger
from doc_tools.utils.templates import load_template

logger = get_logger(__name__)

class DocumentGenerationWorkflow:
    """Document generation workflow."""
    
    def __init__(
        self,
        model_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
        workspace_path: Optional[Union[str, Path]] = None,
    ):
        """Initialize the document generation workflow.
        
        Args:
            model_id: Model ID to use
            profile_name: AWS profile name
            region: AWS region
            workspace_path: Workspace path
        """
        self.model_id = model_id or settings.bedrock.default_model_id
        self.profile_name = profile_name or settings.user.aws_profile
        self.region = region or settings.bedrock.region
        self.workspace_path = Path(workspace_path or settings.user.workspace_path or Path.cwd())
        
        # Initialize document generator
        self.document_generator = DocumentGenerator(
            model_id=self.model_id,
            profile_name=self.profile_name,
            region=self.region
        )
        
        # Workflow state
        self.document_path = None
        self.current_document = None
        self.current_plan = None
    
    def generate_document(
        self,
        plan_path: Union[str, Path],
        output_format: str = "markdown",
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Generate a document from a content plan.
        
        Args:
            plan_path: Path to content plan
            output_format: Output format (markdown or zonbook)
            output_path: Output path
            
        Returns:
            Generated document
        """
        plan_path = Path(plan_path)
        
        # Load content plan
        with open(plan_path, 'r') as f:
            if plan_path.suffix == '.json':
                self.current_plan = json.load(f)
            else:
                content = f.read()
                try:
                    self.current_plan = json.loads(content)
                except json.JSONDecodeError:
                    self.current_plan = {"raw_content": content}
        
        # Determine output path if not provided
        if not output_path:
            if output_format == "markdown":
                output_path = plan_path.with_suffix(".md")
            else:
                output_path = plan_path.with_suffix(".xml")
        
        self.document_path = Path(output_path)
        
        # Generate document
        self.current_document = self.document_generator.generate_document(
            content_plan=self.current_plan,
            output_format=output_format,
            output_path=self.document_path
        )
        
        return self.current_document
    
    def refine_document(
        self,
        feedback: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Refine document based on feedback.
        
        Args:
            feedback: User feedback
            output_path: Output path
            
        Returns:
            Refined document
        """
        if not self.current_document:
            raise ValueError("No document to refine")
        
        if not output_path and self.document_path:
            output_path = self.document_path
        
        self.document_path = Path(output_path)
        
        # Refine document
        self.current_document = self.document_generator.refine_document(
            document=self.current_document,
            feedback=feedback,
            output_path=self.document_path
        )
        
        return self.current_document
    
    def load_document(self, file_path: Union[str, Path]) -> str:
        """Load a document.
        
        Args:
            file_path: File path
            
        Returns:
            Document content
        """
        file_path = Path(file_path)
        
        with open(file_path, 'r') as f:
            self.current_document = f.read()
        
        self.document_path = file_path
        return self.current_document
    
    def save_document(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save the document.
        
        Args:
            file_path: File path
        """
        if not self.current_document:
            raise ValueError("No document to save")
        
        if not file_path and self.document_path:
            file_path = self.document_path
        elif not file_path:
            file_path = self.workspace_path / "document.md"
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(self.current_document)
        
        self.document_path = file_path
        logger.info(f"Document saved to {file_path}")