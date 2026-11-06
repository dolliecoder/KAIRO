; Inno Setup script. Build: ISCC.exe installer\echo.iss  (after build_app.bat has produced dist\Echo)
; Per-user install (no admin prompt): lands in %LOCALAPPDATA%\Programs\Echo. User data lives in %APPDATA%\Echo
; and is never touched by installing, updating or uninstalling.

#define AppName "Echo"
#define AppVersion "1.0.0"

[Setup]
AppId={{42E607F9-DEB8-4715-97E2-280A8C545D86}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Dolly
AppPublisherURL=https://github.com/dolliecoder/KAIRO
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=EchoSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Echo.exe
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "autostart"; Description: "Start Echo automatically when Windows starts"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\Echo\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Echo.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Echo.exe"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\Echo.exe"; Tasks: autostart

[Run]
Filename: "{app}\Echo.exe"; Description: "Start Echo now"; Flags: nowait postinstall skipifsilent
