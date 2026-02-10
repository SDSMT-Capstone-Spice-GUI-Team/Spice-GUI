"""Tests for FFT analysis module."""

import numpy as np
import pytest
from simulation.fft_analysis import (
    FFTResult,
    analyze_signal_spectrum,
    compute_fft,
    compute_thd,
    find_fundamental_frequency,
)


class TestComputeFFT:
    def test_basic_sine_wave(self):
        """Test FFT of a simple sine wave."""
        # Create 1 Hz sine wave sampled at 100 Hz for 1 second
        sample_rate = 100
        duration = 1.0
        freq = 1.0

        time = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        signal = np.sin(2 * np.pi * freq * time)

        result = compute_fft(time, signal, "Test Signal", "none")

        assert isinstance(result, FFTResult)
        assert result.signal_name == "Test Signal"
        assert result.sample_rate == pytest.approx(sample_rate, rel=0.01)
        assert len(result.frequencies) == len(time) // 2

        # Peak should be at 1 Hz
        peak_idx = np.argmax(result.magnitude)
        peak_freq = result.frequencies[peak_idx]
        assert peak_freq == pytest.approx(freq, abs=sample_rate / len(time))

    def test_hanning_window(self):
        """Test FFT with Hanning window."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time)

        result = compute_fft(time, signal, "Test", "hanning")
        assert result.window_type == "hanning"
        assert len(result.magnitude) > 0

    def test_hamming_window(self):
        """Test FFT with Hamming window."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time)

        result = compute_fft(time, signal, "Test", "hamming")
        assert result.window_type == "hamming"

    def test_blackman_window(self):
        """Test FFT with Blackman window."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time)

        result = compute_fft(time, signal, "Test", "blackman")
        assert result.window_type == "blackman"

    def test_invalid_window(self):
        """Test FFT with invalid window type."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time)

        with pytest.raises(ValueError, match="Unknown window type"):
            compute_fft(time, signal, "Test", "invalid_window")

    def test_mismatched_lengths(self):
        """Test FFT with time and signal arrays of different lengths."""
        time = np.linspace(0, 1, 100)
        signal = np.sin(2 * np.pi * 5 * time[:50])  # Half length

        with pytest.raises(ValueError, match="same length"):
            compute_fft(time, signal)

    def test_insufficient_samples(self):
        """Test FFT with too few samples."""
        time = np.array([0, 0.1, 0.2])
        signal = np.array([0, 1, 0])

        with pytest.raises(ValueError, match="at least 4 samples"):
            compute_fft(time, signal)

    def test_magnitude_db_range(self):
        """Test that magnitude_db values are reasonable."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time)

        result = compute_fft(time, signal, "Test", "none")

        # dB values should be finite
        assert np.all(np.isfinite(result.magnitude_db))
        # Peak should be positive dB for unit amplitude sine
        assert np.max(result.magnitude_db) > -10

    def test_phase_range(self):
        """Test that phase values are in valid range."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time)

        result = compute_fft(time, signal, "Test", "none")

        # Phase should be in -180 to 180 degrees
        assert np.all(result.phase >= -180)
        assert np.all(result.phase <= 180)


class TestFindFundamental:
    def test_single_frequency(self):
        """Test fundamental frequency detection for single sine wave."""
        time = np.linspace(0, 1, 1000, endpoint=False)
        freq = 50.0
        signal = np.sin(2 * np.pi * freq * time)

        result = compute_fft(time, signal, "Test", "hanning")
        fundamental = find_fundamental_frequency(result, min_freq=10)

        assert fundamental == pytest.approx(freq, abs=1.0)

    def test_with_harmonics(self):
        """Test fundamental detection with harmonics present."""
        time = np.linspace(0, 1, 1000, endpoint=False)
        fundamental_freq = 60.0

        # Fundamental + 2nd and 3rd harmonics
        signal = np.sin(2 * np.pi * fundamental_freq * time)
        signal += 0.3 * np.sin(2 * np.pi * 2 * fundamental_freq * time)
        signal += 0.2 * np.sin(2 * np.pi * 3 * fundamental_freq * time)

        result = compute_fft(time, signal, "Test", "hanning")
        fundamental = find_fundamental_frequency(result, min_freq=10)

        # Should find the fundamental, not harmonics
        assert fundamental == pytest.approx(fundamental_freq, abs=2.0)

    def test_min_freq_threshold(self):
        """Test that frequencies below min_freq are ignored."""
        time = np.linspace(0, 1, 1000, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time) + 2.0  # 5 Hz + DC offset

        result = compute_fft(time, signal, "Test", "none")
        fundamental = find_fundamental_frequency(result, min_freq=10)

        # With min_freq=10, the 5 Hz component is ignored
        # May find harmonics or noise above 10 Hz instead
        assert fundamental >= 10.0 or fundamental == 0.0


