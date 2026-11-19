@echo off
chcp 65001 >nul
echo Compilant Xoriguer Cercador...
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --clean XoriguerCercador.spec
if errorlevel 1 (echo [ERROR] La compilacio ha fallat. & pause & exit /b 1)
copy /y dist\XoriguerCercador.exe XoriguerCercador.exe >nul
echo [OK] XoriguerCercador.exe creat.
pause
