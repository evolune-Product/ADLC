"""
The model-provider catalogue — every LLM vendor a workspace can bring a key for.

This platform sells orchestration and governance, not tokens. It does not
resell inference and it does not want custody of anyone's model spend: an org
brings its own key, the tokens are billed by the vendor on the org's own
contract, and what this product charges for is the pipeline around them. That
is a positioning choice as much as an architectural one — "your key, your
vendor agreement, your data-processing terms" is the answer to the first
question every enterprise security review asks, and it removes inference from
this company's COGS entirely.

So the catalogue below is deliberately wide. The point is not that we have
integrated twenty vendors; it is that a team who already pays OpenAI, or has
Bedrock credits, or runs Llama on their own GPUs, never has to buy a second
model contract to use this platform.

Wire formats, not vendors
-------------------------
Twenty providers do not need twenty clients. Almost all of them speak the
OpenAI chat-completions shape, so the catalogue records a `wire` per provider
and `llm_service` has one implementation per wire:

    anthropic   native SDK — Claude
    openai      /chat/completions — the majority, including Azure, Groq,
                DeepSeek, xAI, Together, Fireworks, OpenRouter, Mistral,
                Perplexity, Cerebras, DeepInfra, vLLM, LM Studio
    google      :generateContent — Gemini
    ollama      /api/generate — local models

Adding a provider that speaks one of those four is a dict literal here, not
code. That is the whole reason this file is a registry rather than a chain of
if-statements in the service.

On model ids
------------
`suggested_models` is a convenience list, **not** a closed set. Model ids churn
faster than any hardcoded list survives, so the API accepts any string the user
types and these are only autocomplete hints. A stale allow-list would reject a
model the vendor shipped last week, which is a worse failure than an unknown id
reaching the provider and coming back with a clear error.

On pricing
----------
Cost attribution is only honest if the numbers are real. `llm_service` carries
published prices for the models this repo has grounding for; for everything
else the catalogue says so (`pricing: "unknown"`) and the workspace can enter
its own rate — which is the correct answer anyway for anyone on a negotiated
or committed-spend contract.
"""
from __future__ import annotations

# Auth shapes a provider can need beyond a bare API key.
#   key        — an API key in a header. The common case.
#   key+url    — a key plus a base URL the user must supply (Azure, self-hosted).
#   url        — a base URL only; no credential (a local Ollama, an internal proxy).
AUTH_KEY = "key"
AUTH_KEY_URL = "key+url"
AUTH_URL = "url"


