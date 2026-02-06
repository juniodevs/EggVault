"""Serviço de negócios para Entradas."""

from datetime import datetime
from repositories.entrada_repo import EntradaRepository
from services.estoque_service import EstoqueService
from services.relatorio_service import RelatorioService


class EntradaService:
    """Lógica de negócios para registro de entradas de ovos."""

    @staticmethod
    def registrar(quantidade, observacao=''):
        """
        Registra uma nova entrada de ovos.

        Args:
            quantidade: Número de ovos (inteiro positivo).
            observacao: Texto opcional de observação.

        Returns:
            ID da entrada criada.

        Raises:
            ValueError: Se a quantidade for inválida.
        """
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValueError("Quantidade deve ser um número inteiro positivo")

        mes_ref = datetime.now().strftime('%Y-%m')
        entry_id = EntradaRepository.create(quantidade, observacao, mes_ref)
        EstoqueService.atualizar(quantidade, 'add')
        RelatorioService.atualizar_resumo(mes_ref)

        return entry_id

    @staticmethod
    def listar(mes_referencia=None):
        """Lista entradas de um mês. Padrão: mês atual."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')
        return EntradaRepository.get_by_month(mes_referencia)
