# -*- coding: utf-8 -*-
"""
Tests for stargazing_analyzer.cli module.

Uses argparse directly to test argument parsing and helper functions.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from stargazing_analyzer.cli import _bbox_from_center, _deg_per_km, create_parser


class TestDegPerKm:
    """Test _deg_per_km helper."""

    def test_at_equator(self):
        lat_deg, lon_deg = _deg_per_km(0.0)
        assert lat_deg == pytest.approx(1.0 / 111.0)
        assert lon_deg > 0

    def test_at_pole(self):
        lat_deg, lon_deg = _deg_per_km(89.0)
        assert lat_deg == pytest.approx(1.0 / 111.0)
        # lon_deg at pole should be larger due to cos scaling
        assert lon_deg > 1.0 / 111.0

    def test_negative_latitude(self):
        lat_deg, lon_deg = _deg_per_km(-30.0)
        assert lat_deg == pytest.approx(1.0 / 111.0)
        assert lon_deg > 0


class TestBboxFromCenter:
    """Test _bbox_from_center helper."""

    def test_zero_radius(self):
        south, west, north, east = _bbox_from_center(40.0, 116.0, 0)
        assert south == north == 40.0
        assert west == east == 116.0

    def test_positive_radius(self):
        south, west, north, east = _bbox_from_center(40.0, 116.0, 100)
        assert south < 40.0 < north
        assert west < 116.0 < east

    def test_symmetric(self):
        south, west, north, east = _bbox_from_center(40.0, 116.0, 50)
        assert (north - 40.0) == pytest.approx(40.0 - south)
        assert (east - 116.0) == pytest.approx(116.0 - west, rel=0.01)


class TestCreateParser:
    """Test create_parser argument parsing."""

    def test_center_args(self):
        parser = create_parser()
        args = parser.parse_args(["--center", "40.0", "116.0", "50.0"])
        assert args.center == [40.0, 116.0, 50.0]
        assert args.bbox is None
        assert args.max_locations == 30
        assert args.network_type == "drive"
        assert args.no_light_pollution is False
        assert args.no_road_connectivity is False
        assert args.top_n == 0

    def test_bbox_args(self):
        parser = create_parser()
        args = parser.parse_args(["--bbox", "39.0", "115.0", "41.0", "117.0"])
        assert args.bbox == [39.0, 115.0, 41.0, 117.0]
        assert args.center is None

    def test_custom_max_locations(self):
        parser = create_parser()
        args = parser.parse_args(["--center", "40.0", "116.0", "10.0", "--max-locations", "5"])
        assert args.max_locations == 5

    def test_flags(self):
        parser = create_parser()
        args = parser.parse_args(
            ["--center", "40.0", "116.0", "10.0", "--no-light-pollution", "--no-road-connectivity"]
        )
        assert args.no_light_pollution is True
        assert args.no_road_connectivity is True

    def test_verbose_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--center", "40.0", "116.0", "10.0", "--verbose"])
        assert args.verbose is True

    def test_output(self):
        parser = create_parser()
        args = parser.parse_args(["--center", "40.0", "116.0", "10.0", "--output", "results.json"])
        assert args.output == "results.json"

    def test_db_config(self):
        parser = create_parser()
        args = parser.parse_args(["--center", "40.0", "116.0", "10.0", "--db-config", "/path/to/config.json"])
        assert args.db_config == "/path/to/config.json"

    def test_top_n(self):
        parser = create_parser()
        args = parser.parse_args(["--center", "40.0", "116.0", "10.0", "--top-n", "3"])
        assert args.top_n == 3

    def test_mutually_exclusive_center_or_bbox(self):
        """--center and --bbox are mutually exclusive."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--center", "40.0", "116.0", "10.0", "--bbox", "1", "2", "3", "4"])

    def test_missing_required(self):
        """One of --center or --bbox is required."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_road_distance_args(self):
        parser = create_parser()
        args = parser.parse_args(
            ["--center", "40.0", "116.0", "10.0", "--min-road-distance", "0.1", "--max-road-distance", "0.5"]
        )
        assert args.min_road_distance == 0.1
        assert args.max_road_distance == 0.5


class TestMainFunction:
    """Test the CLI main() entry point."""

    @patch("stargazing_analyzer.cli.analyze_area")
    @patch("stargazing_analyzer.cli.create_parser")
    def test_main_with_center(self, mock_create_parser, mock_analyze_area):
        """main() with --center should compute bbox and call analyze_area."""
        from stargazing_analyzer.cli import main

        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(
            center=[40.0, 116.0, 50.0],
            bbox=None,
            max_locations=30,
            network_type="drive",
            no_light_pollution=False,
            no_road_connectivity=False,
            min_road_distance=None,
            max_road_distance=None,
            db_config=None,
            output=None,
            top_n=0,
            verbose=False,
        )
        mock_create_parser.return_value = mock_parser
        mock_analyze_area.return_value = []

        main()

        mock_analyze_area.assert_called_once()
        call_kwargs = mock_analyze_area.call_args.kwargs
        # bbox should be calculated from center
        assert len(call_kwargs["bbox"]) == 4
        assert call_kwargs["include_light_pollution"] is True
        assert call_kwargs["include_road_connectivity"] is True

    @patch("stargazing_analyzer.cli.analyze_area")
    @patch("stargazing_analyzer.cli.create_parser")
    def test_main_with_bbox(self, mock_create_parser, mock_analyze_area):
        """main() with --bbox should pass bbox directly."""
        from stargazing_analyzer.cli import main

        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(
            center=None,
            bbox=[39.0, 115.0, 41.0, 117.0],
            max_locations=30,
            network_type="drive",
            no_light_pollution=False,
            no_road_connectivity=False,
            min_road_distance=None,
            max_road_distance=None,
            db_config=None,
            output=None,
            top_n=0,
            verbose=False,
        )
        mock_create_parser.return_value = mock_parser
        mock_analyze_area.return_value = []

        main()

        mock_analyze_area.assert_called_once()
        bbox = mock_analyze_area.call_args.kwargs["bbox"]
        assert bbox == (39.0, 115.0, 41.0, 117.0)

    @patch("stargazing_analyzer.cli.init_stargazing_analyzer")
    @patch("stargazing_analyzer.cli.analyze_area")
    @patch("stargazing_analyzer.cli.create_parser")
    def test_main_with_db_config(self, mock_create_parser, mock_analyze_area, mock_init):
        """main() with --db-config should call init_stargazing_analyzer."""
        from pathlib import Path

        from stargazing_analyzer.cli import main

        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(
            center=[40.0, 116.0, 50.0],
            bbox=None,
            max_locations=30,
            network_type="drive",
            no_light_pollution=True,
            no_road_connectivity=True,
            min_road_distance=None,
            max_road_distance=None,
            db_config="/path/to/db.json",
            output=None,
            top_n=0,
            verbose=False,
        )
        mock_create_parser.return_value = mock_parser
        mock_analyze_area.return_value = []

        main()

        mock_init.assert_called_once_with(db_config_path=Path("/path/to/db.json"))
        call_kwargs = mock_analyze_area.call_args.kwargs
        assert call_kwargs["include_light_pollution"] is False
        assert call_kwargs["include_road_connectivity"] is False

    @patch("builtins.open")
    @patch("stargazing_analyzer.cli.analyze_area")
    @patch("stargazing_analyzer.cli.create_parser")
    def test_main_with_output(self, mock_create_parser, mock_analyze_area, mock_open):
        """main() with --output should write results to file."""
        from stargazing_analyzer.cli import main

        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(
            center=[40.0, 116.0, 50.0],
            bbox=None,
            max_locations=30,
            network_type="drive",
            no_light_pollution=True,
            no_road_connectivity=True,
            min_road_distance=None,
            max_road_distance=None,
            db_config=None,
            output="/tmp/results.json",
            top_n=0,
            verbose=False,
        )
        mock_create_parser.return_value = mock_parser
        mock_analyze_area.return_value = []

        main()

        mock_open.assert_called_once_with("/tmp/results.json", "w", encoding="utf-8")
