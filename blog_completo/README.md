# ∇eupraxia

Blog tecnico simples com FastAPI, SQLite e HTMX.

## Rodar localmente

```bash
cd blog_completo
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Login admin

- usuario padrao: `admin`
- senha padrao: `admin`

Opcionalmente:

```bash
export EUPRAXIA_ADMIN_USER=admin
export EUPRAXIA_ADMIN_PASS=admin
```
