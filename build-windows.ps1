# Builds Word Template Filler into a single Windows executable.
#
# Runs under Windows PowerShell 5.1 (what build-windows.bat starts) and under
# PowerShell 7. Two 5.1 behaviours shape this script:
#   - Arguments passed to a program lose any embedded double quotes, so a
#     `python -c "..."` probe containing quotes arrives broken. Python is
#     therefore only ever given a script FILE to run, never inline code.
#   - Tee-Object and Out-File write UTF-16, which garbles a UTF-8 log. Every
#     log line goes through Add-Content -Encoding UTF8 instead.
#
# Native build tools such as PyInstaller write normal progress to stderr.
# Continue on those streams and use $LASTEXITCODE to detect real failures.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Log = Join-Path $Root "build-log.txt"
"Build log, $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -Path $Log -Encoding UTF8
"Folder: $Root" | Add-Content -Path $Log -Encoding UTF8
"PowerShell: $($PSVersionTable.PSVersion)" | Add-Content -Path $Log -Encoding UTF8

function Write-Log {
    param([string]$Message)
    Write-Host $Message
    Add-Content -LiteralPath $Log -Value $Message -Encoding UTF8
}

function Write-DiscoveryLog {
    param([string]$Message)
    Add-Content -LiteralPath $Log -Value $Message -Encoding UTF8
}

# What a Python must manage for this build: its real python.exe exists (the
# Microsoft Store alias has an empty one), it is new enough, it has tkinter
# for the app window, and pip to install PyInstaller. LibreOffice's bundled
# Python, which is often first on PATH, has neither tkinter nor pip.
$ProbeSource = @'
import os
import sys

base = getattr(sys, "_base_executable", sys.executable)
if not (os.path.isfile(base) and os.path.getsize(base) > 0):
    print("its own python.exe is missing or empty: " + base)
    sys.exit(17)
if sys.version_info < (3, 9):
    print("Python %d.%d is too old; 3.9 or later is needed" % sys.version_info[:2])
    sys.exit(18)
try:
    import tkinter  # noqa: F401
except Exception as exc:
    print("it has no tkinter, which the app window needs (" + str(exc) + ")")
    sys.exit(19)
try:
    import pip  # noqa: F401
except Exception as exc:
    print("it has no pip, which the build needs to install PyInstaller (" + str(exc) + ")")
    sys.exit(20)
print("usable: Python %d.%d.%d" % sys.version_info[:3])
'@
$ProbeFile = Join-Path ([System.IO.Path]::GetTempPath()) "word-template-filler-python-probe.py"
[System.IO.File]::WriteAllText($ProbeFile, $ProbeSource, (New-Object System.Text.UTF8Encoding($false)))

function Test-PythonCandidate {
    param([string]$Candidate)
    Write-DiscoveryLog "Testing Python candidate: $Candidate"
    try {
        $output = & $Candidate $ProbeFile 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
    } catch {
        Write-DiscoveryLog "  rejected: it could not be started ($($_.Exception.Message))"
        return $false
    }
    $said = ($output -join " ").Trim()
    if ($code -eq 0) {
        Write-DiscoveryLog "  accepted: $said"
        return $true
    }
    if (-not $said) { $said = "no explanation was printed" }
    Write-DiscoveryLog "  rejected (exit code $code): $said"
    return $false
}

