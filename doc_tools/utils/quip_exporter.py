"""Quip export utilities for content plans."""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import requests

from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

class QuipExporter:
    """Export content plans to Quip documents."""
    
    def __init__(self, api_token: str):
        """Initialize the Quip exporter.
        
        Args:
            api_token: Quip API token
        """
        self.api_token = api_token
        self.base_url = "https://platform.quip.com/1"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def export_content_plan(
        self, 
        content_plan: Union[Dict[str, Any], str, Path],
        folder_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> str:
        """Export a content plan to a Quip document.
        
        Args:
            content_plan: Content plan data or path to content plan file
            folder_id: Quip folder ID to create document in
            title: Document title (defaults to content plan title)
            
        Returns:
            Quip document URL
        """
        # Load content plan if it's a path
        if isinstance(content_plan, (str, Path)) and not isinstance(content_plan, dict):
            with open(content_plan, 'r') as f:
                if str(content_plan).endswith('.json'):
                    content_plan = json.load(f)
                else:
                    content_data = f.read()
                    try:
                        content_plan = json.loads(content_data)
                    except json.JSONDecodeError:
                        raise ValueError(f"Invalid JSON in content plan: {content_plan}")
        
        # Set title if not provided
        if not title:
            title = content_plan.get("title", "Content Plan")
        
        # Generate HTML content
        html_content = self._generate_html(content_plan)
        
        # Create Quip document
        response = requests.post(
            f"{self.base_url}/threads/new-document",
            headers=self.headers,
            json={
                "content": html_content,
                "format": "html",
                "title": title,
                "member_ids": []
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to create Quip document: {response.text}")
            raise Exception(f"Failed to create Quip document: {response.status_code}")
        
        thread_id = response.json()["thread"]["id"]
        
        # Move to folder if specified
        if folder_id:
            self._move_to_folder(thread_id, folder_id)
        
        # Return document URL
        return f"https://quip.com/{thread_id}"
    
    def _move_to_folder(self, thread_id: str, folder_id: str) -> None:
        """Move a thread to a folder.
        
        Args:
            thread_id: Thread ID
            folder_id: Folder ID
        """
        response = requests.post(
            f"{self.base_url}/folders/{folder_id}/add-members",
            headers=self.headers,
            json={
                "member_ids": [thread_id]
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to move thread to folder: {response.text}")
    
    def _generate_html(self, content_plan: Dict[str, Any]) -> str:
        """Generate HTML content for Quip document.
        
        Args:
            content_plan: Content plan data
            
        Returns:
            HTML content
        """
        html = f"""
        <h1>{content_plan.get('title', 'Content Plan')}</h1>
        
        <h2>Feature Overview</h2>
        <p><strong>Summary:</strong> {content_plan.get('overview', {}).get('summary', '')}</p>
        <p><strong>Primary Use Case:</strong> {content_plan.get('overview', {}).get('primary_use_case', '')}</p>
        <p><strong>Problem Solved:</strong> {content_plan.get('overview', {}).get('problem_solved', '')}</p>
        
        <h2>Target Personas</h2>
        """
        
        # Add personas
        personas = content_plan.get('personas', [])
        if personas:
            html += "<table>"
            html += "<tr><th>Persona</th><th>Description</th><th>Key Tasks</th><th>Benefits</th><th>Prerequisites</th></tr>"
            
            for persona in personas:
                html += f"""
                <tr>
                    <td>{persona.get('name', '')}</td>
                    <td>{persona.get('description', '')}</td>
                    <td>{self._format_list(persona.get('key_tasks', []))}</td>
                    <td>{self._format_list(persona.get('benefits', []))}</td>
                    <td>{self._format_list(persona.get('prerequisites', []))}</td>
                </tr>
                """
            
            html += "</table>"
        
        # Add key concepts
        html += "<h2>Key Concepts</h2>"
        concepts = content_plan.get('key_concepts', [])
        if concepts:
            html += "<table>"
            html += "<tr><th>Concept</th><th>Description</th></tr>"
            
            for concept in concepts:
                html += f"""
                <tr>
                    <td>{concept.get('name', '')}</td>
                    <td>{concept.get('description', '')}</td>
                </tr>
                """
            
            html += "</table>"
        
        # Add content structure as a spreadsheet
        html += "<h2>Content Structure</h2>"
        html += self._generate_content_structure_spreadsheet(content_plan.get('content_structure', []))
        
        # Add cross references
        html += "<h2>Cross References</h2>"
        cross_refs = content_plan.get('cross_references', [])
        if cross_refs:
            html += "<table>"
            html += "<tr><th>Service</th><th>Description</th><th>URL</th></tr>"
            
            for ref in cross_refs:
                html += f"""
                <tr>
                    <td>{ref.get('service', '')}</td>
                    <td>{ref.get('description', '')}</td>
                    <td><a href="{ref.get('url', '')}">{ref.get('url', '')}</a></td>
                </tr>
                """
            
            html += "</table>"
        
        # Add security and compliance
        html += "<h2>Security and Compliance</h2>"
        security = content_plan.get('security_compliance', {})
        html += f"""
        <h3>Security Considerations</h3>
        {self._format_list(security.get('security_considerations', []))}
        
        <h3>Compliance Requirements</h3>
        {self._format_list(security.get('compliance_requirements', []))}
        """
        
        # Add glossary
        html += "<h2>Glossary</h2>"
        glossary = content_plan.get('glossary', [])
        if glossary:
            html += "<table>"
            html += "<tr><th>Term</th><th>Definition</th></tr>"
            
            for term in glossary:
                html += f"""
                <tr>
                    <td>{term.get('term', '')}</td>
                    <td>{term.get('definition', '')}</td>
                </tr>
                """
            
            html += "</table>"
        
        # Add improvement suggestions
        html += "<h2>Improvement Suggestions</h2>"
        suggestions = content_plan.get('improvement_suggestions', [])
        if suggestions:
            html += "<table>"
            html += "<tr><th>Suggestion</th><th>Rationale</th></tr>"
            
            for suggestion in suggestions:
                html += f"""
                <tr>
                    <td>{suggestion.get('suggestion', '')}</td>
                    <td>{suggestion.get('rationale', '')}</td>
                </tr>
                """
            
            html += "</table>"
        
        return html
    
    def _generate_content_structure_spreadsheet(self, content_structure: List[Dict[str, Any]]) -> str:
        """Generate a spreadsheet for content structure.
        
        Args:
            content_structure: Content structure data
            
        Returns:
            HTML spreadsheet
        """
        # Create a spreadsheet for the main sections
        html = '<spreadsheet>'
        
        # Add header row
        html += '<row>'
        html += '<cell>Title</cell>'
        html += '<cell>Section ID</cell>'
        html += '<cell>Purpose</cell>'
        html += '<cell>Key Points</cell>'
        html += '<cell>Examples</cell>'
        html += '<cell>Visuals</cell>'
        html += '<cell>Has Subsections</cell>'
        html += '</row>'
        
        # Add data rows
        for section in content_structure:
            html += '<row>'
            html += f'<cell>{section.get("title", "")}</cell>'
            html += f'<cell>{section.get("section_id", "")}</cell>'
            html += f'<cell>{section.get("purpose", "")}</cell>'
            html += f'<cell>{self._format_list_plain(section.get("key_points", []))}</cell>'
            
            # Format examples
            examples = section.get("examples", [])
            examples_text = ""
            for example in examples:
                examples_text += f"{example.get('type', '')}: {example.get('description', '')}\n"
            html += f'<cell>{examples_text}</cell>'
            
            html += f'<cell>{self._format_list_plain(section.get("visuals", []))}</cell>'
            html += f'<cell>{"Yes" if section.get("subsections") else "No"}</cell>'
            html += '</row>'
            
            # Add subsections if any
            subsections = section.get("subsections", [])
            for subsection in subsections:
                html += '<row>'
                html += f'<cell>-- {subsection.get("title", "")}</cell>'
                html += f'<cell>{subsection.get("section_id", "")}</cell>'
                html += f'<cell>{subsection.get("purpose", "")}</cell>'
                html += f'<cell>{self._format_list_plain(subsection.get("key_points", []))}</cell>'
                html += '<cell></cell>'  # No examples for subsections in our model
                html += '<cell></cell>'  # No visuals for subsections in our model
                html += '<cell>No</cell>'
                html += '</row>'
        
        html += '</spreadsheet>'
        return html
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list as HTML.
        
        Args:
            items: List items
            
        Returns:
            HTML list
        """
        if not items:
            return ""
        
        html = "<ul>"
        for item in items:
            html += f"<li>{item}</li>"
        html += "</ul>"
        return html
    
    def _format_list_plain(self, items: List[str]) -> str:
        """Format a list as plain text.
        
        Args:
            items: List items
            
        Returns:
            Plain text list
        """
        if not items:
            return ""
        
        return "\n".join([f"- {item}" for item in items])