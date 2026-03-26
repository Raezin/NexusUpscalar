@echo off
echo Starting NexusUpscaler...
echo.

REM Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    echo Installing dependencies...
    venv\Scripts\pip install -r requirements.txt
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Starting application...
python main.py

pause