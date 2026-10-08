param([switch]$SomenteBanco)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    $pythonCandidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe')
    )
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notmatch 'WindowsApps') { $pythonCandidates = @($pythonCommand.Source) + $pythonCandidates }
    $pythonExecutable = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($pythonExecutable) {
        & $pythonExecutable -m venv .venv
    } else {
        $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($pyLauncher) { & $pyLauncher.Source -3 -m venv .venv }
    }
    if (-not (Test-Path -LiteralPath $venvPython)) { throw 'Instale Python 3.10 ou superior e execute este arquivo novamente.' }
}
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências. Verifique a internet.' }
if ($SomenteBanco) {
    & $venvPython scripts\portable_postgres.py --somente-banco
} else {
    & $venvPython scripts\portable_postgres.py
}
if ($LASTEXITCODE -ne 0) { throw 'A aplicação encerrou com erro. Verifique a mensagem acima.' }
