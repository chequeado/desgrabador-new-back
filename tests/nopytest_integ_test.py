#!/usr/bin/env python
"""
Test integral del sistema de subtítulos
"""
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuración
BASE_URL = "http://localhost:8000/api/subtitles"
TEST_VIDEOS = {
    "rickroll": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "short": "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Me at the zoo
}

def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def print_env_config():
    """Muestra configuración actual (ocultando valores sensibles)"""
    print_section("CONFIGURACIÓN ACTUAL")
    
    env_vars = {
        "USE_PROXY": os.getenv('USE_PROXY'),
        "DEBUG": os.getenv('DEBUG'),
        "CORS_ALLOWED_ORIGINS": os.getenv('CORS_ALLOWED_ORIGINS'),
        "WEBSHARE_PROXY_USERNAME": "***" if os.getenv('WEBSHARE_PROXY_USERNAME') else "Not set",
        "WEBSHARE_PROXY_PASSWORD": "***" if os.getenv('WEBSHARE_PROXY_PASSWORD') else "Not set",
        "WEBSHARE_PROXY_LIST": f"{len(os.getenv('WEBSHARE_PROXY_LIST', '').split(','))} proxies" if os.getenv('WEBSHARE_PROXY_LIST') else "Not set"
    }
    
    for key, value in env_vars.items():
        print(f"  {key}: {value}")

def test_health():
    """Test endpoint de salud"""
    print_section("TEST 1: Health Check")
    try:
        resp = requests.get(f"{BASE_URL}/health/", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'ok'
        print("  ✅ Health check passed")
        return True
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        return False

def test_languages(video_url):
    """Test obtener idiomas"""
    print_section("TEST 2: Get Languages")
    try:
        resp = requests.post(
            f"{BASE_URL}/languages/",
            json={"url": video_url},
            timeout=15
        )
        assert resp.status_code == 200
        data = resp.json()
        
        print(f"  ✅ Found {data['total']} languages")
        print(f"  📊 Proxy used: {data.get('proxy_used', False)}")
        
        # Mostrar algunos idiomas
        for i, lang in enumerate(data['languages'][:3]):
            type_str = "auto" if lang['is_generated'] else "manual"
            print(f"     {i+1}. {lang['name']} ({lang['code']}) - {type_str}")
        
        return data
    except Exception as e:
        print(f"  ❌ Languages test failed: {e}")
        return None

def test_subtitles(video_url, language_code=None):
    """Test obtener subtítulos"""
    lang_str = f" in {language_code}" if language_code else ""
    print_section(f"TEST 3: Get Subtitles{lang_str}")
    
    try:
        payload = {"url": video_url}
        if language_code:
            payload["language_code"] = language_code
            
        resp = requests.post(
            f"{BASE_URL}/extract/",
            json=payload,
            timeout=20
        )
        
        if resp.status_code != 200:
            data = resp.json()
            print(f"  ❌ Failed: {data.get('error', 'Unknown error')}")
            return False
            
        data = resp.json()
        
        print(f"  ✅ Got {data['subtitle_count']} subtitles")
        print(f"  📊 Video duration: {data['total_duration']}s")
        print(f"  📊 Proxy used: {data.get('proxy_used', False)}")
        print(f"  📊 Attempts: {data.get('attempts', 1)}")
        
        # Mostrar muestra
        if data['subtitles']:
            sample = data['subtitles'][0]['text'][:100]
            print(f"  📝 Sample: \"{sample}...\"")
        
        return True
    except Exception as e:
        print(f"  ❌ Subtitles test failed: {e}")
        return False

def test_error_handling():
    """Test manejo de errores"""
    print_section("TEST 4: Error Handling")
    
    tests = [
        ("Invalid URL", {"url": "not-a-youtube-url"}),
        ("Empty URL", {"url": ""}),
        ("No URL", {}),
        ("Invalid video ID", {"url": "https://www.youtube.com/watch?v=invalid123"}),
    ]
    
    passed = 0
    for test_name, payload in tests:
        try:
            resp = requests.post(f"{BASE_URL}/extract/", json=payload, timeout=10)
            if resp.status_code == 400:
                print(f"  ✅ {test_name}: Correctly returned error")
                passed += 1
            else:
                print(f"  ❌ {test_name}: Should have failed")
        except:
            print(f"  ❌ {test_name}: Request failed")
    
    print(f"\n  Summary: {passed}/{len(tests)} error tests passed")
    return passed == len(tests)

def test_performance():
    """Test de rendimiento básico"""
    print_section("TEST 5: Performance")
    
    import time
    times = []
    
    for i in range(3):
        start = time.time()
        resp = requests.post(
            f"{BASE_URL}/languages/",
            json={"url": TEST_VIDEOS["rickroll"]},
            timeout=30
        )
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Request {i+1}: {elapsed:.2f}s")
    
    avg_time = sum(times) / len(times)
    print(f"\n  ⏱️  Average response time: {avg_time:.2f}s")
    return avg_time < 10  # Debe responder en menos de 10s

def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n🧪 YOUTUBE SUBTITLES API - INTEGRATION TEST")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Mostrar config
    print_env_config()
    
    # Verificar servidor
    if not test_health():
        print("\n❌ Server is not running! Start with: docker compose up")
        return
    
    # Tests principales
    results = []
    
    # Test languages
    lang_data = test_languages(TEST_VIDEOS["rickroll"])
    results.append(lang_data is not None)
    
    # Test subtitles sin idioma
    results.append(test_subtitles(TEST_VIDEOS["rickroll"]))
    
    # Test subtitles con idioma específico
    if lang_data and lang_data.get('languages'):
        first_lang = lang_data['languages'][0]['code']
        results.append(test_subtitles(TEST_VIDEOS["rickroll"], first_lang))
    
    # Test error handling
    results.append(test_error_handling())
    
    results.append(test_performance())
    
    print_section("TEST SUMMARY")
    passed = sum(results)
    total = len(results)
    
    print(f"  Passed: {passed}/{total}")
    print(f"  Status: {'✅ ALL TESTS PASSED' if passed == total else '❌ SOME TESTS FAILED'}")
    print(f"  Proxy enabled: {os.getenv('USE_PROXY', 'False')}")
    
    if os.getenv('USE_PROXY') == 'True':
        print(f"  Proxy config: {'✅ Complete' if os.getenv('WEBSHARE_PROXY_USERNAME') else '❌ Missing'}")

if __name__ == "__main__":
    run_all_tests()