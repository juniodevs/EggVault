"""Repositório de acesso a dados do Resumo Mensal."""

from database import get_connection


class ResumoRepository:
    """Operações CRUD para a tabela resumo_mensal."""

    @staticmethod
    def upsert(mes_referencia, total_entradas, total_saidas, total_quebrados, total_consumo, faturamento_total, total_despesas, lucro_estimado):
        """Insere ou atualiza o resumo de um mês."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO resumo_mensal
                   (mes_referencia, total_entradas, total_saidas, total_quebrados, total_consumo, faturamento_total, total_despesas, lucro_estimado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(mes_referencia) DO UPDATE SET
                   total_entradas = excluded.total_entradas,
                   total_saidas = excluded.total_saidas,
                   total_quebrados = excluded.total_quebrados,
                   total_consumo = excluded.total_consumo,
                   faturamento_total = excluded.faturamento_total,
                   total_despesas = excluded.total_despesas,
                   lucro_estimado = excluded.lucro_estimado""",
            (mes_referencia, total_entradas, total_saidas, total_quebrados, total_consumo, faturamento_total, total_despesas, lucro_estimado)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_month(mes_referencia):
        """Retorna o resumo de um mês específico."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM resumo_mensal WHERE mes_referencia = ?",
            (mes_referencia,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {
            'mes_referencia': mes_referencia,
            'total_entradas': 0,
            'total_saidas': 0,
            'total_quebrados': 0,
            'total_consumo': 0,
            'faturamento_total': 0.0,
            'total_despesas': 0.0,
            'lucro_estimado': 0.0
        }

    @staticmethod
    def get_by_year(ano):
        """Retorna os resumos de todos os meses de um ano."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM resumo_mensal WHERE mes_referencia LIKE ? ORDER BY mes_referencia",
            (f"{ano}-%",)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
