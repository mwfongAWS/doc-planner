# AWS Documentation Planner

An end-to-end interactive and iterative writer + AI experience tool for technical writers working at AWS.

## Overview

AWS Documentation Planner provides a comprehensive solution for technical writers at AWS to create high-quality documentation with AI assistance. The tool integrates with Amazon Bedrock foundation models and Knowledge Bases to provide context-aware content generation.

## Features

- **Content Planning**: Generate structured content plans based on provided resources
- **Document Generation**: Convert content plans into well-formatted documentation
- **Knowledge Base Integration**: Use Amazon Bedrock Knowledge Bases for context-aware generation
- **Content Validation**: Cross-check content against knowledge base for accuracy
- **VSCode Integration**: Seamless integration with VSCode and Amazon Q extension
- **Iterative Refinement**: Collaborate with AI to refine content plans and documentation
- **Multiple Output Formats**: Support for Markdown and zonbook (XML) formats
- **Quip Integration**: Export content plans to Quip documents with proper visualization

## Quick Start

For a complete step-by-step guide to get started, see [GETTING_STARTED.md](GETTING_STARTED.md).

### Installation

```bash
# Clone the repository
git clone https://github.com/aws/doc-planner.git
cd doc-planner

# Install the package
pip install -e .
```

### Setup

Before using the tool, you need to set up your AWS credentials and configure the tool:

```bash
aws-doc-tools setup
```

This will guide you through:
1. Setting up AWS credentials
2. Checking access to Amazon Bedrock services
3. Configuring your workspace
4. Setting default output format

## Testing the Tool

We provide a complete test workflow script to help you try out all features:

```bash
# Make the script executable if needed
chmod +x examples/test_workflow.sh

# Edit the script to set your S3 bucket name
nano examples/test_workflow.sh

# Run the test workflow
./examples/test_workflow.sh
```

For quick testing of the Quip export feature without going through the entire workflow:

```bash
aws-doc-tools export-to-quip examples/sample_content_plan.json --api-token "YOUR_QUIP_API_TOKEN"
```

See the [examples README](examples/README.md) for more testing options.

## Usage

### Creating a Knowledge Base

```bash
aws-doc-tools create-kb "MyProject" --description "Documentation for MyProject" --bucket "my-kb-bucket"
```

### Uploading Resources

```bash
aws-doc-tools upload-resources kb-12345 /path/to/design-doc.md /path/to/api-spec.yaml
```

### Generating a Content Plan

```bash
aws-doc-tools generate-plan kb-12345 content_plan --output content-plan.json
```

### Generating Documentation

```bash
aws-doc-tools generate-document content-plan.json --format markdown --output documentation.md
```

### Validating Content

```bash
aws-doc-tools validate-content documentation.md kb-12345 --scope paragraph --report validation-report.md
```

### Exporting Content Plan to Quip

```bash
aws-doc-tools export-to-quip content-plan.json --api-token "YOUR_QUIP_API_TOKEN" --folder-id "QUIP_FOLDER_ID"
```

## Complete Workflow

A typical workflow using AWS Documentation Planner:

1. Set up the tool and AWS credentials
2. Create a knowledge base for your project
3. Upload relevant resources (design docs, PRFAQs, code examples)
4. Generate a content plan based on these resources
5. Export the content plan to Quip for collaborative review
6. Review and refine the content plan
7. Generate documentation from the content plan
8. Iteratively refine the documentation with AI assistance

## Development

### Package Structure

```
doc_tools/
├── __init__.py
├── bedrock/          # Amazon Bedrock integration
├── config/           # Configuration management
├── core/             # Core functionality
├── utils/            # Utility functions
├── vscode/           # VSCode integration
├── workflows/        # Workflow modules
└── templates/        # Document templates
```

### Adding Templates

You can add custom templates for content plans or document generation:

```bash
aws-doc-tools add-template my_template /path/to/template.txt
```

## Troubleshooting

If you encounter issues:

1. **AWS Credentials**: Ensure your AWS credentials are properly configured with access to Amazon Bedrock
2. **S3 Bucket Access**: Verify you have permissions to the S3 bucket used for the knowledge base
3. **Bedrock Models**: Check that you have access to the required Bedrock foundation models
4. **Quip API Token**: Ensure your Quip API token is valid and has appropriate permissions

For more detailed troubleshooting, check the logs in `~/.aws-doc-tools/logs/aws-doc-tools.log`

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.