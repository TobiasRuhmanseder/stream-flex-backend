
# Streamflex Backend 🎬
<br>
Django + DRF mit Postgres, Redis und Caddy.  
Dev und Prod laufen per Docker Compose.

![Python](https://img.shields.io/badge/python-3.12-blue)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Docker](https://img.shields.io/badge/docker-ready-blue)

---

## Table of Contents
- [Voraussetzungen](#voraussetzungen)
- [Projekt klonen](#projekt-klonen)
- [.env anlegen](#env-anlegen)
- [Settings](#settings)
  - [Dev](#dev)
  - [Prod](#Prod)
- [Docker Start](#docker-start)
  - [Dev – ohne Caddy](#dev--ohne-caddy)
  - [Prod – mit Caddy + SSL](#prod--mit-caddy--ssl)
- [CSRF & CORS](#csrf--cors)
- [Testing](#testing)
- [Nützliche Admin-Kommandos](#nützliche-admin-kommandos)
- [Troubleshooting](#troubleshooting)

---

## Voraussetzungen

- Docker & Docker Compose<br>
- Git

---

## Projekt klonen
<br>

```bash
git clone git@github.com:TobiasRuhmanseder/stream-flex-backend.git
cd stream-flex-backend
```
<br>

---

## .env anlegen
<br>

Beispiel .env (im Repo-Root):
```python
SECRET_KEY=change-me
DEBUG=False

ALLOWED_HOSTS=localhost,127.0.0.1,api.streamflex.domain.de,streamflex.domain.de
FRONTEND_URL=https://streamflex.domain.de

CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://localhost:4200,https://api.domain.de,https://streamflex.domain.de

DB_NAME=db
DB_USER=admin
DB_PASSWORD=adminpassword
DB_HOST=db
DB_PORT=5432

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

<br>

---

## Settings


### Dev
<br>

```python
DEBUG = True
CSRF_COOKIE_SAMESITE = "lax"
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "lax"
SESSION_COOKIE_SECURE = False

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:4200",
]
```

<br>


### Prod
<br>

```python
DEBUG = False
CSRF_COOKIE_SAMESITE = "none"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "none"
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_DOMAIN = ".tobias-ruhmanseder.de"

CSRF_TRUSTED_ORIGINS = [
    "https://api.domain.de",
    "https://streamflex.domain.de",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

<br>

---

## Docker Start


### Dev - ohne Caddy
<br>

```bash
docker compose -f docker-compose__prod.yml up -d
docker compose -f docker-compose__prod.yml exec web python manage.py migrate
```

-	API: http://localhost:8000<br>
-	Admin: http://localhost:8000/admin

 ### Prod - mit Caddy + SSL
<br>

```bash
docker compose -f docker-compose.yml up -d --build
```
- API: https://api.streamflex.domain.de<br>
- Frontend: https://streamflex.domain.de

<br>

---

## CSRF & CORS


| Umgebung | Domain-Situation | Settings |
|----------|------------------|----------|
| Dev      | localhost        | `SAMESITE=lax`, `SECURE=False` |
| Prod     | Subdomains       | `SAMESITE=none`, `SECURE=True`, `CSRF_COOKIE_DOMAIN=.domain.de` |

<b> ACHTUNG! Der Punkt vor der Domain ist für Django ganz wichtig!<b>

Frontend muss bei <b>POST/PUT/DELETE:<b> <br>

	- withCredentials: true setzen <br>
 	- X-CSRFToken-Header mitsenden

<br>

---

### Testing


```bash
pytest 
```

(siehe pytest.ini)

<br>

## Troubleshooting


### 403 CSRF Failed (Prod):

- CSRF_COOKIE_DOMAIN = ".max-mustermann.de" <br>
- SAMESITE="none", SECURE=True <br>
- Trusted Origins setzen <br>
- Client: X-CSRFToken + withCredentials <br>

 ### 502 (Caddy):
 
- Läuft web auf Port 8000?<br>
- reverse_proxy web:8000 korrekt?<br>

---
 











