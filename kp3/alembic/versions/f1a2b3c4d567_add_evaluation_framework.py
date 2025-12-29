"""add evaluation framework tables

Revision ID: f1a2b3c4d567
Revises: d0e1f2a3b456
Create Date: 2025-12-29

Adds tables for agent evaluation:
- eval_test_cases: Reusable test case definitions
- eval_runs: Evaluation run records
- eval_results: Individual test results with scores
- eval_score_dimensions: Scoring criteria definitions
"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d567"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add evaluation framework tables."""
    
    # eval_test_cases - reusable test case definitions
    op.create_table(
        "eval_test_cases",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        # Identity
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        # Input state
        sa.Column("memory_state", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("prior_messages", sa.dialects.postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("input_message", sa.Text(), nullable=False),
        # Expected behavior
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        sa.Column("eval_criteria", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("gold_response", sa.Text(), nullable=True),
        # Metadata
        sa.Column("difficulty", sa.String(32), nullable=True),
        sa.Column("tags", sa.dialects.postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_eval_test_cases_category", "eval_test_cases", ["category"])
    op.create_index("idx_eval_test_cases_tags", "eval_test_cases", ["tags"], postgresql_using="gin")

    # eval_runs - evaluation run records
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        # What we're testing
        sa.Column("system_prompt_ref", sa.Text(), nullable=True),
        sa.Column("system_prompt_text", sa.Text(), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("config", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("test_case_filter", sa.dialects.postgresql.JSONB(), nullable=True),
        # Execution state
        sa.Column("status", sa.String(32), nullable=False, default="pending"),
        sa.Column("total_cases", sa.Integer(), nullable=True),
        sa.Column("completed_cases", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_cases", sa.Integer(), nullable=False, default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Aggregate scores
        sa.Column("aggregate_scores", sa.dialects.postgresql.JSONB(), nullable=True),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_eval_runs_status", "eval_runs", ["status"])
    op.create_index("idx_eval_runs_created", "eval_runs", ["created_at"])

    # eval_results - individual test results
    op.create_table(
        "eval_results",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("test_case_id", sa.UUID(), nullable=False),
        # What happened
        sa.Column("raw_output", sa.Text(), nullable=False),
        sa.Column("tool_calls", sa.dialects.postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("thinking", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        # Scores
        sa.Column("auto_scores", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("human_scores", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("human_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=True),
        # Embedding for clustering
        sa.Column("output_embedding", Vector(1024), nullable=True),
        # Metadata
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["eval_runs.id"]),
        sa.ForeignKeyConstraint(["test_case_id"], ["eval_test_cases.id"]),
    )
    op.create_index("idx_eval_results_run", "eval_results", ["run_id"])
    op.create_index("idx_eval_results_test_case", "eval_results", ["test_case_id"])
    op.create_index("idx_eval_results_composite_score", "eval_results", ["composite_score"])

    # eval_score_dimensions - scoring criteria definitions
    op.create_table(
        "eval_score_dimensions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("score_type", sa.String(32), nullable=False, default="binary"),
        sa.Column("rubric", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_eval_score_dimensions_category", "eval_score_dimensions", ["category"])


def downgrade() -> None:
    """Remove evaluation framework tables."""
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("eval_test_cases")
    op.drop_table("eval_score_dimensions")
