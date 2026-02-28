"""Add is_big8 column and user_safe_ingredients table

Revision ID: b1234567890a
Revises: a049c090e314
Create Date: 2026-02-01 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1234567890a"
down_revision: str | Sequence[str] | None = "a049c090e314"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_big8 column to ingredients and create user_safe_ingredients table."""
    # Add is_big8 column to ingredients table
    op.add_column(
        "ingredients",
        sa.Column(
            "is_big8",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="True if ingredient is a Big 8 allergen",
        ),
    )

    # Create user_safe_ingredients table
    op.create_table(
        "user_safe_ingredients",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "ingredient_id"),
    )


def downgrade() -> None:
    """Remove is_big8 column and user_safe_ingredients table."""
    op.drop_table("user_safe_ingredients")
    op.drop_column("ingredients", "is_big8")
