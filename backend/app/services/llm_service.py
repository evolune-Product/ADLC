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
The catalogue lives in `llm_providers.py` — roughly twenty vendors, all
bring-your-own-key. This module implements one client per *wire format* rather
than one per vendor, because almost every provider speaks one of four shapes:

    anthropic   native SDK
    openai      /chat/completions — most of the catalogue, Azure included
    google      :generateContent — Gemini
    ollama      /api/generate — local models

Adding a vendor that speaks one of those is a dict literal in `llm_providers`,
not code here.

This platform does not resell inference. There is a platform-key fallback for
single-tenant and self-hosted installs, but the product path is a workspace
bringing its own key: their vendor contract, their data-processing terms, and
no model spend on our books.

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
from app.services import llm_providers

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
    """
    Best guess at the vendor from a bare model id.

    Only a fallback. When a workspace has stored a credential, the provider is
    read off that row instead — an id like `qwen2.5-coder` is served by Groq,
    Together, Fireworks, DeepInfra, vLLM and a local Ollama alike, and guessing
    from the string cannot tell them apart. This exists so a model named with
    no credential configured still routes somewhere sensible.
    """
    m = (model or "").lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    if m.startswith("gemini"):
        return "google"
    if m.startswith("grok"):
        return "xai"
    if m.startswith(("mistral", "codestral", "ministral", "magistral")):
        return "mistral"
    if m.startswith("deepseek"):
        return "deepseek"
    if m.startswith("command"):
        return "cohere"
    if m.startswith("sonar"):
        return "perplexity"
    # A vendor-prefixed id ("anthropic/claude-…", "meta-llama/…") is the
    # OpenRouter and Together convention.
    if "/" in m:
        return "openrouter"
    if m.startswith(("llama", "qwen", "phi", "gemma", "starcoder", "codellama")):
        return "ollama"
    return "anthropic"


def price_for(model: str) -> tuple[int, int]:
    if model in PRICE_CENTS_PER_MTOK:
        return PRICE_CENTS_PER_MTOK[model]
    for known, price in PRICE_CENTS_PER_MTOK.items():
        if model and model.startswith(known):
            return price
    return _FALLBACK_PRICE


def cost_millicents(model: str, input_tokens: int, output_tokens: int,
                    overrides: dict | None = None) -> int:
    """
    Integer arithmetic only — no float drift across millions of rows.

    `overrides` is the workspace's own per-model rate in cents per million
    tokens, `{"gpt-5": {"input": 300, "output": 1500}}`. It wins over the
    published table because anyone on a committed-spend or negotiated contract
    has a truer number than any public price list, and because this repo has
    published prices for only a minority of the catalogue — inventing the rest
    would make every cost figure in the product untrustworthy.
    """
    rate = (overrides or {}).get(model)
    if isinstance(rate, dict) and "input" in rate and "output" in rate:
        in_c, out_c = int(rate["input"]), int(rate["output"])
    else:
        in_c, out_c = price_for(model)
    return round((input_tokens * in_c + output_tokens * out_c) / 1000)


def has_published_price(model: str) -> bool:
    """Whether the cost figure for this model is a real published rate or the
    generic fallback. The UI uses this to prompt for a rate override rather
    than quietly showing an invented number as if it were measured."""
    if model in PRICE_CENTS_PER_MTOK:
        return True
    return any(model and model.startswith(k) for k in PRICE_CENTS_PER_MTOK)


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

def resolve_credentials(byo_provider: str | None, byo_key: str | None, model: str,
                        byo_base_url: str | None = None) -> tuple[str, str, bool, str | None]:
    """
    Returns (provider, api_key, is_byo, base_url).

    A workspace's own credential always wins over the platform key. That is the
    product path, not an enterprise upsell: their spend, their vendor contract,
    their data-processing agreement, and no inference cost on our books.

    Some providers legitimately have no key at all — a local Ollama, an
    unauthenticated internal gateway — so an empty key with a provider named is
    a valid, deliberate configuration rather than a missing one. `is_byo` keys
    off the provider being explicitly chosen, not off the secret being present,
    which is what keeps a self-hosted workspace from being billed as if it had
    used the platform key.
    """
    if byo_provider or byo_key:
        provider = byo_provider or provider_for_model(model)
        return (
            provider,
            byo_key or "",
            True,
            llm_providers.base_url_for(provider, byo_base_url),
        )

    # No workspace credential. Fall back to a platform key if this deployment
    # has one configured — the single-tenant and self-hosted case.
    provider = provider_for_model(model)
    if provider == "anthropic":
        return provider, settings.anthropic_api_key, False, llm_providers.base_url_for(provider)
    if provider == "openai":
        return provider, settings.openai_api_key, False, llm_providers.base_url_for(provider)
    return provider, "", False, llm_providers.base_url_for(provider)


