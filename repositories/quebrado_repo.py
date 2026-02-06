"""Repositório de acesso a dados de Ovos Quebrados."""

from database import get_connection
from datetime import datetime


class QuebradoRepository:
    """Operações CRUD para a tabela quebrados."""

    @staticmethod
    def create(quantidade, motivo='', mes_referencia=None):
        """Cria um novo registro de ovos quebrados."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO quebrados (quantidade, data, motivo, mes_referencia) VALUES (?, ?, ?, ?)",
            (quantidade, datetime.now().isoformat(), motivo, mes_referencia)
        )
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return entry_id

    @staticmethod
    def get_by_month(mes_referencia):
        """Retorna todos os registros de quebrados de um mês específico."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM quebrados WHERE mes_referencia = ? ORDER BY data DESC",
            (mes_referencia,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_total_by_month(mes_referencia):
        """Retorna o total de ovos quebrados em um mês."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(quantidade), 0) as total FROM quebrados WHERE mes_referencia = ?",
            (mes_referencia,)
        )
        result = cursor.fetchone()
        conn.close()
        return result['total']

    @staticmethod
    def get_total_all():
        """Retorna o total geral de ovos quebrados (todas as datas)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(quantidade), 0) as total FROM quebrados")
        result = cursor.fetchone()
        conn.close()
        return result['total']

    @staticmethod
    def delete(entry_id):
        """Remove um registro de quebrado pelo ID e retorna a quantidade."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantidade FROM quebrados WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            raise ValueError("Registro de quebrado não encontrado")
        quantidade = row['quantidade']
        cursor.execute("DELETE FROM quebrados WHERE id = ?", (entry_id,))
        conn.commit()
        conn.close()
        return quantidade
