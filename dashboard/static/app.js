// State Management
const state = {
    tenant: 'bitnet',
    data: null,
    lastValidData: null,
    isError: false,
    filterUf: '',
    filterStatus: '',
    searchQuery: '',
    activeTab: 'todos', // 'todos', 'critico', 'aguardar'
    currentView: 'view-overview'
};

// DOM Elements
const els = {
    btnToggleSidebar: document.getElementById('btn-toggle-sidebar'),
    btnMobileMenu: document.getElementById('btn-mobile-menu'),
    sidebar: document.getElementById('sidebar'),
    navItems: document.querySelectorAll('.nav-item'),
    views: document.querySelectorAll('.view'),
    pageTitle: document.getElementById('page-title'),
    
    tenantBtns: document.querySelectorAll('.tenant-btn'),
    
    // Saúde das Fontes (Health)
    health: {
        omadaDot: document.getElementById('health-dot-omada'),
        omadaBadge: document.getElementById('health-badge-omada'),
        eaceDot: document.getElementById('health-dot-eace'),
        eaceBadge: document.getElementById('health-badge-eace'),
        sheetsDot: document.getElementById('health-dot-sheets'),
        sheetsBadge: document.getElementById('health-badge-sheets')
    },
    
    syncStatus: document.getElementById('sync-status'),
    syncDot: document.querySelector('.sync-dot'),
    syncText: document.getElementById('sync-text'),
    btnRefresh: document.getElementById('btn-refresh'),
    
    // Overview
    kpiCritical: document.getElementById('kpi-critical'),
    kpiWait: document.getElementById('kpi-wait'),
    kpiOs: document.getElementById('kpi-os'),
    kpiRecovery: document.getElementById('kpi-recovery'),
    tableOverview: document.querySelector('#table-overview tbody'),
    recentActivityList: document.getElementById('recent-activity-list'),
    
    // Incidents Fila
    tableIncidents: document.querySelector('#table-incidents tbody'),
    filterUf: document.getElementById('filter-uf'),
    filterStatus: document.getElementById('filter-status'),
    btnClearFilters: document.getElementById('btn-clear-filters'),
    searchInput: document.querySelector('.search-input'),
    tabs: document.querySelectorAll('.tab'),
    countTodos: document.getElementById('count-todos'),
    countCritico: document.getElementById('count-critico'),
    countAguardar: document.getElementById('count-aguardar'),
    
    // Novas Views
    tableOs: document.querySelector('#table-os tbody'),
    tableRecoveries: document.querySelector('#table-recoveries tbody'),
    
    // Drawer
    drawerOverlay: document.getElementById('drawer-overlay'),
    drawer: document.getElementById('drawer-details'),
    btnCloseDrawer: document.getElementById('btn-close-drawer'),
    
    drawerSchool: document.getElementById('drawer-school'),
    drawerLocation: document.getElementById('drawer-location'),
    drawerTime: document.getElementById('drawer-time'),
    drawerBadge: document.getElementById('drawer-badge'),
    drawerInep: document.getElementById('drawer-inep'),
    drawerIp: document.getElementById('drawer-ip'),
    drawerRule: document.getElementById('drawer-rule'),
    drawerPartner: document.getElementById('drawer-partner'),
    drawerCad: document.getElementById('drawer-cad'),
    drawerTimeline: document.getElementById('drawer-timeline')
};

// Initialization
function init() {
    setupEventListeners();
    fetchData();
    setInterval(fetchData, 30000); // 30s auto-refresh
}

