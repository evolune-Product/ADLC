"""
The organisation role catalogue.

Same registry pattern as `llm_providers` and `plugins`: a dict literal, not a
chain of if-statements, so a new role is an entry here rather than a change
scattered across every router that gates on `org_ctx.role`.

Why this exists at all
-----------------------
Before this file there were exactly four roles — owner, admin, member, viewer
— and every "who can manage this" check in the codebase reduced to two
literal patterns: `role == "viewer"` (blocks write access) and
`role not in ("owner", "admin")` (blocks admin actions). That is workable for
a two-person side project. It is not how a company is actually organised.

A real engineering organisation buying this product has at least four kinds of
person who are none of "the owner", "an admin", "a generic member" or "a
read-only viewer":

  * someone who owns the model-provider keys and the payment method, and
    should never need to touch an agent's config to do their job
  * a tech lead who administers agents, pods, skills and policies, and should
    not be the person who can change the org's billing plan
  * a reviewer whose entire function is the approval gate — the platform's
    core differentiator only means something if that gate has a named,
    accountable owner distinct from "whoever happened to click approve"
  * a compliance or security reviewer who needs to see everything (audit log,
    policies, spend) and must be structurally unable to change anything, which
    a role that merely *chooses* not to click "edit" does not guarantee
  * an external party — a client, a contractor's client, an auditor from
    outside the company — who should see status and talk in one channel and
    nothing else

Every one of those is a role a company actually has. This registry names them.

Two independent axes, not one rank
-----------------------------------
The old system was a single ordering (viewer < member < admin < owner) and
that is structurally wrong for a billing manager or an engineering lead: rank
alone cannot express "full authority over billing, none over agents" without
either granting them blanket admin (wrong — a billing manager should not be
able to touch skills) or blanket member (wrong — they need to manage billing,
which a member cannot).

So a role here carries two things instead of one number:

    can_write   whether this role may create or change *anything* at all.
                False is the entire definition of a read-only role — no
                write-gated endpoint anywhere honours a role that isn't in
                `WRITE_ROLES`, not "usually doesn't", structurally can't.

    domains     which admin-only *domains* this role administers. A domain is
                a named area of configuration — "engineering" (skills, agents,
                pods, projects, connections, policies), "billing" (plans,
                payment methods, model-provider keys) — and each admin-gated
                router declares which domain it belongs to and checks
                `is_domain_admin(org_ctx, "that domain")`. `"*"` means every
                domain, which is what owner and admin carry and nothing else
                does — turning a specialist into a de facto full admin is
                exactly the mistake a specialist role exists to avoid.

Backward compatibility
-----------------------
`owner`, `admin`, `member` and `viewer` behave **exactly** as before — same
write access, same domain reach. Every new role is additive. An org that never
assigns anyone a new role sees no behavioural change whatsoever.
"""
from __future__ import annotations

ALL_DOMAINS = "*"

# ── Category, purely for grouping the invite dropdown — has no bearing on access. ──
LEADERSHIP = "leadership"
ENGINEERING = "engineering"
FINANCE = "finance"
OVERSIGHT = "oversight"
EXTERNAL = "external"