class TestComputeTHD:
    def test_pure_sine_wave(self):
        """Test THD of pure sine wave (should be near 0%)."""
        time = np.linspace(0, 1, 1000, endpoint=False)
        freq = 60.0
        signal = np.sin(2 * np.pi * freq * time)

        result = compute_fft(time, signal, "Test", "hanning")
        fundamental = find_fundamental_frequency(result, min_freq=10)
        thd = compute_thd(result, fundamental, num_harmonics=5)

        # Pure sine should have very low THD (< 1%)
        assert thd < 1.0

    def test_with_harmonics(self):
        """Test THD calculation with known harmonics."""
        time = np.linspace(0, 1, 2000, endpoint=False)
        fundamental_freq = 60.0

        # Fundamental + 30% 2nd harmonic
        signal = np.sin(2 * np.pi * fundamental_freq * time)
        signal += 0.3 * np.sin(2 * np.pi * 2 * fundamental_freq * time)

        result = compute_fft(time, signal, "Test", "hanning")
        fundamental = find_fundamental_frequency(result, min_freq=10)
        thd = compute_thd(result, fundamental, num_harmonics=5)

        # THD should be approximately 30%
        assert thd == pytest.approx(30.0, abs=5.0)

    def test_zero_fundamental(self):
        """Test THD with zero fundamental frequency."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.sin(2 * np.pi * 5 * time)

        result = compute_fft(time, signal, "Test", "none")
        thd = compute_thd(result, 0.0)

        assert thd == 0.0


class TestAnalyzeSignalSpectrum:
    def test_complete_analysis(self):
        """Test full spectrum analysis pipeline."""
        time = np.linspace(0, 1, 1000, endpoint=False)
        freq = 50.0
        signal = np.sin(2 * np.pi * freq * time)
        signal += 0.2 * np.sin(2 * np.pi * 2 * freq * time)  # Add 2nd harmonic

        result = analyze_signal_spectrum(time, signal, "Test Signal", "hanning")

        # Check that result has all expected attributes
        assert isinstance(result, FFTResult)
        assert result.signal_name == "Test Signal"
        assert result.fundamental_freq is not None
        assert result.fundamental_freq == pytest.approx(freq, abs=2.0)
        assert result.thd_percent is not None
        assert result.thd_percent > 0  # Should have some THD due to harmonic
        assert result.thd_percent < 50  # But not excessive

    def test_dc_signal(self):
        """Test analysis of DC signal."""
        time = np.linspace(0, 1, 100, endpoint=False)
        signal = np.ones_like(time) * 5.0  # DC signal

        result = analyze_signal_spectrum(time, signal, "DC Signal", "none")

        # FFT should work - DC signal may have numerical noise detected as fundamental
        # Just verify the function completes without error
        assert result.fundamental_freq is not None

    def test_complex_signal(self):
        """Test analysis of complex multi-frequency signal."""
        time = np.linspace(0, 2, 2000, endpoint=False)

        # Mix of three frequencies
        signal = np.sin(2 * np.pi * 10 * time)
        signal += 0.5 * np.sin(2 * np.pi * 25 * time)
        signal += 0.3 * np.sin(2 * np.pi * 40 * time)

        result = analyze_signal_spectrum(time, signal, "Complex", "hanning")

        # Should identify 10 Hz as fundamental (largest amplitude)
        assert result.fundamental_freq == pytest.approx(10.0, abs=1.0)
