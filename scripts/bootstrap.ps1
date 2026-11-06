param(
    [ValidateSet('install', 'update')][string]$Action = 'install',
    [string]$GameDir = ''
)
# Windows PowerShell 5.1+; dependencies: Git and Python 3 (py launcher).
$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/BDadmehr0/deadlock-persian.git'
$ref = 'arena/435414a8-deadlock-persian'
$dir = Join-Path $env:LOCALAPPDATA 'DeadlockPersian'
function Run-Git {
    & git @args
    if ($LASTEXITCODE -ne 0) { throw "Git failed with exit code $LASTEXITCODE" }
}
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required. Install Git for Windows and restart PowerShell.' }
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python 3 is required. Install Python for Windows with the py launcher.' }
    if (-not (Test-Path -LiteralPath $dir)) {
        if ($Action -eq 'update') { throw 'No checkout found. Run the install command first.' }
        $stage = Join-Path $env:LOCALAPPDATA ('.deadlock-persian-clone-' + [guid]::NewGuid().ToString('N'))
        try {
            Run-Git clone --filter=blob:none --no-checkout --single-branch --branch $ref $repo $stage
            Run-Git -C $stage sparse-checkout init --no-cone
            Run-Git -C $stage sparse-checkout set --no-cone '/.gitignore' '/data/citadel_main_english.txt' '/data/pak82_dir.vpk' '/tools/translate_common.py' '/tools/persian_terms.py' '/scripts/install_windows.py'
            Run-Git -C $stage checkout $ref
            Move-Item -LiteralPath $stage -Destination $dir
        } finally {
            if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
        }
    } else {
        if (-not (Test-Path -LiteralPath (Join-Path $dir '.git'))) { throw "Not a Git checkout: $dir" }
        $origin = (& git -C $dir remote get-url origin); if ($LASTEXITCODE -ne 0 -or $origin -ne $repo) { throw "Unexpected Git origin: $dir" }
        $branch = (& git -C $dir symbolic-ref --short HEAD); if ($LASTEXITCODE -ne 0 -or $branch -ne $ref) { throw "Unexpected branch: $dir" }
        $changes = (& git -C $dir status --porcelain --untracked-files=all); if ($LASTEXITCODE -ne 0 -or $changes) { throw "Local changes found in $dir; inspect them before updating." }
        Run-Git -C $dir pull --ff-only origin $ref
    }
    $installer = Join-Path $dir 'scripts/install_windows.py'
    if ($GameDir) { & py -3 $installer $Action --game-dir $GameDir } else { & py -3 $installer $Action }
    if ($LASTEXITCODE -ne 0) { throw "Installer failed with exit code $LASTEXITCODE" }
} catch {
    [Console]::Error.WriteLine($_.ToString())
    exit 1
}
