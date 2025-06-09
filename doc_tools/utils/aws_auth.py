"""AWS authentication utilities."""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any

import boto3
from botocore.exceptions import ClientError, ProfileNotFound

from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

def check_aws_credentials(profile_name: Optional[str] = None) -> bool:
    """Check if AWS credentials are configured.
    
    Args:
        profile_name: AWS profile name to check
        
    Returns:
        True if credentials are configured, False otherwise
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        sts = session.client('sts')
        sts.get_caller_identity()
        return True
    except (ClientError, ProfileNotFound):
        return False

def setup_aws_credentials(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """Set up AWS credentials interactively.
    
    Args:
        profile_name: AWS profile name to use
        
    Returns:
        Setup status
    """
    # Check if credentials already exist
    if profile_name and check_aws_credentials(profile_name):
        return {
            "success": True,
            "profile_name": profile_name,
            "message": f"AWS credentials for profile '{profile_name}' are already configured."
        }
    
    # Check if AWS CLI is installed
    try:
        subprocess.run(["aws", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        return {
            "success": False,
            "error": "AWS CLI is not installed. Please install it first: https://aws.amazon.com/cli/"
        }
    
    # Get available profiles
    aws_config_path = Path.home() / ".aws" / "config"
    aws_credentials_path = Path.home() / ".aws" / "credentials"
    
    available_profiles = []
    
    if aws_config_path.exists():
        with open(aws_config_path, 'r') as f:
            for line in f:
                if line.strip().startswith('[profile '):
                    profile = line.strip()[9:-1]
                    available_profiles.append(profile)
    
    if aws_credentials_path.exists():
        with open(aws_credentials_path, 'r') as f:
            for line in f:
                if line.strip().startswith('[') and line.strip().endswith(']'):
                    profile = line.strip()[1:-1]
                    if profile != 'default' and profile not in available_profiles:
                        available_profiles.append(profile)
    
    # Add default profile if it exists
    if check_aws_credentials('default'):
        if 'default' not in available_profiles:
            available_profiles.append('default')
    
    # Return available profiles if no profile is specified
    if not profile_name:
        if available_profiles:
            # Try each profile to see if it has Bedrock permissions
            valid_profiles = []
            for profile in available_profiles:
                if check_bedrock_access(profile):
                    valid_profiles.append(profile)
            
            if valid_profiles:
                # Use the first valid profile
                profile_name = valid_profiles[0]
                return {
                    "success": True,
                    "profile_name": profile_name,
                    "available_profiles": available_profiles,
                    "valid_profiles": valid_profiles,
                    "message": f"Using existing profile '{profile_name}' with Bedrock access."
                }
            else:
                return {
                    "success": False,
                    "available_profiles": available_profiles,
                    "error": "No profiles with Bedrock access found. Please configure a profile with Bedrock permissions."
                }
        else:
            return {
                "success": False,
                "error": "No AWS profiles found. Please run 'aws configure' to set up credentials."
            }
    
    # Check if the specified profile exists
    if profile_name not in available_profiles:
        return {
            "success": False,
            "available_profiles": available_profiles,
            "error": f"Profile '{profile_name}' not found. Available profiles: {', '.join(available_profiles)}"
        }
    
    # Check if the profile has Bedrock access
    if not check_bedrock_access(profile_name):
        return {
            "success": False,
            "profile_name": profile_name,
            "error": f"Profile '{profile_name}' does not have access to Amazon Bedrock. Please check permissions."
        }
    
    return {
        "success": True,
        "profile_name": profile_name,
        "message": f"AWS credentials for profile '{profile_name}' are configured and have Bedrock access."
    }

def check_bedrock_access(profile_name: Optional[str] = None) -> bool:
    """Check if the profile has access to Amazon Bedrock.
    
    Args:
        profile_name: AWS profile name to check
        
    Returns:
        True if the profile has Bedrock access, False otherwise
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        bedrock = session.client('bedrock')
        bedrock.list_foundation_models()
        return True
    except ClientError as e:
        logger.error(f"Bedrock access check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking Bedrock access: {e}")
        return False

def get_aws_account_id(profile_name: Optional[str] = None) -> Optional[str]:
    """Get AWS account ID.
    
    Args:
        profile_name: AWS profile name to use
        
    Returns:
        AWS account ID or None if not available
    """
    try:
        session = boto3.Session(profile_name=profile_name)
        sts = session.client('sts')
        return sts.get_caller_identity()["Account"]
    except Exception as e:
        logger.error(f"Failed to get AWS account ID: {e}")
        return None