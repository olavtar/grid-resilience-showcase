# This project was developed with assistance from AI tools.

"""Unit tests for the Risk Engine scoring algorithm."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from grid_common.events import GridCell
from risk_engine.scoring import (
    age_score,
    compute_asset_risk,
    inspection_recency_score,
    nearest_grid_cell,
    vegetation_score,
    weather_exposure_score,
)
from risk_engine.settings import RiskEngineSettings


@pytest.fixture
def settings() -> RiskEngineSettings:
    return RiskEngineSettings()


@pytest.fixture
def grid_cells() -> list[GridCell]:
    return [
        GridCell(
            lat=36.06,
            lon=-79.50,
            t2m_k=270.0,
            u10m_mps=15.0,
            v10m_mps=10.0,
            tp_mm=12.0,
            cfrzr=True,
            crain=False,
            cicep=False,
            csnow=False,
        ),
        GridCell(
            lat=36.10,
            lon=-79.45,
            t2m_k=273.0,
            u10m_mps=5.0,
            v10m_mps=3.0,
            tp_mm=4.0,
            cfrzr=True,
            crain=False,
            cicep=False,
            csnow=False,
        ),
        GridCell(
            lat=36.08,
            lon=-79.48,
            t2m_k=275.0,
            u10m_mps=2.0,
            v10m_mps=1.0,
            tp_mm=1.0,
            cfrzr=False,
            crain=True,
            cicep=False,
            csnow=False,
        ),
    ]


class TestNearestGridCell:
    """Tests for grid cell proximity lookup."""

    def test_returns_closest_cell(self, grid_cells: list[GridCell]) -> None:
        """Nearest cell to (36.06, -79.50) is the first cell."""
        cell = nearest_grid_cell(36.06, -79.50, grid_cells)
        assert cell is not None
        assert cell.lat == 36.06

    def test_returns_none_for_empty_list(self) -> None:
        """Empty grid cell list returns None."""
        assert nearest_grid_cell(36.0, -79.0, []) is None

    def test_picks_second_cell_when_closer(self, grid_cells: list[GridCell]) -> None:
        """Point near second cell returns second cell."""
        cell = nearest_grid_cell(36.10, -79.44, grid_cells)
        assert cell is not None
        assert cell.lat == 36.10


class TestWeatherExposureScore:
    """Tests for the weather exposure sub-score."""

    def test_high_wind_and_ice_produces_high_score(
        self, grid_cells: list[GridCell], settings: RiskEngineSettings
    ) -> None:
        """Asset near the severe cell gets a high weather score."""
        score = weather_exposure_score(36.06, -79.50, False, grid_cells, settings)
        assert score > 0.4

    def test_end_of_line_multiplier_increases_score(
        self, grid_cells: list[GridCell], settings: RiskEngineSettings
    ) -> None:
        """End-of-line assets get 1.3x multiplier."""
        normal = weather_exposure_score(36.06, -79.50, False, grid_cells, settings)
        eol = weather_exposure_score(36.06, -79.50, True, grid_cells, settings)
        assert eol >= normal

    def test_calm_weather_produces_low_score(
        self, grid_cells: list[GridCell], settings: RiskEngineSettings
    ) -> None:
        """Asset near the mild cell gets a low weather score."""
        score = weather_exposure_score(36.08, -79.48, False, grid_cells, settings)
        assert score < 0.2

    def test_no_ice_when_no_freezing_rain(self, settings: RiskEngineSettings) -> None:
        """Precipitation without cfrzr flag produces no ice score."""
        cells = [
            GridCell(
                lat=36.0,
                lon=-79.0,
                t2m_k=280.0,
                u10m_mps=0.0,
                v10m_mps=0.0,
                tp_mm=20.0,
                cfrzr=False,
                crain=True,
                cicep=False,
                csnow=False,
            )
        ]
        score = weather_exposure_score(36.0, -79.0, False, cells, settings)
        assert score < 0.05

    def test_score_capped_at_one(self, settings: RiskEngineSettings) -> None:
        """Extreme conditions don't produce scores above 1.0."""
        cells = [
            GridCell(
                lat=36.0,
                lon=-79.0,
                t2m_k=260.0,
                u10m_mps=50.0,
                v10m_mps=50.0,
                tp_mm=100.0,
                cfrzr=True,
                crain=False,
                cicep=False,
                csnow=False,
            )
        ]
        score = weather_exposure_score(36.0, -79.0, True, cells, settings)
        assert score <= 1.0


class TestAgeScore:
    """Tests for the age-based risk sub-score."""

    def test_new_asset_low_score(self, settings: RiskEngineSettings) -> None:
        """Recently installed asset has low age score."""
        score = age_score(2020, 40, settings)
        assert score < 0.2

    def test_old_asset_high_score(self, settings: RiskEngineSettings) -> None:
        """Asset past its expected lifespan scores 1.0."""
        score = age_score(1970, 40, settings)
        assert score == 1.0

    def test_unknown_age_returns_moderate(self, settings: RiskEngineSettings) -> None:
        """Missing install year returns 0.5."""
        assert age_score(None, None, settings) == 0.5

    def test_half_life_asset(self, settings: RiskEngineSettings) -> None:
        """Asset at half its lifespan scores ~0.5."""
        current_year = 2026
        score = age_score(current_year - 20, 40, settings)
        assert 0.45 <= score <= 0.55


