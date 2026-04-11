#!/usr/bin/env python3
"""Execute workflow inline and clean up."""
import os
os.chdir(r'd:\JemmaRepo\Jemma')
os.system('python __temp_workflow_exec__.py')
if os.path.exists('__temp_workflow_exec__.py'):
    os.remove('__temp_workflow_exec__.py')
if os.path.exists('run_temp_workflow.bat'):
    os.remove('run_temp_workflow.bat')
if os.path.exists('exec_workflow_inline.py'):
    os.remove('exec_workflow_inline.py')
