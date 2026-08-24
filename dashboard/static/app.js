// Relógio do cabeçalho
function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('pt-BR');
}
setInterval(updateClock, 1000);
updateClock();

// Função para buscar dados da API FastAPI
async function fetchDashboardData() {
    const statusEl = document.getElementById('sync-status');
    try {
        statusEl.innerText = 'Sincronizando...';
        statusEl.className = 'update-status';

        const response = await fetch('/api/data');
        const data = await response.json();

        if (data.error) {
            console.error(data.error);
            statusEl.innerText = 'Erro de Credenciais';
            statusEl.className = 'update-status pulse-red';
            return;
        }

        updateTenantUI('bitnet', data.bitnet);
        updateTenantUI('st1', data.st1);

        statusEl.innerText = 'Sincronizado';
        statusEl.className = 'update-status pulse-green';
    } catch (error) {
        console.error("Erro na API:", error);
        statusEl.innerText = 'Falha de Conexão';
        statusEl.className = 'update-status pulse-red';
    }
}

// Atualiza o HTML das colunas
function updateTenantUI(tenantId, records) {
    if (!records || records.length === 0) return;

    // Filtra apenas as escolas Offline no Omada
    const offlineSchools = records.filter(row => row['Status Omada'] === 'Offline');
    
    let totalOffline = offlineSchools.length;
    let noTicketCount = 0;
    let tableHtml = '';

    offlineSchools.forEach(row => {
        const inep = row['INEP'] || 'N/A';
        const name = row['Escola'] || 'Desconhecida';
        const rdoStatus = row['Status RDO'] || 'Sem Registro';
        const hasTicket = row['Nº OS Bubble'] || row['Data/Hora RDO'];
        
        let badgeClass = 'warn';
        let badgeText = rdoStatus;

        if (hasTicket && rdoStatus !== 'Sem Registro') {
            badgeClass = 'ok';
        } else {
            noTicketCount++;
            badgeText = 'FALTA ABRIR OS';
        }

        tableHtml += `
            <tr>
                <td>${inep}</td>
                <td>${name}</td>
                <td><span class="badge ${badgeClass}">${badgeText}</span></td>
            </tr>
        `;
    });

    // Atualiza contadores
    document.getElementById(`${tenantId}-offline`).innerText = totalOffline;
    
    const noTicketEl = document.getElementById(`${tenantId}-no-ticket`);
    noTicketEl.innerText = noTicketCount;
    if (noTicketCount > 0) {
        noTicketEl.className = 'value danger pulse-red';
    } else {
        noTicketEl.className = 'value';
        noTicketEl.style.color = 'var(--success)';
        noTicketEl.innerText = '0';
    }

    // Atualiza tendências visuais
    document.getElementById(`${tenantId}-trend`).innerText = `Em ${records.length} escolas conectadas`;

    // Atualiza Tabela
    const tbody = document.querySelector(`#${tenantId}-table tbody`);
    if (tableHtml === '') {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--success);">Tudo Operacional! Nenhuma escola offline.</td></tr>';
    } else {
        tbody.innerHTML = tableHtml;
    }
}

// Busca inicial e depois a cada 30 segundos
fetchDashboardData();
setInterval(fetchDashboardData, 30000);
