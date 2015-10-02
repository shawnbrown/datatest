@ECHO OFF
REM ********************************************************************
REM        File: run-tests.bat
REM Description: Runs test suite under all supported versions of Python
REM              and displays failures when encountered.
REM ********************************************************************

REM ********************************************************************
REM Run test suite in all supported versions of Python.
REM ********************************************************************
SET GLOBAL_ERRORLEVEL=0

CALL :runCommand "C:\Program Files\Python 3.5\python.exe -B -m unittest %*"
CALL :runCommand "C:\Python34\python.exe -B -m unittest %*"
CALL :runCommand "C:\Python33\python.exe -B -m unittest %*"
CALL :runCommand "C:\Python32\python.exe -B -m unittest %*"
CALL :runCommand "C:\Python31\python.exe -B discover.py %*"
CALL :runCommand "C:\Python27\python.exe -B -m unittest discover %*"
CALL :runCommand "C:\Python26\python.exe -B discover.py %*"

IF %GLOBAL_ERRORLEVEL% EQU 0 (
    ECHO.
    ECHO All commands successful.
)
GOTO:EOF

REM ********************************************************************
REM Define function (takes command to run as a single argument).
REM ********************************************************************
:runCommand
    SETLOCAL & IF %GLOBAL_ERRORLEVEL% NEQ 0 ENDLOCAL & GOTO:EOF
    ECHO.
    ECHO ======================================================================
    ECHO %~1
    ECHO ======================================================================
    CALL %~fs1
    IF %ERRORLEVEL% NEQ 0 (
        ECHO.
        ECHO Failed Command: %~1
    )
    ENDLOCAL & SET GLOBAL_ERRORLEVEL=%ERRORLEVEL%
    GOTO:EOF
