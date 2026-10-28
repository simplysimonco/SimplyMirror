@echo off
setlocal
cd /d "%~dp0"
set OUT=diagnostics-pc.txt
echo === Mirror Helper PC diagnostics %DATE% %TIME% === > "%OUT%"
echo Computer: %COMPUTERNAME%  User: %USERNAME% >> "%OUT%"
ver >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- python --- >> "%OUT%"
py --version >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- app files --- >> "%OUT%"
dir >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- dist --- >> "%OUT%"
dir dist >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- tools dir --- >> "%OUT%"
dir tools 2>> "%OUT%" >> "%OUT%"
echo. >> "%OUT%"
echo --- mirror-helper.log tail (80 lines) --- >> "%OUT%"
powershell -command "if (Test-Path mirror-helper.log) { Get-Content mirror-helper.log -Tail 80 } else { 'no mirror-helper.log yet' }" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- adb version / devices (tries ./tools first) --- >> "%OUT%"
if exist "tools\platform-tools\adb.exe" (
  tools\platform-tools\adb.exe version >> "%OUT%" 2>&1
  tools\platform-tools\adb.exe devices -l >> "%OUT%" 2>&1
) else if exist "tools\scrcpy-win64\adb.exe" (
  tools\scrcpy-win64\adb.exe version >> "%OUT%" 2>&1
  tools\scrcpy-win64\adb.exe devices -l >> "%OUT%" 2>&1
) else (
  adb version >> "%OUT%" 2>&1
  adb devices -l >> "%OUT%" 2>&1
)
echo. >> "%OUT%"
echo --- scrcpy version --- >> "%OUT%"
if exist "tools\scrcpy-win64\scrcpy.exe" (
  tools\scrcpy-win64\scrcpy.exe --version >> "%OUT%" 2>&1
) else (
  scrcpy --version >> "%OUT%" 2>&1
)
echo.
echo Saved to %CD%\%OUT%
echo Paste the whole file back here for debugging.
echo Also send: build.log (after build_exe.bat) and mirror-helper.log if present.
pause
