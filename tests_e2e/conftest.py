"""
Fixtures compartilhadas para todos os testes Playwright do EggVault.

Gerencia:
  • Servidor Flask em thread separada (com banco de dados isolado)
  • Browser, context e page com configurações padronizadas
  • Helpers de autenticação reutilizáveis
"""

import os
import sys
import time
import tempfile
import threading
import pytest
from playwright.sync_api import sync_playwright

# ── Caminho do projeto ────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# ── Banco de dados isolado para testes E2E ────────────────────────────────
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "ovos_e2e_test.db")
os.environ["OVOS_DB_PATH"] = TEST_DB_PATH

# ── Configurações (importadas do arquivo na raiz do projeto) ──────────────
# Valores padrão caso o import falhe
BASE_URL = "http://localhost:5000"
DEFAULT_TIMEOUT = 15000
NAVIGATION_TIMEOUT = 30000
HEADLESS = True
SLOW_MO = 0
VIEWPORT = {"width": 1280, "height": 720}
SCREENSHOT_ON_FAILURE = True
SCREENSHOTS_DIR = os.path.join(ROOT_DIR, "test-results", "screenshots")
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin"

try:
    # Forçar o ROOT_DIR no sys.path para encontrar playwright_config
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)
    import playwright_config as _cfg
    BASE_URL = getattr(_cfg, "BASE_URL", BASE_URL)
    DEFAULT_TIMEOUT = getattr(_cfg, "DEFAULT_TIMEOUT", DEFAULT_TIMEOUT)
    NAVIGATION_TIMEOUT = getattr(_cfg, "NAVIGATION_TIMEOUT", NAVIGATION_TIMEOUT)
    HEADLESS = getattr(_cfg, "HEADLESS", HEADLESS)
    SLOW_MO = getattr(_cfg, "SLOW_MO", SLOW_MO)
    VIEWPORT = getattr(_cfg, "VIEWPORT", VIEWPORT)
    SCREENSHOT_ON_FAILURE = getattr(_cfg, "SCREENSHOT_ON_FAILURE", SCREENSHOT_ON_FAILURE)
    SCREENSHOTS_DIR = getattr(_cfg, "SCREENSHOTS_DIR", SCREENSHOTS_DIR)
    DEFAULT_ADMIN_USER = getattr(_cfg, "DEFAULT_ADMIN_USER", DEFAULT_ADMIN_USER)
    DEFAULT_ADMIN_PASS = getattr(_cfg, "DEFAULT_ADMIN_PASS", DEFAULT_ADMIN_PASS)
    print(f"[OK] playwright_config carregado: HEADLESS={HEADLESS}, SLOW_MO={SLOW_MO}")
except ImportError as e:
    print(f"[WARN] playwright_config nao encontrado, usando padroes: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _cleanup_db():
    """Remove arquivos do banco de teste."""
    for suffix in ["", "-wal", "-shm"]:
        path = TEST_DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _start_flask_server():
    """Inicia o servidor Flask em uma thread daemon."""
    from app import app
    from database import init_db

    init_db()
    app.config["TESTING"] = True

    # Werkzeug em thread daemon — morre automaticamente quando o processo principal sai
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def _wait_for_server(url, timeout=10):
    """Aguarda até o servidor responder ou estoura timeout."""
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.3)
    raise RuntimeError(f"Servidor não iniciou em {timeout}s → {url}")


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES — SERVIDOR
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def live_server():
    """Inicia o servidor Flask uma vez por sessão de testes."""
    _cleanup_db()

    server_thread = threading.Thread(target=_start_flask_server, daemon=True)
    server_thread.start()
    _wait_for_server(BASE_URL)

    yield BASE_URL

    _cleanup_db()


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES — BROWSER / CONTEXT / PAGE
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def browser_instance():
    """Abre um browser Chromium que persiste por toda a sessão."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        yield browser
        browser.close()


@pytest.fixture()
def context(browser_instance, live_server):
    """Context isolado por teste — cookies/storage limpos a cada test."""
    ctx = browser_instance.new_context(
        viewport=VIEWPORT,
        base_url=live_server,
        ignore_https_errors=True,
    )
    ctx.set_default_timeout(DEFAULT_TIMEOUT)
    ctx.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
    yield ctx
    ctx.close()


@pytest.fixture()
def page(context):
    """Página nova a cada teste."""
    pg = context.new_page()
    yield pg
    pg.close()


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES — AUTENTICAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def authenticated_page(page):
    """Página já autenticada como admin padrão."""
    page.goto("/")
    page.wait_for_selector("#login-overlay", state="visible")

    page.fill("#login-username", DEFAULT_ADMIN_USER)
    page.fill("#login-password", DEFAULT_ADMIN_PASS)
    page.click("button#btn-login")

    # Aguarda o login completar: overlay desaparece (display:none)
    page.wait_for_selector("#login-overlay", state="hidden", timeout=DEFAULT_TIMEOUT)
    return page


@pytest.fixture()
def admin_api_context(context):
    """Context com token de admin para testes de API."""
    pg = context.new_page()
    response = pg.request.post(
        "/api/auth/login",
        data={"username": DEFAULT_ADMIN_USER, "password": DEFAULT_ADMIN_PASS},
    )
    assert response.ok
    data = response.json()
    assert data["success"]
    token = data["data"]["token"]

    # Coloca o token em extra_http_headers do context
    context.set_extra_http_headers({"Authorization": f"Bearer {token}"})
    pg.close()
    yield context


# ═══════════════════════════════════════════════════════════════════════════
# HOOKS — SCREENSHOT EM FALHA
# ═══════════════════════════════════════════════════════════════════════════

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Captura screenshot quando um teste falha."""
    import pytest as _pytest

    outcome = yield
    rep = outcome.get_result()

    if rep.when == "call" and rep.failed and SCREENSHOT_ON_FAILURE:
        # Tenta obter a fixture 'page'
        page_fixture = item.funcargs.get("page") or item.funcargs.get("authenticated_page")
        if page_fixture and not page_fixture.is_closed():
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            name = item.nodeid.replace("::", "_").replace("/", "_").replace("\\", "_")
            path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
            try:
                page_fixture.screenshot(path=path)
                print(f"\n📸 Screenshot salvo: {path}")
            except Exception:
                pass