# ── Entry point ───────────────────────────────────────────────────────────────

# Wire formats with a vision path wired up below. Kept as an explicit set
# rather than "try and see" so a workspace running Ollama or a bare OpenAI-
# compatible gateway gets a clear error instead of a silently ignored image —
# see `complete()`'s docstring for the reasoning.
_VISION_WIRES = {"anthropic", "openai"}


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
    byo_base_url: str | None = None,
    price_overrides: dict | None = None,
    timeout: float = 300.0,
    image_base64: str | None = None,
    image_media_type: str = "image/png",
) -> LLMResult:
    """
    One call, any provider. When `tool` is given the model is asked to answer
    through that tool schema and `result.tool_input` carries the parsed object.

    `image_base64` is the minimal vision extension added for
    `agents/simulation_agent.py`, which has to show the model a screenshot of
    the page it is driving. It rides the same two wire formats every other
    agent call already uses — the native Anthropic SDK (`source.type: base64`
    content blocks) and the OpenAI chat-completions shape (`image_url` with a
    `data:` URI, which is also what Azure OpenAI and most OpenAI-compatible
    gateways accept). Google and Ollama are reached by this same `complete()`
    for text-only agent calls, but neither wire has an image path implemented
    here — passing an image on those raises `LLMError` immediately rather than
    silently dropping it and letting the persona "see" nothing, which is the
    one failure mode a simulation agent must never fail quietly into (the
    whole point of the loop is grounding the next click in what the screen
    actually shows).
    """
    provider, api_key, _, base_url = resolve_credentials(
        byo_provider, byo_key, model, byo_base_url)

    # Dispatch on wire format, not on vendor. Twenty providers, four clients.
    wire = llm_providers.wire_for(provider)
    if image_base64 and wire not in _VISION_WIRES:
        raise LLMError(
            f"Provider '{provider}' (wire '{wire}') has no vision path wired up in this "
            "platform yet — configure an Anthropic or OpenAI-shaped model credential for "
            "vision-driven agents like the simulation agent."
        )

    if wire == "anthropic":
        result = _anthropic_complete(system, user, model, max_tokens, tool, force_tool, api_key,
                                     timeout, image_base64, image_media_type)
    elif wire == "google":
        result = _google_complete(system, user, model, max_tokens, tool, api_key, base_url, timeout)
    elif wire == "ollama":
        result = _ollama_complete(system, user, model, max_tokens, tool, timeout, base_url)
    elif wire == "openai":
        result = _openai_complete(system, user, model, max_tokens, tool, force_tool,
                                  api_key, provider, timeout, base_url, image_base64, image_media_type)
    else:
        raise LLMError(f"Unknown LLM wire format '{wire}' for provider '{provider}'")

    result.provider = provider
    result.cost_millicents = cost_millicents(
        result.model, result.input_tokens, result.output_tokens, price_overrides)
    return result


# ── Anthropic ─────────────────────────────────────────────────────────────────

def _anthropic_complete(system, user, model, max_tokens, tool, force_tool, api_key, timeout,
                        image_base64=None, image_media_type="image/png") -> LLMResult:
    import anthropic

    if not api_key:
        raise LLMError("No Anthropic API key configured (set ANTHROPIC_API_KEY or an org BYO key)")

    client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
    # A vision call needs `content` as a block list (image block + text block)
    # rather than the bare string every other agent call sends — Claude reads
    # blocks in order, so the image comes first and the question follows it.
    content: Any = user
    if image_base64:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": image_media_type,
                                         "data": image_base64}},
            {"type": "text", "text": user},
        ]
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": content}],
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

