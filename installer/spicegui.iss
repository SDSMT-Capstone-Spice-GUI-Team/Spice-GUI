; =========================================================================
; Spice GUI - Inno Setup Installer Script
;
; Build instructions:
;   1. Build the PyInstaller bundle first:
;        python -m PyInstaller SpiceGUI.spec
;
;   2. Compile this script with Inno Setup 6.x:
;        iscc installer/spicegui.iss
;
;   3. Output: installer/Output/SpiceGUI-v0.1.0-win64-setup.exe
;
; The script supports two install modes:
;   - "Install for all users" (requires admin, installs to Program Files)
;   - "Install for current user only" (no admin, installs to LocalAppData)
; =========================================================================

#define MyAppName      "Spice GUI"
#define MyAppVersion        "0.1.0"
#define MyAppNumericVersion "0.1.0"
#define MyAppPublisher "SDSMT Capstone Spice GUI Team"
#define MyAppURL       "https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI"
#define MyAppExeName   "SpiceGUI.exe"

[Setup]
AppId={{8F2C4E6A-3B7D-4A1E-9C5F-D8E6F2A4B1C3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=LICENSE-COMBINED.txt
OutputDir=Output
OutputBaseFilename=SpiceGUI-v{#MyAppVersion}-win64-setup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; Allow non-admin installs (current user only)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstaller settings
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
; Installer version info
VersionInfoVersion={#MyAppNumericVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
; Uncomment when an .ico file is added:
; SetupIconFile=..\app\assets\spicegui.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "fileassoc"; Description: "Associate .spice files with {#MyAppName}"; GroupDescription: "File associations:"; Flags: checkedonce

[Files]
; Copy the entire PyInstaller dist output
Source: "..\dist\SpiceGUI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Licenses
Source: "LICENSE-COMBINED.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
Source: "..\licenses\NGSPICE-LICENSE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; .spice file association (only when the user selects the task)
Root: HKA; Subkey: "Software\Classes\.spice"; ValueType: string; ValueName: ""; ValueData: "SpiceGUI.Circuit"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\SpiceGUI.Circuit"; ValueType: string; ValueName: ""; ValueData: "Spice GUI Circuit"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\SpiceGUI.Circuit\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\SpiceGUI.Circuit\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc

[Run]
; Install VC++ redistributable silently if bundled and missing
Filename: "{app}\redist\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated skipifdoesntexist; Check: NeedsVCRedist
; Launch application after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// =========================================================================
// Pre-flight system validation (#835)
//
// All checks WARN but never block — the user can always proceed.
// =========================================================================

const
  MIN_DISK_MB = 500;
  // Windows 10 = major 10, minor 0, build >= 10240
  MIN_WINDOWS_MAJOR = 10;
  MIN_WINDOWS_MINOR = 0;

// ------------------------------------------------------------------
// Helper: format megabytes with thousands separator
// ------------------------------------------------------------------
function FormatMB(MB: Int64): String;
begin
  Result := IntToStr(MB) + ' MB';
end;

// ------------------------------------------------------------------
// 1. Windows version check (minimum Windows 10)
// ------------------------------------------------------------------
function CheckWindowsVersion: Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  Result := (Version.Major >= MIN_WINDOWS_MAJOR);
end;

// ------------------------------------------------------------------
// 2. Disk space check (warn if < 500 MB free)
// ------------------------------------------------------------------
function GetFreeDiskSpaceMB(Path: String): Int64;
var
  FreeBytes, TotalBytes: Int64;
begin
  if GetSpaceOnDisk64(ExtractFileDrive(Path), FreeBytes, TotalBytes) then
    Result := FreeBytes div (1024 * 1024)
  else
    Result := -1;
end;

// ------------------------------------------------------------------
// 3. Detect previous Spice GUI installations via registry
//    (Inno Setup stores uninstall info under the AppId)
// ------------------------------------------------------------------
function GetPreviousInstallPath: String;
var
  Path: String;
begin
  Result := '';
  // Check HKLM (all-users install)
  if RegQueryStringValue(HKLM,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8F2C4E6A-3B7D-4A1E-9C5F-D8E6F2A4B1C3}_is1',
    'InstallLocation', Path) then
  begin
    Result := Path;
    Exit;
  end;
  // Check HKCU (per-user install)
  if RegQueryStringValue(HKCU,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8F2C4E6A-3B7D-4A1E-9C5F-D8E6F2A4B1C3}_is1',
    'InstallLocation', Path) then
  begin
    Result := Path;
  end;
end;

function GetPreviousVersion: String;
var
  Ver: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8F2C4E6A-3B7D-4A1E-9C5F-D8E6F2A4B1C3}_is1',
    'DisplayVersion', Ver) then
  begin
    Result := Ver;
    Exit;
  end;
  if RegQueryStringValue(HKCU,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8F2C4E6A-3B7D-4A1E-9C5F-D8E6F2A4B1C3}_is1',
    'DisplayVersion', Ver) then
  begin
    Result := Ver;
  end;
end;

// ------------------------------------------------------------------
// 4. Detect existing ngspice installations
// ------------------------------------------------------------------
function FindNgspiceVersion: String;
var
  Path: String;
