#!/usr/bin/env python
"""Direct validation without pytest CLI."""
import sys
import os
from pathlib import Path

# Setup path
repo_root = Path("D:\\JemmaRepo\\Jemma")
sys.path.insert(0, str(repo_root / "src"))
os.chdir(repo_root)

print("=" * 70)
print("TEST 1: Import Discord modules")
print("=" * 70)
try:
    from jemma.cli import main
    from jemma.discord.blueprint import build_research_server_blueprint_from_app_config
    from jemma.discord.oauth import build_authorize_url, permission_value
    from jemma.config.loader import load_app_config
    print("✓ All Discord modules imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("TEST 2: Check permission_value function")
print("=" * 70)
try:
    perms = permission_value(["SEND_MESSAGES", "CREATE_PRIVATE_THREADS"])
    expected = (1 << 11) | (1 << 36)
    if perms == expected:
        print(f"✓ permission_value works: {perms} == {expected}")
    else:
        print(f"✗ permission_value mismatch: {perms} != {expected}")
        sys.exit(1)
except Exception as e:
    print(f"✗ permission_value test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("TEST 3: Check build_authorize_url function")
print("=" * 70)
try:
    oauth = build_authorize_url(
        client_id="123456",
        scopes=["bot", "applications.commands"],
        permission_names=["SEND_MESSAGES", "CREATE_PRIVATE_THREADS"],
        guild_id="654321",
        redirect_uri="http://127.0.0.1/callback",
    )
    if oauth and oauth.install_url:
        checks = [
            ("client_id=123456", "client_id=123456" in oauth.install_url),
            ("guild_id=654321", "guild_id=654321" in oauth.install_url),
            ("permissions", f"permissions={permission_value(['SEND_MESSAGES', 'CREATE_PRIVATE_THREADS'])}" in oauth.install_url),
        ]
        all_ok = all(check[1] for check in checks)
        for check_name, result in checks:
            print(f"  {'✓' if result else '✗'} {check_name}")
        if all_ok:
            print("✓ build_authorize_url works correctly")
        else:
            print("✗ build_authorize_url has issues")
            sys.exit(1)
    else:
        print(f"✗ oauth object or install_url is missing")
        sys.exit(1)
except Exception as e:
    print(f"✗ build_authorize_url test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("TEST 4: Check blueprint structure")
print("=" * 70)
try:
    config = load_app_config(repo_root)
    blueprint = build_research_server_blueprint_from_app_config(config, client_id="123456")
    channels = {channel.name: channel for channel in blueprint.channels}
    
    checks = [
        ("open-lobby exists", "open-lobby" in channels),
        ("open-lobby is public-write", channels.get("open-lobby") and channels["open-lobby"].visibility == "public-write"),
        ("mod-intake exists", "mod-intake" in channels),
        ("mod-intake has private threads", channels.get("mod-intake") and channels["mod-intake"].default_thread_mode == "private"),
        ("blueprint has oauth", bool(blueprint.oauth)),
        ("oauth has install_url", blueprint.oauth and bool(blueprint.oauth.install_url)),
    ]
    
    for check_name, result in checks:
        print(f"  {'✓' if result else '✗'} {check_name}")
    
    all_ok = all(check[1] for check in checks)
    if all_ok:
        print("✓ Blueprint structure is correct")
    else:
        print("✗ Blueprint structure has issues")
        sys.exit(1)
except Exception as e:
    print(f"✗ Blueprint test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("CLI CHECK 1: discord-setup-check")
print("=" * 70)
try:
    from io import StringIO
    import json as json_module
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    # Clear environment for realistic test
    old_env = {}
    for key in ["DISCORD_BOT_TOKEN", "DISCORD_CLIENT_ID", "DISCORD_GUILD_ID", "DISCORD_CLIENT_SECRET"]:
        old_env[key] = os.environ.pop(key, None)
    
    try:
        exit_code = main(["discord-setup-check"])
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
        for key, val in old_env.items():
            if val is not None:
                os.environ[key] = val
    
    # Parse output
    try:
        data = json_module.loads(output)
        checks = [
            ("Returns exit 0", exit_code == 0),
            ("Has ready field", "ready" in data),
            ("ready is False", data.get("ready") is False),
            ("Has missing_required", "missing_required" in data),
            ("missing_required is not empty", len(data.get("missing_required", [])) > 0),
            ("Has checks list", "checks" in data),
            ("Has next_steps", "next_steps" in data),
        ]
        
        for check_name, result in checks:
            print(f"  {'✓' if result else '✗'} {check_name}")
        
        all_ok = all(check[1] for check in checks)
        if all_ok:
            print("✓ discord-setup-check output is sensible")
        else:
            print("✗ discord-setup-check output issues")
            print(f"  Output: {output}")
            sys.exit(1)
    except json_module.JSONDecodeError as e:
        print(f"✗ Failed to parse JSON output: {e}")
        print(f"  Output: {output}")
        sys.exit(1)
except Exception as e:
    print(f"✗ discord-setup-check CLI check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("CLI CHECK 2: discord-oauth-url")
print("=" * 70)
try:
    from io import StringIO
    import json as json_module
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        exit_code = main(["discord-oauth-url", "--client-id", "123456", "--guild-id", "654321"])
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    
    # Parse output
    try:
        data = json_module.loads(output)
        checks = [
            ("Returns exit 0", exit_code == 0),
            ("Has install_url", "install_url" in data),
            ("install_url is not empty", bool(data.get("install_url"))),
            ("install_url contains client_id", "client_id=123456" in data.get("install_url", "")),
            ("install_url contains guild_id", "guild_id=654321" in data.get("install_url", "")),
        ]
        
        for check_name, result in checks:
            print(f"  {'✓' if result else '✗'} {check_name}")
        
        all_ok = all(check[1] for check in checks)
        if all_ok:
            print("✓ discord-oauth-url output is sensible")
            print(f"  Generated URL starts with: {data.get('install_url', '')[:80]}...")
        else:
            print("✗ discord-oauth-url output issues")
            print(f"  Output: {output}")
            sys.exit(1)
    except json_module.JSONDecodeError as e:
        print(f"✗ Failed to parse JSON output: {e}")
        print(f"  Output: {output}")
        sys.exit(1)
except Exception as e:
    print(f"✗ discord-oauth-url CLI check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)
print("✓ All tests passed")
print("✓ All CLI checks passed")
print("✓ Discord setup additions are working correctly")
