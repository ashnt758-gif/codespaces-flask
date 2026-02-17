#!/usr/bin/env python3
"""
Database initialization script for Customer and Party models
"""
import sys
sys.path.insert(0, '/c/Users/Nirmala computer/Downloads/kspl/kspl')

from app import app, db
from models import Customer, Party, NFA, CostContract, RevenueContract, Agreement, StatutoryDocument

def init_database():
    """Initialize database with Customer and Party models"""
    with app.app_context():
        print("Creating database tables...")
        
        # Create all tables
        db.create_all()
        
        print("✓ Database tables created successfully!")
        
        # Verify tables
        inspector_tables = db.inspect(db.engine).get_table_names()
        print(f"\nCreated tables: {', '.join(inspector_tables)}")
        
        # Check for new tables
        if 'customers' in inspector_tables:
            print("✓ Customers table created")
        if 'parties' in inspector_tables:
            print("✓ Parties table created")
        
        # Check for new columns
        nfa_columns = [col['name'] for col in db.inspect(db.engine).get_columns('nfa')]
        if 'customer_id' in nfa_columns:
            print("✓ customer_id column added to NFA table")
        
        cost_columns = [col['name'] for col in db.inspect(db.engine).get_columns('cost_contracts')]
        if 'customer_id' in cost_columns:
            print("✓ customer_id column added to CostContract table")
        
        revenue_columns = [col['name'] for col in db.inspect(db.engine).get_columns('revenue_contracts')]
        if 'customer_id' in revenue_columns:
            print("✓ customer_id column added to RevenueContract table")
        
        agr_columns = [col['name'] for col in db.inspect(db.engine).get_columns('agreements')]
        if 'party_id' in agr_columns:
            print("✓ party_id column added to Agreement table")
        
        stat_columns = [col['name'] for col in db.inspect(db.engine).get_columns('statutory_documents')]
        if 'party_id' in stat_columns:
            print("✓ party_id column added to StatutoryDocument table")
        
        print("\n✓ Database initialization complete!")

if __name__ == '__main__':
    init_database()
