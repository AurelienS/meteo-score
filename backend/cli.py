#!/usr/bin/env python3
"""CLI for MétéoScore manual operations.

Usage:
    python -m cli seed          # Run seed (only if tables are empty)
    python -m cli seed --force  # Force seed even if data exists
    python -m cli migrate       # Run database migrations
    python -m cli stats         # Show database statistics
    python -m cli collect-forecasts   # Trigger forecast collection
    python -m cli collect-observations # Trigger observation collection
    python -m cli smoke-test    # Run smoke test of data collection pipeline
    python -m cli smoke-test --dry-run  # Test without persisting to database
    python -m cli smoke-test --verbose  # Show detailed output
    python -m cli smoke-test --site "Passy Plaine Joux"  # Test specific site

From Docker:
    docker-compose exec backend python -m cli seed
    docker-compose exec backend python -m cli stats
    docker-compose exec backend python -m cli smoke-test
"""

import argparse
import asyncio
import os
import sys

# Ensure we're in the backend directory context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_migrations() -> None:
    """Run alembic migrations."""
    from subprocess import CalledProcessError, run

    print("Running database migrations...")
    try:
        result = run(
            ["alembic", "upgrade", "head"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        print("Migrations completed successfully!")
    except CalledProcessError as e:
        print(f"Migration failed: {e.stderr}")
        sys.exit(1)


async def run_seed(force: bool = False) -> None:
    """Run database seed.

    Args:
        force: If True, run seed even if data exists.
    """
    from sqlalchemy import func, select

    from core.database import get_async_session_factory
    from core.models import Site

    async_session = get_async_session_factory()

    async with async_session() as db:
        # Check if data exists
        result = await db.execute(select(func.count()).select_from(Site))
        count = result.scalar()

        if count > 0 and not force:
            print(f"Database already has {count} site(s). Use --force to seed anyway.")
            return

        if count > 0 and force:
            print(f"Warning: Database has {count} site(s). Force seeding...")

    # Run the seed script
    from db.seed import run_seed as db_seed
    await db_seed()


async def show_stats() -> None:
    """Show database statistics."""
    from services.storage_service import get_data_stats

    print("=" * 50)
    print("MétéoScore Database Statistics")
    print("=" * 50)

    stats = await get_data_stats()

    print(f"  Sites:        {stats['total_sites']:,}")
    print(f"  Forecasts:    {stats['total_forecasts']:,}")
    print(f"  Observations: {stats['total_observations']:,}")
    print(f"  Pairs:        {stats['total_pairs']:,}")
    print(f"  Deviations:   {stats['total_deviations']:,}")
    print("=" * 50)


async def collect_forecasts() -> None:
    """Trigger manual forecast collection."""
    from scheduler.jobs import collect_all_forecasts

    print("Starting forecast collection...")
    try:
        result = await collect_all_forecasts()

        print(f"Status: {result['status']}")
        print(f"Records collected: {result['records_collected']}")
        print(f"Records persisted: {result['records_persisted']}")
        print(f"Duration: {result['duration_seconds']:.2f}s")

        if result.get('errors'):
            print("Errors:")
            for error in result['errors']:
                print(f"  - {error}")
    except Exception as e:
        print(f"Collection failed with error: {e}")
        sys.exit(1)


async def collect_observations() -> None:
    """Trigger manual observation collection."""
    from scheduler.jobs import collect_all_observations

    print("Starting observation collection...")
    try:
        result = await collect_all_observations()

        print(f"Status: {result['status']}")
        print(f"Records collected: {result['records_collected']}")
        print(f"Records persisted: {result['records_persisted']}")
        print(f"Duration: {result['duration_seconds']:.2f}s")

        if result.get('errors'):
            print("Errors:")
            for error in result['errors']:
                print(f"  - {error}")
    except Exception as e:
        print(f"Collection failed with error: {e}")
        sys.exit(1)


async def run_smoke_test_cmd(
    dry_run: bool = False,
    verbose: bool = False,
    site: str | None = None,
) -> None:
    """Run smoke test of data collection pipeline.

    Args:
        dry_run: If True, don't persist to database.
        verbose: If True, show detailed output.
        site: Optional site name to test.
    """
    from tests.smoke_test import (
        format_smoke_test_output,
        get_site_config_for_test,
        run_smoke_test,
    )

    print("Running smoke test...")

    # Get site config for display
    site_config = await get_site_config_for_test(site)
    if not site_config:
        if site:
            print(f"Error: Site '{site}' not found in database")
        else:
            print("Error: No sites configured in database. Run 'python -m cli seed' first.")
        sys.exit(1)

    site_name = site_config["name"]

    # Run the smoke test
    result = await run_smoke_test(
        dry_run=dry_run,
        verbose=verbose,
        site_name=site,
    )

    # Format and print output
    output = format_smoke_test_output(result, site_name, verbose)
    print(output)

    # Exit with appropriate code
    if result.status == "failed":
        sys.exit(1)
    elif result.status == "partial":
        sys.exit(2)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MétéoScore CLI for manual operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Seed command
    seed_parser = subparsers.add_parser("seed", help="Run database seed")
    seed_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force seed even if data exists",
    )

    # Migrate command
    subparsers.add_parser("migrate", help="Run database migrations")

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Collect commands
    subparsers.add_parser("collect-forecasts", help="Trigger forecast collection")
    subparsers.add_parser("collect-observations", help="Trigger observation collection")

    # Smoke test command
    smoke_parser = subparsers.add_parser(
        "smoke-test",
        help="Run smoke test of data collection pipeline",
    )
    smoke_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test collection without persisting to database",
    )
    smoke_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    smoke_parser.add_argument(
        "--site",
        type=str,
        help="Site name to test (default: first configured site)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Check DATABASE_URL is set
    if not os.environ.get("DATABASE_URL"):
        print("Error: DATABASE_URL environment variable is not set")
        sys.exit(1)

    if args.command == "migrate":
        run_migrations()
    elif args.command == "seed":
        asyncio.run(run_seed(force=args.force))
    elif args.command == "stats":
        asyncio.run(show_stats())
    elif args.command == "collect-forecasts":
        asyncio.run(collect_forecasts())
    elif args.command == "collect-observations":
        asyncio.run(collect_observations())
    elif args.command == "smoke-test":
        asyncio.run(run_smoke_test_cmd(
            dry_run=args.dry_run,
            verbose=args.verbose,
            site=args.site,
        ))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
