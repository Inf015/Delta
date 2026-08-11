# Delta

Plataforma de análisis de telemetría para sim racing. Convierte los datos crudos de una
sesión en respuestas concretas: **dónde se pierde tiempo y qué ajuste de setup lo recupera**.

En una vuelta rápida el margen está en las décimas, y esas décimas siempre salen de un dato:
frenada, trazada, tracción a la salida, reparto de frenos. Delta ingiere la telemetría
exportada del simulador, la cruza con el setup del auto y produce un informe accionable en
lugar de un gráfico que hay que interpretar a ojo.

Simuladores soportados: **Assetto Corsa**, **Assetto Corsa Competizione**, **iRacing**,
**Le Mans Ultimate** y **RaceRoom**.

---

## Qué hace

- **Ingesta de sesiones** — carga de archivos de telemetría y de setup, con parsers propios
  para cada formato.
- **Normalización de pistas** — los simuladores nombran los circuitos de forma distinta;
  Delta los unifica contra una base de datos interna de pistas.
- **Análisis de sesión** — comparación entre vueltas, detección de dónde se pierde tiempo
  y generación de un informe por sesión.
- **Interpretación asistida por IA** — la API de Anthropic traduce los números a
  recomendaciones legibles, apoyada en una base de conocimiento del dominio.
- **Trabajo en equipo** — cuentas de usuario con roles diferenciados de piloto, técnico y
  administrador, para que un ingeniero de pista pueda revisar las sesiones del piloto.
- **Procesamiento asíncrono** — los análisis pesados corren en workers de Celery, así que
  la carga de un archivo grande no bloquea la interfaz.

## Arquitectura

```
backend/     API en FastAPI + SQLAlchemy, migraciones con Alembic
  app/api/         auth · upload · sessions · racing_sessions · analysis · teams · billing · admin
  app/services/    parsers · analysis · tracks · knowledge · ai · reports · storage
  app/tasks/       tareas asíncronas de Celery
  tests/           100 pruebas con pytest
frontend/    Next.js + Tailwind (carga, sesiones, comparación, panel técnico y admin)
nginx/       proxy inverso
```

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · Celery · Redis · pandas · numpy ·
API de Anthropic · Next.js · TypeScript · Tailwind · Docker Compose · nginx

## Calidad

El motor de análisis está respaldado por **100 pruebas automatizadas en pytest**, concentradas
donde un error pasaría inadvertido y corrompería el resultado sin fallar de forma visible:

| Suite | Cubre |
| --- | --- |
| `test_csv_parser` | lectura de telemetría cruda |
| `test_setup_parser` | interpretación de archivos de setup |
| `test_track_normalizer` | equivalencia de nombres de pista entre simuladores |
| `test_pre_analysis` | preparación de datos previa al análisis |
| `test_session_report` | generación del informe de sesión |
| `test_kb_service` | base de conocimiento del dominio |

```bash
docker compose exec api pytest
```

## Puesta en marcha

Requiere Docker y Docker Compose.

```bash
git clone https://github.com/Inf015/Delta.git
cd Delta
cp .env.example .env      # completar las variables antes de levantar
make up                   # docker compose up -d
make logs                 # seguir los logs
```

La API queda en `http://localhost:8000` y el frontend en `http://localhost:3000`.

| Comando | Acción |
| --- | --- |
| `make up` | levanta todos los servicios |
| `make down` | los detiene |
| `make build` | reconstruye las imágenes |
| `make logs` | logs de todos los servicios |
| `make logs-api` | solo la API |
| `make logs-worker` | solo el worker de Celery |

## Estado

En desarrollo activo. El núcleo —ingesta, parsers, análisis de sesión y comparación de
vueltas— está funcionando; el trabajo actual se concentra en ampliar la cobertura de
formatos y afinar las recomendaciones de setup.

## Autor

**Oliver Infante** — Ingeniero QA y desarrollador. Sim racing y drag racing con telemetría
real; Delta nació de querer aplicar a la pista virtual el mismo método de medición que uso
en el cuarto de milla.

[GitHub](https://github.com/Inf015) · [LinkedIn](https://linkedin.com/in/oliver-infante-perez-068226219)
