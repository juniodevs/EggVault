"""
Testes E2E — Segurança.

Cobre:
  • Proteção de endpoints sem autenticação
  • Token inválido/expirado
  • XSS (Cross-Site Scripting)
  • Injeção SQL
  • CSRF / manipulação de headers
  • Rate limiting conceptual
  • Cookie security flags
  • Acesso admin restrito
  • Enumeração de usuários
  • Brute-force protection conceptual
"""

import pytest
import json

pytestmark = [pytest.mark.e2e, pytest.mark.security]


class TestUnauthorizedAccess:
    """Testes de acesso não-autenticado a endpoints protegidos."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/estoque"),
        ("GET", "/api/entradas"),
        ("POST", "/api/entradas"),
        ("GET", "/api/saidas"),
        ("POST", "/api/saidas"),
        ("GET", "/api/precos"),
        ("POST", "/api/precos"),
        ("GET", "/api/quebrados"),
        ("POST", "/api/quebrados"),
        ("GET", "/api/relatorio"),
        ("GET", "/api/relatorio/anual"),
        ("GET", "/api/meses"),
        ("GET", "/api/export/excel"),
        ("GET", "/api/export/pdf"),
        ("GET", "/api/admin/usuarios"),
        ("POST", "/api/admin/usuarios"),
    ]

    @pytest.mark.parametrize("method,endpoint", PROTECTED_ENDPOINTS)
    def test_endpoint_requires_auth(self, page, live_server, method, endpoint):
        """Endpoints protegidos devem retornar 401 sem token."""
        if method == "GET":
            response = page.request.get(f"{live_server}{endpoint}")
        else:
            response = page.request.post(
                f"{live_server}{endpoint}",
                data=json.dumps({"test": True}),
                headers={"Content-Type": "application/json"},
            )

        assert response.status == 401, f"{method} {endpoint} deveria retornar 401, retornou {response.status}"
        body = response.json()
        assert body.get("auth_required") is True or body.get("success") is False

    def test_invalid_token_rejected(self, page, live_server):
        """Token inválido deve ser rejeitado."""
        response = page.request.get(
            f"{live_server}/api/estoque",
            headers={"Authorization": "Bearer token_invalido_12345"},
        )
        assert response.status == 401

    def test_empty_bearer_rejected(self, page, live_server):
        """Bearer vazio deve ser rejeitado."""
        response = page.request.get(
            f"{live_server}/api/estoque",
            headers={"Authorization": "Bearer "},
        )
        assert response.status == 401

    def test_no_auth_header_rejected(self, page, live_server):
        """Requisição sem header de auth deve ser rejeitada."""
        response = page.request.get(f"{live_server}/api/estoque")
        assert response.status == 401


class TestAdminOnlyEndpoints:
    """Testes de endpoints exclusivos de admin usando usuário normal."""

    ADMIN_ENDPOINTS = [
        ("GET", "/api/admin/usuarios"),
        ("POST", "/api/admin/usuarios"),
    ]

    def _create_normal_user_token(self, page, live_server):
        """Cria um user normal e retorna o token."""
        # Login como admin
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        admin_token = res.json()["data"]["token"]

        # Criar usuário normal
        page.request.post(
            f"{live_server}/api/admin/usuarios",
            data=json.dumps({
                "username": "normal_sec_test",
                "password": "1234",
                "nome": "Normal User",
                "is_admin": False,
            }),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}",
            },
        )

        # Login como normal
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "normal_sec_test", "password": "1234"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    @pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
    def test_admin_endpoint_blocked_for_normal_user(self, page, live_server, method, endpoint):
        """Usuário normal não deve acessar endpoints de admin."""
        token = self._create_normal_user_token(page, live_server)

        if method == "GET":
            response = page.request.get(
                f"{live_server}{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
            )
        else:
            response = page.request.post(
                f"{live_server}{endpoint}",
                data=json.dumps({"username": "hack", "password": "1234", "nome": "Hack"}),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )

        assert response.status == 403


class TestXSSProtection:
    """Testes de proteção contra Cross-Site Scripting."""

    XSS_PAYLOADS = [
        '<script>alert("xss")</script>',
        '"><img src=x onerror=alert(1)>',
        "javascript:alert('xss')",
        '<svg onload=alert(1)>',
        "'-alert(1)-'",
        '<iframe src="javascript:alert(1)">',
    ]

    def _get_admin_token(self, page, live_server):
        """Helper para obter token admin."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_entrada_observacao(self, page, live_server, payload):
        """Payloads XSS em observação de entrada não devem ser executados."""
        token = self._get_admin_token(page, live_server)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        # Registrar entrada com payload XSS
        page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 1, "observacao": payload}),
            headers=headers,
        )

        # Navegar e verificar que o payload não é executado
        page.goto(live_server)
        page.fill("#login-username", "admin")
        page.fill("#login-password", "admin")
        page.click("#btn-login")
        page.wait_for_selector("#login-overlay", state="hidden", timeout=15000)
        
        # Aguarda e fecha modal de changelog se aparecer
        page.wait_for_timeout(1500)
        try:
            if page.locator("#modal-changelog").is_visible():
                page.locator(".btn-close-changelog").click()
                page.wait_for_selector("#modal-changelog", state="hidden", timeout=3000)
        except:
            pass

        page.click('li[data-tab="entradas"]')
        page.wait_for_timeout(1000)

        # Verificar que não há alert / script executado
        # Se o XSS fosse executado, poderia haver um dialog
        # Playwright permite interceptar dialogs
        dialog_appeared = False

        def handle_dialog(dialog):
            nonlocal dialog_appeared
            dialog_appeared = True
            dialog.dismiss()

        page.on("dialog", handle_dialog)
        page.wait_for_timeout(1000)

        assert not dialog_appeared, f"XSS executado com payload: {payload}"

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_quebrado_motivo(self, page, live_server, payload):
        """Payloads XSS em motivo de quebra não devem ser executados."""
        token = self._get_admin_token(page, live_server)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        # Adicionar estoque primeiro
        page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 10}),
            headers=headers,
        )

        # Registrar quebrado com payload XSS
        page.request.post(
            f"{live_server}/api/quebrados",
            data=json.dumps({"quantidade": 1, "motivo": payload}),
            headers=headers,
        )

        page.goto(live_server)
        page.fill("#login-username", "admin")
        page.fill("#login-password", "admin")
        page.click("#btn-login")
        page.wait_for_selector("#login-overlay", state="hidden", timeout=15000)
        
        # Aguarda e fecha modal de changelog se aparecer
        page.wait_for_timeout(1500)
        try:
            if page.locator("#modal-changelog").is_visible():
                page.locator(".btn-close-changelog").click()
                page.wait_for_selector("#modal-changelog", state="hidden", timeout=3000)
        except:
            pass

        page.click('li[data-tab="quebrados"]')
        page.wait_for_timeout(1000)

        dialog_appeared = False

        def handle_dialog(dialog):
            nonlocal dialog_appeared
            dialog_appeared = True
            dialog.dismiss()

        page.on("dialog", handle_dialog)
        page.wait_for_timeout(1000)

        assert not dialog_appeared, f"XSS executado com payload: {payload}"