// Event Listeners
function setupEventListeners() {
    // Sidebar Toggle
    els.btnToggleSidebar.addEventListener('click', () => {
        els.sidebar.classList.toggle('collapsed');
    });
    els.btnMobileMenu.addEventListener('click', () => {
        els.sidebar.classList.toggle('open-mobile');
    });

    // Navigation
    els.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const targetId = e.currentTarget.getAttribute('data-target');
            switchView(targetId);
            els.navItems.forEach(n => n.classList.remove('active'));
            e.currentTarget.classList.add('active');
            
            // Close mobile menu if open
            if(window.innerWidth <= 768) {
                els.sidebar.classList.remove('open-mobile');
            }
        });
    });

    // Tenant switch is handled inline via switchTenant(tenant)

    // Manual Refresh
    els.btnRefresh.addEventListener('click', fetchData);
    
    // Drawer Close
    els.btnCloseDrawer.addEventListener('click', closeDrawer);
    els.drawerOverlay.addEventListener('click', closeDrawer);

    // Filters
    els.filterUf.addEventListener('change', (e) => { state.filterUf = e.target.value; renderIncidents(); });
    els.filterStatus.addEventListener('change', (e) => { state.filterStatus = e.target.value; renderIncidents(); });
    els.btnClearFilters.addEventListener('click', () => {
        els.filterUf.value = '';
        els.filterStatus.value = '';
        els.searchInput.value = '';
        state.filterUf = '';
        state.filterStatus = '';
        state.searchQuery = '';
        renderIncidents();
    });
    els.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.toLowerCase();
        renderOverview();
        renderIncidents();
    });

    // Tabs
    els.tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            els.tabs.forEach(t => t.classList.remove('active'));
            const target = e.currentTarget;
            target.classList.add('active');
            state.activeTab = target.getAttribute('data-tab');
            renderIncidents();
        });
    });
}

// Routing (SPA)
function switchView(viewId) {
    state.currentView = viewId;
    els.views.forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    
    const titles = {
        'view-overview': 'Visão Geral',
        'view-incidents': 'Fila de Incidentes',
        'view-os': 'OS em Andamento',
        'view-recoveries': 'Recuperações Pendentes',
        'view-quality': 'Qualidade Cadastral',
        'view-history': 'Histórico de Operações'
    };
    els.pageTitle.textContent = titles[viewId] || 'NOC Operations Center';
    
    if(viewId === 'view-incidents') {
        renderIncidents();
    } else if(viewId === 'view-overview') {
        renderOverview();
    } else if(viewId === 'view-os') {
        renderOs();
    } else if(viewId === 'view-recoveries') {
        renderRecoveries();
    }
}

// Função para Navegar a partir dos Cards de KPI
window.navigateFromKpi = function(kpiType) {
    if (kpiType === 'critical') {
        document.querySelector('.nav-item[data-target="view-incidents"]').click();
        els.filterStatus.value = "CRÍTICO";
        els.filterStatus.dispatchEvent(new Event('change'));
        const tab = document.querySelector('.tab[data-tab="critico"]');
        if (tab) tab.click();
    } else if (kpiType === 'wait') {
        document.querySelector('.nav-item[data-target="view-incidents"]').click();
        els.filterStatus.value = "AGUARDAR";
        els.filterStatus.dispatchEvent(new Event('change'));
        const tab = document.querySelector('.tab[data-tab="aguardar"]');
        if (tab) tab.click();
    } else if (kpiType === 'os') {
        document.querySelector('.nav-item[data-target="view-os"]').click();
    } else if (kpiType === 'recovery') {
        document.querySelector('.nav-item[data-target="view-recoveries"]').click();
    }
};

// Tenant Switching
window.switchTenant = function(tenant) {
    if(state.tenant === tenant) return;
    state.tenant = tenant;
    
    els.tenantBtns.forEach(btn => {
        btn.setAttribute('aria-pressed', btn.id === `btn-tenant-${tenant}`);
    });

    if (tenant === 'st1') {
        document.documentElement.style.setProperty('--brand-active', 'var(--brand-st1)');
    } else {
        document.documentElement.style.setProperty('--brand-active', 'var(--brand-bitnet)');
    }

    // Limpa a tela mostrando os skeletons (Opcional mas dá feedback imediato)
    els.tableOverview.innerHTML = '<tr><td colspan="5"><div class="skeleton sk-text"></div></td></tr>';
    els.tableIncidents.innerHTML = '<tr><td colspan="7"><div class="skeleton sk-text"></div></td></tr>';
    if(els.tableOs) els.tableOs.innerHTML = '<tr><td colspan="5"><div class="skeleton sk-text"></div></td></tr>';
    if(els.tableRecoveries) els.tableRecoveries.innerHTML = '<tr><td colspan="5"><div class="skeleton sk-text"></div></td></tr>';

    // Sempre busca os dados novos ao trocar
    fetchData();
};

