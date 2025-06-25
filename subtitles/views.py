from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .services import get_subtitles, extract_video_id, get_available_languages, test_proxy_connectivity
from .turnstile import require_turnstile 
import os

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
            "proxy_used": False
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
@require_turnstile
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
@require_turnstile 
def get_subtitles_view(request):
    """Obtiene los subtítulos en el idioma especificado"""
    video_url = request.data.get('url')
    language_code = request.data.get('language_code')  # Opcional
    
    if not video_url:
        return Response(
            {'error': 'URL is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Llamar al servicio con el código de idioma si se proporciona
    result = get_subtitles(video_url, language_code)
    
    # Si hay error, devolver 400
    if 'error' in result:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)