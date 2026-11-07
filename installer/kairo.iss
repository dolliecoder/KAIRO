; Inno Setup script. Build: ISCC.exe installer\kairo.iss  (after build_app.bat has produced dist\KAIRO)
; Per-user install (no admin prompt): lands in %LOCALAPPDATA%\Programs\KAIRO. User data lives in %APPDATA%\KAIRO
; and is never touched by installing, updating or uninstalling.
; The three #ifndef blocks let a test build override the name, id and file name (ISCC /DAppName=... /DAppGuid=...
; /DOutName=...) so a test install never touches a real KAIRO install.

#ifndef AppName
#define AppName "KAIRO"
#endif
#ifndef AppGuid
#define AppGuid "{{42E607F9-DEB8-4715-97E2-280A8C545D86}"
#endif
#ifndef OutName
#define OutName "KAIROSetup"
#endif
#define AppVersion "1.1.0"

[Setup]
AppId={#AppGuid}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Dolly
AppPublisherURL=https://github.com/dolliecoder/KAIRO
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename={#OutName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\KAIRO.exe
SetupIconFile=..\assets\kairo.ico
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "autostart"; Description: "Start KAIRO automatically when Windows starts"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\KAIRO\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\KAIRO.exe"; Comment: "Start KAIRO"
Name: "{autoprograms}\Quit {#AppName}"; Filename: "{app}\KAIRO.exe"; Parameters: "--quit"; Comment: "Stop KAIRO if it is running"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\KAIRO.exe"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\KAIRO.exe"; Tasks: autostart

[Run]
Filename: "{app}\KAIRO.exe"; Description: "Start KAIRO now"; Flags: nowait postinstall skipifsilent
