#!/usr/bin/env python
"""
Test simplificado para la API de subtítulos
Uso: python test_simple_api.py
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000/api/subtitles"
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print('='*50)

def test_health():
    print_section("Health Check")
    resp = requests.get(f"{BASE_URL}/health/")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    return resp.status_code == 200

def test_languages():
    print_section("Get Languages")
    resp = requests.post(
        f"{BASE_URL}/languages/",
        json={"url": TEST_VIDEO_URL}
    )
    print(f"Status: {resp.status_code}")
    data = resp.json()
    
    if 'error' not in data:
        print(f"Found {data['total']} languages")
        print(f"Proxy used: {data.get('proxy_used', False)}")
        for i, lang in enumerate(data['languages'][:3]):
            generated = " (auto)" if lang['is_generated'] else ""
            print(f"  {i+1}. {lang['name']} ({lang['code']}){generated}")
    else:
        print(f"Error: {data['error']}")
    
    return data

def test_subtitles(language_code=None):
    lang_str = f" in {language_code}" if language_code else ""
    print_section(f"Get Subtitles{lang_str}")
    
    payload = {"url": TEST_VIDEO_URL}
    if language_code:
        payload["language_code"] = language_code
    
    resp = requests.post(
        f"{BASE_URL}/extract/",
        json=payload
    )
    print(f"Status: {resp.status_code}")
    data = resp.json()
    
    if 'error' not in data:
        print(f"Video ID: {data['video_id']}")
        print(f"Subtitle count: {data['subtitle_count']}")
        print(f"Total duration: {data['total_duration']} seconds")
        print(f"Language: {data.get('language_code', 'default')}")
        print(f"Proxy used: {data.get('proxy_used', False)}")
        if data['subtitles']:
            print(f"\nFirst subtitle: \"{data['subtitles'][0]['text']}\"")
    else:
        print(f"Error: {data['error']}")
        if 'details' in data:
            print(f"Details: {data['details']}")

def show_config():
    print_section("Current Configuration")
    print(f"USE_PROXY: {os.getenv('USE_PROXY', 'False')}")
    
    if os.getenv('USE_PROXY') == 'True':
        username = os.getenv('WEBSHARE_PROXY_USERNAME')
        password = os.getenv('WEBSHARE_PROXY_PASSWORD')
        print(f"WEBSHARE_PROXY_USERNAME: {'***' if username else 'NOT SET'}")
        print(f"WEBSHARE_PROXY_PASSWORD: {'***' if password else 'NOT SET'}")

if __name__ == "__main__":
    print("🧪 YouTube Subtitles API Test (Simplified)")
    print(f"Testing with video: {TEST_VIDEO_URL}")
    
    # Show configuration
    show_config()
    
    # Test health
    if not test_health():
        print("\n❌ Server is not running! Start with: docker compose up")
        exit(1)
    
    # Test languages
    lang_data = test_languages()
    
    # Test subtitles without language
    test_subtitles()
    
    # Test subtitles with specific language if available
    if 'languages' in lang_data and lang_data['languages']:
        first_lang = lang_data['languages'][0]['code']
        test_subtitles(first_lang)
    
    print("\n✅ All tests completed!")