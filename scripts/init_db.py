#!/usr/bin/env python3
"""
Initialize the Thai ALPR database.

Creates tables and optionally seeds with sample data.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import create_tables, get_engine


def init_database(database_url: str | None = None) -> None:
    """
    Initialize the database schema.
    
    Args:
        database_url: PostgreSQL connection string. 
                     If None, uses DATABASE_URL env var.
    """
    if database_url is None:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://alpr_user:alpr_password@localhost:5432/thai_alpr"
        )
    
    print(f"Connecting to database: {database_url}")
    
    try:
        engine = get_engine(database_url)
        
        print("Creating tables...")
        create_tables(engine)
        
        print("✅ Database initialization complete!")
        print("\nTables created:")
        print("  - vehicle_logs")
        
        print("\nYou can now start the ALPR backend service.")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Thai ALPR database")
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection string (default: from DATABASE_URL env var)",
        default=None,
    )
    
    args = parser.parse_args()
    init_database(args.database_url)