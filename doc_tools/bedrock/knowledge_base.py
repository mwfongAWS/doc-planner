"""Amazon Bedrock Knowledge Base integration."""

import json
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import uuid

import boto3
from botocore.exceptions import ClientError

from doc_tools.config.settings import settings
from doc_tools.utils.logger import get_logger

logger = get_logger(__name__)

class KnowledgeBaseClient:
    """Client for interacting with Amazon Bedrock Knowledge Bases."""
    
    def __init__(self, profile_name: Optional[str] = None, region: Optional[str] = None):
        """Initialize the Knowledge Base client.
        
        Args:
            profile_name: AWS profile name to use
            region: AWS region to use
        """
        self.profile_name = profile_name or settings.user.aws_profile
        self.region = region or settings.knowledge_base.region
        self._client = None
        self._s3_client = None
        self._bedrock_client = None
        
    @property
    def client(self):
        """Get the Bedrock Knowledge Base client."""
        if self._client is None:
            session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
            self._client = session.client('bedrock-agent-runtime')
        return self._client
    
    @property
    def s3_client(self):
        """Get the S3 client."""
        if self._s3_client is None:
            session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
            self._s3_client = session.client('s3')
        return self._s3_client
    
    @property
    def bedrock_client(self):
        """Get the Bedrock client."""
        if self._bedrock_client is None:
            session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
            self._bedrock_client = session.client('bedrock')
        return self._bedrock_client
    
    def create_knowledge_base(
        self, 
        name: str, 
        description: str,
        s3_bucket_name: str,
        s3_prefix: str = "knowledge-base/",
        embedding_model_id: Optional[str] = None,
        data_source_type: str = "CUSTOM",
    ) -> Dict[str, Any]:
        """Create a new knowledge base.
        
        Args:
            name: Knowledge base name
            description: Knowledge base description
            s3_bucket_name: S3 bucket name for storage
            s3_prefix: S3 prefix for storage
            embedding_model_id: Embedding model ID
            data_source_type: Data source type (CUSTOM or NATIVE)
            
        Returns:
            Knowledge base information
        """
        try:
            # Create knowledge base configuration
            kb_config = {
                "name": name,
                "description": description,
                "roleArn": f"arn:aws:iam::{self._get_account_id()}:role/BedrockKnowledgeBaseRole",
                "storageConfiguration": {
                    "type": "S3",
                    "s3Configuration": {
                        "bucketName": s3_bucket_name,
                        "bucketOwner": self._get_account_id(),
                        "prefix": s3_prefix
                    }
                },
                "vectorIngestionConfiguration": {
                    "embeddingModelArn": embedding_model_id or settings.knowledge_base.embedding_model_id,
                    "chunkingConfiguration": {
                        "chunkingStrategy": "FIXED_SIZE",
                        "fixedSizeChunkingConfiguration": {
                            "maxTokens": 300,
                            "overlapPercentage": 20
                        }
                    }
                },
                "dataSourceConfiguration": {
                    "type": data_source_type
                }
            }
            
            # Create knowledge base
            response = self.client.create_knowledge_base(**kb_config)
            
            # Wait for knowledge base to be created
            kb_id = response['knowledgeBaseId']
            self._wait_for_knowledge_base(kb_id)
            
            return response
            
        except ClientError as e:
            logger.error(f"Failed to create knowledge base: {e}")
            raise
    
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """List available knowledge bases.
        
        Returns:
            List of knowledge bases
        """
        try:
            response = self.client.list_knowledge_bases()
            return response.get('knowledgeBaseSummaries', [])
        except ClientError as e:
            logger.error(f"Failed to list knowledge bases: {e}")
            raise
    
    def get_knowledge_base(self, kb_id: str) -> Dict[str, Any]:
        """Get information about a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            Knowledge base information
        """
        try:
            response = self.client.get_knowledge_base(knowledgeBaseId=kb_id)
            return response
        except ClientError as e:
            logger.error(f"Failed to get knowledge base {kb_id}: {e}")
            raise
    
    def upload_document(
        self, 
        kb_id: str, 
        file_path: Union[str, Path],
        data_source_id: Optional[str] = None,
        custom_metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a document to a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            file_path: Path to file
            data_source_id: Data source ID (optional)
            custom_metadata: Custom metadata for the document
            
        Returns:
            Upload information
        """
        try:
            file_path = Path(file_path)
            
            # Create data source if not provided
            if not data_source_id:
                data_source_id = str(uuid.uuid4())
                self.client.create_data_source(
                    knowledgeBaseId=kb_id,
                    dataSourceId=data_source_id,
                    name=file_path.name,
                    description=f"Data source for {file_path.name}"
                )
            
            # Get knowledge base info to get S3 location
            kb_info = self.get_knowledge_base(kb_id)
            bucket_name = kb_info['storageConfiguration']['s3Configuration']['bucketName']
            prefix = kb_info['storageConfiguration']['s3Configuration']['prefix']
            
            # Upload file to S3
            s3_key = f"{prefix}{data_source_id}/{file_path.name}"
            
            # Add metadata if provided
            extra_args = {}
            if custom_metadata:
                extra_args['Metadata'] = custom_metadata
            
            with open(file_path, 'rb') as f:
                self.s3_client.upload_fileobj(f, bucket_name, s3_key, ExtraArgs=extra_args)
            
            # Ingest document
            response = self.client.ingest_data(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id
            )
            
            # Wait for ingestion to complete
            self._wait_for_ingestion(kb_id, data_source_id, response['ingestionJobId'])
            
            return response
            
        except ClientError as e:
            logger.error(f"Failed to upload document {file_path}: {e}")
            raise
    
    def query_knowledge_base(
        self, 
        kb_id: str, 
        query: str,
        model_id: Optional[str] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """Query a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            query: Query text
            model_id: Model ID to use for retrieval
            max_results: Maximum number of results
            
        Returns:
            Query results
        """
        try:
            response = self.client.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to query knowledge base {kb_id}: {e}")
            raise
    
    def _get_account_id(self) -> str:
        """Get AWS account ID.
        
        Returns:
            AWS account ID
        """
        session = boto3.Session(profile_name=self.profile_name, region_name=self.region)
        sts_client = session.client('sts')
        return sts_client.get_caller_identity()['Account']
    
    def _wait_for_knowledge_base(self, kb_id: str, max_attempts: int = 30) -> None:
        """Wait for knowledge base to be available.
        
        Args:
            kb_id: Knowledge base ID
            max_attempts: Maximum number of attempts
        """
        for i in range(max_attempts):
            try:
                response = self.client.get_knowledge_base(knowledgeBaseId=kb_id)
                status = response['status']
                
                if status == 'AVAILABLE':
                    logger.info(f"Knowledge base {kb_id} is available")
                    return
                elif status in ['CREATING', 'UPDATING']:
                    logger.info(f"Knowledge base {kb_id} is {status.lower()}... ({i+1}/{max_attempts})")
                    time.sleep(10)
                else:
                    logger.error(f"Knowledge base {kb_id} is in unexpected state: {status}")
                    raise ValueError(f"Knowledge base {kb_id} is in unexpected state: {status}")
            except ClientError as e:
                logger.error(f"Error checking knowledge base status: {e}")
                time.sleep(10)
        
        raise TimeoutError(f"Timed out waiting for knowledge base {kb_id}")
    
    def _wait_for_ingestion(self, kb_id: str, data_source_id: str, job_id: str, max_attempts: int = 30) -> None:
        """Wait for ingestion job to complete.
        
        Args:
            kb_id: Knowledge base ID
            data_source_id: Data source ID
            job_id: Ingestion job ID
            max_attempts: Maximum number of attempts
        """
        for i in range(max_attempts):
            try:
                response = self.client.get_ingestion_job(
                    knowledgeBaseId=kb_id,
                    dataSourceId=data_source_id,
                    ingestionJobId=job_id
                )
                status = response['status']
                
                if status == 'COMPLETE':
                    logger.info(f"Ingestion job {job_id} is complete")
                    return
                elif status in ['IN_PROGRESS', 'STARTING']:
                    logger.info(f"Ingestion job {job_id} is {status.lower()}... ({i+1}/{max_attempts})")
                    time.sleep(10)
                else:
                    logger.error(f"Ingestion job {job_id} is in unexpected state: {status}")
                    raise ValueError(f"Ingestion job {job_id} is in unexpected state: {status}")
            except ClientError as e:
                logger.error(f"Error checking ingestion job status: {e}")
                time.sleep(10)
        
        raise TimeoutError(f"Timed out waiting for ingestion job {job_id}")
