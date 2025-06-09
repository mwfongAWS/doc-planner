"""Command-line interface for AWS Documentation Tools."""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import click
from rich.console import Console
from rich.prompt import Prompt, Confirm

from doc_tools.config.settings import settings
from doc_tools.bedrock.client import BedrockClient
from doc_tools.bedrock.knowledge_base import KnowledgeBaseClient
from doc_tools.workflows.content_planning import ContentPlanningWorkflow
from doc_tools.workflows.document_generation import DocumentGenerationWorkflow
from doc_tools.utils.aws_auth import setup_aws_credentials, check_aws_credentials
from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()

@click.group()
def main():
    """AWS Documentation Tools - AI-assisted documentation for AWS technical writers."""
    pass

@main.command()
def setup():
    """Set up AWS Documentation Tools."""
    console.print("[bold]AWS Documentation Tools Setup[/bold]")
    console.print("This will guide you through setting up AWS Documentation Tools.\n")
    
    # Check if AWS CLI is installed
    try:
        import boto3
    except ImportError:
        console.print("[bold red]Error: boto3 is not installed.[/bold red]")
        console.print("Please install it with: pip install boto3")
        return
    
    # Set up AWS credentials
    console.print("[bold]Step 1: AWS Credentials[/bold]")
    
    # Check if credentials are already configured
    if settings.user.aws_profile and check_aws_credentials(settings.user.aws_profile):
        console.print(f"AWS credentials are already configured with profile: [green]{settings.user.aws_profile}[/green]")
        change_profile = Confirm.ask("Do you want to use a different profile?")
        if not change_profile:
            console.print("Keeping current profile configuration.")
        else:
            settings.user.aws_profile = None
    
    if not settings.user.aws_profile:
        result = setup_aws_credentials()
        
        if not result["success"]:
            console.print(f"[bold red]Error: {result['error']}[/bold red]")
            
            if "available_profiles" in result and result["available_profiles"]:
                console.print("\nAvailable profiles:")
                for profile in result["available_profiles"]:
                    console.print(f"- {profile}")
                
                profile_name = Prompt.ask("Enter profile name to use", default=result["available_profiles"][0])
                result = setup_aws_credentials(profile_name)
                
                if not result["success"]:
                    console.print(f"[bold red]Error: {result['error']}[/bold red]")
                    console.print("\nPlease run 'aws configure' to set up AWS credentials and try again.")
                    return
            else:
                console.print("\nPlease run 'aws configure' to set up AWS credentials and try again.")
                return
        
        settings.user.aws_profile = result["profile_name"]
        console.print(f"[green]AWS credentials configured with profile: {settings.user.aws_profile}[/green]")
    
    # Check Bedrock access
    console.print("\n[bold]Step 2: Checking Amazon Bedrock Access[/bold]")
    try:
        client = BedrockClient(profile_name=settings.user.aws_profile)
        models = client.list_foundation_models()
        console.print(f"[green]Successfully connected to Amazon Bedrock. Found {len(models)} available models.[/green]")
    except Exception as e:
        console.print(f"[bold red]Error connecting to Amazon Bedrock: {e}[/bold red]")
        console.print("Please make sure your AWS profile has access to Amazon Bedrock and try again.")
        return
    
    # Configure workspace
    console.print("\n[bold]Step 3: Configure Workspace[/bold]")
    if settings.user.workspace_path:
        console.print(f"Current workspace path: {settings.user.workspace_path}")
        change_workspace = Confirm.ask("Do you want to change the workspace path?")
        if not change_workspace:
            console.print("Keeping current workspace path.")
        else:
            settings.user.workspace_path = None
    
    if not settings.user.workspace_path:
        workspace_path = Prompt.ask("Enter workspace path", default=str(Path.cwd()))
        workspace_path = Path(workspace_path).expanduser().resolve()
        
        if not workspace_path.exists():
            create_workspace = Confirm.ask(f"Workspace path {workspace_path} does not exist. Create it?")
            if create_workspace:
                workspace_path.mkdir(parents=True, exist_ok=True)
            else:
                console.print("Please specify a valid workspace path.")
                return
        
        settings.user.workspace_path = workspace_path
        console.print(f"[green]Workspace path set to: {settings.user.workspace_path}[/green]")
    
    # Configure output format
    console.print("\n[bold]Step 4: Configure Default Output Format[/bold]")
    console.print(f"Current default output format: {settings.user.default_output_format}")
    change_format = Confirm.ask("Do you want to change the default output format?")
    if change_format:
        output_format = Prompt.ask(
            "Enter default output format",
            choices=["markdown", "zonbook"],
            default=settings.user.default_output_format
        )
        settings.user.default_output_format = output_format
        console.print(f"[green]Default output format set to: {settings.user.default_output_format}[/green]")
    
    # Save settings
    settings.save()
    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("You can now use AWS Documentation Tools.")

