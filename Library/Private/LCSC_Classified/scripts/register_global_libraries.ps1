param(
    [string]$LibraryRoot = (Join-Path $PSScriptRoot '..\libraries'),
    [string]$KiCadConfigRoot = (Join-Path $env:APPDATA 'kicad\10.0')
)

$ErrorActionPreference = 'Stop'

$LibraryRoot = (Resolve-Path -LiteralPath $LibraryRoot).Path
$KiCadConfigRoot = (Resolve-Path -LiteralPath $KiCadConfigRoot).Path
$SymbolTablePath = Join-Path $KiCadConfigRoot 'sym-lib-table'
$FootprintTablePath = Join-Path $KiCadConfigRoot 'fp-lib-table'

if (-not (Test-Path -LiteralPath $SymbolTablePath)) {
    throw "KiCad symbol table not found: $SymbolTablePath"
}
if (-not (Test-Path -LiteralPath $FootprintTablePath)) {
    throw "KiCad footprint table not found: $FootprintTablePath"
}

$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item -LiteralPath $SymbolTablePath -Destination "$SymbolTablePath.backup-$Timestamp" -Force
Copy-Item -LiteralPath $FootprintTablePath -Destination "$FootprintTablePath.backup-$Timestamp" -Force

function Convert-ToKiCadPath {
    param([string]$Path)
    return $Path.Replace('\', '/')
}

function Add-LibraryEntries {
    param(
        [string]$TablePath,
        [string]$EntryKind,
        [System.Collections.IEnumerable]$Libraries
    )

    $content = [System.IO.File]::ReadAllText($TablePath, [System.Text.Encoding]::UTF8)
    $added = [System.Collections.Generic.List[string]]::new()
    $skipped = [System.Collections.Generic.List[string]]::new()
    $entries = [System.Collections.Generic.List[string]]::new()

    foreach ($library in $Libraries) {
        $name = $library.Name
        if ($content -match ('\(name\s+"' + [regex]::Escape($name) + '"\s*\)')) {
            $skipped.Add($name)
            continue
        }

        $uri = Convert-ToKiCadPath $library.Uri
        $entries.Add(
            "`t(lib (name `"$name`") (type `"KiCad`") (uri `"$uri`") (options `"`") (descr `"LCSC classified $EntryKind library`"))"
        )
        $added.Add($name)
    }

    if ($entries.Count -gt 0) {
        $closingIndex = $content.LastIndexOf(')')
        if ($closingIndex -lt 0) {
            throw "Invalid library table: $TablePath"
        }

        $prefix = $content.Substring(0, $closingIndex).TrimEnd()
        $suffix = $content.Substring($closingIndex + 1).TrimEnd()
        $newContent = $prefix + "`r`n" + ($entries -join "`r`n") + "`r`n)"
        if ($suffix) {
            $newContent += "`r`n" + $suffix
        }
        [System.IO.File]::WriteAllText(
            $TablePath,
            $newContent + "`r`n",
            [System.Text.UTF8Encoding]::new($false)
        )
    }

    return [pscustomobject]@{
        Added = $added
        Skipped = $skipped
    }
}

$symbolLibraries = foreach ($directory in Get-ChildItem -LiteralPath $LibraryRoot -Directory | Sort-Object Name) {
    $symbolPath = Join-Path $directory.FullName ($directory.Name + '.kicad_sym')
    if (Test-Path -LiteralPath $symbolPath) {
        [pscustomobject]@{
            Name = $directory.Name
            Uri = $symbolPath
        }
    }
}

$footprintLibraries = foreach ($directory in Get-ChildItem -LiteralPath $LibraryRoot -Directory | Sort-Object Name) {
    $footprintPath = Join-Path $directory.FullName ($directory.Name + '.pretty')
    if (Test-Path -LiteralPath $footprintPath) {
        [pscustomobject]@{
            Name = $directory.Name
            Uri = $footprintPath
        }
    }
}

$symbolResult = Add-LibraryEntries -TablePath $SymbolTablePath -EntryKind 'symbol' -Libraries $symbolLibraries
$footprintResult = Add-LibraryEntries -TablePath $FootprintTablePath -EntryKind 'footprint' -Libraries $footprintLibraries

$report = [pscustomobject]@{
    timestamp = $Timestamp
    library_root = $LibraryRoot
    symbol_table = $SymbolTablePath
    footprint_table = $FootprintTablePath
    symbols_added = @($symbolResult.Added)
    symbols_skipped = @($symbolResult.Skipped)
    footprints_added = @($footprintResult.Added)
    footprints_skipped = @($footprintResult.Skipped)
}

$report | ConvertTo-Json -Depth 5
