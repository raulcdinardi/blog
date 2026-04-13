# Blog Completo

Versao pronta para demonstracao e entrega curta de disciplina.

## O que entrega

- 2 telas: `/` e `/admin`
- FastAPI no back-end
- 2 modelos no banco: `Category` e `Post`
- relacao one-to-many
- CRUD HTMX completo:
  - `hx-post` para categorias e posts
  - `hx-get` para busca e paginacao
  - `hx-put` para editar posts
  - `hx-delete` para excluir posts

## Como rodar

```bash
cd blog_completo
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Observacao

Ao subir pela primeira vez, o app cria algumas categorias e posts de exemplo em `blog_completo.db`.
