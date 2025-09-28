@echo off
setlocal
cd /d "C:\Users\daniel\Desktop\Personal Coding\AeroStack\web" || (echo [ERROR] web folder not found & exit /b 1)
npm i
npm run dev
endlocal
