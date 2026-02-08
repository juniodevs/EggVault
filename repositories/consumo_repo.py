from database import get_connection
from datetime import datetime


class ConsumoRepository:
    @staticmethod
    def create(quantidade, observacao='', mes_referencia=None, usuario_id=None, usuario_nome=''):
        """Cria um novo registro de consumo pessoal."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO consumo (quantidade, data, observacao, mes_referencia, usuario_id, usuario_nome)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (quantidade, datetime.now().isoformat(), observacao, mes_referencia, usuario_id, usuario_nome)
        )
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return entry_id

    @staticmethod
    def get_by_month(mes_referencia):
        """Retorna todos os registros de consumo de um mês específico."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM consumo WHERE mes_referencia = ? ORDER BY data DESC",
            (mes_referencia,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_total_by_month(mes_referencia):
        """Retorna o total de ovos consumidos em um mês."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(quantidade), 0) as total FROM consumo WHERE mes_referencia = ?",
            (mes_referencia,)
        )
        result = cursor.fetchone()
        conn.close()
        return result['total']

    @staticmethod
    def delete(entry_id):
        """Remove um registro de consumo pelo ID e retorna a quantidade."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT quantidade FROM consumo WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        if row is None:
            conn.close()
            raise ValueError("Registro de consumo não encontrado")
        quantidade = row['quantidade']
        cursor.execute("DELETE FROM consumo WHERE id = ?", (entry_id,))
        conn.commit()
        conn.close()
        return quantidade
