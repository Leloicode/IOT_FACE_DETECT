@echo off
REM Khoi dong Flask backend.
REM Tu dong kiem tra Python/venv/dependencies; neu thieu se tu cai (set up).

setlocal EnableExtensions
cd /d "%~dp0python_app"
set "PYTHONUTF8=1"

REM --- Chon Python (u tien 3.11/3.10/3.9) ---
set "PY="
for %%V in (3.11 3.10 3.9) do (
    if not defined PY (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 set "PY=py -%%V"
    )
)

if not defined PY (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else if exist "C:\Program Files\Python311\python.exe" (
        set "PY=C:\Program Files\Python311\python.exe"
    )
)

%PY% --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Chua co Python phu hop. Chay setup.bat de TU CAI...
    call "%~dp0setup.bat"
    REM Sau khi setup xong, kiem tra lai
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else if exist "C:\Program Files\Python311\python.exe" (
        set "PY=C:\Program Files\Python311\python.exe"
    )
)

REM --- Kiem tra venv: neu thieu HOAC dung Python 3.12/3.13 thi goi setup ---
set "NEED_SETUP="
if not exist venv set "NEED_SETUP=1"
if not exist venv\Scripts\python.exe goto :SKIP_VENV_CHECK2
venv\Scripts\python.exe -c "import sys; sys.exit(0 if (3,9) <= sys.version_info[:2] <= (3,11) else 1)" >nul 2>&1
if errorlevel 1 set "NEED_SETUP=1"
:SKIP_VENV_CHECK2
if defined NEED_SETUP (
    echo [INFO] venv thieu/khong phu hop. Chay setup.bat de tu cai...
    call "%~dp0setup.bat"
    exit /b 1
)

REM --- Kiem tra dependencies, neu thieu thi tu cai ---
call venv\Scripts\activate.bat >nul 2>&1
%PY% -c "import flask, flask_cors, face_recognition, cv2, paho.mqtt, waitress" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Thieu thu vien. Dang cai dat...
    %PY% -m pip install https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp311-cp311-win_amd64.whl
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Cai thu vien that bai. Chay setup.bat.
        pause
        exit /b 1
    )
)

echo [INFO] Dang kiem tra va ha cap Numpy de sua loi tuong thich dlib...
%PY% -m pip install "numpy<2.0.0" >nul 2>&1

echo.
echo [INFO] Webserver backend dang chay tai http://localhost:5000
echo [INFO] Nhan Ctrl+C de dung.
%PY% app.py
pause