class TestSQLInjection:
    """Testes de proteção contra SQL Injection."""

    SQL_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE usuarios; --",
        "1; SELECT * FROM usuarios --",
        "' UNION SELECT username, password_hash FROM usuarios --",
        "admin'--",
        "1 OR 1=1",
    ]

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_injection_login_username(self, page, live_server, payload):
        """SQL injection no username do login não deve funcionar."""
        response = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": payload, "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )

        body = response.json()
        # Não deve fazer login com sucesso
        assert not body.get("success") or response.status != 200

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_injection_login_password(self, page, live_server, payload):
        """SQL injection na senha do login não deve funcionar."""
        response = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": payload}),
            headers={"Content-Type": "application/json"},
        )

        body = response.json()
        assert not body.get("success") or response.status != 200

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_injection_in_observacao(self, page, live_server, payload):
        """SQL injection em campos de texto não deve causar erro 500."""
        # Login primeiro
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        token = res.json()["data"]["token"]

        response = page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 1, "observacao": payload}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        # Não deve retornar 500 (server error)
        assert response.status != 500, f"SQL injection causou erro 500 com payload: {payload}"


class TestCookieSecurity:
    """Testes de segurança de cookies."""

    def test_auth_cookie_httponly(self, page, live_server):
        """Cookie auth_token deve ter flag httponly."""
        response = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )

        # Verificar headers de Set-Cookie
        cookies_header = response.headers.get("set-cookie", "")
        if "auth_token" in cookies_header:
            assert "httponly" in cookies_header.lower(), "Cookie auth_token não tem flag HttpOnly"

    def test_auth_cookie_samesite(self, page, live_server):
        """Cookie auth_token deve ter SameSite=Strict."""
        response = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )

        cookies_header = response.headers.get("set-cookie", "")
        if "auth_token" in cookies_header:
            assert "samesite" in cookies_header.lower(), "Cookie auth_token não tem SameSite"


