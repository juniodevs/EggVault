"""Repositório de acesso a dados de Clientes."""

from database import get_connection
from datetime import datetime


class ClienteRepository:
    """Operações CRUD para a tabela clientes."""

    @staticmethod
    def create(nome, numero=None):
        """Cria um novo cliente. Retorna o ID criado."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO clientes (nome, numero, data_criacao)
               VALUES (?, ?, ?)""",
            (nome.strip(), numero, datetime.now().isoformat())
        )
        cliente_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return cliente_id

    @staticmethod
    def get_all():
        """Retorna todos os clientes ordenados por nome."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM clientes ORDER BY nome ASC"
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_by_id(cliente_id):
        """Retorna um cliente pelo ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update(cliente_id, nome=None, numero=None):
        """Atualiza nome e/ou número de um cliente."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            raise ValueError("Cliente não encontrado")

        novo_nome = nome.strip() if nome is not None else row['nome']
        novo_numero = numero if numero is not None else row['numero']

        cursor.execute(
            "UPDATE clientes SET nome = ?, numero = ? WHERE id = ?",
            (novo_nome, novo_numero, cliente_id)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def delete(cliente_id):
        """Remove um cliente."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clientes WHERE id = ?", (cliente_id,))
        if cursor.fetchone() is None:
            conn.close()
            raise ValueError("Cliente não encontrado")
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def update_ultima_compra(cliente_id, data_compra=None):
        """Atualiza o campo data_ultima_compra do cliente."""
        if data_compra is None:
            data_compra = datetime.now().isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE clientes SET data_ultima_compra = ? WHERE id = ?",
            (data_compra, cliente_id)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def exists_by_nome_numero(nome, numero, exclude_id=None):
        """Verifica se já existe cliente com mesmo nome e número."""
        conn = get_connection()
        cursor = conn.cursor()
        if exclude_id:
            cursor.execute(
                "SELECT id FROM clientes WHERE nome = ? AND numero = ? AND id != ?",
                (nome.strip(), numero, exclude_id)
            )
        else:
            cursor.execute(
                "SELECT id FROM clientes WHERE nome = ? AND numero = ?",
                (nome.strip(), numero)
            )
        row = cursor.fetchone()
        conn.close()
        return row is not None
