@echo off
setlocal
cd /d "%~dp0"
set LOG=build.log
echo === SimplyMirror build started %DATE% %TIME% === > "%LOG%" 2>&1
echo App dir: %CD% >> "%LOG%" 2>&1
py --version >> "%LOG%" 2>&1
py -m pip --version >> "%LOG%" 2>&1

echo [1/3] Installing build tools (pyinstaller qrcode pillow)...
py -m pip install --upgrade pyinstaller qrcode pillow >> "%LOG%" 2>&1
if errorlevel 1 (
  echo BUILD FAILED at pip install. See build.log >> "%LOG%" 2>&1
  echo FAILED at pip install - full error in build.log
  pause
  exit /b 1
)

echo [2/3] Building SimplyMirror.exe with PyInstaller...
py -m PyInstaller --onefile --windowed --name SimplyMirror --icon app-icon.ico --add-data "phone_companion;phone_companion" app.py >> "%LOG%" 2>&1
if errorlevel 1 (
  echo BUILD FAILED at PyInstaller. See build.log and build\SimplyMirror\warn-*.txt >> "%LOG%" 2>&1
  echo FAILED at PyInstaller.
  echo --- last 60 lines of build.log: ---
  powershell -command "Get-Content build.log -Tail 60"
  pause
  exit /b 1
)

echo [3/3] Verifying...
dir dist\SimplyMirror.exe >> "%LOG%" 2>&1
if not exist "dist\SimplyMirror.exe" (
  echo EXE NOT FOUND after build - see build.log >> "%LOG%" 2>&1
  echo FAILED: exe missing. See build.log
  pause
  exit /b 1
)

echo.
echo SUCCESS: dist\SimplyMirror.exe ready. Log saved to build.log
echo SUCCESS: dist\SimplyMirror.exe ready. Log saved to build.log >> "%LOG%" 2>&1
pause
