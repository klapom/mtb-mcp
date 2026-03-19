"""Tests for fitness tracking algorithms -- CTL, ATL, TSB calculation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from mtb_mcp.intelligence.fitness_tracker import (
    DailyTrainingLoad,
    calculate_fitness_history,
    check_alpencross_readiness,
    check_xc_readiness,
    estimate_tss_from_activity,
    get_training_status,
)

# ---------------------------------------------------------------------------
# TSS Estimation
# ---------------------------------------------------------------------------


class TestEstimateTSS:
    """Tests for TSS estimation from activity data."""

    def test_power_based_tss(self) -> None:
        """Power-based TSS should use normalized power and FTP."""
        tss = estimate_tss_from_activity(
            distance_km=40.0,
            elevation_m=800.0,
            duration_hours=2.0,
            avg_power=200.0,
            ftp=250.0,
        )
        # IF = 200/250 = 0.8, TSS = (2*3600*200*0.8)/(250*3600)*100 = 128
        assert tss == pytest.approx(128.0, abs=1.0)

    def test_power_based_at_ftp(self) -> None:
        """Riding at FTP for 1 hour should give ~100 TSS."""
        tss = estimate_tss_from_activity(
            distance_km=30.0,
            elevation_m=500.0,
            duration_hours=1.0,
            avg_power=250.0,
            ftp=250.0,
        )
        assert tss == pytest.approx(100.0, abs=1.0)

    def test_hr_based_tss(self) -> None:
        """HR-based TSS should estimate from heart rate intensity."""
        tss = estimate_tss_from_activity(
            distance_km=40.0,
            elevation_m=800.0,
            duration_hours=2.0,
            avg_hr=150.0,
        )
        assert tss > 0
        # HR 150 is moderate effort -> should be in a reasonable range
        assert 50 < tss < 200

    def test_hr_based_higher_hr_more_tss(self) -> None:
        """Higher HR should result in higher TSS."""
        tss_low = estimate_tss_from_activity(
            distance_km=30.0,
            elevation_m=500.0,
            duration_hours=2.0,
            avg_hr=120.0,
        )
        tss_high = estimate_tss_from_activity(
            distance_km=30.0,
            elevation_m=500.0,
            duration_hours=2.0,
            avg_hr=170.0,
        )
        assert tss_high > tss_low

    def test_fallback_tss(self) -> None:
        """Fallback TSS should estimate from duration and terrain."""
        tss = estimate_tss_from_activity(
            distance_km=40.0,
            elevation_m=800.0,
            duration_hours=2.0,
        )
        assert tss > 0
        # 2h moderate ride should be roughly 80-150 TSS
        assert 50 < tss < 200

    def test_fallback_more_elevation_more_tss(self) -> None:
        """More elevation should increase fallback TSS."""
        tss_flat = estimate_tss_from_activity(
            distance_km=40.0,
            elevation_m=100.0,
            duration_hours=2.0,
        )
        tss_hilly = estimate_tss_from_activity(
            distance_km=40.0,
            elevation_m=2000.0,
            duration_hours=2.0,
        )
        assert tss_hilly > tss_flat

    def test_power_takes_priority_over_hr(self) -> None:
        """When both power and HR are available, power should be used."""
        tss_power = estimate_tss_from_activity(
            distance_km=30.0,
            elevation_m=500.0,
            duration_hours=1.0,
            avg_power=250.0,
            ftp=250.0,
            avg_hr=150.0,
        )
        # Power-based at FTP should be ~100
        assert tss_power == pytest.approx(100.0, abs=1.0)

    def test_zero_duration(self) -> None:
        """Zero duration should not crash."""
        tss = estimate_tss_from_activity(
            distance_km=0.0,
            elevation_m=0.0,
            duration_hours=0.0,
        )
        assert tss == 0.0

    def test_zero_ftp_uses_hr_fallback(self) -> None:
        """Zero FTP should fall through to HR or fallback."""
        tss = estimate_tss_from_activity(
            distance_km=30.0,
            elevation_m=500.0,
            duration_hours=2.0,
            avg_power=200.0,
            ftp=0.0,
            avg_hr=140.0,
        )
        # FTP=0 should skip power-based, use HR
        assert tss > 0


# ---------------------------------------------------------------------------
# CTL/ATL/TSB Calculation
# ---------------------------------------------------------------------------


class TestCalculateFitnessHistory:
    """Tests for CTL/ATL/TSB calculation over multiple days."""

    def test_empty_input(self) -> None:
        """Empty daily loads should return empty history."""
        result = calculate_fitness_history([])
        assert result == []

    def test_single_day(self) -> None:
        """Single day should calculate initial CTL/ATL/TSB."""
        loads = [DailyTrainingLoad(date=date(2026, 1, 1), tss=100.0)]
        result = calculate_fitness_history(loads)

        assert len(result) == 1
        assert result[0].date == date(2026, 1, 1)
        # CTL: 0 + (100 - 0) / 42 = ~2.38
        assert result[0].ctl == pytest.approx(2.38, abs=0.01)
        # ATL: 0 + (100 - 0) / 7 = ~14.29
        assert result[0].atl == pytest.approx(14.29, abs=0.01)
        # TSB = CTL - ATL
        assert result[0].tsb == pytest.approx(result[0].ctl - result[0].atl, abs=0.01)

    def test_multiple_days_with_gaps(self) -> None:
        """Gaps between training days should be filled with rest days (TSS=0)."""
        loads = [
            DailyTrainingLoad(date=date(2026, 1, 1), tss=100.0),
            DailyTrainingLoad(date=date(2026, 1, 3), tss=80.0),
        ]
        result = calculate_fitness_history(loads)

        assert len(result) == 3  # Jan 1, 2, 3
        assert result[0].date == date(2026, 1, 1)
        assert result[1].date == date(2026, 1, 2)  # Rest day
        assert result[2].date == date(2026, 1, 3)

    def test_consistent_training_builds_ctl(self) -> None:
        """Consistent training over time should build CTL."""
        # 30 days of 80 TSS
        loads = [
            DailyTrainingLoad(date=date(2026, 1, 1) + timedelta(days=i), tss=80.0)
            for i in range(30)
        ]
        result = calculate_fitness_history(loads)

        assert len(result) == 30
        # CTL should be increasing
        assert result[-1].ctl > result[0].ctl
        # After 30 days of 80 TSS, CTL should be approaching 80
        assert result[-1].ctl > 30

    def test_rest_decreases_atl_faster_than_ctl(self) -> None:
        """Rest days should decrease ATL faster than CTL (7-day vs 42-day)."""
        # 14 days of training then 7 days rest
        loads = [
            DailyTrainingLoad(date=date(2026, 1, 1) + timedelta(days=i), tss=100.0)
            for i in range(14)
        ]
        # 7 days of rest (no load)
        loads.append(DailyTrainingLoad(date=date(2026, 1, 22), tss=0.0))

        result = calculate_fitness_history(loads)

        # Get values at end of training block
        last_training = result[13]
        # Get values at end of rest
        last_rest = result[-1]

        # ATL should drop more than CTL during rest
        atl_drop = last_training.atl - last_rest.atl
        ctl_drop = last_training.ctl - last_rest.ctl
        assert atl_drop > ctl_drop

    def test_initial_ctl_atl(self) -> None:
        """Custom initial CTL/ATL should be used."""
        loads = [DailyTrainingLoad(date=date(2026, 1, 1), tss=50.0)]
        result = calculate_fitness_history(loads, initial_ctl=40.0, initial_atl=60.0)

        assert len(result) == 1
        # CTL: 40 + (50 - 40) / 42
        expected_ctl = 40.0 + (50.0 - 40.0) / 42
        assert result[0].ctl == pytest.approx(expected_ctl, abs=0.01)
        # ATL: 60 + (50 - 60) / 7
        expected_atl = 60.0 + (50.0 - 60.0) / 7
        assert result[0].atl == pytest.approx(expected_atl, abs=0.01)

    def test_tsb_equals_ctl_minus_atl(self) -> None:
        """TSB should always equal CTL - ATL."""
        loads = [
            DailyTrainingLoad(date=date(2026, 1, 1) + timedelta(days=i), tss=75.0)
            for i in range(10)
        ]
        result = calculate_fitness_history(loads)

        for state in result:
            assert state.tsb == pytest.approx(state.ctl - state.atl, abs=0.01)

    def test_unsorted_input_handled(self) -> None:
        """Input loads need not be sorted -- they should be handled correctly."""
        loads = [
            DailyTrainingLoad(date=date(2026, 1, 3), tss=60.0),
            DailyTrainingLoad(date=date(2026, 1, 1), tss=100.0),
        ]
        result = calculate_fitness_history(loads)

        assert result[0].date == date(2026, 1, 1)
        assert result[-1].date == date(2026, 1, 3)


# ---------------------------------------------------------------------------
# Training Status Interpretation
# ---------------------------------------------------------------------------


class TestGetTrainingStatus:
    """Tests for TSB interpretation."""

    @pytest.mark.parametrize(
        ("tsb", "expected"),
        [
            (25.0, "Fresh (possibly detrained)"),
            (16.0, "Fresh (possibly detrained)"),
            (15.1, "Fresh (possibly detrained)"),
            (15.0, "Optimal for racing"),
            (10.0, "Optimal for racing"),
            (5.1, "Optimal for racing"),
            (5.0, "Productive training"),
            (0.0, "Productive training"),
            (-5.0, "Productive training"),
            (-9.9, "Productive training"),
            (-10.0, "Fatigued"),
            (-20.0, "Fatigued"),
            (-29.9, "Fatigued"),
            (-30.0, "Overtraining risk!"),
            (-50.0, "Overtraining risk!"),
        ],
    )
    def test_tsb_to_status(self, tsb: float, expected: str) -> None:
        """Each TSB range should map to the correct status."""
        assert get_training_status(tsb) == expected


# ---------------------------------------------------------------------------
# Alpencross Readiness
# ---------------------------------------------------------------------------


class TestCheckAlpencrossReadiness:
    """Tests for Alpencross readiness check."""

    def test_fully_ready(self) -> None:
        """All criteria met should return ready."""
        result = check_alpencross_readiness(
            ctl=85.0,
            weekly_elevations=[3500, 3200, 3100, 3300],
            longest_rides_km=[90.0, 85.0, 70.0],
            back_to_back_count=3,
        )
        assert result["ready"] is True
        assert result["score"] == 100

    def test_not_ready_low_ctl(self) -> None:
        """Low CTL should fail readiness."""
        result = check_alpencross_readiness(
            ctl=50.0,
            weekly_elevations=[3500, 3200, 3100, 3300],
            longest_rides_km=[90.0, 85.0],
            back_to_back_count=3,
        )
        assert result["ready"] is False
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["ctl_ready"] is False

    def test_not_ready_low_elevation(self) -> None:
        """Insufficient weekly elevation should fail readiness."""
        result = check_alpencross_readiness(
            ctl=85.0,
            weekly_elevations=[1500, 2000, 1800, 2200],
            longest_rides_km=[90.0, 85.0],
            back_to_back_count=3,
        )
        assert result["ready"] is False
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["elevation_ready"] is False

    def test_not_ready_no_long_rides(self) -> None:
        """No rides over 80km should fail readiness."""
        result = check_alpencross_readiness(
            ctl=85.0,
            weekly_elevations=[3500, 3200, 3100, 3300],
            longest_rides_km=[60.0, 70.0, 75.0],
            back_to_back_count=3,
        )
        assert result["ready"] is False
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["long_ride_ready"] is False

    def test_not_ready_no_back_to_back(self) -> None:
        """No back-to-back rides should fail readiness."""
        result = check_alpencross_readiness(
            ctl=85.0,
            weekly_elevations=[3500, 3200, 3100, 3300],
            longest_rides_km=[90.0, 85.0],
            back_to_back_count=0,
        )
        assert result["ready"] is False
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["back_to_back_ready"] is False

    def test_recommendations_for_failures(self) -> None:
        """Failed checks should produce recommendations."""
        result = check_alpencross_readiness(
            ctl=50.0,
            weekly_elevations=[1000, 1200],
            longest_rides_km=[50.0],
            back_to_back_count=0,
        )
        recs = result["recommendations"]
        assert isinstance(recs, list)
        assert len(recs) == 4  # All four checks fail

    @pytest.mark.parametrize(
        ("ctl", "expected_ready"),
        [
            (79.0, False),
            (80.0, True),
            (100.0, True),
        ],
    )
    def test_ctl_threshold(self, ctl: float, expected_ready: bool) -> None:
        """CTL threshold is exactly 80."""
        result = check_alpencross_readiness(
            ctl=ctl,
            weekly_elevations=[3500, 3200, 3100, 3300],
            longest_rides_km=[90.0, 85.0],
            back_to_back_count=3,
        )
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["ctl_ready"] is expected_ready


# ---------------------------------------------------------------------------
# XC Readiness
# ---------------------------------------------------------------------------


class TestCheckXCReadiness:
    """Tests for XC race readiness check."""

    def test_fully_ready(self) -> None:
        """All criteria met should return ready."""
        result = check_xc_readiness(
            ctl=65.0,
            ftp_wkg=4.0,
            weeks_to_race=1,
        )
        assert result["ready"] is True
        assert result["score"] == 100

    def test_not_ready_low_ctl(self) -> None:
        """Low CTL should fail readiness."""
        result = check_xc_readiness(
            ctl=40.0,
            ftp_wkg=4.0,
            weeks_to_race=1,
        )
        assert result["ready"] is False
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["ctl_ready"] is False

    def test_not_ready_low_ftp(self) -> None:
        """Low FTP should fail readiness."""
        result = check_xc_readiness(
            ctl=65.0,
            ftp_wkg=3.0,
            weeks_to_race=1,
        )
        assert result["ready"] is False
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["ftp_ready"] is False

    def test_not_ready_no_taper(self) -> None:
        """Too far from race (no taper) should flag it."""
        result = check_xc_readiness(
            ctl=65.0,
            ftp_wkg=4.0,
            weeks_to_race=8,
        )
        assert result["ready"] is False
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["taper_appropriate"] is False

    def test_no_ftp_data(self) -> None:
        """Missing FTP should fail with recommendation."""
        result = check_xc_readiness(
            ctl=65.0,
            ftp_wkg=None,
            weeks_to_race=1,
        )
        assert result["ready"] is False
        recs = result["recommendations"]
        assert isinstance(recs, list)
        assert any("FTP unknown" in r for r in recs)

    @pytest.mark.parametrize(
        ("ctl", "expected_ready"),
        [
            (59.0, False),
            (60.0, True),
            (80.0, True),
        ],
    )
    def test_ctl_threshold(self, ctl: float, expected_ready: bool) -> None:
        """CTL threshold for XC is exactly 60."""
        result = check_xc_readiness(
            ctl=ctl,
            ftp_wkg=4.0,
            weeks_to_race=1,
        )
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["ctl_ready"] is expected_ready

    @pytest.mark.parametrize(
        ("ftp_wkg", "expected_ready"),
        [
            (3.4, False),
            (3.5, True),
            (4.5, True),
        ],
    )
    def test_ftp_threshold(self, ftp_wkg: float, expected_ready: bool) -> None:
        """FTP threshold for XC is exactly 3.5 W/kg."""
        result = check_xc_readiness(
            ctl=65.0,
            ftp_wkg=ftp_wkg,
            weeks_to_race=1,
        )
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["ftp_ready"] is expected_ready

    @pytest.mark.parametrize(
        ("weeks_to_race", "expected_appropriate"),
        [
            (0, False),
            (1, True),
            (2, True),
            (3, False),
            (8, False),
        ],
    )
    def test_taper_timing(self, weeks_to_race: int, expected_appropriate: bool) -> None:
        """Taper is appropriate 1-2 weeks before race."""
        result = check_xc_readiness(
            ctl=65.0,
            ftp_wkg=4.0,
            weeks_to_race=weeks_to_race,
        )
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert checks["taper_appropriate"] is expected_appropriate
