; Inno Setup script for Splatinator.
;
; Build the executable first:      python build_exe.py
; Then compile this script with Inno Setup 6 (https://jrsoftware.org/isdl.php)
; to get Splatinator-Setup.exe - a normal Windows installer with Start Menu
; and desktop shortcuts. COLMAP and Brush are still fetched on first launch,
; which keeps the installer small.

#define AppName    "Splatinator"
#define AppVersion "2.0"
#define AppExe     "Splatinator.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Abhigyan Mohanty
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=Splatinator-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Per-user install needs no administrator rights.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md";      DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}";      Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
