function mostrarAlerta(msg, tipo = 'success') {
    const el = document.getElementById('alerta');
    if (!el) return;
    el.textContent = msg;
    el.className   = `palert palert-${tipo === 'error' ? 'error' : 'success'}`;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
}

const TIPO_GRADIENT = {
    Simple: 'linear-gradient(145deg,#1a4a7a,#0d3560)',
    Doble:  'linear-gradient(145deg,#2c1810,#5c3420)',
    Suite:  'linear-gradient(145deg,#1a3a1a,#2a5a30)',
};
const TIPO_ICON = { Simple: '🛏', Doble: '🛏', Suite: '🌟' };

function renderFilas(lista) {
    const tbody = document.getElementById('tabla-body');
    if (!lista.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:40px;">No hay habitaciones que coincidan.</td></tr>`;
        return;
    }
    tbody.innerHTML = lista.map(h => {
        const grad  = TIPO_GRADIENT[h.tipo] || TIPO_GRADIENT.Simple;
        const icon  = TIPO_ICON[h.tipo] || '🛏';
        const badge = h.estado === 'Disponible'
            ? `<span class="pbadge pbadge-disponible">Disponible</span>`
            : h.estado === 'Bloqueada'
                ? `<span class="pbadge pbadge-bloqueada">Bloqueada</span>`
                : `<span class="pbadge pbadge-mantenimiento">Mantenimiento</span>`;

        const toggleLabel = h.estado === 'Disponible' ? 'Bloquear' : 'Habilitar';
        const toggleClass = h.estado === 'Disponible' ? 'tbtn-off' : 'tbtn-on';

        return `
        <tr>
            <td><span class="ptable-num">${h.numero}</span></td>
            <td>
                <div class="ptable-room">
                    <div class="ptable-thumb" style="background:${grad}">
                        <span style="font-size:20px;">${icon}</span>
                    </div>
                    <div>
                        <div class="ptable-room-name">${h.tipo}</div>
                        <div class="ptable-room-sub">S/ ${parseFloat(h.precio_base).toFixed(2)} / noche · ${h.capacidad} pers.</div>
                    </div>
                </div>
            </td>
            <td style="font-weight:700;color:var(--navy);">S/ ${parseFloat(h.precio_base).toFixed(2)}</td>
            <td>${h.capacidad} pers.</td>
            <td>${badge}</td>
            <td>
                <div class="ptable-actions">
                    <a href="form.html?id=${h.id_habitacion}" class="tbtn tbtn-edit">✏ Editar</a>
                    <button class="tbtn ${toggleClass}" onclick="toggleDisponibilidad(${h.id_habitacion})">${toggleLabel}</button>
                    <button class="tbtn tbtn-del" onclick="eliminarHabitacion(${h.id_habitacion}, '${h.numero}')">🗑 Eliminar</button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

async function cargarHabitaciones() {
    try {
        const resp = await fetch(`${API_BASE}/api/admin/habitaciones`);
        const data = await resp.json();
        if (!resp.ok) { mostrarAlerta(data.error, 'error'); return; }

        const lista = data.habitaciones;
        document.getElementById('stat-total').textContent       = lista.length;
        document.getElementById('stat-disponibles').textContent = lista.filter(h => h.estado === 'Disponible').length;
        document.getElementById('stat-bloqueadas').textContent  = lista.filter(h => h.estado === 'Bloqueada').length;

        if (typeof window._setFilas === 'function') window._setFilas(lista);
        renderFilas(lista);
    } catch {
        mostrarAlerta('No se pudo conectar con el servidor.', 'error');
    }
}

async function guardarHabitacion(e) {
    e.preventDefault();
    const idHab = document.getElementById('id-habitacion').value;
    const btn   = document.getElementById('btn-guardar');

    const payload = {
        numero:      document.getElementById('numero').value.trim(),
        tipo:        document.getElementById('tipo').value,
        precio_base: parseFloat(document.getElementById('precio_base').value),
        capacidad:   parseInt(document.getElementById('capacidad').value),
        estado:      document.getElementById('estado').value,
        descripcion: document.getElementById('descripcion').value.trim(),
    };

    btn.disabled = true; btn.textContent = 'Guardando…';
    try {
        const url    = idHab ? `${API_BASE}/api/admin/habitaciones/${idHab}` : `${API_BASE}/api/admin/habitaciones`;
        const method = idHab ? 'PUT' : 'POST';
        const resp   = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data   = await resp.json();
        if (!resp.ok) { mostrarAlerta(data.error, 'error'); }
        else { window.location.href = 'index.html?ok=1'; }
    } catch { mostrarAlerta('Error de conexión.', 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Guardar'; }
}

async function cargarHabitacionParaEditar(id) {
    try {
        const resp = await fetch(`${API_BASE}/api/habitaciones/${id}`);
        const h    = await resp.json();
        if (!resp.ok) { mostrarAlerta(h.error, 'error'); return; }
        document.getElementById('numero').value      = h.numero;
        document.getElementById('tipo').value        = h.tipo;
        document.getElementById('precio_base').value = h.precio_base;
        document.getElementById('capacidad').value   = h.capacidad;
        document.getElementById('estado').value      = h.estado;
        document.getElementById('descripcion').value = h.descripcion;
    } catch { mostrarAlerta('Error al cargar la habitación.', 'error'); }
}

async function toggleDisponibilidad(id) {
    try {
        const resp = await fetch(`${API_BASE}/api/admin/habitaciones/${id}/disponibilidad`, { method: 'PATCH' });
        const data = await resp.json();
        if (resp.ok) { mostrarAlerta(`Estado cambiado a ${data.nuevo_estado}`); cargarHabitaciones(); }
        else { mostrarAlerta(data.error, 'error'); }
    } catch { mostrarAlerta('Error de conexión.', 'error'); }
}

async function eliminarHabitacion(id, numero) {
    if (!confirm(`¿Eliminar la habitación ${numero}? Esta acción no se puede deshacer.`)) return;
    try {
        const resp = await fetch(`${API_BASE}/api/admin/habitaciones/${id}`, { method: 'DELETE' });
        const data = await resp.json();
        if (resp.ok) { mostrarAlerta('Habitación eliminada correctamente.'); cargarHabitaciones(); }
        else { mostrarAlerta(data.error, 'error'); }
    } catch { mostrarAlerta('Error de conexión.', 'error'); }
}

window.addEventListener('DOMContentLoaded', function() {
    if (new URLSearchParams(window.location.search).get('ok')) {
        mostrarAlerta('Habitación guardada correctamente.');
        history.replaceState({}, '', 'index.html');
    }
});
