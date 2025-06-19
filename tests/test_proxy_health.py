"""
Test de salud de proxies - Verifica que los proxies funcionen con YouTube
Ejecutar con: docker compose exec web python tests/test_proxy_health.py
"""
import os
import sys
import time
import random
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
os.environ['USE_PROXY'] = 'True'

import django
django.setup()

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from subtitles.proxy_manager import ProxyManager, WebshareProxyProvider


class ProxyHealthChecker:
    """Verifica la salud de los proxies"""
    
    def __init__(self, sample_size: int = 10, max_workers: int = 5):
        self.sample_size = sample_size
        self.max_workers = max_workers
        self.results = {
            'total_tested': 0,
            'youtube_success': 0,
            'youtube_failed': 0,
            'general_success': 0,
            'general_failed': 0,
            'response_times': [],
            'countries': {},
            'errors': {},
            'failed_proxies': []
        }
        
        # Videos de prueba (cortos para rapidez)
        self.test_videos = [
            "jNQXAC9IVRw",  # Me at the zoo (18s)
            "aqz-KE-bpKQ",  # Big Buck Bunny (60s)
        ]
    
    def test_single_proxy(self, proxy_config: Dict, proxy_id: str) -> Dict:
        """Prueba un proxy individual"""
        result = {
            'proxy_id': proxy_id,
            'youtube_test': False,
            'general_test': False,
            'response_time': None,
            'error': None,
            'country': None
        }
        
        start_time = time.time()
        
        try:
            # Test 1: Conexión general (Google)
            response = requests.get(
                'https://www.google.com/robots.txt',
                proxies=proxy_config,
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            if response.status_code == 200:
                result['general_test'] = True
                result['response_time'] = time.time() - start_time
            
            # Test 2: YouTube
            video_id = random.choice(self.test_videos)
            try:
                # Intentar obtener solo los primeros subtítulos
                transcript = YouTubeTranscriptApi.list_transcripts(
                    video_id,
                    proxies=proxy_config
                )
                
                # Si podemos listar transcripts, el proxy funciona con YouTube
                for t in transcript:
                    result['youtube_test'] = True
                    result['country'] = proxy_id.split('-')[0] if '-' in proxy_id else 'Unknown'
                    break
                    
            except Exception as yt_error:
                # YouTube falló pero conexión general puede estar OK
                if "429" in str(yt_error):
                    result['error'] = "Rate limited by YouTube"
                else:
                    result['error'] = f"YouTube error: {type(yt_error).__name__}"
            
        except requests.exceptions.Timeout:
            result['error'] = "Timeout"
        except requests.exceptions.ProxyError:
            result['error'] = "Proxy connection failed"
        except Exception as e:
            result['error'] = f"{type(e).__name__}: {str(e)[:50]}"
        
        return result
    
    def run_health_check(self):
        """Ejecuta el chequeo de salud en paralelo"""
        print(f"\n🏥 PROXY HEALTH CHECK")
        print(f"{'='*60}\n")
        
        # Obtener proxies
        token = os.getenv('WEBSHARE_API_TOKEN', 'a79llykhvz6zr9qrg0nn8oscjowcia2iyugeslip')
        provider = WebshareProxyProvider(token)
        proxy_list = provider.get_proxy_list()
        
        if not proxy_list:
            print("❌ No se pudieron obtener proxies")
            return
        
        print(f"📊 Proxies disponibles: {len(proxy_list)}")
        print(f"🔍 Testeando muestra: {self.sample_size} proxies")
        print(f"⚡ Workers paralelos: {self.max_workers}")
        print(f"\n{'Progreso':.<30}", end='', flush=True)
        
        # Seleccionar muestra aleatoria
        sample = random.sample(proxy_list, min(self.sample_size, len(proxy_list)))
        
        # Ejecutar tests en paralelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_proxy = {
                executor.submit(
                    self.test_single_proxy, 
                    proxy.to_dict(), 
                    proxy.proxy_id
                ): proxy for proxy in sample
            }
            
            completed = 0
            for future in as_completed(future_to_proxy):
                completed += 1
                print('.', end='', flush=True)
                
                result = future.result()
                self.process_result(result)
        
        print(" ✅\n")
        self.print_report()
    
    def process_result(self, result: Dict):
        """Procesa el resultado de un test"""
        self.results['total_tested'] += 1
        
        if result['youtube_test']:
            self.results['youtube_success'] += 1
        else:
            self.results['youtube_failed'] += 1
            self.results['failed_proxies'].append(result['proxy_id'])
        
        if result['general_test']:
            self.results['general_success'] += 1
        else:
            self.results['general_failed'] += 1
        
        if result['response_time']:
            self.results['response_times'].append(result['response_time'])
        
        if result['country']:
            self.results['countries'][result['country']] = \
                self.results['countries'].get(result['country'], 0) + 1
        
        if result['error']:
            error_type = result['error'].split(':')[0]
            self.results['errors'][error_type] = \
                self.results['errors'].get(error_type, 0) + 1
    
    def print_report(self):
        """Imprime reporte detallado"""
        print("\n📈 REPORTE DE SALUD DE PROXIES")
        print("="*60)
        
        # Estadísticas generales
        print(f"\n📊 Estadísticas Generales:")
        print(f"   Total testeados: {self.results['total_tested']}")
        print(f"   Conexión general OK: {self.results['general_success']} "
              f"({self.results['general_success']/self.results['total_tested']*100:.1f}%)")
        print(f"   YouTube OK: {self.results['youtube_success']} "
              f"({self.results['youtube_success']/self.results['total_tested']*100:.1f}%)")
        
        # Tiempos de respuesta
        if self.results['response_times']:
            avg_time = sum(self.results['response_times']) / len(self.results['response_times'])
            min_time = min(self.results['response_times'])
            max_time = max(self.results['response_times'])
            print(f"\n⏱️  Tiempos de Respuesta:")
            print(f"   Promedio: {avg_time:.2f}s")
            print(f"   Mínimo: {min_time:.2f}s")
            print(f"   Máximo: {max_time:.2f}s")
        
        # Distribución por países
        if self.results['countries']:
            print(f"\n🌍 Distribución por País:")
            for country, count in sorted(self.results['countries'].items(), 
                                       key=lambda x: x[1], reverse=True):
                print(f"   {country}: {count}")
        
        # Errores encontrados
        if self.results['errors']:
            print(f"\n❌ Errores Encontrados:")
            for error, count in sorted(self.results['errors'].items(), 
                                      key=lambda x: x[1], reverse=True):
                print(f"   {error}: {count}")
        
        # Proxies fallidos
        if self.results['failed_proxies']:
            print(f"\n🚫 Proxies Fallidos (primeros 5):")
            for proxy_id in self.results['failed_proxies'][:5]:
                print(f"   - {proxy_id}")
        
        # Resumen
        print(f"\n✨ RESUMEN:")
        success_rate = self.results['youtube_success'] / self.results['total_tested'] * 100
        if success_rate >= 80:
            print(f"   ✅ Sistema saludable: {success_rate:.1f}% de éxito con YouTube")
        elif success_rate >= 50:
            print(f"   ⚠️  Sistema degradado: {success_rate:.1f}% de éxito con YouTube")
        else:
            print(f"   ❌ Sistema con problemas: {success_rate:.1f}% de éxito con YouTube")
        
        # Guardar reporte
        report_file = f"proxy_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Reporte guardado en: {report_file}")


def quick_health_check():
    """Chequeo rápido de salud (5 proxies)"""
    checker = ProxyHealthChecker(sample_size=5, max_workers=3)
    checker.run_health_check()


def full_health_check():
    """Chequeo completo de salud (25 proxies)"""
    checker = ProxyHealthChecker(sample_size=25, max_workers=5)
    checker.run_health_check()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Proxy Health Checker')
    parser.add_argument('--full', action='store_true', 
                       help='Run full health check (25 proxies)')
    parser.add_argument('--sample', type=int, default=10,
                       help='Number of proxies to test')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of parallel workers')
    
    args = parser.parse_args()
    
    if args.full:
        full_health_check()
    else:
        checker = ProxyHealthChecker(
            sample_size=args.sample,
            max_workers=args.workers
        )
        checker.run_health_check()