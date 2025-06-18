"""
Tests profesionales con pytest
"""
import pytest
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000/api/subtitles"
TEST_VIDEO = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(scope="session")
def api_url():
    """URL base de la API"""
    return BASE_URL


@pytest.fixture(scope="session")
def session():
    """Session HTTP reutilizable"""
    with requests.Session() as s:
        yield s


class TestHealthEndpoint:
    """Tests para el endpoint de health"""
    
    def test_health_check_returns_200(self, session, api_url):
        """Health check debe retornar 200"""
        response = session.get(f"{api_url}/health/")
        assert response.status_code == 200
    
    def test_health_check_response_format(self, session, api_url):
        """Health check debe tener formato correcto"""
        response = session.get(f"{api_url}/health/")
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


class TestLanguagesEndpoint:
    """Tests para el endpoint de idiomas"""
    
    def test_languages_with_valid_url(self, session, api_url):
        """Debe retornar lista de idiomas para URL válida"""
        response = session.post(
            f"{api_url}/languages/",
            json={"url": TEST_VIDEO}
        )
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert "total" in data
        assert isinstance(data["languages"], list)
        assert data["total"] > 0
    
    def test_languages_with_invalid_url(self, session, api_url):
        """Debe retornar error para URL inválida"""
        response = session.post(
            f"{api_url}/languages/",
            json={"url": "not-a-youtube-url"}
        )
        assert response.status_code == 400
        assert "error" in response.json()
    
    def test_languages_without_url(self, session, api_url):
        """Debe retornar error sin URL"""
        response = session.post(f"{api_url}/languages/", json={})
        assert response.status_code == 400
    
    @pytest.mark.parametrize("url", [
        "",
        None,
        "https://www.youtube.com/watch?v=invalid",
        "https://youtube.com/",
    ])
    def test_languages_with_various_invalid_urls(self, session, api_url, url):
        """Prueba múltiples URLs inválidas"""
        response = session.post(
            f"{api_url}/languages/",
            json={"url": url}
        )
        assert response.status_code == 400


class TestSubtitlesEndpoint:
    """Tests para el endpoint de subtítulos"""
    
    def test_subtitles_default_language(self, session, api_url):
        """Debe obtener subtítulos en idioma por defecto"""
        response = session.post(
            f"{api_url}/extract/",
            json={"url": TEST_VIDEO}
        )
        assert response.status_code == 200
        data = response.json()
        assert "subtitles" in data
        assert "subtitle_count" in data
        assert isinstance(data["subtitles"], list)
        assert len(data["subtitles"]) > 0
    
    def test_subtitles_specific_language(self, session, api_url):
        """Debe obtener subtítulos en idioma específico"""
        response = session.post(
            f"{api_url}/extract/",
            json={"url": TEST_VIDEO, "language_code": "en"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("language_code") == "en"
    
    def test_subtitles_invalid_language(self, session, api_url):
        """Debe manejar idioma no disponible"""
        response = session.post(
            f"{api_url}/extract/",
            json={"url": TEST_VIDEO, "language_code": "xx"}
        )
        assert response.status_code == 400
        assert "error" in response.json()
    
    def test_subtitle_content_structure(self, session, api_url):
        """Verifica estructura de los subtítulos"""
        response = session.post(
            f"{api_url}/extract/",
            json={"url": TEST_VIDEO}
        )
        data = response.json()
        first_subtitle = data["subtitles"][0]
        
        assert "text" in first_subtitle
        assert "start" in first_subtitle
        assert "duration" in first_subtitle
        assert isinstance(first_subtitle["text"], str)
        assert isinstance(first_subtitle["start"], (int, float))


class TestProxyConfiguration:
    """Tests relacionados con configuración de proxy"""
    
    @pytest.mark.skipif(
        os.getenv("USE_PROXY") != "True",
        reason="Proxies disabled"
    )
    def test_proxy_usage_when_enabled(self, session, api_url):
        """Verifica que se usen proxies cuando están habilitados"""
        response = session.post(
            f"{api_url}/extract/",
            json={"url": TEST_VIDEO}
        )
        data = response.json()
        if "error" not in data:
            assert data.get("proxy_used") == True
    
    @pytest.mark.skipif(
        os.getenv("USE_PROXY") == "True",
        reason="Proxies enabled"
    )
    def test_no_proxy_when_disabled(self, session, api_url):
        """Verifica que NO se usen proxies cuando están deshabilitados"""
        response = session.post(
            f"{api_url}/extract/",
            json={"url": TEST_VIDEO}
        )
        data = response.json()
        if "error" not in data:
            assert data.get("proxy_used") == False

'''
@pytest.mark.performance
class TestPerformance:
    """Tests de rendimiento"""
    
    def test_response_time_languages(self, session, api_url):
        """El endpoint de idiomas debe responder en menos de 10s"""
        import time
        start = time.time()
        response = session.post(
            f"{api_url}/languages/",
            json={"url": TEST_VIDEO}
        )
        elapsed = time.time() - start
        assert elapsed < 10
        assert response.status_code == 200
    
    def test_response_time_subtitles(self, session, api_url):
        """El endpoint de subtítulos debe responder en menos de 15s"""
        import time
        start = time.time()
        response = session.post(
            f"{api_url}/extract/",
            json={"url": TEST_VIDEO}
        )
        elapsed = time.time() - start
        assert elapsed < 15
'''

if __name__ == "__main__":
    pytest.main([__file__, "-v"])