class TestInputValidation:
    """Testes de validação de inputs via API."""

    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    def test_entrada_quantidade_negativa(self, page, live_server):
        """Quantidade negativa na entrada deve ser rejeitada."""
        token = self._get_token(page, live_server)
        response = page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": -10}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status in [400, 500]

    def test_entrada_quantidade_zero(self, page, live_server):
        """Quantidade zero na entrada deve ser rejeitada."""
        token = self._get_token(page, live_server)
        response = page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 0}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status in [400, 500]

    def test_entrada_quantidade_string(self, page, live_server):
        """Quantidade como string inválida deve ser rejeitada."""
        token = self._get_token(page, live_server)
        response = page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": "abc"}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status in [400, 500]

    def test_venda_preco_negativo(self, page, live_server):
        """Preço negativo na venda deve ser rejeitado."""
        token = self._get_token(page, live_server)

        # Adicionar estoque
        page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 10}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        response = page.request.post(
            f"{live_server}/api/saidas",
            data=json.dumps({"quantidade": 1, "preco_unitario": -5.0}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status in [400, 500]

    def test_criar_usuario_senha_curta(self, page, live_server):
        """Senha menor que 4 caracteres deve ser recusada."""
        token = self._get_token(page, live_server)
        response = page.request.post(
            f"{live_server}/api/admin/usuarios",
            data=json.dumps({
                "username": "short_pwd_test",
                "password": "12",
                "nome": "Short Pass",
            }),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status == 400

    def test_criar_usuario_username_curto(self, page, live_server):
        """Username menor que 3 caracteres deve ser recusado."""
        token = self._get_token(page, live_server)
        response = page.request.post(
            f"{live_server}/api/admin/usuarios",
            data=json.dumps({
                "username": "ab",
                "password": "1234",
                "nome": "Short User",
            }),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status == 400

    def test_empty_json_body(self, page, live_server):
        """Body vazio deve retornar 400."""
        token = self._get_token(page, live_server)
        response = page.request.post(
            f"{live_server}/api/entradas",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status in [400, 500]

    def test_deletar_ultimo_admin_proibido(self, page, live_server):
        """Não deve ser possível deletar o último admin."""
        token = self._get_token(page, live_server)

        # Obter lista de usuários
        res = page.request.get(
            f"{live_server}/api/admin/usuarios",
            headers={"Authorization": f"Bearer {token}"},
        )
        users = res.json()["data"]
        admin_user = next(u for u in users if u["username"] == "admin")

        # Tentar deletar
        response = page.request.delete(
            f"{live_server}/api/admin/usuarios/{admin_user['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status == 400
        assert "último" in response.json().get("error", "").lower() or "admin" in response.json().get("error", "").lower()


class TestSessionSecurity:
    """Testes de segurança de sessão."""

    def test_logout_invalidates_token(self, page, live_server):
        """Após logout, o token deve ser inválido."""
        # Login
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        token = res.json()["data"]["token"]

        # Logout
        page.request.post(
            f"{live_server}/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Tentar acessar com o token
        res = page.request.get(
            f"{live_server}/api/estoque",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 401

    def test_alterar_senha_invalida_sessoes(self, page, live_server):
        """Alterar senha deve invalidar todas as sessões."""
        # Login
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        token = res.json()["data"]["token"]

        # Alterar senha
        page.request.post(
            f"{live_server}/api/auth/alterar-senha",
            data=json.dumps({"senha_atual": "admin", "nova_senha": "nova1234"}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        # Token antigo deve ser inválido
        res = page.request.get(
            f"{live_server}/api/estoque",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 401

        # Restaurar senha para outros testes
        res2 = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "nova1234"}),
            headers={"Content-Type": "application/json"},
        )
        token2 = res2.json()["data"]["token"]
        page.request.post(
            f"{live_server}/api/auth/alterar-senha",
            data=json.dumps({"senha_atual": "nova1234", "nova_senha": "admin"}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token2}",
            },
        )

class TestMesValidation:
    """Endpoints com parâmetro ?mes= devem rejeitar formatos inválidos com 400."""

    INVALID_MES = [
        "invalid",
        "2025",
        "2025-13",       # mês 13 não existe
        "2025-00",       # mês 00 não existe
        "25-01",         # ano com 2 dígitos
        "abcd-01",       # ano não numérico
        "2025-1",        # mês sem zero à esquerda
        "2025/01",       # separador errado
        "' OR 1=1 --",   # SQL injection attempt
    ]

    VALID_MES = "2025-01"

    ENDPOINTS_WITH_MES = [
        "/api/entradas",
        "/api/saidas",
        "/api/quebrados",
        "/api/consumo",
        "/api/despesas",
        "/api/relatorio",
    ]

    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    @pytest.mark.parametrize("mes", INVALID_MES)
    @pytest.mark.parametrize("endpoint", ENDPOINTS_WITH_MES)
    def test_invalid_mes_returns_400(self, page, live_server, endpoint, mes):
        """Formato de mês inválido deve retornar 400."""
        token = self._get_token(page, live_server)
        res = page.request.get(
            f"{live_server}{endpoint}?mes={mes}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 400, (
            f"{endpoint}?mes={mes} retornou {res.status}, esperado 400"
        )
        body = res.json()
        assert body["success"] is False

    @pytest.mark.parametrize("endpoint", ENDPOINTS_WITH_MES)
    def test_valid_mes_accepted(self, page, live_server, endpoint):
        """Formato de mês válido deve ser aceito (200)."""
        token = self._get_token(page, live_server)
        res = page.request.get(
            f"{live_server}{endpoint}?mes={self.VALID_MES}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 200, (
            f"{endpoint}?mes={self.VALID_MES} retornou {res.status}, esperado 200"
        )

    def test_export_excel_invalid_mes(self, page, live_server):
        """GET /api/export/excel com mês inválido deve retornar 400."""
        token = self._get_token(page, live_server)
        res = page.request.get(
            f"{live_server}/api/export/excel?mes=invalido",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 400

    def test_export_pdf_invalid_mes(self, page, live_server):
        """GET /api/export/pdf com mês inválido deve retornar 400."""
        token = self._get_token(page, live_server)
        res = page.request.get(
            f"{live_server}/api/export/pdf?mes=invalido",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 400


class TestAnoValidation:
    """Endpoints com parâmetro ?ano= devem rejeitar formatos inválidos com 400."""

    INVALID_ANO = [
        "invalid",
        "25",            # ano com 2 dígitos
        "abcd",          # não numérico
        "20255",         # 5 dígitos
        "' OR 1=1 --",  # SQL injection
    ]

    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    def test_relatorio_anual_invalid_ano(self, page, live_server):
        """GET /api/relatorio/anual com ano inválido deve retornar 400."""
        token = self._get_token(page, live_server)
        for ano in self.INVALID_ANO:
            res = page.request.get(
                f"{live_server}/api/relatorio/anual?ano={ano}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status == 400, f"ano={ano} retornou {res.status}, esperado 400"

    def test_relatorio_anual_valid_ano(self, page, live_server):
        """GET /api/relatorio/anual com ano válido deve ser aceito."""
        token = self._get_token(page, live_server)
        res = page.request.get(
            f"{live_server}/api/relatorio/anual?ano=2025",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 200

    def test_export_excel_anual_invalid_ano(self, page, live_server):
        """GET /api/export/excel-anual com ano inválido deve retornar 400."""
        token = self._get_token(page, live_server)
        res = page.request.get(
            f"{live_server}/api/export/excel-anual?ano=xx",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 400

class TestTextFieldLimits:
    """Campos de texto devem rejeitar valores muito longos (>500 chars)."""

    LONG_TEXT = "A" * 501  # 501 caracteres, acima do limite de 500

    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    def _auth_headers(self, token):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def test_entrada_observacao_too_long(self, page, live_server):
        """Observação de entrada com mais de 500 chars deve ser rejeitada."""
        token = self._get_token(page, live_server)
        res = page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 1, "observacao": self.LONG_TEXT}),
            headers=self._auth_headers(token),
        )
        assert res.status == 400
        body = res.json()
        assert body["success"] is False

    def test_entrada_observacao_at_limit(self, page, live_server):
        """Observação de entrada com exatamente 500 chars deve ser aceita."""
        token = self._get_token(page, live_server)
        text_at_limit = "B" * 500
        res = page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 1, "observacao": text_at_limit}),
            headers=self._auth_headers(token),
        )
        assert res.status == 200

    def test_quebrado_motivo_too_long(self, page, live_server):
        """Motivo de quebra com mais de 500 chars deve ser rejeitado."""
        token = self._get_token(page, live_server)
        page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 10}),
            headers=self._auth_headers(token),
        )
        res = page.request.post(
            f"{live_server}/api/quebrados",
            data=json.dumps({"quantidade": 1, "motivo": self.LONG_TEXT}),
            headers=self._auth_headers(token),
        )
        assert res.status == 400

    def test_consumo_observacao_too_long(self, page, live_server):
        """Observação de consumo com mais de 500 chars deve ser rejeitada."""
        token = self._get_token(page, live_server)
        page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 10}),
            headers=self._auth_headers(token),
        )
        res = page.request.post(
            f"{live_server}/api/consumo",
            data=json.dumps({"quantidade": 1, "observacao": self.LONG_TEXT}),
            headers=self._auth_headers(token),
        )
        assert res.status == 400

    def test_despesa_descricao_too_long(self, page, live_server):
        """Descrição de despesa com mais de 500 chars deve ser rejeitada."""
        token = self._get_token(page, live_server)
        res = page.request.post(
            f"{live_server}/api/despesas",
            data=json.dumps({
                "descricao": self.LONG_TEXT,
                "valor": 10.0,
            }),
            headers=self._auth_headers(token),
        )
        assert res.status == 400


