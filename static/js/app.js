let currentTab = 'estoque';
const currentMonth = {
    entradas: getCurrentMonth(),
    vendas: getCurrentMonth(),
    quebrados: getCurrentMonth(),
    relatorios: getCurrentMonth()
};
const charts = {};

// ═══════════════════════════════════════════
// FUNÇÕES UTILITÁRIAS
// ═══════════════════════════════════════════

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

// ═══════════════════════════════════════════
// API WRAPPER
// ═══════════════════════════════════════════

async function api(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
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

// ═══════════════════════════════════════════
// NOTIFICAÇÕES TOAST
// ═══════════════════════════════════════════

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
// NAVEGAÇÃO POR ABAS
// ═══════════════════════════════════════════

function switchTab(tabName) {
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
        case 'precos':     await loadPrecos(); break;
        case 'relatorios': await loadRelatorios(); break;
    }
}

// ═══════════════════════════════════════════
// ABA — ESTOQUE (Dashboard)
// ═══════════════════════════════════════════

async function loadEstoque() {
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
        document.getElementById('stat-preco-atual').textContent =
            preco ? formatCurrency(preco.preco_unitario) : 'Não definido';

        // Última atualização
        document.getElementById('last-update').textContent =
            `Última atualização: ${formatDate(estoque.ultima_atualizacao)}`;

    } catch (e) {
        console.error('Erro ao carregar estoque:', e);
    }
}

// ═══════════════════════════════════════════
// ABA — ENTRADAS
// ═══════════════════════════════════════════

async function loadEntradas() {
    try {
        const mes = currentMonth.entradas;
        document.getElementById('entradas-month-label').textContent = formatMonthLabel(mes);

        const res = await api(`/api/entradas?mes=${mes}`);
        const tbody = document.getElementById('entradas-list');

        if (res.data.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="3" class="empty-state">Nenhuma entrada registrada neste mês</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(e => `
            <tr>
                <td>${formatDate(e.data)}</td>
                <td><strong>${e.quantidade}</strong> ovos</td>
                <td>${e.observacao || '—'}</td>
            </tr>
        `).join('');

    } catch (e) {
        console.error('Erro ao carregar entradas:', e);
    }
}

// ═══════════════════════════════════════════
// ABA — VENDAS
// ═══════════════════════════════════════════

async function loadVendas() {
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
        const tbody = document.getElementById('vendas-list');

        if (res.data.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="4" class="empty-state">Nenhuma venda registrada neste mês</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(s => `
            <tr>
                <td>${formatDate(s.data)}</td>
                <td><strong>${s.quantidade}</strong></td>
                <td>${formatCurrency(s.preco_unitario)}</td>
                <td><strong>${formatCurrency(s.valor_total)}</strong></td>
            </tr>
        `).join('');

    } catch (e) {
        console.error('Erro ao carregar vendas:', e);
    }
}

function updateVendaTotal() {
    const qty = parseInt(document.getElementById('venda-quantidade').value) || 0;
    const price = parseFloat(document.getElementById('venda-preco').value) || 0;
    document.getElementById('venda-total').textContent = formatCurrency(qty * price);
}

// ═══════════════════════════════════════════
// ABA — OVOS QUEBRADOS
// ═══════════════════════════════════════════

async function loadQuebrados() {
    try {
        const mes = currentMonth.quebrados;
        document.getElementById('quebrados-month-label').textContent = formatMonthLabel(mes);

        // Carregar estoque disponível
        const estoqueRes = await api('/api/estoque');
        document.getElementById('quebrado-stock-qty').textContent =
            estoqueRes.data.quantidade_total;

        // Carregar lista de quebrados
        const res = await api(`/api/quebrados?mes=${mes}`);
        const tbody = document.getElementById('quebrados-list');

        // Calcular total do mês
        const totalMes = res.data.reduce((sum, q) => sum + q.quantidade, 0);
        document.getElementById('quebrados-month-total').textContent = totalMes;

        if (res.data.length === 0) {
            tbody.innerHTML =
                '<tr><td colspan="4" class="empty-state">Nenhum registro de quebra neste mês</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(q => `
            <tr>
                <td>${formatDate(q.data)}</td>
                <td><strong>${q.quantidade}</strong> ovos</td>
                <td>${q.motivo || '—'}</td>
                <td>
                    <button class="btn-undo" onclick="undoQuebrado(${q.id})" title="Desfazer — devolver ao estoque">
                        <i class="fas fa-undo"></i> Desfazer
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (e) {
        console.error('Erro ao carregar quebrados:', e);
    }
}

async function undoQuebrado(entryId) {
    try {
        const res = await api(`/api/quebrados/${entryId}`, { method: 'DELETE' });
        showToast(res.message, 'success');
        await loadQuebrados();
    } catch (e) {
        // Toast já exibido
    }
}

// ═══════════════════════════════════════════
// ABA — PREÇOS
// ═══════════════════════════════════════════

async function loadPrecos() {
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
}

// ═══════════════════════════════════════════
// EVENT LISTENERS & INICIALIZAÇÃO
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

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
            const preco_unitario = parseFloat(document.getElementById('venda-preco').value);

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
            document.getElementById('venda-total').textContent = 'R$ 0,00';
            await loadVendas();

        } catch (err) {
            // Toast já exibido
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    });

    // ── Auto-cálculo de valor total na venda ──
    document.getElementById('venda-quantidade').addEventListener('input', updateVendaTotal);
    document.getElementById('venda-preco').addEventListener('input', updateVendaTotal);

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

    // ── Carregamento inicial ──
    loadEstoque();
});
