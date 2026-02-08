import os
import hashlib
import secrets
from datetime import datetime, date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ═══════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith('postgresql'))

DB_PATH = os.environ.get(
    'OVOS_DB_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ovos.db')
)

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor


# ═══════════════════════════════════════════
# WRAPPER  PostgreSQL → interface sqlite3
# ═══════════════════════════════════════════

class PgCursorWrapper:
    """Adapta cursor psycopg2 para comportar-se como sqlite3.Cursor."""

    def __init__(self, cursor):
        self._cursor = cursor
        self._lastrowid = None

    # ── propriedades ──

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    # ── execução ──

    def execute(self, sql, params=None):
        sql = sql.replace('?', '%s')

        is_insert = sql.strip().upper().startswith('INSERT')
        if is_insert and 'RETURNING' not in sql.upper():
            sql = sql.rstrip().rstrip(';') + ' RETURNING id'

        if params:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)

        if is_insert:
            try:
                row = self._cursor.fetchone()
                if row and 'id' in row:
                    self._lastrowid = row['id']
            except Exception:
                pass

        return self

    def executescript(self, sql):
        """Executa múltiplos statements (compatibilidade com sqlite3)."""
        self._cursor.execute(sql)
        return self

    # ── leitura ──

    def fetchone(self):
        try:
            row = self._cursor.fetchone()
            return self._convert_row(row)
        except Exception:
            return None

    def fetchall(self):
        try:
            rows = self._cursor.fetchall()
            return [self._convert_row(r) for r in rows]
        except Exception:
            return []

    # ── helpers ──

    @staticmethod
    def _convert_row(row):
        """Converte tipos PG (datetime → str) para manter compatibilidade."""
        if row is None:
            return None
        converted = {}
        for key, value in row.items():
            if isinstance(value, (datetime, date)):
                # Adicionar 'Z' se for datetime naive (assumir UTC)
                iso = value.isoformat()
                if isinstance(value, datetime) and value.tzinfo is None and 'T' in iso:
                    iso = iso + 'Z'
                converted[key] = iso
            else:
                converted[key] = value
        return converted


