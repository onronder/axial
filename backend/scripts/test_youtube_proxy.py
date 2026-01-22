#!/usr/bin/env python3
"""
YouTube Proxy Testing Utility

Tests the Bright Data / residential proxy configuration for YouTube transcript fetching.
Run from backend directory: python scripts/test_youtube_proxy.py

Usage:
    # Test with default video
    python scripts/test_youtube_proxy.py
    
    # Test with specific video
    python scripts/test_youtube_proxy.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
    
    # Test proxy health only (no transcript fetch)
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


def test_proxy_configuration():
    """Test and display proxy configuration."""
    print_header("🔧 PROXY CONFIGURATION")
    
    from connectors.web import _get_youtube_proxy_config, _build_proxy_dict
    
    config = _get_youtube_proxy_config()
    
    proxy_url = config.get("proxy_url")
    if proxy_url:
        # Mask password in output
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)
        if parsed.password:
            masked_url = proxy_url.replace(parsed.password, "***")
        else:
            masked_url = proxy_url
        print(f"✅ Proxy URL: {masked_url}")
    else:
        print("❌ Proxy URL: NOT CONFIGURED")
        print("   Set YOUTUBE_PROXY_URL environment variable")
    
    print(f"   Proxy Enabled: {config.get('enabled')}")
    print(f"   Timeout: {config.get('timeout')}s")
    print(f"   Retry Count: {config.get('retry_count')}")
    print(f"   Retry Delay: {config.get('retry_delay')}s")
    print(f"   Direct Fallback: {config.get('direct_fallback')}")
    
    # Test proxy dict building
    if proxy_url:
        proxies = _build_proxy_dict(proxy_url)
        if proxies:
            print(f"✅ Proxy dict valid: {list(proxies.keys())}")
        else:
            print("❌ Proxy dict: INVALID (check URL format)")
    
    return config


def test_proxy_connectivity(config: dict) -> bool:
    """Test basic proxy connectivity using a simple HTTP request."""
    print_header("🌐 PROXY CONNECTIVITY TEST")
    
    proxy_url = config.get("proxy_url")
    if not proxy_url:
        print("⚠️  Skipping connectivity test - no proxy configured")
        return False
    
    from connectors.web import _build_proxy_dict
    import requests
    
    proxies = _build_proxy_dict(proxy_url)
    if not proxies:
        print("❌ Cannot test - invalid proxy configuration")
        return False
    
    # Test with a simple endpoint that returns your IP
    test_urls = [
        ("httpbin.org", "https://httpbin.org/ip"),
        ("ipinfo.io", "https://ipinfo.io/json"),
    ]
    
    for name, url in test_urls:
        print(f"\n📡 Testing via {name}...")
        try:
            start = time.time()
            response = requests.get(
                url,
                proxies=proxies,
                timeout=config.get("timeout", 30),
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                ip = data.get("origin") or data.get("ip", "unknown")
                print(f"   ✅ Success! Response in {elapsed:.2f}s")
                print(f"   🌍 Your proxy IP: {ip}")
                
                # Check if it's a residential IP (basic heuristic)
                if "cloud" in str(data).lower() or "datacenter" in str(data).lower():
                    print("   ⚠️  Warning: IP may be detected as datacenter")
                else:
                    print("   ✅ IP appears residential")
                return True
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
        except requests.exceptions.ProxyError as e:
            print(f"   ❌ Proxy Error: {e}")
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout after {config.get('timeout')}s")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False


def test_youtube_connectivity(config: dict) -> bool:
    """Test connectivity to YouTube specifically."""
    print_header("🎥 YOUTUBE CONNECTIVITY TEST")
    
    proxy_url = config.get("proxy_url")
    from connectors.web import _build_proxy_dict
    import requests
    
    proxies = _build_proxy_dict(proxy_url) if proxy_url else None
    
    # Test YouTube homepage
    print("\n📡 Testing YouTube access...")
    try:
        start = time.time()
        response = requests.get(
            "https://www.youtube.com/robots.txt",
            proxies=proxies,
            timeout=config.get("timeout", 30),
            headers={"User-Agent": "Mozilla/5.0 (compatible; AxioBot/1.0)"},
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"   ✅ YouTube accessible in {elapsed:.2f}s")
            print(f"   📄 robots.txt: {len(response.text)} bytes")
            return True
        else:
            print(f"   ❌ Failed: HTTP {response.status_code}")
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
    print(f"🔒 Using Proxy: {'Yes' if config.get('proxy_url') and config.get('enabled') else 'No'}")
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
        description="Test YouTube proxy configuration for transcript fetching"
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
        help="Only test proxy connectivity, don't fetch transcript"
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
    
    print("\n" + "🚀 " + "=" * 76)
    print("   YOUTUBE PROXY TEST UTILITY")
    print("   " + "=" * 76)
    
    # Run tests
    results = {}
    
    # 1. Configuration test
    config = test_proxy_configuration()
    results["configuration"] = bool(config.get("proxy_url"))
    
    # 2. Proxy connectivity test
    if config.get("proxy_url"):
        results["proxy_connectivity"] = test_proxy_connectivity(config)
    else:
        results["proxy_connectivity"] = None  # N/A
    
    # 3. YouTube connectivity test
    results["youtube_connectivity"] = test_youtube_connectivity(config)
    
    # 4. Transcript fetch test (unless health-check only)
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