class TestVegetationScore:
    """Tests for the vegetation proximity sub-score."""

    def test_tight_clearance_high_score(self, settings: RiskEngineSettings) -> None:
        """1.5m clearance (near threshold) produces high score."""
        score = vegetation_score(1.5, settings)
        assert score > 0.4

    def test_wide_clearance_low_score(self, settings: RiskEngineSettings) -> None:
        """5m clearance produces low/zero score."""
        score = vegetation_score(5.0, settings)
        assert score == 0.0

    def test_unknown_clearance_returns_moderate(self, settings: RiskEngineSettings) -> None:
        """Missing clearance data returns 0.5."""
        assert vegetation_score(None, settings) == 0.5

    def test_zero_clearance_max_score(self, settings: RiskEngineSettings) -> None:
        """Zero clearance produces maximum score."""
        score = vegetation_score(0.0, settings)
        assert score == 1.0


class TestInspectionRecencyScore:
    """Tests for the inspection recency sub-score."""

    def test_recent_inspection_low_score(self, settings: RiskEngineSettings) -> None:
        """Inspected yesterday scores near zero."""
        score = inspection_recency_score(date.today() - timedelta(days=1), settings)
        assert score < 0.01

    def test_stale_inspection_high_score(self, settings: RiskEngineSettings) -> None:
        """Inspected over a year ago scores 1.0."""
        score = inspection_recency_score(date.today() - timedelta(days=400), settings)
        assert score == 1.0

    def test_never_inspected_returns_high(self, settings: RiskEngineSettings) -> None:
        """No inspection date returns 0.8."""
        assert inspection_recency_score(None, settings) == 0.8

    def test_six_months_ago_moderate(self, settings: RiskEngineSettings) -> None:
        """Inspected 6 months ago produces ~0.5 score."""
        score = inspection_recency_score(date.today() - timedelta(days=182), settings)
        assert 0.45 <= score <= 0.55


class TestCompositeRiskScore:
    """Tests for the full composite risk calculation."""

    def test_high_risk_asset(
        self, grid_cells: list[GridCell], settings: RiskEngineSettings
    ) -> None:
        """Old wooden pole near severe weather with poor vegetation clearance."""
        asset = {
            "id": "P-037",
            "asset_type": "pole",
            "lat": 36.06,
            "lon": -79.50,
            "install_year": 1988,
            "expected_lifespan_years": 40,
            "is_end_of_line": False,
            "vegetation_clearance_m": 2.5,
            "last_inspection_date": (date.today() - timedelta(days=200)).isoformat(),
        }
        result = compute_asset_risk(asset, grid_cells, 18, settings)
        assert result.composite_score > 0.5
        assert result.breakdown.weather_exposure > 0.4
        assert result.asset_id == "P-037"

    def test_low_risk_asset(self, grid_cells: list[GridCell], settings: RiskEngineSettings) -> None:
        """New concrete pole in calm area with good clearance."""
        asset = {
            "id": "P-070",
            "asset_type": "pole",
            "lat": 36.08,
            "lon": -79.48,
            "install_year": 2020,
            "expected_lifespan_years": 50,
            "is_end_of_line": False,
            "vegetation_clearance_m": 6.0,
            "last_inspection_date": (date.today() - timedelta(days=30)).isoformat(),
        }
        result = compute_asset_risk(asset, grid_cells, 18, settings)
        assert result.composite_score < 0.2

    def test_weights_sum_to_one(self, settings: RiskEngineSettings) -> None:
        """Scoring weights must sum to 1.0."""
        total = (
            settings.weight_weather
            + settings.weight_age
            + settings.weight_vegetation
            + settings.weight_inspection
        )
        assert abs(total - 1.0) < 0.001

    def test_breakdown_fields_bounded(
        self, grid_cells: list[GridCell], settings: RiskEngineSettings
    ) -> None:
        """All sub-scores are between 0 and 1."""
        asset = {
            "id": "T-008",
            "asset_type": "transformer",
            "lat": 36.10,
            "lon": -79.45,
            "install_year": 1995,
            "expected_lifespan_years": 35,
            "is_end_of_line": False,
            "vegetation_clearance_m": None,
            "last_inspection_date": None,
        }
        result = compute_asset_risk(asset, grid_cells, 12, settings)
        for field in ["weather_exposure", "age", "vegetation", "inspection_recency"]:
            val = getattr(result.breakdown, field)
            assert 0.0 <= val <= 1.0, f"{field} = {val} out of bounds"
        assert 0.0 <= result.composite_score <= 1.0
