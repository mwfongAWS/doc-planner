#!/bin/bash
# Test workflow script for AWS Documentation Tools
# This script demonstrates a complete end-to-end workflow

# Exit on error
set -e

# Configuration - MODIFY THESE VALUES
S3_BUCKET="my-test-bucket"  # Replace with your S3 bucket name
QUIP_API_TOKEN=""           # Replace with your Quip API token (optional)

# Create a test directory
TEST_DIR="$(pwd)/aws-doc-tools-test"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "=== AWS Documentation Tools Test Workflow ==="
echo "Working directory: $TEST_DIR"

# Step 1: Create a sample resource file
echo "Creating sample resource files..."
cat > test-design-doc.md << 'EOL'
# AWS Feature X Design Document

## Overview
Feature X is a new AWS service that allows customers to automatically process and analyze data using AI capabilities.

## Problem Statement
Customers need to process large volumes of data efficiently without managing infrastructure.

## Use Cases
- Real-time data processing
- Automated analysis of structured and unstructured data
- Report generation and insights extraction

## Architecture
The feature uses serverless components for scalability and integrates with:
- Amazon S3 for storage
- AWS Lambda for processing
- Amazon Bedrock for AI capabilities

## Security Considerations
- Data encryption at rest and in transit
- IAM-based access control
- VPC integration for network isolation

## Compliance
- GDPR compliant
- HIPAA eligible
- SOC 2 compliant
EOL

cat > test-api-spec.yaml << 'EOL'
openapi: 3.0.0
info:
  title: AWS Feature X API
  description: API for AWS Feature X
  version: 1.0.0
paths:
  /jobs:
    post:
      summary: Create a new processing job
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                dataSource:
                  type: string
                  description: S3 URI of the data source
                outputLocation:
                  type: string
                  description: S3 URI for output
                processingOptions:
                  type: object
                  description: Processing options
      responses:
        '200':
          description: Job created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  jobId:
                    type: string
  /jobs/{jobId}:
    get:
      summary: Get job status
      parameters:
        - name: jobId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Job details
EOL

echo "Sample files created."

# Step 2: Set up the tool
echo -e "\n=== Setting up AWS Documentation Tools ==="
echo "Note: This step will be interactive. Please follow the prompts."
aws-doc-tools setup

# Step 3: Create a knowledge base
echo -e "\n=== Creating Knowledge Base ==="
KB_RESPONSE=$(aws-doc-tools create-kb "TestProject" --description "Test documentation project" --bucket "$S3_BUCKET")
KB_ID=$(echo "$KB_RESPONSE" | grep "Knowledge Base ID:" | awk '{print $4}')

if [ -z "$KB_ID" ]; then
    echo "Failed to extract knowledge base ID. Please check the output above."
    exit 1
fi

echo "Created knowledge base with ID: $KB_ID"

# Step 4: Upload resources
echo -e "\n=== Uploading Resources ==="
aws-doc-tools upload-resources "$KB_ID" test-design-doc.md test-api-spec.yaml

# Step 5: Generate a content plan
echo -e "\n=== Generating Content Plan ==="
aws-doc-tools generate-plan "$KB_ID" content_plan --output test-content-plan.json

# Step 6: Export to Quip (if token provided)
if [ ! -z "$QUIP_API_TOKEN" ]; then
    echo -e "\n=== Exporting to Quip ==="
    aws-doc-tools export-to-quip test-content-plan.json --api-token "$QUIP_API_TOKEN"
else
    echo -e "\n=== Skipping Quip Export (no API token provided) ==="
fi

# Step 7: Generate documentation
echo -e "\n=== Generating Documentation ==="
aws-doc-tools generate-document test-content-plan.json --format markdown --output test-documentation.md

# Step 8: Validate the documentation
echo -e "\n=== Validating Documentation ==="
aws-doc-tools validate-content test-documentation.md "$KB_ID" --scope paragraph --report test-validation-report.md

echo -e "\n=== Test Workflow Complete ==="
echo "Test files are located in: $TEST_DIR"
echo "Content plan: $TEST_DIR/test-content-plan.json"
echo "Documentation: $TEST_DIR/test-documentation.md"
echo "Validation report: $TEST_DIR/test-validation-report.md"