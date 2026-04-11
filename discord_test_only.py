#!/usr/bin/env python
"""Direct Discord validation without subprocess complications."""
import sys
import os
from pathlib import Path

# Setup
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / "src"))
os.chdir(repo_root)

print("=" * 70)
print("DISCORD SETUP VALIDATION")
print("=" * 70)

# Run Discord tests directly
import unittest
from io import StringIO

try:
    from tests.test_discord_blueprint import DiscordBlueprintTests
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(DiscordBlueprintTests)
    runner = unittest.TextTestRunner(verbosity=2)
    
    print("\n[TEST SUITE] Running DiscordBlueprintTests")
    print("-" * 70)
    result = runner.run(suite)
    
    if not result.wasSuccessful():
        print("\n✗ Tests failed")
        for failure in result.failures + result.errors:
            print(f"\nFailed: {failure[0]}")
            print(failure[1])
        sys.exit(1)
    
    print("\n✓ All tests passed")
    
    # Now test CLI directly
    print("\n" + "=" * 70)
    print("CLI VALIDATION")
    print("=" * 70)
    
    from jemma.cli import main
    import json
    
    # Test 1: discord-setup-check
    print("\n[CLI CHECK 1] discord-setup-check")
    print("-" * 70)
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    
    old_env = {}
    for key in ["DISCORD_BOT_TOKEN", "DISCORD_CLIENT_ID", "DISCORD_GUILD_ID"]:
        old_env[key] = os.environ.pop(key, None)
    
    try:
        exit_code = main(["discord-setup-check"])
        output = mystdout.getvalue()
    finally:
        sys.stdout = old_stdout
        for key, val in old_env.items():
            if val is not None:
                os.environ[key] = val
    
    try:
        data = json.loads(output)
        print(f"Exit code: {exit_code}")
        print(f"Ready status: {data.get('ready')}")
        print(f"Missing required: {data.get('missing_required')}")
        if exit_code == 0 and not data.get('ready') and data.get('missing_required'):
            print("✓ discord-setup-check output is sensible")
        else:
            print("✗ discord-setup-check output unexpected")
            print(output)
            sys.exit(1)
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON output: {output}")
        sys.exit(1)
    
    # Test 2: discord-oauth-url
    print("\n[CLI CHECK 2] discord-oauth-url --client-id 123456 --guild-id 654321")
    print("-" * 70)
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    
    try:
        exit_code = main(["discord-oauth-url", "--client-id", "123456", "--guild-id", "654321"])
        output = mystdout.getvalue()
    finally:
        sys.stdout = old_stdout
    
    try:
        data = json.loads(output)
        install_url = data.get('install_url', '')
        print(f"Exit code: {exit_code}")
        print(f"URL generated: {len(install_url) > 0}")
        print(f"Contains client_id=123456: {'client_id=123456' in install_url}")
        print(f"Contains guild_id=654321: {'guild_id=654321' in install_url}")
        
        if (exit_code == 0 and install_url and 
            'client_id=123456' in install_url and 
            'guild_id=654321' in install_url):
            print("✓ discord-oauth-url output is sensible")
            print(f"  URL preview: {install_url[:100]}...")
        else:
            print("✗ discord-oauth-url output unexpected")
            print(output)
            sys.exit(1)
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON output: {output}")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print("✓ Test suite: PASSED")
    print("✓ CLI check (setup-check): PASSED")
    print("✓ CLI check (oauth-url): PASSED")
    print("\n✓ Discord setup additions validated successfully!")
    
except Exception as e:
    print(f"\n✗ Validation failed with exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
