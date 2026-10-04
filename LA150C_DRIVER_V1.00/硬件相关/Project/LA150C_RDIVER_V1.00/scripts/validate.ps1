# LA150C RDIVER V1.00 - schema upgrade, ERC, geometry audit and exports.
#
# Usage:
#   pwsh -NoProfile -File .\scripts\validate.ps1            # verify only
#   pwsh -NoProfile -File .\scripts\validate.ps1 -Rebuild   # rebuild first
[CmdletBinding()]
param(
    [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Resolve-KicadCli {
    $candidates = @(@(
        $env:KICAD_CLI,
        'D:\KiCad10.0\bin\kicad-cli.exe',
        'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
    if (-not $candidates) { throw 'kicad-cli.exe not found; set KICAD_CLI' }
    return $candidates[0]
}

function Resolve-Python {
    $candidates = @(@(
        $env:CODEX_PYTHON,
        "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
    if (-not $candidates) { throw 'python.exe not found; set CODEX_PYTHON' }
    return $candidates[0]
}

$KicadCli = Resolve-KicadCli
$Python = Resolve-Python
$env:KICAD_CONFIG_HOME = Join-Path $ProjectRoot '.kicad-config'
$env:PYTHONIOENCODING = 'utf-8'
New-Item -ItemType Directory -Force -Path $env:KICAD_CONFIG_HOME | Out-Null

Write-Host "kicad-cli : $KicadCli"
Write-Host "python    : $Python"

if ($Rebuild) {
    Write-Host "`n=== build_all ===" -ForegroundColor Cyan
    & $Python (Join-Path $PSScriptRoot 'build_all.py')
    if ($LASTEXITCODE -ne 0) { throw 'build_all.py failed' }
}

Write-Host "`n=== kicad-cli sch upgrade --force ===" -ForegroundColor Cyan
Get-ChildItem -LiteralPath $ProjectRoot -Filter '*.kicad_sch' | ForEach-Object {
    & $KicadCli sch upgrade --force $_.FullName | Out-Null
    Write-Host "  upgraded $($_.Name)"
}

Write-Host "`n=== ERC ===" -ForegroundColor Cyan
$ercReport = Join-Path $ProjectRoot 'docs\erc.rpt'
$rootSheet = Join-Path $ProjectRoot 'LA150C_RDIVER_V1.00.kicad_sch'
& $KicadCli sch erc --exit-code-violations -o $ercReport $rootSheet
$ercExit = $LASTEXITCODE
Get-Content -LiteralPath $ercReport -Encoding UTF8 |
    Select-String -Pattern 'ERC messages' |
    ForEach-Object { Write-Host "  $($_.Line.Trim())" }
if ($ercExit -ne 0) { throw "ERC reported violations (see $ercReport)" }

Write-Host "`n=== geometry audit ===" -ForegroundColor Cyan
& $Python (Join-Path $PSScriptRoot 'verify_sheets.py')
if ($LASTEXITCODE -ne 0) { throw 'geometry audit failed' }

Write-Host "`n=== exports ===" -ForegroundColor Cyan
$docs = Join-Path $ProjectRoot 'docs'
$generated = Join-Path $ProjectRoot 'generated'
New-Item -ItemType Directory -Force -Path $docs, $generated | Out-Null
& $KicadCli sch export netlist --output (Join-Path $generated 'LA150C_RDIVER_V1.00.net') $rootSheet | Out-Null
& $KicadCli sch export bom     --output (Join-Path $generated 'LA150C_RDIVER_V1.00_BOM.csv') $rootSheet | Out-Null
& $KicadCli sch export pdf     --output (Join-Path $docs 'LA150C_RDIVER_V1.00.pdf') $rootSheet | Out-Null
Write-Host "  generated/LA150C_RDIVER_V1.00.net"
Write-Host "  generated/LA150C_RDIVER_V1.00_BOM.csv"
Write-Host "  docs/LA150C_RDIVER_V1.00.pdf"

Write-Host "`n=== PDF text check ===" -ForegroundColor Cyan
& $Python (Join-Path $PSScriptRoot 'check_pdf_text.py')
if ($LASTEXITCODE -ne 0) { throw 'PDF text check failed' }

Write-Host "`nG3 校验通过：ERC 0 错误 0 警告，几何与 PDF 检查通过。" -ForegroundColor Green
