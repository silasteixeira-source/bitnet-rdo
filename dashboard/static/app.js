// State Management
const state = {
    tenant: 'bitnet',
    data: null,
    lastValidData: null,
    isError: false,
    filterUf: '',
    filterStatus: '',
    searchQuery: '',
    filterUfOs: '',
    filterStatusOs: '',
    searchQueryOs: '',
    currentFilteredList: [],
    currentFilteredOsList: [],
    previousRecoveredIneps: new Set(),
    alertsEnabled: localStorage.getItem('nocAlertsEnabled') === 'true',
    hasAlertedStaleData: false,
    activeTab: 'todos', // 'todos', 'critico', 'aguardar'
    currentView: 'view-overview',
    agents: [],
    assignments: {},
    hiddenTickets: {},
    history: []
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
    
    // Novas métricas (Panorama Global)
    kpiTotal: document.getElementById('kpi-total'),
    kpiOffline: document.getElementById('kpi-offline'),
    kpiOnline: document.getElementById('kpi-online'),
    kpiIgnorados: document.getElementById('kpi-ignorados'),
    
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
    btnExportExcel: document.getElementById('btn-export-excel'),
    btnEnableAlerts: document.getElementById('btn-enable-alerts'),
    searchInput: document.querySelector('.search-input'),
    tabs: document.querySelectorAll('.tab'),
    countTodos: document.getElementById('count-todos'),
    countCritico: document.getElementById('count-critico'),
    countAguardar: document.getElementById('count-aguardar'),
    
    // Novas Views
    tableOs: document.querySelector('#table-os tbody'),
    searchOs: document.getElementById('search-os'),
    filterUfOs: document.getElementById('filter-uf-os'),
    filterStatusOs: document.getElementById('filter-status-os'),
    btnExportExcelOs: document.getElementById('btn-export-excel-os'),
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
    drawerTimeline: document.getElementById('drawer-timeline'),
    
    // Agentes
    btnManageAgents: document.getElementById('btn-manage-agents'),
    modalAgents: document.getElementById('modal-agents'),
    btnCloseAgents: document.getElementById('btn-close-agents'),
    inputNewAgent: document.getElementById('input-new-agent'),
    btnAddAgent: document.getElementById('btn-add-agent'),
    listAgents: document.getElementById('list-agents')
};

