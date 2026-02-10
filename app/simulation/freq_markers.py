"""Frequency response marker computation for AC sweep Bode plots.

Detects key characteristics: -3dB cutoff, bandwidth, unity-gain frequency,
gain margin, and phase margin from AC sweep magnitude/phase data.
"""

import numpy as np


def _find_crossing(x_data, y_data, threshold):
    """Find x value(s) where y_data crosses a threshold via linear interpolation.

    Returns a list of crossing x-values (may be empty).
    """
    crossings = []
    for i in range(len(y_data) - 1):
        y0, y1 = y_data[i], y_data[i + 1]
        if (y0 - threshold) * (y1 - threshold) <= 0 and y0 != y1:
            # Linear interpolation
            frac = (threshold - y0) / (y1 - y0)
            x_cross = x_data[i] + frac * (x_data[i + 1] - x_data[i])
            crossings.append(x_cross)
    return crossings


def compute_markers(frequencies, magnitude, phase=None):
    """Compute frequency response markers from AC sweep data.

    Args:
        frequencies: list of frequency values (Hz)
        magnitude: list of magnitude values (linear scale, e.g. V/V)
        phase: optional list of phase values (degrees)

    Returns:
        dict with computed markers:
            cutoff_3db: list of -3dB frequency crossings
            bandwidth: bandwidth between first two -3dB points (or None)
            peak_freq: frequency of peak gain
            peak_gain_db: peak gain in dB
            unity_gain_freq: frequency where gain = 0dB (or None)
            gain_margin_db: gain margin in dB (or None)
            phase_margin_deg: phase margin in degrees (or None)
            ref_level_db: reference level (peak gain in dB)
    """
    if len(frequencies) < 2 or len(magnitude) < 2:
        return _empty_markers()

    freqs = np.array(frequencies, dtype=float)
    mag = np.array(magnitude, dtype=float)

    # Convert to dB, avoiding log of zero
    mag_clipped = np.clip(mag, 1e-30, None)
    mag_db = 20.0 * np.log10(mag_clipped)

    # Peak gain
    peak_idx = int(np.argmax(mag_db))
    peak_gain_db = float(mag_db[peak_idx])
    peak_freq = float(freqs[peak_idx])

    # -3dB level relative to peak
    level_3db = peak_gain_db - 3.0

    # Find -3dB crossings
    cutoff_3db = _find_crossing(freqs.tolist(), mag_db.tolist(), level_3db)

    # Bandwidth: distance between first two -3dB crossings
    bandwidth = None
    if len(cutoff_3db) >= 2:
        bandwidth = cutoff_3db[-1] - cutoff_3db[0]

    # Unity gain frequency: where magnitude = 1.0 (0 dB)
    unity_gain_freq = None
    unity_crossings = _find_crossing(freqs.tolist(), mag_db.tolist(), 0.0)
    if unity_crossings:
        unity_gain_freq = unity_crossings[0]

    # Gain margin and phase margin (require phase data)
    gain_margin_db = None
    phase_margin_deg = None

    if phase is not None and len(phase) == len(frequencies):
        ph = np.array(phase, dtype=float)

        # Phase margin: 180 + phase at unity-gain frequency
        if unity_gain_freq is not None:
            phase_at_ugf = float(np.interp(unity_gain_freq, freqs, ph))
            phase_margin_deg = 180.0 + phase_at_ugf

        # Gain margin: negative of gain (in dB) at phase = -180 crossing
        phase_crossings = _find_crossing(freqs.tolist(), ph.tolist(), -180.0)
        if phase_crossings:
            gain_at_180 = float(np.interp(phase_crossings[0], freqs, mag_db))
            gain_margin_db = -gain_at_180

    return {
        "cutoff_3db": cutoff_3db,
        "bandwidth": bandwidth,
        "peak_freq": peak_freq,
        "peak_gain_db": peak_gain_db,
        "unity_gain_freq": unity_gain_freq,
        "gain_margin_db": gain_margin_db,
        "phase_margin_deg": phase_margin_deg,
        "ref_level_db": level_3db,
    }


def _empty_markers():
    """Return an empty markers dict."""
    return {
        "cutoff_3db": [],
        "bandwidth": None,
        "peak_freq": None,
        "peak_gain_db": None,
        "unity_gain_freq": None,
        "gain_margin_db": None,
        "phase_margin_deg": None,
        "ref_level_db": None,
    }


def format_frequency(freq_hz):
    """Format a frequency value with appropriate SI prefix."""
    if freq_hz is None:
        return "N/A"
    if freq_hz >= 1e9:
        return f"{freq_hz / 1e9:.2f} GHz"
    elif freq_hz >= 1e6:
        return f"{freq_hz / 1e6:.2f} MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz / 1e3:.2f} kHz"
    else:
        return f"{freq_hz:.2f} Hz"
