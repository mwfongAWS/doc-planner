"""Content plan generation and management."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from doc_tools.bedrock.client import BedrockClient
from doc_tools.bedrock.knowledge_base import KnowledgeBaseClient
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger
from doc_tools.utils.templates import load_template

logger = get_logger(__name__)

class ContentPlan:
    """Content plan generator and manager."""
    
    def __init__(
        self,
        kb_id: Optional[str] = None,
        model_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize the content plan generator.
        
        Args:
            kb_id: Knowledge base ID
            model_id: Model ID to use
            profile_name: AWS profile name
            region: AWS region
        """
        self.kb_id = kb_id
        self.model_id = model_id or settings.bedrock.default_model_id
        self.profile_name = profile_name or settings.user.aws_profile
        self.region = region or settings.bedrock.region
        
        # Initialize clients
        self.bedrock_client = BedrockClient(profile_name=self.profile_name, region=self.region)
        self.kb_client = KnowledgeBaseClient(profile_name=self.profile_name, region=self.region)
        
        # Content plan data
        self.plan_data = {}
        
    def generate_content_plan(
        self,
        prompt_template: str,
        context: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Generate a content plan.
        
        Args:
            prompt_template: Prompt template name or content
            context: Context variables for the template
            output_path: Path to save the content plan
            
        Returns:
            Generated content plan
        """
        # Load template if it's a name
        if not prompt_template.strip().startswith('{') and not prompt_template.strip().startswith('<'):
            prompt_template = load_template(prompt_template)
        
        # Format prompt with context
        prompt = prompt_template.format(**context)
        
        # Get relevant information from knowledge base if available
        kb_context = ""
        if self.kb_id:
            kb_results = self.kb_client.query_knowledge_base(
                kb_id=self.kb_id,
                query=prompt[:500],  # Use first 500 chars as query
                max_results=5
            )
            
            # Extract relevant passages
            passages = []
            for result in kb_results.get('retrievalResults', []):
                for block in result.get('content', {}).get('text', {}).get('textBlock', {}).get('span', []):
                    passages.append(block.get('content', ''))
            
            # Add passages to context
            if passages:
                kb_context = "RELEVANT CONTEXT FROM KNOWLEDGE BASE:\n\n" + "\n\n".join(passages) + "\n\n"
        
        # Generate content plan
        full_prompt = f"{kb_context}INSTRUCTIONS:\n\n{prompt}"
        response = self.bedrock_client.invoke_model(
            model_id=self.model_id,
            prompt=full_prompt,
            temperature=0.7,
            max_tokens=4096
        )
        
        # Parse response as JSON if possible
        try:
            self.plan_data = json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, store as raw text
            self.plan_data = {"raw_content": response}
        
        # Save content plan if output path provided
        if output_path:
            self.save_content_plan(output_path)
        
        return self.plan_data
    
    def load_content_plan(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load a content plan from file.
        
        Args:
            file_path: Path to content plan file
            
        Returns:
            Content plan data
        """
        file_path = Path(file_path)
        
        with open(file_path, 'r') as f:
            if file_path.suffix == '.json':
                self.plan_data = json.load(f)
            else:
                self.plan_data = {"raw_content": f.read()}
        
        return self.plan_data
    
    def save_content_plan(self, file_path: Union[str, Path]) -> None:
        """Save content plan to file.
        
        Args:
            file_path: Path to save content plan
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            if file_path.suffix == '.json':
                json.dump(self.plan_data, f, indent=2)
            else:
                if isinstance(self.plan_data, dict) and "raw_content" in self.plan_data:
                    f.write(self.plan_data["raw_content"])
                else:
                    f.write(json.dumps(self.plan_data, indent=2))
        
        logger.info(f"Content plan saved to {file_path}")
    
    def update_content_plan(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update content plan with new data.
        
        Args:
            updates: Updates to apply to content plan
            
        Returns:
            Updated content plan
        """
        if isinstance(self.plan_data, dict):
            self.plan_data.update(updates)
        else:
            self.plan_data = updates
        
        return self.plan_data
    
    def refine_content_plan(
        self,
        feedback: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Refine content plan based on feedback.
        
        Args:
            feedback: User feedback
            output_path: Path to save refined content plan
            
        Returns:
            Refined content plan
        """
        # Create prompt for refinement
        current_plan = json.dumps(self.plan_data, indent=2) if isinstance(self.plan_data, dict) else self.plan_data
        
        prompt = f"""
        CURRENT CONTENT PLAN:
        {current_plan}
        
        USER FEEDBACK:
        {feedback}
        
        INSTRUCTIONS:
        Please refine the content plan based on the user's feedback. Return the updated content plan in the same format.
        """
        
        # Generate refined content plan
        response = self.bedrock_client.invoke_model(
            model_id=self.model_id,
            prompt=prompt,
            temperature=0.7,
            max_tokens=4096
        )
        
        # Parse response as JSON if possible
        try:
            self.plan_data = json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, store as raw text
            self.plan_data = {"raw_content": response}
        
        # Save refined content plan if output path provided
        if output_path:
            self.save_content_plan(output_path)
        
        return self.plan_data