function Find-UsablePython {
    $candidates = [System.Collections.Generic.List[string]]::new()

    # An explicit choice wins: set BUILD_PYTHON to a python.exe to use it.
    if ($env:BUILD_PYTHON) {
        Write-DiscoveryLog "BUILD_PYTHON is set: $env:BUILD_PYTHON"
        [void]$candidates.Add($env:BUILD_PYTHON)
    }

    # setup-python in GitHub Actions names its runtime here. It goes through the
    # same test as everything else, so the build server exercises the probe too.
    foreach ($runtimeRoot in @($env:pythonLocation, $env:Python_ROOT_DIR, $env:Python3_ROOT_DIR)) {
        if ($runtimeRoot) {
            Write-DiscoveryLog "Configured Python runtime: $runtimeRoot"
            [void]$candidates.Add((Join-Path $runtimeRoot "python.exe"))
        }
    }

    # The Python install manager places managed installations under
    # %LOCALAPPDATA%\Python and registers them with the py launcher.
    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        Write-DiscoveryLog "Python launcher: $($pyCommand.Source)"
        foreach ($arguments in @(@("-0p"), @("list", "--format=exe"))) {
            try {
                $lines = & $pyCommand.Source @arguments 2>$null
                foreach ($line in $lines) {
                    Write-DiscoveryLog "py $($arguments -join ' '): $line"
                    if ("$line" -match '(?i)([A-Z]:\\.*?pythonw?\.exe)\s*$') {
                        [void]$candidates.Add(($Matches[1] -replace '(?i)pythonw\.exe$', 'python.exe'))
                    }
                }
            } catch {
                Write-DiscoveryLog "Python launcher query failed: $($_.Exception.Message)"
            }
        }
    } else {
        Write-DiscoveryLog "Python launcher (py.exe): not found on PATH."
    }

    foreach ($commandName in @("python.exe", "python3.exe")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command -and $command.Source) {
            Write-DiscoveryLog "$commandName on PATH: $($command.Source)"
            [void]$candidates.Add($command.Source)
        }
    }

    try {
        $whereOutput = & where.exe python.exe 2>$null
        foreach ($line in $whereOutput) {
            if ("$line" -match '(?i)^[A-Z]:\\.*python\.exe$') {
                [void]$candidates.Add("$line")
            }
        }
    } catch {
        Write-DiscoveryLog "where.exe python.exe could not be run: $($_.Exception.Message)"
    }

    # Both layouts: the Python install manager's %LOCALAPPDATA%\Python and the
    # older python.org installer layout under Programs\Python.
    $roots = @(
        (Join-Path $env:LOCALAPPDATA "Python"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python"),
        (Join-Path $env:ProgramFiles "Python"),
        (Join-Path $env:ProgramFiles "Python Software Foundation")
    ) | Where-Object { $_ }

    foreach ($base in $roots) {
        if (-not (Test-Path -LiteralPath $base -PathType Container)) {
            Write-DiscoveryLog "Install folder not present: $base"
            continue
        }
        Write-DiscoveryLog "Searching install folder: $base"
        $directPython = Join-Path $base "python.exe"
        if (Test-Path -LiteralPath $directPython -PathType Leaf) {
            [void]$candidates.Add($directPython)
        }
        Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                $candidate = Join-Path $_.FullName "python.exe"
                if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                    [void]$candidates.Add($candidate)
                }
            }
    }

    $seen = @{}
    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        $candidate = "$candidate".Trim().Trim('"')
        if ($seen.ContainsKey($candidate.ToLowerInvariant())) { continue }
        $seen[$candidate.ToLowerInvariant()] = $true

        if ($candidate -match '(?i)\\WindowsApps\\') {
            Write-DiscoveryLog "Skipping Windows app execution alias: $candidate"
            continue
        }
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            Write-DiscoveryLog "Candidate does not exist: $candidate"
            continue
        }
        $candidateFile = Get-Item -LiteralPath $candidate -ErrorAction SilentlyContinue
        if (-not $candidateFile -or $candidateFile.Length -eq 0) {
            Write-DiscoveryLog "Candidate is empty or unreadable: $candidate"
            continue
        }
        if (Test-PythonCandidate $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    Write-DiscoveryLog "No candidate passed the test."
    return $null
}

try {
    $required = @("simple_app.py", "core.py", "version.py", "update_checker.py", "self_update.py",
                  "publisher_profiles.py", "USER-GUIDE.txt")
    foreach ($file in $required) {
        if (-not (Test-Path (Join-Path $Root $file))) {
            throw "Required file is missing: $file. Extract the entire repository ZIP before building."
        }
    }

    Write-Log "Looking for a usable Python interpreter..."
    $PythonExe = Find-UsablePython
    if (-not $PythonExe) {
        throw @"
No usable Python was found. Each Python that was tried, and why it was turned
down, is listed above in build-log.txt.

The build needs a regular Python 3.9 or later with tkinter and pip, which the
installer from https://www.python.org/downloads/windows/ provides. The
'python' first on PATH may belong to another program (LibreOffice ships one
without tkinter or pip) or be a Microsoft Store alias.

To name a Python explicitly, set BUILD_PYTHON to its python.exe, for example:
    set BUILD_PYTHON=C:\Users\you\AppData\Local\Python\pythoncore-3.14-64\python.exe
and run build-windows.bat again from the same window. Registered Pythons are
listed by:  py -0p
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
    Remove-Item -Force $ProbeFile -ErrorAction SilentlyContinue
    Write-Log ""
    Write-Log "SUCCESS: $Executable"
    Write-Log "You can copy this executable anywhere on this Windows computer."
    if (-not $env:GITHUB_ACTIONS) {
        Start-Process explorer.exe -ArgumentList (Join-Path $Root "dist")
    }
    exit 0
}
catch {
    Remove-Item -Force $ProbeFile -ErrorAction SilentlyContinue
    Write-Log ""
    Write-Log "BUILD FAILED: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "The build failed. The full log is saved to:"
    Write-Host "  $Log"
    Write-Host ""
    if (-not $env:GITHUB_ACTIONS) {
        try { Start-Process notepad.exe -ArgumentList $Log } catch {}
    }
    exit 1
}

# Temporary negative test: the CI parser must reject this incomplete statement.
if (
