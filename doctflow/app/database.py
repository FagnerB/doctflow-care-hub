from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = metadata


def _connect_args(database_url: str) -> dict[str, object]:
    """Desliga prepared statements do asyncpg quando o alvo é um PgBouncer em
    modo transaction (caso do Transaction Pooler do Supabase, porta 6543).

    Sem isso, a segunda query na mesma conexão lógica falha com
    `DuplicatePreparedStatementError`: o PgBouncer troca a conexão física por
    trás dos panos entre transações, e o cache de prepared statements do
    asyncpg (por conexão) fica referenciando um statement que já não existe
    (ou colide com outro) na conexão física seguinte.
    """
    url = make_url(database_url)
    if url.get_backend_name() == "postgresql" and url.get_driver_name() == "asyncpg":
        return {"statement_cache_size": 0}
    return {}


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    connect_args=_connect_args(settings.database_url),
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
