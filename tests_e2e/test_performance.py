"""
Testes E2E — Performance e Stress.

Cobre:
  • Tempo de resposta da homepage
  • Tempo de resposta das APIs
  • Multiplas operações em sequência
  • Carga de dados na UI
"""

import pytest
import json
import time

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


@pytest.fixture()
def api(page, live_server):
    """Helper: API autenticada."""
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

        def get(self, path):
            return self.req.get(f"{self.base}{path}", headers=self.headers)

        def post(self, path, data):
            return self.req.post(
                f"{self.base}{path}",
                data=json.dumps(data),
                headers=self.headers,
            )

    return API()


class TestResponseTimes:
    """Testes de tempo de resposta."""

    MAX_RESPONSE_MS = 3000  # 3 segundos máx

    def test_homepage_loads_fast(self, page, live_server):
        """Página principal deve carregar em menos de 3s."""
        start = time.time()
        page.goto(live_server)
        elapsed = (time.time() - start) * 1000
        assert elapsed < self.MAX_RESPONSE_MS, f"Homepage levou {elapsed:.0f}ms"

    def test_login_api_fast(self, page, live_server):
        """API de login deve responder rapidamente."""
        start = time.time()
        page.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps({"username": "admin", "password": "admin"}),
            headers={"Content-Type": "application/json"},
        )
        elapsed = (time.time() - start) * 1000
        assert elapsed < self.MAX_RESPONSE_MS, f"Login levou {elapsed:.0f}ms"

    def test_estoque_api_fast(self, api):
        """API de estoque deve responder rapidamente."""
        start = time.time()
        res = api.get("/api/estoque")
        elapsed = (time.time() - start) * 1000
        assert res.status == 200
        assert elapsed < self.MAX_RESPONSE_MS, f"Estoque levou {elapsed:.0f}ms"

    def test_entradas_api_fast(self, api):
        """API de entradas deve responder rapidamente."""
        start = time.time()
        res = api.get("/api/entradas")
        elapsed = (time.time() - start) * 1000
        assert res.status == 200
        assert elapsed < self.MAX_RESPONSE_MS


class TestBulkOperations:
    """Testes de operações em massa."""

    def test_multiple_entradas(self, api):
        """Deve suportar múltiplas entradas em sequência."""
        for i in range(20):
            res = api.post("/api/entradas", {"quantidade": 10, "observacao": f"Bulk #{i}"})
            assert res.status == 200

        # Verificar estoque
        res = api.get("/api/estoque")
        body = res.json()
        assert body["data"]["quantidade_total"] >= 200

    def test_multiple_vendas(self, api):
        """Deve suportar múltiplas vendas em sequência."""
        # Adicionar estoque grande
        api.post("/api/entradas", {"quantidade": 500})

        for i in range(15):
            res = api.post("/api/saidas", {"quantidade": 5, "preco_unitario": 1.0})
            assert res.status == 200

    def test_mixed_operations(self, api):
        """Deve suportar operações mistas sem erros."""
        api.post("/api/entradas", {"quantidade": 200})

        operations = [
            lambda: api.post("/api/saidas", {"quantidade": 5, "preco_unitario": 1.0}),
            lambda: api.post("/api/entradas", {"quantidade": 10}),
            lambda: api.post("/api/quebrados", {"quantidade": 2, "motivo": "stress test"}),
            lambda: api.get("/api/estoque"),
            lambda: api.get("/api/relatorio"),
        ]

        for _ in range(10):
            for op in operations:
                res = op()
                assert res.status == 200

    def test_entradas_list_with_many_records(self, api):
        """Listar entradas com muitos registros deve funcionar."""
        # Criar muitos registros
        for i in range(30):
            api.post("/api/entradas", {"quantidade": 1, "observacao": f"Record {i}"})

        res = api.get("/api/entradas")
        assert res.status == 200
        body = res.json()
        assert len(body["data"]) >= 30


class TestUIPerformance:
    """Testes de performance da UI."""

    def test_page_load_no_js_errors(self, authenticated_page):
        """Página não deve ter erros de JavaScript após login."""
        errors = []

        def on_console(msg):
            if msg.type == "error":
                errors.append(msg.text)

        authenticated_page.on("console", on_console)

        # Navegar por todas as abas
        tabs = ["entradas", "vendas", "quebrados", "precos", "relatorios", "estoque"]
        for tab in tabs:
            authenticated_page.click(f'li[data-tab="{tab}"]')
            authenticated_page.wait_for_timeout(500)

        # Filtrar erros de rede (404 de fontes etc.) que não são erros de app
        app_errors = [e for e in errors if "favicon" not in e.lower() and "font" not in e.lower()]
        assert len(app_errors) == 0, f"Erros de JS: {app_errors}"

    def test_rapid_tab_switching(self, authenticated_page):
        """Troca rápida de abas não deve causar erros."""
        page = authenticated_page
        tabs = ["entradas", "vendas", "quebrados", "precos", "relatorios", "estoque"]

        for _ in range(3):
            for tab in tabs:
                page.click(f'li[data-tab="{tab}"]')
                page.wait_for_timeout(100)

        # App deve continuar funcional
        assert page.locator("#tab-estoque").is_visible() or page.locator(".main-content").is_visible()
