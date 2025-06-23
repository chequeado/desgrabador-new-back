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
        docker compose exec web python tests/test_simple_api.py
        ;;
    
    "test-full")
        echo "🧪 Running full integration test..."
        docker compose exec web python tests/nopytest_integ_test.py
        ;;
    
    "pytest")
        echo "🧪 Running pytest..."
        docker compose exec web pytest tests/ "${@:2}"
        ;;
    
    "stress")
        echo "💪 Running stress test..."
        shift  # Remove 'stress' from arguments
        docker compose exec web python tests/test_stress.py "$@"
        ;;
    
    "stress-quick")
        echo "💪 Running quick stress test (25 requests, 5 workers)..."
        docker compose exec web python tests/test_stress.py --requests 25 --workers 5
        ;;
    
    "stress-heavy")
        echo "💪 Running heavy stress test (200 requests, 30 workers)..."
        docker compose exec web python tests/test_stress.py --requests 200 --workers 30
        ;;
    
    "stress-incremental")
        echo "💪 Running incremental stress test..."
        docker compose exec web python tests/test_stress.py --incremental
        ;;
    
    "test-all")
        echo "🧪 Running ALL tests..."
        echo -e "\n1. Quick test:"
        docker compose exec web python tests/test_simple_api.py
        echo -e "\n2. Integration test:"
        docker compose exec web python tests/nopytest_integ_test.py
        echo -e "\n3. Stress test (quick):"
        docker compose exec web python tests/test_stress.py --requests 10 --workers 3
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
        echo ""
        echo "Stress Testing:"
        echo "  stress              - Run stress test (pass custom args)"
        echo "  stress-quick        - Quick stress test (25 req, 5 workers)"
        echo "  stress-heavy        - Heavy stress test (200 req, 30 workers)"
        echo "  stress-incremental  - Find breaking point incrementally"
        echo ""
        echo "Other:"
        echo "  test-all   - Run ALL tests"
        echo "  rebuild    - Rebuild containers"
        echo "  clean      - Remove everything"
        echo ""
        echo "Examples:"
        echo "  ./docker-dev.sh stress --requests 100 --workers 20"
        echo "  ./docker-dev.sh stress --same-video --workers 50"
        echo "  ./docker-dev.sh stress --incremental"
        echo ""
        ;;
esac