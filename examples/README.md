# AWS Documentation Planner Examples

This directory contains examples and test scripts for the AWS Documentation Planner.

## Test Workflow Script

The `test_workflow.sh` script demonstrates a complete end-to-end workflow using AWS Documentation Planner. It:

1. Creates sample resource files (design document and API spec)
2. Sets up the AWS Documentation Planner
3. Creates a knowledge base
4. Uploads resources to the knowledge base
5. Generates a content plan
6. Exports the content plan to Quip (optional)
7. Generates documentation from the content plan
8. Validates the documentation against the knowledge base

### Prerequisites

Before running the script:

1. Install AWS Documentation Planner (`pip install -e .` from the project root)
2. Configure AWS credentials with access to Amazon Bedrock
3. Edit the script to set your S3 bucket name and Quip API token (optional)

### Usage

```bash
cd examples
./test_workflow.sh
```

## Sample Content Plan

The `sample_content_plan.json` file is a pre-created content plan that you can use to test specific features without going through the entire workflow. It's particularly useful for testing the Quip export functionality.

### Testing Quip Export with Sample Content Plan

```bash
# Replace YOUR_QUIP_API_TOKEN with your actual Quip API token
aws-doc-tools export-to-quip examples/sample_content_plan.json --api-token "YOUR_QUIP_API_TOKEN"
```

## Quick Test Commands

Here are some quick commands to test individual features:

### Generate Documentation from Sample Content Plan

```bash
aws-doc-tools generate-document examples/sample_content_plan.json --format markdown --output feature-x-docs.md
```

### Export Sample Content Plan to Quip

```bash
aws-doc-tools export-to-quip examples/sample_content_plan.json --api-token "YOUR_QUIP_API_TOKEN"
```

## Notes

- The test workflow script creates files in a subdirectory of your current directory (`aws-doc-planner-test`)
- You'll need to have appropriate permissions for the S3 bucket you specify
- The Quip API token is optional, but required if you want to test the Quip export functionality