"""
Testes E2E — Autenticação e Login.

Cobre:
  • Login com credenciais válidas
  • Login com credenciais inválidas
  • Exibição de erros de login
  • Logout
  • Sessão mantida após refresh
  • Proteção de rotas (redirect p/ login)
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


class TestLoginPage:
    """Testes da tela de login."""

    def test_login_page_renders(self, page, live_server):
        """Página de login deve aparecer ao acessar a app sem autenticação."""
        page.goto("/")
        overlay = page.locator("#login-overlay")
        assert overlay.is_visible()
        assert page.locator("#login-username").is_visible()
        assert page.locator("#login-password").is_visible()
        assert page.locator("#btn-login").is_visible()

    def test_login_page_title(self, page, live_server):
        """Título da página deve conter EggVault."""
        page.goto("/")
        assert "EggVault" in page.title()

    def test_login_page_has_default_hint(self, page, live_server):
        """Deve mostrar dica de primeiro acesso (admin/admin)."""
        page.goto("/")
        hint = page.locator(".login-footer")
        assert hint.is_visible()
        assert "admin" in hint.inner_text().lower()

    def test_login_successful(self, page, live_server):
        """Login com admin/admin deve funcionar e esconder overlay."""
        page.goto("/")
        page.fill("#login-username", "admin")
        page.fill("#login-password", "admin")
        page.click("#btn-login")

        # Overlay deve sumir (display:none via classe .hidden)
        page.wait_for_selector("#login-overlay", state="hidden", timeout=15000)
        
        # Aguarda e fecha modal de changelog se aparecer
        page.wait_for_timeout(1500)
        try:
            if page.locator("#modal-changelog").is_visible():
                page.locator(".btn-close-changelog").click()
                page.wait_for_selector("#modal-changelog", state="hidden", timeout=3000)
        except:
            pass
        
        assert not page.locator("#login-overlay").is_visible()

    def test_login_shows_username_in_sidebar(self, authenticated_page):
        """Após login, sidebar deve mostrar o nome do usuário."""
        sidebar_user = authenticated_page.locator("#sidebar-username")
        text = sidebar_user.inner_text()
        assert len(text) > 0
        assert text != "—"

    def test_login_invalid_password(self, page, live_server):
        """Login com senha errada deve exibir erro."""
        page.goto("/")
        page.fill("#login-username", "admin")
        page.fill("#login-password", "senha_errada")
        page.click("#btn-login")

        error_div = page.locator("#login-error")
        error_div.wait_for(state="visible", timeout=10000)
        assert error_div.is_visible()

    def test_login_empty_fields(self, page, live_server):
        """Submit com campos vazios não deve fazer login."""
        page.goto("/")
        # Tentar submeter sem preencher — HTML5 validation deve bloquear
        page.click("#btn-login")
        # O overlay de login deve continuar visível
        assert page.locator("#login-overlay").is_visible()

    def test_login_nonexistent_user(self, page, live_server):
        """Login com usuário inexistente deve exibir erro."""
        page.goto("/")
        page.fill("#login-username", "usuario_fantasma")
        page.fill("#login-password", "qualquer")
        page.click("#btn-login")

        error_div = page.locator("#login-error")
        error_div.wait_for(state="visible", timeout=10000)
        assert error_div.is_visible()


class TestLogout:
    """Testes de logout."""

    def test_logout_redirects_to_login(self, authenticated_page):
        """Logout deve exibir a tela de login novamente."""
        authenticated_page.click(".btn-logout")
        authenticated_page.wait_for_selector("#login-overlay", state="visible", timeout=10000)
        assert authenticated_page.locator("#login-overlay").is_visible()


class TestSessionPersistence:
    """Testes de persistência de sessão."""

    def test_session_survives_refresh(self, authenticated_page):
        """Sessão deve persistir após refresh da página."""
        authenticated_page.reload()
        # Aguarda o conteúdo principal carregar (overlay deve continuar hidden)
        authenticated_page.wait_for_timeout(3000)
        overlay = authenticated_page.locator("#login-overlay")
        assert not overlay.is_visible(), "Overlay de login reapareceu após refresh"

    def test_admin_tab_visible_for_admin(self, authenticated_page):
        """Aba Admin deve estar visível para usuário admin."""
        nav_admin = authenticated_page.locator("#nav-admin")
        assert nav_admin.is_visible()
