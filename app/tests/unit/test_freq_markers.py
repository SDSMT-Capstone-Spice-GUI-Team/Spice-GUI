"""Tests for frequency response marker computation (Issue #142).

Tests -3dB cutoff detection, bandwidth, unity-gain frequency,
gain/phase margin, and edge cases.
"""

import numpy as np
import pytest
from simulation.freq_markers import _find_crossing, compute_markers, format_frequency

# ── Crossing detection ───────────────────────────────────────────────


class TestFindCrossing:
    """Test the linear interpolation crossing finder."""

    def test_simple_crossing(self):
        x = [1.0, 2.0, 3.0]
        y = [0.0, 2.0, 4.0]
        crossings = _find_crossing(x, y, 1.0)
        assert len(crossings) == 1
        assert crossings[0] == pytest.approx(1.5)

    def test_no_crossing(self):
        x = [1.0, 2.0, 3.0]
        y = [5.0, 6.0, 7.0]
        crossings = _find_crossing(x, y, 1.0)
        assert crossings == []

    def test_exact_crossing(self):
        x = [1.0, 2.0, 3.0]
        y = [0.0, 1.0, 2.0]
        crossings = _find_crossing(x, y, 1.0)
        # Point exactly on threshold found in both adjacent segments
        assert len(crossings) >= 1
        assert crossings[0] == pytest.approx(2.0)

    def test_multiple_crossings(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [0.0, 2.0, 0.0, 2.0, 0.0]
        crossings = _find_crossing(x, y, 1.0)
        assert len(crossings) == 4

    def test_empty_data(self):
        crossings = _find_crossing([], [], 1.0)
        assert crossings == []


# ── Low-pass filter response ─────────────────────────────────────────


class TestLowPassMarkers:
    """Test markers on a simple low-pass filter response."""

    @pytest.fixture
    def lowpass_data(self):
        """Generate a first-order low-pass response with fc=1kHz."""
        freqs = np.logspace(1, 6, 200)  # 10 Hz to 1 MHz
        fc = 1000.0  # 1 kHz cutoff
        # Transfer function: H(f) = 1 / (1 + j*f/fc)
        h = 1.0 / (1.0 + 1j * freqs / fc)
        mag = np.abs(h)
        phase = np.degrees(np.angle(h))
        return freqs.tolist(), mag.tolist(), phase.tolist()

    def test_cutoff_frequency(self, lowpass_data):
        freqs, mag, phase = lowpass_data
        markers = compute_markers(freqs, mag, phase)
        # Should find one -3dB point near 1 kHz
        assert len(markers["cutoff_3db"]) >= 1
        fc = markers["cutoff_3db"][0]
        assert fc == pytest.approx(1000.0, rel=0.05)

    def test_peak_gain(self, lowpass_data):
        freqs, mag, phase = lowpass_data
        markers = compute_markers(freqs, mag, phase)
        # DC gain should be ~0 dB (unity)
        assert markers["peak_gain_db"] == pytest.approx(0.0, abs=0.5)

    def test_no_bandwidth_single_cutoff(self, lowpass_data):
        freqs, mag, phase = lowpass_data
        markers = compute_markers(freqs, mag, phase)
        # Low-pass has only one -3dB point, so bandwidth is None or based on
        # single cutoff (depends on whether peak is at DC or not)
        if len(markers["cutoff_3db"]) == 1:
            assert markers["bandwidth"] is None


# ── Bandpass filter response ─────────────────────────────────────────


class TestBandpassMarkers:
    """Test markers on a bandpass filter response."""

    @pytest.fixture
    def bandpass_data(self):
        """Generate a bandpass response centered at 10 kHz with Q=5."""
        freqs = np.logspace(2, 6, 500)  # 100 Hz to 1 MHz
        f0 = 10000.0  # 10 kHz center
        Q = 5.0
        # Second-order bandpass: H(s) = (s/Q) / (s^2 + s/Q + 1) where s = j*f/f0
        s = 1j * freqs / f0
        h = (s / Q) / (s**2 + s / Q + 1.0)
        mag = np.abs(h)
        phase = np.degrees(np.angle(h))
        return freqs.tolist(), mag.tolist(), phase.tolist()

    def test_two_cutoff_points(self, bandpass_data):
        freqs, mag, phase = bandpass_data
        markers = compute_markers(freqs, mag, phase)
        assert len(markers["cutoff_3db"]) >= 2

    def test_bandwidth_computed(self, bandpass_data):
        freqs, mag, phase = bandpass_data
        markers = compute_markers(freqs, mag, phase)
        assert markers["bandwidth"] is not None
        # For Q=5, BW ≈ f0/Q = 10000/5 = 2000 Hz
        assert markers["bandwidth"] == pytest.approx(2000.0, rel=0.2)

    def test_peak_near_center(self, bandpass_data):
        freqs, mag, phase = bandpass_data
        markers = compute_markers(freqs, mag, phase)
        assert markers["peak_freq"] == pytest.approx(10000.0, rel=0.1)


# ── Gain/phase margin ───────────────────────────────────────────────


class TestMargins:
    """Test gain and phase margin computation."""

    def test_phase_margin_with_data(self):
        """Test phase margin when unity-gain and phase data available."""
        # Create response that crosses 0dB with known phase
        freqs = np.logspace(1, 6, 500)
        fc = 1000.0
        h = 10.0 / (1.0 + 1j * freqs / fc)  # Gain of 10 at DC
        mag = np.abs(h)
        phase = np.degrees(np.angle(h))
        markers = compute_markers(freqs.tolist(), mag.tolist(), phase.tolist())
        # Unity gain frequency exists (gain is 10 at DC, drops to 1 somewhere)
        assert markers["unity_gain_freq"] is not None
        # Phase margin should be positive for stable system
        assert markers["phase_margin_deg"] is not None
        assert markers["phase_margin_deg"] > 0

    def test_no_margin_without_phase(self):
        """Test that margins are None when no phase data given."""
        freqs = [100, 1000, 10000]
        mag = [1.0, 0.7, 0.1]
        markers = compute_markers(freqs, mag)
        assert markers["gain_margin_db"] is None
        assert markers["phase_margin_deg"] is None


# ── Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_data(self):
        markers = compute_markers([], [])
        assert markers["cutoff_3db"] == []
        assert markers["peak_gain_db"] is None

    def test_single_point(self):
        markers = compute_markers([1000], [1.0])
        assert markers["cutoff_3db"] == []
        assert markers["peak_gain_db"] is None

    def test_flat_response(self):
        """Flat response should have no -3dB crossings."""
        freqs = np.logspace(1, 6, 100).tolist()
        mag = [1.0] * 100
        markers = compute_markers(freqs, mag)
        assert markers["cutoff_3db"] == []
        assert markers["peak_gain_db"] == pytest.approx(0.0, abs=0.1)

    def test_very_small_magnitude(self):
        """Should handle very small magnitudes without math errors."""
        freqs = [100, 1000, 10000]
        mag = [1e-20, 1e-25, 1e-30]
        markers = compute_markers(freqs, mag)
        assert markers["peak_gain_db"] is not None


# ── format_frequency ─────────────────────────────────────────────────


class TestFormatFrequency:
    """Test frequency formatting with SI prefixes."""

    def test_hz(self):
        assert format_frequency(100) == "100.00 Hz"

    def test_khz(self):
        assert format_frequency(1500) == "1.50 kHz"

    def test_mhz(self):
        assert format_frequency(2.5e6) == "2.50 MHz"

    def test_ghz(self):
        assert format_frequency(3.3e9) == "3.30 GHz"

    def test_none(self):
        assert format_frequency(None) == "N/A"
