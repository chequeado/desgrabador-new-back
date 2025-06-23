from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    YouTubeRequestFailed
)
from youtube_transcript_api.proxies import WebshareProxyConfig
import re
import os
import logging

logger = logging.getLogger('subtitles')

# Inicializar YouTubeTranscriptApi con o sin proxies según configuración
def get_youtube_api():
    """
    Obtiene una instancia de YouTubeTranscriptApi configurada según USE_PROXY
    """
    if os.getenv('USE_PROXY', 'False') == 'True':
        username = os.getenv('WEBSHARE_PROXY_USERNAME')
        password = os.getenv('WEBSHARE_PROXY_PASSWORD')
        
        if not username or not password:
            logger.error("USE_PROXY=True but WEBSHARE_PROXY_USERNAME or WEBSHARE_PROXY_PASSWORD not set")
            raise ValueError("Proxy credentials missing. Set WEBSHARE_PROXY_USERNAME and WEBSHARE_PROXY_PASSWORD")
        
        logger.info("Using Webshare proxies")
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=username,
                proxy_password=password,
            )
        )
    else:
        logger.info("Using direct connection (no proxy)")
        return YouTubeTranscriptApi()

# Instancia global del API
youtube_api = get_youtube_api()

def extract_video_id(url):
    """
    Extrae el ID del video de una URL de YouTube
    Soporta: youtube.com/watch?v=ID y youtu.be/ID
    """
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    return None

def get_available_languages(video_url):
    """
    Lista todos los idiomas disponibles para un video
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return {'error': 'Invalid YouTube URL'}
    
    use_proxy = os.getenv('USE_PROXY', 'False') == 'True'
    
    try:
        transcript_list = youtube_api.list_transcripts(video_id)
        
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
            'proxy_used': use_proxy
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
    Obtiene los subtítulos de un video de YouTube
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return {'error': 'Invalid YouTube URL'}
    
    use_proxy = os.getenv('USE_PROXY', 'False') == 'True'
    logger.info(f"Getting subtitles for video {video_id}, proxy enabled: {use_proxy}")
    
    try:
        # Obtener transcripción
        if language_code:
            logger.info(f"Requesting subtitles in language: {language_code}")
            transcript = youtube_api.get_transcript(
                video_id, 
                languages=[language_code]
            )
        else:
            logger.info("Requesting subtitles in default language")
            transcript = youtube_api.get_transcript(video_id)
        
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
            'proxy_used': use_proxy
        }
        
    except YouTubeRequestFailed as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            logger.error(f"Rate limited: {error_msg}")
            return {
                'error': 'Too many requests - rate limited by YouTube',
                'details': error_msg,
                'proxy_used': use_proxy
            }
        else:
            return {
                'error': f'YouTube request failed: {type(e).__name__}',
                'details': error_msg,
                'proxy_used': use_proxy
            }
            
    except TranscriptsDisabled:
        return {'error': 'Subtitles are disabled for this video'}
        
    except NoTranscriptFound:
        if language_code:
            return {
                'error': f'No transcript found for language code: {language_code}',
                'suggestion': 'Try listing available languages first'
            }
        return {'error': 'No transcript found for this video'}
        
    except VideoUnavailable:
        return {'error': 'Video is unavailable'}
        
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        return {
            'error': f'Unexpected error: {type(e).__name__}',
            'details': str(e),
            'proxy_used': use_proxy
        }