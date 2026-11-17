$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Log = Join-Path $Root "build-log.txt"
"Build log, $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -Path $Log -Encoding UTF8
"Folder: $Root" | Add-Content -Path $Log -Encoding UTF8

function Write-Log {
    param([string]$Message)
    $Message | Tee-Object -FilePath $Log -Append
}

function Find-UsablePython {
    $candidates = [System.Collections.Generic.List[string]]::new()

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        foreach ($arguments in @(@("-0p"), @("list", "--format=exe"))) {
            try {
                $lines = & $pyCommand.Source @arguments 2>$null
                foreach ($line in $lines) {
                    if ("$line" -match '([A-Za-z]:\\.*?python(?:w)?\.exe)\s*$') {
                        $candidates.Add($Matches[1])
                    }
                }
            } catch {}
        }
    }

    foreach ($commandName in @("python.exe", "python3.exe")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command -and $command.Source) { $candidates.Add($command.Source) }
    }

    try {
        $whereOutput = & where.exe python.exe 2>$null
        foreach ($line in $whereOutput) {
            if ("$line" -match '^[A-Za-z]:\\.*python\.exe$') { $candidates.Add("$line") }
        }
    } catch {}

    $roots = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python"),
        (Join-Path $env:ProgramFiles "Python"),
        (Join-Path $env:ProgramFiles "Python Software Foundation")
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($base in $roots) {
        Get-ChildItem -Path $base -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                $candidate = Join-Path $_.FullName "python.exe"
                if (Test-Path $candidate) { $candidates.Add($candidate) }
            }
    }

    $seen = @{}
    $probe = 'import os,sys; p=getattr(sys,"_base_executable",sys.executable); sys.exit(0 if os.path.isfile(p) and os.path.getsize(p)>0 else 17)'
    foreach ($candidate in $candidates) {
        if (-not $candidate -or $seen.ContainsKey($candidate)) { continue }
        $seen[$candidate] = $true
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        try {
            & $candidate -c $probe *>$null
            if ($LASTEXITCODE -eq 0) { return (Resolve-Path -LiteralPath $candidate).Path }
        } catch {}
    }
    return $null
}

try {
    $required = @("simple_app.py", "core.py", "version.py", "update_checker.py", "USER-GUIDE.txt")
    foreach ($file in $required) {
        if (-not (Test-Path (Join-Path $Root $file))) {
            throw "Required file is missing: $file. Extract the entire repository ZIP before building."
        }
    }

    Write-Log "Looking for a usable Python interpreter..."
    $PythonExe = Find-UsablePython
    if (-not $PythonExe) {
        throw @"
No usable Python installation was found.

The Python command on this computer appears to point to the Microsoft Store
version, which can expose an empty launcher executable that PyInstaller
cannot use.

Install Python from https://www.python.org/downloads/windows/ (not the
Microsoft Store). During installation, enable the Python launcher if offered.
Then close and reopen this window and run build-windows.bat again.

You can check registered interpreters with:  py -0p
"@
    }

    $VersionLine = Select-String -Path (Join-Path $Root "version.py") -Pattern '^APP_VERSION\s*=\s*"([^"]+)"'
    if (-not $VersionLine) { throw "Could not read APP_VERSION from version.py." }
    $AppVersion = $VersionLine.Matches[0].Groups[1].Value
    $AppName = "Word Template Filler $AppVersion"

    Write-Log "Using Python: $PythonExe"
    & $PythonExe --version 2>&1 | ForEach-Object { Write-Log "$_" }

    Write-Log "Installing or updating build dependencies..."
    & $PythonExe -m pip install --upgrade pyinstaller lxml 2>&1 | ForEach-Object { Write-Log "$_" }
    if ($LASTEXITCODE -ne 0) { throw "Could not install PyInstaller and lxml." }

    Write-Log "Building $AppName..."
    $BuildArgs = @(
        "-m", "PyInstaller", "--clean", "--noconfirm", "--onefile", "--windowed",
        "--name", $AppName,
        "--distpath", (Join-Path $Root "dist"),
        "--workpath", (Join-Path $Root "build"),
        "--specpath", $Root,
        "--add-data", "USER-GUIDE.txt;.",
        (Join-Path $Root "simple_app.py")
    )
    & $PythonExe @BuildArgs 2>&1 | ForEach-Object { Write-Log "$_" }
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed. See the log above for details." }

    $Executable = Join-Path $Root "dist\$AppName.exe"
    if (-not (Test-Path $Executable)) { throw "PyInstaller reported success but the executable was not found: $Executable" }

    Remove-Item -Recurse -Force (Join-Path $Root "build") -ErrorAction SilentlyContinue
    Remove-Item -Force (Join-Path $Root "$AppName.spec") -ErrorAction SilentlyContinue
    Write-Log ""
    Write-Log "SUCCESS: $Executable"
    Write-Log "You can copy this executable anywhere on this Windows computer."
    if (-not $env:GITHUB_ACTIONS) {
        Start-Process explorer.exe -ArgumentList (Join-Path $Root "dist")
    }
    exit 0
}
catch {
    Write-Log ""
    Write-Log "BUILD FAILED: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "The build failed. The full log is saved to:"
    Write-Host "  $Log"
    Write-Host ""
    try { Start-Process notepad.exe -ArgumentList $Log } catch {}
    exit 1
}
