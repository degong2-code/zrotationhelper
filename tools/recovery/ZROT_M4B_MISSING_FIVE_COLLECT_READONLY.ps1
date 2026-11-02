#requires -Version 5.1
<#
zRotationHelper M4B missing-five read-only collector.
Only reads 5 exact historical runtime modules. Never executes project code,
calls WCL, reads .env/secrets, or changes MAIN/Registry/Pointer/FROZEN.
Requires all five files to match historic SHA256/length; otherwise no ZIP.
Script Parameters optional: double-click/Run with PowerShell uses auto-discovery.
-SelfTest checks contract parsing and synthetic missing-file rejection only.
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [switch]$SelfTest
)
$ErrorActionPreference = "Stop"

$expected = @(
    [pscustomobject]@{ Relative="02_SOURCE/runtime/raid_dps/core/cohort.py"; Length=6147; Sha="e506e7a7073b88b3bad6909822f5289363bba92218de71f1003a7fc3fc2da600" }
    [pscustomobject]@{ Relative="02_SOURCE/runtime/raid_dps/core/evidence.py"; Length=8791; Sha="a5a4261168ffb172d95b655c9d320591e5400fe5bdb1425b1d3a54a0b581d27b" }
    [pscustomobject]@{ Relative="02_SOURCE/runtime/raid_dps/core/renderer.py"; Length=13229; Sha="7c0bf5e1b09d10aec09c89438b18cd302906acf73ef4f24fd6349526e004ca52" }
    [pscustomobject]@{ Relative="02_SOURCE/runtime/raid_dps/core/wcl_client.py"; Length=13129; Sha="452fb44c4c577b5bbb08ceb431013e165de57e62ef72f59500777d703e42ce24" }
    [pscustomobject]@{ Relative="02_SOURCE/runtime/raid_dps/pipelines/orchestrator.py"; Length=19606; Sha="fe398aa9238908c21af433ac5652f1730f66cd5dd0209722ebf6371b68d68d0d" }
)
function Get-RelativeFullPath {
    param([string]$Root, [string]$Rel)
    if ($Rel -match '(^[\\/]|(^|[\\/])\.\.($|[\\/]))') { throw "UNSAFE_RELATIVE_PATH" }
    return Join-Path $Root ($Rel -replace '/', '\')
}
function Test-Candidate {
    param([string]$Root, $Entry)
    $full = Get-RelativeFullPath -Root $Root -Rel $Entry.Relative
    if (!(Test-Path -LiteralPath $full -PathType Leaf)) {
        return [pscustomobject]@{ relative_path=$Entry.Relative; status="MISSING"; expected_sha256=$Entry.Sha; observed_sha256="UNKNOWN"; expected_bytes=$Entry.Length; observed_bytes=-1 }
    }
    $fi = Get-Item -LiteralPath $full
    $hash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    $status="EXACT_MATCH"
    if ($fi.Length -ne $Entry.Length) { $status="SIZE_DIFFERENT" }
    elseif ($hash -ne $Entry.Sha) { $status="SHA_DIFFERENT" }
    return [pscustomobject]@{
        relative_path=$Entry.Relative; status=$status;
        expected_sha256=$Entry.Sha; observed_sha256=$hash;
        expected_bytes=$Entry.Length; observed_bytes=$fi.Length
    }
}
function Test-Root {
    param([string]$Root)
    if ([string]::IsNullOrWhiteSpace($Root)) { return $false }
    foreach ($rel in @("CURRENT_STATE.md", "RUN_zRAID_MAIN.py", "01_WORKFLOW/config/MAIN_CONTROL_PLANE.json")) {
        if (!(Test-Path -LiteralPath (Get-RelativeFullPath -Root $Root -Rel $rel) -PathType Leaf)) { return $false }
    }
    return $true
}
function Find-Root {
    $choices = New-Object 'System.Collections.Generic.List[string]'
    if ($ProjectRoot) { $choices.Add($ProjectRoot) }
    elseif ($env:ZRAID_PROJECT_ROOT) { $choices.Add($env:ZRAID_PROJECT_ROOT) }
    else {
        if ($env:USERPROFILE) {
            $choices.Add((Join-Path $env:USERPROFILE "Desktop\Wow\python\01_PROJECTS\02_ZRAID_DEALCYCLE"))
            $choices.Add((Join-Path $env:USERPROFILE "Desktop\법인, 기타\python\01_PROJECTS\02_ZRAID_DEALCYCLE"))
        }
        $choices.Add((Get-Location).Path)
    }
    $found=@()
    foreach ($candidate in ($choices | Select-Object -Unique)) {
        if (Test-Root $candidate) { $found+=([IO.Path]::GetFullPath($candidate)) }
    }
    if ($found.Count -eq 0) { throw "PROJECT_ROOT_NOT_FOUND: Set ZRAID_PROJECT_ROOT or -ProjectRoot to a folder containing CURRENT_STATE.md and RUN_zRAID_MAIN.py. No files collected." }
    if ($found.Count -gt 1) { throw "MULTIPLE_PROJECT_ROOTS: Set -ProjectRoot or ZRAID_PROJECT_ROOT explicitly. No files collected." }
    return $found[0]
}

if ($expected.Count -ne 5 -or @($expected | Select-Object -ExpandProperty Relative -Unique).Count -ne 5) {
    throw "FIVE_FILE_ALLOWLIST_BROKEN"
}
foreach ($row in $expected) {
    if ($row.Relative -notmatch '^02_SOURCE/runtime/raid_dps/(core|pipelines)/[^\\/]+\.py$' -or $row.Sha -notmatch '^[0-9a-f]{64}$' -or $row.Length -lt 100) {
        throw "EXPECTED_SOURCE_IDENTITY_INVALID"
    }
}
if ($SelfTest) {
    $trialRoot = Join-Path $env:TEMP ("ZROT_MISSING_FIVE_SELFTEST_"+[Guid]::NewGuid().ToString("N"))
    try {
        New-Item -ItemType Directory -Path $trialRoot -Force | Out-Null
        $result=Test-Candidate -Root $trialRoot -Entry $expected[0]
        if ($result.status -ne "MISSING") { throw "EXPECTED_MISSING_FILE_REJECTED_INCORRECTLY" }
        $payload=[ordered]@{ status="PASS"; self_test="EXPECTED_FIVE_PINS_AND_MISSING_FILE_NEGATIVE"; count=5; product_execution="NOT_RUN"; promotion=$false }
        $payload | ConvertTo-Json -Depth 5
    } finally { if (Test-Path $trialRoot) { Remove-Item -LiteralPath $trialRoot -Force -Recurse } }
    exit 0
}

$root = Find-Root
$desktop = [Environment]::GetFolderPath("Desktop")
if (!(Test-Path -LiteralPath $desktop -PathType Container)) { $desktop=$env:USERPROFILE }
$stamp=(Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$receiptPath=Join-Path $desktop ("ZROT_MISSING_FIVE_RECOVERY_"+$stamp+".receipt.json")
$zipPath=Join-Path $desktop ("ZROT_MISSING_FIVE_RECOVERY_"+$stamp+".zip")
$statuses=@($expected | ForEach-Object { Test-Candidate -Root $root -Entry $_ })
$allExact=(@($statuses | Where-Object { $_.status -ne "EXACT_MATCH" }).Count -eq 0)
$receipt=[ordered]@{
    schema="ZrotExactFiveHistoricalSourceCollectorReceiptV1"
    timestamp_utc=(Get-Date).ToUniversalTime().ToString("o")
    scope="FIVE_FILES_ONLY_HISTORICAL_SOURCE_NOT_CURRENT_AUTHORITY"
    status=$(if ($allExact) {"EXACT_FIVE_SOURCE_READY"} else {"BLOCKED_MISSING_OR_CHANGED"})
    file_count=5; matching_count=@($statuses | Where-Object { $_.status -eq "EXACT_MATCH" }).Count
    files=$statuses; zip_sha256="NOT_CREATED"
    product_entrypoint_executed=$false; current_main_authority="UNKNOWN"
    canonical_registry_or_pointer_read=$false; wcl_or_simc_run=$false
    active_pointer_changed=$false; frozen_modified=$false
}
if (!$allExact) {
    ($receipt | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    Write-Host "Missing or changed historic modules. No ZIP created. Receipt: $receiptPath"
    exit 2
}
$stage=Join-Path $env:TEMP ("ZROT_EXACT_FIVE_"+[Guid]::NewGuid().ToString("N"))
try {
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    foreach ($row in $expected) {
        $src=Get-RelativeFullPath -Root $root -Rel $row.Relative
        $dst=Get-RelativeFullPath -Root $stage -Rel ("payload/"+$row.Relative)
        New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $src -Destination $dst -ErrorAction Stop
        $sha=(Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($sha -ne $row.Sha) { throw "POST_COPY_HASH_MISMATCH: $($row.Relative)" }
    }
    Compress-Archive -LiteralPath (Join-Path $stage "payload") -DestinationPath $zipPath -CompressionLevel Optimal
    $receipt.zip_sha256=(Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $receipt.status="EXACT_FIVE_RECOVERED_HISTORICAL_ONLY"
    ($receipt | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $receiptPath -Encoding UTF8
    Write-Host "Five original source modules collected without executing them."
    Write-Host "ZIP: $zipPath"
    Write-Host "Receipt: $receiptPath"
    Write-Host "Keep archive private; inspect before sharing. Product MAIN is NOT promoted."
} finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}
