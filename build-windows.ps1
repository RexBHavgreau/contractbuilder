# Native build tools such as PyInstaller write normal progress messages to stderr.
# Continue those streams and use $LASTEXITCODE to detect a real build failure.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Log = Join-Path $Root "build-log.txt"
"Build log, $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content -Path $Log -Encoding UTF8
"Folder: $Root" | Add-Content -Path $Log -Encoding UTF8

function Write-Log {
    param([string]$Message)
    $Message | Tee-Object -FilePath $Log -Append
}

function Write-DiscoveryLog {
    param([string]$Message)
    Add-Content -LiteralPath $Log -Value $Message -Encoding UTF8
}

function Find-UsablePython {
    $candidates = [System.Collections.Generic.List[string]]::new()

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
                        [void]$candidates.Add($Matches[1])
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

    # setup-python supplies a known-good CPython directory in CI. Prefer it
    # directly rather than resolving a PATH alias.
    foreach ($runtimeRoot in @($env:pythonLocation, $env:Python_ROOT_DIR, $env:Python3_ROOT_DIR)) {
        if (-not $runtimeRoot) { continue }
        $runtimePython = Join-Path $runtimeRoot "python.exe"
        if (Test-Path -LiteralPath $runtimePython -PathType Leaf) {
            $runtimeFile = Get-Item -LiteralPath $runtimePython
            if ($runtimeFile.Length -gt 0) {
                Write-DiscoveryLog "Using configured Python runtime: $runtimePython"
                return (Resolve-Path -LiteralPath $runtimePython).Path
            }
        }
    }

    # Include both layouts: the Python install manager's %LOCALAPPDATA%\Python
    # and the older python.org installer layout under Programs\Python.
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
    $probe = 'import os,sys; p=getattr(sys,"_base_executable",sys.executable); sys.exit(0 if os.path.isfile(p) and os.path.getsize(p)>0 else 17)'
    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        $candidate = "$candidate".Trim()
        if ($seen.ContainsKey($candidate)) { continue }
        $seen[$candidate] = $true

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

        Write-DiscoveryLog "Testing Python candidate: $candidate"
        try {
            & $candidate -c $probe *>$null
            $probeExitCode = $LASTEXITCODE
            if ($probeExitCode -eq 0) {
                Write-DiscoveryLog "Accepted Python interpreter: $candidate"
                return (Resolve-Path -LiteralPath $candidate).Path
            }
            Write-DiscoveryLog "Rejected candidate (probe exit code $probeExitCode): $candidate"
        } catch {
            Write-DiscoveryLog "Rejected candidate (launch error): $candidate - $($_.Exception.Message)"
        }
    }

    Write-DiscoveryLog "No candidate passed the executable verification test."
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
No usable Python installation was found in the registered interpreters, PATH,
or the standard per-user/system installation folders.

Review the Python discovery details above in build-log.txt. The command named
'python' on PATH may belong to another application (for example, LibreOffice)
or may be a Microsoft Store execution alias. The build needs a regular CPython
installation whose underlying python.exe is present and usable.

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