// Initialization
async function init() {
    if (state.alertsEnabled) {
        if ("Notification" in window && Notification.permission === "granted") {
            if (els.btnEnableAlerts) els.btnEnableAlerts.style.display = 'none';
        } else {
            state.alertsEnabled = false;
            localStorage.setItem('nocAlertsEnabled', 'false');
        }
    }
    await fetchAgents();
    await fetchAssignments();
    fetchHiddenTickets();
    fetchHistory();
    setupEventListeners();
    setupAgentsListeners();
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
    
    // Search
    els.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim().toLowerCase();
        renderOverview();
        renderIncidents();
    });

    // Export Excel
    if (els.btnExportExcel) {
        els.btnExportExcel.addEventListener('click', () => {
            if(!state.currentFilteredList || state.currentFilteredList.length === 0) {
                alert("Não há dados para exportar com os filtros atuais.");
                return;
            }
            
            // Transform data for excel
            const dataToExport = state.currentFilteredList.map(item => {
                const nameField = item['NAME'] || item['Nome'] || '';
                let localidade = '-';
                if (item['Municipio'] && item['UF'] && item['Municipio'] !== '-' && item['UF'] !== '-') {
                    localidade = `${item['Municipio']} / ${item['UF']}`;
                } else if (nameField.includes('-')) {
                    localidade = nameField.split('-')[0].trim();
                } else {
                    localidade = nameField || '-';
                }

                return {
                    "INEP": item['INEP_Extraido'] || item['INEP'] || '',
                    "Escola": item['Nome da Escola'] || item['Escola'] || '',
                    "Localidade": localidade,
                    "Parceiro (Provedor)": item['Parceiro'] || '',
                    "Status / Regra": item["Regra de Abertura (4h Offline)"] || '',
                    "IP Address": item['IP Address'] || '',
                    "MAC Address": item['MAC Address'] || '',
                    "Uptime": item['Uptime'] || '',
                    "Última Vez Visto": item['Last Seen'] || ''
                };
            });
            
            try {
                const ws = XLSX.utils.json_to_sheet(dataToExport);
                const wb = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(wb, ws, "Fila de Incidentes");
                
                const ufStr = state.filterUf ? state.filterUf : "Todas";
                XLSX.writeFile(wb, `Fila_Incidentes_NOC_${ufStr}_${new Date().getTime()}.xlsx`);
            } catch (err) {
                console.error("Erro ao gerar Excel:", err);
                alert("Falha ao gerar o arquivo Excel. Verifique o console.");
            }
        });
    }

    // Enable Alerts
    if (els.btnEnableAlerts) {
        els.btnEnableAlerts.addEventListener('click', () => {
            if ("Notification" in window) {
                Notification.requestPermission().then(permission => {
                    if (permission === "granted") {
                        state.alertsEnabled = true;
                        localStorage.setItem('nocAlertsEnabled', 'true');
                        els.btnEnableAlerts.style.display = 'none';
                        // Play silent sound to unlock AudioContext on browsers
                        try {
                            const silentAudio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA');
                            silentAudio.play().catch(()=>{});
                        } catch(e) {}
                        new Notification("Alertas NOC Ativados ✅", { body: "As notificações ficarão ativas permanentemente neste navegador." });
                    } else {
                        alert("Você precisa permitir notificações no navegador para receber alertas.");
                    }
                });
            } else {
                alert("Este navegador não suporta notificações de sistema.");
            }
        });
    }

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
    
    // Eventos da aba OS em Andamento
    if (els.searchOs) {
        els.searchOs.addEventListener('input', (e) => {
            state.searchQueryOs = e.target.value.trim();
            renderOs();
        });
    }
    
    if (els.filterUfOs) {
        els.filterUfOs.addEventListener('change', (e) => {
            state.filterUfOs = e.target.value;
            renderOs();
        });
    }
    
    if (els.filterStatusOs) {
        els.filterStatusOs.addEventListener('change', (e) => {
            state.filterStatusOs = e.target.value;
            renderOs();
        });
    }
    
    if (els.btnExportExcelOs) {
        els.btnExportExcelOs.addEventListener('click', () => {
            if(!state.currentFilteredOsList || state.currentFilteredOsList.length === 0) {
                alert("Não há dados para exportar com os filtros atuais.");
                return;
            }
            
            const dataToExport = state.currentFilteredOsList.map(item => {
                const nameField = item['NAME'] || item['Nome'] || '';
                let localidade = '-';
                if (item['Municipio'] && item['UF'] && item['Municipio'] !== '-' && item['UF'] !== '-') {
                    localidade = `${item['Municipio']} / ${item['UF']}`;
                } else if (nameField.includes('-')) {
                    localidade = nameField.split('-')[0].trim();
                } else {
                    localidade = nameField || '-';
                }

                const inep = item['INEP_Extraido'] || item['INEP'] || '';
                const agentId = state.assignments[inep];
                const agentName = agentId ? (state.agents.find(a => a.id === agentId)?.name || 'Sem Agente') : 'Sem Agente';

                return {
                    "Agente": agentName,
                    "Status": getStatusFromOsItem(item),
                    "Escola": item['Nome da Escola'] || item['Escola'] || '',
                    "Localidade": localidade,
                    "INEP": item['INEP_Extraido'] || item['INEP'] || '',
                    "Causa": item['Causa'] || ''
                };
            });
            
            try {
                const ws = XLSX.utils.json_to_sheet(dataToExport);
                const wb = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(wb, ws, "OS em Andamento");
                XLSX.writeFile(wb, `OS_em_Andamento_NOC_${new Date().getTime()}.xlsx`);
            } catch (err) {
                console.error("Erro ao gerar Excel:", err);
                alert("Falha ao gerar o arquivo Excel. Verifique o console.");
            }
        });
    }
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
    if(els.tableOs) els.tableOs.innerHTML = '<tr><td colspan="6"><div class="skeleton sk-text"></div></td></tr>';
    if(els.tableRecoveries) els.tableRecoveries.innerHTML = '<tr><td colspan="6"><div class="skeleton sk-text"></div></td></tr>';

    // Sempre busca os dados novos ao trocar
    fetchData();
};

