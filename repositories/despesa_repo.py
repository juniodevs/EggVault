"""Repositório de acesso a dados de Despesas."""

from database import get_connection
from datetime import datetime


class DespesaRepository:
    """Operações CRUD para a tabela despesas."""

    @staticmethod
    def create(valor, descricao='', mes_referencia=None, usuario_id=None, usuario_nome=''):
        """Cria um novo registro de despesa."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO despesas (valor, descricao, data, mes_referencia, usuario_id, usuario_nome)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (valor, descricao, datetime.now().isoformat(), mes_referencia, usuario_id, usuario_nome)
        )
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return entry_id

    @staticmethod
    def get_by_month(mes_referencia):
        """Retorna todas as despesas de um mês específico."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM despesas WHERE mes_referencia = ? ORDER BY data DESC",
            (mes_referencia,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_total_by_month(mes_referencia):
        """Retorna o total de despesas em um mês."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(valor), 0) as total FROM despesas WHERE mes_referencia = ?",
            (mes_referencia,)
        )
        result = cursor.fetchone()
        conn.close()
        return result['total']

    @staticmethod
    def delete(entry_id):
        """Remove uma despesa pelo ID e retorna o valor."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT valor, mes_referencia FROM despesas WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            raise ValueError("Despesa não encontrada")
        valor = row['valor']
        mes_referencia = row['mes_referencia']
        cursor.execute("DELETE FROM despesas WHERE id = ?", (entry_id,))
        conn.commit()
        conn.close()
        return valor, mes_referencia
