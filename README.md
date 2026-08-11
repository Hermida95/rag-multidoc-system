# RAG Multidoc System

Sistema RAG (Retrieval-Augmented Generation) multidocumento, **preparado para producción**: sube PDFs y Markdown, se indexan de forma asíncrona (extracción → chunking semántico → embeddings) y se consultan mediante un endpoint de chat que devuelve respuestas fundamentadas con citas de fuentes verificables.

[![CI](https://github.com/Hermida95/rag-multidoc-system/actions/workflows/ci.yml/badge.svg)](https://github.com/Hermida95/rag-multidoc-system/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Hermida95/rag-multidoc-system/actions/workflows/codeql.yml/badge.svg)](https://github.com/Hermida95/rag-multidoc-system/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](docker-compose.yml)

## Por qué existe este proyecto

No es un notebook con un `while True` sobre un PDF de ejemplo. Es un intento honesto de construir el mismo tipo de sistema que se pondría en producción: procesamiento desacoplado del ciclo request/response, dominio aislado de frameworks e IA (se puede cambiar de OpenAI a otro proveedor sin tocar un solo caso de uso), autenticación y rate limiting en los endpoints que cuestan dinero real, migraciones versionadas, y un pipeline de CI que corre linting, tipado, tests, escaneo de dependencias y de seguridad en cada push.

## Arquitectura

```mermaid
flowchart LR
    subgraph Client
        U[Usuario / cliente HTTP]
    end

    subgraph API["FastAPI (api/)"]
        UP["POST /documents/upload"]
        Q["POST /chat/query"]
        AUTH["X-API-Key + rate limit"]
    end

    subgraph Async["Celery worker"]
        EXT[Extractor PDF/Markdown]
        CHK[Chunker semántico]
        EMB[Embeddings OpenAI]
    end

    subgraph Data
        PG[(PostgreSQL + pgvector\nHNSW cosine index)]
        FS[(Filesystem\nstorage/uploads)]
    end

    subgraph RAG["Query pipeline"]
        QEMB[Embed pregunta]
        SIM[Similarity search]
        LLM[LLM con contexto citable]
    end

    U -->|1. sube archivo| AUTH --> UP
    UP -->|guarda bytes| FS
    UP -->|202 + document_id| U
    UP -.->|encola tarea| EXT
    EXT --> CHK --> EMB -->|vectores + metadata| PG

    U -->|2. pregunta| AUTH --> Q
    Q --> QEMB --> SIM
    SIM -->|top-k chunks + score| PG
    SIM --> LLM
    LLM -->|respuesta + fuentes [n]| U
```

**Ingesta**: la subida nunca bloquea — el archivo se persiste, se crea el registro `Document` en estado `pending`, y se responde `202 Accepted` de inmediato. Un worker de Celery, completamente desacoplado, ejecuta extracción → chunking → embeddings → indexado, y actualiza el estado (`processing → ready | failed`) con el error real si algo sale mal.

**Consulta**: la pregunta se embebe, se recuperan los `top_k` chunks más similares por distancia coseno en pgvector (índice HNSW), y se construye un prompt con contexto numerado que el LLM debe citar explícitamente — la respuesta nunca se presenta sin fuentes trazables a un `document_id` + `chunk_id` + score de similitud.

## Estructura del repositorio (Clean Architecture)

```
src/app/
├── domain/           # Entidades y contratos (interfaces de repos) — sin dependencias externas
├── application/      # Casos de uso + puertos (embeddings, LLM, extractor, chunker, storage)
├── infrastructure/   # Implementaciones concretas: SQLAlchemy/pgvector, OpenAI, Celery, filesystem
├── api/               # FastAPI: routers, schemas Pydantic, auth, DI
└── container.py      # Composition root: conecta puertos con implementaciones
```

Los casos de uso (`ProcessDocumentUseCase`, `QueryRagUseCase`, `UploadDocumentUseCase`) no importan FastAPI, Celery ni el SDK de OpenAI — solo dependen de interfaces abstractas. Eso es lo que permite testearlos con dobles de prueba en memoria (ver `tests/`), sin levantar Postgres, Redis ni gastar créditos de API.

## Stack técnico

| Capa | Tecnología | Por qué |
|---|---|---|
| API | FastAPI + Pydantic v2 | Tipado estricto, validación automática, OpenAPI gratis |
| Vector store | PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) (HNSW) | Una sola base de datos transaccional + vectorial, más simple de operar que un cluster separado |
| Async | Celery + Redis | Desacopla el pipeline de IA (lento, costoso) del ciclo HTTP |
| IA | OpenAI (embeddings + chat), tras puertos abstractos | Swap de proveedor sin tocar dominio ni casos de uso |
| Migraciones | Alembic | Esquema versionado, reproducible |
| Infra | Docker Compose | `docker compose up` y ya |
| CI/CD | GitHub Actions | Lint, tipado, tests, `pip-audit`, CodeQL, build de imagen en cada push |

## Seguridad

Ver [SECURITY.md](SECURITY.md) para el detalle completo. Resumen:

- Autenticación por `X-API-Key` en los endpoints que disparan llamadas a OpenAI (evita abuso/gasto no autorizado)
- Rate limiting por IP (`slowapi`) en upload y query
- Contenedor Docker corriendo como usuario no-root
- Cabeceras de seguridad (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`)
- CORS deshabilitado por defecto (opt-in explícito)
- Validación estricta de entrada, allow-list de extensiones, límite de tamaño de archivo
- `.env` fuera del repo; solo se versiona `.env.example` sin valores reales
- Dependabot + CodeQL + `pip-audit` corriendo automáticamente

## Requisitos previos

- Docker y Docker Compose
- Una API key de OpenAI (o compatible) para embeddings y generación

## Puesta en marcha local

1. **Clonar y configurar variables de entorno**

```bash
git clone https://github.com/Hermida95/rag-multidoc-system.git
cd rag-multidoc-system
cp .env.example .env
```

Edita `.env`: añade tu `OPENAI_API_KEY` y genera una `API_KEY` propia con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Levantar todos los servicios**

```bash
docker compose up -d --build
```

Esto arranca: `db` (Postgres + pgvector), `redis`, `api` (FastAPI en `:8000`, ejecuta las migraciones de Alembic automáticamente al arrancar) y `worker` (Celery).

3. **Verificar que todo está sano**

```bash
curl http://localhost:8000/api/v1/health/ready
```

4. **Documentación interactiva**

Abre `http://localhost:8000/docs` (Swagger UI) o `http://localhost:8000/redoc`.

## Uso de la API

Todas las peticiones a `/documents/*` y `/chat/*` requieren la cabecera `X-API-Key` (si configuraste `API_KEY` en `.env`, que es lo recomendado fuera de local).

### Subir un documento

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-API-Key: tu-api-key" \
  -F "file=@/ruta/a/tu/documento.pdf"
```

Responde `202 Accepted` de inmediato con el `document_id`; el procesamiento ocurre en background vía Celery.

### Consultar el estado de ingesta

```bash
curl http://localhost:8000/api/v1/documents/{document_id} -H "X-API-Key: tu-api-key"
```

El campo `status` pasa por `pending → processing → ready` (o `failed`, con `error_message`).

### Preguntar al sistema RAG

```bash
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Qué dice el documento sobre X?"}'
```

Respuesta:

```json
{
  "answer": "Según el documento... [1]",
  "sources": [
    {
      "document_id": "...",
      "document_filename": "documento.pdf",
      "chunk_id": "...",
      "chunk_index": 3,
      "similarity_score": 0.87,
      "excerpt": "..."
    }
  ],
  "model": "gpt-4o-mini"
}
```

Puedes limitar la búsqueda a documentos concretos con `document_ids: [...]` y ajustar `top_k`.

## Desarrollo local sin Docker (opcional)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export PYTHONPATH=src

# Necesitas Postgres+pgvector y Redis corriendo en local (o vía `docker compose up db redis`)
alembic upgrade head
uvicorn app.main:app --reload
# En otra terminal:
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

Opcionalmente, instala los hooks de pre-commit (ruff + comprobaciones básicas):

```bash
pip install pre-commit && pre-commit install
```

## Tests y CI

```bash
make test
# o directamente:
pytest -v --cov=app
```

Los tests unitarios cubren el chunker semántico (sin dependencias externas) y los tests de integración ejercitan los casos de uso (`UploadDocumentUseCase`, `QueryRagUseCase`) con dobles de prueba en memoria, sin requerir Postgres/Redis/OpenAI reales.

En cada push a `main` y en cada PR, [GitHub Actions](.github/workflows/ci.yml) ejecuta: `ruff` (lint), `mypy` (tipado), `pytest` (tests + cobertura), `pip-audit` (vulnerabilidades de dependencias), [CodeQL](.github/workflows/codeql.yml) (análisis estático de seguridad) y un build de la imagen Docker. Dependabot mantiene actualizadas las dependencias de `pip`, Docker y GitHub Actions.

## Decisiones de diseño

- **Chunking semántico**: en lugar de un split fijo por caracteres, se usa un splitter recursivo consciente de estructura (encabezados Markdown → párrafos → líneas → frases → palabras) que solo baja de nivel cuando un segmento no cabe en el presupuesto de tokens (medido con `tiktoken`, el tokenizador real del modelo), preservando la coherencia semántica de cada chunk. Se aplica solapamiento configurable entre chunks consecutivos para mantener continuidad de contexto en la recuperación.
- **pgvector sobre Qdrant**: mantiene la infraestructura a una sola base de datos (transaccional + vectorial), suficiente para el volumen de un portfolio y más simple de operar.
- **Procesamiento asíncrono obligatorio**: la subida de archivos nunca bloquea al cliente; Celery desacopla el pipeline de IA (potencialmente lento) del ciclo de petición/respuesta HTTP.
- **Puertos y adaptadores**: `EmbeddingProvider`, `LLMProvider`, `TextExtractor`, `Chunker`, `VectorStore` y `FileStorage` son interfaces abstractas; las implementaciones OpenAI/pgvector/filesystem viven en `infrastructure/` y se conectan en `container.py`, de modo que cambiar de proveedor de IA o de almacenamiento no toca el dominio ni los casos de uso.

## Posibles extensiones

Fuera de alcance para un proyecto de portfolio, pero es donde iría a continuación en un entorno real: almacenamiento de archivos en S3/GCS en vez de disco local, autenticación por usuario (JWT/OAuth) en vez de una única API key compartida, streaming de la respuesta del LLM (SSE), soporte de re-ranking tras la búsqueda vectorial, y observabilidad con OpenTelemetry.

## Licencia

[MIT](LICENSE)
