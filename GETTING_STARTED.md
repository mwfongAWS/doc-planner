# Getting Started with AWS Documentation Planner

This guide will walk you through setting up and testing the AWS Documentation Planner for technical writers. Follow these steps to create your first AI-assisted documentation project.

## Prerequisites

Before you begin, make sure you have:

1. Python 3.9 or higher installed
2. AWS account with access to Amazon Bedrock
3. AWS CLI configured with appropriate credentials
4. A Quip account and API token (for Quip integration)

## Step 1: Installation

First, install the AWS Documentation Planner package:

```bash
# Clone the repository
git clone https://github.com/aws/doc-planner.git
cd doc-planner

# Install the package in development mode
pip install -e .
```

## Step 2: Initial Setup

Run the setup command to configure your environment:

```bash
aws-doc-tools setup
```

This interactive setup will:
- Verify your AWS credentials
- Check access to Amazon Bedrock
- Configure your workspace
- Set default output format preferences

## Step 3: Create a Knowledge Base

Create a knowledge base to store your documentation resources:

```bash
# Replace "my-bucket" with an S3 bucket you have access to
aws-doc-tools create-kb "MyFirstProject" --description "Documentation for my first project" --bucket "my-bucket"
```

The command will output a knowledge base ID (e.g., `kb-12345`). Save this ID for future steps.

## Step 4: Upload Resources

Upload relevant resources to your knowledge base. These can be design documents, PRFAQs, API specifications, or any other reference materials:

```bash
# Replace kb-12345 with your knowledge base ID
aws-doc-tools upload-resources kb-12345 /path/to/design-doc.md /path/to/api-spec.yaml
```

## Step 5: Generate a Content Plan

Generate an AI-assisted content plan based on your uploaded resources:

```bash
# Replace kb-12345 with your knowledge base ID
aws-doc-tools generate-plan kb-12345 content_plan --output my-content-plan.json
```

This will create a structured content plan in JSON format. The tool will prompt you for any additional information needed.

## Step 6: Export to Quip for Review (Optional)

Export your content plan to Quip for collaborative review:

```bash
# Replace with your Quip API token
aws-doc-tools export-to-quip my-content-plan.json --api-token "YOUR_QUIP_API_TOKEN"
```

To get a Quip API token:
1. Log in to Quip
2. Go to your account settings
3. Navigate to "Personal Access Tokens"
4. Create a new token

## Step 7: Refine the Content Plan

After reviewing the content plan, you can refine it by editing the JSON file directly or by using the tool to generate a new version based on feedback.

## Step 8: Generate Documentation

Generate documentation from your content plan:

```bash
# Generate markdown documentation
aws-doc-tools generate-document my-content-plan.json --format markdown --output my-documentation.md

# Or generate zonbook (XML) documentation
aws-doc-tools generate-document my-content-plan.json --format zonbook --output my-documentation.xml
```

## Step 9: Validate Content

Validate your documentation against the knowledge base to ensure accuracy:

```bash
aws-doc-tools validate-content my-documentation.md kb-12345 --scope paragraph --report validation-report.md
```

## Complete End-to-End Test Workflow

Here's a complete workflow to test all features:

```bash
# 1. Set up the tool
aws-doc-tools setup

# 2. Create a knowledge base
aws-doc-tools create-kb "TestProject" --description "Test documentation project" --bucket "my-test-bucket"
# Note the knowledge base ID (e.g., kb-12345)

# 3. Create a sample resource file
echo "# Test Design Document
This is a test design document for AWS Feature X.

## Overview
Feature X allows users to automatically process data using AI.

## Use Cases
- Data processing
- Automated analysis
- Report generation

## Architecture
The feature uses serverless components for scalability.
" > test-design-doc.md

# 4. Upload the resource
aws-doc-tools upload-resources kb-12345 test-design-doc.md

# 5. Generate a content plan
aws-doc-tools generate-plan kb-12345 content_plan --output test-content-plan.json

# 6. Export to Quip (optional)
aws-doc-tools export-to-quip test-content-plan.json --api-token "YOUR_QUIP_API_TOKEN"

# 7. Generate documentation
aws-doc-tools generate-document test-content-plan.json --format markdown --output test-documentation.md

# 8. Validate the documentation
aws-doc-tools validate-content test-documentation.md kb-12345 --scope paragraph --report test-validation-report.md
```

## Using with VSCode

If you're using VSCode:

1. Install the Amazon Q extension
2. Open your workspace folder
3. The AWS Documentation Planner will integrate with VSCode, allowing you to:
   - Generate content plans
   - Edit and refine documentation
   - Access AI assistance directly in your editor

## Troubleshooting

If you encounter issues:

1. **AWS Credentials**: Ensure your AWS credentials are properly configured with access to Amazon Bedrock
2. **S3 Bucket Access**: Verify you have permissions to the S3 bucket used for the knowledge base
3. **Bedrock Models**: Check that you have access to the required Bedrock foundation models
4. **Quip API Token**: Ensure your Quip API token is valid and has appropriate permissions

For more detailed troubleshooting, check the logs in `~/.aws-doc-tools/logs/aws-doc-tools.log`

## Next Steps

After completing this getting started guide, you can:

1. Create custom templates for your specific documentation needs
2. Integrate the tool into your existing documentation workflow
3. Explore advanced features like content validation and iterative refinement
4. Provide feedback to improve the tool