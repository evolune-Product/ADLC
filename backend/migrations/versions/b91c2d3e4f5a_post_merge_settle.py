"""post-merge settle (no-op)

A merge revision has two down_revisions, so `alembic downgrade -1` run
directly against it is ambiguous — Alembic has no way to pick which parent
branch "one step back" means, and CI runs exactly `downgrade -1 && upgrade
head` on every push. Landing a bare merge revision as the pushed head would
break that check for the next person, not just in theory: reproduced locally
before adding this file. A trivial linear revision on top gives `-1` a single,
unambiguous parent again.

Revision ID: b91c2d3e4f5a
Revises: a20db26d2c93
Create Date: 2026-08-29 00:00:00.000000

"""
revision = "b91c2d3e4f5a"
down_revision = "a20db26d2c93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