// API Fetch
async function fetchData() {
    setSyncState('syncing', 'Atualizando...');
    const API_KEY = window.NOC_API_KEY || 'noc-key-secret';
    
    try {
        const [resCurrent, resOther] = await Promise.all([
            fetch(`/api/v1/dashboard?tenant=${state.tenant}&t=${Date.now()}`, { headers: { 'X-API-KEY': API_KEY } }),
            fetch(`/api/v1/dashboard?tenant=${state.tenant === 'bitnet' ? 'st1' : 'bitnet'}&t=${Date.now()}`, { headers: { 'X-API-KEY': API_KEY } })
        ]);
        
        if (!resCurrent.ok) throw new Error('API Error (Current Tenant)');
        
        let data = await resCurrent.json();
        let otherData = {};
        if (resOther.ok) {
            try { otherData = await resOther.json(); } catch(e) {}
        }
        
        // Se a API retornar vazio, usar mock para validação visual
        if(!data || !data.falta_abrir) {
            console.warn("API retornou sem dados principais. Usando Mock local para testes visuais.");
            data = generateMockData();
        }
        
        const currentOnline = data.stats ? (data.stats.online || 0) : 0;
        const otherOnline = otherData.stats ? (otherData.stats.online || 0) : 0;
        data.globalOnline = currentOnline + otherOnline;
        
        state.data = data;
        state.lastValidData = state.data;
        state.isError = false;
        
        // --- Lógica de Alertas de Recuperação ---
        const currentRecoveredIneps = new Set((state.data.fechar || []).map(i => i.INEP_Extraido || i.INEP));
        
        // Se já tínhamos dados anteriores e a notificação está ligada
        if (state.previousRecoveredIneps.size > 0 && state.alertsEnabled) {
            const newRecoveries = (state.data.fechar || []).filter(item => {
                const inep = item.INEP_Extraido || item.INEP;
                return !state.previousRecoveredIneps.has(inep);
            });
            
            if (newRecoveries.length > 0) {
                // Tocar Som de Notificação
                try {
                    const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
                    audio.volume = 0.5;
                    audio.play().catch(e => console.warn("Audio autoplay blocked", e));
                } catch(e) {}
                
                // Enviar push system notification
                if ("Notification" in window && Notification.permission === "granted") {
                    newRecoveries.forEach(item => {
                        const name = item['Nome da Escola'] || item['NAME'] || item['Escola'] || 'Desconhecida';
                        new Notification("Escola Recuperada! ✅", {
                            body: `A escola ${name} está online novamente.`,
                            icon: "https://cdn-icons-png.flaticon.com/512/190/190411.png"
                        });
                    });
                }
            }
        }
        state.previousRecoveredIneps = currentRecoveredIneps;
        
        // Verifica staleness (Ex: timestamp mais antigo que 10 min)
        const ts = state.data.timestamp ? new Date(state.data.timestamp).getTime() : Date.now();
        const diffMin = (Date.now() - ts) / 60000;
        
        if (diffMin > 15) {
            setSyncState('warning', `Dados Atrasados (${Math.floor(diffMin)}m)`);
            
            // Lógica de alerta para automação parada
            if (state.alertsEnabled && !state.hasAlertedStaleData) {
                state.hasAlertedStaleData = true;
                
                try {
                    // Som de aviso/alerta
                    const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2866/2866-preview.mp3');
                    audio.volume = 0.6;
                    audio.play().catch(e => console.warn("Audio blocked", e));
                } catch(e) {}
                
                if ("Notification" in window && Notification.permission === "granted") {
                    new Notification("⚠️ Alerta NOC", {
                        body: `A automação parou! Dados atrasados há ${Math.floor(diffMin)} minutos. Verifique o servidor.`,
                        icon: "https://cdn-icons-png.flaticon.com/512/564/564619.png"
                    });
                }
            }
        } else {
            setSyncState('success', 'Atualizado agora');
            state.hasAlertedStaleData = false;
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
    
    if (typeof updateDetailedListsData === 'function') {
        updateDetailedListsData(state.lastValidData);
    }
    
    populateUfFilter();
    populateFiltersOs();
    updateKPIs();
    
    if(state.currentView === 'view-overview') {
        renderOverview();
    } else if(state.currentView === 'view-incidents') {
        renderIncidents();
    } else if(state.currentView === 'view-os') {
        renderOs();
    } else if(state.currentView === 'view-recoveries') {
        renderRecoveries();
    } else if(state.currentView === 'view-detailed-lists') {
        renderDetailedList(currentDetailedListType || 'online');
    } else if(state.currentView === 'view-history') {
        window.renderHistory();
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

function getUfFromOsItem(item) {
    if (item['UF'] && item['UF'] !== "-") return String(item['UF']).trim();
    const nameField = String(item['NAME'] || item['Nome'] || '');
    if (nameField.includes('/')) {
        const parts = nameField.split('/');
        return parts[parts.length - 1].split('-')[0].trim();
    }
    return '';
}

function getStatusFromOsItem(item) {
    const s = item['Status'] || item['Status_y'] || item['Status_x'] || 'Em Análise';
    return String(s).trim();
}

function populateFiltersOs() {
    if (!els.filterUfOs || !els.filterStatusOs) return;
    
    const list = state.lastValidData.abertos || [];
    const ufs = new Set();
    const statuses = new Set();
    
    list.forEach(item => {
        const uf = getUfFromOsItem(item);
        if (uf) ufs.add(uf);
        
        const s = getStatusFromOsItem(item);
        if (s) statuses.add(s);
    });
    
    const currUf = els.filterUfOs.value;
    els.filterUfOs.innerHTML = '<option value="">UF: Todas</option>';
    Array.from(ufs).sort().forEach(uf => {
        const opt = document.createElement('option');
        opt.value = uf;
        opt.textContent = uf;
        els.filterUfOs.appendChild(opt);
    });
    els.filterUfOs.value = currUf;
    
    const currStatus = els.filterStatusOs.value;
    els.filterStatusOs.innerHTML = '<option value="">Status: Todos</option>';
    Array.from(statuses).sort().forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        els.filterStatusOs.appendChild(opt);
    });
    els.filterStatusOs.value = currStatus;
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
    
    // Estatísticas Globais do Omada (Total, Offline, Online, Ignorados)
    const stats = state.lastValidData.stats || { total: '-', offline: '-', online: '-', ignorados: '-' };
    if (els.kpiTotal) els.kpiTotal.textContent = stats.total;
    if (els.kpiOffline) els.kpiOffline.textContent = stats.offline;
    if (els.kpiOnline) {
        els.kpiOnline.innerHTML = `${stats.online} <span style="font-size:12px; font-weight:normal; color:var(--text-sec); display:block; margin-top:2px;">Global: ${state.lastValidData.globalOnline || 0}</span>`;
    }
    if (els.kpiIgnorados) els.kpiIgnorados.textContent = stats.ignorados;
    
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
            const inepStr = String(item['INEP_Extraido'] || item['INEP'] || '');
            const nameStr = String(item['Nome da Escola'] || item['Escola'] || '');
            const omadaStr = String(item['NAME'] || item['Nome'] || '');
            const ufStr = String(item['UF'] || '');
            const munStr = String(item['Municipio'] || '');
            
            const str = `${nameStr} ${inepStr} ${omadaStr} ${ufStr} ${munStr}`.toLowerCase();
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
        if (item['Municipio'] && item['UF'] && item['Municipio'] !== '-' && item['UF'] !== '-') {
            localidade = `${item['Municipio']} / ${item['UF']}`;
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

    renderRecentActivity();
}

function renderRecentActivity() {
    if(!els.recentActivityList) return;
    els.recentActivityList.innerHTML = '';
    
    const acts = [];
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    acts.push({ time: timeStr, text: `Sincronização de dados concluída.`, crit: false });
    
    if (state.lastValidData) {
        const recup = state.lastValidData.fechar || [];
        if (recup.length > 0) {
            acts.push({ time: timeStr, text: `${recup.length} escolas reportadas ONLINE no Omada (Aguardando fechamento EACE).`, crit: false });
        }
        
        const falta = state.lastValidData.falta_abrir || [];
        const criticos = falta.filter(i => (i["Regra de Abertura (4h Offline)"] || "").includes('🚨'));
        if (criticos.length > 0) {
            acts.push({ time: timeStr, text: `${criticos.length} escolas atingiram o SLA de 4h (Fila Crítica).`, crit: true });
            criticos.slice(0, 2).forEach(c => {
                const inep = c['INEP_Extraido'] || c['INEP'] || '-';
                acts.push({ time: timeStr, text: `INEP ${inep} extrapolou tempo limite (4h).`, crit: true });
            });
        }
    }
    
    acts.forEach(m => {
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
    
    // First, filter by dropdowns and search (ignoring Tab selection)
    let baseFiltered = list.filter(item => {
        const rule = item["Regra de Abertura (4h Offline)"] || "";
        const inep = item['INEP_Extraido'] || item['INEP'] || '';
        const name = item['Nome da Escola'] || item['Escola'] || '';
        const nameField = item['NAME'] || item['Nome'] || '';
        
        // Dropdown UF
        if(state.filterUf && item['UF'] !== state.filterUf) return false;
        
        // Dropdown Status
        if(state.filterStatus === 'CRÍTICO' && !rule.includes('🚨')) return false;
        if(state.filterStatus === 'AGUARDAR' && !rule.includes('⏳')) return false;
        
        // Search
        if(state.searchQuery) {
            const inepStr = String(item['INEP_Extraido'] || item['INEP'] || '');
            const nameStr = String(item['Nome da Escola'] || item['Escola'] || '');
            const omadaStr = String(item['NAME'] || item['Nome'] || '');
            const ufStr = String(item['UF'] || '');
            const munStr = String(item['Municipio'] || '');
            
            const str = `${nameStr} ${inepStr} ${omadaStr} ${ufStr} ${munStr}`.toLowerCase();
            if(!str.includes(state.searchQuery)) return false;
        }
        
        return true;
    });

    // Update Tab Counts based on baseFiltered
    let cTotal = baseFiltered.length;
    let cCrit = 0;
    let cAgua = 0;
    baseFiltered.forEach(item => {
        const r = item["Regra de Abertura (4h Offline)"] || "";
        if (r.includes('🚨')) cCrit++;
        else if (r.includes('⏳')) cAgua++;
    });

    if(els.countTodos) els.countTodos.textContent = cTotal;
    if(els.countCritico) els.countCritico.textContent = cCrit;
    if(els.countAguardar) els.countAguardar.textContent = cAgua;

    // Now apply active Tab filter
    let filtered = baseFiltered.filter(item => {
        const rule = item["Regra de Abertura (4h Offline)"] || "";
        if(state.activeTab === 'critico' && !rule.includes('🚨')) return false;
        if(state.activeTab === 'aguardar' && !rule.includes('⏳')) return false;
        return true;
    });
    
    // Save to state for Export Excel
    state.currentFilteredList = filtered;
    
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
        if (item['Municipio'] && item['UF'] && item['Municipio'] !== '-' && item['UF'] !== '-') {
            localidade = `${item['Municipio']} / ${item['UF']}`;
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
    let list = state.lastValidData.abertos || [];
    
    // Filtro UF OS
    if (state.filterUfOs) {
        list = list.filter(item => getUfFromOsItem(item) === state.filterUfOs);
    }
    
    // Filtro Status OS
    if (state.filterStatusOs) {
        list = list.filter(item => getStatusFromOsItem(item) === state.filterStatusOs);
    }
    
    // Filtro de Busca OS
    if (state.searchQueryOs) {
        const q = state.searchQueryOs.toLowerCase();
        list = list.filter(item => {
            const inep = (item['INEP_Extraido'] || item['INEP'] || '').toString().toLowerCase();
            const esc = (item['Nome da Escola'] || item['Escola'] || item['NAME'] || item['Nome'] || '').toLowerCase();
            const ticket = (item['Ticket#'] || '').toString().toLowerCase();
            const status = (item['Status'] || '').toLowerCase();
            return inep.includes(q) || esc.includes(q) || ticket.includes(q) || status.includes(q);
        });
    }
    
    state.currentFilteredOsList = list;
    
    if(list.length === 0) {
        els.tableOs.innerHTML = `<tr><td colspan="6"><div class="empty-state"><h3>Nenhuma OS em Andamento</h3></div></td></tr>`;
        return;
    }
    
    list.forEach(item => {
        const inep = item['INEP_Extraido'] || item['INEP'] || '-';
        const name = item['Nome da Escola'] || item['Escola'] || 'Desconhecida';
        const status = getStatusFromOsItem(item);
        
        const nameField = item['NAME'] || item['Nome'] || '';
        let localidade = '-';
        if (item['Municipio'] && item['UF'] && item['Municipio'] !== '-' && item['UF'] !== '-') {
            localidade = `${item['Municipio']} / ${item['UF']}`;
        } else if (nameField.includes('-')) {
            localidade = nameField.split('-')[0].trim();
        } else {
            localidade = nameField || '-';
        }
        
        const tr = document.createElement('tr');
        
        const tdAgente = document.createElement('td');
        const selAgente = document.createElement('select');
        selAgente.className = 'agent-select';
        
        const optDefault = document.createElement('option');
        optDefault.value = '';
        optDefault.textContent = 'Sem Agente';
        selAgente.appendChild(optDefault);
        
        state.agents.forEach(a => {
            const opt = document.createElement('option');
            opt.value = a.id;
            opt.textContent = a.name;
            selAgente.appendChild(opt);
        });
        
        selAgente.value = state.assignments[inep] || '';
        
        selAgente.addEventListener('change', (e) => {
            saveAssignment(inep, e.target.value);
        });
        
        tdAgente.appendChild(selAgente);
        
        const tdStatus = document.createElement('td');
        tdStatus.textContent = status;
        
        const tdEscola = document.createElement('td');
        tdEscola.textContent = name;
        
        const tdLoc = document.createElement('td');
        tdLoc.textContent = localidade;
        
        const tdInep = document.createElement('td');
        tdInep.textContent = inep;
        
        const tdCausa = document.createElement('td');
        tdCausa.textContent = item['Causa'] || '-';
        
        const tdAcao = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.textContent = 'Copiar Resumo';
        btn.onclick = () => navigator.clipboard.writeText(`OS INEP: ${inep} - ${name} - ${status}`);
        tdAcao.appendChild(btn);
        
        tr.appendChild(tdAgente);
        tr.appendChild(tdStatus);
        tr.appendChild(tdEscola);
        tr.appendChild(tdLoc);
        tr.appendChild(tdInep);
        tr.appendChild(tdCausa);
        tr.appendChild(tdAcao);
        
        els.tableOs.appendChild(tr);
    });
}

// Render Recuperações
function renderRecoveries() {
    if(!els.tableRecoveries) return;
    els.tableRecoveries.innerHTML = '';
    let list = state.lastValidData.fechar || [];
    
    if (state.hiddenTickets) {
        list = list.filter(item => {
            const inep = item['INEP_Extraido'] || item['INEP'] || '-';
            return !state.hiddenTickets[inep];
        });
    }
    
    if(list.length === 0) {
        els.tableRecoveries.innerHTML = `<tr><td colspan="6"><div class="empty-state"><h3>Nenhuma Recuperação Pendente</h3></div></td></tr>`;
        return;
    }
    
    list.forEach(item => {
        const inep = item['INEP_Extraido'] || item['INEP'] || '-';
        const name = item['Nome da Escola'] || item['Escola'] || 'Desconhecida';
        const ticket = item['Ticket#'] || 'S/N';
        
        const nameField = item['NAME'] || item['Nome'] || '';
        let localidade = '-';
        if (item['Municipio'] && item['UF'] && item['Municipio'] !== '-' && item['UF'] !== '-') {
            localidade = `${item['Municipio']} / ${item['UF']}`;
        } else if (nameField.includes('-')) {
            localidade = nameField.split('-')[0].trim();
        } else {
            localidade = nameField || '-';
        }
        
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
        
        const tdLoc = document.createElement('td');
        tdLoc.textContent = localidade;
        
        const tdInep = document.createElement('td');
        tdInep.textContent = inep;
        
        const tdCausa = document.createElement('td');
        tdCausa.textContent = item['Causa'] || '-';
        
        const tdAcao = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.textContent = 'Copiar Dados P/ Fechar';
        btn.onclick = () => navigator.clipboard.writeText(`Fechamento INEP: ${inep} - Ticket: ${ticket} - ONLINE`);
        tdAcao.appendChild(btn);

        const btnConcluir = document.createElement('button');
        btnConcluir.className = 'btn';
        btnConcluir.style.marginLeft = '4px';
        btnConcluir.style.backgroundColor = 'var(--status-success)';
        btnConcluir.style.color = '#fff';
        btnConcluir.style.borderColor = 'var(--status-success)';
        btnConcluir.textContent = 'Concluir';
        btnConcluir.disabled = true;
        btnConcluir.style.opacity = '0.5';
        btnConcluir.style.cursor = 'not-allowed';
        btnConcluir.onclick = () => hideTicket(inep, name, 'concluir_recuperacao');

        const btnLock = document.createElement('button');
        btnLock.className = 'btn btn-icon';
        btnLock.style.marginLeft = '8px';
        btnLock.title = 'Destravar botão de concluir';
        btnLock.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>';
        btnLock.onclick = () => {
            if (btnConcluir.disabled) {
                btnConcluir.disabled = false;
                btnConcluir.style.opacity = '1';
                btnConcluir.style.cursor = 'pointer';
                btnLock.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-ok)" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>';
                btnLock.title = 'Travar botão';
            } else {
                btnConcluir.disabled = true;
                btnConcluir.style.opacity = '0.5';
                btnConcluir.style.cursor = 'not-allowed';
                btnLock.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>';
                btnLock.title = 'Destravar botão de concluir';
            }
        };

        tdAcao.appendChild(btnLock);
        tdAcao.appendChild(btnConcluir);
        
        tr.appendChild(tdTicket);
        tr.appendChild(tdStatus);
        tr.appendChild(tdEscola);
        tr.appendChild(tdLoc);
        tr.appendChild(tdInep);
        tr.appendChild(tdCausa);
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
    if (item['Municipio'] && item['UF'] && item['Municipio'] !== '-' && item['UF'] !== '-') {
        localidade = `${item['Municipio']} / ${item['UF']}`;
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

// API Agentes
async function fetchAgents() {
    try {
        const res = await fetch('/api/v1/agents', { headers: { 'x-api-key': window.NOC_API_KEY } });
        if (res.ok) {
            state.agents = await res.json();
            renderAgentsList();
        }
    } catch(e) { console.error("Erro ao carregar agentes", e); }
}

async function fetchAssignments() {
    try {
        const res = await fetch('/api/v1/assignments', { headers: { 'x-api-key': window.NOC_API_KEY } });
        if (res.ok) state.assignments = await res.json();
    } catch(e) { console.error("Erro ao carregar atribuições", e); }
}

async function saveAssignment(inep, agentId) {
    try {
        await fetch('/api/v1/assignments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-api-key': window.NOC_API_KEY },
            body: JSON.stringify({ inep: inep, agent_id: agentId })
        });
        state.assignments[inep] = agentId;
    } catch(e) { console.error("Erro ao salvar atribuição", e); }
}

async function fetchHiddenTickets() {
    try {
        const res = await fetch('/api/v1/hidden_tickets', { headers: { 'x-api-key': window.NOC_API_KEY } });
        if (res.ok) state.hiddenTickets = await res.json();
    } catch(e) { console.error("Erro ao carregar tickets ocultos", e); }
}

async function hideTicket(inep, escola = 'N/A', action = 'ocultar_ticket') {
    try {
        await fetch('/api/v1/hidden_tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-api-key': window.NOC_API_KEY },
            body: JSON.stringify({ inep: inep })
        });
        
        // Log history
        let detailsText = action === 'concluir_recuperacao' ? 'Recuperação concluída' : 'Ticket ocultado';
        await fetch('/api/v1/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-api-key': window.NOC_API_KEY },
            body: JSON.stringify({
                action: action,
                inep: inep,
                escola: escola,
                details: detailsText
            })
        });
        
        state.hiddenTickets[inep] = new Date().toISOString();
        if(els.tableRecoveries) renderRecoveries();
        if(els.tableIncidents) renderIncidents();
        
        // Refresh history if already loaded
        if (state.history) {
            fetchHistory();
        }
    } catch(e) { console.error("Erro ao ocultar ticket", e); }
}

async function undoAction(inep) {
    try {
        await fetch(`/api/v1/hidden_tickets/${inep}`, {
            method: 'DELETE',
            headers: { 'x-api-key': window.NOC_API_KEY }
        });
        
        await fetch('/api/v1/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-api-key': window.NOC_API_KEY },
            body: JSON.stringify({
                action: 'desfazer',
                inep: inep,
                escola: 'Ação Desfeita',
                details: `Ticket ${inep} restaurado`
            })
        });
        
        delete state.hiddenTickets[inep];
        
        if(els.tableRecoveries) renderRecoveries();
        if(els.tableIncidents) renderIncidents();
        fetchHistory();
    } catch(e) { console.error("Erro ao desfazer ação", e); }
}

async function fetchHistory() {
    try {
        const tbody = document.getElementById('table-history-body');
        if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:24px;">Atualizando histórico...</td></tr>`;
        
        const res = await fetch('/api/v1/history', { headers: { 'x-api-key': window.NOC_API_KEY } });
        if (res.ok) {
            state.history = await res.json();
            if (state.currentView === 'view-history') renderHistory();
        }
    } catch(e) { console.error("Erro ao buscar histórico", e); }
}

function renderHistory() {
    const tbody = document.getElementById('table-history-body');
    if(!tbody) return;
    
    tbody.innerHTML = '';
    
    if(!state.history || state.history.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:24px;">O histórico está vazio.</td></tr>`;
        return;
    }
    
    state.history.forEach(log => {
        const tr = document.createElement('tr');
        
        const dateObj = new Date(log.timestamp);
        const dataStr = dateObj.toLocaleDateString('pt-BR') + ' ' + dateObj.toLocaleTimeString('pt-BR');
        
        const tdData = document.createElement('td');
        tdData.style.fontSize = '12px';
        tdData.style.color = 'var(--text-ter)';
        tdData.textContent = dataStr;
        
        const tdEscola = document.createElement('td');
        tdEscola.innerHTML = `<span style="font-weight:500;">${log.escola}</span><br><span style="font-size:12px; font-family:monospace; color:var(--text-ter)">${log.inep}</span>`;
        
        const tdAcao = document.createElement('td');
        const badge = document.createElement('span');
        
        if (log.action === 'concluir_recuperacao') {
            badge.className = 'badge badge-success';
            badge.textContent = 'CONCLUÍDO';
        } else if (log.action === 'desfazer') {
            badge.className = 'badge badge-warning';
            badge.textContent = 'DESFEITO';
        } else {
            badge.className = 'badge badge-neutral';
            badge.textContent = log.action.toUpperCase();
        }
        tdAcao.appendChild(badge);
        
        const tdDetalhes = document.createElement('td');
        tdDetalhes.textContent = log.details;
        
        const tdDesfazer = document.createElement('td');
        tdDesfazer.style.textAlign = 'center';
        
        if (log.action !== 'desfazer') {
            const btnUndo = document.createElement('button');
            btnUndo.className = 'btn btn-icon';
            btnUndo.title = 'Desfazer ação e restaurar ticket';
            btnUndo.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7v6h6"></path><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path></svg>';
            btnUndo.onclick = () => undoAction(log.inep);
            tdDesfazer.appendChild(btnUndo);
        }
        
        tr.appendChild(tdData);
        tr.appendChild(tdEscola);
        tr.appendChild(tdAcao);
        tr.appendChild(tdDetalhes);
        tr.appendChild(tdDesfazer);
        
        tbody.appendChild(tr);
    });
}

function setupAgentsListeners() {
    if(!els.btnManageAgents) return;
    
    els.btnManageAgents.addEventListener('click', () => {
        els.modalAgents.style.display = 'flex';
        renderAgentsList();
    });
    
    els.btnCloseAgents.addEventListener('click', () => {
        els.modalAgents.style.display = 'none';
        renderOs(); // re-render table to reflect agents
    });
    
    els.btnAddAgent.addEventListener('click', async () => {
        const name = els.inputNewAgent.value.trim();
        if(!name) return;
        try {
            const res = await fetch('/api/v1/agents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': window.NOC_API_KEY },
                body: JSON.stringify({ name })
            });
            if(res.ok) {
                els.inputNewAgent.value = '';
                await fetchAgents();
            }
        } catch(e) { console.error("Erro ao adicionar agente", e); }
    });
}

