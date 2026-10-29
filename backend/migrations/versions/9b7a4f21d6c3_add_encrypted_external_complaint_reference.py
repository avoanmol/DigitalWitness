"""add optional encrypted external complaint reference to cases

Revision ID: 9b7a4f21d6c3
Revises: 1ff831b04c78
Create Date: 2026-10-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b7a4f21d6c3"
down_revision: Union[str, Sequence[str], None] = "1ff831b04c78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("external_reference_ciphertext", sa.LargeBinary(), nullable=True))
    op.add_column("cases", sa.Column("external_reference_nonce", sa.LargeBinary(), nullable=True))
    op.add_column("cases", sa.Column("external_reference_channel", sa.String(length=32), nullable=True))
    op.add_column("cases", sa.Column("external_reference_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_cases_external_reference_channel",
        "cases",
        "external_reference_channel IS NULL OR external_reference_channel IN ('cybercrime_portal', 'local_police')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cases_external_reference_channel", "cases", type_="check")
    op.drop_column("cases", "external_reference_updated_at")
    op.drop_column("cases", "external_reference_channel")
    op.drop_column("cases", "external_reference_nonce")
    op.drop_column("cases", "external_reference_ciphertext")
