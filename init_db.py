#!/usr/bin/env python3
"""Initialize the database with tables"""

from database import create_tables

if __name__ == "__main__":
    print("Creating database tables...")
    create_tables()
    print("Database tables created successfully!")