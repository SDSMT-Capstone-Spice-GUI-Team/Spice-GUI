"""
FFT Analysis Module

Provides Fourier transform analysis for transient simulation results.
Includes magnitude/phase spectrum computation, windowing, and THD calculation.
"""

from typing import Optional

import numpy as np


class FFTResult:
    """Container for FFT analysis results"""

    def __init__(
        self,
        frequencies: np.ndarray,
        magnitude: np.ndarray,
        magnitude_db: np.ndarray,
        phase: np.ndarray,
        signal_name: str,
        sample_rate: float,
        window_type: str,
    ):
        self.frequencies = frequencies
        self.magnitude = magnitude
        self.magnitude_db = magnitude_db
        self.phase = phase
        self.signal_name = signal_name
        self.sample_rate = sample_rate
        self.window_type = window_type
        self.fundamental_freq: Optional[float] = None
        self.thd_percent: Optional[float] = None
        self.harmonics: list = []


def compute_fft(
    time: np.ndarray,
    signal: np.ndarray,
    signal_name: str = "Signal",
    window: str = "hanning",
) -> FFTResult:
    """
    Compute FFT of a time-domain signal.

    Args:
        time: Time array (seconds)
        signal: Signal amplitude array
        signal_name: Name of the signal for labeling
        window: Window function ('hanning', 'hamming', 'blackman', 'none')

    Returns:
        FFTResult containing frequency-domain data

    Raises:
        ValueError: If time and signal arrays have different lengths or are too short
    """
    if len(time) != len(signal):
        raise ValueError("Time and signal arrays must have the same length")

    if len(time) < 4:
        raise ValueError("Need at least 4 samples for FFT analysis")

    # Calculate sample rate from time array
    dt = np.mean(np.diff(time))
    sample_rate = 1.0 / dt
    n_samples = len(signal)

    # Apply window function to reduce spectral leakage
    if window.lower() == "hanning":
        window_func = np.hanning(n_samples)
    elif window.lower() == "hamming":
        window_func = np.hamming(n_samples)
    elif window.lower() == "blackman":
        window_func = np.blackman(n_samples)
    elif window.lower() == "none":
        window_func = np.ones(n_samples)
    else:
        raise ValueError(
            f"Unknown window type: {window}. Use 'hanning', 'hamming', 'blackman', or 'none'"
        )

    # Apply window and compensate for window power loss
    windowed_signal = signal * window_func
    window_power_correction = np.sqrt(np.mean(window_func**2))

    # Compute FFT
    fft_result = np.fft.fft(windowed_signal) / n_samples
    fft_result = fft_result / window_power_correction  # Correct for window attenuation

    # Get positive frequencies only (first half of spectrum)
    n_positive = n_samples // 2
    frequencies = np.fft.fftfreq(n_samples, dt)[:n_positive]

    # Magnitude (multiply by 2 to account for negative frequencies, except DC)
    magnitude = np.abs(fft_result[:n_positive])
    magnitude[1:] *= 2  # Double all except DC component

    # Magnitude in dB (avoid log(0) by adding tiny epsilon)
    magnitude_db = 20 * np.log10(magnitude + 1e-12)

    # Phase in degrees
    phase = np.angle(fft_result[:n_positive], deg=True)

    return FFTResult(
        frequencies=frequencies,
        magnitude=magnitude,
        magnitude_db=magnitude_db,
        phase=phase,
        signal_name=signal_name,
        sample_rate=sample_rate,
        window_type=window,
    )


def find_fundamental_frequency(fft_result: FFTResult, min_freq: float = 10.0) -> float:
    """
    Find the fundamental frequency (peak in magnitude spectrum).

    Args:
        fft_result: FFT analysis result
        min_freq: Minimum frequency to consider (Hz) to avoid DC

    Returns:
        Fundamental frequency in Hz
    """
    # Only consider frequencies above min_freq to avoid DC component
    mask = fft_result.frequencies >= min_freq
    if not np.any(mask):
        return 0.0

    valid_freqs = fft_result.frequencies[mask]
    valid_mags = fft_result.magnitude[mask]

    # Find peak
    peak_idx = np.argmax(valid_mags)
    return valid_freqs[peak_idx]


