"""
Script de conveniência para executar os testes Playwright do EggVault.

Uso:
    python run_tests.py                 # Todos os testes E2E
    python run_tests.py --smoke         # Apenas smoke tests
    python run_tests.py --security      # Apenas testes de segurança
    python run_tests.py --api           # Apenas testes de API
    python run_tests.py --ui            # Apenas testes de UI
    python run_tests.py --report        # Gerar relatório HTML
"""

import sys
import subprocess


def main():
    cmd = ["python", "-m", "pytest", "tests_e2e/", "-v", "--tb=short"]

    args = sys.argv[1:]

    if "--smoke" in args:
        cmd += ["-m", "smoke"]
        args.remove("--smoke")
    elif "--security" in args:
        cmd += ["-m", "security"]
        args.remove("--security")
    elif "--api" in args:
        cmd += ["-m", "api"]
        args.remove("--api")
    elif "--ui" in args:
        cmd += ["-m", "ui"]
        args.remove("--ui")
    elif "--slow" in args:
        cmd += ["-m", "slow"]
        args.remove("--slow")

    if "--report" in args:
        cmd += ["--html=test-results/report.html", "--self-contained-html"]
        args.remove("--report")

    # Passar quaisquer outros args ao pytest
    cmd += args

    print(f"🧪 Executando: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
