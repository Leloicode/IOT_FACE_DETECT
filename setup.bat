@echo on
REM Setup tu dong: kiem tra Python 3.11 -> neu thieu thi TU CAI -> tao venv -> cai thu vien
REM Chay file nay bang "double-click" (se tu xin quyen admin khi can)

setlocal EnableExtensions

cd /d "%~dp0python_app"
set "PYTHONUTF8=1"

echo ============================================
echo  AUTO SETUP - He thong Diem Danh IOT
echo ============================================

REM ---------------------------------------------------------------
REM [BUOC 1] Tim Python phu hop (3.11 > 3.10 > 3.9 > 3.x)
REM ---------------------------------------------------------------
set "PY="
for %%V in (3.11 3.10 3.9) do (
    if not defined PY (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 set "PY=py -%%V"
    )
)
%PY% --version >nul 2>&1
if not errorlevel 1 (
    echo [OK] Da tim thay: 
    %PY% --version
    goto :HAVE_PY
)

REM ---------------------------------------------------------------
REM Khong co Python phu hop -> TU CAI Python 3.11 (ban 64-bit)
REM ---------------------------------------------------------------
echo.
echo [INFO] Khong tim thay Python 3.9-3.11 phu hop.
echo [INFO] Tien hanh tai va cai Python 3.11 (can quyen quan tri vien)...

set "PY_INSTALLER=%TEMP%\python-3.11.9-amd64.exe"
set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

echo [INFO] Dang tai Python 3.11 (may lau tuy mang)...
where curl >nul 2>&1
if not errorlevel 1 (
    curl -L -o "%PY_INSTALLER%" "%PY_URL%"
) else (
    powershell -Command "(New-Object Net.WebClient).DownloadFile('%PY_URL%', '%PY_INSTALLER%')"
)

if not exist "%PY_INSTALLER%" (
    echo [ERROR] Tai Python that bai. Kiem tra mang hoac tai thu cong:
    echo    %PY_URL%
    pause
    exit /b 1
)

REM Cai am tham: cai cho user hien tai (khong can quyen admin), them PATH
echo [INFO] Dang cai Python 3.11 (may 1-2 phut)...
start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
if errorlevel 1 (
    echo [WARN] Cai Python co the can thuc thi lai voi quyen Admin.
    echo [INFO] Neu loi, hay chay file nay bang "Run as administrator".
)

REM Sau khi cai, duong dan moi bat dau hoat dong tu cmd moi.
REM Dung cach go thang toi exe de khoi can mo lai terminal:
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "C:\Program Files\Python311\python.exe" (
    set "PY=C:\Program Files\Python311\python.exe"
) else (
    set "PY=py -3.11"
)

echo [OK] Python da san sang:
%PY% --version

:HAVE_PY

REM ---------------------------------------------------------------
REM [BUOC 2] Tao venv
REM ---------------------------------------------------------------
echo.
echo ============================================
echo [2/4] Tao venv
echo ============================================

REM Neu venv cu dung Python 3.12/3.13 (khong co dlib wheel) thi xoa de tao lai
set "BAD_VENV="
if not exist venv\Scripts\python.exe goto :SKIP_VENV_CHECK
venv\Scripts\python.exe -c "import sys; sys.exit(0 if sys.version_info.major==3 and 9<=sys.version_info.minor<=11 else 1)" >nul 2>&1
if errorlevel 1 set "BAD_VENV=1"
:SKIP_VENV_CHECK
if not defined BAD_VENV goto :SKIP_RM_VENV
echo [INFO] venv cu dung Python khong phu hop (3.12/3.13). Xoa de tao lai...
rmdir /s /q venv
:SKIP_RM_VENV

if exist venv goto :VENV_EXISTS
%PY% -m venv venv
if errorlevel 1 (
    echo [ERROR] Tao venv that bai. Loi thu cong: %PY% -m venv venv
    pause
    exit /b 1
)
echo [OK] Da tao venv.
goto :VENV_DONE
:VENV_EXISTS
echo [OK] venv da co san.
:VENV_DONE

REM ---------------------------------------------------------------
REM [BUOC 3] Cap nhat pip
REM ---------------------------------------------------------------
echo.
echo ============================================
echo [3/4] Cap nhat pip
echo ============================================
call venv\Scripts\activate.bat >nul 2>&1
%PY% -m pip install --upgrade pip

REM ---------------------------------------------------------------
REM [BUOC 4] Cai thu vien
REM ---------------------------------------------------------------
echo.
echo ============================================
echo [4/4] Cai thu vien (co the mat vai phut)
echo ============================================
echo [INFO] Dang cai dat dlib (Nhan dien khuon mat) ban dung cho Windows...
%PY% -m pip install https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp311-cp311-win_amd64.whl

echo [INFO] Dang cai dat cac thu vien con lai...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Cai thu vien that bai.
    echo    - Neu LOI bien dich dlib: Python ban tu dong cai la 3.11 nen co wheel.
    echo      Neu van loi, hay doi ten thu muc thanh khong dau VD DU_AN_IOT_CAMERA.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  [DONE] Hoan tat! Chay:  start_backend.bat
echo ============================================
pause
