; Build with Inno Setup 6 on Windows after PyInstaller has generated dist/.
; Result is ONE setup EXE containing the app + Python runtime + bundled libraries.
#define AppName "Ven0m TikTok LIVE Assistant"
#define AppVer "6.3.1-beta"
#define AppExe "Ven0m_TikTok_LIVE_Assistant.exe"
[Setup]
AppId={{A56C55FD-C222-4F76-8A04-CAC26B4135B1}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Ven0m
DefaultDirName={localappdata}\Programs\Ven0mTikTokLIVEAssistant
DefaultGroupName={#AppName}
OutputDir=dist_installer
OutputBaseFilename=Ven0m_TikTok_LIVE_Assistant_Setup_x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExe}
DisableProgramGroupPage=yes
SetupIconFile=assets\branding\ven0m_icon.ico
[Files]
Source: "dist\Ven0m_TikTok_LIVE_Assistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
[Run]
Filename: "{app}\{#AppExe}"; Description: "Run {#AppName}"; Flags: nowait postinstall skipifsilent
