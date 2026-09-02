"""
Simulation Agent — persona-driven simulated user testing.

WHAT THIS DOES THAT THE QA AGENT DOESN'T
`agents/qa_agent.py` reads a PR diff and asks an LLM whether the code looks
right — it never runs the application. This module drives a real, running app
through a real headless-Chromium browser (Playwright), acting as a named
Persona (`models/persona.py`): a free-text goal/behavior plus a starting URL.
It is the closest thing this platform has to actually putting a user in front
of the product before a human does.

THE LOOP (bounded at `SimulationRun.max_steps`, default 15)
  1. Screenshot the current page.
  2. Ask the configured LLM, as this persona, "what would you do next — and is
     anything here broken, confusing, or blocking you?" via a single
     vision-capable tool call (`_STEP_TOOL`) so the answer comes back
     structured rather than parsed out of prose.
  3. If the model reports the goal reached or itself stuck, stop.
  4. Otherwise translate its answer into one concrete Playwright action
     (click / type / navigate / scroll — see `_execute`) and run it.
  5. Anything flagged along the way becomes a `SimulationFinding` via
     `services/simulation_service.create_finding`, screenshot attached.

GROUNDING STRATEGY: visible text, not coordinates or raw selectors
The model sees a screenshot, the same thing a human tester sees — not the DOM.
So actions are grounded on the *visible/accessible name* of an element
("Sign up", "Email address", "Continue") and `_locate` tries several
Playwright locator strategies in that order (role, label, placeholder, plain
text) until one resolves. This is deliberately simpler than a full
set-of-marks / DOM-serialization pipeline: it is enough to drive a typical
signup/checkout/settings flow, and a v1 optimizing for "ships and is honest
about its limits" over "handles every possible UI" is the right trade here.
A locator miss is not immediately fatal — the failure is fed back into the
next prompt so the model can try a different approach, and only three
consecutive misses ends the run (and is itself logged as a low-severity
finding, since a real user would be just as stuck).

NO CODE-WRITE ACCESS, ON PURPOSE
This agent only ever calls Playwright page actions and one read-only LLM
call. It has no git, GitHub, or filesystem-write access to the product's own
repo — matching the "agent proposes, human approves" governance model this
whole platform is built on. A finding is a suggestion a human reads, same as
every `ReviewFinding` the Reviewer agent already produces.

OPERATIONAL DEPENDENCY
This module imports `playwright.sync_api` lazily (inside `run_simulation`,
not at module load) specifically so importing this file — and therefore
`app.main` and the whole test suite — never fails in an environment where
Playwright's browser binary hasn't been installed. The Python package alone
is not enough: **`playwright install chromium` must be run once per
environment** (this checkout, any Docker image, any worker host) or every
simulation run fails fast with a clear `SimulationRun.error_message` rather
than importing successfully and crashing deep inside a Celery task.
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents._common import call_llm
from app.config import settings
from app.models.persona import Persona
from app.models.simulation import SimulationRun
from app.services import simulation_service

log = logging.getLogger(__name__)

MAX_HISTORY_IN_PROMPT = 6
MAX_CONSECUTIVE_FAILURES = 3
VIEWPORT = {"width": 1280, "height": 800}
NAV_TIMEOUT_MS = 30_000
ACTION_TIMEOUT_MS = 5_000

_SYSTEM_PROMPT = (
    "You are simulating a real human end user of a web application, driving a real "
    "browser one step at a time. You are shown a screenshot of the current page and "
    "must decide the ONE next action this persona would take next, exactly the way a "
    "real, impatient user would — using only what is visible on screen, with no special "
    "knowledge of the app's internals or source code. Actively look for anything that "
    "would confuse, block, or frustrate this specific persona: a functional bug, but "
    "also bad copy, a missing label, a dead end, a confusing error, or a step that does "
    "not match what this persona would expect. Flag it via issue_flagged even if the "
    "page is technically working. Always call the simulation_step tool — never answer "
    "in plain text."
)

_STEP_TOOL = {
    "name": "simulation_step",
    "description": (
        "Report what this persona sees, decide their next action, and flag anything "
        "broken or confusing on the current screen."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "One or two sentences: what is on screen, and why this persona would do this next.",
            },
            "action": {
                "type": "string",
                "enum": ["click", "type", "navigate", "scroll", "goal_reached", "stuck"],
                "description": (
                    "click: click a button/link by its visible text. type: fill a field "
                    "(and optionally submit). navigate: go directly to a URL. scroll: scroll "
                    "down to see more of the page. goal_reached: the persona's goal is "
                    "complete. stuck: the persona cannot find a way to proceed."
                ),
            },
            "target_text": {
                "type": "string",
                "description": "Visible text, label, or placeholder of the element to click or type into. Required for click/type.",
            },
            "value": {
                "type": "string",
                "description": "Text to type, or the URL to navigate to. Required for type/navigate.",
            },
            "submit_after_type": {
                "type": "boolean",
                "description": "Whether to press Enter after typing (e.g. a search box). Only relevant for type.",
            },
            "issue_flagged": {
                "type": "boolean",
                "description": "True if anything on THIS screen would confuse, block, or frustrate this persona.",
            },
            "issue_severity": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low"],
                "description": "Only when issue_flagged is true. critical = persona cannot complete their goal at all.",
            },
            "issue_title": {
                "type": "string",
                "description": "Short (under 12 words) title for the issue. Only when issue_flagged is true.",
            },
            "issue_description": {
                "type": "string",
                "description": "What is wrong, and why it would trip up this persona specifically. Only when issue_flagged is true.",
            },
        },
        "required": ["reasoning", "action"],
    },
}


def run_simulation(db: Session, simulation_run_id) -> SimulationRun:
    """Entry point called by `tasks/simulation_tasks.py`. Loads the run,
    drives the browser, and always leaves the run in a terminal status —
    never raises out to the Celery task."""
    run = db.query(SimulationRun).filter(SimulationRun.id == simulation_run_id).first()
    if not run:
        raise ValueError(f"SimulationRun {simulation_run_id} not found")

    persona = db.query(Persona).filter(Persona.id == run.persona_id).first()
    if not persona:
        run.status = "failed"
        run.error_message = "Persona no longer exists"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return run

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        run.status = "failed"
        run.error_message = (
            "Playwright is not installed in this environment. Run "
            "`pip install -r requirements.txt && playwright install chromium` "
            "(once per environment/Docker image/worker host) and retry."
        )
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        log.error("Simulation run %s failed — Playwright not installed", run.id)
        return run

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    db.commit()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport=VIEWPORT)
                page.set_default_timeout(ACTION_TIMEOUT_MS)
                _drive(db, run, persona, page)
            finally:
                browser.close()
        run.status = "failed" if run.error_message else "completed"
    except PlaywrightError as exc:
        log.exception("Simulation run %s failed (Playwright error)", run.id)
        run.status = "failed"
        run.error_message = f"Browser error: {str(exc)[:1500]}"
    except Exception as exc:                                    # noqa: BLE001
        log.exception("Simulation run %s failed", run.id)
        run.status = "failed"
        run.error_message = str(exc)[:1500]
    finally:
        run.completed_at = datetime.now(timezone.utc)
        db.commit()

    return run


def _drive(db: Session, run: SimulationRun, persona: Persona, page) -> None:
    try:
        page.goto(run.target_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    except Exception as exc:
        run.error_message = f"Could not load the starting URL {run.target_url}: {exc}"
        run.summary = run.error_message
        return

    transcript: list[str] = []
    last_action_note = ""
    consecutive_failures = 0

    for step in range(1, run.max_steps + 1):
        run.steps_taken = step
        db.commit()

        try:
            screenshot_bytes = page.screenshot()
        except Exception as exc:
            run.error_message = f"Could not capture a screenshot at step {step}: {exc}"
            run.summary = run.error_message
            return
        screenshot_path = _save_screenshot(run.id, step, screenshot_bytes)

        result = call_llm(
            db, run_id=None, agent=None, agent_role="simulation",
            system=_SYSTEM_PROMPT,
            user=_build_prompt(persona, run, page.url, step, transcript, last_action_note),
            tool=_STEP_TOOL, max_tokens=1024,
            image_base64=base64.b64encode(screenshot_bytes).decode(),
            user_id=run.user_id, org_id=run.org_id,
        )
        decision = result.tool_input or {}
        action = decision.get("action") or "stuck"
        reasoning = (decision.get("reasoning") or "").strip()
        transcript.append(f"Step {step} ({page.url}): {reasoning or '(no reasoning given)'} → {action}")

        if decision.get("issue_flagged"):
            simulation_service.create_finding(
                db, run,
                severity=decision.get("issue_severity") or "medium",
                title=decision.get("issue_title") or "Issue flagged during simulation",
                description=decision.get("issue_description") or reasoning
                             or "The persona flagged this screen without further detail.",
                reproduction_steps=list(transcript),
                screenshot_path=screenshot_path,
                step_number=step,
            )

        if action == "goal_reached":
            run.summary = f"Goal reached after {step} step(s). {reasoning}".strip()
            return
        if action == "stuck":
            run.summary = f"Persona reported being stuck after {step} step(s). {reasoning}".strip()
            return

        try:
            _execute(page, action, decision)
            last_action_note = ""
            consecutive_failures = 0
        except Exception as exc:
            consecutive_failures += 1
            last_action_note = (
                f"Your last action ({action} targeting \"{decision.get('target_text', '')}\") "
                f"failed: {exc}. Try a different visible label or a different approach."
            )
            transcript.append(f"  (action failed: {exc})")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                run.summary = (
                    f"Stopped after {consecutive_failures} consecutive failed actions — "
                    "the agent could not find a way to proceed."
                )
                simulation_service.create_finding(
                    db, run, severity="low",
                    title="Simulation agent could not proceed",
                    description=(
                        f"After {consecutive_failures} consecutive failed actions the agent gave "
                        f"up driving this persona further. This may be a real dead end for a user "
                        f"too, or a limit of this agent's element-grounding — a human should check "
                        f"the screenshot. Last error: {exc}"
                    ),
                    reproduction_steps=list(transcript),
                    screenshot_path=screenshot_path,
                    step_number=step,
                )
                return

    run.summary = (
        f"Reached the {run.max_steps}-step limit without the persona reporting the goal "
        "reached or being stuck."
    )


def _build_prompt(persona: Persona, run: SimulationRun, current_url: str, step: int,
                  transcript: list[str], last_action_note: str) -> str:
    history = "\n".join(transcript[-MAX_HISTORY_IN_PROMPT:]) or "(none yet — this is the first step)"
    note = f"\n\nNOTE: {last_action_note}" if last_action_note else ""
    return (
        f"Persona: {persona.name}\n"
        f"Persona goal/behavior: {persona.description}\n\n"
        f"Current URL: {current_url}\n"
        f"Step {step} of {run.max_steps}.\n\n"
        f"Recent history:\n{history}{note}\n\n"
        "Look at the attached screenshot of the current page. As this persona, decide the "
        "single next action. If the persona's goal is already complete, use action="
        "goal_reached. If nothing on screen lets the persona proceed, use action=stuck."
    )


def _execute(page, action: str, decision: dict) -> None:
    target_text = (decision.get("target_text") or "").strip()
    value = decision.get("value") or ""

    if action == "click":
        _locate(page, target_text).click(timeout=ACTION_TIMEOUT_MS)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=ACTION_TIMEOUT_MS)
        except Exception:
            pass  # a click that doesn't navigate (opens a menu, etc.) is not a failure
    elif action == "type":
        locator = _locate(page, target_text)
        locator.fill(value, timeout=ACTION_TIMEOUT_MS)
        if decision.get("submit_after_type"):
            locator.press("Enter")
    elif action == "navigate":
        if not value:
            raise ValueError("navigate action given with no value/URL")
        page.goto(value, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    elif action == "scroll":
        page.mouse.wheel(0, 900)
    else:
        raise ValueError(f"Unknown action '{action}'")


def _locate(page, text: str):
    """Try a handful of accessible-name-based locator strategies, in the order
    a real user's mental model would rank them, and return the first that
    resolves to at least one visible element. See module docstring for why
    this is text-based rather than DOM-selector-based."""
    if not text:
        raise ValueError("No target_text given for this action")

    strategies = (
        lambda: page.get_by_role("button", name=text, exact=False),
        lambda: page.get_by_role("link", name=text, exact=False),
        lambda: page.get_by_label(text, exact=False),
        lambda: page.get_by_placeholder(text, exact=False),
        lambda: page.get_by_role("textbox", name=text, exact=False),
        lambda: page.get_by_text(text, exact=False),
    )
    for strategy in strategies:
        try:
            locator = strategy()
            if locator.count() > 0:
                return locator.first
        except Exception:
            continue
    raise ValueError(f"Could not find any visible element matching \"{text}\"")


def _screenshot_dir(run_id) -> Path:
    base = Path(settings.simulation_screenshot_dir)
    if not base.is_absolute():
        # Backend package root — two levels up from app/agents/.
        base = Path(__file__).resolve().parent.parent.parent / base
    directory = base / str(run_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _save_screenshot(run_id, step: int, data: bytes) -> str:
    path = _screenshot_dir(run_id) / f"step_{step:02d}.png"
    path.write_bytes(data)
    return str(path)
