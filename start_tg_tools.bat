@echo off
title TG Tools - Docker Startup
echo.
echo =========================================================
echo 🚀 TG TOOLS - COMPLETE DOCKER SETUP
echo =========================================================
echo.
echo Starting all services with SDR Lead Profiles feature...
echo.

REM Check if Docker is running
docker version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running or not installed.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo ✅ Docker is running
echo.

REM Build and start all services
echo 🔧 Building and starting all services...
docker-compose up --build -d

if errorlevel 1 (
    echo ❌ Failed to start services
    echo Check the error messages above
    pause
    exit /b 1
)

echo ✅ Services started successfully
echo.

REM Wait for services to be ready
echo ⏳ Waiting for services to initialize...
echo This may take 30-60 seconds on first run...
echo.

REM Install Python requests for testing (if not already installed)
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import requests" >nul 2>&1
    if errorlevel 1 (
        echo 📦 Installing Python requests for testing...
        python -m pip install requests >nul 2>&1
    )
    
    REM Run validation tests
    echo 🧪 Running validation tests...
    python test_docker_setup.py
    
    if not errorlevel 1 (
        echo.
        echo =========================================================
        echo 🎉 SUCCESS! TG Tools is ready to use
        echo =========================================================
        echo.
        echo 🌐 Access Points:
        echo    • Frontend:     http://localhost:3000
        echo    • Backend API:  http://localhost:8000  
        echo    • API Docs:     http://localhost:8000/docs
        echo    • Health Check: http://localhost:8000/health
        echo.
        echo 👥 Test Users (password: testpass123):
        echo    • free@test.com       - FREE plan (❌ No SDR access)
        echo    • pro@test.com        - PRO plan (❌ No SDR access)
        echo    • enterprise@test.com - ENTERPRISE plan (✅ Full SDR access)
        echo    • admin@test.com      - ADMIN plan (✅ Full SDR access)
        echo.
        echo 🎯 SDR Lead Profiles Feature:
        echo    • Enterprise/Admin ONLY
        echo    • No limits on profiles/leads
        echo    • Sample data pre-loaded
        echo.
        echo 📋 Docker Management:
        echo    • View logs:    docker-compose logs -f
        echo    • Stop services: docker-compose down
        echo    • Restart:      docker-compose restart
        echo.
    ) else (
        echo.
        echo ⚠️ Some tests failed, but services might still be working
        echo Check http://localhost:8000/health manually
        echo.
    )
) else (
    echo ⚠️ Python not found - skipping validation tests
    echo Services should be available at:
    echo    • Frontend: http://localhost:3000
    echo    • Backend:  http://localhost:8000
    echo.
)

echo Press any key to open the application in your browser...
pause >nul

REM Open browser to frontend
start http://localhost:3000

echo.
echo 🎊 TG Tools is now running!
echo Press any key to exit...
pause >nul