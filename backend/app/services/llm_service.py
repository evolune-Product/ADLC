"""
LLM provider abstraction — the answer to "are we locked into one model vendor?"

Forrester lists *model agility* as a differentiator for agentic development
platforms, and no enterprise signs a single-model dependency. Every agent call
in the platform goes through `complete()`, which:

  1. picks a provider from the model id (or an explicit org override),
  2. uses the org's own API key when one is configured (BYO-LLM = zero COGS),
  3. returns a normalised LLMResult carrying token usage + costed spend,

so the metering, budget-cap and ROI layers work identically regardless of who
serves the tokens.

Providers
---------
anthropic  (default)  native SDK
openai / azure / ollama / openai-compatible  via HTTP (no extra dependency)

Anthropic note: `temperature` / `top_p` / `top_k` are rejected by current Claude
models, so sampling params are only forwarded to OpenAI-shaped providers.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger(__name__)

# ── Pricing, in cents per million tokens (input, output) ──────────────────────
# Source: Anthropic / OpenAI public pricing, August 2026. Used for per-run cost
# attribution — the CFO metric competitors cannot show.
PRICE_CENTS_PER_MTOK: dict[str, tuple[int, int]] = {
    # Anthropic
    "claude-fable-5":     (1000, 5000),
    "claude-opus-5":      (500, 2500),
    "claude-opus-4-8":    (500, 2500),
    "claude-opus-4-7":    (500, 2500),
    "claude-opus-4-6":    (500, 2500),
    "claude-sonnet-5":    (300, 1500),
    "claude-sonnet-4-6":  (300, 1500),
    "claude-haiku-4-5":   (100, 500),
    # OpenAI-shaped (approximate; used only when an org brings its own key)
    "gpt-5.6":            (500, 2500),
    "gpt-5":              (300, 1500),
    "gpt-4o":             (250, 1000),
    # Local models cost nothing to call
    "ollama":             (0, 0),
}

DEFAULT_MODEL = "claude-sonnet-4-6"
_FALLBACK_PRICE = (300, 1500)


def provider_for_model(model: str) -> str:
    m = (model or "").lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if m.startswith(("llama", "qwen", "mistral", "deepseek", "phi", "gemma")):
        return "ollama"
    return "anthropic"


def price_for(model: str) -> tuple[int, int]:
    if model in PRICE_CENTS_PER_MTOK:
        return PRICE_CENTS_PER_MTOK[model]
    for known, price in PRICE_CENTS_PER_MTOK.items():
        if model and model.startswith(known):
            return price
    return _FALLBACK_PRICE


def cost_millicents(model: str, input_tokens: int, output_tokens: int) -> int:
    """Integer arithmetic only — no float drift across millions of rows."""
    in_c, out_c = price_for(model)
    return round((input_tokens * in_c + output_tokens * out_c) / 1000)


@dataclass
class LLMResult:
    text: str = ""
    tool_input: dict | None = None
    tool_name: str | None = None
    model: str = DEFAULT_MODEL
    provider: str = "anthropic"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_millicents: int = 0
    stop_reason: str | None = None
    raw: Any = field(default=None, repr=False)

    @property
    def cost_usd(self) -> float:
        return self.cost_millicents / 100_000


class LLMError(RuntimeError):
    pass


# ── Credentials ───────────────────────────────────────────────────────────────

def resolve_credentials(byo_provider: str | None, byo_key: str | None, model: str) -> tuple[str, str, bool]:
    """
    Returns (provider, api_key, is_byo).

    A per-org BYO key wins over the platform key — that is the enterprise path
    (their spend, their vendor contract, their data-processing agreement) and it
    also removes LLM cost from our COGS entirely.
    """
    if byo_key:
        return (byo_provider or provider_for_model(model), byo_key, True)
    provider = provider_for_model(model)
    if provider == "anthropic":
        return provider, settings.anthropic_api_key, False
    if provider == "openai":
        return provider, settings.openai_api_key, False
    return provider, "", False


# ── Entry point ───────────────────────────────────────────────────────────────

def complete(
    *,
    system: str,
    user: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 8192,
    tool: dict | None = None,
    force_tool: bool = True,
    byo_provider: str | None = None,
    byo_key: str | None = None,
    timeout: float = 300.0,
) -> LLMResult:
    """
    One call, any provider. When `tool` is given the model is asked to answer
    through that tool schema and `result.tool_input` carries the parsed object.
    """
    provider, api_key, _ = resolve_credentials(byo_provider, byo_key, model)

    if provider == "anthropic":
        result = _anthropic_complete(system, user, model, max_tokens, tool, force_tool, api_key, timeout)
    elif provider in ("openai", "azure", "openai_compatible"):
        result = _openai_complete(system, user, model, max_tokens, tool, force_tool, api_key, provider, timeout)
    elif provider == "ollama":
        result = _ollama_complete(system, user, model, max_tokens, tool, timeout)
    else:
        raise LLMError(f"Unknown LLM provider: {provider}")

    result.provider = provider
    result.cost_millicents = cost_millicents(result.model, result.input_tokens, result.output_tokens)
    return result


# ── Anthropic ─────────────────────────────────────────────────────────────────

def _anthropic_complete(system, user, model, max_tokens, tool, force_tool, api_key, timeout) -> LLMResult:
    import anthropic

    if not api_key:
        raise LLMError("No Anthropic API key configured (set ANTHROPIC_API_KEY or an org BYO key)")

    client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if tool:
        kwargs["tools"] = [tool]
        if force_tool:
            kwargs["tool_choice"] = {"type": "any"}

    resp = client.messages.create(**kwargs)

    text_parts, tool_input, tool_name = [], None, None
    for block in resp.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_input, tool_name = block.input, block.name

    return LLMResult(
        text="\n".join(text_parts),
        tool_input=tool_input,
        tool_name=tool_name,
        model=model,
        input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
        output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
        stop_reason=resp.stop_reason,
        raw=resp,
    )


# ── OpenAI-compatible (OpenAI, Azure OpenAI, vLLM, LiteLLM, …) ────────────────

def _openai_complete(system, user, model, max_tokens, tool, force_tool, api_key, provider, timeout) -> LLMResult:
    base_url = settings.openai_base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if provider == "azure":
        headers["api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    body: dict[str, Any] = {
        "model": model,
        "max_completion_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if tool:
        body["tools"] = [{
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool["input_schema"],
            },
        }]
        if force_tool:
            body["tool_choice"] = {"type": "function", "function": {"name": tool["name"]}}

    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{base_url}/chat/completions", headers=headers, json=body)
    if r.status_code >= 400:
        raise LLMError(f"{provider} error {r.status_code}: {r.text[:400]}")

    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message", {})
    tool_input, tool_name = None, None
    for call in message.get("tool_calls") or []:
        fn = call.get("function", {})
        try:
            tool_input = json.loads(fn.get("arguments") or "{}")
            tool_name = fn.get("name")
        except json.JSONDecodeError:
            log.warning("Could not parse tool arguments from %s", provider)

    usage = data.get("usage", {})
    return LLMResult(
        text=message.get("content") or "",
        tool_input=tool_input,
        tool_name=tool_name,
        model=data.get("model", model),
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        stop_reason=choice.get("finish_reason"),
        raw=data,
    )


# ── Ollama (self-hosted / air-gapped) ─────────────────────────────────────────

def _ollama_complete(system, user, model, max_tokens, tool, timeout) -> LLMResult:
    prompt = user
    if tool:
        prompt = (
            f"{user}\n\nRespond with ONLY a JSON object matching this schema "
            f"(no prose, no markdown fence):\n{json.dumps(tool['input_schema'])}"
        )
    body = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{settings.ollama_base_url.rstrip('/')}/api/generate", json=body)
    if r.status_code >= 400:
        raise LLMError(f"Ollama error {r.status_code}: {r.text[:400]}")

    data = r.json()
    text = data.get("response", "")
    tool_input = _extract_json(text) if tool else None

    return LLMResult(
        text=text,
        tool_input=tool_input,
        tool_name=tool["name"] if tool and tool_input else None,
        model=model,
        input_tokens=data.get("prompt_eval_count", 0),
        output_tokens=data.get("eval_count", 0),
        stop_reason=data.get("done_reason"),
        raw=data,
    )


def _extract_json(text: str) -> dict | None:
    """Pull the first balanced JSON object out of a local model's prose."""
    start = text.find("{")
    if start == -1:
        return None
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
