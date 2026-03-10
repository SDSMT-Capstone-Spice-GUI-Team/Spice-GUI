# Installation Guide

This guide covers installing SDM Spice on Windows, macOS, and Linux.

## Prerequisites

- **Python 3.10 or higher**
- **ngspice** (SPICE simulation engine)
- **Git** (for cloning the repository)

## Step 1: Install ngspice

SDM Spice requires ngspice to be installed separately on your system.

### Windows

1. Download the latest ngspice installer from [ngspice.sourceforge.io](http://ngspice.sourceforge.io/download.html)
2. Run the installer (e.g., `ngspice-XX-64.exe`)
3. During installation, select "Add ngspice to PATH" or manually add the installation directory to your system PATH
4. Default installation path: `C:\Program Files\Spice64\bin`

**Verify installation:**
```cmd
ngspice --version
```

### macOS

Using Homebrew:
```bash
brew install ngspice
```

**Verify installation:**
```bash
ngspice --version
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install ngspice
```

**Verify installation:**
```bash
ngspice --version
```

### Linux (Fedora/RHEL)

```bash
sudo dnf install ngspice
```

## Step 2: Clone the Repository

```bash
git clone https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI.git
cd Spice-GUI
```

## Step 3: Set Up Python Environment

### Create Virtual Environment

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r app/requirements.txt
```

This installs:
- PyQt6 (GUI framework)
- matplotlib (plotting)
- numpy (numerical computing)
- scipy (scientific computing)
- PySpice (SPICE utilities)

## Step 4: Run SDM Spice

```bash
python app/main.py
```

The application window should open with the circuit design interface.

## Troubleshooting

### "ngspice not found" Error

SDM Spice searches for ngspice in common installation paths. If not found:

1. Verify ngspice is installed: `ngspice --version`
2. Add ngspice to your system PATH
3. Restart your terminal/command prompt

**Windows PATH locations checked:**
- `C:\Program Files\Spice64\bin\ngspice.exe`
- `C:\Program Files\ngspice\bin\ngspice.exe`
- `C:\Spice64\bin\ngspice.exe`

### PyQt6 Installation Issues

If PyQt6 fails to install:

```bash
pip install --upgrade pip
pip install PyQt6
```

On Linux, you may need:
```bash
sudo apt install python3-pyqt6
```

### Display Issues on Linux

If you encounter display errors on Linux:

```bash
sudo apt install libxcb-xinerama0
```

### Permission Denied (Linux/macOS)

If you get permission errors:

```bash
chmod +x app/main.py
python app/main.py
```

## Updating SDM Spice

To update to the latest version:

```bash
cd Spice-GUI
git pull origin main
pip install -r app/requirements.txt --upgrade
```

## Uninstalling

1. Delete the `Spice-GUI` directory
2. Optionally remove the virtual environment
3. ngspice can be uninstalled through your system's package manager

## Next Steps

- [[Quick Start Tutorial]] - Learn the basics
- [[User Interface Overview]] - Understand the layout
- [[Components]] - Available circuit components
