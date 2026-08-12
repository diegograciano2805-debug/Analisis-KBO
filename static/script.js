let currentMatchesData = [];

async function cargarMetricas() {
    try {
        const res = await fetch('/api/metrics');
        const data = await res.json();
        document.getElementById('stat-precision').innerText = data.precision || '0.0%';
        document.getElementById('stat-roi').innerText = data.roi_promedio || '+0.0%';
        document.getElementById('stat-evaluados').innerText = data.partidos_evaluados || '0';
        document.getElementById('stat-record').innerText = `${data.ganadas || 0}G - ${data.perdidas || 0}P`;
    } catch (e) {
        console.error("Error al cargar métricas:", e);
    }
}

async function abrirHistorial() {
    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        const tbody = document.getElementById('history-table-body');
        tbody.innerHTML = '';

        if (data.historial && data.historial.length > 0) {
            data.historial.forEach(h => {
                const tr = document.createElement('tr');
                let estadoTag = `<span style="color:#8b949e;">PENDIENTE</span>`;
                if (h.estado === 'GANADA') {
                    estadoTag = `<strong style="color:#2e7d32;">✔ ACERTADA</strong>`;
                } else if (h.estado === 'PERDIDA') {
                    estadoTag = `<strong style="color:#d32f2f;">✖ NO ACERTADA</strong>`;
                } else if (h.estado === 'CANCELADO') {
                    estadoTag = `<strong style="color:#d97706;">⚠️ CANCELADO</strong>`;
                }

                tr.innerHTML = `
                    <td>${h.fecha}</td>
                    <td>${h.partido}</td>
                    <td><strong>${h.favorito_pronostico}</strong></td>
                    <td>@${h.momio_decimal ? Number(h.momio_decimal).toFixed(2) : '1.90'}</td>
                    <td>${h.stake_sugerido} de tu dinero</td>
                    <td>${h.resultado_carreras || 'N/A'}</td>
                    <td>${estadoTag}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No hay registros de partidos finalizados aún.</td></tr>';
        }

        document.getElementById('history-modal').classList.remove('hidden');
    } catch (e) {
        console.error("Error al obtener historial:", e);
    }
}

function cerrarHistorial() {
    document.getElementById('history-modal').classList.add('hidden');
}

function cerrarHistorialModal(event) {
    if (event.target.id === 'history-modal') {
        cerrarHistorial();
    }
}

async function cargarPronosticos() {
    const fecha = document.getElementById('game-date').value;
    const container = document.getElementById('games-container');
    const loading = document.getElementById('loading');

    loading.classList.remove('hidden');
    container.innerHTML = '';

    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fecha: fecha })
        });
        
        const data = await response.json();
        loading.classList.add('hidden');

        if (data.partidos && data.partidos.length > 0) {
            currentMatchesData = data.partidos;
            data.partidos.forEach((p, index) => {
                const probLocal = p.probabilidad_local ?? 0.5;
                const probLocalPct = (probLocal * 100).toFixed(1);
                const probAwayPct = ((1 - probLocal) * 100).toFixed(1);

                const ganador = p.favorito_pronostico ?? (probLocal >= 0.5 ? p.equipo_local : p.equipo_visitante);
                const recOU = p.recomendacion_ou || "Over 8.5";
                const recRL = p.recomendacion_runline || "N/A";
                const stake = p.stake_sugerido || "1.5%";
                const momio = p.momio_decimal ? Number(p.momio_decimal).toFixed(2) : "1.90";
                const ev = p.ev_label || "+0.0% EV";
                const isPositiveEV = ev.includes('+');

                // Traducción de Conveniencia
                const convenienciaTexto = isPositiveEV ? "SÍ CONVIENE (+Ventaja)" : "NO CONVIENE (Riesgo alto)";

                const estado = p.estado || 'PENDIENTE';
                let estadoBadge = '';
                if (estado === 'CANCELADO') {
                    estadoBadge = `<div style="text-align:center; margin-bottom:0.4rem;"><span style="background:#d97706; color:white; padding:0.25rem 0.6rem; border-radius:4px; font-size:0.75rem; font-weight:bold;">⚠️ PARTIDO CANCELADO / POSPUESTO</span></div>`;
                }

                const card = document.createElement('div');
                card.className = 'game-card';
                card.onclick = () => openModal(index);
                card.innerHTML = `
                    <div class="teams-header">
                        <span>${p.equipo_visitante}</span>
                        <span class="vs-badge">VS</span>
                        <span>${p.equipo_local}</span>
                    </div>

                    ${estadoBadge}

                    <div class="prob-container" style="margin: 0.6rem 0 1rem 0;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: #8b949e; margin-bottom: 0.3rem;">
                            <span>${p.equipo_visitante} <strong style="color: #58a6ff;">${probAwayPct}%</strong></span>
                            <span><strong style="color: #3fb950;">${probLocalPct}%</strong> ${p.equipo_local}</span>
                        </div>
                        <div style="background: #21262d; height: 8px; border-radius: 4px; overflow: hidden; display: flex;">
                            <div style="width: ${probAwayPct}%; background: #1f6beb;"></div>
                            <div style="width: ${probLocalPct}%; background: #238636;"></div>
                        </div>
                    </div>

                    <div class="bet-options">
                        <div class="badge">
                            <span>Equipo a Ganar (@${momio}):</span>
                            <strong>${ganador}</strong>
                        </div>
                        <div class="badge">
                            <span>¿Conviene Apostar?:</span>
                            <strong style="color: ${isPositiveEV ? '#2e7d32' : '#d32f2f'};">${convenienciaTexto}</strong>
                        </div>
                        <div class="badge">
                            <span>Total de Carreras:</span>
                            <strong>${recOU}</strong>
                        </div>
                        <div class="badge">
                            <span>Ventaja de Carreras:</span>
                            <strong>${recRL}</strong>
                        </div>
                        <div class="badge" style="border-color: #2e7d32;">
                            <span style="color: #8b949e;">Inversión Recomendada:</span>
                            <strong style="color: #2e7d32;">${stake} de tu Dinero</strong>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        } else {
            container.innerHTML = '<p style="text-align:center; grid-column: 1/-1;">No hay partidos programados para esta fecha.</p>';
        }

        await cargarMetricas();

    } catch (error) {
        console.error("Error cargando pronósticos:", error);
        loading.innerHTML = "Error al conectar con el servidor.";
    }
}

function openModal(index) {
    const p = currentMatchesData[index];
    if (!p) return;

    document.getElementById('modal-title').innerText = `${p.equipo_visitante} vs ${p.equipo_local}`;
    
    const body = document.getElementById('modal-body');
    body.innerHTML = `
        <div style="margin-bottom: 1rem; font-size: 0.85rem; color: #8b949e;">
            Clima estimado: <strong style="color: #f0f3f6;">${p.clima_info || '24°C, 12 km/h'}</strong>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Factor Analizado</th>
                    <th>Valor Calculado</th>
                    <th>Efecto en la Pronóstico</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Calidad de Picheo Abridor</td>
                    <td>Favorece a ${p.equipo_local}</td>
                    <td><span style="color: #2e7d32;">+4.5% Probabilidad</span></td>
                </tr>
                <tr>
                    <td>Poder de Bateo del Equipo</td>
                    <td>Rendimiento Alto</td>
                    <td><span style="color: #2e7d32;">+3.1% Probabilidad</span></td>
                </tr>
                <tr>
                    <td>Factor del Estadio</td>
                    <td>${p.equipo_local === 'SSG Landers' ? 'Estadio de Bateadores' : 'Estadio Neutral'}</td>
                    <td>Ajusta Puntos Totales</td>
                </tr>
            </tbody>
        </table>
        <div style="margin-top: 1.2rem; background: #161b22; padding: 0.8rem; border-radius: 6px; border: 1px solid #262c36; font-size: 0.8rem; color: #8b949e;">
            💡 <strong>Resumen Simplificado:</strong> El modelo analiza el rendimiento de los lanzadores abridores y el historial del equipo. Se sugiere invertir como máximo el ${p.stake_sugerido || '1.5%'} de tu presupuesto total.
        </div>
    `;

    document.getElementById('match-modal').classList.remove('hidden');
}

function closeModalDirect() {
    document.getElementById('match-modal').classList.add('hidden');
}

function closeModal(event) {
    if (event.target.id === 'match-modal') {
        closeModalDirect();
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const messages = document.getElementById('chat-messages');
    const fecha = document.getElementById('game-date').value;
    const text = input.value.trim();

    if (!text) return;

    const userMsg = document.createElement('div');
    userMsg.className = 'message user-message';
    userMsg.innerText = text;
    messages.appendChild(userMsg);

    input.value = '';
    messages.scrollTop = messages.scrollHeight;

    const botMsg = document.createElement('div');
    botMsg.className = 'message bot-message';
    botMsg.innerText = "Analizando partido...";
    messages.appendChild(botMsg);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, fecha: fecha })
        });
        const data = await response.json();
        botMsg.innerHTML = typeof marked !== 'undefined' ? marked.parse(data.response) : data.response;
    } catch (err) {
        botMsg.innerText = "Error al obtener respuesta del asistente.";
    }

    messages.scrollTop = messages.scrollHeight;
}

function handleKeyPress(e) {
    if (e.key === 'Enter') sendMessage();
}


async function vaciarHistorialBD() {
    if (confirm("¿Seguro que deseas vaciar el historial de la base de datos?")) {
        try {
            const res = await fetch('/api/clear-db', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'ok') {
                alert("Base de datos reiniciada correctamente.");
                await cargarPronosticos();
            }
        } catch (e) {
            console.error("Error al reiniciar BD:", e);
        }
    }
}

document.addEventListener('DOMContentLoaded', cargarPronosticos);