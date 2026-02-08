let currentTab = 'estoque';
const currentMonth = {
    entradas: getCurrentMonth(),
    vendas: getCurrentMonth(),
    quebrados: getCurrentMonth(),
    despesas: getCurrentMonth(),
    relatorios: getCurrentMonth()
};
const charts = {};

function showSkeleton(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.style.display = '';
}

function hideSkeleton(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.style.display = 'none';
}

function showTableSkeleton(tbodyId, cols = 5, rows = 3) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    
    let html = '';
    for (let i = 0; i < rows; i++) {
        html += '<tr class="skeleton-row"><td colspan="' + cols + '">';
        html += '<div class="skeleton-table-row">';
        for (let j = 0; j < cols; j++) {
            html += '<div class="skeleton skeleton-table-cell"></div>';
        }
        html += '</div></td></tr>';
    }
    tbody.innerHTML = html;
}

let authToken = localStorage.getItem('auth_token') || '';
let currentUser = null;

function saveToken(token) {
    authToken = token;
    localStorage.setItem('auth_token', token);
}

function clearToken() {
    authToken = '';
    localStorage.removeItem('auth_token');
}

function showLogin() {
    document.getElementById('login-overlay').classList.remove('hidden');
    document.getElementById('login-username').value = '';
    document.getElementById('login-password').value = '';
    document.getElementById('login-error').style.display = 'none';
    document.getElementById('login-username').focus();
}

function hideLogin() {
    document.getElementById('login-overlay').classList.add('hidden');
}

async function checkAuth() {
    if (!authToken) {
        showLogin();
        return false;
    }
    try {
        const res = await fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (data.success) {
            hideLogin();
            currentUser = data.data;
            document.getElementById('sidebar-username').textContent = data.data.nome || data.data.username;
            // Mostrar aba admin se for administrador
            const navAdmin = document.getElementById('nav-admin');
            if (navAdmin) navAdmin.style.display = data.data.is_admin ? '' : 'none';
            return true;
        } else {
            clearToken();
            showLogin();
            return false;
        }
    } catch {
        clearToken();
        showLogin();
        return false;
    }
}

async function doLogin(username, password) {
    const btn = document.getElementById('btn-login');
    const errorDiv = document.getElementById('login-error');
    const errorText = document.getElementById('login-error-text');

    btn.innerHTML = '<span class="spinner"></span> Entrando...';
    btn.disabled = true;
    errorDiv.style.display = 'none';

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (data.success) {
            saveToken(data.data.token);
            hideLogin();
            currentUser = data.data.usuario;
            document.getElementById('sidebar-username').textContent =
                data.data.usuario.nome || data.data.usuario.username;
            // Mostrar aba admin se for administrador
            const navAdmin = document.getElementById('nav-admin');
            if (navAdmin) navAdmin.style.display = data.data.usuario.is_admin ? '' : 'none';
            loadEstoque();
            showToast(`Bem-vindo, ${data.data.usuario.nome || data.data.usuario.username}!`, 'success');
        } else {
            errorText.textContent = data.error || 'Credenciais inválidas';
            errorDiv.style.display = 'flex';
        }
    } catch {
        errorText.textContent = 'Erro de conexão com o servidor';
        errorDiv.style.display = 'flex';
    } finally {
        btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Entrar';
        btn.disabled = false;
    }
}

async function doLogout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
    } catch {}
    clearToken();
    showLogin();
    showToast('Você saiu do sistema', 'info');
}

function togglePasswordVisibility() {
    const input = document.getElementById('login-password');
    const icon = document.getElementById('password-eye-icon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

function showChangePassword() {
    document.getElementById('modal-senha').style.display = 'flex';
    document.getElementById('senha-atual').value = '';
    document.getElementById('nova-senha').value = '';
    document.getElementById('confirmar-senha').value = '';
    document.getElementById('senha-atual').focus();

    document.getElementById('sidebar').classList.remove('open');
}

function hideChangePassword() {
    document.getElementById('modal-senha').style.display = 'none';
}

async function doChangePassword(senhaAtual, novaSenha) {
    try {
        const res = await api('/api/auth/alterar-senha', {
            method: 'POST',
            body: JSON.stringify({ senha_atual: senhaAtual, nova_senha: novaSenha })
        });
        showToast('Senha alterada! Faça login novamente.', 'success');
        hideChangePassword();
        clearToken();
        showLogin();
    } catch {
    }
}

function getReportMonth() {
    const month = document.getElementById('report-month')?.value;
    const year = document.getElementById('report-year')?.value;
    if (month && year) return `${year}-${month}`;
    return getCurrentMonth();
}

function getReportYear() {
    return document.getElementById('report-year')?.value || new Date().getFullYear().toString();
}

function downloadWithAuth(url) {
    // Create a temporary link with the auth token as query param
    // Since we set cookie on login, file downloads use cookie auth automatically
    const link = document.createElement('a');
    link.href = url;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    setTimeout(() => link.remove(), 1000);
}

function exportExcel() {
    const mes = getReportMonth();
    downloadWithAuth(`/api/export/excel?mes=${mes}`);
    showToast(`Baixando Excel de ${formatMonthLabel(mes)}...`, 'info');
}

function exportPDF() {
    const mes = getReportMonth();
    downloadWithAuth(`/api/export/pdf?mes=${mes}`);
    showToast(`Baixando PDF de ${formatMonthLabel(mes)}...`, 'info');
}

function exportExcelAnual() {
    const ano = getReportYear();
    downloadWithAuth(`/api/export/excel-anual?ano=${ano}`);
    showToast(`Baixando Excel anual de ${ano}...`, 'info');
}

function getCurrentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value || 0);
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatMonthLabel(monthStr) {
    const [year, month] = monthStr.split('-');
    const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    return `${months[parseInt(month) - 1]} ${year}`;
}

async function api(endpoint, options = {}) {
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }
        const response = await fetch(endpoint, {
            headers,
            ...options
        });

        // Sessão expirada → redirecionar para login
        if (response.status === 401) {
            clearToken();
            showLogin();
            throw new Error('Sessão expirada. Faça login novamente.');
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Erro desconhecido');
        }
        return data;
    } catch (error) {
        if (error.message !== 'Failed to fetch') {
            showToast(error.message, 'error');
        }
        throw error;
    }
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        info: 'info-circle'
    };
    const icon = icons[type] || icons.info;
    toast.innerHTML = `<i class="fas fa-${icon}"></i><span>${message}</span>`;

    container.appendChild(toast);

    // Anima a entrada
    requestAnimationFrame(() => {
        requestAnimationFrame(() => toast.classList.add('show'));
    });

    // Remove após 3.5s
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 350);
    }, 3500);
}

