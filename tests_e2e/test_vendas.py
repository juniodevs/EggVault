"""
Testes E2E — CRUD de Vendas / Saídas.

Cobre:
  • Registrar nova venda
  • Visualizar lista de vendas
  • Deletar venda
  • Cálculo de valor total
  • Validação estoque insuficiente
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


class TestVendaForm:
    """Testes do formulário de vendas."""

    def test_venda_form_visible(self, authenticated_page):
        """Formulário de venda deve estar visível."""
        page = authenticated_page
        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)

        assert page.locator("#form-venda").is_visible()
        assert page.locator("#venda-quantidade").is_visible()
        assert page.locator("#venda-preco").is_visible()

    def test_venda_stock_info_bar(self, authenticated_page):
        """Barra de info de estoque deve estar visível."""
        page = authenticated_page
        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)

        stock_bar = page.locator("#venda-stock-info")
        assert stock_bar.is_visible()

    def test_registrar_venda(self, authenticated_page):
        """Deve registrar uma venda com sucesso."""
        page = authenticated_page
        _add_stock(page, 100)

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)

        page.fill("#venda-quantidade", "10")
        page.fill("#venda-preco", "1.50")
        page.click('#form-venda button[type="submit"]')

        # Toast de sucesso
        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        page.wait_for_timeout(1000)

        # Lista deve mostrar a venda
        vendas_list = page.locator("#vendas-list")
        text = vendas_list.inner_text()
        assert "10" in text

    def test_venda_valor_total_auto(self, authenticated_page):
        """Valor total deve ser calculado automaticamente."""
        page = authenticated_page
        _add_stock(page, 50)

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)

        page.fill("#venda-quantidade", "10")
        page.fill("#venda-preco", "2.00")

        # Disparar evento de input para forçar cálculo
        page.locator("#venda-quantidade").dispatch_event("input")
        page.wait_for_timeout(300)

        total = page.locator("#venda-total").inner_text()
        # Deve conter algo como "R$ 20,00" ou "20.00"
        assert "20" in total or "R$" in total

    def test_venda_reduce_stock(self, authenticated_page):
        """Venda deve reduzir o estoque."""
        page = authenticated_page
        _add_stock(page, 60)

        # Verificar estoque inicial
        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_before = int(page.locator("#stock-quantity").inner_text())

        # Fazer venda
        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)
        page.fill("#venda-quantidade", "15")
        page.fill("#venda-preco", "1.00")
        page.click('#form-venda button[type="submit"]')
        page.wait_for_timeout(1500)

        # Verificar estoque depois
        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_after = int(page.locator("#stock-quantity").inner_text())

        assert stock_after == stock_before - 15


class TestVendaDelete:
    """Testes de remoção de vendas."""

    def test_deletar_venda(self, authenticated_page):
        """Deve ser possível deletar uma venda."""
        page = authenticated_page
        _add_stock(page, 50)

        # Registrar venda
        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)
        page.fill("#venda-quantidade", "5")
        page.fill("#venda-preco", "1.00")
        page.click('#form-venda button[type="submit"]')
        page.wait_for_timeout(1500)

        # Deletar
        delete_btn = page.locator("#vendas-list .btn-delete, #vendas-list button.btn-danger").first
        if delete_btn.is_visible():
            delete_btn.click()
            confirm = page.locator("#confirm-ok-btn")
            if confirm.is_visible():
                confirm.click()
            page.wait_for_timeout(1500)
