# Setup for the Research library and Library Manager - run it with Setup.bat in the library folder.
# Safe to run again at any time (after moving the folder, on a new PC, or to repair): it only adds what is missing.
#   1. Python 3.14 (64-bit, with Tk)      - finds it, or offers to install it
#   2. the library's Python environment   - _scripts\.venv, rebuilt if it doesn't work on this PC (e.g. a new computer)
#   3. the Python packages                - from _scripts\requirements.txt
#   4. optional tools                     - offers Chrome (if neither Chrome nor Edge) and antiword (via Git for Windows)
#   5. desktop shortcut                   - "Library Manager", pointing at this copy of the folder
#   6. a final check                      - _scripts\check_setup.py
param([switch]$Yes, [switch]$NoShortcut)   # -Yes: answer Yes to every question; -NoShortcut: leave the desktop alone
$ErrorActionPreference = "Continue"   # Python/pip print warnings on stderr; success is judged by exit codes
$Scripts = $PSScriptRoot
$Root = Split-Path $Scripts -Parent
$Venv = Join-Path $Scripts ".venv"
$VPy = Join-Path $Venv "Scripts\python.exe"
$VPyw = Join-Path $Venv "Scripts\pythonw.exe"

function Say($text, $color = "Gray") { Write-Host $text -ForegroundColor $color }
function Step($n, $text) { Write-Host ""; Write-Host "[$n/6] $text" -ForegroundColor Cyan }
function Ask($q) {
    if ($Yes) { return $true }
    $a = Read-Host "$q [Y/n]"
    return ($a -eq "" -or $a -match "^[yY]")
}
function Have-Winget { return [bool](Get-Command winget -ErrorAction SilentlyContinue) }
function Winget-Install($id) {
    winget install -e --id $id --accept-package-agreements --accept-source-agreements --silent
    return ($LASTEXITCODE -eq 0)
}

Say "Library Manager setup" White
Say "Library folder: $Root"

# ------------------------------------------------------------------ 1. Python
Step 1 "Python 3.14"
function Find-Python {
    $candidates = @("C:\Python314\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
                    "$env:ProgramFiles\Python314\python.exe")
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    try {
        $p = & py -3.14 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $p) { return $p.Trim() }
    } catch { }
    return $null
}
$Py = Find-Python
if (-not $Py) {
    Say "Python 3.14 is not installed on this PC." Yellow
    if (Ask "Download and install Python 3.14 from python.org now?") {
        if (Have-Winget) {
            Say "Installing with winget..."
            winget install -e --id Python.Python.3.14 --scope user --accept-package-agreements --accept-source-agreements --silent
        } else {
            Say "Finding the newest Python 3.14 on python.org..."
            $index = (Invoke-WebRequest "https://www.python.org/ftp/python/" -UseBasicParsing).Content
            $n = ([regex]::Matches($index, 'href="3\.14\.(\d+)/"') | ForEach-Object { [int]$_.Groups[1].Value } | Measure-Object -Maximum).Maximum
            $ver = "3.14.$n"
            $exe = Join-Path $env:TEMP "python-$ver-amd64.exe"
            Invoke-WebRequest "https://www.python.org/ftp/python/$ver/python-$ver-amd64.exe" -OutFile $exe -UseBasicParsing
            Say "Installing Python $ver (this takes a minute)..."
            Start-Process $exe -ArgumentList "/quiet InstallAllUsers=0 PrependPath=0 Include_tcltk=1 Include_pip=1 Include_launcher=1" -Wait
        }
        $Py = Find-Python
    }
    if (-not $Py) {
        Say "Python 3.14 is needed. Install it from https://www.python.org/downloads/ (keep 'tcl/tk' ticked), then run Setup again." Red
        exit 1
    }
}
Say "Using $Py" Green

