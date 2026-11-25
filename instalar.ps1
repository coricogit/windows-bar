# Instala Windows Bar sin ningun .exe sin firmar:
#
#   irm https://raw.githubusercontent.com/coricogit/windows-bar/main/instalar.ps1 | iex
#
# Descarga el ultimo release, comprueba su SHA-256 con el que publica GitHub y copia
# la barra en %LOCALAPPDATA%\Programs\Windows Bar. No pide administrador.
# Todos los ejecutables que lleva van firmados por sus autores (Python y Qt).

& {
  $ErrorActionPreference = 'Stop'
  $ProgressPreference = 'SilentlyContinue'
  $temp = Join-Path $env:TEMP 'windows-bar-instalar'
  try {
    Write-Host 'Windows Bar oculta la barra de Windows mientras esta abierta y pregunta a GitHub cada 6 horas si hay version nueva.'
    Write-Host 'Privacidad: https://github.com/coricogit/windows-bar/blob/main/PRIVACIDAD.md'
    Write-Host 'Buscando la ultima version...'
    $release = Invoke-RestMethod 'https://api.github.com/repos/coricogit/windows-bar/releases/latest' -UseBasicParsing
    $zip = $release.assets | Where-Object { $_.name -like 'Windows-Bar-*.zip' } | Select-Object -First 1
    if (-not $zip -or $zip.digest -notlike 'sha256:*') { throw 'El ultimo release no trae el .zip.' }
    if ($zip.browser_download_url -notlike 'https://github.com/coricogit/windows-bar/releases/download/*') { throw 'Direccion inesperada.' }
    if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
    New-Item $temp -ItemType Directory | Out-Null
    $archivo = Join-Path $temp 'barra.zip'
    Write-Host "Descargando $($zip.name)..."
    Invoke-WebRequest $zip.browser_download_url -OutFile $archivo -UseBasicParsing
    # certutil y tar son de Windows y van tambien con PowerShell restringido.
    $hash = (& "$env:SystemRoot\System32\certutil.exe" -hashfile $archivo SHA256)[1] -replace '\s', ''
    if ("sha256:$hash" -ne $zip.digest) { throw 'La descarga no coincide con la publicada.' }
    $carpeta = Join-Path $temp 'barra'
    New-Item $carpeta -ItemType Directory | Out-Null
    & "$env:SystemRoot\System32\tar.exe" -xf $archivo -C $carpeta
    if ($LASTEXITCODE) { throw 'No se pudo descomprimir.' }
    Write-Host 'Instalando...'
    & (Join-Path $carpeta 'python\python.exe') (Join-Path $carpeta 'barra\instalado.py') --instalar
    if ($LASTEXITCODE) { throw "La instalacion no termino (codigo $LASTEXITCODE)." }
    Write-Host 'Listo. Clic derecho en el reloj de la barra: temas y ajustes. Ctrl+Alt+Mayus+B: volver a la de Windows.'
  }
  finally {
    if (Test-Path $temp) { Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue }
  }
}
