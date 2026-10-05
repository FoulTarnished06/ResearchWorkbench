"""
scripts/reset_db.py - AI Research Workbench Database Reset Utility

Usage:
    # Soft Reset (Clears research runs, cached literature, sentences, response cache, PDF sessions; preserves users & API keys):
    python scripts/reset_db.py

    # Hard Factory Reset (Wipes EVERYTHING: drops all tables including users & API keys, recreates pristine schema):
    python scripts/reset_db.py --hard

    # Non-interactive mode (for automation/CI):
    python scripts/reset_db.py --yes
    python scripts/reset_db.py --hard --yes
"""

import os
import sys
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import reset_database, get_db_connection, get_cache_stats, IS_POSTGRES, DB_PATH

def main():
    parser = argparse.ArgumentParser(
        description="Reset the AI Research Workbench database (SQLite or Cloud PostgreSQL)."
    )
    parser.add_argument(
        "--hard",
        action="store_true",
        help="Complete factory reset: drops and recreates all tables including users and encrypted API key vaults."
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt and proceed immediately."
    )

    args = parser.parse_args()

    engine_type = "Cloud PostgreSQL" if IS_POSTGRES else f"Local SQLite ({DB_PATH})"
    print("=" * 60)
    print("AI RESEARCH WORKBENCH - DATABASE RESET TOOL")
    print("=" * 60)
    print(f"Target Database : {engine_type}")
    print(f"Reset Mode      : {'HARD FACTORY RESET (Wipes all tables & users)' if args.hard else 'SOFT RESET (Clears runs & cache, preserves users)'}")
    print("-" * 60)

    # Show current stats
    try:
        stats = get_cache_stats()
        print("Current Record Counts:")
        for k, v in stats.items():
            print(f"  - {k.replace('_', ' ').title()}: {v}")
    except Exception as e:
        print(f"  (Could not read stats: {e})")

    print("-" * 60)

    if not args.yes:
        warning_msg = (
            "WARNING: This will permanently DROP ALL TABLES and recreate a clean empty database!"
            if args.hard else
            "This will clear all pipeline research runs, cached papers, sentences, and document workspaces."
        )
        print(warning_msg)
        try:
            confirm = input("Are you sure you want to proceed? [y/N]: ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(0)

        if confirm not in ("y", "yes"):
            print("Reset cancelled.")
            sys.exit(0)

    print("\nExecuting database reset...")
    try:
        result = reset_database(hard=args.hard)
        print(f"✅ Reset Successful! Status: {result.get('status')} | Mode: {result.get('mode')}")

        # Verify empty state
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM pipeline_runs")
        remaining_runs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM scraped_papers")
        remaining_papers = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users")
        remaining_users = cur.fetchone()[0]
        conn.close()

        print("\nVerification:")
        print(f"  - Pipeline Runs Remaining : {remaining_runs}")
        print(f"  - Scraped Papers Remaining : {remaining_papers}")
        print(f"  - Registered Users Remaining: {remaining_users}")
        print("\nDatabase is now clean and ready for fresh research runs.")
    except Exception as ex:
        print(f"❌ Error during database reset: {ex}")
        sys.exit(1)

if __name__ == "__main__":
    main()
