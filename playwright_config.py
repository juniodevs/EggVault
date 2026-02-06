"""
Configuração global do Playwright para o projeto EggVault.
Centraliza constantes, timeouts e opções de browser.
"""

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