def compute_thd(
    fft_result: FFTResult, fundamental_freq: float, num_harmonics: int = 5
) -> float:
    """
    Compute Total Harmonic Distortion (THD).

    THD = sqrt(sum of harmonic powers) / fundamental power * 100%

    Args:
        fft_result: FFT analysis result
        fundamental_freq: Fundamental frequency in Hz
        num_harmonics: Number of harmonics to include in THD calculation

    Returns:
        THD as a percentage
    """
    if fundamental_freq <= 0:
        return 0.0

    # Find fundamental component
    freq_resolution = fft_result.sample_rate / (2 * len(fft_result.frequencies))
    tolerance = 2 * freq_resolution  # Allow some frequency bin tolerance

    # Get fundamental magnitude
    fund_mask = np.abs(fft_result.frequencies - fundamental_freq) < tolerance
    if not np.any(fund_mask):
        return 0.0

    fundamental_mag = np.max(fft_result.magnitude[fund_mask])
    fundamental_power = fundamental_mag**2

    # Sum harmonic powers
    harmonic_power_sum = 0.0
    for n in range(2, num_harmonics + 2):  # 2nd through (num_harmonics+1)th harmonic
        harmonic_freq = n * fundamental_freq
        if harmonic_freq > fft_result.frequencies[-1]:
            break  # Beyond Nyquist frequency

        harm_mask = np.abs(fft_result.frequencies - harmonic_freq) < tolerance
        if np.any(harm_mask):
            harmonic_mag = np.max(fft_result.magnitude[harm_mask])
            harmonic_power_sum += harmonic_mag**2

    # Calculate THD percentage
    if fundamental_power == 0:
        return 0.0

    thd = np.sqrt(harmonic_power_sum / fundamental_power) * 100
    return thd


def find_harmonics(
    fft_result: FFTResult, fundamental_freq: float, num_harmonics: int = 5
) -> list:
    """
    Identify harmonic frequencies and their magnitudes.

    Args:
        fft_result: FFT analysis result
        fundamental_freq: Fundamental frequency in Hz
        num_harmonics: Number of harmonics to find (default 5)

    Returns:
        List of dicts with 'harmonic' (int), 'frequency' (Hz),
        'magnitude' (linear), and 'magnitude_db' (dB) keys.
        The first entry (harmonic=1) is the fundamental.
    """
    if fundamental_freq <= 0:
        return []

    freq_resolution = fft_result.sample_rate / (2 * len(fft_result.frequencies))
    tolerance = 2 * freq_resolution

    harmonics = []
    for n in range(1, num_harmonics + 1):
        target_freq = n * fundamental_freq
        if target_freq > fft_result.frequencies[-1]:
            break

        mask = np.abs(fft_result.frequencies - target_freq) < tolerance
        if not np.any(mask):
            continue

        idx = np.argmax(fft_result.magnitude[mask])
        mag = fft_result.magnitude[mask][idx]
        mag_db = fft_result.magnitude_db[mask][idx]
        freq = fft_result.frequencies[mask][idx]

        harmonics.append(
            {
                "harmonic": n,
                "frequency": float(freq),
                "magnitude": float(mag),
                "magnitude_db": float(mag_db),
            }
        )

    return harmonics


def analyze_signal_spectrum(
    time: np.ndarray,
    signal: np.ndarray,
    signal_name: str = "Signal",
    window: str = "hanning",
) -> FFTResult:
    """
    Complete spectral analysis including FFT, fundamental detection, and THD.

    Args:
        time: Time array (seconds)
        signal: Signal amplitude array
        signal_name: Name of the signal
        window: Window function type

    Returns:
        FFTResult with fundamental frequency and THD populated
    """
    # Compute FFT
    fft_result = compute_fft(time, signal, signal_name, window)

    # Find fundamental frequency
    fundamental = find_fundamental_frequency(fft_result)
    fft_result.fundamental_freq = fundamental

    # Compute THD and find harmonics if we found a fundamental
    if fundamental > 0:
        thd = compute_thd(fft_result, fundamental)
        fft_result.thd_percent = thd
        fft_result.harmonics = find_harmonics(fft_result, fundamental)

    return fft_result