class TestUserFieldLimits:
    """Username e nome de usuário devem respeitar limites de comprimento."""

    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    def _auth_headers(self, token):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def test_username_too_long(self, page, live_server):
        """Username com mais de 50 caracteres deve ser rejeitado."""
        token = self._get_token(page, live_server)
        res = page.request.post(
            f"{live_server}/api/admin/usuarios",
            data=json.dumps({
                "username": "u" * 51,
                "password": "1234",
                "nome": "Long Username",
            }),
            headers=self._auth_headers(token),
        )
        assert res.status == 400

    def test_nome_too_long(self, page, live_server):
        """Nome com mais de 100 caracteres deve ser rejeitado."""
        token = self._get_token(page, live_server)
        res = page.request.post(
            f"{live_server}/api/admin/usuarios",
            data=json.dumps({
                "username": "valid_user",
                "password": "1234",
                "nome": "N" * 101,
            }),
            headers=self._auth_headers(token),
        )
        assert res.status == 400

class TestCookieSecureFlag:
    """Verifica flags de segurança no cookie auth_token."""

    def test_auth_cookie_has_httponly(self, page, live_server):
        """Cookie auth_token deve ter flag HttpOnly."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        cookies_header = res.headers.get("set-cookie", "")
        if "auth_token" in cookies_header:
            assert "httponly" in cookies_header.lower(), "Cookie sem flag HttpOnly"

    def test_auth_cookie_has_samesite(self, page, live_server):
        """Cookie auth_token deve ter flag SameSite."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        cookies_header = res.headers.get("set-cookie", "")
        if "auth_token" in cookies_header:
            assert "samesite" in cookies_header.lower(), "Cookie sem flag SameSite"


