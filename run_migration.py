#!/usr/bin/env python
"""Script to run database migrations"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

app = create_app()
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    with app.app_context():
        print("Running database migrations...")
        manager.run()
