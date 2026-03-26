"""
Configuration file for Autonomous Field Engineer system.
Loads AWS credentials from .env, initializes Bedrock Runtime client,
and defines model constants for the Amazon Nova 2 model family.
"""

import os
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS Configuration (reads from .env or environment)
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Initialize Bedrock Runtime client
# This client is used for both invoke_model (embeddings) and converse (Nova 2 Lite, Sonic)
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION
)

# ── Amazon Nova 2 Model IDs ──────────────────────────────────────────────────

# Reasoning & Multimodal Diagnosis (replaces Nova Pro)
NOVA_2_LITE_MODEL_ID = "us.amazon.nova-2-lite-v1:0"

# Agentic Tool-Calling & UI Automation
NOVA_ACT_MODEL_ID = "us.amazon.nova-act-v1:0"

# Speech-to-Speech Voice AI (us. prefix for cross-region inference)
NOVA_2_SONIC_MODEL_ID = "us.amazon.nova-2-sonic-v1:0"

# Unified Multimodal Embeddings (replaces Titan Embeddings + CLIP)
NOVA_MULTIMODAL_EMBEDDINGS_MODEL_ID = "amazon.nova-2-multimodal-embeddings-v1:0"

# Validation Judge
CLAUDE_SONNET_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# Embedding dimension for Nova Multimodal Embeddings (text + image unified space)
EMBEDDING_DIMENSION = 1024

# ── Legacy Model IDs (kept for backward compatibility) ────────────────────────
NOVA_PRO_MODEL_ID = "us.amazon.nova-pro-v1:0"

# ── Model Configuration ──────────────────────────────────────────────────────

MODEL_CONFIG = {
    "nova_2_lite": {
        "model_id": NOVA_2_LITE_MODEL_ID,
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    "nova_act": {
        "model_id": NOVA_ACT_MODEL_ID,
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    "nova_2_sonic": {
        "model_id": NOVA_2_SONIC_MODEL_ID,
        "max_tokens": 4096,
        "temperature": 0.3,
    },
    "nova_multimodal_embeddings": {
        "model_id": NOVA_MULTIMODAL_EMBEDDINGS_MODEL_ID,
        "embedding_dimension": EMBEDDING_DIMENSION,
    },
    "claude_sonnet": {
        "model_id": CLAUDE_SONNET_MODEL_ID,
        "max_tokens": 8192,
        "temperature": 0.7,
    },
    # Legacy — kept for backward compatibility
    "nova_pro": {
        "model_id": NOVA_PRO_MODEL_ID,
        "max_tokens": 4096,
        "temperature": 0.7,
    },
}

# ── Application Configuration ─────────────────────────────────────────────────

ENABLE_VALIDATION = os.getenv("ENABLE_VALIDATION", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "./audit_logs/judgments.db")
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "./checkpoints")
THOUGHT_LOG_PATH = os.getenv("THOUGHT_LOG_PATH", "./logs/agent_thoughts.jsonl")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