class TestErrorSanitization:
    """Em modo de produção, erros internos não devem expor detalhes."""

    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    def test_error_messages_no_stack_trace(self, page, live_server):
        """Mensagens de erro não devem conter stack traces ou nomes de módulos internos."""
        token = self._get_token(page, live_server)
        res = page.request.delete(
            f"{live_server}/api/entradas/999999",
            headers={"Authorization": f"Bearer {token}"},
        )
        if res.status >= 400:
            body = res.json()
            error_msg = body.get("error", "")
            assert "Traceback" not in error_msg
            assert "File \"" not in error_msg
            assert ".py\"" not in error_msg


class TestPBKDF2Migration:
    """O login com PBKDF2 deve funcionar de forma transparente."""

    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    def _auth_headers(self, token):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def test_admin_login_works(self, page, live_server):
        """Admin padrão consegue fazer login (hash PBKDF2)."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        assert res.status == 200
        body = res.json()
        assert body["success"] is True
        assert "token" in body["data"]

    def test_created_user_login_works(self, page, live_server):
        """Usuário criado via API consegue fazer login (hash PBKDF2)."""
        token = self._get_token(page, live_server)
        page.request.post(
            f"{live_server}/api/admin/usuarios",
            data=json.dumps({
                "username": "pbkdf2_test_user",
                "password": "senha123",
                "nome": "PBKDF2 Test",
            }),
            headers=self._auth_headers(token),
        )
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "pbkdf2_test_user", "password": "senha123"}),
            headers={"Content-Type": "application/json"},
        )
        assert res.status == 200
        body = res.json()
        assert body["success"] is True

    def test_password_change_works(self, page, live_server):
        """Alterar senha funciona com hashing PBKDF2."""
        token = self._get_token(page, live_server)
        page.request.post(
            f"{live_server}/api/admin/usuarios",
            data=json.dumps({
                "username": "pwd_change_test",
                "password": "old_pass",
                "nome": "Pwd Change",
            }),
            headers=self._auth_headers(token),
        )
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "pwd_change_test", "password": "old_pass"}),
            headers={"Content-Type": "application/json"},
        )
        user_token = res.json()["data"]["token"]
        res = page.request.post(
            f"{live_server}/api/auth/alterar-senha",
            data=json.dumps({"senha_atual": "old_pass", "nova_senha": "new_pass"}),
            headers=self._auth_headers(user_token),
        )
        assert res.status == 200
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "pwd_change_test", "password": "new_pass"}),
            headers={"Content-Type": "application/json"},
        )
        assert res.status == 200
        assert res.json()["success"] is True
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "pwd_change_test", "password": "old_pass"}),
            headers={"Content-Type": "application/json"},
        )
        body = res.json()
        assert body["success"] is False


class TestDeletionUsesOriginalMonth:
    def _get_token(self, page, live_server):
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        return res.json()["data"]["token"]

    def _auth_headers(self, token):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def test_entrada_delete_returns_success(self, page, live_server):
        token = self._get_token(page, live_server)
        headers = self._auth_headers(token)
        res = page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 30}),
            headers=headers,
        )
        assert res.status == 200
        entry_id = res.json()["id"]
        res = page.request.delete(
            f"{live_server}/api/entradas/{entry_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 200
        body = res.json()
        assert body["success"] is True

    def test_saida_delete_returns_success(self, page, live_server):
        token = self._get_token(page, live_server)
        headers = self._auth_headers(token)
        page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 50}),
            headers=headers,
        )
        page.request.post(
            f"{live_server}/api/precos",
            data=json.dumps({"preco": 1.0}),
            headers=headers,
        )
        res = page.request.post(
            f"{live_server}/api/saidas",
            data=json.dumps({"quantidade": 5}),
            headers=headers,
        )
        assert res.status == 200
        sale_id = res.json()["id"]
        res = page.request.delete(
            f"{live_server}/api/saidas/{sale_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 200
        assert res.json()["success"] is True

    def test_quebrado_delete_returns_success(self, page, live_server):
        token = self._get_token(page, live_server)
        headers = self._auth_headers(token)
        page.request.post(
            f"{live_server}/api/entradas",
            data=json.dumps({"quantidade": 20}),
            headers=headers,
        )
        res = page.request.post(
            f"{live_server}/api/quebrados",
            data=json.dumps({"quantidade": 3, "motivo": "teste"}),
            headers=headers,
        )
        assert res.status == 200
        entry_id = res.json()["id"]
        res = page.request.delete(
            f"{live_server}/api/quebrados/{entry_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status == 200
        assert res.json()["success"] is True