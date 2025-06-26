from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .services import get_subtitles, extract_video_id, get_available_languages, test_proxy_connectivity
from .turnstile import require_turnstile 
import os
import json
import time
import hashlib
import hmac

# Token de sesión temporal (válido por 5 minutos)
SESSION_TOKEN_DURATION = 300  # segundos

def generate_session_token(video_id):
    """Genera un token de sesión temporal para un video específico"""
    secret_key = os.getenv('SECRET_KEY', 'django-secret-key')
    timestamp = str(int(time.time()))
    
    # Crear un token que incluya video_id y timestamp
    message = f"{video_id}:{timestamp}"
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{message}:{signature}"

def validate_session_token(token, video_id):
    """Valida un token de sesión"""
    try:
        parts = token.split(':')
        if len(parts) != 3:
            return False
            
        token_video_id, timestamp, signature = parts
        
        # Verificar que el video_id coincida
        if token_video_id != video_id:
            return False
            
        # Verificar que no haya expirado
        token_time = int(timestamp)
        current_time = int(time.time())
        if current_time - token_time > SESSION_TOKEN_DURATION:
            return False
            
        # Verificar la firma
        secret_key = os.getenv('SECRET_KEY', 'django-secret-key')
        message = f"{token_video_id}:{timestamp}"
        expected_signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception:
        return False

# Add to your existing health_check function
@swagger_auto_schema(
    method='get',
    operation_description="Check if the API is running",
    responses={200: "API health status with environment info"}
)
@api_view(['GET'])
def health_check(request):
    health_data = {
        'status': 'ok', 
        'message': 'Subtitles API is running',
        'proxy_enabled': os.getenv('USE_PROXY') == 'True',
        'proxy_configured': bool(os.getenv('WEBSHARE_PROXY_USERNAME') and os.getenv('WEBSHARE_PROXY_PASSWORD'))
    }
    return Response(health_data)


@api_view(['POST'])
def test_video_id(request):
    """Endpoint de debug para probar extracción de ID"""
    video_url = request.data.get('url')
    video_id = extract_video_id(video_url) if video_url else None
    return Response({
        'url': video_url,
        'extracted_id': video_id
    })

# Esquema de request para languages
languages_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['url'],
    properties={
        'url': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='YouTube video URL',
            example='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        ),
    }
)

languages_response = openapi.Response(
    description="List of available languages",
    examples={
        "application/json": {
            "video_id": "dQw4w9WgXcQ",
            "languages": [
                {
                    "code": "en",
                    "name": "English",
                    "is_generated": False,
                    "is_translatable": True
                },
                {
                    "code": "es",
                    "name": "Spanish",
                    "is_generated": True,
                    "is_translatable": True
                }
            ],
            "total": 5,
            "proxy_used": False,
            "session_token": "video_id:timestamp:signature"  # NUEVO
        }
    }
)

@swagger_auto_schema(
    method='post',
    request_body=languages_request,
    responses={
        200: languages_response,
        400: 'Bad Request - Invalid URL or video not found'
    },
    operation_description="Get all available subtitle languages for a YouTube video"
)
@api_view(['POST'])
@require_turnstile  # Solo aquí se valida Turnstile
def get_languages_view(request):
    """Obtiene todos los idiomas disponibles para un video"""
    video_url = request.data.get('url')
    
    if not video_url:
        return Response(
            {'error': 'URL is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    result = get_available_languages(video_url)
    
    if 'error' in result:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    # Generar token de sesión para este video
    session_token = generate_session_token(result['video_id'])
    result['session_token'] = session_token
    
    return Response(result)

extract_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['url'],
    properties={
        'url': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='YouTube video URL',
            example='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        ),
        'language_code': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Language code (optional)',
            example='en'
        ),
    }
)

@swagger_auto_schema(
    method='post',
    request_body=extract_request,
    responses={
        200: openapi.Response(
            description="Subtitles extracted successfully",
            examples={
                "application/json": {
                    "video_id": "dQw4w9WgXcQ",
                    "subtitles": [
                        {
                            "text": "Never gonna give you up",
                            "start": 0.0,
                            "duration": 2.5
                        }
                    ],
                    "subtitle_count": 150,
                    "language_code": "en",
                    "total_duration": 212.5,
                    "proxy_used": False,
                    "attempts": 1
                }
            }
        ),
        400: 'Bad Request - Invalid URL, video not found, or language not available'
    },
    operation_description="Extract subtitles from a YouTube video in the specified language"
)
@api_view(['POST'])
def get_subtitles_view(request):
    """Obtiene los subtítulos en el idioma especificado"""
    video_url = request.data.get('url')
    language_code = request.data.get('language_code')
    
    if not video_url:
        return Response(
            {'error': 'URL is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Extraer video_id para validación
    video_id = extract_video_id(video_url)
    if not video_id:
        return Response(
            {'error': 'Invalid YouTube URL'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar token de sesión
    session_token = request.headers.get('X-Session-Token')
    
    if not session_token or not validate_session_token(session_token, video_id):
        # Si no hay token de sesión válido, verificar Turnstile
        if os.getenv('TURNSTILE_ENABLED', 'True') == 'True':
            turnstile_token = request.headers.get('X-Turnstile-Token')
            if not turnstile_token:
                return Response({
                    'error': 'Session expired. Please reload the video.',
                    'code': 'session_expired'
                }, status=status.HTTP_403)
    
    # Llamar al servicio con el código de idioma si se proporciona
    result = get_subtitles(video_url, language_code)
    
    # Si hay error, devolver 400
    if 'error' in result:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)