// API Fetch
async function fetchData() {
    setSyncState('syncing', 'Atualizando...');
    const API_KEY = window.NOC_API_KEY || 'noc-key-secret';
    
    try {
        const response = await fetch(`/api/v1/dashboard?tenant=${state.tenant}&t=${Date.now()}`, {
            headers: { 'X-API-KEY': API_KEY }
        });
        
        if (!response.ok) throw new Error('API Error');
        
        const data = await response.json();
        
        // Se a API retornar vazio, usar mock para validação visual (ajuda em homologação)
        if(!data || !data.falta_abrir) {
            console.warn("API retornou sem dados principais. Usando Mock local para testes visuais.");
            state.data = generateMockData();
        } else {
            state.data = data;
        }
        
        state.lastValidData = state.data;
        state.isError = false;
        
        // Verifica staleness (Ex: timestamp mais antigo que 10 min)
        const ts = state.data.timestamp ? new Date(state.data.timestamp).getTime() : Date.now();
        const diffMin = (Date.now() - ts) / 60000;
        
        if (diffMin > 10) {
            setSyncState('warning', `Dados Atrasados (${Math.floor(diffMin)}m)`);
        } else {
            setSyncState('success', 'Atualizado agora');
        }
        
        updateUI();
    } catch (err) {
        console.error("Fetch Error:", err);
        state.isError = true;
        if(state.lastValidData) {
            setSyncState('error', 'API Falhou (Último Snapshot)');
        } else {
            setSyncState('error', 'Fonte Indisponível');
            // Se falhou e não tem nada, usa Mock para não ficar tela preta na homologação
            state.data = generateMockData();
            state.lastValidData = state.data;
            updateUI();
        }
    }
}

function setSyncState(status, text) {
    els.syncDot.className = 'sync-dot';
    els.syncStatus.style.border = '1px solid var(--border-subtle)';
    els.syncStatus.style.background = 'var(--bg-surface)';
    
    if (status === 'syncing') {
        els.syncDot.classList.add('syncing');
    } else if (status === 'error') {
        els.syncDot.classList.add('error');
        els.syncStatus.style.border = '1px solid var(--status-critical)';
        els.syncStatus.style.background = 'rgba(255, 100, 124, 0.1)';
    } else if (status === 'warning') {
        els.syncDot.style.background = 'var(--status-warning)';
        els.syncStatus.style.border = '1px solid var(--status-warning)';
        els.syncStatus.style.background = 'rgba(245, 184, 75, 0.1)';
    }
    els.syncText.textContent = text;
}

// Update Global UI
function updateUI() {
    if(!state.lastValidData) return;
    
    populateUfFilter();
    updateKPIs();
    
    if(state.currentView === 'view-overview') {
        renderOverview();
    } else if(state.currentView === 'view-incidents') {
        renderIncidents();
    } else if(state.currentView === 'view-os') {
        renderOs();
    } else if(state.currentView === 'view-recoveries') {
        renderRecoveries();
    }
}

