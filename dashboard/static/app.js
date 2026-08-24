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
    
    // Troca a cor tema principal
    if (tenant === 'st1') {
        document.documentElement.style.setProperty('--cyan', '#bc13fe'); // Roxo ST1
    } else {
        document.documentElement.style.setProperty('--cyan', '#00f3ff'); // Ciano Bitnet
    }

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
            throw new Error(data.error);
        }

        // Se veio vazio (Google Rate Limit), aborta sem zerar o cache local
        if (!data.bitnet || Object.keys(data.bitnet).length === 0) {
            throw new Error("Planilha retornou vazia (rate limit)");
        }

        // --- BLINDAGEM CONTRA PLANILHAS ZERADAS ---
        // Se as três abas de um tenant vierem zeradas, assumimos que o robô do cliente
        // está no meio de uma atualização (wiping). Então mantemos os dados antigos!
        if (dashboardData) {
            const isBitnetEmpty = data.bitnet.falta_abrir.length === 0 && data.bitnet.abertos.length === 0 && data.bitnet.fechar.length === 0;
            if (isBitnetEmpty) {
                data.bitnet = dashboardData.bitnet;
            }
            
            const isSt1Empty = data.st1.falta_abrir.length === 0 && data.st1.abertos.length === 0 && data.st1.fechar.length === 0;
            if (isSt1Empty) {
                data.st1 = dashboardData.st1;
            }
        }

        dashboardData = data;
        updateCards();
        loadTable(currentView);

        statusEl.innerText = 'SYNCHRONIZED';
        statusEl.style.color = 'var(--success)';
    } catch (error) {
        console.error("Erro no Sync:", error);
        statusEl.innerText = 'RETRYING...';
        statusEl.style.color = 'var(--warning)';
        // Importante: NÃO zeramos a variável dashboardData.
        // Assim o painel continua mostrando os dados antigos enquanto tenta reconectar!
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

// Função para ser chamada quando digitar no input de busca
function filterTable() {
    loadTable(currentView);
}

// Carregar Tabela Embutida
function loadTable(viewType) {
    currentView = viewType;
    let records = dashboardData[currentTenant][viewType] || [];

    // --- FILTRO DE BUSCA ---
    const searchInput = document.getElementById('search-inep');
    if (searchInput) {
        const searchTerm = searchInput.value.toLowerCase().trim();
        if (searchTerm) {
            records = records.filter(row => {
                const inepStr = (row['INEP_Extraido'] || row['INEP'] || '').toString().toLowerCase();
                const nameStr = (row['Nome da Escola'] || row['Escola'] || '').toLowerCase();
                const cidadeStr = (row['NAME'] || row['Nome'] || '').toLowerCase();
                return inepStr.includes(searchTerm) || nameStr.includes(searchTerm) || cidadeStr.includes(searchTerm);
            });
        }
    }

    const tbody = document.querySelector('#data-table tbody');
    const title = document.getElementById('table-title');
    
    let html = '';

    if (viewType === 'falta_abrir') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - FALTA ABRIR OS (${records.length})`;
        records.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const nameField = row['NAME'] || row['Nome'] || '';
            const cidade = nameField.includes('-') ? nameField.split('-')[0].trim() : nameField;
            const regra = row['Regra de Abertura (4h Offline)'] || 'Verificar';
            
            let badgeClass = 'wait';
            if (regra.includes('✅')) badgeClass = 'danger'; // Pode Abrir (Ação necessária)
            
            html += `<tr><td>${inep}</td><td>${cidade}</td><td>${name}</td><td><span class="badge ${badgeClass}">${regra}</span></td><td><button class="action-btn" style="padding: 4px; font-size: 0.7rem;">ABRIR CHAMADO</button></td></tr>`;
        });
    } 
    else if (viewType === 'abertos') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - OS EM ANDAMENTO (${records.length})`;
        records.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const nameField = row['NAME'] || row['Nome'] || '';
            const cidade = nameField.includes('-') ? nameField.split('-')[0].trim() : nameField;
            const ticket = row['Ticket#'] || 'OS';
            const status = row['Status'] || 'Análise';
            
            html += `<tr><td>${inep}</td><td>${cidade}</td><td>${name}</td><td><span class="badge warning">${ticket} - ${status}</span></td><td><button class="action-btn" style="padding: 4px; font-size: 0.7rem;">VER DETALHES</button></td></tr>`;
        });
    } 
    else if (viewType === 'fechar') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - FALTA FECHAR OS (${records.length})`;
        records.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const nameField = row['NAME'] || row['Nome'] || '';
            const cidade = nameField.includes('-') ? nameField.split('-')[0].trim() : nameField;
            const ticket = row['Ticket#'] || 'OS';
            
            html += `<tr><td>${inep}</td><td>${cidade}</td><td>${name}</td><td><span class="badge success">FECHAR ${ticket}</span></td><td><button class="action-btn" style="padding: 4px; font-size: 0.7rem;">VALIDAR</button></td></tr>`;
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
