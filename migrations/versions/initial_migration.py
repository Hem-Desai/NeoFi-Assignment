"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-05-20

"""
from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('username', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), default=False),
        sa.Column('recurrence_pattern', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('current_version', sa.Integer(), default=1),
    )
    
    # Create event_permissions table
    op.create_table(
        'event_permissions',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('event_id', sa.String(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create event_versions table
    op.create_table(
        'event_versions',
        sa.Column('id', sa.String(), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('event_id', sa.String(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), default=False),
        sa.Column('recurrence_pattern', sa.JSON(), nullable=True),
        sa.Column('changed_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('change_comment', sa.Text(), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_events_start_time', 'events', ['start_time'])
    op.create_index('ix_events_end_time', 'events', ['end_time'])
    op.create_index('ix_event_permissions_event_id_user_id', 'event_permissions', ['event_id', 'user_id'], unique=True)
    op.create_index('ix_event_versions_event_id_version_number', 'event_versions', ['event_id', 'version_number'], unique=True)


def downgrade():
    op.drop_table('event_versions')
    op.drop_table('event_permissions')
    op.drop_table('events')
    op.drop_table('users')
