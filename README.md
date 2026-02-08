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

**Para desenvolvimento (inclui testes):**
```bash
pip install -r requirements-dev.txt
```

**Para produção:**
```bash
pip install -r requirements.txt
```

**Para produção mínima (sem Google Drive):**
```bash
pip install -r requirements-prod-minimal.txt
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

**Instalar dependências de teste:**
```bash
pip install -r requirements-dev.txt
```

**Executar testes E2E:**
```bash
pytest tests_e2e/ -v
```

**Executar testes unitários:**
```bash
python -m pytest tests/ -v
```

Ou com unittest:

```bash
python -m unittest tests.test_app -v
```

## 🌐 Deploy no Vercel

O projeto está configurado para deploy automático no Vercel:

1. **Conecte seu repositório ao Vercel**
2. **Configure as variáveis de ambiente:**
   - `DATABASE_URL` - Connection string do PostgreSQL (Vercel Postgres ou outro)
   - `FLASK_SECRET_KEY` - Chave secreta para sessões
   - Outras variáveis necessárias (Google Drive, etc.)

3. **O Vercel vai:**
   - Usar `requirements.txt` (apenas dependências de produção)
   - Excluir testes e arquivos desnecessários via `.vercelignore`
   - Manter o tamanho da function abaixo de 250 MB

**Nota:** Se ainda houver erro de tamanho, use `requirements-prod-minimal.txt` renomeando para `requirements.txt` no deploy.

## 🔒 Backup Automático para Google Drive

### Configuração

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar .env:**
   ```env
   # Google Drive - Obtenha em https://console.cloud.google.com
   GOOGLE_DRIVE_CLIENT_ID=seu_client_id.apps.googleusercontent.com
   GOOGLE_DRIVE_CLIENT_SECRET=seu_client_secret
   GOOGLE_DRIVE_REFRESH_TOKEN=seu_refresh_token
   
   # Opcional: ID da pasta no Google Drive para organizar backups
   GDRIVE_BACKUP_FOLDER_ID=id_da_pasta
   ```

3. **Obter credenciais Google Drive:**
   - Acesse: https://console.cloud.google.com/
   - Crie projeto → Ative "Google Drive API"
   - Crie credenciais OAuth 2.0 (Desktop app)
   - Use o script helper para obter o refresh token:
     ```bash
     python -c "from services.backup_service import obter_refresh_token; obter_refresh_token()"
     ```

4. **Executar backup:**
   ```bash
   # Manual
   python scripts_backup/backup_manual.py
   
   # Automático (diário às 3h)
   python scripts_backup/backup_agendado.py
   
   # Ou use Task Scheduler (Windows) com scripts_backup/executar_backup.bat
   ```

### Recursos

- ✅ Backup automático do PostgreSQL
- ✅ Backup automático do SQLite
- ✅ Upload para Google Drive
- ✅ Mantém 5 backups locais mais recentes
- ✅ Histórico completo no Google Drive

### 🔍 Verificar Sistema de Backup

Para garantir que o sistema de backup está funcionando corretamente:

```bash
# Verificação básica (sem executar backup)
python scripts_backup/verificar_backup.py

# Verificação com teste de backup local (sem upload)
python scripts_backup/verificar_backup.py --test

# Verificação completa com backup e upload
python scripts_backup/verificar_backup.py --full-test

# Status rápido
python scripts_backup/status_backup.py
```

Ou no Windows:
```bash
# Duplo clique em:
scripts_backup\verificar_backup.bat

# Ou com argumentos:
scripts_backup\verificar_backup.bat --test
```

**O script verifica:**
- ✅ Diretório de backups existe
- ✅ Backups existentes e idade
- ✅ Conexão com banco de dados
- ✅ Configuração do Google Drive
- ✅ Instalação do pg_dump (PostgreSQL)
- ✅ Teste de criação de backup (opcional)

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
│   ├── relatorio_service.py
│   └── backup_service.py          # Serviço de backup
├── scripts_backup/                 # Scripts de backup e verificação
│   ├── backup_manual.py           # Backup manual
│   ├── backup_agendado.py         # Backup agendado
│   ├── executar_backup.bat        # Atalho Windows
│   ├── verificar_backup.py        # Verificação completa
│   ├── status_backup.py           # Status rápido
│   └── verificar_backup.bat       # Atalho verificação
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