@main.command()
@click.argument("name")
@click.option("--description", "-d", help="Knowledge base description")
@click.option("--bucket", "-b", required=True, help="S3 bucket name")
@click.option("--prefix", "-p", default="knowledge-base/", help="S3 prefix")
def create_kb(name: str, description: Optional[str] = None, bucket: str = None, prefix: str = "knowledge-base/"):
    """Create a knowledge base."""
    if not settings.user.aws_profile:
        console.print("[bold red]AWS profile not configured. Run 'aws-doc-tools setup' first.[/bold red]")
        return
    
    description = description or f"Knowledge base for {name}"
    
    try:
        workflow = ContentPlanningWorkflow(profile_name=settings.user.aws_profile)
        kb_id = workflow.create_knowledge_base(
            name=name,
            description=description,
            s3_bucket_name=bucket,
            s3_prefix=prefix
        )
        
        console.print(f"[bold green]Knowledge base created successfully![/bold green]")
        console.print(f"Knowledge Base ID: {kb_id}")
        console.print(f"Name: {name}")
        console.print(f"Description: {description}")
        console.print(f"S3 Location: s3://{bucket}/{prefix}")
        
    except Exception as e:
        console.print(f"[bold red]Failed to create knowledge base: {e}[/bold red]")

@main.command()
@click.argument("kb_id")
@click.argument("files", nargs=-1, type=click.Path(exists=True))
def upload_resources(kb_id: str, files: List[str]):
    """Upload resources to a knowledge base."""
    if not settings.user.aws_profile:
        console.print("[bold red]AWS profile not configured. Run 'aws-doc-tools setup' first.[/bold red]")
        return
    
    if not files:
        console.print("[bold red]No files specified.[/bold red]")
        return
    
    try:
        workflow = ContentPlanningWorkflow(
            kb_id=kb_id,
            profile_name=settings.user.aws_profile
        )
        
        console.print(f"Uploading {len(files)} files to knowledge base {kb_id}...")
        
        for i, file_path in enumerate(files):
            console.print(f"Uploading [{i+1}/{len(files)}]: {file_path}")
            workflow.kb_client.upload_document(
                kb_id=kb_id,
                file_path=file_path
            )
        
        console.print(f"[bold green]Successfully uploaded {len(files)} files to knowledge base {kb_id}![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Failed to upload resources: {e}[/bold red]")

@main.command()
@click.argument("kb_id", required=False)
@click.argument("template_name")
@click.option("--output", "-o", help="Output file path")
@click.option("--model", "-m", help="Bedrock model ID")
@click.option("--context", "-c", help="Context variables in JSON format")
def generate_plan(kb_id: Optional[str], template_name: str, output: Optional[str] = None, 
                 model: Optional[str] = None, context: Optional[str] = None):
    """Generate a content plan."""
    if not settings.user.aws_profile:
        console.print("[bold red]AWS profile not configured. Run 'aws-doc-tools setup' first.[/bold red]")
        return
    
    try:
        workflow = ContentPlanningWorkflow(
            kb_id=kb_id,
            model_id=model,
            profile_name=settings.user.aws_profile
        )
        
        # Parse context
        context_vars = {}
        if context:
            try:
                context_vars = json.loads(context)
            except json.JSONDecodeError:
                console.print("[bold red]Invalid JSON context. Please provide valid JSON.[/bold red]")
                return
        
        # Set default context variables
        if "service_name" not in context_vars:
            context_vars["service_name"] = Prompt.ask("Enter service name")
        
        if "feature_name" not in context_vars:
            context_vars["feature_name"] = Prompt.ask("Enter feature name", default="")
        
        console.print(f"Generating content plan using template '{template_name}'...")
        plan = workflow.generate_content_plan(
            template_name=template_name,
            context=context_vars,
            output_path=output
        )
        
        console.print(f"[bold green]Content plan generated successfully![/bold green]")
        if output:
            console.print(f"Content plan saved to: {output}")
        else:
            console.print(f"Content plan saved to: {workflow.plan_path}")
        
    except Exception as e:
        console.print(f"[bold red]Failed to generate content plan: {e}[/bold red]")

