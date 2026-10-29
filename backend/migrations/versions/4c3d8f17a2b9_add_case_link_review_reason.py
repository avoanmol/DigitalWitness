"""record a reason for human case-link decisions

Revision ID: 4c3d8f17a2b9
Revises: 9b7a4f21d6c3
Create Date: 2026-10-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c3d8f17a2b9"
down_revision: Union[str, Sequence[str], None] = "9b7a4f21d6c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case_links", sa.Column("review_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("case_links", "review_reason")
