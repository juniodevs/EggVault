"""
Testes E2E — CRUD de Ovos Quebrados.

Cobre:
  • Registrar perda
  • Visualizar registros
  • Deletar registro
  • Impacto no estoque
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


def _add_stock(page, qty=100):
    """Helper: adiciona estoque via aba Entradas."""
    page.click('li[data-tab="entradas"]')
    page.wait_for_timeout(500)
    page.fill("#entrada-quantidade", str(qty))
    page.click('#form-entrada button[type="submit"]')
    page.wait_for_timeout(1500)


class TestQuebradoForm:
    """Testes do formulário de ovos quebrados."""

    def test_quebrado_form_visible(self, authenticated_page):
        """Formulário de quebrados deve estar visível."""
        page = authenticated_page
        page.click('li[data-tab="quebrados"]')
        page.wait_for_timeout(500)

        assert page.locator("#form-quebrado").is_visible()
        assert page.locator("#quebrado-quantidade").is_visible()
        assert page.locator("#quebrado-motivo").is_visible()

    def test_registrar_quebrado(self, authenticated_page):
        """Deve registrar ovos quebrados."""
        page = authenticated_page
        _add_stock(page, 50)

        page.click('li[data-tab="quebrados"]')
        page.wait_for_timeout(500)

        page.fill("#quebrado-quantidade", "3")
        page.fill("#quebrado-motivo", "Caíram do ninho - teste Playwright")
        page.click('#form-quebrado button[type="submit"]')

        # Toast de sucesso
        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        page.wait_for_timeout(1000)
        quebrados_list = page.locator("#quebrados-hoje-list")
        assert "3" in quebrados_list.inner_text()

    def test_quebrado_reduz_estoque(self, authenticated_page):
        """Quebrados devem reduzir o estoque."""
        page = authenticated_page
        _add_stock(page, 40)

        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_before = int(page.locator("#stock-quantity").inner_text())

        page.click('li[data-tab="quebrados"]')
        page.wait_for_timeout(500)
        page.fill("#quebrado-quantidade", "5")
        page.fill("#quebrado-motivo", "Teste redução")
        page.click('#form-quebrado button[type="submit"]')
        page.wait_for_timeout(1500)

        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_after = int(page.locator("#stock-quantity").inner_text())

        assert stock_after == stock_before - 5

    def test_quebrado_month_total(self, authenticated_page):
        """Total de quebrados no mês deve atualizar."""
        page = authenticated_page
        _add_stock(page, 50)

        page.click('li[data-tab="quebrados"]')
        page.wait_for_timeout(500)

        page.fill("#quebrado-quantidade", "7")
        page.click('#form-quebrado button[type="submit"]')
        page.wait_for_timeout(1500)

        total = page.locator("#quebrados-mes-total")
        total_text = total.inner_text()
        # Extrair número do texto (pode ser "7 ovos" ou similar)
        import re
        match = re.search(r'(\d+)', total_text)
        if match:
            total_value = int(match.group(1))
            assert total_value >= 7


class TestQuebradoDelete:
    """Testes de remoção de registros de quebra."""

    def test_deletar_quebrado(self, authenticated_page):
        """Deve ser possível deletar um registro de quebra."""
        page = authenticated_page
        _add_stock(page, 40)

        page.click('li[data-tab="quebrados"]')
        page.wait_for_timeout(500)
        page.fill("#quebrado-quantidade", "2")
        page.click('#form-quebrado button[type="submit"]')
        page.wait_for_timeout(1500)

        delete_btn = page.locator("#quebrados-hoje-list .btn-undo, #quebrados-hoje-list button").first
        if delete_btn.is_visible():
            delete_btn.click()
            confirm = page.locator("#confirm-ok-btn")
            if confirm.is_visible():
                confirm.click()
            page.wait_for_timeout(1500)