class PgConnectionWrapper:
    """Adapta conexão psycopg2 para interface sqlite3.Connection."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PgCursorWrapper(self._conn.cursor(cursor_factory=RealDictCursor))

    def execute(self, sql, params=None):
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


# ═══════════════════════════════════════════
# CONEXÃO
# ═══════════════════════════════════════════

def get_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return PgConnectionWrapper(conn)
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn


# ═══════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════

_SQLITE_SCHEMA = '''
    -- SQLite: DATETIME armazena como texto, sempre tratado como UTC quando convertido
    CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quantidade_total INTEGER NOT NULL DEFAULT 0,
        ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS entradas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        observacao TEXT DEFAULT '',
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS saidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        preco_unitario REAL NOT NULL CHECK(preco_unitario >= 0),
        valor_total REAL NOT NULL CHECK(valor_total >= 0),
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS precos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        preco_unitario REAL NOT NULL CHECK(preco_unitario >= 0),
        data_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
        ativo BOOLEAN NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS quebrados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        motivo TEXT DEFAULT '',
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS consumo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        observacao TEXT DEFAULT '',
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        valor REAL NOT NULL CHECK(valor > 0),
        descricao TEXT NOT NULL DEFAULT '',
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS resumo_mensal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mes_referencia TEXT NOT NULL UNIQUE,
        total_entradas INTEGER NOT NULL DEFAULT 0,
        total_saidas INTEGER NOT NULL DEFAULT 0,
        total_quebrados INTEGER NOT NULL DEFAULT 0,
        faturamento_total REAL NOT NULL DEFAULT 0.0,
        total_despesas REAL NOT NULL DEFAULT 0.0,
        lucro_estimado REAL NOT NULL DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        nome TEXT NOT NULL DEFAULT '',
        is_admin INTEGER NOT NULL DEFAULT 0,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        ultimo_login DATETIME
    );

    CREATE TABLE IF NOT EXISTS sessoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        expira_em DATETIME NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );

    CREATE TABLE IF NOT EXISTS configuracoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chave TEXT NOT NULL UNIQUE,
        valor TEXT NOT NULL,
        atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
    );
'''

_POSTGRES_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS estoque (
        id SERIAL PRIMARY KEY,
        quantidade_total INTEGER NOT NULL DEFAULT 0,
        ultima_atualizacao TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS entradas (
        id SERIAL PRIMARY KEY,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        data TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        observacao TEXT DEFAULT '',
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS saidas (
        id SERIAL PRIMARY KEY,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        preco_unitario DOUBLE PRECISION NOT NULL CHECK(preco_unitario >= 0),
        valor_total DOUBLE PRECISION NOT NULL CHECK(valor_total >= 0),
        data TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS precos (
        id SERIAL PRIMARY KEY,
        preco_unitario DOUBLE PRECISION NOT NULL CHECK(preco_unitario >= 0),
        data_inicio TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        ativo INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS quebrados (
        id SERIAL PRIMARY KEY,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        data TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        motivo TEXT DEFAULT '',
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS consumo (
        id SERIAL PRIMARY KEY,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        data TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        observacao TEXT DEFAULT '',
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS despesas (
        id SERIAL PRIMARY KEY,
        valor DOUBLE PRECISION NOT NULL CHECK(valor > 0),
        descricao TEXT NOT NULL DEFAULT '',
        data TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        mes_referencia TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS resumo_mensal (
        id SERIAL PRIMARY KEY,
        mes_referencia TEXT NOT NULL UNIQUE,
        total_entradas INTEGER NOT NULL DEFAULT 0,
        total_saidas INTEGER NOT NULL DEFAULT 0,
        total_quebrados INTEGER NOT NULL DEFAULT 0,
        faturamento_total DOUBLE PRECISION NOT NULL DEFAULT 0.0,
        total_despesas DOUBLE PRECISION NOT NULL DEFAULT 0.0,
        lucro_estimado DOUBLE PRECISION NOT NULL DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        nome TEXT NOT NULL DEFAULT '',
        is_admin INTEGER NOT NULL DEFAULT 0,
        criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        ultimo_login TIMESTAMPTZ
    );

    CREATE TABLE IF NOT EXISTS sessoes (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        expira_em TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );

    CREATE TABLE IF NOT EXISTS configuracoes (
        id SERIAL PRIMARY KEY,
        chave TEXT NOT NULL UNIQUE,
        valor TEXT NOT NULL,
        atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
'''


# ═══════════════════════════════════════════
# INICIALIZAÇÃO
# ═══════════════════════════════════════════

def init_db():
    """Inicializa as tabelas do banco e insere dados padrão."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── Criar tabelas ─────────────────────
    if USE_POSTGRES:
        cursor.executescript(_POSTGRES_SCHEMA)
    else:
        cursor.executescript(_SQLITE_SCHEMA)

    # ── Commit schema creation before migrations ──
    conn.commit()

    # ── Migrações (adicionar colunas novas) ──
    _migrate_columns = [
        ('entradas', 'usuario_id', 'INTEGER'),
        ('entradas', 'usuario_nome', "TEXT DEFAULT ''"),
        ('saidas', 'usuario_id', 'INTEGER'),
        ('saidas', 'usuario_nome', "TEXT DEFAULT ''"),
        ('quebrados', 'usuario_id', 'INTEGER'),
        ('quebrados', 'usuario_nome', "TEXT DEFAULT ''"),
        ('consumo', 'usuario_id', 'INTEGER'),
        ('consumo', 'usuario_nome', "TEXT DEFAULT ''"),
        ('usuarios', 'is_admin', 'INTEGER NOT NULL DEFAULT 0'),
        ('resumo_mensal', 'total_despesas', 'REAL NOT NULL DEFAULT 0.0' if not USE_POSTGRES else 'DOUBLE PRECISION NOT NULL DEFAULT 0.0'),
        ('resumo_mensal', 'total_consumo', 'INTEGER NOT NULL DEFAULT 0'),
    ]

    for table, col, col_type in _migrate_columns:
        try:
            if USE_POSTGRES:
                cursor.execute(
                    f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}'
                )
            else:
                cursor.execute(
                    f'ALTER TABLE {table} ADD COLUMN {col} {col_type}'
                )
        except Exception:
            pass  # Coluna já existe (SQLite)

    # ── Fix tipo BOOLEAN → INTEGER para coluna ativo (PostgreSQL) ──
    if USE_POSTGRES:
        try:
            cursor._cursor.execute(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'precos' AND column_name = 'ativo'"
            )
            col_info = cursor._cursor.fetchone()
            if col_info and col_info.get('data_type') == 'boolean':
                cursor._cursor.execute(
                    "ALTER TABLE precos ALTER COLUMN ativo DROP DEFAULT; "
                    "ALTER TABLE precos ALTER COLUMN ativo TYPE INTEGER "
                    "USING CASE WHEN ativo THEN 1 ELSE 0 END; "
                    "ALTER TABLE precos ALTER COLUMN ativo SET DEFAULT 0"
                )
                conn.commit()
        except Exception:
            try:
                conn._conn.rollback()
            except Exception:
                pass

    # ── Estoque inicial ──────────────────
    cursor.execute("SELECT COUNT(*) as count FROM estoque")
    if cursor.fetchone()['count'] == 0:
        cursor.execute(
            "INSERT INTO estoque (quantidade_total, ultima_atualizacao) VALUES (?, ?)",
            (0, datetime.now().isoformat())
        )

    # ── Usuário admin padrão ─────────────
    cursor.execute("SELECT COUNT(*) as count FROM usuarios")
    if cursor.fetchone()['count'] == 0:
        salt = secrets.token_hex(32)
        password_hash = hashlib.sha256(('admin' + salt).encode()).hexdigest()
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, salt, nome, is_admin) VALUES (?, ?, ?, ?, ?)",
            ('admin', password_hash, salt, 'Administrador', 1)
        )
    else:
        # Garantir que o admin existente tenha is_admin=1
        cursor.execute("UPDATE usuarios SET is_admin = 1 WHERE username = 'admin' AND is_admin = 0")

    _default_configs = [
        ('consumo_habilitado', '0'),
        ('timezone', 'America/Sao_Paulo'),
        ('nome_fazenda', 'EggVault'),
        ('moeda', 'BRL'),
        ('formato_data', 'DD/MM/AAAA'),
    ]
    for chave, valor_padrao in _default_configs:
        cursor.execute("SELECT COUNT(*) as count FROM configuracoes WHERE chave = ?", (chave,))
        if cursor.fetchone()['count'] == 0:
            cursor.execute(
                "INSERT INTO configuracoes (chave, valor) VALUES (?, ?)",
                (chave, valor_padrao)
            )

    conn.commit()
    conn.close()

    db_name = 'PostgreSQL (Supabase)' if USE_POSTGRES else f'SQLite ({DB_PATH})'
    print(f"💾 Banco de dados: {db_name}")
