"""Organisation roles — engineering lead, billing manager, reviewer, auditor, client/guest

Widens org_members.role_check and org_invitations.role_check from four roles
(owner/admin/member/viewer) to the full catalogue in app/services/org_roles.py.

Purely additive: every existing row's role is still a valid value under the
new constraint, and owner/admin/member/viewer keep exactly the access they had
before. No data is touched — this only widens what the CHECK constraint permits.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-26
"""
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

# Mirrors app/services/org_roles.py — see that module for why each role exists.
# Duplicated here rather than imported because a migration must keep working
# even after the registry itself changes further down the line; a migration
# describes the schema at the moment it ran, not the schema as of whatever the
# registry says today.
ALL_ROLES = (
    "owner", "admin", "engineering_lead", "billing_manager",
    "member", "reviewer", "auditor", "viewer", "client_guest",
)
INVITABLE_ROLES = (
    "admin", "engineering_lead", "billing_manager",
    "member", "reviewer", "auditor", "viewer", "client_guest",
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
    # A row using a new role would violate the old, narrower constraint — any
    # org actually using engineering_lead/billing_manager/reviewer/auditor/
    # client_guest must reassign those members before downgrading. That is the
    # correct failure mode: silently reassigning someone's role during a
    # downgrade would be a worse surprise than a blocked migration.
    op.drop_constraint("org_invitations_role_check", "org_invitations", type_="check")
    op.create_check_constraint(
        "org_invitations_role_check", "org_invitations",
        "role IN ('admin','member','viewer')",
    )

    op.drop_constraint("org_members_role_check", "org_members", type_="check")
    op.create_check_constraint(
        "org_members_role_check", "org_members",
        "role IN ('owner','admin','member','viewer')",
    )
