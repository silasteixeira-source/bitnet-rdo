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
        updateSheetTime();
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
        let usingStaleData = false;
        if (dashboardData) {
            const isBitnetEmpty = data.bitnet.falta_abrir.length === 0 && data.bitnet.abertos.length === 0 && data.bitnet.fechar.length === 0;
            if (isBitnetEmpty) {
                data.bitnet = dashboardData.bitnet;
                usingStaleData = true;
            }
            
            const isSt1Empty = data.st1.falta_abrir.length === 0 && data.st1.abertos.length === 0 && data.st1.fechar.length === 0;
            if (isSt1Empty) {
                data.st1 = dashboardData.st1;
                usingStaleData = true;
            }
        }

        dashboardData = data;
        updateCards();
        loadTable(currentView);
        updateSheetTime();

        if (usingStaleData) {
            statusEl.innerText = 'STALE DATA (SNAPSHOT)';
            statusEl.style.color = 'var(--warning)';
        } else {
            statusEl.innerText = 'SYNCHRONIZED';
            statusEl.style.color = 'var(--success)';
        }
        
        const lastCheckEl = document.getElementById('last-check');
        if (lastCheckEl) {
            const now = new Date();
            lastCheckEl.innerText = now.toLocaleTimeString();
        }
    } catch (error) {
        console.error("Erro no Sync:", error);
        statusEl.innerText = 'RETRYING...';
        statusEl.style.color = 'var(--warning)';
        // Importante: NÃO zeramos a variável dashboardData.
        // Assim o painel continua mostrando os dados antigos enquanto tenta reconectar!
    }
}

// Atualizar horário da planilha
function updateSheetTime() {
    let sheetTime = '-';
    
    // Procura o campo 'Atualizado Em' na primeira linha que encontrar
    const views = ['falta_abrir', 'abertos', 'fechar'];
    for (let view of views) {
        const records = dashboardData[currentTenant][view];
        if (records && records.length > 0) {
            if (records[0]['Atualizado Em']) {
                sheetTime = records[0]['Atualizado Em'];
                break;
            }
        }
    }
    
    const el = document.getElementById('sheet-updated');
    if (el) el.innerText = sheetTime;
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
    
    // Limpa a tabela de forma segura
    tbody.innerHTML = '';

    if (viewType === 'falta_abrir') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - FALTA ABRIR OS (${records.length})`;
    } else if (viewType === 'abertos') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - OS EM ANDAMENTO (${records.length})`;
    } else if (viewType === 'fechar') {
        title.innerText = `DETALHES DE OCORRÊNCIAS - FALTA FECHAR OS (${records.length})`;
    }

    if (records.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 5;
        td.style.textAlign = 'center';
        td.style.padding = '30px';
        td.style.color = 'var(--success)';
        td.textContent = 'Tudo Operacional! Nenhuma ação pendente.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    records.forEach(row => {
        const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
        const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
        const nameField = row['NAME'] || row['Nome'] || '';
        const cidade = nameField.includes('-') ? nameField.split('-')[0].trim() : nameField;
        const ticket = row['Ticket#'] || 'OS';
        const status = row['Status'] || 'Análise';
        const regra = row['Regra de Abertura (4h Offline)'] || 'Verificar';
        
        const tr = document.createElement('tr');
        
        // INEP
        const tdInep = document.createElement('td');
        tdInep.textContent = inep;
        tr.appendChild(tdInep);
        
        // CIDADE
        const tdCidade = document.createElement('td');
        tdCidade.textContent = cidade;
        tr.appendChild(tdCidade);
        
        // ESCOLA
        const tdNome = document.createElement('td');
        tdNome.textContent = name;
        tr.appendChild(tdNome);

        // STATUS
        const tdStatus = document.createElement('td');
        const spanBadge = document.createElement('span');
        
        // AÇÃO
        const tdAcao = document.createElement('td');
        const btnAcao = document.createElement('button');
        btnAcao.className = 'action-btn';
        btnAcao.style.padding = '4px';
        btnAcao.style.fontSize = '0.7rem';
        
        if (viewType === 'falta_abrir') {
            let badgeClass = 'wait';
            if (regra.includes('✅')) badgeClass = 'danger';
            spanBadge.className = `badge ${badgeClass}`;
            spanBadge.textContent = regra;
            
            btnAcao.textContent = 'COPIAR DADOS';
            btnAcao.setAttribute('aria-label', `Copiar dados da escola ${name}`);
            btnAcao.onclick = () => {
                const textToCopy = `INEP: ${inep}\nEscola: ${name}\nCidade: ${cidade}\nStatus: ${regra}`;
                navigator.clipboard.writeText(textToCopy);
                btnAcao.textContent = 'COPIADO!';
                setTimeout(() => btnAcao.textContent = 'COPIAR DADOS', 2000);
            };
        } else if (viewType === 'abertos') {
            spanBadge.className = `badge warning`;
            spanBadge.textContent = `${ticket} - ${status}`;
            
            btnAcao.textContent = 'VER DETALHES';
            btnAcao.setAttribute('aria-label', `Ver detalhes do ticket ${ticket}`);
            btnAcao.onclick = () => alert(`Detalhes do Ticket: ${ticket}\nEscola: ${name}\nStatus: ${status}`);
        } else if (viewType === 'fechar') {
            spanBadge.className = `badge success`;
            spanBadge.textContent = `FECHAR ${ticket}`;
            
            btnAcao.textContent = 'COPIAR DADOS';
            btnAcao.setAttribute('aria-label', `Copiar dados para fechamento do ticket ${ticket}`);
            btnAcao.onclick = () => {
                const textToCopy = `INEP: ${inep}\nEscola: ${name}\nTicket para fechar: ${ticket}`;
                navigator.clipboard.writeText(textToCopy);
                btnAcao.textContent = 'COPIADO!';
                setTimeout(() => btnAcao.textContent = 'COPIAR DADOS', 2000);
            };
        }

        tdStatus.appendChild(spanBadge);
        tr.appendChild(tdStatus);
        
        tdAcao.appendChild(btnAcao);
        tr.appendChild(tdAcao);

        tbody.appendChild(tr);
    });
}

// Inicia
fetchDashboardData();
setInterval(fetchDashboardData, 30000);
