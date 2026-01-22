#!/usr/bin/env python3
"""
YouTube Bright Data Unlocker API Testing Utility

Tests the Bright Data Unlocker API configuration for YouTube transcript fetching.
Run from backend directory: python scripts/test_youtube_proxy.py

Usage:
    # Test with default video
    python scripts/test_youtube_proxy.py
    
    # Test with specific video
    python scripts/test_youtube_proxy.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
    
    # Test API health only (no transcript fetch)
    python scripts/test_youtube_proxy.py --health-check
"""
import os
import sys
import time
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_unlocker_configuration():
    """Test and display Bright Data Unlocker API configuration."""
    print_header("🔧 BRIGHT DATA UNLOCKER API CONFIGURATION")
    
    from connectors.web import _get_brightdata_config
    
    config = _get_brightdata_config()
    
    api_key = config.get("api_key")
    if api_key:
        # Mask API key in output (show first/last 4 chars)
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
        print(f"✅ API Key: {masked_key}")
    else:
        print("❌ API Key: NOT CONFIGURED")
        print("   Set BRIGHTDATA_API_KEY environment variable")
    
    print(f"   Zone: {config.get('zone')}")
    print(f"   Timeout: {config.get('timeout')}s")
    print(f"   Retry Count: {config.get('retry_count')}")
    print(f"   Retry Delay: {config.get('retry_delay')}s")
    print(f"   Direct Fallback: {config.get('direct_fallback')}")
    
    return config


