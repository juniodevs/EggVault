from datetime import datetime
from repositories.consumo_repo import ConsumoRepository
from services.estoque_service import EstoqueService
from services.relatorio_service import RelatorioService


class ConsumoService:
    """Lógica de negócios para registro de consumo pessoal de ovos."""

    @staticmethod
    def registrar(quantidade, observacao='', usuario_id=None, usuario_nome=''):
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValueError("Quantidade deve ser um número inteiro positivo")

        estoque = EstoqueService.get_estoque()
        if quantidade > estoque['quantidade_total']:
            raise ValueError(
                f"Estoque insuficiente. Disponível: {estoque['quantidade_total']} ovos"
            )

        mes_ref = datetime.now().strftime('%Y-%m')
        entry_id = ConsumoRepository.create(quantidade, observacao, mes_ref, usuario_id, usuario_nome)
        EstoqueService.atualizar(quantidade, 'subtract')
        RelatorioService.atualizar_resumo(mes_ref)

        return entry_id

    @staticmethod
    def remover(entry_id):
        quantidade = ConsumoRepository.delete(entry_id)
        EstoqueService.atualizar(quantidade, 'add')

        mes_ref = datetime.now().strftime('%Y-%m')
        RelatorioService.atualizar_resumo(mes_ref)

        return quantidade

    @staticmethod
    def listar(mes_referencia=None):
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')
        return ConsumoRepository.get_by_month(mes_referencia)
