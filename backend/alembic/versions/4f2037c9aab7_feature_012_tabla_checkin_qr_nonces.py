"""HU-03: tabla checkin_qr_nonces (012-checkin-qr-dinamico)

Revision ID: 4f2037c9aab7
Revises: 27f9ec997e70
Create Date: 2026-07-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f2037c9aab7'
down_revision = '27f9ec997e70'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('checkin_qr_nonces',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device_id', sa.String(length=100), nullable=False),
    sa.Column('nonce', sa.String(length=64), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expira_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usado_en', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_checkin_qr_nonces_device_id'), 'checkin_qr_nonces', ['device_id'], unique=False)
    op.create_index(op.f('ix_checkin_qr_nonces_id'), 'checkin_qr_nonces', ['id'], unique=False)
    op.create_index(op.f('ix_checkin_qr_nonces_nonce'), 'checkin_qr_nonces', ['nonce'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_checkin_qr_nonces_nonce'), table_name='checkin_qr_nonces')
    op.drop_index(op.f('ix_checkin_qr_nonces_id'), table_name='checkin_qr_nonces')
    op.drop_index(op.f('ix_checkin_qr_nonces_device_id'), table_name='checkin_qr_nonces')
    op.drop_table('checkin_qr_nonces')
