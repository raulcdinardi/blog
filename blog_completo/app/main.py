from contextlib import asynccontextmanager
from datetime import date
import os
import secrets

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Boolean, ForeignKey, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

engine = create_engine("sqlite:///./blog_completo.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
templates = Jinja2Templates(directory="app/templates")
PAGE_SIZE = 4
security = HTTPBasic()
ADMIN_USER = os.getenv("EUPRAXIA_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("EUPRAXIA_ADMIN_PASS", "admin")


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(String(180))
    posts: Mapped[list["Post"]] = relationship(back_populates="category")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    excerpt: Mapped[str] = mapped_column(String(220))
    content: Mapped[str] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[str | None] = mapped_column(String(10))
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category: Mapped["Category"] = relationship(back_populates="posts")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if not (
        secrets.compare_digest(credentials.username, ADMIN_USER)
        and secrets.compare_digest(credentials.password, ADMIN_PASS)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


def seed():
    with engine.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(posts)").fetchall()}
        if "pdf_path" not in cols:
            conn.exec_driver_sql("ALTER TABLE posts ADD COLUMN pdf_path VARCHAR(255)")
        if "created_at" not in cols:
            conn.exec_driver_sql("ALTER TABLE posts ADD COLUMN created_at VARCHAR(10)")

    db = SessionLocal()
    category = db.scalar(select(Category).where(Category.name == "Artigos"))
    if category is None:
        category = Category(name="Artigos", description="Categoria interna")
        db.add(category)
        db.flush()
    if db.scalar(select(Post.id).limit(1)) is not None:
        db.close()
        return

    for i in range(1, 201):
        db.add(
            Post(
                title=f"post #{i}",
                excerpt=f"resumo do post #{i}",
                content=f"conteudo do post #{i}",
                published=True,
                created_at="2026-04-09",
                category_id=category.id,
            )
        )

    db.add(
        Post(
            title="Debate Proposal",
            excerpt="Documento PDF adicionado como post do blog.",
            content="Voce pode visualizar o documento abaixo ou abrir em outra aba.",
            pdf_path="pdfs/debate_proposal.pdf",
            published=True,
            created_at="2026-04-10",
            category_id=category.id,
        )
    )
    db.add(
        Post(
            title="Apart AI Control 2026",
            excerpt="Documento PDF adicionado como post do blog.",
            content="Voce pode visualizar o documento abaixo ou abrir em outra aba.",
            pdf_path="pdfs/apart_ai_control_2026.pdf",
            published=True,
            created_at="2026-04-10",
            category_id=category.id,
        )
    )

    db.commit()
    db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"page_title": "∇eupraxia"})


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, _: HTTPBasicCredentials = Depends(require_admin), db: Session = Depends(get_db)):
    posts = db.scalars(select(Post).order_by(Post.id.desc())).all()
    return templates.TemplateResponse(request=request, name="admin.html", context={"page_title": "∇eupraxia Admin", "posts": posts})


@app.get("/posts", response_class=HTMLResponse)
def list_posts(request: Request, page: int = 1, db: Session = Depends(get_db)):
    where = [Post.published.is_(True)]
    total = db.scalar(select(func.count(Post.id)).where(*where)) or 0
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, pages))
    posts = db.scalars(
        select(Post).where(*where).order_by(Post.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="partials/post_list.html",
        context={"posts": posts, "page": page, "pages": pages, "total": total},
    )


@app.get("/posts/{post_id}", response_class=HTMLResponse)
def show_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if post is None or not post.published:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request=request, name="post_detail.html", context={"page_title": post.title, "post": post})


@app.post("/posts", response_class=HTMLResponse)
def create_post(
    request: Request,
    title: str = Form(...),
    excerpt: str = Form(...),
    content: str = Form(...),
    pdf_path: str = Form(""),
    published: bool = Form(False),
    _: HTTPBasicCredentials = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not title.strip() or not excerpt.strip() or not content.strip():
        posts = db.scalars(select(Post).order_by(Post.id.desc())).all()
        return templates.TemplateResponse(
            request=request,
            name="partials/post_form_result.html",
            context={"message": "Preencha todos os campos.", "success": False, "posts": posts},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    category = db.scalar(select(Category).where(Category.name == "Artigos"))
    if category is None:
        category = Category(name="Artigos", description="Categoria interna")
        db.add(category)
        db.flush()
    db.add(
        Post(
            title=title.strip(),
            excerpt=excerpt.strip(),
            content=content.strip(),
            pdf_path=pdf_path.strip() or None,
            published=published,
            created_at=date.today().isoformat(),
            category_id=category.id,
        )
    )
    db.commit()
    posts = db.scalars(select(Post).order_by(Post.id.desc())).all()
    return templates.TemplateResponse(
        request=request,
        name="partials/post_form_result.html",
        context={"message": "Post salvo.", "success": True, "posts": posts},
    )


@app.put("/posts/{post_id}", response_class=HTMLResponse)
def update_post(
    post_id: int,
    request: Request,
    title: str = Form(...),
    excerpt: str = Form(...),
    content: str = Form(...),
    pdf_path: str = Form(""),
    published: bool = Form(False),
    _: HTTPBasicCredentials = Depends(require_admin),
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)
    if post is None:
        return templates.TemplateResponse(
            request=request,
            name="partials/message.html",
            context={"message": "Post nao encontrado.", "success": False},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    post.title = title.strip()
    post.excerpt = excerpt.strip()
    post.content = content.strip()
    post.pdf_path = pdf_path.strip() or None
    post.published = published
    db.commit()
    return templates.TemplateResponse(request=request, name="partials/admin_post.html", context={"post": post})


@app.delete("/posts/{post_id}")
def delete_post(post_id: int, _: HTTPBasicCredentials = Depends(require_admin), db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if post:
        db.delete(post)
        db.commit()
    return Response(status_code=200)
