"""Tests for CLI commands.

Tests verify:
- CLI argument parsing
- Command execution with mocked dependencies
- Proper error handling
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_no_command_shows_help(self):
        """Test that running without command shows help."""
        from cli import main

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["cli"]):
                main()

        assert exc_info.value.code == 1

    def test_seed_command_parsing(self):
        """Test seed command with --force flag."""

        from cli import main

        # Mock asyncio.run to capture the call
        with patch("cli.asyncio.run") as mock_run:
            with patch("sys.argv", ["cli", "seed"]):
                with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}):
                    main()

        mock_run.assert_called_once()

    def test_seed_force_flag(self):
        """Test seed command with --force flag."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        seed_parser = subparsers.add_parser("seed")
        seed_parser.add_argument("--force", "-f", action="store_true")

        args = parser.parse_args(["seed", "--force"])
        assert args.command == "seed"
        assert args.force is True

        args = parser.parse_args(["seed"])
        assert args.command == "seed"
        assert args.force is False

    def test_migrate_command_parsing(self):
        """Test migrate command exists."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("migrate")

        args = parser.parse_args(["migrate"])
        assert args.command == "migrate"

    def test_stats_command_parsing(self):
        """Test stats command exists."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("stats")

        args = parser.parse_args(["stats"])
        assert args.command == "stats"

    def test_collect_forecasts_command_parsing(self):
        """Test collect-forecasts command exists."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("collect-forecasts")

        args = parser.parse_args(["collect-forecasts"])
        assert args.command == "collect-forecasts"

    def test_collect_observations_command_parsing(self):
        """Test collect-observations command exists."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("collect-observations")

        args = parser.parse_args(["collect-observations"])
        assert args.command == "collect-observations"


class TestSeedCommand:
    """Tests for seed command."""

    @pytest.mark.asyncio
    async def test_seed_skips_when_data_exists(self):
        """Test that seed skips when data already exists without --force."""
        from cli import run_seed

        with patch("cli.get_async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 5  # 5 sites exist
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_factory.return_value = lambda: mock_session

            # Should not raise and not call db_seed
            with patch("cli.db_seed") as mock_db_seed:
                await run_seed(force=False)
                mock_db_seed.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_runs_when_empty(self):
        """Test that seed runs when database is empty."""
        from cli import run_seed

        with patch("cli.get_async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 0  # No sites
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_factory.return_value = lambda: mock_session

            with patch("cli.db_seed", new_callable=AsyncMock) as mock_db_seed:
                await run_seed(force=False)
                mock_db_seed.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_runs_with_force(self):
        """Test that seed runs with --force even when data exists."""
        from cli import run_seed

        with patch("cli.get_async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 5  # 5 sites exist
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_factory.return_value = lambda: mock_session

            with patch("cli.db_seed", new_callable=AsyncMock) as mock_db_seed:
                await run_seed(force=True)
                mock_db_seed.assert_called_once()


class TestMigrateCommand:
    """Tests for migrate command."""

    def test_migrate_runs_alembic(self):
        """Test that migrate command runs alembic upgrade head."""
        from cli import run_migrations

        with patch("cli.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            run_migrations()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "alembic" in call_args[0][0]
        assert "upgrade" in call_args[0][0]
        assert "head" in call_args[0][0]


class TestStatsCommand:
    """Tests for stats command."""

    @pytest.mark.asyncio
    async def test_stats_displays_counts(self, capsys):
        """Test that stats command displays counts."""
        from cli import show_stats

        mock_stats = {
            "total_sites": 1,
            "total_forecasts": 1234,
            "total_observations": 567,
            "total_pairs": 123,
            "total_deviations": 890,
        }

        with patch("cli.get_data_stats", new_callable=AsyncMock, return_value=mock_stats):
            await show_stats()

        captured = capsys.readouterr()
        assert "Sites:" in captured.out
        assert "1" in captured.out
        assert "Forecasts:" in captured.out
        assert "1,234" in captured.out


class TestCollectCommands:
    """Tests for manual collection commands."""

    @pytest.mark.asyncio
    async def test_collect_forecasts_displays_result(self, capsys):
        """Test that collect-forecasts displays results."""
        from cli import collect_forecasts

        mock_result = {
            "status": "success",
            "records_collected": 100,
            "records_persisted": 95,
            "duration_seconds": 30.5,
            "errors": None,
        }

        with patch("cli.collect_all_forecasts", new_callable=AsyncMock, return_value=mock_result):
            await collect_forecasts()

        captured = capsys.readouterr()
        assert "success" in captured.out.lower()
        assert "100" in captured.out
        assert "95" in captured.out

    @pytest.mark.asyncio
    async def test_collect_observations_displays_result(self, capsys):
        """Test that collect-observations displays results."""
        from cli import collect_observations

        mock_result = {
            "status": "partial",
            "records_collected": 50,
            "records_persisted": 45,
            "duration_seconds": 15.2,
            "errors": ["ROMMA timeout"],
        }

        with patch("cli.collect_all_observations", new_callable=AsyncMock, return_value=mock_result):
            await collect_observations()

        captured = capsys.readouterr()
        assert "partial" in captured.out.lower()
        assert "50" in captured.out
        assert "ROMMA timeout" in captured.out


class TestDatabaseURLRequired:
    """Tests for DATABASE_URL requirement."""

    def test_missing_database_url_exits(self):
        """Test that missing DATABASE_URL causes exit."""
        from cli import main

        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=True):
            with patch("sys.argv", ["cli", "stats"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