// ═══════════════════════════════════════════
// MODAL DE CONFIRMAÇÃO CUSTOMIZADO
// ═══════════════════════════════════════════

function customConfirm(title, message) {
    return new Promise((resolve) => {
        document.getElementById('confirm-title').textContent = title;
        document.getElementById('confirm-message').textContent = message;
        const overlay = document.getElementById('modal-confirm');
        overlay.style.display = 'flex';

        const okBtn = document.getElementById('confirm-ok-btn');
        const cancelBtn = document.getElementById('confirm-cancel-btn');

        function cleanup() {
            overlay.style.display = 'none';
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
            overlay.removeEventListener('click', onOverlay);
        }
        function onOk() { cleanup(); resolve(true); }
        function onCancel() { cleanup(); resolve(false); }
        function onOverlay(e) { if (e.target === overlay) { cleanup(); resolve(false); } }

        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
        overlay.addEventListener('click', onOverlay);
    });
}

// ═══════════════════════════════════════════
// MODAL REDEFINIR SENHA (ADMIN)
// ═══════════════════════════════════════════

function showResetPassword(userId, username) {
    document.getElementById('reset-senha-user-id').value = userId;
    document.getElementById('reset-senha-username').value = username;
    document.getElementById('reset-senha-subtitle').textContent = `Definir nova senha para "${username}"`;
    document.getElementById('reset-nova-senha').value = '';
    document.getElementById('reset-confirmar-senha').value = '';
    document.getElementById('modal-reset-senha').style.display = 'flex';
    document.getElementById('reset-nova-senha').focus();
}

function hideResetPassword() {
    document.getElementById('modal-reset-senha').style.display = 'none';
}

async function doResetPassword(userId, username, novaSenha) {
    try {
        const res = await api(`/api/admin/usuarios/${userId}`, {
            method: 'PUT',
            body: JSON.stringify({ nova_senha: novaSenha })
        });
        showToast(`Senha de "${username}" redefinida`, 'success');
    } catch {
        // Toast exibido
    }
}

// ═══════════════════════════════════════════
// NAVEGAÇÃO POR ABAS
// ═══════════════════════════════════════════

function switchTab(tabName) {
    // Bloquear acesso de não-admin à aba Admin
    if (tabName === 'admin' && (!currentUser || !currentUser.is_admin)) {
        switchTab('estoque');
        return;
    }
    // Atualizar sidebar
    document.querySelectorAll('.nav-links li').forEach(li => li.classList.remove('active'));
    const target = document.querySelector(`.nav-links li[data-tab="${tabName}"]`);
    if (target) target.classList.add('active');

    // Atualizar conteúdo
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    const tabEl = document.getElementById(`tab-${tabName}`);
    if (tabEl) tabEl.classList.add('active');

    currentTab = tabName;
    loadTabData(tabName);

    // Fechar menu mobile
    document.getElementById('sidebar').classList.remove('open');
}

async function loadTabData(tabName) {
    switch (tabName) {
        case 'estoque':    await loadEstoque(); break;
        case 'entradas':   await loadEntradas(); break;
        case 'vendas':     await loadVendas(); break;
        case 'quebrados':  await loadQuebrados(); break;
        case 'despesas':   await loadDespesas(); break;
        case 'precos':     await loadPrecos(); break;
        case 'relatorios': await loadRelatorios(); break;
        case 'admin':      await loadAdminUsers(); break;
    }
}

// ═══════════════════════════════════════════
// ABA — ESTOQUE (Dashboard)
// ═══════════════════════════════════════════

async function loadEstoque() {
    // Show skeleton
    const statsGrid = document.getElementById('stats-grid-estoque');
    if (statsGrid) statsGrid.style.opacity = '0.5';
    
    try {
        const [estoqueRes, relatorioRes, precoRes] = await Promise.all([
            api('/api/estoque'),
            api('/api/relatorio?mes=' + getCurrentMonth()),
            api('/api/precos/ativo')
        ]);

        const estoque = estoqueRes.data;
        const relatorio = relatorioRes.data;
        const preco = precoRes.data;

        // Atualizar display de estoque
        document.getElementById('stock-quantity').textContent =
            estoque.quantidade_total.toLocaleString('pt-BR');

        // Atualizar indicador
        const card = document.getElementById('stock-main-card');
        const indicator = document.getElementById('stock-indicator');
        let statusText, statusClass;

        if (estoque.cor === 'verde') {
            statusText = '🟢 Estoque Alto';
            statusClass = 'status-high';
        } else if (estoque.cor === 'amarelo') {
            statusText = '🟡 Estoque Médio';
            statusClass = 'status-medium';
        } else {
            statusText = '🔴 Estoque Baixo';
            statusClass = 'status-low';
        }

        card.className = `stock-card ${statusClass}`;
        indicator.innerHTML = `<span class="indicator-text">${statusText}</span>`;

        // Atualizar stats
        document.getElementById('stat-entradas-mes').textContent = relatorio.total_entradas;
        document.getElementById('stat-saidas-mes').textContent = relatorio.total_saidas;
        document.getElementById('stat-quebrados-mes').textContent = relatorio.total_quebrados || 0;
        document.getElementById('stat-faturamento-mes').textContent =
            formatCurrency(relatorio.faturamento_total);
        document.getElementById('stat-despesas-mes').textContent =
            formatCurrency(relatorio.total_despesas || 0);
        document.getElementById('stat-preco-atual').textContent =
            preco ? formatCurrency(preco.preco_unitario) : 'Não definido';

        // Última atualização
        document.getElementById('last-update').textContent =
            `Última atualização: ${formatDate(estoque.ultima_atualizacao)}`;

        // Hide skeleton
        if (statsGrid) statsGrid.style.opacity = '1';

    } catch (e) {
        console.error('Erro ao carregar estoque:', e);
        if (statsGrid) statsGrid.style.opacity = '1';
    }
}

// ═══════════════════════════════════════════
// ABA — ENTRADAS
// ═══════════════════════════════════════════

