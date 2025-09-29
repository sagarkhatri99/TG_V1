@echo off
echo ========================================
echo TG Tools SDR API Setup and Testing
echo ========================================
echo.

REM Check if we're in the correct directory
if not exist "backend" (
    echo Error: backend directory not found!
    echo Please run this script from the TG_V1 root directory
    pause
    exit /b 1
)

echo 1. Setting up Python virtual environment...
cd backend

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo 2. Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo 3. Running database migrations...
alembic upgrade head
if errorlevel 1 (
    echo Error: Database migration failed
    echo You may need to initialize alembic first: alembic init alembic
    pause
    exit /b 1
)

echo.
echo 4. Creating test users...
python create_test_users.py
if errorlevel 1 (
    echo Error: Failed to create test users
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To test the API:
echo 1. Start the server: uvicorn main:app --reload
echo 2. In another terminal, run: python test_enterprise_access.py
echo.
echo Test Users Created:
echo - free@test.com (should be denied access)
echo - pro@test.com (should be denied access) 
echo - enterprise@test.com (should have full access)
echo - admin@test.com (should have full access)
echo Password for all: testpass123
echo.

REM Ask user if they want to start the server
set /p startserver="Would you like to start the server now? (y/n): "
if /i "%startserver%"=="y" (
    echo.
    echo Starting FastAPI server...
    echo Server will be available at http://localhost:8000
    echo Press Ctrl+C to stop the server
    echo.
    uvicorn main:app --reload
) else (
    echo.
    echo Setup complete! You can start the server manually with:
    echo uvicorn main:app --reload
)

pause