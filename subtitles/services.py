from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    YouTubeRequestFailed
)
import re
import os
import random
import time

def extract_video_id(url):
    """
    Extrae el ID del video de una URL de YouTube
    Soporta: youtube.com/watch?v=ID y youtu.be/ID
    """
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    return None

def get_all_proxies():
    """
    Obtiene todos los proxies disponibles
    """
    proxy_list = os.getenv('WEBSHARE_PROXY_LIST', '')
    if not proxy_list:
        return []
    
    return [p.strip() for p in proxy_list.split(',') if p.strip()]

def get_proxy_config(exclude_proxies=None):
    """
    Construye la configuración del proxy desde las variables de entorno
    """
    if os.getenv('USE_PROXY', 'False') != 'True':
        return None
    
    # Si USE_PROXY=True, DEBE usar proxies o fallar
    username = os.getenv('WEBSHARE_PROXY_USERNAME')
    password = os.getenv('WEBSHARE_PROXY_PASSWORD')
    
    if not all([username, password]):
        raise ValueError("USE_PROXY=True but proxy credentials are missing. Set WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD")
    
    all_proxies = get_all_proxies()
    if not all_proxies:
        raise ValueError("USE_PROXY=True but no proxies found in WEBSHARE_PROXY_LIST")
    
    if exclude_proxies:
        available_proxies = [p for p in all_proxies if p not in exclude_proxies]
    else:
        available_proxies = all_proxies
    
    if not available_proxies:
        raise ValueError("All proxies have been excluded/failed")
    
    selected_proxy = random.choice(available_proxies)
    print(f"Selected proxy: {selected_proxy}")
    
    proxy_url = f"http://{username}:{password}@{selected_proxy}"
    return {
        "http": proxy_url,
        "https": proxy_url
    }, selected_proxy

def get_available_languages(video_url):
    """
    Lista todos los idiomas disponibles para un video
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return {'error': 'Invalid YouTube URL'}
    
    use_proxy = os.getenv('USE_PROXY', 'False') == 'True'
    
    try:
        proxies = None
        if use_proxy:
            try:
                proxy_result = get_proxy_config()
                if proxy_result:
                    proxies, _ = proxy_result
            except ValueError as e:
                return {
                    'error': 'Proxy configuration error',
                    'details': str(e)
                }
        
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, proxies=proxies)
        
        languages = []
        for transcript in transcript_list:
            lang_info = {
                'code': transcript.language_code,
                'name': transcript.language,
                'is_generated': transcript.is_generated,
                'is_translatable': transcript.is_translatable
            }
            languages.append(lang_info)
        
        # Ordenar: manuales primero, luego por nombre
        languages.sort(key=lambda x: (x['is_generated'], x['name']))
        
        return {
            'video_id': video_id,
            'languages': languages,
            'total': len(languages),
            'proxy_used': bool(proxies)
        }
        
    except TranscriptsDisabled:
        return {'error': 'Subtitles are disabled for this video'}
    except VideoUnavailable:
        return {'error': 'Video is unavailable'}
    except Exception as e:
        return {
            'error': f'Error getting languages: {type(e).__name__}',
            'details': str(e)
        }

def get_subtitles(video_url, language_code=None):
    """
    Obtiene los subtítulos de un video de YouTube con reintentos
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return {'error': 'Invalid YouTube URL'}
    
    use_proxy = os.getenv('USE_PROXY', 'False') == 'True'
    print(f"USE_PROXY setting: {os.getenv('USE_PROXY')} -> using proxy: {use_proxy}")
    
    failed_proxies = []
    max_retries = 3 if use_proxy else 1
    
    for attempt in range(max_retries):
        try:
            if use_proxy:
                try:
                    proxy_result = get_proxy_config(exclude_proxies=failed_proxies)
                    if proxy_result:
                        proxies, current_proxy = proxy_result
                        print(f"Attempt {attempt + 1} with proxy {current_proxy}")
                    else:
                        # Esto no debería pasar ahora, pero por si acaso
                        proxies = None
                        current_proxy = None
                except ValueError as e:
                    return {
                        'error': 'Proxy configuration error',
                        'details': str(e),
                        'attempts': attempt + 1
                    }
            else:
                proxies = None
                current_proxy = None
                print(f"Attempt {attempt + 1} WITHOUT proxy (direct connection)")
            
            # Obtener transcripción
            if language_code:
                print(f"Requesting subtitles in language: {language_code}")
                transcript = YouTubeTranscriptApi.get_transcript(
                    video_id, 
                    languages=[language_code],
                    proxies=proxies
                )
            else:
                print("Requesting subtitles in default language")
                transcript = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)
            
            # Calcular duración total
            total_duration = 0
            if transcript:
                last_item = transcript[-1]
                total_duration = last_item['start'] + last_item.get('duration', 0)
            
            return {
                'video_id': video_id,
                'subtitles': transcript,
                'subtitle_count': len(transcript),
                'language_code': language_code,
                'total_duration': round(total_duration, 2),
                'proxy_used': bool(proxies),
                'attempts': attempt + 1
            }
            
        except YouTubeRequestFailed as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"Rate limited on attempt {attempt + 1}")
                if current_proxy:
                    failed_proxies.append(current_proxy)
                    print(f"Marked proxy {current_proxy} as failed")
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    return {
                        'error': 'Too many failed attempts',
                        'details': str(e),
                        'proxy_used': bool(proxies),
                        'attempts': attempt + 1
                    }
            else:
                return {
                    'error': f'YouTube request failed: {type(e).__name__}',
                    'details': str(e),
                    'proxy_used': bool(proxies)
                }
                
        except TranscriptsDisabled:
            return {'error': 'Subtitles are disabled for this video'}
                
        except NoTranscriptFound:
            # Si se especificó un idioma, dar más info
            if language_code:
                return {
                    'error': f'No transcript found for language code: {language_code}',
                    'suggestion': 'Try listing available languages first'
                }
            return {'error': 'No transcript found for this video'}
            
        except VideoUnavailable:
            return {'error': 'Video is unavailable'}
            
        except Exception as e:
            return {
                'error': f'Unexpected error: {type(e).__name__}',
                'details': str(e),
                'proxy_used': bool(proxies)
            }