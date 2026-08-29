"""
LLM Configuration schemas for BYOK (Bring Your Own Key) model.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LLMConfigIn(BaseModel):
    """Request schema for saving LLM configuration."""
    provider: str = Field(..., description="LLM provider: anthropic, openai, google")
    api_key: str = Field(..., description="API key (will be encrypted)")
    model: str = Field(..., description="Model name: claude-sonnet-4-6, gpt-4, etc")
    config: Optional[dict] = Field(default={}, description="Additional config: max_tokens, temperature, etc")


class LLMConfigOut(BaseModel):
    """Response schema for LLM configuration."""
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key_hint: Optional[str] = None  # Last 4 chars of API key
    is_configured: bool = False
    config: dict = {}


class LLMTestRequest(BaseModel):
    """Request schema for testing LLM connection."""
    provider: str
    api_key: str
    model: str


class LLMTestResponse(BaseModel):
    """Response schema for LLM connection test."""
    success: bool
    message: str
    model_info: Optional[dict] = None
