"""Add Customer and Party models with foreign keys

Revision ID: add_customer_party_models
Revises: d7a0bce5af11
Create Date: 2026-02-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_customer_party_models'
down_revision = 'd7a0bce5af11'
branch_labels = None
depends_on = None


def upgrade():
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(120), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('email', sa.String(120), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(120), nullable=True),
        sa.Column('state', sa.String(120), nullable=True),
        sa.Column('country', sa.String(120), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create parties table
    op.create_table(
        'parties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(120), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('email', sa.String(120), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(120), nullable=True),
        sa.Column('state', sa.String(120), nullable=True),
        sa.Column('country', sa.String(120), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Add customer_id to NFA table
    op.add_column('nfa', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'nfa', 'customers', ['customer_id'], ['id'], ondelete='SET NULL')

    # Add customer_id to cost_contracts table
    op.add_column('cost_contracts', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'cost_contracts', 'customers', ['customer_id'], ['id'], ondelete='SET NULL')

    # Add customer_id to revenue_contracts table
    op.add_column('revenue_contracts', sa.Column('customer_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'revenue_contracts', 'customers', ['customer_id'], ['id'], ondelete='SET NULL')

    # Add party_id to agreements table
    op.add_column('agreements', sa.Column('party_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'agreements', 'parties', ['party_id'], ['id'], ondelete='SET NULL')

    # Add party_id to statutory_documents table
    op.add_column('statutory_documents', sa.Column('party_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'statutory_documents', 'parties', ['party_id'], ['id'], ondelete='SET NULL')


def downgrade():
    # Drop foreign keys
    op.drop_constraint(None, 'statutory_documents', type_='foreignkey')
    op.drop_constraint(None, 'agreements', type_='foreignkey')
    op.drop_constraint(None, 'revenue_contracts', type_='foreignkey')
    op.drop_constraint(None, 'cost_contracts', type_='foreignkey')
    op.drop_constraint(None, 'nfa', type_='foreignkey')

    # Drop columns
    op.drop_column('statutory_documents', 'party_id')
    op.drop_column('agreements', 'party_id')
    op.drop_column('revenue_contracts', 'customer_id')
    op.drop_column('cost_contracts', 'customer_id')
    op.drop_column('nfa', 'customer_id')

    # Drop tables
    op.drop_table('parties')
    op.drop_table('customers')
