"""
Módulo de banco de dados SQLite.
Gerencia conexão, inicialização de tabelas e dados padrão.
"""

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime

DB_PATH = os.environ.get(
    'OVOS_DB_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ovos.db')
)


def get_connection():
    """Cria e retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Inicializa as tabelas do banco e insere dados padrão."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript('''
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

        CREATE TABLE IF NOT EXISTS resumo_mensal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes_referencia TEXT NOT NULL UNIQUE,
            total_entradas INTEGER NOT NULL DEFAULT 0,
            total_saidas INTEGER NOT NULL DEFAULT 0,
            total_quebrados INTEGER NOT NULL DEFAULT 0,
            faturamento_total REAL NOT NULL DEFAULT 0.0,
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
    ''')

    # Migrações — adicionar colunas se não existem (para bancos existentes)
    _migrate_columns = [
        ('entradas', 'usuario_id', 'INTEGER'),
        ('entradas', 'usuario_nome', "TEXT DEFAULT ''"),
        ('saidas', 'usuario_id', 'INTEGER'),
        ('saidas', 'usuario_nome', "TEXT DEFAULT ''"),
        ('quebrados', 'usuario_id', 'INTEGER'),
        ('quebrados', 'usuario_nome', "TEXT DEFAULT ''"),
        ('usuarios', 'is_admin', 'INTEGER NOT NULL DEFAULT 0'),
    ]
    for table, col, col_type in _migrate_columns:
        try:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')
        except Exception:
            pass  # Coluna já existe

    # Inicializa registro de estoque se vazio
    cursor.execute("SELECT COUNT(*) as count FROM estoque")
    if cursor.fetchone()['count'] == 0:
        cursor.execute(
            "INSERT INTO estoque (quantidade_total, ultima_atualizacao) VALUES (?, ?)",
            (0, datetime.now().isoformat())
        )

    # Cria usuário admin padrão se não houver nenhum usuário
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

    conn.commit()
    conn.close()