function populateUfFilter() {
    const list = state.lastValidData.falta_abrir || [];
    const ufs = new Set();
    list.forEach(item => {
        if(item['UF'] && item['UF'] !== "-") {
            ufs.add(item['UF'].trim());
        }
    });
    
    // Preserve current selection
    const curr = els.filterUf.value;
    els.filterUf.innerHTML = '<option value="">UF: Todas</option>';
    Array.from(ufs).sort().forEach(uf => {
        if(!uf) return;
        const opt = document.createElement('option');
        opt.value = uf;
        opt.textContent = uf;
        els.filterUf.appendChild(opt);
    });
    els.filterUf.value = curr;
}

function updateKPIs() {
    const list = state.lastValidData.falta_abrir || [];
    let criticalCount = 0;
    let waitCount = 0;
    
    list.forEach(item => {
        const regra = item["Regra de Abertura (4h Offline)"] || "";
        if(regra.includes('🚨')) criticalCount++;
        else if(regra.includes('⏳')) waitCount++;
    });
    
    els.kpiCritical.textContent = criticalCount;
    els.kpiWait.textContent = waitCount;
    
    // Values from JSON snapshot
    const osAbertasCount = (state.lastValidData.abertos || []).length;
    const recupCount = (state.lastValidData.fechar || []).length;
    
    els.kpiOs.textContent = osAbertasCount;
    els.kpiRecovery.textContent = recupCount;
    
    // Atualiza Saúde das Fontes
    const health = state.lastValidData.health || { omada: 'ok', eace: 'ok', sheets: 'ok' };
    
    function setHealthUI(dotEl, badgeEl, statusStr) {
        if (!dotEl || !badgeEl) return;
        if (statusStr === 'error') {
            dotEl.className = 'sync-dot error';
            badgeEl.className = 'badge badge-critical';
            badgeEl.textContent = 'FALHA';
        } else {
            dotEl.className = 'sync-dot';
            badgeEl.className = 'badge badge-success';
            badgeEl.textContent = 'OK';
        }
    }
    
    setHealthUI(els.health.omadaDot, els.health.omadaBadge, health.omada);
    setHealthUI(els.health.eaceDot, els.health.eaceBadge, health.eace);
    setHealthUI(els.health.sheetsDot, els.health.sheetsBadge, health.sheets);
    
    els.countTodos.textContent = list.length;
    els.countCritico.textContent = criticalCount;
    els.countAguardar.textContent = waitCount;
}

