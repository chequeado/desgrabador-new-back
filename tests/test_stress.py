#!/usr/bin/env python
"""
Test de estrés para la API de subtítulos
Simula múltiples usuarios concurrentes para verificar el manejo de rate limits
"""
import os
import sys
import time
import random
import requests
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import json

# Configuración
BASE_URL = "http://localhost:8000/api/subtitles"

# Videos de prueba variados (para simular diferentes usuarios)
TEST_VIDEOS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo
    "https://www.youtube.com/watch?v=9bZkp7q19f0",  # Gangnam Style
    "https://www.youtube.com/watch?v=kJQP7kiw5Fk",  # Despacito
    "https://www.youtube.com/watch?v=hTWKbfoikeg",  # Smells Like Teen Spirit
    "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",  # Bohemian Rhapsody
    "https://www.youtube.com/watch?v=YQHsXMglC9A",  # Hello - Adele
]

class StressTestResult:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0
        self.response_times = []
        self.errors = defaultdict(int)
        self.start_time = None
        self.end_time = None
        
    def add_success(self, response_time):
        self.successful_requests += 1
        self.response_times.append(response_time)
        
    def add_failure(self, error_type, is_rate_limit=False):
        self.failed_requests += 1
        self.errors[error_type] += 1
        if is_rate_limit:
            self.rate_limited_requests += 1
            
    def get_summary(self):
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        summary = {
            "duration_seconds": round(total_time, 2),
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "rate_limited": self.rate_limited_requests,
            "success_rate": round(self.successful_requests / self.total_requests * 100, 2) if self.total_requests > 0 else 0,
            "requests_per_second": round(self.total_requests / total_time, 2) if total_time > 0 else 0,
        }
        
        if self.response_times:
            summary["response_times"] = {
                "min": round(min(self.response_times), 2),
                "max": round(max(self.response_times), 2),
                "mean": round(statistics.mean(self.response_times), 2),
                "median": round(statistics.median(self.response_times), 2),
                "p95": round(statistics.quantiles(self.response_times, n=20)[18], 2) if len(self.response_times) > 20 else "N/A",
                "p99": round(statistics.quantiles(self.response_times, n=100)[98], 2) if len(self.response_times) > 100 else "N/A",
            }
        
        summary["errors"] = dict(self.errors)
        
        return summary

def make_request(video_url, endpoint="extract", language_code=None):
    """Hace una solicitud a la API y mide el tiempo de respuesta"""
    start_time = time.time()
    
    try:
        if endpoint == "extract":
            payload = {"url": video_url}
            if language_code:
                payload["language_code"] = language_code
            response = requests.post(
                f"{BASE_URL}/extract/",
                json=payload,
                timeout=30
            )
        else:  # languages
            response = requests.post(
                f"{BASE_URL}/languages/",
                json={"url": video_url},
                timeout=30
            )
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            return {
                "success": True,
                "response_time": response_time,
                "proxy_used": response.json().get("proxy_used", False)
            }
        else:
            error_data = response.json()
            is_rate_limit = "429" in str(error_data.get("details", "")) or "rate" in error_data.get("error", "").lower()
            
            return {
                "success": False,
                "error": error_data.get("error", "Unknown error"),
                "is_rate_limit": is_rate_limit,
                "response_time": response_time
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout",
            "is_rate_limit": False,
            "response_time": time.time() - start_time
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)[:50]}",
            "is_rate_limit": False,
            "response_time": time.time() - start_time
        }

def worker_task(task_id, video_url, endpoint="extract"):
    """Tarea individual del worker"""
    # Pequeño delay aleatorio para simular usuarios reales
    time.sleep(random.uniform(0, 0.5))
    
    result = make_request(video_url, endpoint)
    result["task_id"] = task_id
    result["video_url"] = video_url
    
    return result

