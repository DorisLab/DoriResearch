#Requires -Version 7.4
[CmdletBinding()]
param(
    [ValidateSet('All','Standard','Security')][string]$Mode = 'All',
    [ValidateSet('All','Backend','Frontend')][string]$Target = 'All',
    [string]$Uv = 'uv'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
function Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed ($LASTEXITCODE)" }
}
$oldNoEnv = $env:UV_NO_ENV_FILE
$env:UV_NO_ENV_FILE = '1'
try {
    Push-Location $root
    try {
        Checked git @('diff','--check')
        Checked node @('--test','scripts/release.test.mjs')
    } finally { Pop-Location }
    if ($Target -in @('All','Backend')) {
        Push-Location (Join-Path $root 'backend')
        try {
            Checked $Uv @('sync','--locked')
            if ($Mode -in @('All','Standard')) {
                Checked $Uv @('run','--no-sync','ruff','format','--check','.', '../run.py')
                Checked $Uv @('run','--no-sync','ruff','check','.', '../run.py')
                Checked $Uv @('run','--no-sync','mypy')
                Checked $Uv @('run','--no-sync','python','scripts/check_size.py')
                Checked $Uv @('run','--no-sync','pytest')
                Checked $Uv @('build','--python', (Join-Path $root 'backend/.venv/Scripts/python.exe'),'--no-build-isolation','--out-dir', (Join-Path $root 'dist/python'))
            }
            if ($Mode -in @('All','Security')) {
                $requirements = Join-Path $root 'dist/audit-requirements.txt'
                New-Item -ItemType Directory -Path (Split-Path $requirements -Parent) -Force | Out-Null
                Checked $Uv @('export','--locked','--all-groups','--no-emit-project','--format','requirements-txt','--output-file',$requirements)
                Checked $Uv @('run','--no-sync','pip-audit','--require-hashes','--disable-pip','--no-deps','-r',$requirements)
            }
        } finally { Pop-Location }
    }
    if ($Target -in @('All','Frontend')) {
        Push-Location (Join-Path $root 'frontend')
        try {
            if ($Mode -in @('All','Standard')) {
                Checked npm.cmd @('ci','--ignore-scripts','--no-audit','--no-fund')
                foreach ($name in @('typecheck','lint','test','build','build:desktop')) {
                    Checked npm.cmd @('run',$name)
                }
            }
            if ($Mode -in @('All','Security')) {
                Checked npm.cmd @('audit','--package-lock-only','--audit-level=low','--registry=https://registry.npmjs.org')
            }
        } finally { Pop-Location }
    }
} finally { $env:UV_NO_ENV_FILE = $oldNoEnv }
