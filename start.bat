@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
  echo Creating backend virtual environment...
  python -m venv backend\venv
)

echo Installing backend dependencies...
call backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo Backend dependency installation failed.
  pause
  exit /b 1
)

if not exist "backend\skillbridge.db" (
  echo Preparing demo database...
  pushd backend
  call venv\Scripts\python.exe seed.py
  if errorlevel 1 (
    popd
    echo Database seeding failed.
    pause
    exit /b 1
  )
  popd
)
start "SkillBridge AI API" cmd /k "cd /d ""%~dp0backend"" && venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

if not exist "frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd frontend
  call npm.cmd install
  if errorlevel 1 (
    popd
    echo Frontend dependency installation failed.
    pause
    exit /b 1
  )
  popd
)

start "SkillBridge AI web" cmd /k "cd /d ""%~dp0frontend"" && npm.cmd run dev"
echo.
echo SkillBridge AI is starting.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000/docs
echo.
endlocal
