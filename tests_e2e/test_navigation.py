"""
Testes E2E — Navegação e UI.

Cobre:
  • Navegação entre abas (sidebar)
  • Elementos visuais de cada aba
  • Menu mobile
  • Responsividade básica
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


class TestSidebar:
    """Testes da barra lateral de navegação."""

    def test_sidebar_visible(self, authenticated_page):
        """Sidebar deve estar visível após login."""
        sidebar = authenticated_page.locator("#sidebar")
        assert sidebar.is_visible()

    def test_sidebar_has_all_tabs(self, authenticated_page):
        """Sidebar deve conter todas as abas principais."""
        tabs = ["estoque", "entradas", "vendas", "quebrados", "precos", "relatorios"]
        for tab in tabs:
            link = authenticated_page.locator(f'li[data-tab="{tab}"]')
            assert link.is_visible(), f"Aba '{tab}' não está visível na sidebar"

    def test_default_tab_is_estoque(self, authenticated_page):
        """Aba padrão após login deve ser Estoque."""
        estoque_tab = authenticated_page.locator('li[data-tab="estoque"]')
        assert "active" in (estoque_tab.get_attribute("class") or "")
        assert authenticated_page.locator("#tab-estoque").is_visible()

    def test_navigate_to_entradas(self, authenticated_page):
        """Clicar em Entradas deve mostrar a aba de entradas."""
        authenticated_page.click('li[data-tab="entradas"]')
        authenticated_page.wait_for_timeout(500)
        assert authenticated_page.locator("#tab-entradas").is_visible()
        assert not authenticated_page.locator("#tab-estoque").is_visible()

    def test_navigate_to_vendas(self, authenticated_page):
        """Clicar em Vendas deve mostrar a aba de vendas."""
        authenticated_page.click('li[data-tab="vendas"]')
        authenticated_page.wait_for_timeout(500)
        assert authenticated_page.locator("#tab-vendas").is_visible()

    def test_navigate_to_quebrados(self, authenticated_page):
        """Clicar em Quebrados deve mostrar a aba de quebrados."""
        authenticated_page.click('li[data-tab="quebrados"]')
        authenticated_page.wait_for_timeout(500)
        assert authenticated_page.locator("#tab-quebrados").is_visible()

    def test_navigate_to_precos(self, authenticated_page):
        """Clicar em Preços deve mostrar a aba de preços."""
        authenticated_page.click('li[data-tab="precos"]')
        authenticated_page.wait_for_timeout(500)
        assert authenticated_page.locator("#tab-precos").is_visible()

    def test_navigate_to_relatorios(self, authenticated_page):
        """Clicar em Relatórios deve mostrar a aba de relatórios."""
        authenticated_page.click('li[data-tab="relatorios"]')
        authenticated_page.wait_for_timeout(500)
        assert authenticated_page.locator("#tab-relatorios").is_visible()

    def test_navigate_to_admin(self, authenticated_page):
        """Clicar em Admin deve mostrar a aba de administração."""
        authenticated_page.click('li[data-tab="admin"]')
        authenticated_page.wait_for_timeout(500)
        assert authenticated_page.locator("#tab-admin").is_visible()

    def test_active_tab_highlight(self, authenticated_page):
        """Tab ativa deve ter classe 'active'."""
        authenticated_page.click('li[data-tab="vendas"]')
        authenticated_page.wait_for_timeout(300)

        vendas_li = authenticated_page.locator('li[data-tab="vendas"]')
        assert "active" in (vendas_li.get_attribute("class") or "")

        estoque_li = authenticated_page.locator('li[data-tab="estoque"]')
        assert "active" not in (estoque_li.get_attribute("class") or "")

    def test_navigate_back_and_forth(self, authenticated_page):
        """Deve ser possível navegar entre abas sem problemas."""
        page = authenticated_page
        tabs = ["entradas", "vendas", "quebrados", "precos", "relatorios", "estoque"]

        for tab in tabs:
            page.click(f'li[data-tab="{tab}"]')
            page.wait_for_timeout(300)
            assert page.locator(f"#tab-{tab}").is_visible(), f"Aba {tab} não ficou visível"


class TestEstoquePage:
    """Testes da aba de Estoque."""

    def test_stock_card_visible(self, authenticated_page):
        """Card principal de estoque deve estar visível."""
        card = authenticated_page.locator("#stock-main-card")
        assert card.is_visible()

    def test_stock_quantity_displayed(self, authenticated_page):
        """Quantidade do estoque deve ser exibida."""
        qty = authenticated_page.locator("#stock-quantity")
        assert qty.is_visible()
        # Valor deve ser numérico
        text = qty.inner_text()
        assert text.isdigit()

    def test_stats_grid_visible(self, authenticated_page):
        """Grid de estatísticas deve conter todos os cards."""
        stats = authenticated_page.locator(".stat-card")
        assert stats.count() >= 4

    def test_last_update_visible(self, authenticated_page):
        """Informação de última atualização deve aparecer."""
        update = authenticated_page.locator("#last-update")
        assert update.is_visible()


class TestMobileResponsive:
    """Testes de layout mobile."""

    def test_mobile_menu_button_visible_on_small_screen(self, context, live_server):
        """Botão de menu mobile deve aparecer em tela pequena."""
        mobile_ctx = context.browser.new_context(
            viewport={"width": 375, "height": 667},
            base_url=live_server,
        )
        pg = mobile_ctx.new_page()
        pg.goto("/")

        # Login
        pg.fill("#login-username", "admin")
        pg.fill("#login-password", "admin")
        pg.click("#btn-login")
        pg.wait_for_selector("#login-overlay", state="hidden", timeout=15000)

        btn = pg.locator("#mobile-menu-btn")
        assert btn.is_visible()

        pg.close()
        mobile_ctx.close()

    def test_sidebar_hidden_on_mobile(self, context, live_server):
        """Sidebar deve estar oculta por padrão em tela mobile."""
        mobile_ctx = context.browser.new_context(
            viewport={"width": 375, "height": 667},
            base_url=live_server,
        )
        pg = mobile_ctx.new_page()
        pg.goto("/")

        pg.fill("#login-username", "admin")
        pg.fill("#login-password", "admin")
        pg.click("#btn-login")
        pg.wait_for_selector("#login-overlay", state="hidden", timeout=15000)

        sidebar = pg.locator("#sidebar")
        # Em mobile, sidebar não deve ter a classe "open" por padrão
        classes = sidebar.get_attribute("class") or ""
        assert "open" not in classes

        pg.close()
        mobile_ctx.close()
