@echo off
echo ════════════════════════════════════════════════════════════════
echo   DEPLOYING TO ANDROID...
echo ════════════════════════════════════════════════════════════════
echo.
echo Make sure:
echo  1. Phone is connected via USB
echo  2. USB Debugging is enabled
echo  3. You allowed USB debugging on phone
echo.
echo Starting deployment...
echo.
wsl bash -c "cd /mnt/f/projetos/chordImporter/android-kivy && export PATH=\$PATH:~/.local/bin && buildozer android debug deploy run"
echo.
echo ════════════════════════════════════════════════════════════════
pause