def test_unlocker_connectivity(config: dict) -> bool:
    """Test basic Bright Data Unlocker API connectivity."""
    print_header("🌐 UNLOCKER API CONNECTIVITY TEST")
    
    api_key = config.get("api_key")
    if not api_key:
        print("⚠️  Skipping connectivity test - no API key configured")
        return False
    
    from connectors.web import _fetch_via_brightdata_unlocker
    
    # Test with Bright Data's test endpoint
    test_url = "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api"
    
    print(f"\n📡 Testing API connectivity...")
    print(f"   URL: {test_url}")
    
    try:
        start = time.time()
        result = _fetch_via_brightdata_unlocker(test_url, config)
        elapsed = time.time() - start
        
        if result:
            print(f"   ✅ Success! Response in {elapsed:.2f}s")
            print(f"   📄 Response: {result[:100]}...")
            return True
        else:
            print(f"   ❌ Failed: No response received")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_unlocker_ip(config: dict) -> bool:
    """Test IP resolution via Bright Data Unlocker API."""
    print_header("🌍 IP RESOLUTION TEST")
    
    api_key = config.get("api_key")
    if not api_key:
        print("⚠️  Skipping IP test - no API key configured")
        return False
    
    from connectors.web import _fetch_via_brightdata_unlocker
    import json
    
    test_url = "https://httpbin.org/ip"
    
    print(f"\n📡 Testing IP via httpbin.org...")
    
    try:
        start = time.time()
        result = _fetch_via_brightdata_unlocker(test_url, config)
        elapsed = time.time() - start
        
        if result:
            try:
                data = json.loads(result)
                ip = data.get("origin", "unknown")
                print(f"   ✅ Success! Response in {elapsed:.2f}s")
                print(f"   🌍 Your Bright Data IP: {ip}")
                return True
            except json.JSONDecodeError:
                print(f"   ⚠️  Response received but not JSON: {result[:100]}...")
                return True
        else:
            print(f"   ❌ Failed: No response received")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_youtube_connectivity(config: dict) -> bool:
    """Test connectivity to YouTube via Bright Data Unlocker API."""
    print_header("🎥 YOUTUBE CONNECTIVITY TEST")
    
    api_key = config.get("api_key")
    if not api_key:
        print("⚠️  Skipping YouTube test - no API key configured")
        print("   Attempting direct connection...")
        
        import requests
        try:
            response = requests.get(
                "https://www.youtube.com/robots.txt",
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AxioBot/1.0)"},
            )
            if response.status_code == 200:
                print(f"   ✅ YouTube accessible directly (robots.txt: {len(response.text)} bytes)")
                return True
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Direct connection failed: {e}")
            return False
    
    from connectors.web import _fetch_via_brightdata_unlocker
    
    # Test YouTube robots.txt via Unlocker
    test_url = "https://www.youtube.com/robots.txt"
    
    print(f"\n📡 Testing YouTube access via Unlocker API...")
    
    try:
        start = time.time()
        result = _fetch_via_brightdata_unlocker(test_url, config)
        elapsed = time.time() - start
        
        if result:
            print(f"   ✅ YouTube accessible in {elapsed:.2f}s")
            print(f"   📄 robots.txt: {len(result)} bytes")
            return True
        else:
            print(f"   ❌ Failed: No response received")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_youtube_page_fetch(config: dict) -> bool:
    """Test fetching a YouTube video page via Unlocker API."""
    print_header("📄 YOUTUBE PAGE FETCH TEST")
    
    api_key = config.get("api_key")
    if not api_key:
        print("⚠️  Skipping page fetch test - no API key configured")
        return False
    
    from connectors.web import _fetch_via_brightdata_unlocker
    
    # Use a well-known video
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"\n📡 Testing YouTube page fetch...")
    print(f"   URL: {test_url}")
    
    try:
        start = time.time()
        result = _fetch_via_brightdata_unlocker(test_url, config)
        elapsed = time.time() - start
        
        if result:
            print(f"   ✅ Page fetched in {elapsed:.2f}s")
            print(f"   📄 Page size: {len(result)} bytes")
            
            # Check for key indicators
            has_player_response = "ytInitialPlayerResponse" in result
            has_title = "<title>" in result.lower()
            
            print(f"   📋 Has player response: {'Yes' if has_player_response else 'No'}")
            print(f"   📋 Has title tag: {'Yes' if has_title else 'No'}")
            
            if has_player_response:
                return True
            else:
                print("   ⚠️  Warning: Page may be incomplete or blocked")
                return True  # Still count as partial success
        else:
            print(f"   ❌ Failed: No response received")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_transcript_fetch(video_url: str, config: dict) -> bool:
    """Test actual transcript fetching."""
    print_header("📝 TRANSCRIPT FETCH TEST")
    
    from connectors.web import WebConnector
    
    connector = WebConnector()
    
    # Extract video ID
    video_id = connector._extract_youtube_video_id(video_url)
    if not video_id:
        print(f"❌ Invalid YouTube URL: {video_url}")
        return False
    
    print(f"🎬 Video URL: {video_url}")
    print(f"🔑 Video ID: {video_id}")
    print(f"🔒 Using Unlocker API: {'Yes' if config.get('api_key') else 'No (direct only)'}")
    print("\n⏳ Fetching transcript (this may take a few seconds)...")
    
    start = time.time()
    transcript = connector.fetch_youtube_transcript(video_url)
    elapsed = time.time() - start
    
    if transcript:
        print(f"\n✅ SUCCESS! Transcript fetched in {elapsed:.2f}s")
        print(f"📊 Length: {len(transcript)} characters")
        print(f"📊 Words: ~{len(transcript.split())} words")
        
        # Show preview
        print("\n📄 Preview (first 300 chars):")
        print("-" * 40)
        print(transcript[:300] + "..." if len(transcript) > 300 else transcript)
        print("-" * 40)
        return True
    else:
        print(f"\n❌ FAILED to fetch transcript after {elapsed:.2f}s")
        print("   Check the logs above for detailed error messages")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test Bright Data Unlocker API configuration for YouTube transcript fetching"
    )
    parser.add_argument(
        "video_url",
        nargs="?",
        default="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        help="YouTube video URL to test (default: Rick Astley - Never Gonna Give You Up)"
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Only test API connectivity, don't fetch transcript"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Enable verbose logging if requested
    if args.verbose:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    else:
        # Enable INFO logging to see connector logs
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s"
        )
    
    print("\n" + "🚀 " + "=" * 76)
    print("   BRIGHT DATA UNLOCKER API - YOUTUBE TRANSCRIPT TEST UTILITY")
    print("   " + "=" * 76)
    
    # Run tests
    results = {}
    
    # 1. Configuration test
    config = test_unlocker_configuration()
    results["configuration"] = bool(config.get("api_key"))
    
    # 2. Unlocker API connectivity test
    if config.get("api_key"):
        results["api_connectivity"] = test_unlocker_connectivity(config)
        results["ip_resolution"] = test_unlocker_ip(config)
    else:
        results["api_connectivity"] = None  # N/A
        results["ip_resolution"] = None  # N/A
    
    # 3. YouTube connectivity test
    results["youtube_connectivity"] = test_youtube_connectivity(config)
    
    # 4. YouTube page fetch test
    if config.get("api_key"):
        results["youtube_page_fetch"] = test_youtube_page_fetch(config)
    else:
        results["youtube_page_fetch"] = None  # N/A
    
    # 5. Transcript fetch test (unless health-check only)
    if not args.health_check:
        results["transcript_fetch"] = test_transcript_fetch(args.video_url, config)
    else:
        results["transcript_fetch"] = None  # Skipped
    
    # Summary
    print_header("📊 TEST SUMMARY")
    
    status_map = {
        True: "✅ PASS",
        False: "❌ FAIL",
        None: "⏭️  SKIP",
    }
    
    for test_name, result in results.items():
        print(f"   {status_map[result]} - {test_name.replace('_', ' ').title()}")
    
    # Overall result
    failures = sum(1 for r in results.values() if r is False)
    if failures == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failures} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
