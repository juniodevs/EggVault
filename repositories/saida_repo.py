"""Repositório de acesso a dados de Saídas/Vendas."""

from database import get_connection
from datetime import datetime


class SaidaRepository:
    """Operações CRUD para a tabela saidas."""

    @staticmethod
    def create(quantidade, preco_unitario, valor_total, mes_referencia=None, usuario_id=None, usuario_nome='', cliente_id=None, cliente_nome=''):
        """Cria um novo registro de saída/venda."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO saidas (quantidade, preco_unitario, valor_total, data, mes_referencia, usuario_id, usuario_nome, cliente_id, cliente_nome)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (quantidade, preco_unitario, valor_total, datetime.now().isoformat(), mes_referencia, usuario_id, usuario_nome, cliente_id, cliente_nome)
        )
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return sale_id

    @staticmethod
    def get_by_month(mes_referencia):
        """Retorna todas as saídas de um mês específico."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM saidas WHERE mes_referencia = ? ORDER BY data DESC",
            (mes_referencia,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_totals_by_month(mes_referencia):
        """Retorna os totais (quantidade e valor) de um mês."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COALESCE(SUM(quantidade), 0) as total_quantidade,
                      COALESCE(SUM(valor_total), 0.0) as total_valor
               FROM saidas WHERE mes_referencia = ?""",
            (mes_referencia,)
        )
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def delete(sale_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantidade, mes_referencia FROM saidas WHERE id = ?", (sale_id,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            raise ValueError("Venda não encontrada")
        quantidade = row['quantidade']
        mes_referencia = row['mes_referencia']
        cursor.execute("DELETE FROM saidas WHERE id = ?", (sale_id,))
        conn.commit()
        conn.close()
        return quantidade, mes_referencia