async function loadEntradas() {
    showTableSkeleton('entradas-hoje-list', 5, 2);
    
    try {
        const mes = currentMonth.entradas;
        document.getElementById('entradas-month-label').textContent = formatMonthLabel(mes);

        const res = await api(`/api/entradas?mes=${mes}`);

        if (res.data.length === 0) {
            document.getElementById('entradas-hoje-list').innerHTML =
                '<tr><td colspan="5" class="empty-state">Nenhuma entrada registrada hoje</td></tr>';
            document.getElementById('entradas-anteriores-container').innerHTML =
                '<div class="empty-state" style="padding: 2rem;">Nenhuma entrada anterior neste mês</div>';
            document.getElementById('entradas-hoje-total').textContent = '0 ovos';
            document.getElementById('entradas-mes-total').textContent = '0 ovos';
            return;
        }

        // Agrupar entradas por data
        const hoje = new Date().toISOString().split('T')[0];
        const entradasPorDia = {};
        let totalMes = 0;

        res.data.forEach(entrada => {
            const dataEntrada = entrada.data.split('T')[0];
            if (!entradasPorDia[dataEntrada]) {
                entradasPorDia[dataEntrada] = [];
            }
            entradasPorDia[dataEntrada].push(entrada);
            totalMes += entrada.quantidade;
        });

        // Renderizar entradas de hoje
        const entradasHoje = entradasPorDia[hoje] || [];
        renderEntradasHoje(entradasHoje);

        // Renderizar entradas dos dias anteriores
        renderEntradasAnteriores(entradasPorDia, hoje);

        // Atualizar total do mês
        document.getElementById('entradas-mes-total').textContent = `${totalMes} ovos`;

    } catch (e) {
        console.error('Erro ao carregar entradas:', e);
    }
}

