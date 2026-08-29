"""Company OS roles — department_head, team_lead, agent

Widens org_members.role_check (and org_invitations.role_check, minus 'agent'
which is not invitable — see app/services/org_roles.py) to the full Company OS
catalogue. Same purely-additive shape as f6a7b8c9d0e1: every existing row's
role is still valid, owner/admin/.../client_guest keep exactly the access
they had before.

Revision ID: b2c3d4e5a1b2
Revises: a1b2c3d4e5a1
Create Date: 2026-08-29
"""
from alembic import op

revision = "b2c3d4e5a1b2"
down_revision = "a1b2c3d4e5a1"
branch_labels = None
depends_on = None

# Mirrors app/services/org_roles.py ALL_KEYS / INVITABLE_ROLES at the moment
# this migration was written — duplicated rather than imported, same
# rationale as f6a7b8c9d0e1: a migration describes the schema as of when it
# ran, not as of whatever the registry says today.
ALL_ROLES = (
    "owner", "admin", "engineering_lead", "billing_manager",
    "member", "reviewer", "auditor", "viewer", "client_guest",
    "department_head", "team_lead", "agent",
)
INVITABLE_ROLES = (
    "admin", "engineering_lead", "billing_manager",
    "member", "reviewer", "auditor", "viewer", "client_guest",
    "department_head", "team_lead",
)


def upgrade() -> None:
    op.drop_constraint("org_members_role_check", "org_members", type_="check")
    op.create_check_constraint(
        "org_members_role_check", "org_members",
        "role IN (" + ",".join(f"'{r}'" for r in ALL_ROLES) + ")",
    )

    op.drop_constraint("org_invitations_role_check", "org_invitations", type_="check")
    op.create_check_constraint(
        "org_invitations_role_check", "org_invitations",
        "role IN (" + ",".join(f"'{r}'" for r in INVITABLE_ROLES) + ")",
    )


def downgrade() -> None:
    # Any org actually using department_head/team_lead/agent must reassign
    # those members before downgrading — same correct-failure-mode rationale
    # as f6a7b8c9d0e1's downgrade.
    op.drop_constraint("org_invitations_role_check", "org_invitations", type_="check")
    op.create_check_constraint(
        "org_invitations_role_check", "org_invitations",
        "role IN ('admin','engineering_lead','billing_manager','member','reviewer','auditor','viewer','client_guest')",
    )

    op.drop_constraint("org_members_role_check", "org_members", type_="check")
    op.create_check_constraint(
        "org_members_role_check", "org_members",
        "role IN ('owner','admin','engineering_lead','billing_manager','member','reviewer','auditor','viewer','client_guest')",
    )