// Render Table (Overview)
function renderOverview() {
    els.tableOverview.innerHTML = '';
    const list = state.lastValidData.falta_abrir || [];
    
    // Sort and limit to 8 prioritizing CRÍTICO
    let sorted = [...list].sort((a,b) => {
        const aCrit = (a["Regra de Abertura (4h Offline)"] || "").includes('🚨') ? 1 : 0;
        const bCrit = (b["Regra de Abertura (4h Offline)"] || "").includes('🚨') ? 1 : 0;
        return bCrit - aCrit;
    });
    
    // Filter by search
    if(state.searchQuery) {
        sorted = sorted.filter(item => {
            const inep = item['INEP_Extraido'] || item['INEP'] || '';
            const name = item['Nome da Escola'] || item['Escola'] || '';
            const nameField = item['NAME'] || item['Nome'] || '';
            const str = (name + inep + nameField).toLowerCase();
            return str.includes(state.searchQuery);
        });
    }

    const sliced = sorted.slice(0, 8);
    
    if(sliced.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 5;
        td.style.textAlign = 'center';
        td.style.padding = '32px';
        td.style.color = 'var(--text-secondary)';
        td.textContent = 'Nenhuma ocorrência encontrada na Fila Prioritária.';
        tr.appendChild(td);
        els.tableOverview.appendChild(tr);
        return;
    }

    sliced.forEach(item => {
        const inep = item['INEP_Extraido'] || item['INEP'] || '-';
        const name = item['Nome da Escola'] || item['Escola'] || 'Desconhecida';
        const nameField = item['NAME'] || item['Nome'] || '';
        
        let localidade = '-';
        if (item['Município'] && item['UF'] && item['Município'] !== '-' && item['UF'] !== '-') {
            localidade = `${item['Município']} / ${item['UF']}`;
        } else if (nameField.includes('-')) {
            localidade = nameField.split('-')[0].trim();
        } else {
            localidade = nameField || '-';
        }
        
        const rule = item["Regra de Abertura (4h Offline)"] || "";
        const isCritical = rule.includes('🚨');
        const timeOffline = rule.includes('- Offline há ') ? rule.split('- Offline há ')[1] : '-';
        
        const tr = document.createElement('tr');
        tr.className = `priority-row ${isCritical ? 'critical' : ''}`;
        
        // Status Badge
        const tdStatus = document.createElement('td');
        const spanBadge = document.createElement('span');
        if(isCritical) {
            spanBadge.className = 'badge badge-critical';
            spanBadge.textContent = '🚨 CRÍTICO';
        } else {
            spanBadge.className = 'badge badge-warning';
            spanBadge.textContent = '⏳ AGUARDAR';
        }
        tdStatus.appendChild(spanBadge);
        
        // Escola
        const tdEscola = document.createElement('td');
        const divE = document.createElement('div');
        divE.textContent = name;
        divE.style.fontWeight = '500';
        const divI = document.createElement('div');
        divI.textContent = inep;
        divI.className = 'text-ter';
        divI.style.fontSize = '11px';
        tdEscola.appendChild(divE);
        tdEscola.appendChild(divI);
        
        // Localidade
        const tdLoc = document.createElement('td');
        tdLoc.textContent = localidade;
        
        // Tempo Offline
        const tdTime = document.createElement('td');
        const divT = document.createElement('div');
        divT.textContent = timeOffline;
        const divU = document.createElement('div');
        divU.textContent = item["Uptime"] || "-";
        divU.className = 'text-ter';
        divU.style.fontSize = '11px';
        tdTime.appendChild(divT);
        tdTime.appendChild(divU);
        
        // Ação
        const tdAct = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.textContent = 'Detalhes';
        btn.onclick = (e) => { e.stopPropagation(); openDrawer(item); };
        tdAct.appendChild(btn);
        
        tr.onclick = () => openDrawer(item);
        
        tr.appendChild(tdStatus);
        tr.appendChild(tdEscola);
        tr.appendChild(tdLoc);
        tr.appendChild(tdTime);
        tr.appendChild(tdAct);
        
        els.tableOverview.appendChild(tr);
    });

    renderActivityMock();
}

function renderActivityMock() {
    els.recentActivityList.innerHTML = '';
    const mocks = [
        { time: '11:24', text: 'Escola Municipal Ceará reportada offline no Omada', crit: false },
        { time: '11:15', text: 'INEP 3522201 atingiu SLA de 4h (Crítico)', crit: true },
        { time: '11:00', text: 'Sincronização com Google Sheets finalizada (30ms)', crit: false },
        { time: '10:42', text: 'OS 20260012 fechada no sistema EACE', crit: false },
    ];
    mocks.forEach(m => {
        const div = document.createElement('div');
        div.className = 'event-item';
        
        const time = document.createElement('div');
        time.className = 'event-time';
        time.textContent = m.time;
        
        const content = document.createElement('div');
        content.className = 'event-content';
        if(m.crit) content.style.color = 'var(--status-critical)';
        content.textContent = m.text;
        
        div.appendChild(time);
        div.appendChild(content);
        els.recentActivityList.appendChild(div);
    });
}

