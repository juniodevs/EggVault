"""Repositório de acesso a dados de Preços."""

from database import get_connection
from datetime import datetime


class PrecoRepository:
    """Operações CRUD para a tabela precos."""

    @staticmethod
    def create(preco_unitario):
        """
        Cria um novo preço ativo, desativando os anteriores.
        Garante apenas um preço ativo por vez.
        """
        conn = get_connection()
        cursor = conn.cursor()

        # Desativar todos os preços existentes
        cursor.execute("UPDATE precos SET ativo = 0")

        # Criar novo preço ativo
        cursor.execute(
            "INSERT INTO precos (preco_unitario, data_inicio, ativo) VALUES (?, ?, 1)",
            (preco_unitario, datetime.now().isoformat())
        )
        price_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return price_id

    @staticmethod
    def get_active():
        """Retorna o preço ativo atual."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM precos WHERE ativo = 1 ORDER BY data_inicio DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_all():
        """Retorna todo o histórico de preços."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM precos ORDER BY data_inicio DESC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