@main.command()
@click.argument("plan_path", type=click.Path(exists=True))
@click.option("--format", "-f", default=None, type=click.Choice(["markdown", "zonbook"]), help="Output format")
@click.option("--output", "-o", help="Output file path")
@click.option("--model", "-m", help="Bedrock model ID")
def generate_document(plan_path: str, format: Optional[str] = None, output: Optional[str] = None, model: Optional[str] = None):
    """Generate a document from a content plan."""
    if not settings.user.aws_profile:
        console.print("[bold red]AWS profile not configured. Run 'aws-doc-tools setup' first.[/bold red]")
        return
    
    # Use default format if not specified
    format = format or settings.user.default_output_format
    
    try:
        from doc_tools.workflows.document_generation import DocumentGenerationWorkflow
        
        workflow = DocumentGenerationWorkflow(
            model_id=model,
            profile_name=settings.user.aws_profile
        )
        
        console.print(f"Generating {format} document from content plan...")
        document = workflow.generate_document(
            plan_path=plan_path,
            output_format=format,
            output_path=output
        )
        
        console.print(f"[bold green]Document generated successfully![/bold green]")
        if output:
            console.print(f"Document saved to: {output}")
        else:
            console.print(f"Document saved to: {workflow.document_path}")
        
    except Exception as e:
        console.print(f"[bold red]Failed to generate document: {e}[/bold red]")

@main.command()
@click.argument("content_path", type=click.Path(exists=True))
@click.argument("kb_id")
@click.option("--scope", "-s", default="full", type=click.Choice(["full", "section", "paragraph", "sentence"]), help="Validation scope")
@click.option("--output", "-o", help="Output file path")
@click.option("--report", "-r", help="Generate validation report")
@click.option("--report-format", "-f", default="markdown", type=click.Choice(["markdown", "html"]), help="Report format")
@click.option("--model", "-m", help="Bedrock model ID")
def validate_content(content_path: str, kb_id: str, scope: str = "full", output: Optional[str] = None, 
                    report: Optional[str] = None, report_format: str = "markdown", model: Optional[str] = None):
    """Validate content against a knowledge base."""
    if not settings.user.aws_profile:
        console.print("[bold red]AWS profile not configured. Run 'aws-doc-tools setup' first.[/bold red]")
        return
    
    from doc_tools.workflows.content_validation import ContentValidationWorkflow
    
    try:
        workflow = ContentValidationWorkflow(
            kb_id=kb_id,
            model_id=model,
            profile_name=settings.user.aws_profile
        )
        
        console.print(f"Validating content in {content_path} with scope '{scope}'...")
        results = workflow.validate_file(
            file_path=content_path,
            scope=scope,
            output_path=output
        )
        
        # Display summary
        console.print(f"\n[bold]Validation Results:[/bold]")
        console.print(f"Status: {results['overall_status']}")
        console.print(f"Chunks validated: {results['summary']['validated_chunks']}")
        console.print(f"Issues found: {results['summary']['issues_found']}")
        
        # Display issues if any
        if results['summary']['issues_found'] > 0:
            console.print("\n[bold yellow]Issues found:[/bold yellow]")
            for i, chunk in enumerate(results['chunks']):
                if chunk['status'] != 'valid':
                    console.print(f"\n[bold]Issue {i+1}:[/bold]")
                    console.print(f"Content: {chunk['content'][:100]}...")
                    console.print(f"Status: {chunk['status']}")
                    console.print(f"Message: {chunk['message']}")
                    
                    if chunk['suggestions']:
                        console.print("[bold]Suggestions:[/bold]")
                        for suggestion in chunk['suggestions']:
                            console.print(f"- {suggestion}")
        
        if output:
            console.print(f"\n[bold green]Detailed validation results saved to {output}[/bold green]")
        
        # Generate report if requested
        if report:
            console.print(f"\nGenerating {report_format} validation report...")
            workflow.generate_validation_report(
                output_format=report_format,
                output_path=report
            )
            console.print(f"[bold green]Validation report saved to {report}[/bold green]")
            
    except Exception as e:
        console.print(f"[bold red]Failed to validate content: {e}[/bold red]")

@main.command()
@click.argument("content_plan_path", type=click.Path(exists=True))
@click.option("--api-token", "-t", required=True, help="Quip API token")
@click.option("--folder-id", "-f", help="Quip folder ID to create document in")
@click.option("--title", help="Document title (defaults to content plan title)")
def export_to_quip(content_plan_path: str, api_token: str, folder_id: Optional[str] = None, title: Optional[str] = None):
    """Export a content plan to a Quip document."""
    from doc_tools.utils.quip_exporter import QuipExporter
    
    try:
        exporter = QuipExporter(api_token=api_token)
        
        console.print(f"Exporting content plan {content_plan_path} to Quip...")
        quip_url = exporter.export_content_plan(
            content_plan=content_plan_path,
            folder_id=folder_id,
            title=title
        )
        
        console.print(f"[bold green]Content plan exported to Quip successfully![/bold green]")
        console.print(f"Quip document URL: {quip_url}")
        
    except Exception as e:
        console.print(f"[bold red]Failed to export content plan to Quip: {e}[/bold red]")

if __name__ == "__main__":
    main()