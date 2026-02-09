"""Serviço de negócios para Despesas."""

from datetime import datetime
from repositories.despesa_repo import DespesaRepository
from services.relatorio_service import RelatorioService


class DespesaService:
    """Lógica de negócios para registro de despesas (subtraídas do faturamento)."""

    @staticmethod
    def registrar(valor, descricao='', usuario_id=None, usuario_nome=''):
        """
        Registra uma nova despesa.

        Args:
            valor: Valor da despesa (float positivo).
            descricao: Descrição da despesa.
            usuario_id: ID do usuário que registrou.
            usuario_nome: Nome do usuário que registrou.

        Returns:
            ID do registro criado.

        Raises:
            ValueError: Se valor inválido.
        """
        if not isinstance(valor, (int, float)) or valor <= 0:
            raise ValueError("Valor da despesa deve ser um número positivo")

        if not descricao or not descricao.strip():
            raise ValueError("Descrição da despesa é obrigatória")

        if len(descricao.strip()) > 500:
            raise ValueError("Descrição deve ter no máximo 500 caracteres")

        mes_ref = datetime.now().strftime('%Y-%m')
        entry_id = DespesaRepository.create(valor, descricao.strip(), mes_ref, usuario_id, usuario_nome)
        RelatorioService.atualizar_resumo(mes_ref)

        return entry_id

    @staticmethod
    def remover(entry_id):
        """
        Remove uma despesa.

        Args:
            entry_id: ID do registro a remover.

        Returns:
            Valor da despesa removida.

        Raises:
            ValueError: Se o registro não for encontrado.
        """
        valor, mes_ref = DespesaRepository.delete(entry_id)
        RelatorioService.atualizar_resumo(mes_ref)
        return valor

    @staticmethod
    def listar(mes_referencia=None):
        """Lista despesas de um mês. Padrão: mês atual."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')
        return DespesaRepository.get_by_month(mes_referencia)
