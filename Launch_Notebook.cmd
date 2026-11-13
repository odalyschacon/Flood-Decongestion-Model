@echo off
cd /d "%~dp0"
set "FLOODLAB_PYTHON=%USERPROFILE%\anaconda3\envs\gb10\python.exe"
if not exist "%FLOODLAB_PYTHON%" (
  echo Could not find the gb10 Python environment. Open Anaconda Prompt and activate gb10.
  pause
  exit /b 1
)
"%FLOODLAB_PYTHON%" -m jupyterlab "%~dp0SanAntonio_Flood_Planning.ipynb"
