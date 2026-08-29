"""Organization company-profile fields — industry, company_size, timezone, locale, description, logo

Widens the Organization row into a company profile: this is the SAME tenant
row that has always carried SSO, billing and membership, not a parallel
"Company" table — an org already *is* the company in this schema.

Purely additive: every column is nullable or carries a server_default, so
every existing organizations row is valid the instant this migration lands.

Revision ID: a1b2c3d4e5a1
Revises: a7b8c9d0e1f2
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5a1"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("industry", sa.String(length=100), nullable=True))
    op.add_column("organizations", sa.Column("company_size", sa.String(length=50), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "organizations",
        sa.Column("default_locale", sa.String(length=16), nullable=False, server_default="en-US"),
    )
    op.add_column("organizations", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("organizations", sa.Column("logo_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "logo_url")
    op.drop_column("organizations", "description")
    op.drop_column("organizations", "default_locale")
    op.drop_column("organizations", "timezone")
    op.drop_column("organizations", "company_size")
    op.drop_column("organizations", "industry")
