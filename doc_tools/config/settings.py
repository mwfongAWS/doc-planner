"""Settings configuration for AWS Documentation Tools."""

import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class BedrockSettings(BaseModel):
    """Settings for Amazon Bedrock."""
    
    default_model_id: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        description="Default Bedrock model ID to use"
    )
    available_models: List[str] = Field(
        default=[
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "amazon.titan-text-express-v1",
            "amazon.titan-text-premier-v1:0",
            "meta.llama3-70b-instruct-v1:0",
            "meta.llama3-8b-instruct-v1:0"
        ],
        description="Available Bedrock models"
    )
    region: str = Field(
        default="us-west-2",
        description="AWS region for Bedrock"
    )

class KnowledgeBaseSettings(BaseModel):
    """Settings for Amazon Bedrock Knowledge Bases."""
    
    region: str = Field(
        default="us-west-2",
        description="AWS region for Knowledge Bases"
    )
    embedding_model_id: str = Field(
        default="amazon.titan-embed-text-v1",
        description="Embedding model ID for Knowledge Bases"
    )

class UserSettings(BaseModel):
    """User-specific settings."""
    
    aws_profile: Optional[str] = Field(
        default=None,
        description="AWS profile to use"
    )
    default_output_format: str = Field(
        default="markdown",
        description="Default output format (markdown or zonbook)"
    )
    workspace_path: Optional[Path] = Field(
        default=None,
        description="Path to user's workspace"
    )

class Settings(BaseModel):
    """Global settings for AWS Documentation Tools."""
    
    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    user: UserSettings = Field(default_factory=UserSettings)
    
    # Paths
    config_dir: Path = Field(
        default=Path.home() / ".aws-doc-tools",
        description="Configuration directory"
    )
    templates_dir: Path = Field(
        default=Path(__file__).parent.parent / "templates",
        description="Templates directory"
    )
    
    def save(self) -> None:
        """Save settings to disk."""
        import json
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Save settings to file
        with open(self.config_dir / "settings.json", "w") as f:
            # Convert to dict and handle Path objects
            settings_dict = self.model_dump()
            settings_dict["config_dir"] = str(settings_dict["config_dir"])
            settings_dict["templates_dir"] = str(settings_dict["templates_dir"])
            if settings_dict["user"]["workspace_path"]:
                settings_dict["user"]["workspace_path"] = str(settings_dict["user"]["workspace_path"])
            
            json.dump(settings_dict, f, indent=2)
    
    @classmethod
    def load(cls) -> "Settings":
        """Load settings from disk."""
        import json
        
        config_path = Path.home() / ".aws-doc-tools" / "settings.json"
        if not config_path.exists():
            return cls()
        
        with open(config_path, "r") as f:
            settings_dict = json.load(f)
            
        # Convert string paths back to Path objects
        settings_dict["config_dir"] = Path(settings_dict["config_dir"])
        settings_dict["templates_dir"] = Path(settings_dict["templates_dir"])
        if settings_dict["user"]["workspace_path"]:
            settings_dict["user"]["workspace_path"] = Path(settings_dict["user"]["workspace_path"])
            
        return cls(**settings_dict)

# Global settings instance
settings = Settings.load()
