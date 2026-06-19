"""initial production-oriented schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The application also keeps startup-safe lightweight migrations for easier
    # technical-test review with existing Docker volumes. This Alembic migration
    # documents the intended production schema.
    op.create_table(
        "route_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("route_code", sa.String(length=64), nullable=True),
        sa.Column("route_date", sa.String(length=32), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_volume", sa.Float(), nullable=False),
        sa.Column("total_containers", sa.Integer(), nullable=False),
        sa.Column("declared_total_volume", sa.Float(), nullable=True),
        sa.Column("declared_total_containers", sa.Integer(), nullable=True),
        sa.Column("original_distance_m", sa.Float(), nullable=True),
        sa.Column("optimized_distance_m", sa.Float(), nullable=True),
        sa.Column("original_duration_s", sa.Float(), nullable=True),
        sa.Column("optimized_duration_s", sa.Float(), nullable=True),
        sa.Column("metrics_source", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_route_jobs_route_code", "route_jobs", ["route_code"])
    op.create_index("ix_route_jobs_route_date", "route_jobs", ["route_date"])
    op.create_index("ix_route_jobs_status", "route_jobs", ["status"])

    op.create_table(
        "collection_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("route_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_order", sa.Integer(), nullable=False),
        sa.Column("optimized_order", sa.Integer(), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("bin_code", sa.String(length=64), nullable=True),
        sa.Column("service_day_code", sa.String(length=32), nullable=True),
        sa.Column("service_days", sa.String(length=128), nullable=True),
        sa.Column("frequency_code", sa.String(length=32), nullable=True),
        sa.Column("frequency_weeks", sa.Integer(), nullable=True),
        sa.Column("service_date", sa.String(length=32), nullable=True),
        sa.Column("time_spent", sa.String(length=32), nullable=True),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("containers", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("geocode_quality", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_collection_points_job_id", "collection_points", ["job_id"])
    op.create_index("ix_collection_points_original_order", "collection_points", ["original_order"])
    op.create_index("ix_collection_points_optimized_order", "collection_points", ["optimized_order"])

    op.create_table(
        "geocode_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("quality", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("query", name="uq_geocode_query"),
    )

    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("route_job_id", sa.Integer(), sa.ForeignKey("route_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_optimization_runs_route_job_id", "optimization_runs", ["route_job_id"])
    op.create_index("ix_optimization_runs_status", "optimization_runs", ["status"])


def downgrade() -> None:
    op.drop_table("optimization_runs")
    op.drop_table("geocode_cache")
    op.drop_table("collection_points")
    op.drop_table("route_jobs")
