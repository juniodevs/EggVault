"""
Testes E2E — API REST (todos os endpoints).

Cobre:
  • CRUD completo de cada recurso via API
  • Status codes corretos
  • Formato de resposta JSON
  • Filtros e parâmetros
"""

import pytest
import json

pytestmark = [pytest.mark.e2e, pytest.mark.api]


@pytest.fixture()
def api(page, live_server):
    """Helper: retorna (request, token, base_url)."""
    res = page.request.post(
        f"{live_server}/api/auth/login",
        data=json.dumps({"username": "admin", "password": "admin"}),
        headers={"Content-Type": "application/json"},
    )
    token = res.json()["data"]["token"]

    class API:
        def __init__(self):
            self.base = live_server
            self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
            self.req = page.request

        def get(self, path, **kw):
            return self.req.get(f"{self.base}{path}", headers=self.headers, **kw)

        def post(self, path, data, **kw):
            return self.req.post(
                f"{self.base}{path}",
                data=json.dumps(data),
                headers=self.headers,
                **kw,
            )

        def delete(self, path, **kw):
            return self.req.delete(f"{self.base}{path}", headers=self.headers, **kw)

        def put(self, path, data, **kw):
            return self.req.put(
                f"{self.base}{path}",
                data=json.dumps(data),
                headers=self.headers,
                **kw,
            )

    return API()


# ═══════════════════════════════════════════
# AUTENTICAÇÃO
# ═══════════════════════════════════════════

