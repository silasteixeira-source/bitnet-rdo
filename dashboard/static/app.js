// Variável global para armazenar os dados carregados e poder usar nos Modais
let dashboardData = null;

// Relógio do cabeçalho
function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('pt-BR');
}
setInterval(updateClock, 1000);
updateClock();

// Função de alternar Abas (BITNET / ST1)
function switchTab(tenant) {
    // Esconde tudo
    document.getElementById('bitnet-view').classList.remove('active-view');
    document.getElementById('st1-view').classList.remove('active-view');
    document.querySelector('.bitnet-tab').classList.remove('active');
    document.querySelector('.st1-tab').classList.remove('active');

    // Mostra o clicado
    document.getElementById(`${tenant}-view`).classList.add('active-view');
    document.querySelector(`.${tenant}-tab`).classList.add('active');
}

// Função para buscar dados da API FastAPI
async function fetchDashboardData() {
    const statusEl = document.getElementById('sync-status');
    try {
        statusEl.innerText = 'Sincronizando...';
        statusEl.className = 'update-status';

        // O ?t= impede cache do JSON
        const response = await fetch(`/api/data?t=${new Date().getTime()}`);
        const data = await response.json();

        if (data.error) {
            console.error(data.error);
            statusEl.innerText = 'Erro de Credenciais';
            statusEl.className = 'update-status pulse-red';
            return;
        }

        // Salva globalmente
        dashboardData = data;

        updateTenantCards('bitnet', data.bitnet);
        updateTenantCards('st1', data.st1);

        statusEl.innerText = 'Sincronizado';
        statusEl.className = 'update-status pulse-green';
    } catch (error) {
        console.error("Erro na API:", error);
        statusEl.innerText = 'Falha de Conexão';
        statusEl.className = 'update-status pulse-red';
    }
}

// Atualiza apenas os NÚMEROS dos Cards
function updateTenantCards(tenantId, records) {
    if (!records) return;

    const faltaAbrir = records.falta_abrir || [];
    const abertos = records.abertos || [];
    const fechar = records.fechar || [];

    document.getElementById(`${tenantId}-falta-abrir`).innerText = faltaAbrir.length;
    document.getElementById(`${tenantId}-abertos`).innerText = abertos.length;
    document.getElementById(`${tenantId}-fechar`).innerText = fechar.length;
}

// Função para ABRIR O MODAL
function openModal(tenantId, tipo) {
    if (!dashboardData || !dashboardData[tenantId]) return;

    const registros = dashboardData[tenantId][tipo] || [];
    const tbody = document.querySelector('#modal-table tbody');
    const modalTitle = document.getElementById('modal-title');
    
    let html = '';

    // Define o título e constrói as linhas dependendo do balão clicado
    if (tipo === 'falta_abrir') {
        modalTitle.innerText = `${tenantId.toUpperCase()} - Falta Abrir OS (${registros.length})`;
        registros.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const regra = row['Regra de Abertura (4h Offline)'] || 'Verificar';
            // Se tiver o ícone ✅ na regra, a gente pinta de vermelho pedindo pra abrir
            const badgeClass = regra.includes('✅') ? 'warn pulse-red' : '';
            html += `<tr><td>${inep}</td><td>${name}</td><td><span class="badge ${badgeClass}">${regra}</span></td></tr>`;
        });
    } 
    else if (tipo === 'abertos') {
        modalTitle.innerText = `${tenantId.toUpperCase()} - OS Em Andamento (${registros.length})`;
        registros.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const ticket = row['Ticket#'] || 'OS';
            const status = row['Status'] || 'Análise';
            html += `<tr><td>${inep}</td><td>${name}</td><td><span class="badge" style="background: rgba(255, 170, 0, 0.2); color: #ffaa00;">${ticket} - ${status}</span></td></tr>`;
        });
    } 
    else if (tipo === 'fechar') {
        modalTitle.innerText = `${tenantId.toUpperCase()} - Falta Fechar OS (${registros.length})`;
        registros.forEach(row => {
            const inep = row['INEP_Extraido'] || row['INEP'] || 'N/A';
            const name = row['Nome da Escola'] || row['Escola'] || 'Desconhecida';
            const ticket = row['Ticket#'] || 'OS';
            html += `<tr><td>${inep}</td><td>${name}</td><td><span class="badge ok pulse-green">FECHAR ${ticket}</span></td></tr>`;
        });
    }

    if (html === '') {
        html = '<tr><td colspan="3" style="text-align: center; padding: 30px; color: var(--success); font-size: 1.5rem;">Nada pendente nesta categoria! 🎉</td></tr>';
    }

    tbody.innerHTML = html;
    
    // Abre a janela
    document.getElementById('details-modal').classList.add('open');
}

// Fechar modal
function closeModal() {
    document.getElementById('details-modal').classList.remove('open');
}

// Fecha o modal ao clicar fora dele
document.getElementById('details-modal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

// Busca inicial e depois a cada 30 segundos
fetchDashboardData();
setInterval(fetchDashboardData, 30000);