def _openai_complete(system, user, model, max_tokens, tool, force_tool, api_key,
                     provider, timeout, base_url=None, image_base64=None,
                     image_media_type="image/png") -> LLMResult:
    # The base URL is what makes one client serve fifteen vendors. It comes
    # from the stored credential when the customer set one (Azure, vLLM, an
    # internal gateway), else the catalogue's default for that provider, else
    # the legacy global setting.
    base_url = (base_url or llm_providers.base_url_for(provider)
                or settings.openai_base_url).rstrip("/")
    if not base_url:
        raise LLMError(f"No endpoint configured for provider '{provider}' — set a base URL on the credential")
    headers = {"Content-Type": "application/json"}
    if provider == "azure":
        headers["api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    # Vision on the OpenAI chat-completions shape: `content` becomes a part
    # list with an inline data: URI rather than a bare string. Same trigger
    # and same block-ordering rationale as the Anthropic wire above.
    user_content: Any = user
    if image_base64:
        user_content = [
            {"type": "image_url", "image_url": {"url": f"data:{image_media_type};base64,{image_base64}"}},
            {"type": "text", "text": user},
        ]

    body: dict[str, Any] = {
        "model": model,
        "max_completion_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
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



# ── Google Gemini ─────────────────────────────────────────────────────────────

def _google_complete(system, user, model, max_tokens, tool, api_key, base_url, timeout) -> LLMResult:
    """
    Gemini's own :generateContent shape.

    Three things differ from the OpenAI wire and each one silently breaks the
    call if assumed away: the key travels in an `x-goog-api-key` header rather
    than a bearer token, the system prompt is a distinct `systemInstruction`
    field rather than a message with role "system", and tool calls come back as
    a `functionCall` part inside the candidate's content rather than as a
    `tool_calls` array on the message.
    """
    if not api_key:
        raise LLMError("No Google API key configured for this workspace")

    root = (base_url or llm_providers.base_url_for("google")).rstrip("/")
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tool:
        body["tools"] = [{
            "functionDeclarations": [{
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": _gemini_schema(tool["input_schema"]),
            }]
        }]

    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{root}/models/{model}:generateContent", headers=headers, json=body)
    if r.status_code >= 400:
        raise LLMError(f"google error {r.status_code}: {r.text[:400]}")

    data = r.json()
    candidate = (data.get("candidates") or [{}])[0]
    parts = (candidate.get("content") or {}).get("parts") or []

    text, tool_input, tool_name = "", None, None
    for part in parts:
        if "text" in part:
            text += part["text"]
        fn = part.get("functionCall")
        if fn:
            tool_name = fn.get("name")
            tool_input = fn.get("args") or {}

    # A model asked for a tool but answered in prose happens often enough on
    # non-Anthropic providers to be worth recovering from rather than failing.
    if tool and tool_input is None and text:
        tool_input = _extract_json(text)
        tool_name = tool["name"] if tool_input else None

    usage = data.get("usageMetadata", {})
    return LLMResult(
        text=text,
        tool_input=tool_input,
        tool_name=tool_name,
        model=model,
        input_tokens=usage.get("promptTokenCount", 0),
        output_tokens=usage.get("candidatesTokenCount", 0),
        stop_reason=candidate.get("finishReason"),
        raw=data,
    )


# Keys JSON Schema carries that Gemini's function-declaration schema rejects
# outright with a 400 rather than ignoring.
_GEMINI_UNSUPPORTED = {
    "additionalProperties", "$schema", "$id", "definitions", "$defs",
    "default", "examples", "title", "const",
}


def _gemini_schema(schema: dict) -> dict:
    """
    Strip the JSON Schema keys Gemini refuses.

    The agent tool schemas are written once and handed to every provider.
    Anthropic and OpenAI accept the full vocabulary; Gemini 400s on several
    common keys, so rather than maintain a second copy of every tool definition
    the schema is filtered on the way out.
    """
    if not isinstance(schema, dict):
        return schema
    out = {}
    for k, v in schema.items():
        if k in _GEMINI_UNSUPPORTED:
            continue
        if k == "properties" and isinstance(v, dict):
            out[k] = {pk: _gemini_schema(pv) for pk, pv in v.items()}
        elif k == "items":
            out[k] = _gemini_schema(v)
        elif isinstance(v, dict):
            out[k] = _gemini_schema(v)
        else:
            out[k] = v
    return out


# ── Ollama (self-hosted / air-gapped) ─────────────────────────────────────────

def _ollama_complete(system, user, model, max_tokens, tool, timeout, base_url=None) -> LLMResult:
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
        host = (base_url or settings.ollama_base_url).rstrip("/")
        r = client.post(f"{host}/api/generate", json=body)
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
