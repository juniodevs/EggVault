"""Serviço de negócios para Saídas/Vendas."""

from datetime import datetime
from repositories.saida_repo import SaidaRepository
from services.estoque_service import EstoqueService
from services.preco_service import PrecoService
from services.relatorio_service import RelatorioService


class SaidaService:
    """Lógica de negócios para registro de vendas/saídas de ovos."""

    @staticmethod
    def registrar(quantidade, preco_unitario=None, valor_total=None, usuario_id=None, usuario_nome=''):
        """
        Registra uma nova venda de ovos.

        Args:
            quantidade: Número de ovos vendidos (inteiro positivo).
            preco_unitario: Preço por ovo. Se None, usa o preço ativo.
            valor_total: Valor total da venda. Se fornecido, tem prioridade sobre preco_unitario.
            usuario_id: ID do usuário que registrou.
            usuario_nome: Nome do usuário que registrou.

        Returns:
            ID da venda criada.

        Raises:
            ValueError: Se quantidade inválida, estoque insuficiente,
                        preço negativo ou nenhum preço definido.
        """
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValueError("Quantidade deve ser um número inteiro positivo")

        # Verificar estoque disponível
        estoque = EstoqueService.get_estoque()
        if quantidade > estoque['quantidade_total']:
            raise ValueError(
                f"Estoque insuficiente. Disponível: {estoque['quantidade_total']} ovos"
            )

        # Determinar valor_total e preco_unitario
        if valor_total is not None:
            # Se valor_total foi fornecido, usa ele e calcula o preço unitário
            if valor_total < 0:
                raise ValueError("Valor total não pode ser negativo")
            preco_unitario = round(valor_total / quantidade, 4)  # Mais precisão para o preço unitário
        elif preco_unitario is not None:
            # Se apenas preco_unitario foi fornecido, calcula o total
            if preco_unitario < 0:
                raise ValueError("Preço unitário não pode ser negativo")
            valor_total = round(quantidade * preco_unitario, 2)
        else:
            # Nenhum dos dois foi fornecido, usa o preço ativo
            preco = PrecoService.get_ativo()
            if preco is None:
                raise ValueError("Nenhum preço ativo definido. Defina um preço antes de vender.")
            preco_unitario = preco['preco_unitario']
            valor_total = round(quantidade * preco_unitario, 2)

        mes_ref = datetime.now().strftime('%Y-%m')

        sale_id = SaidaRepository.create(quantidade, preco_unitario, valor_total, mes_ref, usuario_id, usuario_nome)
        EstoqueService.atualizar(quantidade, 'subtract')
        RelatorioService.atualizar_resumo(mes_ref)

        return sale_id

    @staticmethod
    def remover(sale_id):
        """
        Remove uma venda — devolve ovos ao estoque.

        Args:
            sale_id: ID da venda a remover.

        Returns:
            Quantidade devolvida ao estoque.

        Raises:
            ValueError: Se a venda não for encontrada.
        """
        quantidade, mes_ref = SaidaRepository.delete(sale_id)
        EstoqueService.atualizar(quantidade, 'add')
        RelatorioService.atualizar_resumo(mes_ref)

        return quantidade

    @staticmethod
    def listar(mes_referencia=None):
        """Lista saídas de um mês. Padrão: mês atual."""
        if mes_referencia is None:
            mes_referencia = datetime.now().strftime('%Y-%m')
        return SaidaRepository.get_by_month(mes_referencia)
