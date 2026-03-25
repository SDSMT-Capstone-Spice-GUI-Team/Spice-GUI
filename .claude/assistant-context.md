# Slack Assistant Context

## Circuit JSON Schema

Analysis params use these exact keys (NOT step_time/stop_time):

```
"analysis_type": "Transient",
"analysis_params": {
    "step": "1n",        # NOT step_time
    "duration": "5u",    # NOT stop_time
    "startTime": 0       # optional
}

"analysis_type": "DC Sweep",
"analysis_params": {
    "source": "V1",
    "min": 0,
    "max": 5,
    "step": 0.1
}

"analysis_type": "AC Sweep",
"analysis_params": {
    "fStart": 1,
    "fStop": 1e6,
    "points": 100,
    "sweepType": "dec"
}

"analysis_type": "DC Operating Point",
"analysis_params": {}
```

## Simulation Performance

Keep total plot data points ≤ 500 to avoid slow rendering. Choose step size
and duration so that `duration / step ≤ 500`. For example:
- 5μs simulation with 10ns steps = 500 points ✓
- 1s simulation with 1ms steps = 1000 points — too many
- 1s simulation with 2ms steps = 500 points ✓

If the user needs high resolution, warn them that large datasets slow down
the waveform plot.

## Validated Circuit Files

All files loaded and simulated successfully:
- MOSFETSwitchedResistor.json ✓
- MOSFETSwitchedMotor.json ✓
- FullWaveRectifierWithSmoothing.json ✓
- RCCircuit.json ✓
- Simple4ResistorCircuit.json ✓
- SeriesDiodeAndResistor.json ✓
- PulseTest.json ✓ (initially used wrong param keys — fixed)
