"""
Slack incoming-webhook delivery.

Approvals are where engineering leads actually live, so the approval gate needs
to reach Slack. Incoming webhooks (rather than a Slack app) keep setup to a
paste-one-URL step and require no OAuth scopes review from the customer's
workspace admin.
"""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

_EMOJI = {"info": ":large_blue_circle:", "warning": ":warning:", "critical": ":rotating_light:"}


def post(webhook_url: str, *, title: str, body: str, url: str, severity: str = "info") -> bool:
    if not webhook_url:
        return False

    payload = {
        "text": f"{_EMOJI.get(severity, ':robot_face:')} {title}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn",
                                         "text": f"{_EMOJI.get(severity, ':robot_face:')} *{title}*"}},
        ],
    }
    if body:
        payload["blocks"].append(
            {"type": "section", "text": {"type": "mrkdwn", "text": body[:2900]}}
        )
    payload["blocks"].append({
        "type": "actions",
        "elements": [{
            "type": "button",
            "text": {"type": "plain_text", "text": "Open run"},
            "url": url,
            "style": "primary" if severity != "critical" else "danger",
        }],
    })

    try:
        r = httpx.post(webhook_url, json=payload, timeout=10)
        if r.status_code >= 400:
            log.warning("Slack webhook returned %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception:
        log.exception("Slack webhook delivery failed")
        return False


def test(webhook_url: str) -> bool:
    return post(
        webhook_url,
        title="Agentic SDLC connected",
        body="Approval requests, run failures and deploy events will appear here.",
        url="https://localhost",
        severity="info",
    )
