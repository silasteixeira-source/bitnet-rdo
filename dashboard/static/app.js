let dashboardData = null;
let currentTenant = 'bitnet';
let currentView = 'falta_abrir';

// Relógio
function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('pt-BR');
    document.getElementById('last-check').innerText = now.toLocaleTimeString('pt-BR');
}
setInterval(updateClock, 1000);
updateClock();

// Alternar entre Bitnet e ST1
function switchTenant(tenant) {
    currentTenant = tenant;
    
    // Atualiza menu
    document.getElementById('btn-bitnet').classList.remove('active');
    document.getElementById('btn-st1').classList.remove('active');
    document.getElementById(`btn-${tenant}`).classList.add('active');

    // Atualiza Label
    document.getElementById('current-tenant-label').innerText = tenant.toUpperCase();

    // Atualiza a tela se os dados já chegaram
    if (dashboardData) {
        updateCards();
        loadTable(currentView);
    }
}

// Buscar API
async function fetchDashboardData() {
    const statusEl = document.getElementById('sync-status');
    try {
        statusEl.innerText = 'SYNCING...';
        statusEl.style.color = 'var(--warning)';

        const response = await fetch(`/api/data?t=${new Date().getTime()}`);
        const data = await response.json();

        if (data.error) {
            statusEl.innerText = 'ERROR';
            statusEl.style.color = 'var(--danger)';
            return;
        }

        dashboardData = data;
        updateCards();
        loadTable(currentView);

        statusEl.innerText = 'SYNCHRONIZED';
        statusEl.style.color = 'var(--success)';
    } catch (error) {
        statusEl.innerText = 'OFFLINE';
        statusEl.style.color = 'var(--danger)';
    }
}

// Atualizar Números nos Cards
function updateCards() {
    const records = dashboardData[currentTenant];
    if (!records) return;

    document.getElementById('val-falta-abrir').innerText = (records.falta_abrir || []).length;
    document.getElementById('val-abertos').innerText = (records.abertos || []).length;
    document.getElementById('val-fechar').innerText = (records.fechar || []).length;
}

// Carregar Tabela Embutida
function loadTable(viewType) {
    currentView = viewType;
    const records = dashboardData[currentTenant][viewType] || [];
    const tbody = document.querySelector('#data-table tbody');
    const title = document.getElementById('table-title');
    
    let html = '';

    if (viewType === 'falta_abrir') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - FALTA ABRIR OS (${records.length})`;
        records.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const regra = row['Regra de Abertura (4h Offline)'] || 'Verificar';
            
            let badgeClass = 'wait';
            if (regra.includes('✅')) badgeClass = 'danger'; // Pode Abrir (Ação necessária)
            
            html += `<tr><td>${inep}</td><td>${name}</td><td><span class="badge ${badgeClass}">${regra}</span></td><td><button class="action-btn" style="padding: 4px; font-size: 0.7rem;">ABRIR CHAMADO</button></td></tr>`;
        });
    } 
    else if (viewType === 'abertos') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - OS EM ANDAMENTO (${records.length})`;
        records.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const ticket = row['Ticket#'] || 'OS';
            const status = row['Status'] || 'Análise';
            
            html += `<tr><td>${inep}</td><td>${name}</td><td><span class="badge warning">${ticket} - ${status}</span></td><td><button class="action-btn" style="padding: 4px; font-size: 0.7rem;">VER DETALHES</button></td></tr>`;
        });
    } 
    else if (viewType === 'fechar') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - FALTA FECHAR OS (${records.length})`;
        records.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const ticket = row['Ticket#'] || 'OS';
            
            html += `<tr><td>${inep}</td><td>${name}</td><td><span class="badge success">FECHAR ${ticket}</span></td><td><button class="action-btn" style="padding: 4px; font-size: 0.7rem;">VALIDAR</button></td></tr>`;
        });
    }

    if (html === '') {
        html = '<tr><td colspan="4" style="text-align: center; padding: 30px; color: var(--success);">Tudo Operacional! Nenhuma ação pendente.</td></tr>';
    }

    tbody.innerHTML = html;
}

// Inicia
fetchDashboardData();
setInterval(fetchDashboardData, 30000);