begin
  Result := '';
  // Check common registry key for ngspice
  if RegQueryStringValue(HKLM,
    'SOFTWARE\ngspice', 'InstallPath', Path) then
  begin
    Result := Path;
    Exit;
  end;
  // Check if ngspice is on PATH
  if FileExists(ExpandConstant('{sys}\ngspice.exe')) then
  begin
    Result := ExpandConstant('{sys}\ngspice.exe');
    Exit;
  end;
  // Check Program Files
  if DirExists(ExpandConstant('{pf}\ngspice')) then
  begin
    Result := ExpandConstant('{pf}\ngspice');
    Exit;
  end;
  if DirExists(ExpandConstant('{pf}\Spice64')) then
  begin
    Result := ExpandConstant('{pf}\Spice64');
  end;
end;

// ------------------------------------------------------------------
// 5. Check for Visual C++ Redistributable (x64)
//    Checks for VC++ 2015-2022 (v14.x) which PyQt6 and ngspice need
// ------------------------------------------------------------------
function IsVCRedistInstalled: Boolean;
var
  Installed: Cardinal;
begin
  Result := False;
  if RegQueryDWordValue(HKLM,
    'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64',
    'Installed', Installed) then
  begin
    Result := (Installed = 1);
  end;
end;

// Check function used by [Run] entry for vc_redist
function NeedsVCRedist: Boolean;
begin
  Result := not IsVCRedistInstalled;
end;

// ------------------------------------------------------------------
// Main pre-flight: runs on InitializeSetup
// ------------------------------------------------------------------
function InitializeSetup: Boolean;
var
  Warnings: String;
  WarningCount: Integer;
  FreeMB: Int64;
  PrevPath, PrevVer, NgspicePath: String;
  Version: TWindowsVersion;
begin
  Result := True;
  Warnings := '';
  WarningCount := 0;

  // 1. Windows version
  if not CheckWindowsVersion then
  begin
    GetWindowsVersionEx(Version);
    WarningCount := WarningCount + 1;
    Warnings := Warnings + #13#10 + #13#10 +
      IntToStr(WarningCount) + '. UNSUPPORTED WINDOWS VERSION' + #13#10 +
      '   Spice GUI requires Windows 10 or later.' + #13#10 +
      '   Detected: Windows ' + IntToStr(Version.Major) + '.' + IntToStr(Version.Minor) + #13#10 +
      '   The application may not work correctly.';
  end;

  // 2. Disk space
  FreeMB := GetFreeDiskSpaceMB(WizardDirValue);
  if (FreeMB >= 0) and (FreeMB < MIN_DISK_MB) then
  begin
    WarningCount := WarningCount + 1;
    Warnings := Warnings + #13#10 + #13#10 +
      IntToStr(WarningCount) + '. LOW DISK SPACE' + #13#10 +
      '   Recommended: at least ' + FormatMB(MIN_DISK_MB) + ' free.' + #13#10 +
      '   Available: ' + FormatMB(FreeMB) + '.' + #13#10 +
      '   Installation may fail or leave insufficient space.';
  end;

  // 3. Previous installation
  PrevPath := GetPreviousInstallPath;
  if PrevPath <> '' then
  begin
    PrevVer := GetPreviousVersion;
    WarningCount := WarningCount + 1;
    if PrevVer <> '' then
      Warnings := Warnings + #13#10 + #13#10 +
        IntToStr(WarningCount) + '. PREVIOUS INSTALLATION DETECTED' + #13#10 +
        '   Spice GUI v' + PrevVer + ' is already installed at:' + #13#10 +
        '   ' + PrevPath + #13#10 +
        '   This installer will upgrade the existing installation.'
    else
      Warnings := Warnings + #13#10 + #13#10 +
        IntToStr(WarningCount) + '. PREVIOUS INSTALLATION DETECTED' + #13#10 +
        '   A previous version is installed at:' + #13#10 +
        '   ' + PrevPath + #13#10 +
        '   This installer will upgrade the existing installation.';
  end;

  // 4. ngspice detection (informational, not a warning)
  NgspicePath := FindNgspiceVersion;

  // 5. VC++ Redistributable
  if not IsVCRedistInstalled then
  begin
    if FileExists(ExpandConstant('{src}\redist\vc_redist.x64.exe')) or
       FileExists(ExpandConstant('{app}\redist\vc_redist.x64.exe')) then
    begin
      // VC++ redist is bundled — will be installed automatically
      // No warning needed
    end
    else
    begin
      WarningCount := WarningCount + 1;
      Warnings := Warnings + #13#10 + #13#10 +
        IntToStr(WarningCount) + '. VISUAL C++ REDISTRIBUTABLE NOT FOUND' + #13#10 +
        '   The Microsoft Visual C++ 2015-2022 Redistributable (x64) is' + #13#10 +
        '   required but was not detected on this system.' + #13#10 +
        '   Download it from: https://aka.ms/vs/17/release/vc_redist.x64.exe';
    end;
  end;

  // Show combined warning dialog if any issues found
  if WarningCount > 0 then
  begin
    Result := (MsgBox(
      'Spice GUI Setup detected ' + IntToStr(WarningCount) + ' potential issue(s):' +
      Warnings + #13#10 + #13#10 +
      'Do you want to continue with the installation anyway?',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON1) = IDYES);
  end;

  // Log ngspice detection result (shown in setup log, not to user)
  if NgspicePath <> '' then
    Log('Pre-flight: existing ngspice found at ' + NgspicePath)
  else
    Log('Pre-flight: no existing ngspice installation detected');
end;
