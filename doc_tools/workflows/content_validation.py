"""Content validation workflow."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from doc_tools.bedrock.client import BedrockClient
from doc_tools.bedrock.knowledge_base import KnowledgeBaseClient
from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

class ContentValidationWorkflow:
    """Content validation workflow."""
    
    def __init__(
        self,
        kb_id: str,
        model_id: Optional[str] = None,
        profile_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize the content validation workflow.
        
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
        
        # Validation results
        self.validation_results = None
    
    def validate_file(
        self,
        file_path: Union[str, Path],
        scope: str = "full",
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Validate a file against the knowledge base.
        
        Args:
            file_path: Path to file
            scope: Validation scope (full, section, paragraph, sentence)
            output_path: Output path for validation results
            
        Returns:
            Validation results
        """
        file_path = Path(file_path)
        
        # Read file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split content based on scope
        chunks = self._split_content(content, scope)
        
        # Validate each chunk
        validated_chunks = []
        issues_found = 0
        
        for chunk in chunks:
            result = self._validate_chunk(chunk)
            validated_chunks.append(result)
            
            if result["status"] != "valid":
                issues_found += 1
        
        # Compile validation results
        self.validation_results = {
            "file_path": str(file_path),
            "scope": scope,
            "overall_status": "valid" if issues_found == 0 else "issues_found",
            "summary": {
                "validated_chunks": len(chunks),
                "issues_found": issues_found
            },
            "chunks": validated_chunks
        }
        
        # Save validation results if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(self.validation_results, f, indent=2)
            
            logger.info(f"Validation results saved to {output_path}")
        
        return self.validation_results
    
    def generate_validation_report(
        self,
        output_format: str = "markdown",
        output_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """Generate a validation report.
        
        Args:
            output_format: Output format (markdown or html)
            output_path: Output path for report
            
        Returns:
            Validation report
        """
        if not self.validation_results:
            raise ValueError("No validation results available")
        
        # Generate report based on format
        if output_format == "markdown":
            report = self._generate_markdown_report()
        else:
            report = self._generate_html_report()
        
        # Save report if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(report)
            
            logger.info(f"Validation report saved to {output_path}")
        
        return report
    
    def _split_content(self, content: str, scope: str) -> List[str]:
        """Split content based on scope.
        
        Args:
            content: Content to split
            scope: Validation scope (full, section, paragraph, sentence)
            
        Returns:
            List of content chunks
        """
        if scope == "full":
            return [content]
        elif scope == "section":
            # Split by markdown headings or XML section tags
            if "<section" in content:
                # XML content
                sections = re.split(r'<section[^>]*>', content)
                # Remove empty sections and clean up
                return [s.strip() for s in sections if s.strip()]
            else:
                # Markdown content
                sections = re.split(r'\n#{1,6} ', content)
                # Remove empty sections and clean up
                return [s.strip() for s in sections if s.strip()]
        elif scope == "paragraph":
            # Split by blank lines
            paragraphs = re.split(r'\n\s*\n', content)
            # Remove empty paragraphs and clean up
            return [p.strip() for p in paragraphs if p.strip()]
        elif scope == "sentence":
            # Simple sentence splitting (not perfect but good enough)
            sentences = re.split(r'(?<=[.!?])\s+', content)
            # Remove empty sentences and clean up
            return [s.strip() for s in sentences if s.strip()]
        else:
            raise ValueError(f"Invalid scope: {scope}")
    
    def _validate_chunk(self, chunk: str) -> Dict[str, Any]:
        """Validate a content chunk against the knowledge base.
        
        Args:
            chunk: Content chunk
            
        Returns:
            Validation result
        """
        # Query knowledge base for relevant information
        kb_results = self.kb_client.query_knowledge_base(
            kb_id=self.kb_id,
            query=chunk[:500],  # Use first 500 chars as query
            max_results=3
        )
        
        # Extract relevant passages
        passages = []
        for result in kb_results.get('retrievalResults', []):
            for block in result.get('content', {}).get('text', {}).get('textBlock', {}).get('span', []):
                passages.append(block.get('content', ''))
        
        # Create validation prompt
        prompt = f"""
        CONTENT TO VALIDATE:
        {chunk}
        
        RELEVANT INFORMATION FROM KNOWLEDGE BASE:
        {passages[0] if passages else "No relevant information found."}
        
        {passages[1] if len(passages) > 1 else ""}
        
        {passages[2] if len(passages) > 2 else ""}
        
        INSTRUCTIONS:
        Please validate the content against the information from the knowledge base.
        Check for factual accuracy, completeness, and consistency.
        
        Return your validation result in the following JSON format:
        {{
            "status": "valid" or "issues_found",
            "message": "Brief explanation of validation result",
            "suggestions": ["Suggestion 1", "Suggestion 2", ...] (empty list if no suggestions)
        }}
        """
        
        # Invoke model for validation
        response = self.bedrock_client.invoke_model(
            model_id=self.model_id,
            prompt=prompt,
            temperature=0.2,  # Lower temperature for more consistent results
            max_tokens=1024
        )
        
        # Parse response as JSON
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, create a default result
            result = {
                "status": "error",
                "message": "Failed to parse validation result",
                "suggestions": []
            }
        
        # Add content to result
        result["content"] = chunk
        
        return result
    
    def _generate_markdown_report(self) -> str:
        """Generate a markdown validation report.
        
        Returns:
            Markdown report
        """
        results = self.validation_results
        
        report = f"# Content Validation Report\n\n"
        report += f"**File:** {results['file_path']}\n"
        report += f"**Scope:** {results['scope']}\n"
        report += f"**Status:** {results['overall_status']}\n"
        report += f"**Chunks Validated:** {results['summary']['validated_chunks']}\n"
        report += f"**Issues Found:** {results['summary']['issues_found']}\n\n"
        
        if results['summary']['issues_found'] > 0:
            report += "## Issues\n\n"
            
            for i, chunk in enumerate(results['chunks']):
                if chunk['status'] != 'valid':
                    report += f"### Issue {i+1}\n\n"
                    report += f"**Content:**\n\n```\n{chunk['content']}\n```\n\n"
                    report += f"**Status:** {chunk['status']}\n\n"
                    report += f"**Message:** {chunk['message']}\n\n"
                    
                    if chunk['suggestions']:
                        report += "**Suggestions:**\n\n"
                        for suggestion in chunk['suggestions']:
                            report += f"- {suggestion}\n"
                        report += "\n"
        
        return report
    
    def _generate_html_report(self) -> str:
        """Generate an HTML validation report.
        
        Returns:
            HTML report
        """
        results = self.validation_results
        
        report = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Content Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #0066cc; }}
                h2 {{ color: #0066cc; margin-top: 30px; }}
                h3 {{ margin-top: 20px; }}
                .summary {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .valid {{ color: green; }}
                .issues {{ color: orange; }}
                .error {{ color: red; }}
                .content {{ background-color: #f8f8f8; padding: 15px; border-left: 4px solid #ddd; margin: 10px 0; }}
                .suggestions {{ margin-left: 20px; }}
            </style>
        </head>
        <body>
            <h1>Content Validation Report</h1>
            
            <div class="summary">
                <p><strong>File:</strong> {results['file_path']}</p>
                <p><strong>Scope:</strong> {results['scope']}</p>
                <p><strong>Status:</strong> <span class="{'valid' if results['overall_status'] == 'valid' else 'issues'}">{results['overall_status']}</span></p>
                <p><strong>Chunks Validated:</strong> {results['summary']['validated_chunks']}</p>
                <p><strong>Issues Found:</strong> {results['summary']['issues_found']}</p>
            </div>
        """
        
        if results['summary']['issues_found'] > 0:
            report += "<h2>Issues</h2>"
            
            for i, chunk in enumerate(results['chunks']):
                if chunk['status'] != 'valid':
                    report += f"<h3>Issue {i+1}</h3>"
                    report += f"<div class='content'><pre>{chunk['content']}</pre></div>"
                    report += f"<p><strong>Status:</strong> <span class='issues'>{chunk['status']}</span></p>"
                    report += f"<p><strong>Message:</strong> {chunk['message']}</p>"
                    
                    if chunk['suggestions']:
                        report += "<p><strong>Suggestions:</strong></p><ul class='suggestions'>"
                        for suggestion in chunk['suggestions']:
                            report += f"<li>{suggestion}</li>"
                        report += "</ul>"
        
        report += """
        </body>
        </html>
        """
        
        return report