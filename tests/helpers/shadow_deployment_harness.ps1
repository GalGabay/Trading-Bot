# Test-only boundary: every scheduler mutation is replaced by a local function.
# Native mutation cmdlets also receive -WhatIf if command resolution changes.
param(
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$ReviewDirectory,
    [Parameter(Mandatory = $true)][string]$Case,
    [string]$OutsideDirectory = ''
)
$ErrorActionPreference = 'Stop'
$global:MutationCalls = New-Object 'System.Collections.Generic.List[string]'
$global:FixtureCase = $Case
$global:FixtureRepository = $Repository
$PSDefaultParameterValues['Register-ScheduledTask:WhatIf'] = $true
$PSDefaultParameterValues['Unregister-ScheduledTask:WhatIf'] = $true
$PSDefaultParameterValues['Stop-ScheduledTask:WhatIf'] = $true

function global:Register-ScheduledTask {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param($TaskName, $TaskPath, $Xml)
    $global:MutationCalls.Add('register')
}
function global:Unregister-ScheduledTask {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param($TaskName, $TaskPath)
    $global:MutationCalls.Add('unregister')
}
function global:Stop-ScheduledTask {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param($TaskName, $TaskPath)
    $global:MutationCalls.Add('stop')
}
function global:Get-ScheduledTask {
    [CmdletBinding()]
    param($TaskName, $TaskPath)
    if ($global:FixtureCase -in @('install', 'installWhatIf', 'installBadSid', 'installBadReview', 'installNotReady', 'installRelative', 'removeAbsent')) {
        return $null
    }
    $description = 'TradingBot shadow-only observer | ' + $global:FixtureRepository
    if ($global:FixtureCase -eq 'removeForeign') { $description = 'Some other application' }
    $state = 'Ready'
    if ($global:FixtureCase -in @('removeRunning', 'removeForce', 'removeWhatIf')) { $state = 'Running' }
    return [PSCustomObject]@{ Description = $description; State = $state }
}

$failed = $false
$message = ''
try {
    if ($OutsideDirectory) { Set-Location -LiteralPath $OutsideDirectory }
    $install = Join-Path $Repository 'deploy\windows\Install-ShadowObserver.ps1'
    $remove = Join-Path $Repository 'deploy\windows\Remove-ShadowObserver.ps1'
    if ($Case -eq 'installWhatIf') { & $install -ReviewDirectory $ReviewDirectory -WhatIf }
    elseif ($Case.StartsWith('install')) { & $install -ReviewDirectory $ReviewDirectory }
    elseif ($Case -eq 'removeWhatIf') { & $remove -StopRunning -WhatIf }
    elseif ($Case -eq 'removeForce') { & $remove -StopRunning }
    else { & $remove }
}
catch {
    $failed = $true
    $message = $_.Exception.Message
}
$summary = @{ failed = $failed; message = $message; calls = @($global:MutationCalls.ToArray()); real_mutations = 0 }
Write-Output ('SHADOW_HARNESS_RESULT=' + ($summary | ConvertTo-Json -Compress))
