"""Amazon Bedrock client for interacting with foundation models."""

import json
from typing import Dict, List, Optional, Any, Union

import boto3
from botocore.exceptions import ClientError

from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

class BedrockClient:
    """Client for interacting with Amazon Bedrock foundation models."""
    
    def __init__(self, profile_name: Optional[str] = None, region: Optional[str] = None):
        """Initialize the Bedrock client.
        
        Args:
            profile_name: AWS profile name to use
            region: AWS region to use
        """
        self.profile_name = profile_name or settings.user.aws_profile
        self.region = region or settings.bedrock.region
        self._client = None
        self._runtime_client = None
        
    @property
    def client(self):
        """Get the Bedrock client."""
        if self._client is None:
            session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
            self._client = session.client('bedrock')
        return self._client
    
    @property
    def runtime_client(self):
        """Get the Bedrock runtime client."""
        if self._runtime_client is None:
            session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
            self._runtime_client = session.client('bedrock-runtime')
        return self._runtime_client
    
    def list_foundation_models(self) -> List[Dict[str, Any]]:
        """List available foundation models.
        
        Returns:
            List of foundation models
        """
        try:
            response = self.client.list_foundation_models()
            return response.get('modelSummaries', [])
        except ClientError as e:
            logger.error(f"Failed to list foundation models: {e}")
            raise
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a foundation model.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model information
        """
        try:
            response = self.client.get_foundation_model(modelIdentifier=model_id)
            return response
        except ClientError as e:
            logger.error(f"Failed to get model info for {model_id}: {e}")
            raise
    
    def invoke_model(
        self, 
        model_id: str, 
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 4096,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """Invoke a foundation model.
        
        Args:
            model_id: Model ID
            prompt: Prompt text
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            max_tokens: Maximum number of tokens to generate
            stop_sequences: Sequences that stop generation
            
        Returns:
            Generated text
        """
        try:
            # Format request body based on model provider
            request_body = self._format_request_body(
                model_id=model_id,
                prompt=prompt,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences or []
            )
            
            # Invoke model
            response = self.runtime_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response based on model provider
            response_body = json.loads(response['body'].read())
            return self._parse_response(model_id, response_body)
            
        except ClientError as e:
            logger.error(f"Failed to invoke model {model_id}: {e}")
            raise
    
    def _format_request_body(
        self, 
        model_id: str, 
        prompt: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        stop_sequences: List[str]
    ) -> Dict[str, Any]:
        """Format request body based on model provider.
        
        Args:
            model_id: Model ID
            prompt: Prompt text
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            max_tokens: Maximum number of tokens to generate
            stop_sequences: Sequences that stop generation
            
        Returns:
            Formatted request body
        """
        if model_id.startswith('anthropic.claude'):
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stop_sequences": stop_sequences,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        elif model_id.startswith('amazon.titan'):
            return {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": temperature,
                    "topP": top_p,
                    "stopSequences": stop_sequences
                }
            }
        elif model_id.startswith('meta.llama'):
            return {
                "prompt": prompt,
                "max_gen_len": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            }
        else:
            raise ValueError(f"Unsupported model: {model_id}")
    
    def _parse_response(self, model_id: str, response_body: Dict[str, Any]) -> str:
        """Parse response based on model provider.
        
        Args:
            model_id: Model ID
            response_body: Response body
            
        Returns:
            Generated text
        """
        if model_id.startswith('anthropic.claude'):
            return response_body['content'][0]['text']
        elif model_id.startswith('amazon.titan'):
            return response_body['results'][0]['outputText']
        elif model_id.startswith('meta.llama'):
            return response_body['generation']
        else:
            raise ValueError(f"Unsupported model: {model_id}")
