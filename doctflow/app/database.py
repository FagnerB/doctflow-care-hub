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


def _is_asyncpg(database_url: str) -> bool:
    url = make_url(database_url)
    return url.get_backend_name() == "postgresql" and url.get_driver_name() == "asyncpg"


def _connect_args(database_url: str) -> dict[str, object]:
    """Desliga prepared statements do asyncpg quando o alvo é um PgBouncer em
    modo transaction (caso do Transaction Pooler do Supabase, porta 6543).

    Sem isso, a segunda query na mesma conexão lógica falha com
    `DuplicatePreparedStatementError`: o PgBouncer troca a conexão física por
    trás dos panos entre transações, e o cache de prepared statements do
    asyncpg (por conexão) fica referenciando um statement que já não existe
    (ou colide com outro) na conexão física seguinte.

    `timeout` maior porque o backend (Railway, US) e o Postgres (Supabase,
    sa-east-1) ficam em continentes diferentes — o handshake TCP+TLS+auth
    sozinho já consome boa parte do timeout padrão de 60s do asyncpg sob
    latência alta; folga extra evita timeout prematuro numa conexão que só
    está lenta, não morta.
    """
    if not _is_asyncpg(database_url):
        return {}
    return {"statement_cache_size": 0, "timeout": 30, "command_timeout": 30}


def _engine_kwargs(database_url: str) -> dict[str, object]:
    """Pool pequeno e reaproveitável, não NullPool.

    NullPool parecia a escolha "correta" contra um pooler externo (evita
    duplicar pooling), mas nessa distância Railway↔Supabase o handshake de
    conexão nova é a parte mais frágil — NullPool paga esse custo em TODA
    requisição. Testado: 8/8 sucesso chamando o serviço direto (uma conexão
    de cada vez, sem HTTP no meio) contra ~20% de sucesso passando pelo
    endpoint real. Um pool pequeno mantém poucas conexões já autenticadas
    vivas entre requisições, pagando o handshake caro raramente em vez de
    sempre. `pool_pre_ping` descarta uma conexão morta do pool antes de
    usá-la, em vez de tentar uma query nela e falhar.
    """
    if _is_asyncpg(database_url):
        return {"pool_size": 3, "max_overflow": 2, "pool_pre_ping": True, "pool_recycle": 300}
    return {"pool_pre_ping": True}


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=_connect_args(settings.database_url),
    **_engine_kwargs(settings.database_url),
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