// Render Table (Incidents Full)
function renderIncidents() {
    els.tableIncidents.innerHTML = '';
    const list = state.lastValidData.falta_abrir || [];
    
    let filtered = list.filter(item => {
        const rule = item["Regra de Abertura (4h Offline)"] || "";
        const inep = item['INEP_Extraido'] || item['INEP'] || '';
        const name = item['Nome da Escola'] || item['Escola'] || '';
        const nameField = item['NAME'] || item['Nome'] || '';
        
        // Tab Filter
        if(state.activeTab === 'critico' && !rule.includes('🚨')) return false;
        if(state.activeTab === 'aguardar' && !rule.includes('⏳')) return false;
        
        // Dropdown UF
        if(state.filterUf) {
            if(item['UF'] !== state.filterUf) return false;
        }
        
        // Dropdown Status
        if(state.filterStatus === 'CRÍTICO' && !rule.includes('🚨')) return false;
        if(state.filterStatus === 'AGUARDAR' && !rule.includes('⏳')) return false;
        
        // Search
        if(state.searchQuery) {
            const str = (name + inep + nameField).toLowerCase();
            if(!str.includes(state.searchQuery)) return false;
        }
        
        return true;
    });
    
    if(filtered.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 7;
        td.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                <h3>Nenhum resultado encontrado</h3>
                <p>Altere os filtros ou a busca para tentar novamente.</p>
            </div>
        `;
        tr.appendChild(td);
        els.tableIncidents.appendChild(tr);
        return;
    }

    filtered.forEach(item => {
        const inep = item['INEP_Extraido'] || item['INEP'] || '-';
        const name = item['Nome da Escola'] || item['Escola'] || 'Desconhecida';
        const nameField = item['NAME'] || item['Nome'] || '';
        
        let localidade = '-';
        if (item['Município'] && item['UF'] && item['Município'] !== '-' && item['UF'] !== '-') {
            localidade = `${item['Município']} / ${item['UF']}`;
        } else if (nameField.includes('-')) {
            localidade = nameField.split('-')[0].trim();
        } else {
            localidade = nameField || '-';
        }
        
        const rule = item["Regra de Abertura (4h Offline)"] || "";
        const isCritical = rule.includes('🚨');
        const timeOffline = rule.includes('- Offline há ') ? rule.split('- Offline há ')[1] : '-';
        
        const tr = document.createElement('tr');
        
        // Status Badge
        const tdStatus = document.createElement('td');
        const spanBadge = document.createElement('span');
        if(isCritical) {
            spanBadge.className = 'badge badge-critical';
            spanBadge.textContent = 'CRÍTICO';
        } else {
            spanBadge.className = 'badge badge-warning';
            spanBadge.textContent = 'AGUARDAR';
        }
        tdStatus.appendChild(spanBadge);
        
        // Escola
        const tdEscola = document.createElement('td');
        tdEscola.textContent = name;
        
        // Localidade
        const tdLoc = document.createElement('td');
        tdLoc.textContent = localidade;
        
        // INEP
        const tdInep = document.createElement('td');
        tdInep.textContent = inep;
        
        // Tempo Offline
        const tdTime = document.createElement('td');
        tdTime.textContent = timeOffline;
        
        // Qualidade
        const tdQual = document.createElement('td');
        const qual = document.createElement('span');
        if(name === 'N/A' || !item['Nome da Escola']) {
            qual.className = 'badge badge-warning';
            qual.textContent = 'Sem Cadastro';
        } else {
            qual.className = 'badge badge-neutral';
            qual.textContent = 'OK';
        }
        tdQual.appendChild(qual);
        
        // Ação
        const tdAct = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.textContent = 'Ver';
        btn.onclick = (e) => { e.stopPropagation(); openDrawer(item); };
        tdAct.appendChild(btn);
        
        tr.onclick = () => openDrawer(item);
        
        tr.appendChild(tdStatus);
        tr.appendChild(tdEscola);
        tr.appendChild(tdLoc);
        tr.appendChild(tdInep);
        tr.appendChild(tdTime);
        tr.appendChild(tdQual);
        tr.appendChild(tdAct);
        
        els.tableIncidents.appendChild(tr);
    });
}

// Render OS em Andamento
function renderOs() {
    if(!els.tableOs) return;
    els.tableOs.innerHTML = '';
    const list = state.lastValidData.abertos || [];
    
    if(list.length === 0) {
        els.tableOs.innerHTML = `<tr><td colspan="5"><div class="empty-state"><h3>Nenhuma OS em Andamento</h3></div></td></tr>`;
        return;
    }
    
    list.forEach(item => {
        const inep = item['INEP_Extraido'] || item['INEP'] || '-';
        const name = item['Nome da Escola'] || item['Escola'] || 'Desconhecida';
        const ticket = item['Ticket#'] || 'S/N';
        const status = item['Status'] || 'Em Análise';
        
        const tr = document.createElement('tr');
        
        const tdTicket = document.createElement('td');
        const badgeTicket = document.createElement('span');
        badgeTicket.className = 'badge badge-info';
        badgeTicket.textContent = ticket;
        tdTicket.appendChild(badgeTicket);
        
        const tdStatus = document.createElement('td');
        tdStatus.textContent = status;
        
        const tdEscola = document.createElement('td');
        tdEscola.textContent = name;
        
        const tdInep = document.createElement('td');
        tdInep.textContent = inep;
        
        const tdAcao = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.textContent = 'Copiar Resumo';
        btn.onclick = () => navigator.clipboard.writeText(`Ticket: ${ticket} - INEP: ${inep}`);
        tdAcao.appendChild(btn);
        
        tr.appendChild(tdTicket);
        tr.appendChild(tdStatus);
        tr.appendChild(tdEscola);
        tr.appendChild(tdInep);
        tr.appendChild(tdAcao);
        
        els.tableOs.appendChild(tr);
    });
}

// Render Recuperações
function renderRecoveries() {
    if(!els.tableRecoveries) return;
    els.tableRecoveries.innerHTML = '';
    const list = state.lastValidData.fechar || [];
    
    if(list.length === 0) {
        els.tableRecoveries.innerHTML = `<tr><td colspan="5"><div class="empty-state"><h3>Nenhuma Recuperação Pendente</h3></div></td></tr>`;
        return;
    }
    
    list.forEach(item => {
        const inep = item['INEP_Extraido'] || item['INEP'] || '-';
        const name = item['Nome da Escola'] || item['Escola'] || 'Desconhecida';
        const ticket = item['Ticket#'] || 'S/N';
        
        const tr = document.createElement('tr');
        
        const tdTicket = document.createElement('td');
        const badgeTicket = document.createElement('span');
        badgeTicket.className = 'badge badge-warning';
        badgeTicket.textContent = ticket;
        tdTicket.appendChild(badgeTicket);
        
        const tdStatus = document.createElement('td');
        const badgeStatus = document.createElement('span');
        badgeStatus.className = 'badge badge-success';
        badgeStatus.textContent = 'ONLINE';
        tdStatus.appendChild(badgeStatus);
        
        const tdEscola = document.createElement('td');
        tdEscola.textContent = name;
        
        const tdInep = document.createElement('td');
        tdInep.textContent = inep;
        
        const tdAcao = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.textContent = 'Copiar Dados P/ Fechar';
        btn.onclick = () => navigator.clipboard.writeText(`Fechamento INEP: ${inep} - Ticket: ${ticket} - ONLINE`);
        tdAcao.appendChild(btn);
        
        tr.appendChild(tdTicket);
        tr.appendChild(tdStatus);
        tr.appendChild(tdEscola);
        tr.appendChild(tdInep);
        tr.appendChild(tdAcao);
        
        els.tableRecoveries.appendChild(tr);
    });
}

// Drawer Interactions
function openDrawer(item) {
    const inep = item['INEP_Extraido'] || item['INEP'] || '-';
    const name = item['Nome da Escola'] || item['Escola'] || 'Desconhecida';
    const nameField = item['NAME'] || item['Nome'] || '';
    
    let localidade = 'Localização Indisponível';
    if (item['Município'] && item['UF'] && item['Município'] !== '-' && item['UF'] !== '-') {
        localidade = `${item['Município']} / ${item['UF']}`;
    } else if (nameField.includes('-')) {
        localidade = nameField.split('-')[0].trim();
    } else {
        localidade = nameField || 'Localização Indisponível';
    }
    
    const rule = item["Regra de Abertura (4h Offline)"] || "";
    const ip = item['IP Address'] || item['IP'] || 'Não reportado';
    const timeOffline = rule.includes('- Offline há ') ? rule.split('- Offline há ')[1] : '-';

    els.drawerOverlay.classList.add('active');
    els.drawer.classList.add('open');
    
    els.drawerSchool.textContent = name;
    els.drawerLocation.textContent = localidade;
    els.drawerInep.textContent = inep;
    els.drawerIp.textContent = ip;
    
    els.drawerRule.textContent = rule;
    if (els.drawerPartner) {
        els.drawerPartner.textContent = item['Parceiro'] || 'Desconhecido';
    }
    
    if(rule.includes('🚨')) {
        els.drawerBadge.className = 'badge badge-critical';
        els.drawerBadge.textContent = '🚨 CRÍTICO';
    } else {
        els.drawerBadge.className = 'badge badge-warning';
        els.drawerBadge.textContent = '⏳ AGUARDAR SLA';
    }
    
    els.drawerTime.textContent = 'Offline há ' + timeOffline;
    
    if(!item['Nome da Escola'] || item['Nome da Escola'] === 'N/A') {
        els.drawerCad.innerHTML = '<span class="badge badge-warning">Divergência EACE</span>';
    } else {
        els.drawerCad.innerHTML = '<span class="badge badge-success">Sincronizado</span>';
    }
}

function closeDrawer() {
    els.drawerOverlay.classList.remove('active');
    els.drawer.classList.remove('open');
}

// Fallback Mock Data Generator
function generateMockData() {
    return {
        timestamp: new Date().toISOString(),
        falta_abrir: [
            { Escola: "E M E I F  FRANCISCA DE ALMEIDA CLAUDINO", INEP: "23237199", Localidade: "Lavras da Mangabeira - CE", "Offline Since": "há 14h30m", Uptime: "Uptime: 2026-08-24 20:00", "Regra de Abertura (4h Offline)": "🚨 CRÍTICO (>4h) - Offline há 14h30m", IP: "10.0.0.4" },
            { Escola: "EEB JOAO JOSE DE SOUZA CABRAL", INEP: "42032483", Localidade: "Canoinhas - SC", "Offline Since": "há 4h05m", Uptime: "Uptime: 2026-08-25 07:15", "Regra de Abertura (4h Offline)": "🚨 CRÍTICO (>4h) - Offline há 4h05m", IP: "192.168.1.5" },
            { Escola: "COLEGIO ESTADUAL PRESIDENTE COSTA E SILVA", INEP: "41088680", Localidade: "Cascavel - PR", "Offline Since": "há 1h10m", Uptime: "Uptime: 2026-08-25 10:10", "Regra de Abertura (4h Offline)": "⏳ AGUARDAR (<4h) - Offline há 1h10m", IP: "10.50.2.2" },
            { Escola: "N/A", INEP: "N/A", Localidade: "Desconhecido - SP", "Offline Since": "há 20h00m", Uptime: "Uptime: 2026-08-24 15:00", "Regra de Abertura (4h Offline)": "🚨 CRÍTICO (>4h) - Offline há 20h00m", IP: "172.16.0.1" },
            { Escola: "ESCOLA MUNICIPAL ALDA CARVALHO", INEP: "33011122", Localidade: "Rio de Janeiro - RJ", "Offline Since": "há 0h30m", Uptime: "Uptime: 2026-08-25 10:50", "Regra de Abertura (4h Offline)": "⏳ AGUARDAR (<4h) - Offline há 0h30m", IP: "10.10.10.1" }
        ]
    };
}

// Run
document.addEventListener('DOMContentLoaded', init);
