"""
Testes E2E — CRUD de Consumo Pessoal.

Cobre:
  • Verificar que aba está oculta por padrão
  • Habilitar aba via admin
  • Registrar consumo pessoal
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


def _enable_consumo(page):
    """Helper: habilita a aba de consumo via painel admin."""
    page.click('li[data-tab="admin"]')
    page.wait_for_timeout(500)
    
    # Marcar checkbox de consumo habilitado
    checkbox = page.locator("#config-consumo-habilitado")
    if not checkbox.is_checked():
        checkbox.check()
    
    page.click('#form-configuracoes button[type="submit"]')
    page.wait_for_timeout(1500)


class TestConsumoVisibility:
    """Testes de visibilidade da aba de consumo."""

    def test_consumo_hidden_by_default(self, authenticated_page):
        """Aba de consumo deve estar oculta por padrão."""
        page = authenticated_page
        nav_consumo = page.locator('li[data-tab="consumo"]')
        
        # Verificar se está oculta (display: none ou não visível)
        is_hidden = not nav_consumo.is_visible() or nav_consumo.get_attribute("style") == "display: none;"
        assert is_hidden, "Aba de consumo deveria estar oculta por padrão"

    def test_consumo_visible_after_enable(self, authenticated_page):
        """Aba de consumo deve aparecer após ser habilitada pelo admin."""
        page = authenticated_page
        _enable_consumo(page)
        
        page.wait_for_timeout(500)
        nav_consumo = page.locator('li[data-tab="consumo"]')
        assert nav_consumo.is_visible(), "Aba de consumo deveria estar visível após habilitação"


class TestConsumoForm:
    """Testes do formulário de consumo pessoal."""

    def test_consumo_form_visible(self, authenticated_page):
        """Formulário de consumo deve estar visível após habilitação."""
        page = authenticated_page
        _enable_consumo(page)
        
        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)

        assert page.locator("#form-consumo").is_visible()
        assert page.locator("#consumo-quantidade").is_visible()
        assert page.locator("#consumo-observacao").is_visible()

    def test_registrar_consumo(self, authenticated_page):
        """Deve registrar consumo pessoal."""
        page = authenticated_page
        _add_stock(page, 50)
        _enable_consumo(page)

        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)

        page.fill("#consumo-quantidade", "4")
        page.fill("#consumo-observacao", "Café da manhã - teste Playwright")
        page.click('#form-consumo button[type="submit"]')

        # Toast de sucesso
        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        page.wait_for_timeout(1000)
        
        # Verificar se aparece na lista de hoje
        consumo_hoje = page.locator("#consumo-hoje-list")
        text = consumo_hoje.inner_text()
        assert "4" in text, "Quantidade deveria aparecer na lista"

    def test_consumo_reduz_estoque(self, authenticated_page):
        """Consumo pessoal deve reduzir o estoque."""
        page = authenticated_page
        _add_stock(page, 60)
        _enable_consumo(page)

        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_before = int(page.locator("#stock-quantity").inner_text())

        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)
        page.fill("#consumo-quantidade", "6")
        page.fill("#consumo-observacao", "Teste redução de estoque")
        page.click('#form-consumo button[type="submit"]')
        page.wait_for_timeout(1500)

        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_after = int(page.locator("#stock-quantity").inner_text())

        assert stock_after == stock_before - 6, f"Estoque deveria reduzir de {stock_before} para {stock_before - 6}, mas está em {stock_after}"

    def test_consumo_month_total(self, authenticated_page):
        """Total de consumo no mês deve atualizar."""
        page = authenticated_page
        _add_stock(page, 50)
        _enable_consumo(page)

        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)

        page.fill("#consumo-quantidade", "8")
        page.fill("#consumo-observacao", "Teste total mensal")
        page.click('#form-consumo button[type="submit"]')
        page.wait_for_timeout(1500)

        # Verificar total do mês
        total_mes = page.locator("#consumo-mes-total")
        total_text = total_mes.inner_text()
        # Extrair número do texto (pode ser "8 ovos" ou similar)
        import re
        match = re.search(r'(\d+)', total_text)
        if match:
            total_value = int(match.group(1))
            assert total_value >= 8, f"Total do mês deveria ser >= 8, mas é {total_value}"

    def test_consumo_sem_observacao(self, authenticated_page):
        """Deve permitir registrar consumo sem observação."""
        page = authenticated_page
        _add_stock(page, 30)
        _enable_consumo(page)

        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)

        page.fill("#consumo-quantidade", "2")
        # Não preencher observação
        page.click('#form-consumo button[type="submit"]')

        # Toast de sucesso
        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        page.wait_for_timeout(1000)
        
        # Verificar se foi registrado
        consumo_hoje = page.locator("#consumo-hoje-list")
        text = consumo_hoje.inner_text()
        assert "2" in text


class TestConsumoDelete:
    """Testes de remoção de registros de consumo."""

    def test_desfazer_consumo(self, authenticated_page):
        """Deve ser possível desfazer um registro de consumo."""
        page = authenticated_page
        _add_stock(page, 40)
        _enable_consumo(page)

        # Verificar estoque inicial
        page.click('li[data-tab="estoque"]')
        page.wait_for_timeout(1000)
        stock_before = int(page.locator("#stock-quantity").inner_text())

        # Registrar consumo
        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)
        page.fill("#consumo-quantidade", "3")
        page.click('#form-consumo button[type="submit"]')
        page.wait_for_timeout(1500)

        # Desfazer
        undo_btn = page.locator("#consumo-hoje-list .btn-undo, #consumo-hoje-list button").first
        if undo_btn.is_visible():
            undo_btn.click()
            
            # Confirmar no modal se aparecer
            page.wait_for_timeout(500)
            confirm = page.locator("#confirm-ok-btn")
            if confirm.is_visible():
                confirm.click()
            
            page.wait_for_timeout(1500)

            # Verificar se estoque foi restaurado
            page.click('li[data-tab="estoque"]')
            page.wait_for_timeout(1000)
            stock_after = int(page.locator("#stock-quantity").inner_text())
            
            assert stock_after == stock_before, f"Estoque deveria voltar para {stock_before}, mas está em {stock_after}"

    def test_consumo_mostra_usuario(self, authenticated_page):
        """Registro de consumo deve mostrar o usuário que registrou."""
        page = authenticated_page
        _add_stock(page, 50)
        _enable_consumo(page)

        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)

        page.fill("#consumo-quantidade", "5")
        page.fill("#consumo-observacao", "Teste usuário")
        page.click('#form-consumo button[type="submit"]')
        page.wait_for_timeout(1500)

        consumo_list = page.locator("#consumo-hoje-list")
        text = consumo_list.inner_text()
        
        # Deve conter alguma referência ao usuário (admin ou similar)
        assert "admin" in text.lower() or "administrador" in text.lower()


class TestConsumoValidation:
    """Testes de validação do formulário de consumo."""

    def test_consumo_quantidade_invalida(self, authenticated_page):
        """Deve validar quantidade inválida (HTML5 validation com min=1)."""
        page = authenticated_page
        _add_stock(page, 20)
        _enable_consumo(page)

        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)

        # O campo tem min="1" no HTML, então o navegador impede valores menores
        # Vamos verificar que o atributo min está presente
        input_field = page.locator("#consumo-quantidade")
        min_attr = input_field.get_attribute("min")
        assert min_attr == "1", "Campo quantidade deve ter min='1'"
        
        # Tentar preencher com valor negativo (não bloqueado por min mas inválido)
        # Remove o atributo min para testar a validação JS
        page.evaluate("document.getElementById('consumo-quantidade').removeAttribute('min')")
        
        # Aguardar toasts antigos desaparecerem
        page.wait_for_timeout(4000)
        
        # Tentar quantidade zero
        page.fill("#consumo-quantidade", "0")
        page.click('#form-consumo button[type="submit"]')
        
        # Esperar especificamente por um toast aparecer
        toast = page.locator("#toast-container .toast").first
        toast.wait_for(state="visible", timeout=5000)
        
        # Verificar o texto
        text = toast.inner_text()
        assert "positivo" in text.lower() or "número" in text.lower(), f"Toast inesperado: {text}"

    def test_consumo_estoque_insuficiente(self, authenticated_page):
        """Deve validar estoque insuficiente."""
        page = authenticated_page
        _add_stock(page, 5)  # Apenas 5 ovos
        _enable_consumo(page)

        page.click('li[data-tab="consumo"]')
        page.wait_for_timeout(500)

        # Aguardar toasts antigos desaparecerem
        page.wait_for_timeout(4000)

        # Tentar consumir mais que o disponível
        page.fill("#consumo-quantidade", "10")
        page.click('#form-consumo button[type="submit"]')
        
        # Aguardar novo toast aparecer
        page.wait_for_timeout(500)

        # Verificar mensagem de erro - procurar por toast que contenha "insuficiente"
        toast = page.locator("#toast-container .toast:has-text('insuficiente')")
        toast.wait_for(state="visible", timeout=5000)
        text = toast.inner_text()
        assert "insuficiente" in text.lower()
