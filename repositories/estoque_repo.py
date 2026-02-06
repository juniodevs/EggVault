"""Repositório de acesso a dados do Estoque."""

from database import get_connection
from datetime import datetime


class EstoqueRepository:
    """Operações CRUD para a tabela estoque."""

    @staticmethod
    def get_current():
        """Retorna o registro atual de estoque."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM estoque ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_quantidade(delta, operacao='add'):
        """
        Atualiza a quantidade do estoque.

        Args:
            delta: Quantidade a adicionar ou subtrair.
            operacao: 'add' para entrada, 'subtract' para saída.

        Returns:
            Nova quantidade total.

        Raises:
            ValueError: Se o estoque ficar negativo.
        """
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, quantidade_total FROM estoque ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                "INSERT INTO estoque (quantidade_total, ultima_atualizacao) VALUES (0, ?)",
                (datetime.now().isoformat(),)
            )
            conn.commit()
            current_qty = 0
            estoque_id = cursor.lastrowid
        else:
            current_qty = row['quantidade_total']
            estoque_id = row['id']

        if operacao == 'add':
            new_qty = current_qty + delta
        elif operacao == 'subtract':
            new_qty = current_qty - delta
        else:
            conn.close()
            raise ValueError(f"Operação inválida: {operacao}")

        if new_qty < 0:
            conn.close()
            raise ValueError("Estoque insuficiente para esta operação")

        cursor.execute(
            "UPDATE estoque SET quantidade_total = ?, ultima_atualizacao = ? WHERE id = ?",
            (new_qty, datetime.now().isoformat(), estoque_id)
        )
        conn.commit()
        conn.close()
        return new_qty
