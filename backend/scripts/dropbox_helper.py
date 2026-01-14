#!/usr/bin/env python3
"""
Dropbox Helper Script

Test utility for Dropbox connector verification.
Supports both Personal and Team/Business accounts.

Usage:
    # Validate token and show account info
    python dropbox_helper.py --token YOUR_ACCESS_TOKEN validate
    
    # List files from root
    python dropbox_helper.py --token YOUR_ACCESS_TOKEN list
    
    # List files with namespace (Team account)
    python dropbox_helper.py --token YOUR_ACCESS_TOKEN --namespace ns:12345 list
    
    # List files with custom path
    python dropbox_helper.py --token YOUR_ACCESS_TOKEN list --path /Documents
    
    # Download a file
    python dropbox_helper.py --token YOUR_ACCESS_TOKEN download --path /test.pdf
    
    # Full connector test
    python dropbox_helper.py --token YOUR_ACCESS_TOKEN test

Environment Variables:
    DROPBOX_ACCESS_TOKEN: Access token (instead of --token)
    DROPBOX_NAMESPACE_ID: Namespace ID for Team accounts (instead of --namespace)
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from connectors.dropbox import DropboxConnector
    from connectors.base import ConnectorAuthError, ConnectorRateLimitError, ConnectorTransientError
    from connectors.enhanced import ItemNotFoundError
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the backend directory or have the correct PYTHONPATH")
    sys.exit(1)


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_account_info(account: dict):
    """Pretty print account information."""
    print("👤 Account Information:")
    print(f"   Account ID: {account.get('account_id', 'N/A')}")
    
    name = account.get('name', {})
    print(f"   Name: {name.get('display_name', 'N/A')}")
    print(f"   Email: {account.get('email', 'N/A')}")
    print(f"   Country: {account.get('country', 'N/A')}")
    
    # Team/Business account detection
    root_info = account.get('root_info', {})
    tag = root_info.get('.tag', '')
    
    if tag == 'team':
        print(f"\n🏢 Team Account Detected:")
        print(f"   Root Namespace ID: {root_info.get('root_namespace_id', 'N/A')}")
        print(f"   Home Namespace ID: {root_info.get('home_namespace_id', 'N/A')}")
        
        team = account.get('team', {})
        if team:
            print(f"   Team Name: {team.get('name', 'N/A')}")
            print(f"   Team ID: {team.get('id', 'N/A')}")
    else:
        print(f"\n👤 Personal Account")
        print(f"   Root Namespace ID: {root_info.get('root_namespace_id', 'N/A')}")


def validate_command(connector: DropboxConnector, config: dict):
    """Validate token and show account information."""
    print_header("Token Validation")
    
    try:
        account = connector._verify_token(config['access_token'])
        print("✅ Token is valid!\n")
        print_account_info(account)
        
        # Extract and show namespace for Team accounts
        root_info = account.get('root_info', {})
        namespace_id = root_info.get('root_namespace_id')
        
        if namespace_id:
            print(f"\n💡 Tip: Use --namespace {namespace_id} to access Team folders")
        
        return True
    except ConnectorAuthError as e:
        print(f"❌ Token validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def list_command(connector: DropboxConnector, config: dict, args):
    """List files from Dropbox."""
    print_header("File Listing")
    
    path = args.path or ""
    recursive = args.recursive
    
    print(f"📂 Listing: '{path or '(root)'}'")
    print(f"   Recursive: {recursive}")
    if config.get('namespace_id'):
        print(f"   Namespace: {config['namespace_id']}")
    print()
    
    list_config = {
        **config,
        'parent_id': path if path else None,
        'recursive': recursive,
    }
    
    try:
        files = list(connector.list_files(list_config))
        
        # Separate folders and files
        folders = [f for f in files if f.mime_type == "inode/directory"]
        regular_files = [f for f in files if f.mime_type != "inode/directory"]
        
        print(f"📁 Folders ({len(folders)}):")
        for folder in folders[:20]:  # Limit output
            print(f"   📁 {folder.name}")
        if len(folders) > 20:
            print(f"   ... and {len(folders) - 20} more folders")
        
        print(f"\n📄 Files ({len(regular_files)}):")
        for file in regular_files[:30]:  # Limit output
            size_str = f"{file.size:,} bytes" if file.size else "N/A"
            mod_str = file.modified_at.strftime("%Y-%m-%d %H:%M") if file.modified_at else "N/A"
            print(f"   📄 {file.name} ({size_str}, {mod_str})")
        if len(regular_files) > 30:
            print(f"   ... and {len(regular_files) - 30} more files")
        
        print(f"\n✅ Total: {len(folders)} folders, {len(regular_files)} files")
        return True
        
    except ItemNotFoundError as e:
        print(f"❌ Path not found: {e}")
        return False
    except ConnectorAuthError as e:
        print(f"❌ Auth error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def download_command(connector: DropboxConnector, config: dict, args):
    """Download a file from Dropbox."""
    print_header("File Download")
    
    if not args.path:
        print("❌ --path is required for download")
        return False
    
    path = args.path
    output = args.output or os.path.basename(path)
    
    print(f"📥 Downloading: {path}")
    print(f"   Output: {output}")
    if config.get('namespace_id'):
        print(f"   Namespace: {config['namespace_id']}")
    print()
    
    try:
        content = connector.fetch_file_content(path, config)
        
        with open(output, 'wb') as f:
            f.write(content)
        
        print(f"✅ Downloaded {len(content):,} bytes to '{output}'")
        return True
        
    except ItemNotFoundError as e:
        print(f"❌ File not found: {e}")
        return False
    except ConnectorAuthError as e:
        print(f"❌ Auth error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_command(connector: DropboxConnector, config: dict):
    """Run full connector test."""
    print_header("Full Connector Test")
    
    results = []
    
    # Test 1: Validate
    print("🧪 Test 1: Token Validation")
    try:
        account = connector._verify_token(config['access_token'])
        print("   ✅ PASS")
        results.append(("Token Validation", True))
        
        # Check for Team account
        root_info = account.get('root_info', {})
        namespace_id = root_info.get('root_namespace_id')
        if namespace_id and not config.get('namespace_id'):
            config['namespace_id'] = namespace_id
            print(f"   📝 Using Team namespace: {namespace_id}")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Token Validation", False))
        return False
    
    # Test 2: Config Validation
    print("\n🧪 Test 2: Config Validation")
    try:
        is_valid = connector.validate_config(config)
        if is_valid:
            print("   ✅ PASS")
            results.append(("Config Validation", True))
        else:
            print("   ❌ FAIL: validate_config returned False")
            results.append(("Config Validation", False))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Config Validation", False))
    
    # Test 3: List Files
    print("\n🧪 Test 3: List Files (Root)")
    try:
        list_config = {**config, 'parent_id': '', 'recursive': False}
        files = list(connector.list_files(list_config))
        print(f"   ✅ PASS: Found {len(files)} items in root")
        results.append(("List Files", True))
        
        # Find a test file for download
        test_file = None
        for f in files:
            if f.mime_type != "inode/directory" and f.size and f.size < 1024 * 1024:
                test_file = f
                break
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("List Files", False))
        test_file = None
    
    # Test 4: Download File
    print("\n🧪 Test 4: Download File")
    if test_file:
        try:
            content = connector.fetch_file_content(test_file.id, config)
            print(f"   ✅ PASS: Downloaded {test_file.name} ({len(content):,} bytes)")
            results.append(("Download File", True))
        except Exception as e:
            print(f"   ❌ FAIL: {e}")
            results.append(("Download File", False))
    else:
        print("   ⏭️ SKIP: No suitable test file found")
        results.append(("Download File", None))
    
    # Test 5: Get Headers (Team Support)
    print("\n🧪 Test 5: Team Namespace Headers")
    try:
        headers = connector._get_headers(config)
        if config.get('namespace_id'):
            if 'Dropbox-API-Path-Root' in headers:
                print(f"   ✅ PASS: Path root header present")
                results.append(("Team Headers", True))
            else:
                print(f"   ❌ FAIL: Path root header missing for Team account")
                results.append(("Team Headers", False))
        else:
            print("   ⏭️ SKIP: Not a Team account")
            results.append(("Team Headers", None))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Team Headers", False))
    
    # Summary
    print_header("Test Results Summary")
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    for name, result in results:
        if result is True:
            print(f"   ✅ {name}")
        elif result is False:
            print(f"   ❌ {name}")
        else:
            print(f"   ⏭️ {name} (skipped)")
    
    print(f"\n📊 Total: {passed} passed, {failed} failed, {skipped} skipped")
    
    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Dropbox Connector Test Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--token', '-t',
        default=os.environ.get('DROPBOX_ACCESS_TOKEN'),
        help='Dropbox access token (or set DROPBOX_ACCESS_TOKEN env var)'
    )
    parser.add_argument(
        '--namespace', '-n',
        default=os.environ.get('DROPBOX_NAMESPACE_ID'),
        help='Namespace ID for Team accounts (or set DROPBOX_NAMESPACE_ID env var)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate token and show account info')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List files')
    list_parser.add_argument('--path', '-p', default='', help='Path to list (default: root)')
    list_parser.add_argument('--recursive', '-r', action='store_true', help='Recursive listing')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a file')
    download_parser.add_argument('--path', '-p', required=True, help='File path to download')
    download_parser.add_argument('--output', '-o', help='Output filename')
    
    # Test command
    subparsers.add_parser('test', help='Run full connector test')
    
    args = parser.parse_args()
    
    if not args.token:
        print("❌ Error: Access token required")
        print("   Use --token or set DROPBOX_ACCESS_TOKEN environment variable")
        sys.exit(1)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Build config
    config = {
        'access_token': args.token,
    }
    if args.namespace:
        config['namespace_id'] = args.namespace
        print(f"🏢 Using Team namespace: {args.namespace}")
    
    # Create connector
    connector = DropboxConnector()
    
    # Run command
    success = False
    
    if args.command == 'validate':
        success = validate_command(connector, config)
    elif args.command == 'list':
        success = list_command(connector, config, args)
    elif args.command == 'download':
        success = download_command(connector, config, args)
    elif args.command == 'test':
        success = test_command(connector, config)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

