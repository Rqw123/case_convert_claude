[CmdletBinding()]
param(
    [string]$RemoteUrl = "",
    [string]$Branch = "main",
    [string]$RemoteName = "origin",
    [string]$CommitMessage = "",
    [switch]$ForceSetRemote
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-GitOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$AllowFailure
    )

    $output = & git @Arguments 2>&1
    if (-not $AllowFailure -and $LASTEXITCODE -ne 0) {
        throw ($output -join [Environment]::NewLine)
    }
    return $output
}

function Test-GitRepo {
    & git rev-parse --is-inside-work-tree *> $null
    return $LASTEXITCODE -eq 0
}

function Test-HasCommit {
    & git rev-parse --verify HEAD *> $null
    return $LASTEXITCODE -eq 0
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Push local code to remote repository" -ForegroundColor Green

try {
    Get-GitOutput -Arguments @("--version") | Out-Null
    if ([string]::IsNullOrWhiteSpace($RemoteUrl)) {
        $RemoteUrl = Read-Host "Enter remote repository URL"
    }

    if ([string]::IsNullOrWhiteSpace($RemoteUrl)) {
        throw "Remote repository URL is required."
    }

    if (-not (Test-GitRepo)) {
        Write-Step "Initializing git repository"
        Get-GitOutput -Arguments @("init") | Out-Null
    }

    $existingRemoteUrl = ""
    $remoteLookup = Get-GitOutput -Arguments @("remote", "get-url", $RemoteName) -AllowFailure
    if ($LASTEXITCODE -eq 0) {
        $existingRemoteUrl = ($remoteLookup | Select-Object -First 1).Trim()
    }

    if ([string]::IsNullOrWhiteSpace($existingRemoteUrl)) {
        Write-Step "Adding remote '$RemoteName'"
        Get-GitOutput -Arguments @("remote", "add", $RemoteName, $RemoteUrl) | Out-Null
    } elseif ($existingRemoteUrl -ne $RemoteUrl) {
        if (-not $ForceSetRemote) {
            throw "Remote '$RemoteName' already points to '$existingRemoteUrl'. Re-run with -ForceSetRemote to replace it."
        }
        Write-Step "Updating remote '$RemoteName'"
        Get-GitOutput -Arguments @("remote", "set-url", $RemoteName, $RemoteUrl) | Out-Null
    } else {
        Write-Step "Remote '$RemoteName' already configured"
    }

    Write-Step "Staging files"
    Get-GitOutput -Arguments @("add", "-A") | Out-Null

    $statusLines = Get-GitOutput -Arguments @("status", "--porcelain")
    $hasCommit = Test-HasCommit

    if ($statusLines.Count -gt 0) {
        if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
            $CommitMessage = "chore: initial push " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        }
        Write-Step "Creating commit"
        Get-GitOutput -Arguments @("commit", "-m", $CommitMessage) | Out-Null
    } elseif (-not $hasCommit) {
        throw "Repository has no commit and no files to commit."
    } else {
        Write-Step "No local changes to commit"
    }

    Write-Step "Switching branch to '$Branch'"
    Get-GitOutput -Arguments @("branch", "-M", $Branch) | Out-Null

    Write-Step "Pushing to '$RemoteName/$Branch'"
    Get-GitOutput -Arguments @("push", "-u", $RemoteName, $Branch)

    Write-Host ""
    Write-Host "Completed." -ForegroundColor Green
    Write-Host "Remote: $RemoteUrl"
    Write-Host "Branch: $Branch"
} catch {
    Write-Host ""
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