def run_stress_test(
    num_requests=50,
    max_workers=10,
    endpoint="extract",
    use_random_videos=True,
    delay_between_batches=0
):
    """
    Ejecuta el test de estrés
    
    Args:
        num_requests: Número total de requests a realizar
        max_workers: Número máximo de workers concurrentes
        endpoint: "extract" o "languages"
        use_random_videos: Si True, usa videos aleatorios. Si False, usa siempre el mismo
        delay_between_batches: Delay en segundos entre batches de workers
    """
    print(f"\n🚀 STRESS TEST - YouTube Subtitles API")
    print("="*60)
    print(f"📊 Configuration:")
    print(f"   Total requests: {num_requests}")
    print(f"   Concurrent workers: {max_workers}")
    print(f"   Endpoint: {endpoint}")
    print(f"   Random videos: {use_random_videos}")
    print(f"   Proxies enabled: {os.getenv('USE_PROXY', 'False')}")
    
    if os.getenv('USE_PROXY') != 'True':
        print("\n⚠️  WARNING: Proxies are disabled! YouTube may rate limit.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    print(f"\n⏳ Starting stress test...")
    print(f"{'Progress':.<50}", end='', flush=True)
    
    results = StressTestResult()
    results.start_time = time.time()
    results.total_requests = num_requests
    
    # Ejecutar requests en paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        for i in range(num_requests):
            if use_random_videos:
                video_url = random.choice(TEST_VIDEOS)
            else:
                video_url = TEST_VIDEOS[0]
            
            future = executor.submit(worker_task, i, video_url, endpoint)
            futures.append(future)
            
            # Opcional: delay entre batches
            if delay_between_batches > 0 and (i + 1) % max_workers == 0:
                time.sleep(delay_between_batches)
        
        # Procesar resultados conforme se completan
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 10 == 0:
                print('.', end='', flush=True)
            
            try:
                result = future.result()
                
                if result["success"]:
                    results.add_success(result["response_time"])
                else:
                    results.add_failure(
                        result["error"],
                        result.get("is_rate_limit", False)
                    )
                    
            except Exception as e:
                results.add_failure(f"Future error: {type(e).__name__}")
    
    results.end_time = time.time()
    print(" ✅")
    
    # Mostrar resultados
    print_results(results)
    
    # Guardar resultados
    save_results(results)
    
    return results

def print_results(results: StressTestResult):
    """Imprime los resultados del test"""
    summary = results.get_summary()
    
    print(f"\n📈 RESULTS")
    print("="*60)
    
    print(f"\n⏱️  Performance:")
    print(f"   Total duration: {summary['duration_seconds']}s")
    print(f"   Requests/second: {summary['requests_per_second']}")
    
    print(f"\n📊 Request Statistics:")
    print(f"   Total requests: {summary['total_requests']}")
    print(f"   Successful: {summary['successful']} ({summary['success_rate']}%)")
    print(f"   Failed: {summary['failed']}")
    print(f"   Rate limited: {summary['rate_limited']}")
    
    if "response_times" in summary:
        print(f"\n⏱️  Response Times:")
        rt = summary["response_times"]
        print(f"   Min: {rt['min']}s")
        print(f"   Max: {rt['max']}s")
        print(f"   Mean: {rt['mean']}s")
        print(f"   Median: {rt['median']}s")
        if rt.get('p95') != "N/A":
            print(f"   P95: {rt['p95']}s")
        if rt.get('p99') != "N/A":
            print(f"   P99: {rt['p99']}s")
    
    if summary["errors"]:
        print(f"\n❌ Errors:")
        for error_type, count in sorted(summary["errors"].items(), key=lambda x: x[1], reverse=True):
            print(f"   {error_type}: {count}")
    
    # Análisis y recomendaciones
    print(f"\n💡 Analysis:")
    
    if summary['success_rate'] >= 95:
        print(f"   ✅ Excellent! {summary['success_rate']}% success rate")
    elif summary['success_rate'] >= 80:
        print(f"   ⚠️  Good, but could be better: {summary['success_rate']}% success rate")
    else:
        print(f"   ❌ Poor performance: {summary['success_rate']}% success rate")
    
    if summary['rate_limited'] > 0:
        print(f"   ⚠️  Rate limiting detected: {summary['rate_limited']} requests")
        if os.getenv('USE_PROXY') != 'True':
            print(f"   💡 Enable proxies to avoid rate limiting")
    
    if summary.get('response_times', {}).get('mean', 0) > 5:
        print(f"   ⚠️  Slow response times (mean: {summary['response_times']['mean']}s)")

def save_results(results: StressTestResult):
    """Guarda los resultados en un archivo JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stress_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results.get_summary(), f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")

def run_incremental_test():
    """Ejecuta un test incremental para encontrar el límite"""
    print("\n🔬 INCREMENTAL STRESS TEST")
    print("Finding the breaking point by gradually increasing load...")
    
    worker_counts = [1, 5, 10, 20, 30, 50]
    
    for workers in worker_counts:
        print(f"\n\n{'='*60}")
        print(f"Testing with {workers} concurrent workers...")
        
        results = run_stress_test(
            num_requests=workers * 5,  # 5 requests per worker
            max_workers=workers,
            endpoint="extract",
            use_random_videos=True
        )
        
        if results.get_summary()['success_rate'] < 80:
            print(f"\n⚠️  Performance degraded at {workers} workers")
            break
        
        time.sleep(5)  # Pause between tests

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Stress test for YouTube Subtitles API')
    parser.add_argument('--requests', type=int, default=50, help='Total number of requests')
    parser.add_argument('--workers', type=int, default=10, help='Number of concurrent workers')
    parser.add_argument('--endpoint', choices=['extract', 'languages'], default='extract', help='API endpoint to test')
    parser.add_argument('--same-video', action='store_true', help='Use same video for all requests')
    parser.add_argument('--delay', type=float, default=0, help='Delay between worker batches')
    parser.add_argument('--incremental', action='store_true', help='Run incremental test to find limits')
    
    args = parser.parse_args()
    
    if args.incremental:
        run_incremental_test()
    else:
        run_stress_test(
            num_requests=args.requests,
            max_workers=args.workers,
            endpoint=args.endpoint,
            use_random_videos=not args.same_video,
            delay_between_batches=args.delay
        )