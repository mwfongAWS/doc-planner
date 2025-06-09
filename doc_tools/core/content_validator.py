"""Content validation and cross-checking against knowledge base."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

from doc_tools.bedrock.client import BedrockClient
from doc_tools.bedrock.knowledge_base import KnowledgeBaseClient
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

class ContentValidator:
    """Content validator for cross-checking against knowledge base."""
    
    def __init__(
        self,
        kb_id: Optional[str] = None,
        model_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize the content validator.
        
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
    
    def validate_content(
        self,
        content: str,
        scope: str = "full",
        max_results: int = 5,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Validate content against knowledge base.
        
        Args:
            content: Content to validate
            scope: Validation scope ('full', 'section', 'paragraph', 'sentence')
            max_results: Maximum number of results to return
            output_path: Path to save validation results
            
        Returns:
            Validation results
        """
        if not self.kb_id:
            raise ValueError("Knowledge base ID is required for validation")
        
        # Split content based on scope
        content_chunks = self._split_content_by_scope(content, scope)
        
        validation_results = {
            "summary": {
                "total_chunks": len(content_chunks),
                "validated_chunks": 0,
                "issues_found": 0,
            },
            "chunks": []
        }
        
        # Process each chunk
        for i, chunk in enumerate(content_chunks):
            logger.info(f"Validating chunk {i+1}/{len(content_chunks)}")
            
            # Skip empty chunks
            if not chunk.strip():
                continue
            
            # Query knowledge base for relevant information
            kb_results = self.kb_client.query_knowledge_base(
                kb_id=self.kb_id,
                query=chunk[:500],  # Use first 500 chars as query
                max_results=max_results
            )
            
            # Extract relevant passages
            passages = []
            for result in kb_results.get('retrievalResults', []):
                for block in result.get('content', {}).get('text', {}).get('textBlock', {}).get('span', []):
                    passages.append(block.get('content', ''))
            
            # If no passages found, continue to next chunk
            if not passages:
                validation_results["chunks"].append({
                    "content": chunk,
                    "status": "unknown",
                    "message": "No relevant information found in knowledge base",
                    "references": []
                })
                continue
            
            # Analyze chunk against passages
            analysis = self._analyze_chunk_against_passages(chunk, passages)
            
            # Add to results
            validation_results["chunks"].append({
                "content": chunk,
                "status": analysis["status"],
                "message": analysis["message"],
                "references": analysis["references"],
                "suggestions": analysis["suggestions"]
            })
            
            # Update summary
            validation_results["summary"]["validated_chunks"] += 1
            if analysis["status"] != "valid":
                validation_results["summary"]["issues_found"] += 1
        
        # Generate overall summary
        validation_results["overall_status"] = "valid" if validation_results["summary"]["issues_found"] == 0 else "issues_found"
        
        # Save results if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            logger.info(f"Validation results saved to {output_path}")
        
        return validation_results
    
    def validate_file(
        self,
        file_path: Union[str, Path],
        scope: str = "full",
        max_results: int = 5,
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Validate file content against knowledge base.
        
        Args:
            file_path: Path to file
            scope: Validation scope ('full', 'section', 'paragraph', 'sentence')
            max_results: Maximum number of results to return
            output_path: Path to save validation results
            
        Returns:
            Validation results
        """
        file_path = Path(file_path)
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Generate default output path if not provided
        if not output_path:
            output_path = file_path.parent / f"{file_path.stem}_validation.json"
        
        return self.validate_content(
            content=content,
            scope=scope,
            max_results=max_results,
            output_path=output_path
        )
    
    def _split_content_by_scope(self, content: str, scope: str) -> List[str]:
        """Split content based on scope.
        
        Args:
            content: Content to split
            scope: Scope ('full', 'section', 'paragraph', 'sentence')
            
        Returns:
            List of content chunks
        """
        if scope == "full":
            return [content]
        elif scope == "section":
            # Split by markdown headings or XML section tags
            if "<section" in content or "</section>" in content:
                # XML content
                import re
                sections = re.split(r'<section[^>]*>|</section>', content)
                return [s for s in sections if s.strip()]
            else:
                # Markdown content
                sections = []
                current_section = []
                
                for line in content.split('\n'):
                    if line.startswith('#'):
                        if current_section:
                            sections.append('\n'.join(current_section))
                            current_section = []
                    current_section.append(line)
                
                if current_section:
                    sections.append('\n'.join(current_section))
                
                return sections
        elif scope == "paragraph":
            # Split by blank lines
            paragraphs = content.split('\n\n')
            return [p for p in paragraphs if p.strip()]
        elif scope == "sentence":
            # Simple sentence splitting (not perfect but good enough)
            import re
            sentences = re.split(r'(?<=[.!?])\s+', content)
            return [s for s in sentences if s.strip()]
        else:
            raise ValueError(f"Invalid scope: {scope}")
    
    def _analyze_chunk_against_passages(self, chunk: str, passages: List[str]) -> Dict[str, Any]:
        """Analyze content chunk against knowledge base passages.
        
        Args:
            chunk: Content chunk
            passages: Knowledge base passages
            
        Returns:
            Analysis results
        """
        # Combine passages into context
        context = "\n\n".join(passages)
        
        # Create prompt for analysis
        prompt = f"""
        CONTENT TO VALIDATE:
        {chunk}
        
        KNOWLEDGE BASE CONTEXT:
        {context}
        
        TASK:
        Analyze the content against the knowledge base context and determine if there are any:
        1. Factual inaccuracies
        2. Missing important information
        3. Outdated information
        4. Inconsistencies with the knowledge base
        
        Return your analysis as a JSON object with the following structure:
        {{
            "status": "valid" | "minor_issues" | "major_issues",
            "message": "Brief explanation of the validation result",
            "references": [
                {{
                    "text": "Relevant text from knowledge base",
                    "issue_type": "inaccuracy" | "missing" | "outdated" | "inconsistency" | "supporting"
                }}
            ],
            "suggestions": [
                "Suggestion 1",
                "Suggestion 2"
            ]
        }}
        
        If the content is fully supported by the knowledge base, use "valid" status.
        If there are minor issues that don't affect overall accuracy, use "minor_issues".
        If there are significant problems that need to be addressed, use "major_issues".
        """
        
        # Get analysis from model
        response = self.bedrock_client.invoke_model(
            model_id=self.model_id,
            prompt=prompt,
            temperature=0.2,  # Lower temperature for more consistent analysis
            max_tokens=2048
        )
        
        # Parse response as JSON
        try:
            analysis = json.loads(response)
            
            # Ensure all required fields are present
            required_fields = ["status", "message", "references", "suggestions"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = [] if field in ["references", "suggestions"] else ""
            
            return analysis
        except json.JSONDecodeError:
            # If parsing fails, return a generic result
            logger.warning(f"Failed to parse analysis response as JSON: {response[:100]}...")
            return {
                "status": "unknown",
                "message": "Failed to analyze content",
                "references": [],
                "suggestions": ["Re-run validation with different scope"]
            }
