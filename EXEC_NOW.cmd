@echo off
setlocal enabledelayedexpansion
cd /d d:\JemmaRepo\Jemma
python.exe _execute_workflow.py
del /q _execute_workflow.py
del /q EXEC_NOW.cmd
