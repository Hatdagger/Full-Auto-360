# Full Auto 360 - Windows build script
#
# Run it by double-clicking build.bat in the project folder. It:
#   1. checks for (and offers to install) Visual Studio 2026 Build Tools with Clang
#   2. downloads the ReXGlue SDK into sdk\
#   3. makes sure your game files are in game\ (can extract a Games on Demand folder or an ISO)
#   4. runs codegen (PowerPC -> C++) and compiles the PC version
#   5. writes "Play Full Auto.bat"
# Everything is logged to logs\last-build.log.
#
# Keep this file plain ASCII: Windows PowerShell 5.1 misreads UTF-8 without a BOM.

param(
    [string]$GameSource = "",
    [ValidateSet("Release", "RelWithDebInfo", "Debug")]
    [string]$Config = "Release",
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$SdkVersion = "0.11.0"
$Root = Split-Path -Parent $PSScriptRoot
$SdkDir = Join-Path $Root "sdk"
$SdkPrefix = Join-Path $SdkDir "win-amd64"
$GameDir = Join-Path $Root "game"
$LogDir = Join-Path $Root "logs"
$ToolBin = Join-Path $Root "tools\bin"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("build-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
$LastLog = Join-Path $LogDir "last-build.log"
$Utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Log([string]$line) { [System.IO.File]::AppendAllText($Log, $line + "`r`n", $Utf8) }
function Say([string]$msg, [string]$color = "Gray") { Write-Host $msg -ForegroundColor $color; Write-Log $msg }
function Step([string]$msg) { Say ""; Say ("==> " + $msg) "Cyan" }
function Finish([int]$code) {
    Copy-Item -Path $Log -Destination $LastLog -Force
    if (-not $NoPause) { Write-Host ""; Read-Host "Press Enter to close" | Out-Null }
    exit $code
}
function Fail([string]$msg) {
    Say ""
    Say ("BUILD STOPPED: " + $msg) "Red"
    Say ("Full log: " + $LastLog) "Yellow"
    Finish 1
}

# Runs a program, shows its output and copies it into the log. Returns the exit code.
function Run([string]$exe, [string[]]$argList) {
    Write-Log ("> " + $exe + " " + ($argList -join " "))
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $exe @argList 2>&1 | ForEach-Object {
        $line = "$_"
        Write-Host $line
        Write-Log $line
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $old
    return $code
}

function Download([string]$url, [string]$dest) {
    Say ("Downloading " + $url)
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

Say ("Full Auto 360 build - " + (Get-Date)) "White"
Say ("Project folder: " + $Root)
Say ("Configuration: " + $Config)

# ---------------------------------------------------------------------------------------------
Step "Checking for Visual Studio 2026 Build Tools with Clang"
$VsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$Needs = @("Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "Microsoft.VisualStudio.Component.VC.Llvm.Clang")

function Find-VS {
    if (-not (Test-Path $VsWhere)) { return $null }
    $found = & $VsWhere -products * -version "[18.0,19.0)" -requires $Needs -latest -property installationPath
    if ($found) { return ([string]($found | Select-Object -First 1)).Trim() }
    return $null
}

$Vs = Find-VS
if (-not $Vs) {
    Say "Not found. The recompiled game needs Microsoft's free C++ Build Tools 2026 with the Clang compiler." "Yellow"
    Say "This is a one-time download of a few GB. Windows will ask for permission to install it." "Yellow"
    $answer = Read-Host "Install it now? (Y/N)"
    if ($answer -notmatch "^[Yy]") { Fail "Visual Studio 2026 Build Tools with Clang are required." }
    $bootstrap = Join-Path $env:TEMP "vs_buildtools_2026.exe"
    Download "https://aka.ms/vs/18/stable/vs_buildtools.exe" $bootstrap
    $vsArgs = @(
        "--passive", "--wait", "--norestart", "--nocache",
        "--add", "Microsoft.VisualStudio.Workload.VCTools", "--includeRecommended",
        "--add", "Microsoft.VisualStudio.Component.VC.Llvm.Clang",
        "--add", "Microsoft.VisualStudio.Component.VC.CMake.Project"
    )
    Say "Installing (a progress window will open; this can take a while)..."
    # Wait for the installer itself only. Start-Process -Wait also waits for every process the
    # installer leaves running in the background, which can keep this window waiting after the
    # install is done.
    $p = Start-Process -FilePath $bootstrap -ArgumentList $vsArgs -Verb RunAs -PassThru
    $null = $p.Handle   # keeps the exit code readable after the installer ends
    $p.WaitForExit()
    Say ("Installer finished with code " + $p.ExitCode)
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) { Fail "The Build Tools installer reported an error." }
    $Vs = Find-VS
    if (-not $Vs) { Fail "Build Tools still not found after installing. Restart the PC and run build.bat again." }
}
Say ("Using " + $Vs) "Green"

# Enter the Visual Studio developer environment (compiler, Windows SDK, CMake, Ninja on PATH).
Import-Module (Join-Path $Vs "Common7\Tools\Microsoft.VisualStudio.DevShell.dll")
Enter-VsDevShell -VsInstallPath $Vs -SkipAutomaticLocation -DevCmdArguments "-arch=x64 -host_arch=x64" | Out-Null
$extra = @(@(
    (Join-Path $Vs "VC\Tools\Llvm\x64\bin"),
    (Join-Path $Vs "Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin"),
    (Join-Path $Vs "Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja"),
    $ToolBin
) | Where-Object { Test-Path $_ })
$env:PATH = (($extra + @($env:PATH)) -join ";")

foreach ($tool in @("clang++", "cmake")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail ($tool + " was not found in the Build Tools install.") }
}
if (-not (Get-Command "ninja" -ErrorAction SilentlyContinue)) {
    Say "Ninja not found, downloading it into tools\bin"
    New-Item -ItemType Directory -Force -Path $ToolBin | Out-Null
    $nz = Join-Path $env:TEMP "ninja-win.zip"
    Download "https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-win.zip" $nz
    Expand-Archive -Path $nz -DestinationPath $ToolBin -Force
    $env:PATH = $ToolBin + ";" + $env:PATH
}
$clangVer = (& "clang++" --version | Select-Object -First 1)
Say ("Compiler: " + $clangVer)
if ($clangVer -match "version (\d+)\.") {
    if ([int]$Matches[1] -lt 20) { Fail ("ReXGlue needs Clang 20 or newer, found " + $clangVer + ". Update the Build Tools.") }
}
Say ("CMake: " + (& "cmake" --version | Select-Object -First 1))

# ---------------------------------------------------------------------------------------------
Step ("Getting the ReXGlue SDK " + $SdkVersion)
$RexGlue = Join-Path $SdkPrefix "bin\rexglue.exe"
$SdkStamp = Join-Path $SdkDir "version.txt"
$haveVer = ""
if (Test-Path $SdkStamp) { $haveVer = (Get-Content $SdkStamp -Raw).Trim() }
if (-not (Test-Path $RexGlue) -or $haveVer -ne $SdkVersion) {
    New-Item -ItemType Directory -Force -Path $SdkDir | Out-Null
    if (Test-Path $SdkPrefix) { Remove-Item -Recurse -Force $SdkPrefix }
    $zip = Join-Path $SdkDir ("rexglue-sdk-" + $SdkVersion + "-win-amd64.zip")
    Download ("https://github.com/rexglue/rexglue-sdk/releases/download/v" + $SdkVersion + "/rexglue-sdk-" + $SdkVersion + "-win-amd64.zip") $zip
    Expand-Archive -Path $zip -DestinationPath $SdkDir -Force
    Remove-Item -Force $zip
    Set-Content -Path $SdkStamp -Value $SdkVersion
}
if (-not (Test-Path $RexGlue)) { Fail ("rexglue.exe missing after unpacking the SDK (" + $RexGlue + ")") }
Say ("SDK ready: " + $SdkPrefix) "Green"

# ---------------------------------------------------------------------------------------------
Step "Checking your game files"

# Finds something rexglue can unpack: a Games on Demand header (a file with a <name>.data folder
# beside it) or an .iso. Returns $null if there is none.
function Find-Container([string]$path) {
    if (Test-Path $path -PathType Leaf) {
        if ($path -match "\.iso$") { return $path }
        if (Test-Path ($path + ".data") -PathType Container) { return $path }
        return $null
    }
    $iso = Get-ChildItem -Path $path -Recurse -File -Filter "*.iso" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($iso) { return $iso.FullName }
    $god = Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { Test-Path ($_.FullName + ".data") -PathType Container } | Select-Object -First 1
    if ($god) { return $god.FullName }
    return $null
}

if (-not (Test-Path (Join-Path $GameDir "default.xex"))) {
    Say "game\default.xex is missing. Point me at your Full Auto copy:"
    Say "  - a Games on Demand folder (the one holding 534507D5), or"
    Say "  - an .iso disc image, or"
    Say "  - a folder that already holds default.xex, Media, piLaunch, rtdXenon ..."
    if (-not $GameSource) { $GameSource = Read-Host "Drag it onto this window, then press Enter" }
    $GameSource = $GameSource.Trim().Trim('"')
    if (-not (Test-Path $GameSource)) { Fail ("Not found: " + $GameSource) }

    if (Test-Path (Join-Path $GameSource "default.xex")) {
        # Already extracted somewhere: link game\ to it instead of copying 3.5 GB.
        Say ("Linking game\ to " + $GameSource)
        cmd /c mklink /J "$GameDir" "$GameSource" | Out-Null
    } else {
        $container = Find-Container $GameSource
        if (-not $container) { Fail "No Games on Demand package or .iso found there." }
        Say ("Extracting " + $container + " into game\ (3.5 GB, a few minutes)")
        $code = Run $RexGlue @("vfs", "dump", $container, $GameDir)
        if ($code -ne 0) { Fail "Extracting the game files failed." }
    }
}
if (-not (Test-Path (Join-Path $GameDir "default.xex"))) { Fail "game\default.xex still missing." }
$xexHash = (Get-FileHash -Algorithm SHA1 (Join-Path $GameDir "default.xex")).Hash
Say ("default.xex SHA1 " + $xexHash)
if ($xexHash -ne "855AEFB7D2E227C8E71F33B6E68743CEC5FC6F9A") {
    Say "Note: this is not the XEX the project was set up with (Games on Demand v4). It may still work." "Yellow"
}

# ---------------------------------------------------------------------------------------------
$BuildPreset = "win-amd64-" + $Config.ToLower()

Step "Configuring (CMake)"
Push-Location $Root
$code = Run "cmake" @("--preset", "win-amd64")
if ($code -ne 0) { Pop-Location; Fail "CMake configure failed." }

# Codegen writes generated\default\sources.cmake, the list of recompiled C++ files. CMake reads
# that list only when it configures, so codegen runs first and CMake configures again after it.
# (One build on a fresh folder would run codegen and then link without the recompiled code.)
Step "Recompiling the game code (PowerPC to C++)"
$code = Run "cmake" @("--build", "--preset", $BuildPreset, "--target", "fullauto_codegen")
if ($code -ne 0) {
    Pop-Location
    if (Select-String -Path $Log -Pattern "Validation failed" -Quiet) {
        Fail "Codegen found functions it could not place. Tell Claude; the addresses are in the log."
    }
    Fail "Codegen failed. Tell Claude; the details are in the log."
}
$code = Run "cmake" @("--preset", "win-amd64")
if ($code -ne 0) { Pop-Location; Fail "CMake configure failed after codegen." }

Step ("Compiling (" + $Config + "). The first build takes a long time.")
$code = Run "cmake" @("--build", "--preset", $BuildPreset)
Pop-Location
if ($code -ne 0) { Fail "The build failed. Tell Claude; the details are in the log." }

$Exe = Join-Path $Root ("out\build\win-amd64\" + $Config + "\fullauto.exe")
if (-not (Test-Path $Exe)) { Fail ("Build finished but " + $Exe + " is missing.") }

# ---------------------------------------------------------------------------------------------
Step "Writing Play Full Auto.bat"
$play = @(
    "@echo off",
    "cd /d ""%~dp0""",
    ("start """" ""%~dp0out\build\win-amd64\" + $Config + "\fullauto.exe"" --title.game_root=""%~dp0game"" --app.user_root=""%~dp0user"" --app.log_root=""%~dp0logs""")
)
Set-Content -Path (Join-Path $Root "Play Full Auto.bat") -Value $play -Encoding ASCII
Say ""
Say "DONE. Double-click 'Play Full Auto.bat' to start the game." "Green"
Finish 0
