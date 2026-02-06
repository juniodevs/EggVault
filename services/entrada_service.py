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
    def remover(entry_id):
        """
        Remove uma entrada — subtrai ovos do estoque.

        Args:
            entry_id: ID da entrada a remover.

        Returns:
            Quantidade removida do estoque.

        Raises:
            ValueError: Se a entrada não for encontrada ou
                        estoque insuficiente para reverter.
        """
        quantidade = EntradaRepository.delete(entry_id)

        # Verificar se estoque suficiente para reverter
        estoque = EstoqueService.get_estoque()
        if quantidade > estoque['quantidade_total']:
            # Re-inserir a entrada (rollback manual)
            mes_ref = datetime.now().strftime('%Y-%m')
            EntradaRepository.create(quantidade, '(restaurado após falha)', mes_ref)
            raise ValueError(
                f"Não é possível desfazer: estoque ficaria negativo. "
                f"Estoque atual: {estoque['quantidade_total']}, entrada: {quantidade}"
            )

        EstoqueService.atualizar(quantidade, 'subtract')

        mes_ref = datetime.now().strftime('%Y-%m')
        RelatorioService.atualizar_resumo(mes_ref)

        return quantidade

    @staticmethod
    def listar(mes_referencia=None):
        """Lista entradas de um mês. Padrão: mês atual."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')
        return EntradaRepository.get_by_month(mes_referencia)
