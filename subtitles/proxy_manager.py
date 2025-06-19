import os
import time
import logging
import requests
from collections import deque
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger('subtitles')


class ProxyConfig:
    """Representa la configuración de un proxy"""
    def __init__(self, host: str, port: int, username: str, password: str, proxy_id: str = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.proxy_id = proxy_id or f"{host}:{port}"
        
    def to_dict(self) -> Dict[str, str]:
        """Convierte a formato que espera youtube-transcript-api"""
        proxy_url = f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def __str__(self):
        return f"{self.host}:{self.port}"


class BaseProxyProvider(ABC):
    """Interface base para proveedores de proxies"""
    
    @abstractmethod
    def get_proxy_list(self) -> List[ProxyConfig]:
        """Obtiene lista de proxies disponibles"""
        pass


class WebshareProxyProvider(BaseProxyProvider):
    """Provider que obtiene proxies de la API de Webshare"""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.api_url = "https://proxy.webshare.io/api/v2/proxy/list/"
        self._cache = None
        self._cache_timestamp = None
        self.cache_duration = 3600  # 1 hora
        # Host fijo para proxies backbone
        self.backbone_host = "p.webshare.io"
        
    def get_proxy_list(self) -> List[ProxyConfig]:
        """Obtiene lista de proxies de Webshare API con cache"""
        
        # Verificar cache
        if self._cache and self._cache_timestamp:
            if time.time() - self._cache_timestamp < self.cache_duration:
                logger.debug(f"Returning {len(self._cache)} proxies from cache")
                return self._cache
        
        try:
            logger.info("Fetching fresh proxy list from Webshare API")
            
            # Para proxies residenciales usar mode=backbone
            response = requests.get(
                self.api_url,
                headers={"Authorization": f"Token {self.api_token}"},
                params={
                    "mode": "backbone",  # Requerido para proxies residenciales
                    "page": 1,
                    "page_size": 100  # Obtener 100 proxies
                },
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            proxies = []
            results = data.get('results', [])
            
            if not results:
                logger.warning("No proxies returned from API")
                return []
            
            logger.info(f"API returned {len(results)} proxies (total available: {data.get('count', '?')})")
            
            for proxy_data in results:
                try:
                    # Para backbone proxies, usar el host fijo p.webshare.io
                    # El proxy_address puede ser None, eso es normal
                    proxy = ProxyConfig(
                        host=self.backbone_host,  # Siempre p.webshare.io para backbone
                        port=proxy_data['port'],
                        username=proxy_data['username'],
                        password=proxy_data['password'],
                        proxy_id=str(proxy_data.get('id', f"backbone-{proxy_data['username']}"))
                    )
                    proxies.append(proxy)
                    
                except KeyError as e:
                    logger.error(f"Missing required field in proxy data: {e}")
                    logger.debug(f"Proxy data: {proxy_data}")
                    continue
            
            # Actualizar cache
            self._cache = proxies
            self._cache_timestamp = time.time()
            
            logger.info(f"Successfully fetched {len(proxies)} backbone proxies from Webshare")
            logger.info(f"All proxies will connect through {self.backbone_host}")
            return proxies
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching proxies from Webshare: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            # Si hay cache viejo, usarlo
            if self._cache:
                logger.warning("Using stale cache due to API error")
                return self._cache
            return []
        except Exception as e:
            logger.error(f"Unexpected error in WebshareProxyProvider: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

class EnvProxyProvider(BaseProxyProvider):
    """Provider legacy que lee proxies del .env (retrocompatible)"""
    
    def __init__(self):
        self.username = os.getenv('WEBSHARE_PROXY_USERNAME')
        self.password = os.getenv('WEBSHARE_PROXY_PASSWORD')
        self.proxy_list_str = os.getenv('WEBSHARE_PROXY_LIST', '')
        
    def get_proxy_list(self) -> List[ProxyConfig]:
        """Obtiene lista de proxies desde variables de entorno"""
        if not all([self.username, self.password, self.proxy_list_str]):
            logger.error("Missing proxy credentials in environment variables")
            return []
        
        proxies = []
        for proxy_str in self.proxy_list_str.split(','):
            proxy_str = proxy_str.strip()
            if proxy_str and ':' in proxy_str:
                host, port = proxy_str.split(':')
                proxy = ProxyConfig(
                    host=host.strip(),
                    port=int(port.strip()),
                    username=self.username,
                    password=self.password
                )
                proxies.append(proxy)
        
        logger.info(f"Loaded {len(proxies)} proxies from environment variables")
        return proxies


class ProxyManager:
    """Gestiona el pool de proxies con rotación inteligente"""
    
    def __init__(self, provider: BaseProxyProvider):
        self.provider = provider
        self.available_proxies = deque()
        self.blacklist = {}  # {proxy_id: {'until': timestamp, 'reason': str}}
        self.stats = {}  # {proxy_id: {'success': 0, 'failures': 0}}
        self.last_refresh = None
        self.refresh_interval = 3600  # 1 hora
        
        # Configuración
        self.blacklist_duration_rate_limit = 300  # 5 minutos para 429
        self.blacklist_duration_general = 1800  # 30 minutos para fallos generales
        self.max_failures_before_blacklist = 3
        
        # Cargar proxies iniciales
        self._refresh_proxy_list()
    
    def _refresh_proxy_list(self):
        """Actualiza la lista de proxies del provider"""
        logger.info("Refreshing proxy list...")
        
        proxy_list = self.provider.get_proxy_list()
        if not proxy_list:
            logger.error("No proxies available from provider!")
            return
        
        # Limpiar cola actual
        self.available_proxies.clear()
        
        # Agregar todos los proxies que no estén blacklisted
        for proxy in proxy_list:
            if proxy.proxy_id not in self.blacklist:
                self.available_proxies.append(proxy)
        
        self.last_refresh = time.time()
        logger.info(f"Proxy list refreshed. Available: {len(self.available_proxies)}, "
                   f"Blacklisted: {len(self.blacklist)}")
    
    def _clean_expired_blacklist(self):
        """Limpia proxies cuyo blacklist haya expirado"""
        current_time = time.time()
        expired = []
        
        for proxy_id, info in self.blacklist.items():
            if current_time > info['until']:
                expired.append(proxy_id)
        
        for proxy_id in expired:
            logger.info(f"Removing {proxy_id} from blacklist (expired)")
            del self.blacklist[proxy_id]
            # TODO: Re-agregar a available_proxies si tenemos la info del proxy
    
    def get_proxy(self) -> Optional[Tuple[Dict[str, str], str]]:
        """
        Obtiene el siguiente proxy disponible
        Returns: Tupla (proxy_config_dict, proxy_id) o None si no hay disponibles
        """
        # Limpiar blacklist expirada
        self._clean_expired_blacklist()
        
        # Refrescar si es necesario
        if (self.last_refresh is None or 
            time.time() - self.last_refresh > self.refresh_interval or
            len(self.available_proxies) == 0):
            self._refresh_proxy_list()
        
        # Intentar obtener un proxy disponible
        attempts = 0
        while self.available_proxies and attempts < len(self.available_proxies):
            proxy = self.available_proxies.popleft()
            
            # Verificar que no esté blacklisted
            if proxy.proxy_id not in self.blacklist:
                # Mover al final de la cola (LRU)
                self.available_proxies.append(proxy)
                logger.debug(f"Providing proxy: {proxy.proxy_id}")
                return proxy.to_dict(), proxy.proxy_id
            
            attempts += 1
        
        logger.error("No available proxies!")
        return None
    
    def report_success(self, proxy_id: str):
        """Registra un uso exitoso del proxy"""
        if proxy_id not in self.stats:
            self.stats[proxy_id] = {'success': 0, 'failures': 0}
        
        self.stats[proxy_id]['success'] += 1
        logger.debug(f"Proxy {proxy_id} success. Total: {self.stats[proxy_id]['success']}")
    
    def report_failure(self, proxy_id: str, is_rate_limit: bool = False):
        """Registra un fallo del proxy"""
        if proxy_id not in self.stats:
            self.stats[proxy_id] = {'success': 0, 'failures': 0}
        
        self.stats[proxy_id]['failures'] += 1
        failures = self.stats[proxy_id]['failures']
        
        logger.warning(f"Proxy {proxy_id} failed. Total failures: {failures}")
        
        # Decidir si blacklist
        if is_rate_limit:
            # Rate limit = blacklist inmediato por 5 min
            until = time.time() + self.blacklist_duration_rate_limit
            self.blacklist[proxy_id] = {
                'until': until,
                'reason': 'rate_limit',
                'failures': failures
            }
            logger.warning(f"Proxy {proxy_id} blacklisted for {self.blacklist_duration_rate_limit}s (rate limit)")
        elif failures >= self.max_failures_before_blacklist:
            # Demasiados fallos = blacklist por 30 min
            until = time.time() + self.blacklist_duration_general
            self.blacklist[proxy_id] = {
                'until': until,
                'reason': 'max_failures',
                'failures': failures
            }
            logger.warning(f"Proxy {proxy_id} blacklisted for {self.blacklist_duration_general}s (max failures)")
    
    def get_status(self) -> Dict:
        """Obtiene estado actual del manager"""
        return {
            'provider': self.provider.__class__.__name__,
            'total_proxies': len(self.available_proxies) + len(self.blacklist),
            'available': len(self.available_proxies),
            'blacklisted': len(self.blacklist),
            'stats': self.stats,
            'last_refresh': datetime.fromtimestamp(self.last_refresh).isoformat() if self.last_refresh else None
        }