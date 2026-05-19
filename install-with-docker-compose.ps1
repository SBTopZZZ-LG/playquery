#!/usr/bin/env pwsh

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoOwner = 'SBTopZZZ-LG'
$RepoName = 'playquery'
$RawBase = "https://raw.githubusercontent.com/$RepoOwner/$RepoName"
$ApiBase = "https://api.github.com/repos/$RepoOwner/$RepoName"

function Get-EnvFileValue {
    param(
        [string]$File,
        [string]$Key
    )

    if (-not (Test-Path -LiteralPath $File)) {
        return $null
    }

    $escapedKey = [regex]::Escape($Key)
    $line = Get-Content -LiteralPath $File | Where-Object { $_ -match "^$escapedKey=" } | Select-Object -Last 1
    if ($null -eq $line) {
        return $null
    }

    return $line.Substring($Key.Length + 1)
}

function Get-ValueOrDefault {
    param(
        [string]$File,
        [string]$Key,
        [string]$Fallback
    )

    $value = Get-EnvFileValue -File $File -Key $Key
    if ([string]::IsNullOrEmpty($value)) {
        return $Fallback
    }

    return $value
}

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "Missing required command: $Name"
        exit 1
    }
}

function Select-ComposeCommand {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $script:UseLegacyDockerCompose = $true
        return
    }

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            & docker compose version | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $script:UseLegacyDockerCompose = $false
                return
            }
        }
        catch {
        }
    }

    Write-Error 'Neither docker-compose nor docker compose is available.'
    exit 1
}

function Get-LatestReleaseRef {
    try {
        $release = Invoke-RestMethod -Uri "$ApiBase/releases/latest"
        return $release.tag_name
    }
    catch {
        return $null
    }
}

