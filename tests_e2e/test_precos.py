"""
Testes E2E — Gerenciamento de Preços.

Cobre:
  • Visualizar preço atual
  • Definir novo preço
  • Histórico de preços
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


class TestPrecoForm:
    """Testes da aba de preços."""

    def test_preco_page_visible(self, authenticated_page):
        """Aba de preços deve estar acessível."""
        page = authenticated_page
        page.click('li[data-tab="precos"]')
        page.wait_for_timeout(500)

        assert page.locator("#form-preco").is_visible()
        assert page.locator("#novo-preco").is_visible()
        assert page.locator("#current-price").is_visible()

    def test_definir_novo_preco(self, authenticated_page):
        """Deve definir um novo preço com sucesso."""
        page = authenticated_page
        page.click('li[data-tab="precos"]')
        page.wait_for_timeout(500)

        page.fill("#novo-preco", "1.50")
        page.click('#form-preco button[type="submit"]')

        # Aguardar toast
        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        page.wait_for_timeout(1000)

        # Preço atual deve atualizar
        current = page.locator("#current-price").inner_text()
        assert "1" in current or "1,50" in current

    def test_historico_precos_atualiza(self, authenticated_page):
        """Histórico deve ser populado após definir preços."""
        page = authenticated_page
        page.click('li[data-tab="precos"]')
        page.wait_for_timeout(500)

        # Definir primeiro preço
        page.fill("#novo-preco", "2.00")
        page.click('#form-preco button[type="submit"]')
        page.wait_for_timeout(1500)

        # Definir segundo preço
        page.fill("#novo-preco", "2.50")
        page.click('#form-preco button[type="submit"]')
        page.wait_for_timeout(1500)

        # Tabela deve ter pelo menos 2 linhas
        rows = page.locator("#precos-list tr")
        assert rows.count() >= 2

    def test_preco_zero_allowed(self, authenticated_page):
        """Preço zero deve ser aceito (gratuito)."""
        page = authenticated_page
        page.click('li[data-tab="precos"]')
        page.wait_for_timeout(500)

        page.fill("#novo-preco", "0")
        page.click('#form-preco button[type="submit"]')
        page.wait_for_timeout(1500)

        current = page.locator("#current-price").inner_text()
        assert "0" in current
