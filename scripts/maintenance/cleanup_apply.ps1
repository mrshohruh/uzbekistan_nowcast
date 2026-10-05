param([string]$Workspace = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
$ErrorActionPreference = 'Stop'
$rootPath = [IO.Path]::GetFullPath($Workspace).TrimEnd('\')
$rootPrefix = $rootPath + '\'
$reportPath = Join-Path $rootPath 'results\cleanup'
$plan = Import-Csv -LiteralPath (Join-Path $reportPath 'cleanup_plan.csv')
$baselineChecks = Get-ChildItem -LiteralPath $reportPath -Filter 'validation_baseline_*_tests.json'
if ($baselineChecks.Count -lt 7) { throw 'All seven baseline test groups must complete before quarantine.' }
foreach ($check in $baselineChecks) {
    $counts = Get-Content -LiteralPath $check.FullName -Raw | ConvertFrom-Json
    if ($counts.exit_code -ne 0) { throw ('Baseline tests failed: ' + $check.Name) }
}
if ($plan | Where-Object { $_.category -eq 'CURRENT_ACTIVE' -and $_.action -in @('ARCHIVE','DELETE_SAFE') }) {
    throw 'A current-active file has an unsafe planned action.'
}
$moved = [Collections.Generic.List[object]]::new()
$deleted = [Collections.Generic.List[object]]::new()
foreach ($item in $plan) {
    if ($item.action -notin @('ARCHIVE','DELETE_SAFE')) { continue }
    if ($item.protected -eq 'True') { throw ('Protected path in mutation plan: ' + $item.path) }
    $source = [IO.Path]::GetFullPath((Join-Path $rootPath $item.path))
    if (-not $source.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Source escaped workspace.' }
    if ($source.StartsWith((Join-Path $rootPath 'results\phase6d') + '\',[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Phase 6D is preserved in full.'
    }
    $actualHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $item.hash) { throw ('File changed after audit: ' + $item.path) }
    $record = [pscustomobject]@{path=$item.path;destination=$item.destination;size_bytes=$item.size_bytes;sha256=$actualHash;reason=$item.reason}
    if ($item.action -eq 'ARCHIVE') {
        $destination = [IO.Path]::GetFullPath((Join-Path $rootPath $item.destination))
        $archivePrefix = (Join-Path $rootPath 'archive') + '\'
        if (-not $destination.StartsWith($archivePrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escaped archive.' }
        if (Test-Path -LiteralPath $destination) { throw ('Archive destination already exists: ' + $destination) }
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Move-Item -LiteralPath $source -Destination $destination
        $moved.Add($record)
        $record | Export-Csv -LiteralPath (Join-Path $reportPath 'archived_files.csv') -NoTypeInformation -Encoding UTF8 -Append
    } else {
        if ([IO.Path]::GetExtension($source) -eq '.py') { throw 'Python source cannot be permanently deleted.' }
        Remove-Item -LiteralPath $source
        $deleted.Add($record)
        $record | Export-Csv -LiteralPath (Join-Path $reportPath 'deleted_files.csv') -NoTypeInformation -Encoding UTF8 -Append
    }
}
# Empty-directory deletion is nonrecursive and restricted to audited mutation parents.
$parents = $plan | Where-Object { $_.action -in @('ARCHIVE','DELETE_SAFE') } | ForEach-Object {
    [IO.Path]::GetFullPath((Split-Path -Parent (Join-Path $rootPath $_.path)))
} | Sort-Object -Unique | Sort-Object Length -Descending
foreach ($directory in $parents) {
    if ($directory.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $directory) -and
        @(Get-ChildItem -LiteralPath $directory -Force).Count -eq 0) {
        Remove-Item -LiteralPath $directory
    }
}
Write-Output ('Archived files: ' + $moved.Count)
Write-Output ('Deleted safe files: ' + $deleted.Count)
