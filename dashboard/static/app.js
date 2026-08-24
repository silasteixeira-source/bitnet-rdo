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
    if (!records) return;

    const faltaAbrir = records.falta_abrir || [];
    const abertos = records.abertos || [];
    const fechar = records.fechar || [];

    // Atualiza contadores
    document.getElementById(`${tenantId}-falta-abrir`).innerText = faltaAbrir.length;
    document.getElementById(`${tenantId}-abertos`).innerText = abertos.length;
    document.getElementById(`${tenantId}-fechar`).innerText = fechar.length;
    
    let tableHtml = '';

    // Adiciona linhas: Falta Abrir
    faltaAbrir.forEach(row => {
        const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
        const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
        tableHtml += `
            <tr>
                <td>${inep}</td>
                <td>${name}</td>
                <td><span class="badge warn pulse-red">ABRIR CHAMADO</span></td>
            </tr>
        `;
    });

    // Adiciona linhas: Fechar OS
    fechar.forEach(row => {
        const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
        const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
        const ticket = row['Ticket#'] || 'OS';
        tableHtml += `
            <tr>
                <td>${inep}</td>
                <td>${name}</td>
                <td><span class="badge ok pulse-green">FECHAR ${ticket}</span></td>
            </tr>
        `;
    });

    // Adiciona linhas: Abertos
    abertos.forEach(row => {
        const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
        const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
        const ticket = row['Ticket#'] || 'OS';
        tableHtml += `
            <tr>
                <td>${inep}</td>
                <td>${name}</td>
                <td><span class="badge" style="background: rgba(255, 170, 0, 0.2); color: #ffaa00;">${ticket} ANDAMENTO</span></td>
            </tr>
        `;
    });

    // Atualiza Tabela
    const tbody = document.querySelector(`#${tenantId}-table tbody`);
    if (tableHtml === '') {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--success);">Tudo Operacional! Nenhuma ação pendente.</td></tr>';
    } else {
        tbody.innerHTML = tableHtml;
    }
}

// Busca inicial e depois a cada 30 segundos
fetchDashboardData();
setInterval(fetchDashboardData, 30000);
