#!/bin/bash

# Script helper para desarrollo con Docker

case "$1" in
    "start")
        echo "🚀 Starting containers..."
        docker compose up -d
        echo "✅ Backend running at http://localhost:8000"
        ;;
    
    "stop")
        echo "🛑 Stopping containers..."
        docker compose down
        ;;
    
    "logs")
        echo "📋 Showing logs (Ctrl+C to exit)..."
        docker compose logs -f
        ;;
    
    "shell")
        echo "🐚 Opening Django shell..."
        docker compose exec web python manage.py shell
        ;;
    
    "test")
        echo "🧪 Running quick API test..."
        docker compose exec web python tests/test_api.py
        ;;
    
    "test-full")
        echo "🧪 Running full integration test..."
        docker compose exec web python tests/nopytest_integ_test.py
        ;;
    
    "pytest")
        echo "🧪 Running pytest..."
        docker compose exec web pytest tests/ "${@:2}"
        ;;
    
    "proxy-health")
        echo "🏥 Running proxy health check (10 proxies)..."
        docker compose exec web python tests/test_proxy_health.py
        ;;
    
    "proxy-health-full")
        echo "🏥 Running FULL proxy health check (25 proxies)..."
        docker compose exec web python tests/test_proxy_health.py --full
        ;;
    
    "proxy-health-custom")
        echo "🏥 Running custom proxy health check..."
        echo "   Sample size: ${2:-10} proxies"
        echo "   Workers: ${3:-5}"
        docker compose exec web python tests/test_proxy_health.py --sample "${2:-10}" --workers "${3:-5}"
        ;;
    
    "test-all")
        echo "🧪 Running ALL tests..."
        echo -e "\n1. Quick test:"
        docker compose exec web python tests/test_api.py
        echo -e "\n2. Integration test:"
        docker compose exec web python tests/nopytest_integ_test.py
        echo -e "\n3. Pytest:"
        docker compose exec web pytest tests/ -v
        ;;
    
    "rebuild")
        echo "🔨 Rebuilding containers..."
        docker compose down
        docker compose build --no-cache
        docker compose up -d
        ;;
    
    "clean")
        echo "🧹 Cleaning everything..."
        docker compose down -v
        ;;
    
    *)
        echo "YouTube Subtitles API - Docker Helper"
        echo ""
        echo "Usage: ./docker-dev.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start      - Start containers"
        echo "  stop       - Stop containers"
        echo "  logs       - Show logs"
        echo "  shell      - Django shell"
        echo "  test       - Run quick test"
        echo "  test-full  - Run integration test"
        echo "  pytest     - Run pytest (can add args)"
        echo "  proxy-health      - Test proxy health (10 proxies)"
        echo "  proxy-health-full - Test proxy health (25 proxies)"
        echo "  proxy-health-custom - Test with custom params"
        echo "  test-all   - Run ALL tests"
        echo "  rebuild    - Rebuild containers"
        echo "  clean      - Remove everything"
        echo ""
        echo "Examples:"
        echo "  ./docker-dev.sh pytest -v"
        echo "  ./docker-dev.sh pytest -k health"
        echo ""
        ;;
esac
