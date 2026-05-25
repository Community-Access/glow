[CmdletBinding()]
param(
    [string]$ServerHost = "lp.csedesigns.com",
    [string]$ServerUser = "jeffbis",
    [string]$LocalGggPath = "C:\code\ggg",
    [string]$RemoteGggPath = "~/ggg",
    [switch]$Apply,
    [switch]$SkipUpload,
    [string]$AppRoot = "~/app",
    [string]$WebRoot = "~/app/web",
    [int]$ServiceWaitSeconds = 300,
    [int]$ServiceCheckIntervalSeconds = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-CommandAvailable {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Invoke-Remote {
    param([Parameter(Mandatory = $true)][string]$Command)

    $target = "$ServerUser@$ServerHost"
    Write-Host "[remote] $Command"
    & ssh $target $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Remote command failed (exit $LASTEXITCODE): $Command"
    }
}

Write-Host "== GGG sync from Windows to server =="
Write-Host "Server: $ServerUser@$ServerHost"
Write-Host "Local:  $LocalGggPath"
Write-Host "Remote: $RemoteGggPath"
Write-Host "Apply runtime: $Apply"
Write-Host "Skip upload: $SkipUpload"
Write-Host ""

Test-CommandAvailable -Name "ssh"
Test-CommandAvailable -Name "tar"
Test-CommandAvailable -Name "scp"

if (-not (Test-Path -LiteralPath $LocalGggPath)) {
    throw "Local path does not exist: $LocalGggPath"
}

if (-not (Test-Path -LiteralPath (Join-Path $LocalGggPath "site"))) {
    Write-Warning "Expected site directory missing at $LocalGggPath\site. Continuing anyway."
}

Write-Host "Checking SSH connectivity..."
Invoke-Remote -Command "echo connected"
Write-Host "SSH check passed."
Write-Host ""

$remoteHome = (& ssh "$ServerUser@$ServerHost" 'printf %s "$HOME"').Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($remoteHome)) {
    throw "Unable to resolve remote HOME directory."
}

if ($RemoteGggPath -eq "~/ggg") {
    $RemoteGggPath = "$remoteHome/ggg"
} elseif ($RemoteGggPath.StartsWith("~/")) {
    $RemoteGggPath = "$remoteHome/" + $RemoteGggPath.Substring(2)
}

if ($AppRoot -eq "~/app") {
    $AppRoot = "$remoteHome/app"
} elseif ($AppRoot.StartsWith("~/")) {
    $AppRoot = "$remoteHome/" + $AppRoot.Substring(2)
}

if ($WebRoot -eq "~/app/web") {
    $WebRoot = "$remoteHome/app/web"
} elseif ($WebRoot.StartsWith("~/")) {
    $WebRoot = "$remoteHome/" + $WebRoot.Substring(2)
}

Write-Host "Resolved remote paths:"
Write-Host "- HOME: $remoteHome"
Write-Host "- GGG:  $RemoteGggPath"
Write-Host "- APP:  $AppRoot"
Write-Host "- WEB:  $WebRoot"
Write-Host ""

if (-not $SkipUpload) {
    Write-Host "Preparing remote folder..."
    Invoke-Remote -Command "mkdir -p '$RemoteGggPath'; find '$RemoteGggPath' -mindepth 1 -maxdepth 1 -exec rm -rf {} +"
    Write-Host "Remote folder prepared."
    Write-Host ""

    Write-Host "Uploading all GGG files (including media) ..."
    $tempTar = Join-Path $env:TEMP ("ggg-sync-" + [Guid]::NewGuid().ToString("N") + ".tar")

    try {
        & tar -C $LocalGggPath -cf $tempTar .
        if ($LASTEXITCODE -ne 0) {
            throw "Failed creating tar archive (exit $LASTEXITCODE)."
        }

        $remoteTar = "$RemoteGggPath/ggg-upload.tar"
        & scp $tempTar "${ServerUser}@${ServerHost}:$remoteTar"
        if ($LASTEXITCODE -ne 0) {
            throw "Upload failed during scp (exit $LASTEXITCODE)."
        }

        Invoke-Remote -Command "tar -xf '$remoteTar' -C '$RemoteGggPath'; rm -f '$remoteTar'"
    }
    finally {
        if (Test-Path -LiteralPath $tempTar) {
            Remove-Item -LiteralPath $tempTar -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Host "Upload complete."
    Write-Host ""
}
else {
    Write-Host "Skipping upload as requested."
    Write-Host ""
}

Write-Host "Verifying remote content..."
Invoke-Remote -Command "set -e; test -f '$RemoteGggPath/Caddyfile'; test -d '$RemoteGggPath/site'; ls -lah '$RemoteGggPath' | head; ls -lah '$RemoteGggPath/site' | head"
Write-Host "Remote verification complete."
Write-Host ""

if ($Apply) {
    Write-Host "Applying GGG-only runtime changes on server..."
    Invoke-Remote -Command "mkdir -p '$AppRoot/ggg'"
    Invoke-Remote -Command "if command -v rsync >/dev/null 2>&1; then rsync -av --delete '$RemoteGggPath/' '$AppRoot/ggg/'; else rm -rf '$AppRoot/ggg'/*; cp -a '$RemoteGggPath/'* '$AppRoot/ggg/'; fi"

    $hasGggService = $false
    $deadline = (Get-Date).AddSeconds([Math]::Max(0, $ServiceWaitSeconds))

    do {
        try {
            Invoke-Remote -Command "cd '$WebRoot' && docker compose -f docker-compose.prod.yml config --services | grep -Fxq ggg"
            $hasGggService = $true
        }
        catch {
            $hasGggService = $false
            if ((Get-Date) -lt $deadline) {
                Write-Host "GGG service not visible yet in compose; waiting $ServiceCheckIntervalSeconds seconds..."
                Start-Sleep -Seconds ([Math]::Max(1, $ServiceCheckIntervalSeconds))
            }
        }
    } until ($hasGggService -or ((Get-Date) -ge $deadline))

    if (-not $hasGggService) {
        throw "Remote compose file at $WebRoot/docker-compose.prod.yml still does not define service 'ggg' after waiting $ServiceWaitSeconds seconds. Ensure deployment is complete, then rerun with -Apply (or increase -ServiceWaitSeconds)."
    }

    Invoke-Remote -Command "cd '$WebRoot' && docker compose -f docker-compose.prod.yml up -d --no-deps --force-recreate ggg caddy"

    Write-Host "Running quick remote checks..."
    Invoke-Remote -Command "curl -sSI https://lp.csedesigns.com/ggg/ | head -n 5"
    Invoke-Remote -Command "curl -sSI https://lp.csedesigns.com/ggg/feed.xml | head -n 5"
    Write-Host "GGG runtime apply completed."
}

Write-Host ""
Write-Host "Done."
Write-Host "Only GGG content/actions were applied by this script."