PROVIDERS: list[dict] = [
    # ── Frontier labs ─────────────────────────────────────────────────────────
    {
        "key": "anthropic",
        "label": "Anthropic",
        "family": "frontier",
        "wire": "anthropic",
        "auth": AUTH_KEY,
        "base_url": "https://api.anthropic.com",
        "key_hint": "sk-ant-…",
        "console_url": "https://console.anthropic.com/settings/keys",
        "docs_url": "https://docs.anthropic.com/en/api/getting-started",
        "suggested_models": [
            "claude-opus-5", "claude-sonnet-5", "claude-sonnet-4-6", "claude-haiku-4-5",
        ],
        "pricing": "published",
        "notes": "The platform default. Tool-use is native, which is what the "
                 "agent nodes rely on for structured output.",
    },
    {
        "key": "openai",
        "label": "OpenAI",
        "family": "frontier",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.openai.com/v1",
        "key_hint": "sk-…",
        "console_url": "https://platform.openai.com/api-keys",
        "docs_url": "https://platform.openai.com/docs/api-reference/chat",
        "suggested_models": ["gpt-5.6", "gpt-5", "gpt-4o", "o3"],
        "pricing": "published",
    },
    {
        "key": "google",
        "label": "Google Gemini",
        "family": "frontier",
        "wire": "google",
        "auth": AUTH_KEY,
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "key_hint": "AIza…",
        "console_url": "https://aistudio.google.com/apikey",
        "docs_url": "https://ai.google.dev/gemini-api/docs",
        "suggested_models": [
            "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash",
        ],
        "pricing": "unknown",
        "notes": "Gemini uses its own :generateContent shape rather than the "
                 "OpenAI one, and passes the key as a header rather than a bearer token.",
    },
    {
        "key": "xai",
        "label": "xAI (Grok)",
        "family": "frontier",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.x.ai/v1",
        "key_hint": "xai-…",
        "console_url": "https://console.x.ai",
        "docs_url": "https://docs.x.ai/docs/api-reference",
        "suggested_models": ["grok-4", "grok-3", "grok-3-mini"],
        "pricing": "unknown",
    },
    {
        "key": "mistral",
        "label": "Mistral AI",
        "family": "frontier",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.mistral.ai/v1",
        "console_url": "https://console.mistral.ai/api-keys",
        "docs_url": "https://docs.mistral.ai/api/",
        "suggested_models": ["mistral-large-latest", "codestral-latest", "mistral-small-latest"],
        "pricing": "unknown",
        "notes": "Codestral is code-specialised — a reasonable choice for the Dev agent "
                 "on a cost-sensitive workspace.",
    },
    {
        "key": "deepseek",
        "label": "DeepSeek",
        "family": "frontier",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.deepseek.com/v1",
        "console_url": "https://platform.deepseek.com/api_keys",
        "docs_url": "https://api-docs.deepseek.com/",
        "suggested_models": ["deepseek-chat", "deepseek-reasoner"],
        "pricing": "unknown",
    },
    {
        "key": "cohere",
        "label": "Cohere",
        "family": "frontier",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "console_url": "https://dashboard.cohere.com/api-keys",
        "docs_url": "https://docs.cohere.com/docs/compatibility-api",
        "suggested_models": ["command-a-03-2025", "command-r-plus"],
        "pricing": "unknown",
        "notes": "Reached through Cohere's OpenAI-compatibility endpoint rather than "
                 "its native API, so it needs no separate client.",
    },

    # ── Fast inference hosts ──────────────────────────────────────────────────
    {
        "key": "groq",
        "label": "Groq",
        "family": "inference",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.groq.com/openai/v1",
        "key_hint": "gsk_…",
        "console_url": "https://console.groq.com/keys",
        "docs_url": "https://console.groq.com/docs/openai",
        "suggested_models": ["llama-3.3-70b-versatile", "qwen-2.5-coder-32b"],
        "pricing": "unknown",
    },
    {
        "key": "cerebras",
        "label": "Cerebras",
        "family": "inference",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.cerebras.ai/v1",
        "key_hint": "csk-…",
        "console_url": "https://cloud.cerebras.ai",
        "docs_url": "https://inference-docs.cerebras.ai/introduction",
        "suggested_models": ["llama-3.3-70b", "qwen-3-32b"],
        "pricing": "unknown",
    },
    {
        "key": "together",
        "label": "Together AI",
        "family": "inference",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.together.xyz/v1",
        "console_url": "https://api.together.ai/settings/api-keys",
        "docs_url": "https://docs.together.ai/docs/openai-api-compatibility",
        "suggested_models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "Qwen/Qwen2.5-Coder-32B-Instruct",
        ],
        "pricing": "unknown",
    },
    {
        "key": "fireworks",
        "label": "Fireworks AI",
        "family": "inference",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.fireworks.ai/inference/v1",
        "key_hint": "fw_…",
        "console_url": "https://fireworks.ai/account/api-keys",
        "docs_url": "https://docs.fireworks.ai/tools-sdks/openai-compatibility",
        "suggested_models": ["accounts/fireworks/models/llama-v3p3-70b-instruct"],
        "pricing": "unknown",
    },
    {
        "key": "deepinfra",
        "label": "DeepInfra",
        "family": "inference",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.deepinfra.com/v1/openai",
        "console_url": "https://deepinfra.com/dash/api_keys",
        "docs_url": "https://deepinfra.com/docs/openai_api",
        "suggested_models": ["meta-llama/Llama-3.3-70B-Instruct"],
        "pricing": "unknown",
    },
    {
        "key": "nebius",
        "label": "Nebius AI Studio",
        "family": "inference",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.studio.nebius.ai/v1",
        "console_url": "https://studio.nebius.ai",
        "docs_url": "https://docs.nebius.com/studio/inference/api",
        "suggested_models": ["meta-llama/Llama-3.3-70B-Instruct"],
        "pricing": "unknown",
    },

    # ── Routers and aggregators ───────────────────────────────────────────────
    {
        "key": "openrouter",
        "label": "OpenRouter",
        "family": "router",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://openrouter.ai/api/v1",
        "key_hint": "sk-or-…",
        "console_url": "https://openrouter.ai/keys",
        "docs_url": "https://openrouter.ai/docs/quickstart",
        "suggested_models": [
            "anthropic/claude-sonnet-4.5", "openai/gpt-5", "google/gemini-2.5-pro",
        ],
        "pricing": "unknown",
        "notes": "One key, most vendors. The pragmatic choice for a workspace that "
                 "wants to switch models per agent without holding six contracts.",
    },
    {
        "key": "perplexity",
        "label": "Perplexity",
        "family": "router",
        "wire": "openai",
        "auth": AUTH_KEY,
        "base_url": "https://api.perplexity.ai",
        "key_hint": "pplx-…",
        "console_url": "https://www.perplexity.ai/settings/api",
        "docs_url": "https://docs.perplexity.ai/api-reference/chat-completions-post",
        "suggested_models": ["sonar-pro", "sonar-reasoning"],
        "pricing": "unknown",
        "notes": "Search-grounded. Useful for the Planner when a ticket needs current "
                 "external context; a poor fit for the Dev agent.",
    },

    # ── Enterprise clouds ─────────────────────────────────────────────────────
    {
        "key": "azure",
        "label": "Azure OpenAI",
        "family": "cloud",
        "wire": "openai",
        "auth": AUTH_KEY_URL,
        "base_url": None,
        "url_hint": "https://<resource>.openai.azure.com/openai/deployments/<deployment>",
        "console_url": "https://portal.azure.com",
        "docs_url": "https://learn.microsoft.com/azure/ai-services/openai/reference",
        "suggested_models": ["gpt-4o", "gpt-5"],
        "pricing": "published",
        "notes": "The endpoint is per-resource and per-deployment, so the base URL is "
                 "required. Azure authenticates with an `api-key` header rather than "
                 "a bearer token; the wire format is otherwise identical to OpenAI.",
    },

    # ── Self-hosted and local ─────────────────────────────────────────────────
    {
        "key": "ollama",
        "label": "Ollama",
        "family": "self_hosted",
        "wire": "ollama",
        "auth": AUTH_URL,
        "base_url": "http://localhost:11434",
        "url_hint": "http://localhost:11434",
        "docs_url": "https://github.com/ollama/ollama/blob/main/docs/api.md",
        "suggested_models": ["llama3.3", "qwen2.5-coder", "deepseek-r1"],
        "pricing": "free",
        "notes": "No key, no egress, no per-token cost. The air-gapped path, and the "
                 "reason this platform can install from a compose file inside a "
                 "perimeter with no outbound internet at all.",
    },
    {
        "key": "vllm",
        "label": "vLLM",
        "family": "self_hosted",
        "wire": "openai",
        "auth": AUTH_KEY_URL,
        "base_url": None,
        "url_hint": "http://vllm.internal:8000/v1",
        "docs_url": "https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html",
        "suggested_models": ["meta-llama/Llama-3.3-70B-Instruct"],
        "pricing": "free",
        "notes": "Your own GPUs, OpenAI wire format. The key is whatever `--api-key` "
                 "the server was started with; leave it blank if it was started without one.",
    },
    {
        "key": "lmstudio",
        "label": "LM Studio",
        "family": "self_hosted",
        "wire": "openai",
        "auth": AUTH_URL,
        "base_url": "http://localhost:1234/v1",
        "url_hint": "http://localhost:1234/v1",
        "docs_url": "https://lmstudio.ai/docs/app/api/endpoints/openai",
        "suggested_models": ["qwen2.5-coder-32b-instruct"],
        "pricing": "free",
    },
    {
        "key": "openai_compatible",
        "label": "Any OpenAI-compatible endpoint",
        "family": "self_hosted",
        "wire": "openai",
        "auth": AUTH_KEY_URL,
        "base_url": None,
        "url_hint": "https://your-gateway.example.com/v1",
        "docs_url": "https://platform.openai.com/docs/api-reference/chat",
        "suggested_models": [],
        "pricing": "unknown",
        "notes": "The escape hatch: an internal gateway, a proxy that enforces DLP, a "
                 "vendor not listed here. If it speaks /chat/completions, it works.",
    },
]

