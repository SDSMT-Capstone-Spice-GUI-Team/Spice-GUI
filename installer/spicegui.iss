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
#define MyAppVersion   "0.1.0"
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
VersionInfoVersion={#MyAppVersion}.0
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
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
