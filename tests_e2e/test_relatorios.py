"""
Testes E2E — Relatórios e Gráficos.

Cobre:
  • Visualização de resumo mensal
  • Cards de estatísticas
  • Gráficos Chart.js presentes
  • Botões de exportação
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


class TestRelatorioPage:
    """Testes da aba de relatórios."""

    def test_relatorio_page_renders(self, authenticated_page):
        """Aba de relatórios deve renderizar com filtros."""
        page = authenticated_page
        page.click('li[data-tab="relatorios"]')
        page.wait_for_timeout(500)

        assert page.locator("#tab-relatorios").is_visible()
        assert page.locator("#report-month").is_visible()
        assert page.locator("#report-year").is_visible()

    def test_relatorio_stats_visible(self, authenticated_page):
        """Cards de estatísticas devem estar visíveis."""
        page = authenticated_page
        page.click('li[data-tab="relatorios"]')
        page.wait_for_timeout(1000)

        assert page.locator("#report-entradas").is_visible()
        assert page.locator("#report-saidas").is_visible()
        assert page.locator("#report-quebrados").is_visible()
        assert page.locator("#report-faturamento").is_visible()

    def test_relatorio_charts_exist(self, authenticated_page):
        """Canvas dos gráficos devem existir no DOM."""
        page = authenticated_page
        page.click('li[data-tab="relatorios"]')
        page.wait_for_timeout(1000)

        assert page.locator("#chart-entradas-saidas").count() == 1
        assert page.locator("#chart-faturamento").count() == 1
        assert page.locator("#chart-distribuicao").count() == 1

    def test_export_buttons_visible(self, authenticated_page):
        """Botões de exportação devem estar visíveis."""
        page = authenticated_page
        page.click('li[data-tab="relatorios"]')
        page.wait_for_timeout(500)

        assert page.locator(".btn-export-excel").is_visible()
        assert page.locator(".btn-export-pdf").is_visible()
        assert page.locator(".btn-export-anual").is_visible()

    def test_gerar_relatorio_click(self, authenticated_page):
        """Botão Gerar Relatório deve funcionar sem erros."""
        page = authenticated_page
        page.click('li[data-tab="relatorios"]')
        page.wait_for_timeout(500)

        # Clicar no botão de gerar relatório
        page.click('button:has-text("Gerar Relatório")')
        page.wait_for_timeout(2000)

        # Não deve haver mensagem de erro visível
        # Stats devem continuar visíveis
        assert page.locator("#report-entradas").is_visible()
