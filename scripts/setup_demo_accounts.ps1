param(
    [switch]$RotatePassword
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$credentialsPath = Join-Path $repoRoot ".demo-accounts.local.txt"

$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCommand) {
    $docker = $dockerCommand.Source
} else {
    $dockerCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"),
        (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe")
    )
    $docker = $dockerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $docker) {
    throw "Docker Desktop's docker.exe was not found. Start Docker Desktop and check its installation path."
}

$demoPassword = $null
if ((Test-Path -LiteralPath $credentialsPath) -and -not $RotatePassword) {
    $savedCredentials = Get-Content -LiteralPath $credentialsPath -Raw
    if ($savedCredentials -match '(?m)^Password:\s*(\S+)\s*$') {
        $demoPassword = $Matches[1]
    } else {
        throw "The existing local credential file has no readable Password entry. Use -RotatePassword to replace it."
    }
} else {
    $randomBytes = [byte[]]::new(32)
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
    $demoPassword = [BitConverter]::ToString($randomBytes).Replace("-", "").ToLowerInvariant()
}

$previousSeedFlag = $env:DW_ENABLE_SYNTHETIC_SEED
$previousDemoPassword = $env:DW_DEMO_PASSWORD
try {
    $env:DW_ENABLE_SYNTHETIC_SEED = "true"
    $env:DW_DEMO_PASSWORD = $demoPassword
    Push-Location $repoRoot
    try {
        & $docker compose run --rm --no-deps -e DW_ENABLE_SYNTHETIC_SEED -e DW_DEMO_PASSWORD api python -m backend.seed_demo --users-only
        if ($LASTEXITCODE -ne 0) {
            throw "Demo account setup failed. The credential file was not changed."
        }
    } finally {
        Pop-Location
    }

    $credentialText = @"
DigitalWitness local demo accounts — synthetic data only
Password: $demoPassword

demo.reporter@example.com      role: reporter
demo.investigator@example.com  role: investigator
demo.legal@example.com         role: legal
demo.admin@example.com         role: admin

Use only with your local development database. Do not use these accounts with real cases or deploy these credentials.
"@
    Set-Content -LiteralPath $credentialsPath -Value $credentialText -Encoding UTF8
    Write-Output "Four synthetic demo roles are ready. Their shared local password is stored in .demo-accounts.local.txt (excluded from Git)."
} finally {
    if ($null -eq $previousSeedFlag) { Remove-Item Env:DW_ENABLE_SYNTHETIC_SEED -ErrorAction SilentlyContinue } else { $env:DW_ENABLE_SYNTHETIC_SEED = $previousSeedFlag }
    if ($null -eq $previousDemoPassword) { Remove-Item Env:DW_DEMO_PASSWORD -ErrorAction SilentlyContinue } else { $env:DW_DEMO_PASSWORD = $previousDemoPassword }
}
