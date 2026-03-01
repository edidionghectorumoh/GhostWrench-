"""
Configuration file for Autonomous Field Engineer system.
Initializes AWS Bedrock Runtime client and defines model constants.
"""

import boto3

# AWS Configuration
AWS_REGION = "us-east-1"

# Initialize Bedrock Runtime client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION
)

# Model IDs for Amazon Bedrock
NOVA_PRO_MODEL_ID = "us.amazon.nova-pro-v1:0"
CLAUDE_SONNET_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# Model configuration constants
MODEL_CONFIG = {
    "nova_pro": {
        "model_id": NOVA_PRO_MODEL_ID,
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    "claude_sonnet": {
        "model_id": CLAUDE_SONNET_MODEL_ID,
        "max_tokens": 8192,
        "temperature": 0.7,
    }
}
