@echo off
REM Batch script to run sorter.py and zipper.py in sequence, only running zipper if sorter succeeds

REM Activate virtual environment if needed (uncomment and edit if using venv)
REM call venv\Scripts\activate

REM Run sorter.py
python fullauto\sorter.py
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] sorter.py failed. Zipper will NOT run.
    pause
    exit /b %ERRORLEVEL%
)

REM Run zipper.py
python fullauto\zipper.py

pause