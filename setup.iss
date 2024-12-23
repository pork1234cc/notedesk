#define MyAppName "久久便签"
#define MyAppVersion "1.0"
#define MyAppPublisher "微信779059811"
#define MyAppExeName "久久便签.exe"

[Setup]
AppId={{8B8B4F1F-1234-4321-9876-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=久久便签_安装程序
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
LanguageDetectionMethod=locale

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Messages]
chinesesimplified.BeveledLabel=简体中文
chinesesimplified.ButtonNext=下一步(&N)
chinesesimplified.ButtonBack=上一步(&B)
chinesesimplified.ButtonCancel=取消(&C)
chinesesimplified.ButtonInstall=安装(&I)
chinesesimplified.ButtonFinish=完成(&F)
chinesesimplified.SetupWindowTitle=安装 - %1
chinesesimplified.SelectDirLabel3=安装程序将安装 [name] 到下列文件夹。
chinesesimplified.SelectDirBrowseLabel=点击"下一步"继续。如果要选择其他文件夹，请点击"浏览"。

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "创建快速启动栏图标"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
Source: "dist\久久便签\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ChineseSimplified.isl"; Flags: dontcopy

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent