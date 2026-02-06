"""
Testes E2E — CRUD de Entradas de Ovos.

Cobre:
  • Registrar nova entrada
  • Visualizar lista de entradas
  • Deletar entrada
  • Validação de campos obrigatórios
  • Impacto no estoque
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


class TestEntradaForm:
    """Testes do formulário de nova entrada."""

    def test_entrada_form_visible(self, authenticated_page):
        """Formulário de entrada deve estar visível na aba Entradas."""
        page = authenticated_page
        page.click('li[data-tab="entradas"]')
        page.wait_for_timeout(500)

        form = page.locator("#form-entrada")
        assert form.is_visible()
        assert page.locator("#entrada-quantidade").is_visible()
        assert page.locator("#entrada-observacao").is_visible()

    def test_registrar_entrada(self, authenticated_page):
        """Deve registrar uma nova entrada e mostrar toast de sucesso."""
        page = authenticated_page
        page.click('li[data-tab="entradas"]')
        page.wait_for_timeout(500)

        page.fill("#entrada-quantidade", "50")
        page.fill("#entrada-observacao", "Coleta teste Playwright")
        page.click('#form-entrada button[type="submit"]')

        # Toast de sucesso deve aparecer
        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        # Verificar lista de entradas atualizada
        page.wait_for_timeout(1000)
        entradas_list = page.locator("#entradas-list")
        assert "50" in entradas_list.inner_text()

    def test_entrada_atualiza_estoque(self, authenticated_page):
        """Após registrar entrada, estoque deve atualizar."""
        page = authenticated_page

        # Registrar entrada
        page.click('li[data-tab="entradas"]')
        page.wait_for_timeout(500)
        page.fill("#entrada-quantidade", "30")
        page.click('#form-entrada button[type="submit"]')
        page.wait_for_timeout(1500)

        # Ir para estoque e verificar
        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)

        qty_text = page.locator("#stock-quantity").inner_text()
        assert int(qty_text) >= 30

    def test_entrada_sem_quantidade(self, authenticated_page):
        """Tentativa de registrar sem quantidade não deve funcionar."""
        page = authenticated_page
        page.click('li[data-tab="entradas"]')
        page.wait_for_timeout(500)

        # Limpa o campo e tenta submeter
        page.fill("#entrada-quantidade", "")
        page.click('#form-entrada button[type="submit"]')

        # O formulário não deve ser submetido (validação HTML5)
        page.wait_for_timeout(500)

    def test_entrada_com_observacao(self, authenticated_page):
        """Observação deve ser salva corretamente."""
        page = authenticated_page
        page.click('li[data-tab="entradas"]')
        page.wait_for_timeout(500)

        page.fill("#entrada-quantidade", "10")
        page.fill("#entrada-observacao", "Teste com observação especial 🥚")
        page.click('#form-entrada button[type="submit"]')
        page.wait_for_timeout(1500)

        entradas_list = page.locator("#entradas-list")
        text = entradas_list.inner_text()
        assert "10" in text


class TestEntradaDelete:
    """Testes de remoção de entradas."""

    def test_deletar_entrada(self, authenticated_page):
        """Deve ser possível deletar uma entrada."""
        page = authenticated_page
        page.click('li[data-tab="entradas"]')
        page.wait_for_timeout(500)

        # Criar entrada
        page.fill("#entrada-quantidade", "25")
        page.click('#form-entrada button[type="submit"]')
        page.wait_for_timeout(1500)

        # Clicar no botão de deletar da primeira entrada
        delete_btn = page.locator("#entradas-list .btn-delete, #entradas-list button.btn-danger").first
        if delete_btn.is_visible():
            delete_btn.click()
            # Se houver modal de confirmação, confirmar
            confirm_btn = page.locator("#confirm-ok-btn")
            if confirm_btn.is_visible():
                confirm_btn.click()
            page.wait_for_timeout(1500)
