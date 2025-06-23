# Desgrabador

## API de Extracción de Subtítulos

Una API REST robusta construida con Django para extraer subtítulos de videos de YouTube con soporte para proxies y capacidades multi-idioma.

## 🚀 Características

- Extrae subtítulos de cualquier video público de YouTube
- Lista todos los idiomas disponibles para un video
- Soporte para subtítulos manuales y auto-generados
- Soporte integrado para proxies rotativos de Webshare
- Entorno de desarrollo basado en Docker
- Suite completa de pruebas

## 📋 Requisitos

- Docker y Docker Compose
- Python 3.11+ (si se ejecuta localmente)
- Cuenta de Webshare con paquete "Residential" (opcional, para proxies)

## 🛠️ Inicio Rápido

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/chequeado/desgrabador-new-back.git
   cd desgrabador-new-back
   ```

2. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tu configuración
   ```

3. **Iniciar el servidor**
   ```bash
   ./docker-dev.sh start
   ```

   o

   ```bash
   docker compose up --build
   ```

4. **Verificar que esté funcionando**
   ```bash
   curl http://localhost:8000/api/subtitles/health/
   ```

   o

   ```bash
   ./docker-dev.sh test
   ```

## 🔧 Configuración

### Variables de Entorno

| Variable | Descripción | Por defecto | Requerida |
|----------|-------------|-------------|-----------|
| `DEBUG` | Modo debug de Django | `False` | No |
| `SECRET_KEY` | Clave secreta de Django | - | Sí |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos | `localhost` | No |
| `CORS_ALLOWED_ORIGINS` | Orígenes CORS | - | Sí |
| `USE_PROXY` | Habilitar proxies de Webshare | `False` | No |
| `WEBSHARE_PROXY_USERNAME` | Usuario del proxy | - | Si USE_PROXY=True |
| `WEBSHARE_PROXY_PASSWORD` | Contraseña del proxy | - | Si USE_PROXY=True |

### Configuración de Proxies con Webshare

1. **Crear cuenta en Webshare**: https://www.webshare.io

2. **Comprar paquete "Residential"** (NO comprar "Proxy Server" o "Static Residential")

3. **Obtener credenciales**:
   - Ir a Proxy Settings en tu dashboard de Webshare
   - Copiar tu "Proxy Username" y "Proxy Password"

4. **Configurar en .env**:
   ```bash
   USE_PROXY=True
   WEBSHARE_PROXY_USERNAME=tu_usuario_aqui
   WEBSHARE_PROXY_PASSWORD=tu_password_aqui
   ```

Con esta configuración, todos los requests a YouTube se harán automáticamente a través de proxies rotativos residenciales.

## 📡 Endpoints de la API

### Verificación de Estado
```http
GET /api/subtitles/health/
```

**Respuesta:**
```json
{
  "status": "ok",
  "message": "Subtitles API is running"
}
```

### Listar Idiomas Disponibles
```http
POST /api/subtitles/languages/
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Respuesta:**
```json
{
  "video_id": "VIDEO_ID",
  "languages": [
    {
      "code": "es",
      "name": "Spanish",
      "is_generated": false,
      "is_translatable": true
    }
  ],
  "total": 5,
  "proxy_used": false
}
```

### Extraer Subtítulos
```http
POST /api/subtitles/extract/
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "language_code": "es"  // Opcional
}
```

**Respuesta:**
```json
{
  "video_id": "VIDEO_ID",
  "subtitles": [
    {
      "text": "Never gonna give you up",
      "start": 0.0,
      "duration": 2.5
    }
  ],
  "subtitle_count": 150,
  "language_code": "en",
  "total_duration": 300.5,
  "proxy_used": false
}
```

## 📖 Documentación Interactiva
La API incluye documentación interactiva con Swagger UI:

Swagger UI: http://localhost:8000/swagger/

Desde Swagger puedes:
- Ver todos los endpoints disponibles
- Probar las llamadas directamente desde el navegador
- Ver ejemplos de requests y responses
- Descargar la especificación OpenAPI

## 🧪 Pruebas

### Prueba Rápida
```bash
./docker-dev.sh test
```

### Suite Completa de Pruebas
```bash
./docker-dev.sh pytest
```

### Pruebas de Integración
```bash
./docker-dev.sh test-full
```

## 🐳 Comandos Docker

El proyecto incluye un script auxiliar `docker-dev.sh`:

```bash
./docker-dev.sh start    # Iniciar contenedores
./docker-dev.sh stop     # Detener contenedores
./docker-dev.sh logs     # Ver logs
./docker-dev.sh shell    # Shell de Django
./docker-dev.sh rebuild  # Reconstruir contenedores
```

## 🔍 Solución de Problemas

### Problemas Comunes

**Límite de tasa (errores 429)**
- Habilitar soporte de proxy configurando `USE_PROXY=True`
- Asegurarse de tener credenciales válidas de Webshare

**Contenedor no encontrado**
- Asegurarse de que Docker esté ejecutándose
- Ejecutar `./docker-dev.sh start`

**Errores de importación**
- Reconstruir el contenedor: `./docker-dev.sh rebuild`

**Subtítulos no disponibles (aunque existan)**
- Posiblemente baneo de IP de Youtube, usar proxies

## 📞 Soporte

Para problemas y preguntas:
- Abrir un issue en GitHub
- Contactar al equipo de desarrollo