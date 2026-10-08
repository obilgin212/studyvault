@echo off
rem Python runner for Obsidian Execute Code on Windows: the `study` env + the check helper.
rem Code files go through _tabfix_run.py (Obsidian's Tab key can insert real tabs; Python rejects mixed indentation).
set PYTHONUTF8=1
set "PYTHONPATH=%USERPROFILE%\StudyVault\tools\py;%PYTHONPATH%"
set "PY=%USERPROFILE%\miniconda3\envs\study\python.exe"
if /I "%~x1"==".py" if exist "%~1" (
  "%PY%" "%USERPROFILE%\StudyVault\tools\py\_tabfix_run.py" %*
  exit /b %ERRORLEVEL%
)
"%PY%" %*
