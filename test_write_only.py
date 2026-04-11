with open('test_write_output.txt', 'w') as f:
    f.write('Python execution successful!\n')
    import sys
    f.write(f'Python: {sys.executable}\n')
    f.write(f'Version: {sys.version}\n')
print('Done')
