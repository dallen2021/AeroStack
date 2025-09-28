@echo off
setlocal enabledelayedexpansion

REM === Path to your repo ===
set "REPO_DIR=C:\Users\daniel\Desktop\Personal Coding\AeroStack"

if not exist "%REPO_DIR%" (
  echo Repo directory not found: "%REPO_DIR%"
  exit /b 1
)

cd /d "%REPO_DIR%"

REM Determine current branch (default to main if detection fails)
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%b"
if not defined BRANCH set "BRANCH=main"

REM Build commit message: use all args, or timestamped default
set "MSG=%*"
if "%MSG%"=="" (
  for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm\""') do set "MSG=Update %%i"
)

echo ----------------------------------------
echo Repo : %REPO_DIR%
echo Branch: %BRANCH%
echo Message: %MSG%
echo ----------------------------------------

REM Stage changes
git add -A

REM Commit only if there is something to commit
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "%MSG%"
) else (
  echo Nothing to commit; working tree clean.
)

REM Pull latest with rebase (safer history)
git pull --rebase origin %BRANCH%
if errorlevel 1 (
  echo.
  echo Pull failed (likely due to conflicts). Resolve conflicts, then re-run push.bat.
  exit /b 1
)

REM First push: set upstream if needed
git rev-parse --abbrev-ref --symbolic-full-name @{u} >nul 2>&1
if errorlevel 1 (
  git push -u origin %BRANCH%
) else (
  git push origin %BRANCH%
)

echo.
echo ✅ Done.
endlocal
