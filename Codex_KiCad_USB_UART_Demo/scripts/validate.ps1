[CmdletBinding()]
param(
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'

function Resolve-KiCadRoot {
    $candidates = @(
        'D:\KiCad10.0',
        'C:\Program Files\KiCad\10.0'
    )

    foreach ($candidate in $candidates) {
        $cli = Join-Path $candidate 'bin\kicad-cli.exe'
        if (Test-Path -LiteralPath $cli) {
            return $candidate
        }
    }

    throw 'KiCad 10 installation was not found.'
}

$kicadRoot = Resolve-KiCadRoot
$cli = Join-Path $kicadRoot 'bin\kicad-cli.exe'
$python = Join-Path $kicadRoot 'bin\python.exe'

$hardwareDir = Join-Path $ProjectDir 'hardware\USB_UART_Bridge'
$generatedDir = Join-Path $ProjectDir 'generated'
$reportsDir = Join-Path $ProjectDir 'reports'
$manufacturingDir = Join-Path $ProjectDir 'manufacturing'
$configDir = Join-Path $ProjectDir '.kicad-config'

New-Item -ItemType Directory -Path $generatedDir, $reportsDir, $manufacturingDir, $configDir -Force | Out-Null
$env:KICAD_CONFIG_HOME = $configDir

$schematic = Join-Path $hardwareDir 'USB_UART_Bridge.kicad_sch'
$board = Join-Path $hardwareDir 'USB_UART_Bridge.kicad_pcb'
$drawingSheet = Join-Path $hardwareDir 'AD_Style_A4.kicad_wks'
$failed = $false

Write-Host "KiCad root: $kicadRoot"

if (-not (Test-Path -LiteralPath $drawingSheet)) {
    throw "Schematic drawing sheet not found: $drawingSheet"
}

if (Test-Path -LiteralPath $python) {
    & $python (Join-Path $ProjectDir 'scripts\check_schematic_grid.py')
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }
}

if (Test-Path -LiteralPath $schematic) {
    & $cli sch erc --format json --severity-all --exit-code-violations `
        -o (Join-Path $reportsDir 'erc.json') $schematic
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }

    & $cli sch export netlist `
        -o (Join-Path $generatedDir 'USB_UART_Bridge.net') $schematic
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }

    & $cli sch export bom `
        --fields 'Reference,Value,Footprint,QUANTITY,DNP' `
        --labels 'Refs,Value,Footprint,Qty,DNP' `
        --group-by 'Value,Footprint' `
        --sort-field 'Reference' `
        -o (Join-Path $generatedDir 'USB_UART_Bridge_BOM.csv') $schematic
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }

    & $cli sch export pdf `
        --drawing-sheet $drawingSheet `
        -o (Join-Path $manufacturingDir 'USB_UART_Bridge.pdf') $schematic
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }
}
else {
    Write-Host "Schematic not present yet: $schematic"
}

if (Test-Path -LiteralPath $board) {
    $gerberDir = Join-Path $manufacturingDir 'gerbers'
    New-Item -ItemType Directory -Path $gerberDir -Force | Out-Null

    & $cli pcb drc --schematic-parity --refill-zones --save-board `
        --format json --severity-all --exit-code-violations `
        -o (Join-Path $reportsDir 'drc.json') $board
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }

    & $cli pcb export gerbers --board-plot-params -o $gerberDir $board
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }

    & $cli pcb export drill -o $gerberDir $board
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }

    & $cli pcb render --side top --quality high `
        -o (Join-Path $manufacturingDir 'top.png') $board
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }
}
else {
    Write-Host "PCB not present yet: $board"
}

if (Test-Path -LiteralPath $python) {
    & $python -c "import pcbnew; print('pcbnew', pcbnew.GetBuildVersion())"
    if ($LASTEXITCODE -ne 0) {
        $failed = $true
    }
}

if ($failed) {
    throw 'One or more KiCad validation steps failed.'
}

Write-Host 'All available KiCad validation steps passed.'