ROLES: list[dict] = [
    {
        "key": "owner",
        "label": "Owner",
        "description": "Full control, including billing, org deletion and ownership transfer. "
                       "Exactly one per organisation.",
        "category": LEADERSHIP,
        "can_write": True,
        "domains": ALL_DOMAINS,
        "invitable": False,   # ownership moves by transfer, never by invite
    },
    {
        "key": "admin",
        "label": "Admin",
        "description": "Full control except deleting the organisation or transferring ownership. "
                       "The generalist trusted role — use a specialist role below when the "
                       "person's job is actually narrower than \"everything\".",
        "category": LEADERSHIP,
        "can_write": True,
        "domains": ALL_DOMAINS,
        "invitable": True,
    },
    {
        "key": "engineering_lead",
        "label": "Engineering lead",
        "description": "Administers skills, agents, pods, projects, connections and approval "
                       "policies. Cannot see or change billing, payment methods, or invite "
                       "other members — a tech lead's authority over the pipeline, not the "
                       "company account.",
        "category": ENGINEERING,
        "can_write": True,
        "domains": {"engineering"},
        "invitable": True,
    },
    {
        "key": "billing_manager",
        "label": "Billing manager",
        "description": "Manages the subscription, payment methods and model-provider API keys. "
                       "Cannot touch agents, skills, pods or policies — spending authority, "
                       "not engineering authority. The role for finance or ops, who should "
                       "never need write access to a codebase to pay an invoice.",
        "category": FINANCE,
        "can_write": True,
        "domains": {"billing"},
        "invitable": True,
    },
    {
        "key": "member",
        "label": "Member",
        "description": "Day-to-day work: trigger runs, use the workspace, review and approve "
                       "pull requests through the gate. Cannot change org-wide configuration.",
        "category": ENGINEERING,
        "can_write": True,
        "domains": set(),
        "invitable": True,
    },
    {
        "key": "reviewer",
        "label": "Reviewer",
        "description": "The same day-to-day access as a member, named for the person whose job "
                       "is specifically the approval gate — QA lead, release manager. Exists "
                       "so an audit trail can say who was accountable for approving, not just "
                       "who happened to click the button.",
        "category": ENGINEERING,
        "can_write": True,
        "domains": set(),
        "invitable": True,
    },
    {
        "key": "auditor",
        "label": "Auditor",
        "description": "Read-only, but sees more than a viewer: the audit log, compliance "
                       "posture, approval policies and billing history. For an internal "
                       "compliance officer or an external auditor who must be able to answer "
                       "\"what happened and who approved it\" and be structurally unable to "
                       "change anything while doing so.",
        "category": OVERSIGHT,
        "can_write": False,
        "domains": set(),
        "invitable": True,
    },
    {
        "key": "viewer",
        "label": "Viewer",
        "description": "Read-only access to the ordinary product surface — runs, projects, "
                       "the workspace. No visibility into billing or the audit log beyond "
                       "what any member sees.",
        "category": OVERSIGHT,
        "can_write": False,
        "domains": set(),
        "invitable": True,
    },
    {
        "key": "client_guest",
        "label": "Client / guest",
        "description": "For someone outside the company — a client, a contractor's own client, "
                       "a stakeholder who needs to watch progress and talk in the workspace "
                       "without seeing internal cost, billing or audit data. The role that "
                       "replaces \"add them to a WhatsApp group so they can see updates\".",
        "category": EXTERNAL,
        "can_write": False,
        "domains": set(),
        "invitable": True,
    },
    {
        "key": "department_head",
        "label": "Department head",
        "description": "Leads one department — Engineering, Sales, Support, whatever the org "
                       "has created. Day-to-day write access like a member; department- and "
                       "team-scoped authority (create teams, assign work, name team leads) is "
                       "checked separately with `is_department_head`, not through `domains` — "
                       "that authority is scoped to the specific department they head, not to "
                       "an org-wide configuration area the way `domains` expresses.",
        "category": ENGINEERING,
        "can_write": True,
        "domains": set(),
        "invitable": True,
    },
    {
        "key": "team_lead",
        "label": "Team lead",
        "description": "Leads one team inside a department. Day-to-day write access like a "
                       "member; team-scoped authority (assign work within the team) is checked "
                       "separately with `is_team_lead`.",
        "category": ENGINEERING,
        "can_write": True,
        "domains": set(),
        "invitable": True,
    },
    {
        "key": "agent",
        "label": "Agent",
        "description": "An AI agent acting as a first-class organisational actor outside the "
                       "SDLC pipeline's existing Agent/Pod machinery — e.g. an agent that can be "
                       "assigned generic Work items directly. Deliberately excluded from "
                       "`INVITABLE_ROLES`: an agent is never invited by email the way a human "
                       "is, it is granted this role programmatically when it is registered as an "
                       "org member.",
        "category": ENGINEERING,
        "can_write": True,
        "domains": set(),
        "invitable": False,
    },
]

BY_KEY: dict[str, dict] = {r["key"]: r for r in ROLES}

# ── Derived sets, computed once rather than duplicated at each call site. ──────

#: Roles allowed to write anything at all. Every `role == "viewer"`-style gate
#: in the codebase became `role not in WRITE_ROLES` when this registry landed;
#: a role absent from this set is read-only *everywhere*, not just wherever a
#: developer remembered to check.
WRITE_ROLES: frozenset[str] = frozenset(r["key"] for r in ROLES if r["can_write"])

#: The set every `role not in ("owner", "admin")` full-admin gate becomes.
#: Unchanged from before this registry existed — full admin is still exactly
#: owner and admin, on purpose. A specialist role earning blanket admin
#: defeats the reason the specialist role exists.
FULL_ADMIN_ROLES: frozenset[str] = frozenset(
    r["key"] for r in ROLES if r["domains"] == ALL_DOMAINS
)

#: Roles that may be granted through an invitation. Ownership moves by
#: transfer only — inviting someone straight in as owner would let a single
#: admin mint a second one, which is not how ownership transfer is supposed
#: to require the *current* owner's action.
INVITABLE_ROLES: frozenset[str] = frozenset(r["key"] for r in ROLES if r["invitable"])

#: The CHECK constraint's value set. Kept in sync with ROLES by construction —
#: there is exactly one list of role keys in this codebase, not one in Python
#: and a second copy in a migration that can drift from it.
ALL_KEYS: tuple[str, ...] = tuple(r["key"] for r in ROLES)


def get(role_key: str) -> dict | None:
    return BY_KEY.get(role_key)


def can_write(role: str | None) -> bool:
    """Whether this role may mutate anything. `None` (no org context — a
    personal workspace) is always writable; org membership is what can
    restrict, never its absence."""
    return role is None or role in WRITE_ROLES


def is_domain_admin(role: str | None, domain: str) -> bool:
    """
    Whether this role administers `domain` — "engineering", "billing", or
    whatever a router declares. `None` (personal workspace, no org) always
    passes: a solo user administers everything they own by definition.
    """
    if role is None:
        return True
    spec = BY_KEY.get(role)
    if not spec:
        return False
    doms = spec["domains"]
    return doms == ALL_DOMAINS or domain in doms


def catalog() -> list[dict]:
    """
    The role list as the invite/member UI needs it: label, description,
    category, and whether it can currently be invited. No access-control
    internals (`domains`, `can_write`) — those are enforcement details, not
    something to render as a checkbox grid in an invite form.
    """
    return [
        {"key": r["key"], "label": r["label"], "description": r["description"],
         "category": r["category"], "invitable": r["invitable"]}
        for r in ROLES
    ]
