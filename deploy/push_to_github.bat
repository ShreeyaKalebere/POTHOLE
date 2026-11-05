@echo off
title Push Render Repository to GitHub
echo ================================================================
echo   Kolhapur Road Damage System - Push to GitHub for Render.com
echo ================================================================
echo.
cd /d "%~dp0\render_repo"

echo Current Git status:
git status
echo.

set /p REPO_URL="Enter your GitHub repository HTTPS URL (e.g., https://github.com/Shreeyakalebere11/road-damage-kolhapur.git): "

if "%REPO_URL%"=="" (
    echo [ERROR] No URL provided. Aborting.
    pause
    exit /b 1
)

echo.
echo Adding remote origin: %REPO_URL%
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo Renaming branch to main...
git branch -M main

echo.
echo Pushing code to GitHub...
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================================================
    echo [SUCCESS] Code pushed to GitHub successfully!
    echo.
    echo Next Steps on Render.com:
    echo 1. Go to https://dashboard.render.com
    echo 2. Click "New +" -> "Web Service"
    echo 3. Select your GitHub repository
    echo 4. Click "Deploy Web Service"
    echo ================================================================
) else (
    echo.
    echo [ERROR] Git push failed. Please check your GitHub credentials or permissions.
)

pause

