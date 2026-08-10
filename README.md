# RAG Multidoc System

Sistema RAG (Retrieval-Augmented Generation) multidocumento, listo para producción: sube PDFs y Markdown, se indexan de forma asíncrona (extracción → chunking semántico → embeddings) y se consultan mediante un endpoint de chat que devuelve respuestas fundamentadas con citas de fuentes.

## Stack

- **API**: FastAPI + Pydantic v2, tipado estricto
- **Base de datos vectorial**: PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) (índice HNSW, distancia coseno)
- **Procesamiento asíncrono**: Celery + Redis (broker/result backend)
- **IA**: OpenAI (embeddings + chat completions), abstraído tras puertos (`EmbeddingProvider`, `LLMProvider`) para poder cambiar de proveedor sin tocar el dominio
- **Arquitectura**: Clean Architecture (`domain` → `application` → `infrastructure` → `api`), inyección de dependencias explícita vía `container.py`
- **Infraestructura**: Docker + Docker Compose

## Arquitectura del repositorio

```
src/app/
├── domain/           # Entidades y contratos (interfaces de repos), sin dependencias externas
├── application/       # Casos de uso + puertos (embeddings, LLM, extractor, chunker)
├── infrastructure/    # Implementaciones concretas: SQLAlchemy/pgvector, OpenAI, Celery, filesystem
├── api/                # FastAPI: routers, schemas Pydantic, DI
└── container.py       # Composition root: conecta puertos con implementaciones
```

El pipeline de ingesta (`ProcessDocumentUseCase`) y el pipeline de consulta (`QueryRagUseCase`) no conocen FastAPI, Celery ni OpenAI directamente — solo dependen de interfaces abstractas, lo que permite testear la lógica de negocio con dobles de prueba (ver `tests/`).

## Requisitos previos

- Docker y Docker Compose
- Una API key de OpenAI (o compatible) para embeddings y generación

## Puesta en marcha local

1. **Clonar y configurar variables de entorno**

```bash
git clone <tu-fork-o-repo> rag-multidoc-system
cd rag-multidoc-system
cp .env.example .env
```

Edita `.env` y añade al menos tu `OPENAI_API_KEY`. Los valores por defecto ya están preparados para funcionar con Docker Compose (host `db`/`redis`).

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

### Subir un documento

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/ruta/a/tu/documento.pdf"
```

Responde `202 Accepted` de inmediato con el `document_id`; el procesamiento (extracción, chunking, embeddings) ocurre en background vía Celery.

### Consultar el estado de ingesta

```bash
curl http://localhost:8000/api/v1/documents/{document_id}
```

El campo `status` pasa por `pending → processing → ready` (o `failed`, con `error_message`).

### Preguntar al sistema RAG

```bash
curl -X POST http://localhost:8000/api/v1/chat/query \
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

## Tests

```bash
make test
# o directamente:
pytest -v
```

Los tests unitarios cubren el chunker semántico (sin dependencias externas) y los tests de integración ejercitan los casos de uso (`UploadDocumentUseCase`, `QueryRagUseCase`) con dobles de prueba en memoria, sin requerir Postgres/Redis/OpenAI reales.

## Decisiones de diseño

- **Chunking semántico**: en lugar de un split fijo por caracteres, se usa un splitter recursivo consciente de estructura (encabezados Markdown → párrafos → líneas → frases → palabras) que solo baja de nivel cuando un segmento no cabe en el presupuesto de tokens (medido con `tiktoken`, el tokenizador real del modelo), preservando la coherencia semántica de cada chunk. Se aplica solapamiento configurable entre chunks consecutivos para mantener continuidad de contexto en la recuperación.
- **pgvector sobre Qdrant**: mantiene la infraestructura a una sola base de datos (transaccional + vectorial), suficiente para el volumen de un portfolio y más simple de operar.
- **Procesamiento asíncrono obligatorio**: la subida de archivos nunca bloquea al cliente; Celery desacopla el pipeline de IA (potencialmente lento) del ciclo de petición/respuesta HTTP.
- **Puertos y adaptadores**: `EmbeddingProvider`, `LLMProvider`, `TextExtractor`, `Chunker`, `VectorStore` y `FileStorage` son interfaces abstractas; las implementaciones OpenAI/pgvector/filesystem viven en `infrastructure/` y se conectan en `container.py`, de modo que cambiar de proveedor de IA o de almacenamiento no toca el dominio ni los casos de uso.