# ------------------------------------------------------------------ 2. the library's Python environment
Step 2 "The library's Python environment (_scripts\.venv)"
$works = $false
if (Test-Path $VPy) {
    & $VPy -c "import sys, tkinter; assert sys.version_info[:2] == (3, 14)" 2>$null
    $works = ($LASTEXITCODE -eq 0)
    if ($works) {   # the .exe launchers (pip, yt-dlp...) hold the folder path, so a moved environment breaks them
        & (Join-Path $Venv "Scripts\pip.exe") --version 2>$null | Out-Null
        $works = ($LASTEXITCODE -eq 0)
    }
}
if ($works) {
    Say "Already set up and working." Green
} else {
    if (Test-Path $Venv) {   # e.g. copied from another PC: keep it aside rather than delete it
        $old = ".venv.old-" + (Get-Date -Format "yyyyMMdd-HHmmss")
        Rename-Item $Venv $old -ErrorAction Stop
        Say "The old environment doesn't work on this PC - moved it aside to _scripts\$old (you can delete it later)." Yellow
    }
    Say "Creating a fresh environment..."
    & $Py -m venv $Venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VPy)) { Say "Could not create the environment." Red; exit 1 }
    Say "Created." Green
}

# ------------------------------------------------------------------ 3. packages
Step 3 "Python packages (first time: several minutes, about 400 MB)"
& $VPy -m pip install --upgrade pip --disable-pip-version-check --quiet
$pipArgs = @("-m", "pip", "install", "-r", (Join-Path $Scripts "requirements.txt"), "--disable-pip-version-check")
if ($works) { $pipArgs += "--quiet" }   # re-run: only show something if a package actually changes
& $VPy @pipArgs
if ($LASTEXITCODE -ne 0) { Say "Some packages could not be installed - see the messages above (is the internet connected?)." Red; exit 1 }
Say "Packages are installed." Green

# ------------------------------------------------------------------ 4. optional tools
Step 4 "Optional tools"
$missing = (& $VPy (Join-Path $Scripts "check_setup.py") --missing) -split ","
if ($missing -contains "browser") {
    Say "No Chrome or Edge found - they make the clean one-page recipe PDFs." Yellow
    if ((Have-Winget) -and (Ask "Install Google Chrome now?")) { if (Winget-Install "Google.Chrome") { Say "Chrome installed." Green } }
}
if ($missing -contains "antiword") {
    Say "antiword not found - it reads old Word .doc files (it comes with Git for Windows, about 300 MB)." Yellow
    if ((Have-Winget) -and (Ask "Install Git for Windows now?")) { if (Winget-Install "Git.Git") { Say "Git for Windows installed." Green } }
}
if (-not ($missing | Where-Object { $_ })) { Say "Nothing else needed." Green }

# ------------------------------------------------------------------ 5. desktop shortcut
Step 5 "Desktop shortcut"
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Library Manager.lnk"
$sh = New-Object -ComObject WScript.Shell
$target = Join-Path $Scripts "library_manager.pyw"
$current = if (Test-Path $lnk) { $sh.CreateShortcut($lnk).Arguments } else { "" }
if ($NoShortcut) {
    Say "Skipped." Gray
} elseif ($current -eq "`"$target`"") {
    Say "The Library Manager shortcut already points at this folder." Green
} elseif (Ask ($(if ($current) { "Update the desktop shortcut to open this copy of the library?" } else { "Put a Library Manager shortcut on the desktop?" }))) {
    $s = $sh.CreateShortcut($lnk)
    $s.TargetPath = $VPyw
    $s.Arguments = "`"$target`""
    $s.WorkingDirectory = $Root
    $s.IconLocation = (Join-Path $Scripts "library_manager.ico") + ",0"
    $s.Description = "Add, browse and read the Research library"
    $s.Save()
    Say "Shortcut saved: $lnk" Green
}

# ------------------------------------------------------------------ 6. final check
Step 6 "Checking everything"
& $VPy (Join-Path $Scripts "check_setup.py")
$ok = ($LASTEXITCODE -eq 0)
Write-Host ""
if ($ok) { Say "Setup finished. Start Library Manager from the desktop shortcut or 'Library Manager.vbs'." Green }
else { Say "Setup finished with problems - see the NEED lines above." Red; exit 1 }
