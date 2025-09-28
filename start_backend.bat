@echo off
setlocal

rem ===== config =====
set "SRV_DIR=C:\Users\daniel\Desktop\Personal Coding\AeroStack\server"

rem ===== checks =====
if not exist "%SRV_DIR%" goto MISSING_DIR
cd /d "%SRV_DIR%"

rem ===== venv create (3.13) =====
if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual env with Python 3.13 ...
  py -3.13 -m venv .venv
  if errorlevel 1 goto VENV_FAIL
)

rem ===== activate =====
call ".venv\Scripts\activate"
if errorlevel 1 goto ACT_FAIL

rem ===== tooling =====
echo [INFO] Upgrading pip setuptools wheel ...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto PIP_FAIL

rem ===== install deps (wheels only) =====
echo [INFO] Installing requirements as wheels only ...
python -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto REQ_FAIL

rem ===== run =====
echo [INFO] Starting Uvicorn on http://127.0.0.1:8000 ...
python -m uvicorn main:app --reload --port 8000
goto END

:MISSING_DIR
echo [ERROR] Directory not found: "%SRV_DIR%"
exit /b 1

:VENV_FAIL
echo [ERROR] Failed to create .venv with Python 3.13 . Check "py -3.13 -V".
exit /b 1

:ACT_FAIL
echo [ERROR] Failed to activate .venv .
exit /b 1

:PIP_FAIL
echo [ERROR] Failed to upgrade pip tooling .
exit /b 1

:REQ_FAIL
echo [ERROR] Failed to install requirements on Python 3.13 .
echo        Ensure requirements include: numpy>=2.1,<2.3  and  scipy>=1.14,<1.16
exit /b 1

:END
endlocal
