@echo off
rem Haskell runner for Obsidian Execute Code on Windows (see tools\hsnote.py).
set PYTHONUTF8=1
"%USERPROFILE%\miniconda3\envs\study\python.exe" "%USERPROFILE%\StudyVault\tools\hsnote.py" %*
