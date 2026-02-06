"""Serviço de negócios para Estoque."""

from repositories.estoque_repo import EstoqueRepository


class EstoqueService:
    """Lógica de negócios relacionada ao estoque."""

    LIMITE_BAIXO = 30
    LIMITE_MEDIO = 100

    @staticmethod
    def get_estoque():
        """
        Retorna o estoque atual com indicador de status.

        Returns:
            dict com quantidade_total, status ('baixo'|'medio'|'alto'),
            cor ('vermelho'|'amarelo'|'verde') e ultima_atualizacao.
        """
        estoque = EstoqueRepository.get_current()
        if not estoque:
            return {
                'quantidade_total': 0,
                'status': 'baixo',
                'cor': 'vermelho',
                'ultima_atualizacao': ''
            }

        qty = estoque['quantidade_total']
        if qty <= EstoqueService.LIMITE_BAIXO:
            status, cor = 'baixo', 'vermelho'
        elif qty <= EstoqueService.LIMITE_MEDIO:
            status, cor = 'medio', 'amarelo'
        else:
            status, cor = 'alto', 'verde'

        return {
            'id': estoque['id'],
            'quantidade_total': qty,
            'ultima_atualizacao': estoque['ultima_atualizacao'],
            'status': status,
            'cor': cor
        }

    @staticmethod
    def atualizar(quantidade, operacao='add'):
        """Atualiza o estoque (add ou subtract)."""
        return EstoqueRepository.update_quantidade(quantidade, operacao)
