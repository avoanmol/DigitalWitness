# Load chain keys from the ignored root .env into this PowerShell process without printing them.
$envFile = Join-Path (Split-Path -Parent $PSScriptRoot) '.env'
if (-not (Test-Path -LiteralPath $envFile)) { throw 'Root .env not found.' }
foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match '^\s*(AMOY_RPC_URL|AMOY_PRIVATE_KEY|CHAIN_RPC_URL|CHAIN_EXPECTED_ID|CHAIN_CONTRACT_ADDRESS|CHAIN_SENDER_ADDRESS|CHAIN_PRIVATE_KEY|CHAIN_CONFIRMATIONS)\s*=\s*(.*)\s*$') {
        $value = $Matches[2].Trim().Trim('"').Trim("'")
        if ($value) { [Environment]::SetEnvironmentVariable($Matches[1], $value, 'Process') }
    }
}
