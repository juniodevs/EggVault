"""Serviço de negócios para Entradas."""

from datetime import datetime
from repositories.entrada_repo import EntradaRepository
from services.estoque_service import EstoqueService
from services.relatorio_service import RelatorioService


class EntradaService:
    """Lógica de negócios para registro de entradas de ovos."""

    @staticmethod
    def registrar(quantidade, observacao='', usuario_id=None, usuario_nome=''):
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValueError("Quantidade deve ser um número inteiro positivo")
        if observacao and len(observacao) > 500:
            raise ValueError("Observação deve ter no máximo 500 caracteres")

        mes_ref = datetime.now().strftime('%Y-%m')
        entry_id = EntradaRepository.create(quantidade, observacao, mes_ref, usuario_id, usuario_nome)
        EstoqueService.atualizar(quantidade, 'add')
        RelatorioService.atualizar_resumo(mes_ref)

        return entry_id

    @staticmethod
    def remover(entry_id):
        entrada = EntradaRepository.get_by_id(entry_id)
        if not entrada:
            raise ValueError("Entrada não encontrada")

        quantidade = entrada['quantidade']
        mes_ref = entrada['mes_referencia']

        estoque = EstoqueService.get_estoque()
        if quantidade > estoque['quantidade_total']:
            raise ValueError(
                f"Não é possível desfazer: estoque ficaria negativo. "
                f"Estoque atual: {estoque['quantidade_total']}, entrada: {quantidade}"
            )

        # Seguro deletar — entrada existe e estoque suporta
        EntradaRepository.delete(entry_id)
        EstoqueService.atualizar(quantidade, 'subtract')
        RelatorioService.atualizar_resumo(mes_ref)

        return quantidade

    @staticmethod
    def listar(mes_referencia=None):
        """Lista entradas de um mês. Padrão: mês atual."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')
        return EntradaRepository.get_by_month(mes_referencia)