function renderAgentsList() {
    if(!els.listAgents) return;
    els.listAgents.innerHTML = '';
    if(state.agents.length === 0) {
        els.listAgents.innerHTML = '<div style="padding:8px; color:var(--text-sec); text-align:center;">Nenhum agente cadastrado.</div>';
        return;
    }
    
    state.agents.forEach(agent => {
        const div = document.createElement('div');
        div.className = 'agent-item';
        div.innerHTML = `
            <span>${agent.name}</span>
            <button class="agent-delete-btn" data-id="${agent.id}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
        `;
        const btnDelete = div.querySelector('.agent-delete-btn');
        btnDelete.addEventListener('click', async () => {
            try {
                const res = await fetch(`/api/v1/agents/${agent.id}`, {
                    method: 'DELETE',
                    headers: { 'x-api-key': window.NOC_API_KEY }
                });
                if(res.ok) await fetchAgents();
            } catch(e) { console.error("Erro ao deletar agente", e); }
        });
        els.listAgents.appendChild(div);
    });
}

// Run
document.addEventListener('DOMContentLoaded', init);

// --- Detalhamento de Registros ---
let detailedListData = { online: [], offline: [], ignorados: [] };
window.currentDetailedListType = 'online';

function updateDetailedListsData(data) {
    detailedListData.online = data.list_online || [];
    detailedListData.offline = data.list_offline || [];
    detailedListData.ignorados = data.list_ignorados || [];
    
    const co = document.getElementById('count-list-online');
    if(co) co.textContent = detailedListData.online.length;
    const cf = document.getElementById('count-list-offline');
    if(cf) cf.textContent = detailedListData.offline.length;
    const ci = document.getElementById('count-list-ignorados');
    if(ci) ci.textContent = detailedListData.ignorados.length;
    
    if (state.currentView === 'view-detailed-lists') {
        renderDetailedList(currentDetailedListType);
    }
}

