"""Document generation from content plans."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from doc_tools.bedrock.client import BedrockClient
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger
from doc_tools.utils.templates import load_template

logger = get_logger(__name__)

class DocumentGenerator:
    """Document generator from content plans."""
    
    def __init__(
        self,
        model_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize the document generator.
        
        Args:
            model_id: Model ID to use
            profile_name: AWS profile name
            region: AWS region
        """
        self.model_id = model_id or settings.bedrock.default_model_id
        self.profile_name = profile_name or settings.user.aws_profile
        self.region = region or settings.bedrock.region
        
        # Initialize Bedrock client
        self.bedrock_client = BedrockClient(profile_name=self.profile_name, region=self.region)
    
    def generate_document(
        self,
        content_plan: Dict[str, Any],
        output_format: str = "markdown",
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Generate a document from a content plan.
        
        Args:
            content_plan: Content plan data
            output_format: Output format (markdown or zonbook)
            output_path: Output path
            
        Returns:
            Generated document
        """
        # Load appropriate template
        if output_format == "markdown":
            template_name = "document_markdown.txt"
        else:
            template_name = "document_zonbook.txt"
        
        template = load_template(template_name)
        
        # Format content plan as JSON string
        content_plan_str = json.dumps(content_plan, indent=2)
        
        # Create prompt
        prompt = f"""
        CONTENT PLAN:
        {content_plan_str}
        
        INSTRUCTIONS:
        Please generate a complete {output_format.upper()} document based on the content plan above.
        Follow the structure defined in the content plan, including all sections and subsections.
        Include all key points, examples, and visuals mentioned in the plan.
        
        {template}
        """
        
        # Generate document
        document = self.bedrock_client.invoke_model(
            model_id=self.model_id,
            prompt=prompt,
            temperature=0.7,
            max_tokens=8192
        )
        
        # Save document if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(document)
            
            logger.info(f"Document saved to {output_path}")
        
        return document
    
    def refine_document(
        self,
        document: str,
        feedback: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Refine a document based on feedback.
        
        Args:
            document: Current document
            feedback: User feedback
            output_path: Output path
            
        Returns:
            Refined document
        """
        # Create prompt for refinement
        prompt = f"""
        CURRENT DOCUMENT:
        {document}
        
        USER FEEDBACK:
        {feedback}
        
        INSTRUCTIONS:
        Please refine the document based on the user's feedback. Return the complete updated document.
        """
        
        # Generate refined document
        refined_document = self.bedrock_client.invoke_model(
            model_id=self.model_id,
            prompt=prompt,
            temperature=0.7,
            max_tokens=8192
        )
        
        # Save refined document if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(refined_document)
            
            logger.info(f"Refined document saved to {output_path}")
        
        return refined_document
    
    def generate_section(
        self,
        content_plan: Dict[str, Any],
        section_index: int,
        output_format: str = "markdown",
    ) -> str:
        """Generate a specific section of a document.
        
        Args:
            content_plan: Content plan data
            section_index: Index of section to generate
            output_format: Output format (markdown or zonbook)
            
        Returns:
            Generated section
        """
        # Validate section index
        if "sections" not in content_plan or section_index >= len(content_plan["sections"]):
            raise ValueError(f"Invalid section index: {section_index}")
        
        # Get section from content plan
        section = content_plan["sections"][section_index]
        
        # Create prompt for section generation
        prompt = f"""
        CONTENT PLAN SECTION:
        {json.dumps(section, indent=2)}
        
        DOCUMENT CONTEXT:
        Title: {content_plan.get("title", "Document")}
        Overview: {content_plan.get("overview", "")}
        
        INSTRUCTIONS:
        Please generate a complete {output_format.upper()} section based on the content plan section above.
        Include all key points, examples, and visuals mentioned in the plan.
        """
        
        # Generate section
        section_content = self.bedrock_client.invoke_model(
            model_id=self.model_id,
            prompt=prompt,
            temperature=0.7,
            max_tokens=4096
        )
        
        return section_content