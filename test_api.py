#!/usr/bin/env python
"""
Script de prueba para la API de subtítulos
Uso: python test_api.py
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/subtitles"

TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

def test_health():
    print("1. Testing health endpoint...")
    resp = requests.get(f"{BASE_URL}/health/")
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}\n")

def test_languages():
    print("2. Testing languages endpoint...")
    resp = requests.post(
        f"{BASE_URL}/languages/",
        json={"url": TEST_VIDEO_URL}
    )
    print(f"   Status: {resp.status_code}")
    data = resp.json()
    
    if 'error' not in data:
        print(f"   Found {data['total']} languages:")
        for lang in data['languages'][:5]:  # Mostrar primeros 5
            generated = " (auto-generated)" if lang['is_generated'] else ""
            print(f"   - {lang['name']} ({lang['code']}){generated}")
        if data['total'] > 5:
            print(f"   ... and {data['total'] - 5} more")
    else:
        print(f"   Error: {data['error']}")
    
    print()
    return data

def test_subtitles(language_code=None):
    print(f"3. Testing subtitles endpoint{' with language ' + language_code if language_code else ''}...")
    
    payload = {"url": TEST_VIDEO_URL}
    if language_code:
        payload["language_code"] = language_code
    
    resp = requests.post(
        f"{BASE_URL}/extract/",
        json=payload
    )
    print(f"   Status: {resp.status_code}")
    data = resp.json()
    
    if 'error' not in data:
        print(f"   Video ID: {data['video_id']}")
        print(f"   Subtitle count: {data['subtitle_count']}")
        print(f"   Total duration: {data['total_duration']} seconds")
        print(f"   Language: {data.get('language_code', 'default')}")
        print(f"   First subtitle: {data['subtitles'][1]['text'][:500]}...")
    else:
        print(f"   Error: {data['error']}")
    
    print()

if __name__ == "__main__":
    print("YouTube Subtitles API Test\n")
    print(f"Testing with video: {TEST_VIDEO_URL}\n")
    
    # Test health
    test_health()
    
    # Test languages
    lang_data = test_languages()
    
    # Test subtitles without language
    test_subtitles()
    
    # Test subtitles with specific language if available
    if 'languages' in lang_data and lang_data['languages']:
        first_lang = lang_data['languages'][1]['code']
        test_subtitles(first_lang)