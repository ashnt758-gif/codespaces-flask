#!/usr/bin/env python3
"""Add missing customer_id and party_id columns to existing tables"""
import sqlite3

conn = sqlite3.connect('instance/kspl_app.db')
cursor = conn.cursor()

print("=" * 70)
print("ADDING MISSING FOREIGN KEY COLUMNS")
print("=" * 70)

# Tables that need customer_id
tables_customer = ['nfa', 'cost_contracts', 'revenue_contracts']

# Tables that need party_id
tables_party = ['agreements', 'statutory_documents']

# Add customer_id to tables
for table in tables_customer:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN customer_id INTEGER")
        print(f"✓ Added customer_id to {table}")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print(f"✓ customer_id already exists in {table}")
        else:
            print(f"✗ Error adding customer_id to {table}: {e}")

# Add party_id to tables
for table in tables_party:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN party_id INTEGER")
        print(f"✓ Added party_id to {table}")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print(f"✓ party_id already exists in {table}")
        else:
            print(f"✗ Error adding party_id to {table}: {e}")

conn.commit()

print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

# Verify columns were added
for table in tables_customer:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if 'customer_id' in columns:
        print(f"✓ {table} has customer_id column")
    else:
        print(f"✗ {table} MISSING customer_id column")

for table in tables_party:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if 'party_id' in columns:
        print(f"✓ {table} has party_id column")
    else:
        print(f"✗ {table} MISSING party_id column")

print("\n" + "=" * 70)
print("✓ MIGRATION COMPLETE")
print("=" * 70)

conn.close()
