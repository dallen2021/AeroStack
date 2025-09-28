@echo off
cd /d "C:\Users\daniel\Desktop\Personal Coding\AeroStack\server" || exit /b 1
if not exist .venv (
  py -m venv .venv || exit /b 1
)
call .\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
