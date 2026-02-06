# 🥚 EggVault— Gerenciamento de Ovos

Sistema completo de gerenciamento de ovos com controle de estoque, vendas, entradas, preços e relatórios mensais com gráficos.

## 📋 Funcionalidades

- **📦 Estoque** — Visualização em tempo real com indicadores visuais (🟢🟡🔴)
- **📥 Entradas** — Registro de ovos com observações
- **📤 Vendas** — Registro de vendas com cálculo automático
- **💲 Preços** — Controle de preço com histórico
- **📊 Relatórios** — Gráficos mensais (barras, linhas, rosca)

## 🚀 Como Executar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Executar o aplicativo

```bash
python app.py
```

### 3. Acessar no navegador

```
http://localhost:5000
```

O banco de dados SQLite (`ovos.db`) será criado automaticamente na primeira execução.

## 🧪 Executar Testes

```bash
python -m pytest tests/ -v
```

Ou com unittest:

```bash
python -m unittest tests.test_app -v
```

## 🏗️ Arquitetura

```
Egg/
├── app.py                          # Servidor Flask (API REST)
├── database.py                     # Camada de banco de dados SQLite
├── repositories/                   # Acesso a dados (Repository Pattern)
│   ├── estoque_repo.py
│   ├── entrada_repo.py
│   ├── saida_repo.py
│   ├── preco_repo.py
│   └── resumo_repo.py
├── services/                       # Lógica de negócios (Service Layer)
│   ├── estoque_service.py
│   ├── entrada_service.py
│   ├── saida_service.py
│   ├── preco_service.py
│   └── relatorio_service.py
├── templates/
│   └── index.html                  # Interface SPA
├── static/
│   ├── css/style.css              # Estilos
│   └── js/app.js                  # Frontend JavaScript
├── tests/
│   └── test_app.py                # Testes unitários e funcionais
├── requirements.txt
└── README.md
```

## 🗃️ Banco de Dados

- **estoque** — Quantidade total de ovos
- **entradas** — Registros de entrada
- **saidas** — Registros de vendas
- **precos** — Histórico de preços (apenas 1 ativo por vez)
- **resumo_mensal** — Resumo calculado por mês

## 🛡️ Regras de Negócio

- Quantidade de entrada deve ser positiva
- Venda bloqueada se estoque insuficiente
- Apenas um preço ativo por vez
- Relatórios recalculados automaticamente
- Dados organizados por mês (formato `YYYY-MM`)

## 🎨 Tecnologias

- **Backend:** Python 3 + Flask
- **Banco:** SQLite3
- **Frontend:** HTML5 + CSS3 + JavaScript (Vanilla)
- **Gráficos:** Chart.js 4
- **Ícones:** Font Awesome 6
