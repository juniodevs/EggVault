"""
Configuração global do Playwright para o projeto EggVault.
Centraliza constantes, timeouts e opções de browser.
"""

# ═══════════════════════════════════════════
# CONFIGURAÇÃO DO SERVIDOR
# ═══════════════════════════════════════════
BASE_URL = "http://localhost:5000"
SERVER_START_TIMEOUT = 10  # segundos para o servidor iniciar

# ═══════════════════════════════════════════
# CREDENCIAIS PADRÃO (teste)
# ═══════════════════════════════════════════
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin"

# ═══════════════════════════════════════════
# TIMEOUTS (milissegundos)
# ═══════════════════════════════════════════
DEFAULT_TIMEOUT = 15000
NAVIGATION_TIMEOUT = 30000
ACTION_TIMEOUT = 10000

# ═══════════════════════════════════════════
# BROWSER OPTIONS
# ═══════════════════════════════════════════
HEADLESS = True
SLOW_MO = 150  # ms entre ações (útil para debug: 100-500)
VIEWPORT = {"width": 1280, "height": 720}

# ═══════════════════════════════════════════
# SCREENSHOT / VIDEO
# ═══════════════════════════════════════════
SCREENSHOT_ON_FAILURE = True
SCREENSHOTS_DIR = "test-results/screenshots"
VIDEOS_DIR = "test-results/videos"
