import requests
import os
from functools import wraps
from django.http import JsonResponse
import logging

logger = logging.getLogger('subtitles')

def verify_turnstile_token(token, ip_address):
    """
    Verifica el token con Cloudflare Turnstile
    Documentación: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
    """
    secret_key = os.getenv('TURNSTILE_SECRET_KEY')
    
    if not secret_key:
        logger.error("TURNSTILE_SECRET_KEY not configured")
        return {'success': False, 'error-codes': ['missing-secret-key']}
    
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': secret_key,
                'response': token,
                'remoteip': ip_address
            },
            timeout=5
        )
        
        result = response.json()
        
        if not result.get('success'):
            logger.warning(f"Turnstile validation failed: {result.get('error-codes', [])}")
        
        return result
        
    except requests.exceptions.Timeout:
        logger.error("Turnstile validation timeout")
        return {'success': False, 'error-codes': ['timeout']}
    except Exception as e:
        logger.error(f"Turnstile validation error: {str(e)}")
        return {'success': False, 'error-codes': ['request-failed']}

def require_turnstile(view_func):
    """
    Decorador para proteger vistas con Turnstile
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Verificar si Turnstile está habilitado
        if os.getenv('TURNSTILE_ENABLED', 'True') == 'False':
            return view_func(request, *args, **kwargs)
        
        # Obtener token del header
        token = request.headers.get('X-Turnstile-Token')
        
        if not token:
            logger.warning("Missing Turnstile token in request")
            return JsonResponse({
                'error': 'Security verification required',
                'code': 'missing_token'
            }, status=403)
        
        # Obtener IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Tomar la primera IP si hay varias
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', '')
        
        logger.info(f"Validating Turnstile token for IP: {ip_address}")
        
        # Verificar token
        result = verify_turnstile_token(token, ip_address)
        
        if not result.get('success'):
            logger.warning(f"Turnstile validation failed for IP {ip_address}")
            return JsonResponse({
                'error': 'Security verification failed',
                'code': 'invalid_token',
                'details': result.get('error-codes', [])
            }, status=403)
        
        logger.info("Turnstile validation successful")
        return view_func(request, *args, **kwargs)
    
    return wrapped_view