function renderEntradasHoje(entradas) {
    const tbody = document.getElementById('entradas-hoje-list');
    
    if (entradas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhuma entrada registrada hoje</td></tr>';
        document.getElementById('entradas-hoje-total').textContent = '0 ovos';
        return;
    }

    let totalHoje = 0;
    tbody.innerHTML = entradas.map(e => {
        totalHoje += e.quantidade;
        const hora = new Date(e.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        return `
            <tr>
                <td>${hora}</td>
                <td><strong>${e.quantidade}</strong> ovos</td>
                <td>${e.observacao || '—'}</td>
                <td><span class="user-badge">${e.usuario_nome || '—'}</span></td>
                <td>
                    <button class="btn-undo" onclick="undoEntrada(${e.id}, ${e.quantidade})" title="Desfazer — remover do estoque">
                        <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    document.getElementById('entradas-hoje-total').textContent = `${totalHoje} ovos`;
}

function renderEntradasAnteriores(entradasPorDia, hoje) {
    const container = document.getElementById('entradas-anteriores-container');
    
    // Filtrar e ordenar datas anteriores (mais recente primeiro)
    const datasAnteriores = Object.keys(entradasPorDia)
        .filter(data => data !== hoje)
        .sort((a, b) => b.localeCompare(a));

    if (datasAnteriores.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding: 2rem;">Nenhuma entrada anterior neste mês</div>';
        return;
    }

    container.innerHTML = datasAnteriores.map(data => {
        const entradas = entradasPorDia[data];
        let totalDia = 0;
        
        const rows = entradas.map(e => {
            totalDia += e.quantidade;
            const hora = new Date(e.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            return `
                <tr>
                    <td>${hora}</td>
                    <td><strong>${e.quantidade}</strong> ovos</td>
                    <td>${e.observacao || '—'}</td>
                    <td><span class="user-badge">${e.usuario_nome || '—'}</span></td>
                    <td>
                        <button class="btn-undo" onclick="undoEntrada(${e.id}, ${e.quantidade})" title="Desfazer — remover do estoque">
                            <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        const dataFormatada = formatDateLong(data);
        
        return `
            <div class="day-section">
                <div class="day-section-header">
                    <span class="day-date">${dataFormatada}</span>
                    <span class="day-total">Total: ${totalDia} ovos</span>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Hora</th>
                                <th>Quantidade</th>
                                <th>Observação</th>
                                <th>Usuário</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join('');
}

// ═══════════════════════════════════════════
// ABA — VENDAS
// ═══════════════════════════════════════════

async function loadVendas() {
    showTableSkeleton('vendas-hoje-list', 6, 2);
    
    try {
        const mes = currentMonth.vendas;
        document.getElementById('vendas-month-label').textContent = formatMonthLabel(mes);

        // Carregar estoque disponível
        const estoqueRes = await api('/api/estoque');
        document.getElementById('venda-stock-qty').textContent =
            estoqueRes.data.quantidade_total;

        // Carregar preço ativo e preencher campo
        const precoRes = await api('/api/precos/ativo');
        if (precoRes.data) {
            const precoInput = document.getElementById('venda-preco');
            if (!precoInput.value) {
                precoInput.value = precoRes.data.preco_unitario;
            }
            updateVendaTotal();
        }

        // Carregar lista de vendas
        const res = await api(`/api/saidas?mes=${mes}`);
        
        if (res.data.length === 0) {
            document.getElementById('vendas-hoje-list').innerHTML =
                '<tr><td colspan="6" class="empty-state">Nenhuma venda registrada hoje</td></tr>';
            document.getElementById('vendas-anteriores-container').innerHTML =
                '<div class="empty-state" style="padding: 2rem;">Nenhuma venda anterior neste mês</div>';
            document.getElementById('vendas-hoje-total').textContent = 'R$ 0,00';
            document.getElementById('vendas-mes-total').textContent = 'R$ 0,00';
            return;
        }

        // Agrupar vendas por data
        const hoje = new Date().toISOString().split('T')[0];
        const vendasPorDia = {};
        let totalMes = 0;

        res.data.forEach(venda => {
            const dataVenda = venda.data.split('T')[0];
            if (!vendasPorDia[dataVenda]) {
                vendasPorDia[dataVenda] = [];
            }
            vendasPorDia[dataVenda].push(venda);
            totalMes += venda.valor_total;
        });

        const vendasHoje = vendasPorDia[hoje] || [];
        renderVendasHoje(vendasHoje);

        renderVendasAnteriores(vendasPorDia, hoje);

        document.getElementById('vendas-mes-total').textContent = formatCurrency(totalMes);

    } catch (e) {
        console.error('Erro ao carregar vendas:', e);
    }
}

function renderVendasHoje(vendas) {
    const tbody = document.getElementById('vendas-hoje-list');
    
    if (vendas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Nenhuma venda registrada hoje</td></tr>';
        document.getElementById('vendas-hoje-total').textContent = 'R$ 0,00';
        return;
    }

    let totalHoje = 0;
    tbody.innerHTML = vendas.map(s => {
        totalHoje += s.valor_total;
        const hora = new Date(s.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        return `
            <tr>
                <td>${hora}</td>
                <td><strong>${s.quantidade}</strong></td>
                <td>${formatCurrency(s.preco_unitario)}</td>
                <td><strong>${formatCurrency(s.valor_total)}</strong></td>
                <td><span class="user-badge">${s.usuario_nome || '—'}</span></td>
                <td>
                    <button class="btn-undo" onclick="undoVenda(${s.id}, ${s.quantidade})" title="Desfazer — devolver ao estoque">
                        <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    document.getElementById('vendas-hoje-total').textContent = formatCurrency(totalHoje);
}

function renderVendasAnteriores(vendasPorDia, hoje) {
    const container = document.getElementById('vendas-anteriores-container');
    
    // Filtrar e ordenar datas anteriores (mais recente primeiro)
    const datasAnteriores = Object.keys(vendasPorDia)
        .filter(data => data !== hoje)
        .sort((a, b) => b.localeCompare(a));

    if (datasAnteriores.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding: 2rem;">Nenhuma venda anterior neste mês</div>';
        return;
    }

    container.innerHTML = datasAnteriores.map(data => {
        const vendas = vendasPorDia[data];
        let totalDia = 0;
        
        const rows = vendas.map(s => {
            totalDia += s.valor_total;
            const hora = new Date(s.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            return `
                <tr>
                    <td>${hora}</td>
                    <td><strong>${s.quantidade}</strong></td>
                    <td>${formatCurrency(s.preco_unitario)}</td>
                    <td><strong>${formatCurrency(s.valor_total)}</strong></td>
                    <td><span class="user-badge">${s.usuario_nome || '—'}</span></td>
                    <td>
                        <button class="btn-undo" onclick="undoVenda(${s.id}, ${s.quantidade})" title="Desfazer — devolver ao estoque">
                            <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        const dataFormatada = formatDateLong(data);
        
        return `
            <div class="day-section">
                <div class="day-section-header">
                    <span class="day-date">${dataFormatada}</span>
                    <span class="day-total">Total: ${formatCurrency(totalDia)}</span>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Hora</th>
                                <th>Qtd</th>
                                <th>Preço Unit.</th>
                                <th>Total</th>
                                <th>Usuário</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join('');
}

function formatDateLong(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('pt-BR', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
}

let lastEditedField = null;

function parseDecimalInput(value) {
    return parseFloat(value.toString().replace(',', '.')) || 0;
}

function formatDecimalInput(value) {
    return value.toFixed(2).replace('.', ',');
}

function updateVendaTotal() {
    if (lastEditedField === 'total') return; // Evita loop
    
    const qty = parseInt(document.getElementById('venda-quantidade').value) || 0;
    const price = parseDecimalInput(document.getElementById('venda-preco').value);
    const total = qty * price;
    
    lastEditedField = 'price';
    document.getElementById('venda-total').value = formatDecimalInput(total);
}

function updateVendaUnitPrice() {
    if (lastEditedField === 'price') return; // Evita loop
    
    const qty = parseInt(document.getElementById('venda-quantidade').value) || 0;
    const total = parseDecimalInput(document.getElementById('venda-total').value);
    
    if (qty > 0) {
        const unitPrice = total / qty;
        lastEditedField = 'total';
        document.getElementById('venda-preco').value = formatDecimalInput(unitPrice);
    }
}

// ═══════════════════════════════════════════
// ABA — OVOS QUEBRADOS
// ═══════════════════════════════════════════

async function loadQuebrados() {
    showTableSkeleton('quebrados-hoje-list', 5, 2);
    
    try {
        const mes = currentMonth.quebrados;
        document.getElementById('quebrados-month-label').textContent = formatMonthLabel(mes);

        // Carregar estoque disponível
        const estoqueRes = await api('/api/estoque');
        document.getElementById('quebrado-stock-qty').textContent =
            estoqueRes.data.quantidade_total;

        // Carregar lista de quebrados
        const res = await api(`/api/quebrados?mes=${mes}`);

        if (res.data.length === 0) {
            document.getElementById('quebrados-hoje-list').innerHTML =
                '<tr><td colspan="5" class="empty-state">Nenhum registro de quebra hoje</td></tr>';
            document.getElementById('quebrados-anteriores-container').innerHTML =
                '<div class="empty-state" style="padding: 2rem;">Nenhum registro anterior neste mês</div>';
            document.getElementById('quebrados-hoje-total').textContent = '0 ovos';
            document.getElementById('quebrados-mes-total').textContent = '0 ovos';
            return;
        }

        // Agrupar quebrados por data
        const hoje = new Date().toISOString().split('T')[0];
        const quebradosPorDia = {};
        let totalMes = 0;

        res.data.forEach(quebrado => {
            const dataQuebrado = quebrado.data.split('T')[0];
            if (!quebradosPorDia[dataQuebrado]) {
                quebradosPorDia[dataQuebrado] = [];
            }
            quebradosPorDia[dataQuebrado].push(quebrado);
            totalMes += quebrado.quantidade;
        });

        // Renderizar quebrados de hoje
        const quebradosHoje = quebradosPorDia[hoje] || [];
        renderQuebradosHoje(quebradosHoje);

        // Renderizar quebrados dos dias anteriores
        renderQuebradosAnteriores(quebradosPorDia, hoje);

        // Atualizar total do mês
        document.getElementById('quebrados-mes-total').textContent = `${totalMes} ovos`;

    } catch (e) {
        console.error('Erro ao carregar quebrados:', e);
    }
}

function renderQuebradosHoje(quebrados) {
    const tbody = document.getElementById('quebrados-hoje-list');
    
    if (quebrados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhum registro de quebra hoje</td></tr>';
        document.getElementById('quebrados-hoje-total').textContent = '0 ovos';
        return;
    }

    let totalHoje = 0;
    tbody.innerHTML = quebrados.map(q => {
        totalHoje += q.quantidade;
        const hora = new Date(q.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        return `
            <tr>
                <td>${hora}</td>
                <td><strong>${q.quantidade}</strong> ovos</td>
                <td>${q.motivo || '—'}</td>
                <td><span class="user-badge">${q.usuario_nome || '—'}</span></td>
                <td>
                    <button class="btn-undo" onclick="undoQuebrado(${q.id}, ${q.quantidade})" title="Desfazer — devolver ao estoque">
                        <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    document.getElementById('quebrados-hoje-total').textContent = `${totalHoje} ovos`;
}

function renderQuebradosAnteriores(quebradosPorDia, hoje) {
    const container = document.getElementById('quebrados-anteriores-container');
    
    // Filtrar e ordenar datas anteriores (mais recente primeiro)
    const datasAnteriores = Object.keys(quebradosPorDia)
        .filter(data => data !== hoje)
        .sort((a, b) => b.localeCompare(a));

    if (datasAnteriores.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding: 2rem;">Nenhum registro anterior neste mês</div>';
        return;
    }

    container.innerHTML = datasAnteriores.map(data => {
        const quebrados = quebradosPorDia[data];
        let totalDia = 0;
        
        const rows = quebrados.map(q => {
            totalDia += q.quantidade;
            const hora = new Date(q.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            return `
                <tr>
                    <td>${hora}</td>
                    <td><strong>${q.quantidade}</strong> ovos</td>
                    <td>${q.motivo || '—'}</td>
                    <td><span class="user-badge">${q.usuario_nome || '—'}</span></td>
                    <td>
                        <button class="btn-undo" onclick="undoQuebrado(${q.id}, ${q.quantidade})" title="Desfazer — devolver ao estoque">
                            <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        const dataFormatada = formatDateLong(data);
        
        return `
            <div class="day-section">
                <div class="day-section-header">
                    <span class="day-date">${dataFormatada}</span>
                    <span class="day-total" style="background: linear-gradient(135deg, #fef2f2, #fee2e2); color: #dc2626;">Total: ${totalDia} ovos</span>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Hora</th>
                                <th>Quantidade</th>
                                <th>Motivo</th>
                                <th>Usuário</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join('');
}

async function undoQuebrado(entryId, quantidade) {
    const ok = await customConfirm('Desfazer Quebrado', `Desfazer registro de ${quantidade} ovo(s) quebrado(s)? Os ovos serão devolvidos ao estoque.`);
    if (!ok) return;
    try {
        const res = await api(`/api/quebrados/${entryId}`, { method: 'DELETE' });
        showToast(res.message, 'success');
        await loadQuebrados();
    } catch (e) {
        // Toast já exibido
    }
}

// ═══════════════════════════════════════════
// ABA — DESPESAS
// ═══════════════════════════════════════════

async function loadDespesas() {
    showTableSkeleton('despesas-hoje-list', 5, 2);
    
    try {
        const mes = currentMonth.despesas;
        document.getElementById('despesas-month-label').textContent = formatMonthLabel(mes);

        const res = await api(`/api/despesas?mes=${mes}`);

        if (res.data.length === 0) {
            document.getElementById('despesas-hoje-list').innerHTML =
                '<tr><td colspan="5" class="empty-state">Nenhuma despesa registrada hoje</td></tr>';
            document.getElementById('despesas-anteriores-container').innerHTML =
                '<div class="empty-state" style="padding: 2rem;">Nenhuma despesa anterior neste mês</div>';
            document.getElementById('despesas-hoje-total').textContent = 'R$ 0,00';
            document.getElementById('despesas-mes-total').textContent = 'R$ 0,00';
            return;
        }

        // Agrupar despesas por data
        const hoje = new Date().toISOString().split('T')[0];
        const despesasPorDia = {};
        let totalMes = 0;

        res.data.forEach(despesa => {
            const dataDespesa = despesa.data.split('T')[0];
            if (!despesasPorDia[dataDespesa]) {
                despesasPorDia[dataDespesa] = [];
            }
            despesasPorDia[dataDespesa].push(despesa);
            totalMes += despesa.valor || 0;
        });

        // Renderizar despesas de hoje
        const despesasHoje = despesasPorDia[hoje] || [];
        renderDespesasHoje(despesasHoje);

        // Renderizar despesas dos dias anteriores
        renderDespesasAnteriores(despesasPorDia, hoje);

        // Atualizar total do mês
        document.getElementById('despesas-mes-total').textContent = formatCurrency(totalMes);

    } catch (e) {
        console.error('Erro ao carregar despesas:', e);
    }
}

function renderDespesasHoje(despesas) {
    const tbody = document.getElementById('despesas-hoje-list');
    
    if (despesas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhuma despesa registrada hoje</td></tr>';
        document.getElementById('despesas-hoje-total').textContent = 'R$ 0,00';
        return;
    }

    let totalHoje = 0;
    tbody.innerHTML = despesas.map(d => {
        totalHoje += d.valor || 0;
        const hora = new Date(d.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        return `
            <tr>
                <td>${hora}</td>
                <td><strong>${formatCurrency(d.valor)}</strong></td>
                <td>${d.descricao || '—'}</td>
                <td><span class="user-badge">${d.usuario_nome || '—'}</span></td>
                <td>
                    <button class="btn-undo" onclick="undoDespesa(${d.id}, ${d.valor})" title="Remover despesa">
                        <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    document.getElementById('despesas-hoje-total').textContent = formatCurrency(totalHoje);
}

function renderDespesasAnteriores(despesasPorDia, hoje) {
    const container = document.getElementById('despesas-anteriores-container');
    
    // Filtrar e ordenar datas anteriores (mais recente primeiro)
    const datasAnteriores = Object.keys(despesasPorDia)
        .filter(data => data !== hoje)
        .sort((a, b) => b.localeCompare(a));

    if (datasAnteriores.length === 0) {
        container.innerHTML = '<div class="empty-state" style="padding: 2rem;">Nenhuma despesa anterior neste mês</div>';
        return;
    }

    container.innerHTML = datasAnteriores.map(data => {
        const despesas = despesasPorDia[data];
        let totalDia = 0;
        
        const rows = despesas.map(d => {
            totalDia += d.valor || 0;
            const hora = new Date(d.data).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            return `
                <tr>
                    <td>${hora}</td>
                    <td><strong>${formatCurrency(d.valor)}</strong></td>
                    <td>${d.descricao || '—'}</td>
                    <td><span class="user-badge">${d.usuario_nome || '—'}</span></td>
                    <td>
                        <button class="btn-undo" onclick="undoDespesa(${d.id}, ${d.valor})" title="Remover despesa">
                            <i class="fas fa-undo"></i> <span class="btn-undo-label">Desfazer</span>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        const dataFormatada = formatDateLong(data);
        
        return `
            <div class="day-section">
                <div class="day-section-header">
                    <span class="day-date">${dataFormatada}</span>
                    <span class="day-total" style="background: linear-gradient(135deg, #fff7ed, #fed7aa); color: #c2410c;">Total: ${formatCurrency(totalDia)}</span>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Hora</th>
                                <th>Valor</th>
                                <th>Descrição</th>
                                <th>Usuário</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join('');
}

async function undoDespesa(entryId, valor) {
    const ok = await customConfirm('Remover Despesa', `Remover despesa de ${formatCurrency(valor)}? O valor será devolvido ao faturamento.`);
    if (!ok) return;
    try {
        const res = await api(`/api/despesas/${entryId}`, { method: 'DELETE' });
        showToast(res.message, 'success');
        await loadDespesas();
    } catch (e) {
        // Toast já exibido
    }
}

async function undoVenda(saleId, quantidade) {
    const ok = await customConfirm('Desfazer Venda', `Desfazer venda de ${quantidade} ovo(s)? Os ovos serão devolvidos ao estoque.`);
    if (!ok) return;
    try {
        const res = await api(`/api/saidas/${saleId}`, { method: 'DELETE' });
        showToast(res.message, 'success');
        await loadVendas();
    } catch (e) {
        // Toast já exibido
    }
}

async function undoEntrada(entryId, quantidade) {
    const ok = await customConfirm('Desfazer Entrada', `Desfazer entrada de ${quantidade} ovo(s)? Os ovos serão removidos do estoque.`);
    if (!ok) return;
    try {
        const res = await api(`/api/entradas/${entryId}`, { method: 'DELETE' });
        showToast(res.message, 'success');
        await loadEntradas();
    } catch (e) {
        // Toast já exibido
    }
}

// ═══════════════════════════════════════════
// ABA — PREÇOS
// ═══════════════════════════════════════════

async function loadPrecos() {
    showTableSkeleton('precos-list', 3, 3);
    const priceDisplay = document.getElementById('current-price');
    if (priceDisplay) priceDisplay.textContent = '...';
    
    try {
        const [ativoRes, historicoRes] = await Promise.all([
            api('/api/precos/ativo'),
            api('/api/precos')
        ]);

        // Preço atual
        document.getElementById('current-price').textContent =
            ativoRes.data ? formatCurrency(ativoRes.data.preco_unitario) : 'Não definido';

        // Tabela de histórico
        const tbody = document.getElementById('precos-list');
        if (historicoRes.data.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="3" class="empty-state">Nenhum preço definido</td></tr>';
            return;
        }

        tbody.innerHTML = historicoRes.data.map(p => `
            <tr>
                <td>${formatDate(p.data_inicio)}</td>
                <td><strong>${formatCurrency(p.preco_unitario)}</strong></td>
                <td>
                    ${p.ativo
                        ? '<span class="badge badge-success">Ativo</span>'
                        : '<span class="badge badge-inactive">Inativo</span>'}
                </td>
            </tr>
        `).join('');

    } catch (e) {
        console.error('Erro ao carregar preços:', e);
    }
}

// ═══════════════════════════════════════════
// ABA — RELATÓRIOS & GRÁFICOS
// ═══════════════════════════════════════════

async function loadRelatorios() {
    loadReportFilters();
    await loadReport();
}

function loadReportFilters() {
    const currentYear = new Date().getFullYear();

    // Selector de ano
    const yearSelect = document.getElementById('report-year');
    if (yearSelect.options.length === 0) {
        for (let y = currentYear; y >= currentYear - 5; y--) {
            const opt = document.createElement('option');
            opt.value = y;
            opt.textContent = y;
            if (y === currentYear) opt.selected = true;
            yearSelect.appendChild(opt);
        }
    }

    // Selector de mês
    const monthSelect = document.getElementById('report-month');
    if (monthSelect.options.length === 0) {
        const months = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ];
        const currentMonthNum = new Date().getMonth();
        months.forEach((m, i) => {
            const opt = document.createElement('option');
            opt.value = String(i + 1).padStart(2, '0');
            opt.textContent = m;
            if (i === currentMonthNum) opt.selected = true;
            monthSelect.appendChild(opt);
        });
    }
}

async function loadReport() {
    // Show loading on stat cards
    const reportStats = document.querySelectorAll('#tab-relatorios .stat-value');
    reportStats.forEach(el => el.textContent = '...');
    
    try {
        const month = document.getElementById('report-month').value;
        const year = document.getElementById('report-year').value;

        if (!month || !year) return;

        const mes = `${year}-${month}`;

        const [relatorioRes, anualRes] = await Promise.all([
            api(`/api/relatorio?mes=${mes}`),
            api(`/api/relatorio/anual?ano=${year}`)
        ]);

        const rel = relatorioRes.data;

        // Atualizar cards de resumo
        document.getElementById('report-entradas').textContent = rel.total_entradas;
        document.getElementById('report-saidas').textContent = rel.total_saidas;
        document.getElementById('report-quebrados').textContent = rel.total_quebrados || 0;
        document.getElementById('report-faturamento').textContent =
            formatCurrency(rel.faturamento_total);
        document.getElementById('report-despesas').textContent =
            formatCurrency(rel.total_despesas || 0);
        document.getElementById('report-lucro').textContent =
            formatCurrency(rel.lucro_estimado || 0);
        document.getElementById('report-saldo').textContent =
            rel.total_entradas - rel.total_saidas - (rel.total_quebrados || 0);

        // Atualizar gráficos
        updateCharts(anualRes.data);

    } catch (e) {
        console.error('Erro ao carregar relatório:', e);
    }
}

// ═══════════════════════════════════════════
// GRÁFICOS (Chart.js)
// ═══════════════════════════════════════════

function updateCharts(data) {
    // Add loading overlay to charts
    const chartsGrid = document.querySelector('.charts-grid');
    if (chartsGrid) chartsGrid.style.opacity = '0.6';
    
    const monthLabels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                         'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

    // Preparar dados para 12 meses
    const entradas = new Array(12).fill(0);
    const saidas = new Array(12).fill(0);
    const quebrados = new Array(12).fill(0);
    const faturamento = new Array(12).fill(0);

    data.forEach(d => {
        const idx = parseInt(d.mes_referencia.split('-')[1]) - 1;
        entradas[idx] = d.total_entradas;
        saidas[idx] = d.total_saidas;
        quebrados[idx] = d.total_quebrados || 0;
        faturamento[idx] = d.faturamento_total;
    });

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: { padding: 16, usePointStyle: true, font: { size: 12, weight: '600' } }
            }
        }
    };

    // ── Gráfico de Barras: Entradas vs Saídas ──
    if (charts.entradasSaidas) charts.entradasSaidas.destroy();
    charts.entradasSaidas = new Chart(
        document.getElementById('chart-entradas-saidas'), {
            type: 'bar',
            data: {
                labels: monthLabels,
                datasets: [
                    {
                        label: 'Entradas',
                        data: entradas,
                        backgroundColor: 'rgba(16, 185, 129, 0.75)',
                        borderColor: '#10b981',
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false
                    },
                    {
                        label: 'Saídas',
                        data: saidas,
                        backgroundColor: 'rgba(239, 68, 68, 0.75)',
                        borderColor: '#ef4444',
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false
                    },
                    {
                        label: 'Quebrados',
                        data: quebrados,
                        backgroundColor: 'rgba(190, 24, 93, 0.70)',
                        borderColor: '#be185d',
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: { font: { size: 11 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
        }
    );

    // ── Gráfico de Linha: Faturamento ──
    if (charts.faturamento) charts.faturamento.destroy();
    charts.faturamento = new Chart(
        document.getElementById('chart-faturamento'), {
            type: 'line',
            data: {
                labels: monthLabels,
                datasets: [{
                    label: 'Faturamento (R$)',
                    data: faturamento,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.08)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#6366f1',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: {
                            font: { size: 11 },
                            callback: value => 'R$ ' + value.toLocaleString('pt-BR')
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
        }
    );

    // ── Gráfico de Rosca: Distribuição ──
    const totalEntradas = entradas.reduce((a, b) => a + b, 0);
    const totalSaidas = saidas.reduce((a, b) => a + b, 0);
    const totalQuebrados = quebrados.reduce((a, b) => a + b, 0);
    const saldo = Math.max(0, totalEntradas - totalSaidas - totalQuebrados);

    if (charts.distribuicao) charts.distribuicao.destroy();
    charts.distribuicao = new Chart(
        document.getElementById('chart-distribuicao'), {
            type: 'doughnut',
            data: {
                labels: ['Vendido', 'Quebrados', 'Em Estoque'],
                datasets: [{
                    data: [totalSaidas, totalQuebrados, saldo],
                    backgroundColor: [
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(190, 24, 93, 0.8)',
                        'rgba(16, 185, 129, 0.8)'
                    ],
                    borderColor: ['#ef4444', '#be185d', '#10b981'],
                    borderWidth: 2,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 20, usePointStyle: true, font: { size: 13, weight: '600' } }
                    }
                }
            }
        }
    );
    
    // Remove loading overlay
    if (chartsGrid) chartsGrid.style.opacity = '1';
}

// ═══════════════════════════════════════════
// NAVEGAÇÃO DE MÊS
// ═══════════════════════════════════════════

function changeMonth(section, delta) {
    const [year, month] = currentMonth[section].split('-').map(Number);
    let newMonth = month + delta;
    let newYear = year;

    if (newMonth > 12) { newMonth = 1; newYear++; }
    if (newMonth < 1)  { newMonth = 12; newYear--; }

    currentMonth[section] = `${newYear}-${String(newMonth).padStart(2, '0')}`;

    if (section === 'entradas') loadEntradas();
    if (section === 'vendas') loadVendas();
    if (section === 'quebrados') loadQuebrados();
    if (section === 'despesas') loadDespesas();
}

// ═══════════════════════════════════════════
// ABA — PAINEL ADMIN
// ═══════════════════════════════════════════

async function loadAdminUsers() {
    showTableSkeleton('admin-users-list', 5, 3);
    
    try {
        const res = await api('/api/admin/usuarios');
        const tbody = document.getElementById('admin-users-list');

        if (res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhum usuário</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(u => `
            <tr>
                <td><strong>${u.nome || '—'}</strong></td>
                <td><code>${u.username}</code></td>
                <td>
                    ${u.is_admin
                        ? '<span class="badge badge-admin"><i class="fas fa-shield-alt"></i> Admin</span>'
                        : '<span class="badge badge-user"><i class="fas fa-user"></i> Usuário</span>'}
                </td>
                <td>${u.ultimo_login ? formatDate(u.ultimo_login) : '<em>Nunca</em>'}</td>
                <td>
                    <div class="admin-actions">
                        <button class="btn-admin-action btn-admin-reset"
                                onclick="adminResetPassword(${u.id}, '${u.username}')"
                                title="Redefinir senha">
                            <i class="fas fa-key"></i>
                        </button>
                        <button class="btn-admin-action btn-admin-delete"
                                onclick="adminDeleteUser(${u.id}, '${u.username}')"
                                title="Remover conta"
                                ${u.username === 'admin' ? 'disabled' : ''}>
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

    } catch (e) {
        console.error('Erro ao carregar usuários:', e);
    }
}

async function adminCreateUser(username, password, nome, isAdmin) {
    try {
        const res = await api('/api/admin/usuarios', {
            method: 'POST',
            body: JSON.stringify({ username, password, nome, is_admin: isAdmin })
        });
        showToast(res.message, 'success');
        await loadAdminUsers();
    } catch {
        // Toast já exibido
    }
}

async function adminDeleteUser(userId, username) {
    const ok = await customConfirm('Remover Conta', `Remover a conta "${username}"? Essa ação não pode ser desfeita.`);
    if (!ok) return;
    try {
        const res = await api(`/api/admin/usuarios/${userId}`, { method: 'DELETE' });
        showToast(res.message, 'success');
        await loadAdminUsers();
    } catch {
        // Toast já exibido
    }
}

function adminResetPassword(userId, username) {
    showResetPassword(userId, username);
}

// ═══════════════════════════════════════════
// EVENT LISTENERS & INICIALIZAÇÃO
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

    // ── Autenticação: verificar sessão ──
    checkAuth().then(authenticated => {
        if (authenticated) loadEstoque();
    });

    // ── Formulário: Login ──
    document.getElementById('form-login').addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        doLogin(username, password);
    });

    // ── Formulário: Alterar Senha ──
    document.getElementById('form-alterar-senha').addEventListener('submit', async (e) => {
        e.preventDefault();
        const senhaAtual = document.getElementById('senha-atual').value;
        const novaSenha = document.getElementById('nova-senha').value;
        const confirmar = document.getElementById('confirmar-senha').value;

        if (novaSenha.length < 4) {
            showToast('Nova senha deve ter no mínimo 4 caracteres', 'error');
            return;
        }
        if (novaSenha !== confirmar) {
            showToast('As senhas não coincidem', 'error');
            return;
        }
        await doChangePassword(senhaAtual, novaSenha);
    });

    // ── Fechar modal ao clicar no fundo ──
    document.getElementById('modal-senha').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) hideChangePassword();
    });

    // ── Fechar modal reset senha ao clicar no fundo ──
    document.getElementById('modal-reset-senha').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) hideResetPassword();
    });

    // ── Formulário: Redefinir Senha (Admin) ──
    document.getElementById('form-reset-senha').addEventListener('submit', async (e) => {
        e.preventDefault();
        const userId = document.getElementById('reset-senha-user-id').value;
        const username = document.getElementById('reset-senha-username').value;
        const novaSenha = document.getElementById('reset-nova-senha').value;
        const confirmar = document.getElementById('reset-confirmar-senha').value;

        if (novaSenha.length < 4) {
            showToast('Senha deve ter no mínimo 4 caracteres', 'error');
            return;
        }
        if (novaSenha !== confirmar) {
            showToast('As senhas não coincidem', 'error');
            return;
        }

        await doResetPassword(userId, username, novaSenha);
        hideResetPassword();
    });

    // ── Formulário: Criar Usuário (Admin) ──
    document.getElementById('form-criar-usuario').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        try {
            btn.innerHTML = '<span class="spinner"></span> Criando...';
            btn.disabled = true;

            const nome = document.getElementById('new-user-nome').value.trim();
            const username = document.getElementById('new-user-username').value.trim();
            const password = document.getElementById('new-user-password').value;
            const isAdmin = document.getElementById('new-user-admin').checked;

            await adminCreateUser(username, password, nome, isAdmin);
            e.target.reset();
        } catch {
            // Toast já exibido
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // ── Navegação por abas ──
    document.querySelectorAll('.nav-links li').forEach(li => {
        li.addEventListener('click', () => switchTab(li.dataset.tab));
    });

    // ── Menu mobile ──
    const mobileBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.getElementById('sidebar');
    mobileBtn.addEventListener('click', () => sidebar.classList.toggle('open'));

    // Fechar sidebar ao clicar fora (mobile)
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 &&
            !sidebar.contains(e.target) &&
            !mobileBtn.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });

    // ── Formulário: Entrada ──
    document.getElementById('form-entrada').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        try {
            btn.innerHTML = '<span class="spinner"></span> Registrando...';
            btn.disabled = true;

            const quantidade = parseInt(document.getElementById('entrada-quantidade').value);
            const observacao = document.getElementById('entrada-observacao').value.trim();

            if (isNaN(quantidade) || quantidade <= 0) {
                showToast('Quantidade deve ser um número positivo', 'error');
                return;
            }

            const res = await api('/api/entradas', {
                method: 'POST',
                body: JSON.stringify({ quantidade, observacao })
            });

            showToast(res.message, 'success');
            e.target.reset();
            await loadEntradas();

        } catch (err) {
            // Toast já exibido pelo api()
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // ── Formulário: Venda ──
    document.getElementById('form-venda').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        try {
            btn.innerHTML = '<span class="spinner"></span> Registrando...';
            btn.disabled = true;

            const quantidade = parseInt(document.getElementById('venda-quantidade').value);
            const preco_unitario = parseDecimalInput(document.getElementById('venda-preco').value);

            if (isNaN(quantidade) || quantidade <= 0) {
                showToast('Quantidade deve ser um número positivo', 'error');
                return;
            }
            if (isNaN(preco_unitario) || preco_unitario < 0) {
                showToast('Preço unitário inválido', 'error');
                return;
            }

            const res = await api('/api/saidas', {
                method: 'POST',
                body: JSON.stringify({ quantidade, preco_unitario })
            });

            showToast(res.message, 'success');
            document.getElementById('venda-quantidade').value = '';
            document.getElementById('venda-preco').value = '';
            document.getElementById('venda-total').value = '';
            lastEditedField = null;
            await loadVendas();

        } catch (err) {
            // Toast já exibido
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    document.getElementById('venda-quantidade').addEventListener('input', () => {
        if (lastEditedField === 'total') {
            updateVendaUnitPrice();
        } else {
            updateVendaTotal();
        }
    });
    
    document.getElementById('venda-preco').addEventListener('input', () => {
        lastEditedField = 'price';
        updateVendaTotal();
    });
    
    document.getElementById('venda-total').addEventListener('input', () => {
        lastEditedField = 'total';
        updateVendaUnitPrice();
    });

    // ── Formulário: Quebrados ──
    document.getElementById('form-quebrado').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        try {
            btn.innerHTML = '<span class="spinner"></span> Registrando...';
            btn.disabled = true;

            const quantidade = parseInt(document.getElementById('quebrado-quantidade').value);
            const motivo = document.getElementById('quebrado-motivo').value.trim();

            if (isNaN(quantidade) || quantidade <= 0) {
                showToast('Quantidade deve ser um número positivo', 'error');
                return;
            }

            const res = await api('/api/quebrados', {
                method: 'POST',
                body: JSON.stringify({ quantidade, motivo })
            });

            showToast(res.message, 'success');
            e.target.reset();
            await loadQuebrados();

        } catch (err) {
            // Toast já exibido pelo api()
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // ── Formulário: Despesas ──
    document.getElementById('form-despesa').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        try {
            btn.innerHTML = '<span class="spinner"></span> Registrando...';
            btn.disabled = true;

            const valor = parseFloat(document.getElementById('despesa-valor').value);
            const descricao = document.getElementById('despesa-descricao').value.trim();

            if (isNaN(valor) || valor <= 0) {
                showToast('Valor deve ser um número positivo', 'error');
                return;
            }
            if (!descricao) {
                showToast('Descrição é obrigatória', 'error');
                return;
            }

            const res = await api('/api/despesas', {
                method: 'POST',
                body: JSON.stringify({ valor, descricao })
            });

            showToast(res.message, 'success');
            e.target.reset();
            await loadDespesas();

        } catch (err) {
            // Toast já exibido pelo api()
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // ── Formulário: Preço ──
    document.getElementById('form-preco').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        try {
            btn.innerHTML = '<span class="spinner"></span> Salvando...';
            btn.disabled = true;

            const preco_unitario = parseFloat(document.getElementById('novo-preco').value);

            if (isNaN(preco_unitario) || preco_unitario < 0) {
                showToast('Preço deve ser um número não negativo', 'error');
                return;
            }

            const res = await api('/api/precos', {
                method: 'POST',
                body: JSON.stringify({ preco_unitario })
            });

            showToast(res.message, 'success');
            e.target.reset();
            await loadPrecos();

            // Atualizar preço no formulário de vendas
            document.getElementById('venda-preco').value = preco_unitario;

        } catch (err) {
            // Toast já exibido
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // ── Carregamento inicial (feito via checkAuth acima) ──
});
