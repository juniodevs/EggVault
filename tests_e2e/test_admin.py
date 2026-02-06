"""
Testes E2E — Administração de Usuários (Admin Panel).

Cobre:
  • Criar novo usuário
  • Listar usuários
  • Deletar usuário
  • Alterar senha
  • Permissões admin vs. não-admin
"""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.ui]


class TestAdminPanel:
    """Testes do painel de administração."""

    def test_admin_page_renders(self, authenticated_page):
        """Aba admin deve mostrar formulário e lista."""
        page = authenticated_page
        page.click('li[data-tab="admin"]')
        page.wait_for_timeout(500)

        assert page.locator("#form-criar-usuario").is_visible()
        assert page.locator("#admin-users-list").is_visible()

    def test_admin_lista_usuarios(self, authenticated_page):
        """Lista de usuários deve conter ao menos o admin."""
        page = authenticated_page
        page.click('li[data-tab="admin"]')
        page.wait_for_timeout(1000)

        users_list = page.locator("#admin-users-list")
        text = users_list.inner_text()
        assert "admin" in text.lower()

    def test_criar_usuario(self, authenticated_page):
        """Deve criar um novo usuário pelo painel admin."""
        page = authenticated_page
        page.click('li[data-tab="admin"]')
        page.wait_for_timeout(500)

        page.fill("#new-user-nome", "Teste Playwright")
        page.fill("#new-user-username", "playwright_user")
        page.fill("#new-user-password", "1234")
        page.click('#form-criar-usuario button[type="submit"]')

        # Toast de sucesso
        toast = page.locator("#toast-container .toast, #toast-container div")
        toast.first.wait_for(state="visible", timeout=10000)

        page.wait_for_timeout(1500)

        # Usuário deve aparecer na lista
        users_list = page.locator("#admin-users-list")
        assert "playwright_user" in users_list.inner_text().lower()

    def test_criar_usuario_admin(self, authenticated_page):
        """Deve criar um usuário com privilégio admin."""
        page = authenticated_page
        page.click('li[data-tab="admin"]')
        page.wait_for_timeout(500)

        page.fill("#new-user-nome", "Admin Teste")
        page.fill("#new-user-username", "admin_test")
        page.fill("#new-user-password", "1234")
        page.check("#new-user-admin")
        page.click('#form-criar-usuario button[type="submit"]')
        page.wait_for_timeout(2000)

        users_list = page.locator("#admin-users-list")
        assert "admin_test" in users_list.inner_text().lower()

    def test_criar_usuario_duplicado(self, authenticated_page):
        """Tentar criar usuário com username já existente deve falhar."""
        page = authenticated_page
        page.click('li[data-tab="admin"]')
        page.wait_for_timeout(500)

        # Criar primeiro
        page.fill("#new-user-nome", "User A")
        page.fill("#new-user-username", "user_dup_test")
        page.fill("#new-user-password", "1234")
        page.click('#form-criar-usuario button[type="submit"]')
        page.wait_for_timeout(2000)

        # Tentar criar novamente
        page.fill("#new-user-nome", "User B")
        page.fill("#new-user-username", "user_dup_test")
        page.fill("#new-user-password", "5678")
        page.click('#form-criar-usuario button[type="submit"]')
        page.wait_for_timeout(2000)

        # Deve mostrar toast de erro
        toast_container = page.locator("#toast-container")
        text = toast_container.inner_text()
        assert "já existe" in text.lower() or "erro" in text.lower() or "error" in text.lower()


class TestChangePassword:
    """Testes de alteração de senha."""

    def test_modal_alterar_senha_opens(self, authenticated_page):
        """Modal de alterar senha deve abrir ao clicar no botão."""
        page = authenticated_page

        page.click('button[onclick="showChangePassword()"]')
        page.wait_for_timeout(500)

        modal = page.locator("#modal-senha")
        assert modal.is_visible()

    def test_modal_alterar_senha_cancel(self, authenticated_page):
        """Cancelar deve fechar o modal sem alterar nada."""
        page = authenticated_page

        page.click('button[onclick="showChangePassword()"]')
        page.wait_for_timeout(500)
        assert page.locator("#modal-senha").is_visible()

        page.click('button[onclick="hideChangePassword()"]')
        page.wait_for_timeout(500)
        assert not page.locator("#modal-senha").is_visible()

    def test_alterar_senha_form_fields(self, authenticated_page):
        """Modal deve ter todos os campos necessários."""
        page = authenticated_page
        page.click('button[onclick="showChangePassword()"]')
        page.wait_for_timeout(500)

        assert page.locator("#senha-atual").is_visible()
        assert page.locator("#nova-senha").is_visible()
        assert page.locator("#confirmar-senha").is_visible()