window.renderDetailedList = function(type) {
    currentDetailedListType = type;
    
    // Update button styles
    const btns = ['online', 'offline', 'ignorados'];
    btns.forEach(b => {
        const btn = document.getElementById('btn-list-' + b);
        if(btn) {
            if(b === type) {
                btn.style.opacity = '1';
                btn.style.boxShadow = '0 0 10px rgba(255,255,255,0.2)';
            } else {
                btn.style.opacity = '0.5';
                btn.style.boxShadow = 'none';
            }
        }
    });
    
    filterDetailedList();
};

window.filterDetailedList = function() {
    const list = detailedListData[currentDetailedListType] || [];
    const searchInput = document.getElementById('detailed-search-input');
    const search = searchInput ? searchInput.value.toLowerCase() : '';
    
    const filtered = list.filter(item => {
        const inep = String(item.INEP_Extraido || '').toLowerCase();
        const nome = String(item.NAME || item.Escola || '').toLowerCase();
        return inep.includes(search) || nome.includes(search);
    });
    
    const tbody = document.getElementById('detailed-list-body');
    if (!tbody) return;
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:24px;">Nenhum registro encontrado.</td></tr>`;
        return;
    }
    
    tbody.innerHTML = filtered.map(item => {
        const inep = item.INEP_Extraido || '-';
        const nome = item.NAME || item.Escola || 'Sem nome';
        const status = item.STATUS || (currentDetailedListType === 'offline' ? 'OFFLINE' : (currentDetailedListType === 'online' ? 'ONLINE' : '-'));
        const statusColor = status.toUpperCase().includes('OFFLINE') ? 'var(--status-critical)' : (status.toUpperCase().includes('ONLINE') ? 'var(--status-ok)' : 'var(--text-sec)');
        
        return `
            <tr class="table-row">
                <td style="font-family: monospace; color: var(--text-sec);">${inep}</td>
                <td style="font-weight: 500;">${nome}</td>
                <td><span class="badge" style="background:${statusColor}20; color:${statusColor}">${status}</span></td>
            </tr>
        `;
    }).join('');
};
