"""
PageIndex SDK Configuration Module

Handles loading configuration from environment variables and .env files.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


@dataclass
class SDKConfig:
    """Configuration for PageIndex SDK."""

    openai_api_key: Optional[str] = None
    mongodb_uri: str = "mongodb://localhost:27017"
    model: str = "gpt-4o-2024-11-20"
    db_name: str = "pageindex"

    def validate(self) -> None:
        """Validate configuration. Raises ValueError if invalid."""
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set PAGEINDEX_OPENAI_API_KEY environment variable or pass in config."
            )


def load_config(overrides: Optional[dict] = None) -> SDKConfig:
    """
    Load SDK configuration from environment variables.

    Environment variables (with PAGEINDEX_ prefix):
        - PAGEINDEX_OPENAI_API_KEY: OpenAI API key (required)
        - PAGEINDEX_MONGODB_URI: MongoDB connection URI
        - PAGEINDEX_MODEL: OpenAI model to use
        - PAGEINDEX_DB_NAME: MongoDB database name

    Args:
        overrides: Optional dict to override environment values

    Returns:
        SDKConfig instance

    Example:
        >>> config = load_config()
        >>> config = load_config({"model": "gpt-4o-mini"})
    """
    # Load .env file if present
    load_dotenv()

    # Build config from environment
    config_dict = {
        "openai_api_key": os.environ.get("PAGEINDEX_OPENAI_API_KEY") or os.environ.get("CHATGPT_API_KEY"),
        "mongodb_uri": os.environ.get("PAGEINDEX_MONGODB_URI", "mongodb://localhost:27017"),
        "model": os.environ.get("PAGEINDEX_MODEL", "gpt-4o-2024-11-20"),
        "db_name": os.environ.get("PAGEINDEX_DB_NAME", "pageindex"),
    }

    # Apply overrides
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                config_dict[key] = value

    return SDKConfig(**config_dict)
