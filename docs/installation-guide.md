# Spice GUI Installation Guide (Windows)

This guide covers downloading, installing, and troubleshooting Spice GUI on Windows 10 and Windows 11.

## System Requirements

### Minimum

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10 (version 1903 or later) |
| **CPU** | Intel i3 / AMD Ryzen 3 (x64) |
| **RAM** | 4 GB |
| **Disk** | 500 MB free space |
| **Display** | 1280 x 720 |

### Recommended

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 11 |
| **CPU** | Intel i5 / AMD Ryzen 5 |
| **RAM** | 8 GB |
| **Disk** | 1 GB free space |
| **Display** | 1920 x 1080 |

### Prerequisites

- **Visual C++ Redistributable 2015-2022 (x64)** — the installer will attempt to install this automatically if it is bundled; otherwise you can download it from [Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe).
- **ngspice** — bundled with the installer. If you have an existing ngspice installation, the app will detect it and let you choose which copy to use.

## Downloading Spice GUI

1. Go to the [Releases page](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/releases).
2. Under the latest release, download the file named **`SpiceGUI-vX.Y.Z-win64-setup.exe`** (where X.Y.Z is the version number).
3. Save the file to a convenient location such as your Downloads folder.

## Installation Steps

### Step 1: Run the Installer

Double-click the downloaded `SpiceGUI-vX.Y.Z-win64-setup.exe` file.

![installer step screenshot](screenshots/step-1-run-installer.png)

### Step 2: Windows SmartScreen Warning

Because the installer is not code-signed, Windows SmartScreen may show a warning:

1. Click **"More info"** on the SmartScreen dialog.
2. Click **"Run anyway"**.

This is normal for unsigned software and does not indicate a security problem with Spice GUI.

![installer step screenshot](screenshots/step-2-smartscreen.png)

### Step 3: Pre-flight Checks

The installer runs automatic system checks. If any issues are found (e.g., low disk space, missing VC++ runtime), a dialog will appear listing the warnings. You can click **Yes** to proceed anyway or **No** to cancel.

![installer step screenshot](screenshots/step-3-preflight.png)

### Step 4: License Agreement

Read the license agreement and select **"I accept the agreement"** to continue.

![installer step screenshot](screenshots/step-4-license.png)

### Step 5: Choose Install Mode

The installer offers two modes:

- **Install for all users** — requires administrator privileges, installs to `C:\Program Files\Spice GUI`
- **Install for current user only** — no admin needed, installs to your local AppData folder

Choose the appropriate option for your situation.

![installer step screenshot](screenshots/step-5-install-mode.png)

### Step 6: Select Installation Directory

Accept the default directory or click **Browse** to choose a different location.

![installer step screenshot](screenshots/step-6-directory.png)

### Step 7: Additional Options

- **Create a desktop icon** — optional shortcut on your desktop
- **Associate .spice files** — lets you double-click `.spice` files to open them in Spice GUI

![installer step screenshot](screenshots/step-7-options.png)

### Step 8: Install

Click **Install** to begin copying files. The installer will also install the Visual C++ Redistributable if it is needed.

![installer step screenshot](screenshots/step-8-installing.png)

### Step 9: Launch

Check the **"Launch Spice GUI"** box and click **Finish** to start the application.

![installer step screenshot](screenshots/step-9-finish.png)

## Switching Between Bundled and System ngspice

Spice GUI ships with a bundled copy of ngspice. If you also have ngspice installed on your system, the application will detect both and let you choose:

1. Open Spice GUI.
2. Go to **Edit > Preferences** (or the settings/preferences menu).
3. Under the **Simulation** section, select the ngspice binary to use:
   - **Bundled** — uses the copy shipped with Spice GUI (recommended for most users)
   - **System** — uses the ngspice found on your system PATH or the path you specify
4. Click **OK** to save your preference.

The bundled version is tested for compatibility with this release. Use the system version only if you need a specific ngspice feature or version.

## Uninstalling

### Via Windows Settings

1. Open **Settings > Apps > Apps & features** (Windows 10) or **Settings > Apps > Installed apps** (Windows 11).
2. Search for **"Spice GUI"**.
3. Click **Uninstall** and follow the prompts.

### Via Start Menu

1. Open the **Start Menu**.
2. Find the **Spice GUI** folder.
3. Click **Uninstall Spice GUI**.

### Via Control Panel

1. Open **Control Panel > Programs > Programs and Features**.
2. Select **Spice GUI**.
3. Click **Uninstall**.

The uninstaller removes all application files. Your saved circuit files (`.spice`) are not deleted.

## Troubleshooting

### "App won't start" — Missing Visual C++ Runtime

**Symptoms:** Double-clicking SpiceGUI.exe shows an error about missing DLLs (`MSVCP140.dll`, `VCRUNTIME140.dll`, or similar), or the app closes immediately.

**Solution:**
1. Download the [Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe) from Microsoft.
2. Run the installer.
3. Restart your computer.
4. Try launching Spice GUI again.

### "App won't start" — Antivirus Blocking

**Symptoms:** The app is deleted or quarantined by antivirus software after installation.

**Solution:**
1. Open your antivirus software.
2. Check the quarantine/threat history for `SpiceGUI.exe`.
3. Restore the file and add an exclusion for the Spice GUI installation folder (e.g., `C:\Program Files\Spice GUI\`).
4. If using Windows Defender:
   - Open **Windows Security > Virus & threat protection > Protection history**.
   - Find the blocked item and select **Allow on device**.

### "Simulations fail" — ngspice Path Issue

**Symptoms:** Running a simulation shows an error like "ngspice not found" or "simulation engine unavailable".

**Solution:**
1. Open **Edit > Preferences** in Spice GUI.
2. Check that the ngspice path is set correctly:
   - If using the bundled copy, ensure it points to the `ngspice\bin` folder inside the Spice GUI installation directory.
   - If using a system installation, verify the path exists and the `ngspice.exe` file is present.
3. If ngspice is installed but not detected, ensure it is on your system PATH:
   - Open **Settings > System > About > Advanced system settings > Environment Variables**.
   - Under **System variables**, find `Path` and add the directory containing `ngspice.exe`.

### "Windows SmartScreen warning" — Unsigned Installer

**Symptoms:** A blue dialog says "Windows protected your PC" when running the installer.

**Solution:**
This warning appears because the installer is not digitally signed. It is safe to proceed:
1. Click **"More info"**.
2. Click **"Run anyway"**.

This is expected behavior for open-source software distributed without a code-signing certificate.

### "Permission denied" — Install Location

**Symptoms:** The installer fails with an access denied or permission error.

**Solution:**
- **If installing to Program Files:** Right-click the installer and select **Run as administrator**.
- **If you don't have admin access:** Run the installer normally and choose **"Install for current user only"** when prompted. This installs to your user profile and does not require admin privileges.

## Getting Help

If you encounter an issue not covered here:

1. Check the [GitHub Issues](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues) page for known problems.
2. Open a new issue with:
   - Your Windows version (Settings > System > About)
   - The Spice GUI version (shown in the title bar or Help > About)
   - Steps to reproduce the problem
   - Any error messages or screenshots