BY_KEY: dict[str, dict] = {p["key"]: p for p in PROVIDERS}

FAMILIES = {
    "frontier":    "Frontier labs",
    "inference":   "Fast inference hosts",
    "router":      "Routers and aggregators",
    "cloud":       "Enterprise clouds",
    "self_hosted": "Self-hosted and local",
}


def get(provider_key: str) -> dict | None:
    return BY_KEY.get((provider_key or "").lower())


def wire_for(provider_key: str) -> str:
    """Which client implementation serves this provider. Defaults to the
    OpenAI shape, because an unknown provider is far more likely to be another
    OpenAI-compatible endpoint than anything else."""
    p = get(provider_key)
    return p["wire"] if p else "openai"


def base_url_for(provider_key: str, override: str | None = None) -> str | None:
    """
    The endpoint to call. A stored per-credential override always wins — Azure
    and every self-hosted deployment have a URL only the customer knows.
    """
    if override:
        return override.rstrip("/")
    p = get(provider_key)
    return (p.get("base_url") or None) if p else None


def requires_base_url(provider_key: str) -> bool:
    p = get(provider_key)
    return bool(p and p["auth"] in (AUTH_KEY_URL,) and not p.get("base_url"))


def requires_key(provider_key: str) -> bool:
    """`url`-auth providers (a local Ollama, an unauthenticated internal proxy)
    legitimately have no credential."""
    p = get(provider_key)
    return bool(p and p["auth"] != AUTH_URL)


def catalog() -> list[dict]:
    """
    The catalogue as the settings UI needs it, grouped by family.

    Never includes a secret — this endpoint describes what *could* be
    connected, and is deliberately safe to serve to any authenticated user.
    """
    out = []
    for family, label in FAMILIES.items():
        members = [p for p in PROVIDERS if p["family"] == family]
        if members:
            out.append({
                "family": family,
                "label": label,
                "providers": [
                    {k: v for k, v in p.items() if k != "family"} for p in members
                ],
            })
    return out
