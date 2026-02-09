"""Serviço de negócios para Ovos Quebrados."""

from datetime import datetime
from repositories.quebrado_repo import QuebradoRepository
from services.estoque_service import EstoqueService
from services.relatorio_service import RelatorioService


class QuebradoService:
    """Lógica de negócios para registro de ovos quebrados (perda)."""

    @staticmethod
    def registrar(quantidade, motivo='', usuario_id=None, usuario_nome=''):
        """
        Registra ovos quebrados — subtrai do estoque.

        Args:
            quantidade: Número de ovos quebrados (inteiro positivo).
            motivo: Motivo/observação da perda (máx 500 caracteres).
            usuario_id: ID do usuário que registrou.
            usuario_nome: Nome do usuário que registrou.

        Returns:
            ID do registro criado.

        Raises:
            ValueError: Se quantidade inválida ou estoque insuficiente.
        """
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValueError("Quantidade deve ser um número inteiro positivo")
        if motivo and len(motivo) > 500:
            raise ValueError("Motivo deve ter no máximo 500 caracteres")

        # Verificar estoque disponível
        estoque = EstoqueService.get_estoque()
        if quantidade > estoque['quantidade_total']:
            raise ValueError(
                f"Estoque insuficiente. Disponível: {estoque['quantidade_total']} ovos"
            )

        mes_ref = datetime.now().strftime('%Y-%m')
        entry_id = QuebradoRepository.create(quantidade, motivo, mes_ref, usuario_id, usuario_nome)
        EstoqueService.atualizar(quantidade, 'subtract')
        RelatorioService.atualizar_resumo(mes_ref)

        return entry_id

    @staticmethod
    def remover(entry_id):
        """
        Remove um registro de quebrado — devolve ao estoque.

        Args:
            entry_id: ID do registro a remover.

        Returns:
            Quantidade devolvida ao estoque.

        Raises:
            ValueError: Se o registro não for encontrado.
        """
        quantidade, mes_ref = QuebradoRepository.delete(entry_id)
        EstoqueService.atualizar(quantidade, 'add')
        RelatorioService.atualizar_resumo(mes_ref)

        return quantidade

    @staticmethod
    def listar(mes_referencia=None):
        """Lista registros de quebrados de um mês. Padrão: mês atual."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')
        return QuebradoRepository.get_by_month(mes_referencia)
