"""Tests for transient power metrics computation."""

import math

from models.component import ComponentData
from simulation.power_metrics import (_fmt_eng, compute_rms,
                                      compute_transient_power_metrics,
                                      format_power_summary)

# ---------------------------------------------------------------------------
# compute_rms tests
# ---------------------------------------------------------------------------


class TestComputeRms:
    def test_empty_list(self):
        assert compute_rms([]) == 0.0

    def test_dc_signal(self):
        """RMS of a constant signal equals its absolute value."""
        assert compute_rms([5.0, 5.0, 5.0]) == 5.0

    def test_negative_dc(self):
        assert compute_rms([-3.0, -3.0, -3.0]) == 3.0

    def test_sine_wave_approximation(self):
        """RMS of a sine wave is Vpeak / sqrt(2)."""
        import math

        n = 10000
        peak = 10.0
        values = [peak * math.sin(2 * math.pi * i / n) for i in range(n)]
        expected = peak / math.sqrt(2)
        assert abs(compute_rms(values) - expected) < 0.01

    def test_single_value(self):
        assert compute_rms([7.0]) == 7.0

    def test_mixed_positive_negative(self):
        """RMS of [1, -1] = 1."""
        assert compute_rms([1.0, -1.0]) == 1.0


# ---------------------------------------------------------------------------
# compute_transient_power_metrics tests
# ---------------------------------------------------------------------------


def _make_component(cid, ctype, value="1k"):
    return ComponentData(
        component_id=cid,
        component_type=ctype,
        value=value,
        position=(0, 0),
    )


class TestComputeTransientPowerMetrics:
    def test_empty_data(self):
        assert compute_transient_power_metrics([], {}) == []

    def test_none_data(self):
        assert compute_transient_power_metrics(None, {}) == []

    def test_no_components(self):
        data = [{"time": 0.0, "v_r1": 5.0}]
        assert compute_transient_power_metrics(data, {}) == []

    def test_resistor_dc_voltage(self):
        """Constant 10V across 1k resistor: Vrms=10, Irms=10mA, Pavg=0.1W."""
        components = {"R1": _make_component("R1", "Resistor", "1k")}
        data = [
            {"time": 0.0, "v_r1": 10.0},
            {"time": 1e-3, "v_r1": 10.0},
            {"time": 2e-3, "v_r1": 10.0},
        ]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 1
        m = metrics[0]
        assert m["component_id"] == "R1"
        assert m["vrms"] == 10.0
        assert abs(m["irms"] - 0.01) < 1e-9
        assert abs(m["pavg"] - 0.1) < 1e-9
        assert abs(m["ppeak"] - 0.1) < 1e-9

    def test_resistor_varying_voltage(self):
        """0V and 10V alternating across 100 ohm: Vrms=sqrt(50), Pavg=0.5W."""
        components = {"R1": _make_component("R1", "Resistor", "100")}
        data = [
            {"time": 0.0, "v_r1": 0.0},
            {"time": 1e-3, "v_r1": 10.0},
        ]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 1
        m = metrics[0]
        assert abs(m["vrms"] - math.sqrt(50)) < 1e-9
        # Pavg = mean(0/100, 100/100) = 0.5
        assert abs(m["pavg"] - 0.5) < 1e-9
        # Ppeak = 100/100 = 1.0
        assert abs(m["ppeak"] - 1.0) < 1e-9

    def test_multiple_resistors(self):
        """Two resistors should each get their own metrics."""
        components = {
            "R1": _make_component("R1", "Resistor", "1k"),
            "R2": _make_component("R2", "Resistor", "2k"),
        }
        data = [
            {"time": 0.0, "v_r1": 5.0, "v_r2": 10.0},
            {"time": 1e-3, "v_r1": 5.0, "v_r2": 10.0},
        ]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 2
        ids = {m["component_id"] for m in metrics}
        assert ids == {"R1", "R2"}

    def test_ground_component_skipped(self):
        components = {"GND": _make_component("GND", "Ground", "0")}
        data = [{"time": 0.0}]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 0

    def test_missing_voltage_key(self):
        """Components without v_XX key in data are skipped."""
        components = {"R1": _make_component("R1", "Resistor", "1k")}
        data = [{"time": 0.0, "out": 5.0}]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 0

    def test_non_resistor_skipped(self):
        """Only resistors get power metrics (voltage sources lack current data)."""
        components = {"V1": _make_component("V1", "Voltage Source", "5")}
        data = [{"time": 0.0, "v_v1": 5.0}]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 0

    def test_invalid_resistance_value(self):
        """Components with unparseable values are skipped."""
        components = {"R1": _make_component("R1", "Resistor", "abc")}
        data = [{"time": 0.0, "v_r1": 5.0}]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 0

    def test_si_prefix_resistance(self):
        """Resistance with SI prefix parsed correctly (10k = 10000)."""
        components = {"R1": _make_component("R1", "Resistor", "10k")}
        data = [{"time": 0.0, "v_r1": 100.0}]
        metrics = compute_transient_power_metrics(data, components)
        assert len(metrics) == 1
        # P = V^2/R = 10000/10000 = 1W
        assert abs(metrics[0]["pavg"] - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# format_power_summary tests
# ---------------------------------------------------------------------------


class TestFormatPowerSummary:
    def test_empty_metrics(self):
        assert format_power_summary([]) == ""

    def test_single_resistor(self):
        metrics = [
            {
                "component_id": "R1",
                "component_type": "Resistor",
                "value": "1k",
                "vrms": 10.0,
                "irms": 0.01,
                "pavg": 0.1,
                "ppeak": 0.1,
            }
        ]
        result = format_power_summary(metrics)
        assert "POWER SUMMARY" in result
        assert "R1" in result
        assert "1k" in result
        assert "Total" in result

    def test_total_power(self):
        """Total Pavg should sum individual pavg values."""
        metrics = [
            {
                "component_id": "R1",
                "component_type": "Resistor",
                "value": "1k",
                "vrms": 10.0,
                "irms": 0.01,
                "pavg": 0.1,
                "ppeak": 0.1,
            },
            {
                "component_id": "R2",
                "component_type": "Resistor",
                "value": "2k",
                "vrms": 10.0,
                "irms": 0.005,
                "pavg": 0.05,
                "ppeak": 0.05,
            },
        ]
        result = format_power_summary(metrics)
        # Total should be 0.15W = 150mW
        assert "150 mW" in result


# ---------------------------------------------------------------------------
# _fmt_eng tests
# ---------------------------------------------------------------------------


class TestFmtEng:
    def test_zero(self):
        assert _fmt_eng(0, "W") == "0 W"

    def test_milliwatts(self):
        result = _fmt_eng(0.015, "W")
        assert "mW" in result

    def test_kilohms(self):
        result = _fmt_eng(4700, "V")
        assert "kV" in result

    def test_microamps(self):
        result = _fmt_eng(0.000050, "A")
        assert "uA" in result

    def test_plain_unit(self):
        result = _fmt_eng(5.0, "V")
        assert "V" in result
        assert "5" in result
