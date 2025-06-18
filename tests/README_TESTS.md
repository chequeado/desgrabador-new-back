# 🧪 Guía de Tests

## Estructura
```
desgrabador-new-back/
├── docker-dev.sh
├── tests/
│   ├── test_api.py          # Test rápido
│   ├── test_integral.py     # Test completo
│   ├── test_api_pytest.py   # Tests profesionales
│   └── pytest.ini           # Config de pytest
└── ...
```

## Prerequisitos
```bash
# Reconstruir imagen con las nuevas dependencias
docker compose build
```

## Tests Disponibles

### 1. **Test Rápido** (`tests/test_api.py`)
**Cuándo usar**: Para verificar que la API funciona básicamente

```bash
# Ejecutar
docker compose exec web python tests/test_api.py
```

### 2. **Test Integral** (`tests/test_integral.py`) 
**Cuándo usar**: Para un chequeo completo del sistema + ver configuración

```bash
# Ejecutar
docker compose exec web python tests/test_integral.py
```

### 3. **Tests Profesionales** (`tests/test_api_pytest.py`)
**Cuándo usar**: Para desarrollo, antes de hacer commit, CI/CD

```bash
# Todos los tests
docker compose exec web pytest tests/

# Con detalles
docker compose exec web pytest tests/ -v

# Solo tests rápidos (sin performance)
docker compose exec web pytest tests/ -m "not performance"

# Con coverage
docker compose exec web pytest tests/ --cov=subtitles

# Un test específico
docker compose exec web pytest tests/ -k "test_health"
```

## Workflow Típico

### Durante desarrollo:
```bash
# 1. Hacer cambios en el código
# 2. Test rápido
docker compose exec web python test_api.py

# 3. Si todo OK, test completo
docker compose exec web pytest
```

### Antes de hacer push:
```bash
# Test integral + pytest
docker compose exec web python test_integral.py
docker compose exec web pytest -v
```

### Si algo falla:
```bash
# Ver logs del servidor
docker compose logs

# Reiniciar todo
docker compose restart

# O reconstruir
docker compose down
docker compose up --build
```

## Tips

- **Sin Docker corriendo?** Primero: `docker compose up -d`
- **Tests lentos?** Normal con proxies activados
- **Error "container not found"?** El servidor no está corriendo
- **pytest no encontrado?** Ejecuta `docker compose build` primero