@echo off
cd /d d:\JemmaRepo\Jemma
python.exe __temp_workflow_exec__.py
del /q __temp_workflow_exec__.py
del /q run_temp_workflow.bat
