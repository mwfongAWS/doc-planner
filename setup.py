from setuptools import setup, find_packages

setup(
    name="aws-doc-planner",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.28.0",
        "click>=8.0.0",
        "rich>=10.0.0",
        "pydantic>=2.0.0",
        "langchain>=0.0.267",
        "python-dotenv>=1.0.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "aws-doc-tools=doc_tools.cli:main",
        ],
    },
    author="AWS Documentation Team",
    author_email="aws-doc-planner@amazon.com",
    description="Interactive AI-assisted documentation planning tool for AWS technical writers",
    keywords="documentation, aws, ai, technical writing, planning",
    python_requires=">=3.9",
)