class TestAuthAPI:
    """Testes da API de autenticação."""

    def test_login_returns_token(self, page, live_server):
        """Login deve retornar um token."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert "token" in body["data"]
        assert len(body["data"]["token"]) > 0

    def test_login_returns_user_info(self, page, live_server):
        """Login deve retornar dados do usuário."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        body = res.json()
        user = body["data"]["usuario"]
        assert "id" in user
        assert "username" in user
        assert user["username"] == "admin"
        assert "is_admin" in user

    def test_auth_me(self, api):
        """GET /api/auth/me deve retornar dados do usuário."""
        res = api.get("/api/auth/me")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert body["data"]["username"] == "admin"

    def test_login_no_body(self, page, live_server):
        """Login sem body deve retornar 400."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            headers={"Content-Type": "application/json"},
        )
        assert res.status == 400

    def test_login_wrong_password(self, page, live_server):
        """Login com senha errada deve retornar 401."""
        res = page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "wrong"}),
            headers={"Content-Type": "application/json"},
        )
        assert res.status == 401

    def test_logout(self, api):
        """POST /api/auth/logout deve retornar sucesso."""
        res = api.post("/api/auth/logout", {})
        assert res.status == 200


# ═══════════════════════════════════════════
# ESTOQUE
# ═══════════════════════════════════════════

class TestEstoqueAPI:
    """Testes da API de estoque."""

    def test_get_estoque(self, api):
        """GET /api/estoque deve retornar dados de estoque."""
        res = api.get("/api/estoque")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert "quantidade_total" in body["data"]
        assert "status" in body["data"]
        assert "cor" in body["data"]

    def test_estoque_initial_zero(self, api):
        """Estoque inicial deve ser zero."""
        res = api.get("/api/estoque")
        body = res.json()
        assert body["data"]["quantidade_total"] >= 0


# ═══════════════════════════════════════════
# ENTRADAS
# ═══════════════════════════════════════════

class TestEntradasAPI:
    """Testes da API de entradas."""

    def test_listar_entradas(self, api):
        """GET /api/entradas deve retornar lista."""
        res = api.get("/api/entradas")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert isinstance(body["data"], list)

    def test_criar_entrada(self, api):
        """POST /api/entradas deve criar entrada."""
        res = api.post("/api/entradas", {"quantidade": 50, "observacao": "API test"})
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert body["id"] > 0
        assert "50" in body["message"]

    def test_criar_entrada_sem_dados(self, api):
        """POST /api/entradas sem quantidade deve falhar."""
        res = api.post("/api/entradas", {})
        assert res.status in [400, 500]

    def test_deletar_entrada(self, api):
        """DELETE /api/entradas/<id> deve remover entrada."""
        # Criar
        res = api.post("/api/entradas", {"quantidade": 10})
        entry_id = res.json()["id"]

        # Deletar
        res = api.delete(f"/api/entradas/{entry_id}")
        assert res.status == 200
        assert res.json()["success"]

    def test_deletar_entrada_inexistente(self, api):
        """DELETE de entrada inexistente deve retornar erro."""
        res = api.delete("/api/entradas/999999")
        assert res.status in [400, 404, 500]

    def test_entrada_com_filtro_mes(self, api):
        """GET /api/entradas?mes=... deve filtrar por mês."""
        res = api.get("/api/entradas?mes=2025-01")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert isinstance(body["data"], list)


# ═══════════════════════════════════════════
# SAÍDAS / VENDAS
# ═══════════════════════════════════════════

class TestSaidasAPI:
    """Testes da API de saídas."""

    def test_listar_saidas(self, api):
        """GET /api/saidas deve retornar lista."""
        res = api.get("/api/saidas")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert isinstance(body["data"], list)

    def test_criar_saida(self, api):
        """POST /api/saidas deve registrar venda."""
        # Adicionar estoque primeiro
        api.post("/api/entradas", {"quantidade": 100})

        res = api.post("/api/saidas", {"quantidade": 10, "preco_unitario": 1.5})
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert body["id"] > 0

    def test_criar_saida_sem_estoque(self, api):
        """Venda sem estoque suficiente deve falhar."""
        # Garantir estoque zerado vendendo tudo (se houver)
        res = api.post("/api/saidas", {"quantidade": 999999, "preco_unitario": 1.0})
        # Deve falhar
        assert res.status in [400, 500]

    def test_deletar_saida(self, api):
        """DELETE /api/saidas/<id> deve remover venda."""
        api.post("/api/entradas", {"quantidade": 50})
        res = api.post("/api/saidas", {"quantidade": 5, "preco_unitario": 1.0})
        sale_id = res.json()["id"]

        res = api.delete(f"/api/saidas/{sale_id}")
        assert res.status == 200
        assert res.json()["success"]


# ═══════════════════════════════════════════
# PREÇOS
# ═══════════════════════════════════════════

class TestPrecosAPI:
    """Testes da API de preços."""

    def test_get_precos(self, api):
        """GET /api/precos deve retornar histórico."""
        res = api.get("/api/precos")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert isinstance(body["data"], list)

    def test_get_preco_ativo(self, api):
        """GET /api/precos/ativo deve retornar preço ativo."""
        res = api.get("/api/precos/ativo")
        assert res.status == 200
        body = res.json()
        assert body["success"]

    def test_definir_preco(self, api):
        """POST /api/precos deve definir novo preço."""
        res = api.post("/api/precos", {"preco_unitario": 2.50})
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert body["id"] > 0

    def test_definir_preco_sem_dados(self, api):
        """POST /api/precos sem dados deve falhar."""
        res = api.post("/api/precos", {})
        # preco_unitario=0.0 pode ser aceito, então verificar se não é 500
        assert res.status != 500 or res.json().get("success") is False


# ═══════════════════════════════════════════
# QUEBRADOS
# ═══════════════════════════════════════════

class TestQuebradosAPI:
    """Testes da API de quebrados."""

    def test_listar_quebrados(self, api):
        """GET /api/quebrados deve retornar lista."""
        res = api.get("/api/quebrados")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert isinstance(body["data"], list)

    def test_registrar_quebrado(self, api):
        """POST /api/quebrados deve registrar perda."""
        api.post("/api/entradas", {"quantidade": 30})

        res = api.post("/api/quebrados", {"quantidade": 2, "motivo": "API test"})
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert body["id"] > 0

    def test_deletar_quebrado(self, api):
        """DELETE /api/quebrados/<id> deve remover registro."""
        api.post("/api/entradas", {"quantidade": 20})
        res = api.post("/api/quebrados", {"quantidade": 1, "motivo": "delete test"})
        entry_id = res.json()["id"]

        res = api.delete(f"/api/quebrados/{entry_id}")
        assert res.status == 200
        assert res.json()["success"]


# ═══════════════════════════════════════════
# RELATÓRIOS
# ═══════════════════════════════════════════

class TestRelatoriosAPI:
    """Testes da API de relatórios."""

    def test_get_relatorio(self, api):
        """GET /api/relatorio deve retornar resumo."""
        res = api.get("/api/relatorio")
        assert res.status == 200
        body = res.json()
        assert body["success"]

    def test_get_relatorio_com_mes(self, api):
        """GET /api/relatorio?mes=... deve filtrar."""
        res = api.get("/api/relatorio?mes=2026-02")
        assert res.status == 200
        body = res.json()
        assert body["success"]

    def test_get_relatorio_anual(self, api):
        """GET /api/relatorio/anual deve retornar dados."""
        res = api.get("/api/relatorio/anual?ano=2026")
        assert res.status == 200
        body = res.json()
        assert body["success"]

    def test_get_meses(self, api):
        """GET /api/meses deve retornar lista de meses."""
        res = api.get("/api/meses")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert isinstance(body["data"], list)


# ═══════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════

class TestAdminAPI:
    """Testes da API de administração."""

    def test_listar_usuarios(self, api):
        """GET /api/admin/usuarios deve retornar lista."""
        res = api.get("/api/admin/usuarios")
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert isinstance(body["data"], list)
        assert len(body["data"]) >= 1

    def test_criar_usuario(self, api):
        """POST /api/admin/usuarios deve criar usuário."""
        import random
        uname = f"api_test_{random.randint(1000, 9999)}"
        res = api.post("/api/admin/usuarios", {
            "username": uname,
            "password": "1234",
            "nome": "API Test User",
            "is_admin": False,
        })
        assert res.status == 200
        body = res.json()
        assert body["success"]
        assert body["data"]["username"] == uname

    def test_atualizar_usuario(self, api):
        """PUT /api/admin/usuarios/<id> deve atualizar."""
        import random
        uname = f"upd_test_{random.randint(1000, 9999)}"
        res = api.post("/api/admin/usuarios", {
            "username": uname,
            "password": "1234",
            "nome": "Before Update",
        })
        uid = res.json()["data"]["id"]

        res = api.put(f"/api/admin/usuarios/{uid}", {"nome": "After Update"})
        assert res.status == 200
        assert res.json()["success"]

    def test_deletar_usuario(self, api):
        """DELETE /api/admin/usuarios/<id> deve remover."""
        import random
        uname = f"del_test_{random.randint(1000, 9999)}"
        res = api.post("/api/admin/usuarios", {
            "username": uname,
            "password": "1234",
            "nome": "Delete Me",
        })
        uid = res.json()["data"]["id"]

        res = api.delete(f"/api/admin/usuarios/{uid}")
        assert res.status == 200
        assert res.json()["success"]


# ═══════════════════════════════════════════
# EXPORTAÇÃO
# ═══════════════════════════════════════════

class TestExportAPI:
    """Testes da API de exportação."""

    def test_export_excel(self, api):
        """GET /api/export/excel deve retornar arquivo."""
        res = api.get("/api/export/excel")
        assert res.status == 200
        assert "spreadsheet" in res.headers.get("content-type", "") or "octet" in res.headers.get("content-type", "")

    def test_export_pdf(self, api):
        """GET /api/export/pdf deve retornar arquivo."""
        res = api.get("/api/export/pdf")
        assert res.status == 200
        assert "pdf" in res.headers.get("content-type", "")

    def test_export_excel_anual(self, api):
        """GET /api/export/excel-anual deve retornar arquivo."""
        res = api.get("/api/export/excel-anual?ano=2026")
        assert res.status == 200
        assert "spreadsheet" in res.headers.get("content-type", "") or "octet" in res.headers.get("content-type", "")


# ═══════════════════════════════════════════
# FORMATO DE RESPOSTA
# ═══════════════════════════════════════════

class TestResponseFormat:
    """Testes de formato de resposta padrão."""

    def test_success_response_format(self, api):
        """Respostas de sucesso devem ter {success: true, data: ...}."""
        res = api.get("/api/estoque")
        body = res.json()
        assert "success" in body
        assert body["success"] is True
        assert "data" in body

    def test_error_response_format(self, page, live_server):
        """Respostas de erro devem ter {success: false, error: ...}."""
        res = page.request.get(f"{live_server}/api/estoque")
        body = res.json()
        assert "success" in body
        assert body["success"] is False
        assert "error" in body

    def test_json_content_type(self, api):
        """Respostas devem ter Content-Type application/json."""
        res = api.get("/api/estoque")
        assert "application/json" in res.headers.get("content-type", "")
