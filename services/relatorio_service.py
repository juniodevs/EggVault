"""Serviço de negócios para Relatórios."""

from repositories.resumo_repo import ResumoRepository
from repositories.entrada_repo import EntradaRepository
from repositories.saida_repo import SaidaRepository
from repositories.quebrado_repo import QuebradoRepository
from repositories.consumo_repo import ConsumoRepository
from repositories.despesa_repo import DespesaRepository


class RelatorioService:
    """Lógica de negócios para geração de relatórios."""

    @staticmethod
    def atualizar_resumo(mes_referencia):
        """
        Recalcula e salva o resumo mensal baseado nas entradas e saídas.

        Args:
            mes_referencia: Mês no formato 'YYYY-MM'.
        """
        total_entradas = EntradaRepository.get_total_by_month(mes_referencia)
        totais_saidas = SaidaRepository.get_totals_by_month(mes_referencia)
        total_quebrados = QuebradoRepository.get_total_by_month(mes_referencia)
        total_consumo = ConsumoRepository.get_total_by_month(mes_referencia)
        total_despesas = DespesaRepository.get_total_by_month(mes_referencia)

        total_saidas = totais_saidas['total_quantidade']
        faturamento = totais_saidas['total_valor']
        lucro = faturamento - total_despesas  # Faturamento líquido = faturamento - despesas

        ResumoRepository.upsert(
            mes_referencia, total_entradas, total_saidas, total_quebrados, total_consumo, faturamento, total_despesas, lucro
        )

    @staticmethod
    def get_resumo(mes_referencia):
        """Retorna o resumo de um mês específico."""
        return ResumoRepository.get_by_month(mes_referencia)

    @staticmethod
    def get_dados_anuais(ano):
        """Retorna os resumos de todos os meses de um ano para gráficos."""
        return ResumoRepository.get_by_year(ano)
