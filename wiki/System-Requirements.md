# System Requirements

Hardware and software requirements for running SDM Spice.

## Software Requirements

### Operating System

| OS | Minimum Version | Recommended |
|----|-----------------|-------------|
| Windows | Windows 10 (64-bit) | Windows 11 |
| macOS | 10.14 (Mojave) | 12 (Monterey)+ |
| Linux | Ubuntu 20.04 LTS | Ubuntu 22.04 LTS |

**Other Linux distributions** should work if they support Python 3.10+ and Qt6.

### Python

| Requirement | Version |
|-------------|---------|
| Minimum | Python 3.10 |
| Recommended | Python 3.12+ |

### ngspice

| Requirement | Version |
|-------------|---------|
| Minimum | ngspice 36 |
| Recommended | ngspice 42+ |

ngspice must be installed separately and accessible via system PATH.

## Hardware Requirements

### Minimum Specifications

| Component | Requirement |
|-----------|-------------|
| **Processor** | Intel Core i3 / AMD Ryzen 3 or equivalent |
| **RAM** | 4 GB |
| **Storage** | 500 MB available space |
| **Display** | 1280 x 720 resolution |
| **Graphics** | Integrated graphics sufficient |

### Recommended Specifications

| Component | Requirement |
|-----------|-------------|
| **Processor** | Intel Core i5 / AMD Ryzen 5 or equivalent |
| **RAM** | 8 GB |
| **Storage** | 1 GB available space (SSD preferred) |
| **Display** | 1920 x 1080 resolution |
| **Graphics** | Integrated or discrete |

### For Large Simulations

| Component | Requirement |
|-----------|-------------|
| **Processor** | Intel Core i7 / AMD Ryzen 7 or equivalent |
| **RAM** | 16 GB |
| **Storage** | 2 GB available space (SSD) |

Large transient simulations with many data points benefit from additional RAM and faster storage.

## Display Requirements

### Resolution

| Requirement | Resolution |
|-------------|------------|
| Minimum | 1280 x 720 (720p) |
| Recommended | 1920 x 1080 (1080p) |
| Optimal | 2560 x 1440 (1440p) |

### Scaling

SDM Spice supports high-DPI displays through Qt6. For best results:
- Windows: Use 100%, 125%, or 150% scaling
- macOS: Retina displays fully supported
- Linux: Set appropriate DPI in Qt settings

## Network Requirements

### Phase 1 (Current)
No network connection required. SDM Spice works entirely offline.

### Future Phases
When cloud features are added:
- Broadband internet connection
- HTTPS (port 443) access

## Storage Space Breakdown

| Item | Size |
|------|------|
| Python installation | ~100 MB |
| Virtual environment | ~400 MB |
| SDM Spice application | ~50 MB |
| Simulation output files | Variable |
| **Total (typical)** | ~600 MB |

## Compatibility Notes

### Windows

- Windows Defender may scan the application on first run
- PowerShell or Command Prompt for installation
- ngspice typically installs to `C:\Program Files\Spice64`

### macOS

- Gatekeeper may require approval on first run
- Homebrew recommended for ngspice installation
- Terminal.app or iTerm2 for installation

### Linux

- Standard package manager for ngspice
- May need `libxcb-xinerama0` for Qt6 on some distributions
- Desktop environment with X11 or Wayland

## Virtual Machine Support

SDM Spice can run in virtual machines with:
- 3D acceleration enabled (recommended)
- Sufficient RAM allocation (4 GB minimum)
- Display resolution configured appropriately

Tested on:
- VMware Workstation/Fusion
- VirtualBox
- Parallels Desktop

## Performance Guidelines

### Circuit Complexity

| Circuit Size | Components | Expected Performance |
|--------------|------------|---------------------|
| Small | < 20 | Instant simulation |
| Medium | 20-100 | < 5 seconds |
| Large | 100-500 | < 30 seconds |
| Very Large | 500+ | May require patience |

### Transient Analysis

| Duration | Time Step | Data Points | Memory |
|----------|-----------|-------------|--------|
| 1 ms | 1 µs | 1,000 | Low |
| 10 ms | 1 µs | 10,000 | Low |
| 100 ms | 1 µs | 100,000 | Medium |
| 1 s | 1 µs | 1,000,000 | High |

For long simulations, consider:
- Increasing time step
- Using appropriate start time to skip initial transients
- Closing other applications

## Troubleshooting

### "Not enough memory"
- Close other applications
- Reduce simulation duration or increase time step
- Upgrade RAM

### "Display issues"
- Update graphics drivers
- Adjust display scaling
- Try different Qt platform plugin (`QT_QPA_PLATFORM=xcb` on Linux)

### "Slow performance"
- Check available RAM
- Close background applications
- Use SSD for file operations

## See Also

- [[Installation Guide]] - Step-by-step setup
- [[Technology Stack]] - Technical details
- [[Troubleshooting]] - Common issues