function Test-RefHasProdCompose {
    param([string]$Ref)

    if ([string]::IsNullOrWhiteSpace($Ref)) {
        return $false
    }

    try {
        Invoke-WebRequest -Uri "$RawBase/$Ref/docker-compose.prod.yaml" -Method Head | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Assert-Interactive {
    param([string]$Message)

    if (-not [Environment]::UserInteractive) {
        Write-Error $Message
        exit 1
    }
}

function Prompt-Default {
    param(
        [string]$Prompt,
        [string]$DefaultValue
    )

    Assert-Interactive 'Interactive input requires a tty. Set the environment variables before running the installer.'

    if (-not [string]::IsNullOrEmpty($DefaultValue)) {
        $value = Read-Host "$Prompt [$DefaultValue]"
        if ([string]::IsNullOrEmpty($value)) {
            return $DefaultValue
        }

        return $value
    }

    return (Read-Host $Prompt)
}

function ConvertTo-PlainText {
    param([Security.SecureString]$SecureString)

    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Prompt-Secret {
    param(
        [string]$Prompt,
        [string]$DefaultValue = ''
    )

    Assert-Interactive 'Interactive secret input requires a tty. Set PLAYQUERY_AI_GITHUB_TOKEN before running the installer.'

    while ($true) {
        $value = ConvertTo-PlainText (Read-Host -Prompt $Prompt -AsSecureString)
        if (-not [string]::IsNullOrEmpty($value)) {
            return $value
        }

        if (-not [string]::IsNullOrEmpty($DefaultValue)) {
            return $DefaultValue
        }
    }
}

function Prompt-Confirm {
    param(
        [string]$Prompt,
        [string]$DefaultValue = 'n'
    )

    Assert-Interactive 'Interactive input requires a tty. Set the environment variables before running the installer.'

    $promptSuffix = 'y/N'
    if ($DefaultValue -eq 'y') {
        $promptSuffix = 'Y/n'
    }

    $value = Read-Host "$Prompt [$promptSuffix]"
    if ([string]::IsNullOrEmpty($value)) {
        $value = $DefaultValue
    }

    $value = $value.ToLowerInvariant()
    return $value -in @('y', 'yes')
}

function Invoke-Compose {
    param(
        [string]$WorkingDirectory,
        [string[]]$Arguments,
        [switch]$IgnoreExitCode,
        [switch]$SuppressStderr
    )

    Push-Location $WorkingDirectory
    try {
        if ($script:UseLegacyDockerCompose) {
            if ($SuppressStderr) {
                $output = & docker-compose @Arguments 2>$null
            }
            else {
                $output = & docker-compose @Arguments
            }
        }
        else {
            if ($SuppressStderr) {
                $output = & docker compose @Arguments 2>$null
            }
            else {
                $output = & docker compose @Arguments
            }
        }

        if ((-not $IgnoreExitCode) -and $LASTEXITCODE -ne 0) {
            throw "Compose command failed with exit code $LASTEXITCODE."
        }

        return $output
    }
    finally {
        Pop-Location
    }
}

function Test-StackRunning {
    param(
        [string]$InstallDir,
        [string]$ComposeFile
    )

    if (-not (Test-Path -LiteralPath $ComposeFile)) {
        return $false
    }

    $output = Invoke-Compose -WorkingDirectory $InstallDir -Arguments @('-f', $ComposeFile, 'ps', '-q', 'playquery') -IgnoreExitCode -SuppressStderr
    return -not [string]::IsNullOrWhiteSpace(($output | Out-String).Trim())
}

function Write-ExistingStackStatus {
    param(
        [string]$InstallDir,
        [string]$EnvFile,
        [string]$LatestReleaseTag
    )

    $currentImageTag = Get-ValueOrDefault -File $EnvFile -Key 'PLAYQUERY_IMAGE_TAG' -Fallback 'latest'

    Write-Host "`nPlayQuery is already running in $InstallDir."

    if (-not [string]::IsNullOrEmpty($LatestReleaseTag)) {
        Write-Host "Current configured image tag: $currentImageTag"
        Write-Host "Latest release tag: $LatestReleaseTag"

        if ($currentImageTag -eq $LatestReleaseTag) {
            Write-Host 'It is already running the latest released version.'
        }
        elseif ($currentImageTag -ne 'latest') {
            Write-Host 'Note: the running stack is outdated.'
        }
    }
}

Require-Command -Name 'curl'
Require-Command -Name 'docker'

Select-ComposeCommand
$latestReleaseTag = Get-LatestReleaseRef
$defaultRef = if ([string]::IsNullOrEmpty($latestReleaseTag)) { 'main' } else { $latestReleaseTag }

if (-not (Test-RefHasProdCompose -Ref $defaultRef)) {
    $defaultRef = 'main'
}

$defaultImageTag = if ($defaultRef -eq 'main') { 'latest' } else { $defaultRef }

$installDir = $env:PLAYQUERY_INSTALL_DIR
if ([string]::IsNullOrEmpty($installDir)) {
    $installDir = Prompt-Default -Prompt 'Install directory' -DefaultValue (Join-Path $HOME '.playquery')
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null

$composeFile = Join-Path $installDir 'docker-compose.prod.yaml'
$envFile = Join-Path $installDir '.env'
$stackRunning = $false

if (Test-StackRunning -InstallDir $installDir -ComposeFile $composeFile) {
    $stackRunning = $true
    Write-ExistingStackStatus -InstallDir $installDir -EnvFile $envFile -LatestReleaseTag $latestReleaseTag

    if (-not (Prompt-Confirm -Prompt 'Re-configure the existing stack' -DefaultValue 'n')) {
        exit 0
    }
}

$releaseRef = $env:PLAYQUERY_RELEASE_REF
if ([string]::IsNullOrEmpty($releaseRef)) {
    $releaseRef = Prompt-Default -Prompt 'Release ref to install' -DefaultValue $defaultRef
}

$imageTag = $env:PLAYQUERY_IMAGE_TAG
if ([string]::IsNullOrEmpty($imageTag)) {
    $imageTag = Prompt-Default -Prompt 'Docker image tag' -DefaultValue $defaultImageTag
}

$mcpPort = $env:PLAYQUERY_MCP_PORT
if ([string]::IsNullOrEmpty($mcpPort)) {
    $mcpPort = Prompt-Default -Prompt 'MCP host port' -DefaultValue (Get-ValueOrDefault -File $envFile -Key 'PLAYQUERY_MCP_PORT' -Fallback '8000')
}

$aiModel = $env:PLAYQUERY_AI_MODEL
if ([string]::IsNullOrEmpty($aiModel)) {
    $aiModel = Prompt-Default -Prompt 'AI model' -DefaultValue (Get-ValueOrDefault -File $envFile -Key 'PLAYQUERY_AI_MODEL' -Fallback 'claude-haiku-4.5')
}

$loggingLevel = $env:PLAYQUERY_LOGGING_LEVEL
if ([string]::IsNullOrEmpty($loggingLevel)) {
    $loggingLevel = Prompt-Default -Prompt 'Logging level' -DefaultValue (Get-ValueOrDefault -File $envFile -Key 'PLAYQUERY_LOGGING_LEVEL' -Fallback 'DEBUG')
}

$corsOrigins = $env:PLAYQUERY_MCP_CORS_ORIGINS
if ([string]::IsNullOrEmpty($corsOrigins)) {
    $corsOrigins = Prompt-Default -Prompt 'Allowed CORS origins' -DefaultValue (Get-ValueOrDefault -File $envFile -Key 'PLAYQUERY_MCP_CORS_ORIGINS' -Fallback '*')
}

$githubToken = $env:PLAYQUERY_AI_GITHUB_TOKEN
if ([string]::IsNullOrEmpty($githubToken)) {
    $githubToken = Prompt-Secret -Prompt 'GitHub token for Copilot' -DefaultValue (Get-ValueOrDefault -File $envFile -Key 'PLAYQUERY_AI_GITHUB_TOKEN' -Fallback '')
}

Invoke-WebRequest -Uri "$RawBase/$releaseRef/docker-compose.prod.yaml" -OutFile $composeFile

$envContent = @"
PLAYQUERY_IMAGE_TAG=$imageTag
PLAYQUERY_AI_GITHUB_TOKEN=$githubToken
PLAYQUERY_AI_MODEL=$aiModel
PLAYQUERY_LOGGING_LEVEL=$loggingLevel
PLAYQUERY_MCP_PORT=$mcpPort
PLAYQUERY_MCP_CORS_ORIGINS=$corsOrigins
"@
[System.IO.File]::WriteAllText($envFile, "$envContent`n", [System.Text.UTF8Encoding]::new($false))

if ($stackRunning) {
    Invoke-Compose -WorkingDirectory $installDir -Arguments @('-f', $composeFile, 'down') | Out-Null
}

try {
    Invoke-Compose -WorkingDirectory $installDir -Arguments @('-f', $composeFile, 'pull') | Out-Null
}
catch {
}

Invoke-Compose -WorkingDirectory $installDir -Arguments @('-f', $composeFile, 'up', '-d') | Out-Null

Write-Host "`nPlayQuery is starting."
Write-Host "Install directory: $installDir"
Write-Host "MCP endpoint: http://localhost:$mcpPort/mcp"
