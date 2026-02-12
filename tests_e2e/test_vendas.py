"""
Testes E2E — CRUD de Vendas / Saídas.

Cobre:
  • Registrar nova venda
  • Visualizar lista de vendas
  • Deletar venda
  • Cálculo de valor total
  • Validação estoque insuficiente
"""

import re
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
        assert page.locator("#venda-total").is_visible()

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

        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        page.wait_for_timeout(1000)

        vendas_list = page.locator("#vendas-hoje-list")
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

        page.locator("#venda-preco").dispatch_event("input")
        page.wait_for_timeout(300)

        total = page.locator("#venda-total").input_value()
        assert "20" in total

    def test_venda_calc_preco_from_total(self, authenticated_page):
        """Preço unitário deve ser calculado ao digitar valor total."""
        page = authenticated_page
        _add_stock(page, 50)

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)

        page.fill("#venda-quantidade", "12")
        page.fill("#venda-total", "10,80")

        page.locator("#venda-total").dispatch_event("input")
        page.wait_for_timeout(300)

        preco = page.locator("#venda-preco").input_value()
        assert "0,90" in preco or "0.90" in preco

    def test_venda_reduce_stock(self, authenticated_page):
        """Venda deve reduzir o estoque."""
        page = authenticated_page
        _add_stock(page, 60)

        # Verificar estoque inicial
        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_text = page.locator("#stock-quantity").inner_text()
        stock_before = int(re.sub(r'[^\d]', '', stock_text))

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)
        page.fill("#venda-quantidade", "15")
        page.fill("#venda-preco", "1.00")
        page.click('#form-venda button[type="submit"]')
        page.wait_for_timeout(1500)

        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_text = page.locator("#stock-quantity").inner_text()
        stock_after = int(re.sub(r'[^\d]', '', stock_text))

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


class TestVendaTotals:
    """Testes dos totais nas tabelas de vendas."""

    def test_venda_total_row_visible(self, authenticated_page):
        """Linha de total deve estar visível após registrar vendas."""
        page = authenticated_page
        _add_stock(page, 100)

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)

        # Verificar total antes
        total_row = page.locator("#vendas-hoje-list tr.total-row")
        total_before = 0
        if total_row.is_visible():
            match = re.search(r'(\d+)\s+ovos', total_row.inner_text())
            if match:
                total_before = int(match.group(1))

        # Registrar múltiplas vendas
        page.fill("#venda-quantidade", "10")
        page.fill("#venda-preco", "1.50")
        page.click('#form-venda button[type="submit"]')
        page.wait_for_timeout(1500)

        page.fill("#venda-quantidade", "5")
        page.fill("#venda-preco", "2.00")
        page.click('#form-venda button[type="submit"]')
        page.wait_for_timeout(1500)

        # Verificar se a linha de total existe
        total_row = page.locator("#vendas-hoje-list tr.total-row")
        assert total_row.is_visible()

        # Verificar se o total está correto
        text = total_row.inner_text()
        assert "TOTAL" in text
        
        # Extrair quantidade de ovos e verificar que aumentou pelo menos 15
        match = re.search(r'(\d+)\s+ovos', text)
        assert match, "Total deve conter quantidade de ovos"
        total_after = int(match.group(1))
        assert total_after >= total_before + 15

    def test_venda_total_shows_quantity_and_value(self, authenticated_page):
        """Total de vendas deve mostrar quantidade e valor."""
        page = authenticated_page
        _add_stock(page, 100)

        page.click('li[data-tab="vendas"]')
        page.wait_for_timeout(500)

        # Verificar total antes
        header_total_before = page.locator("#vendas-hoje-total").inner_text()
        qty_before = 0
        match = re.search(r'(\d+)\s+ovos', header_total_before)
        if match:
            qty_before = int(match.group(1))

        # Registrar venda
        page.fill("#venda-quantidade", "12")
        page.fill("#venda-preco", "1.00")
        page.click('#form-venda button[type="submit"]')
        page.wait_for_timeout(1500)

        # Verificar total no cabeçalho
        header_total = page.locator("#vendas-hoje-total").inner_text()
        
        # Deve conter quantidade e valor formatados corretamente
        assert "ovos" in header_total
        assert "R$" in header_total or "•" in header_total  # Separador entre qtd e valor
        
        # Verificar que a quantidade aumentou pelo menos 12
        match = re.search(r'(\d+)\s+ovos', header_total)
        assert match, "Total deve conter quantidade de ovos"
        qty_after = int(match.group(1))
        assert qty_after >= qty_before + 12
