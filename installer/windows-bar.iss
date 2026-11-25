; Instalador de Windows Bar (Inno Setup 6). Lo crea installer/build.py, que pasa
; Version, Stage (la carpeta que se empaqueta) y Out.

#define Py "{app}\python\python.exe"
#define Ayuda "{app}\barra\instalado.py"

[Setup]
AppId={{B0A9C1D4-6E37-4C52-9F0B-2B7B5C3E8A61}
AppName=Windows Bar
AppVersion={#Version}
AppVerName=Windows Bar {#Version}
AppPublisher=coricogit
AppPublisherURL=https://github.com/coricogit/windows-bar
AppSupportURL=https://github.com/coricogit/windows-bar/issues
VersionInfoVersion={#Version}
VersionInfoProductName=Windows Bar
VersionInfoProductVersion={#Version}
; Qué cambia en el equipo y con quién se conecta.
InfoBeforeFile=antes.txt
; Solo para ti: sin administrador y sin nada fuera de tu perfil.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\Windows Bar
; Al actualizar se limpian sus subcarpetas: la carpeta no se elige.
DisableDirPage=yes
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
SetupIconFile={#Stage}\windows-bar.ico
UninstallDisplayIcon={app}\windows-bar.ico
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; El código de abajo cierra la barra.
CloseApplications=no
OutputDir={#Out}
OutputBaseFilename=Windows-Bar-Setup-{#Version}

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
es.Autostart=Abrir Windows Bar al iniciar sesión
es.Restore=Restaurar barra de Windows
es.InUse=Los archivos de Windows Bar están en uso. Cierra la barra (clic derecho en el reloj > Salir) y vuelve a ejecutar este instalador.

[Messages]
es.FinishedLabel=Windows Bar está instalado.%n%nClic derecho en el reloj de la barra: temas y ajustes.%n%nPara volver a la barra de Windows en cualquier momento, pulsa Ctrl+Alt+Mayús+B.
es.FinishedLabelNoIcons=Windows Bar está instalado.%n%nClic derecho en el reloj de la barra: temas y ajustes.%n%nPara volver a la barra de Windows en cualquier momento, pulsa Ctrl+Alt+Mayús+B.

[Tasks]
Name: "autostart"; Description: "{cm:Autostart}"

[Files]
Source: "{#Stage}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Windows Bar"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\barra.pyw"""; WorkingDir: "{app}"; IconFilename: "{app}\windows-bar.ico"
Name: "{autoprograms}\{cm:Restore}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\barra\vigilante.py"" --restaurar"; WorkingDir: "{app}"; IconFilename: "{app}\windows-bar.ico"

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\barra.pyw"""; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,Windows Bar}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{#Py}"; Parameters: """{#Ayuda}"" --quitar"; Flags: runhidden waituntilterminated; RunOnceId: "Quitar"

[UninstallDelete]
; Los compilados de Python.
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\barra"
Type: filesandordirs; Name: "{app}\claudito"
Type: filesandordirs; Name: "{app}\lib"
Type: filesandordirs; Name: "{app}\qml"
Type: filesandordirs; Name: "{app}\temas"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\*.old"
Type: dirifempty; Name: "{app}"

[Code]
// La versión anterior se aparta, sin borrarla, hasta que la nueva está puesta:
// si algo falla, vuelve a su sitio.
const
  LastPart = 7;

var
  AppDir: String;
  Moved, Installed: Boolean;

// La ejecuta la propia barra (barra/actualizar.py), sin nadie delante.
function Updating: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE|0}') = '1';
end;

function Part(I: Integer): String;
begin
  case I of
    0: Result := 'python';
    1: Result := 'barra';
    2: Result := 'qml';
    3: Result := 'temas';
    4: Result := 'lib';
    5: Result := 'barra.pyw';
    6: Result := 'claudito';
  else
    Result := 'version.txt';
  end;
  Result := AppDir + '\' + Result;
end;

function Exists(Path: String): Boolean;
begin
  Result := FileExists(Path) or DirExists(Path);
end;

procedure Remove(Path: String);
begin
  if DirExists(Path) then
    DelTree(Path, True, True, True)
  else if FileExists(Path) then
    DeleteFile(Path);
end;

procedure PutBack;
var
  I: Integer;
begin
  for I := 0 to LastPart do
    if Exists(Part(I) + '.old') then
    begin
      Remove(Part(I));
      if not RenameFile(Part(I) + '.old', Part(I)) then
        Log('No se pudo devolver ' + Part(I));
    end;
end;

// Si un archivo está en uso, deja todo como estaba y devuelve False.
function MoveAway: Boolean;
var
  I: Integer;
begin
  Result := True;
  for I := 0 to LastPart do
    if Exists(Part(I)) then
    begin
      Remove(Part(I) + '.old');
      if not RenameFile(Part(I), Part(I) + '.old') then
      begin
        Log('En uso: ' + Part(I));
        PutBack;
        Result := False;
        exit;
      end;
    end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code, Attempt: Integer;
begin
  Result := '';
  AppDir := ExpandConstant('{app}');
  // Hay una versión anterior: sus archivos están en uso.
  if FileExists(ExpandConstant('{#Ayuda}')) then
    Exec(ExpandConstant('{#Py}'), ExpandConstant('"{#Ayuda}" --parar'), '', SW_HIDE, ewWaitUntilTerminated, Code);
  for Attempt := 1 to 40 do
  begin
    Moved := MoveAway;
    if Moved then
      exit;
    Sleep(500);
  end;
  Result := CustomMessage('InUse');
end;

procedure DeinitializeSetup;
var
  I, Code: Integer;
  Dir: String;
begin
  if Moved then
    if Installed then
      for I := 0 to LastPart do
        Remove(Part(I) + '.old')
    else
      PutBack;
  if Updating then
  begin
    // La versión nueva, o la de antes si falló.
    Dir := ExpandConstant('{param:DIR}');
    Exec(Dir + '\python\pythonw.exe', '"' + Dir + '\barra.pyw"', Dir, SW_SHOWNORMAL, ewNoWait, Code);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
  Params: String;
begin
  if CurStep <> ssPostInstall then
    exit;
  Installed := True;
  if Updating then
    exit;                  // el arranque pudo cambiarse en el menú: no se toca
  // --parar: otra copia abierta (la del código) no dejaría abrir esta.
  Params := ExpandConstant('"{#Ayuda}" --parar --arranque ');
  if WizardIsTaskSelected('autostart') then
    Params := Params + 'si'
  else
    Params := Params + 'no';
  Exec(ExpandConstant('{#Py}'), Params, '', SW_HIDE, ewWaitUntilTerminated, Code);
end;
