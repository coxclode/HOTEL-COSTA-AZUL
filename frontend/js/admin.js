// ── HU15 + HU18: Panel administrador ──

function mostrarAlerta(msg, tipo = "success") {
    const el = document.getElementById("alerta");
    el.textContent = msg;
    el.className   = `alert alert-${tipo}`;
    el.style.display = "block";
    setTimeout(() => { el.style.display = "none"; }, 4000);
}

// ── HU15: Listar habitaciones ──
async function cargarHabitaciones() {
    try {
        const resp = await fetch(`${API_BASE}/api/admin/habitaciones`);
        const data = await resp.json();

        if (!resp.ok) { mostrarAlerta(data.error, "error"); return; }

        const lista = data.habitaciones;
        const total       = lista.length;
        const disponibles = lista.filter(h => h.estado === "Disponible").length;
        const bloqueadas  = lista.filter(h => h.estado === "Bloqueada").length;

        document.getElementById("stat-total").textContent       = total;
        document.getElementById("stat-disponibles").textContent = disponibles;
        document.getElementById("stat-bloqueadas").textContent  = bloqueadas;

        const badgeClass = { Disponible: "disponible", Bloqueada: "bloqueada", Mantenimiento: "mantenimiento" };

        const filas = lista.map(h => `
            <tr>
                <td><strong style="color:#0f4c81;">${h.numero}</strong></td>
                <td>${h.tipo}</td>
                <td>S/ ${parseFloat(h.precio_base).toFixed(2)}</td>
                <td>${h.capacidad} pers.</td>
                <td><span class="badge badge-${badgeClass[h.estado] || "disponible"}">${h.estado}</span></td>
                <td style="max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                    title="${h.descripcion}">${h.descripcion}</td>
                <td>
                    <div style="display:flex;gap:8px;justify-content:flex-end;">
                        <a href="form.html?id=${h.id_habitacion}" class="btn btn-sm btn-secondary">Editar</a>
                        <button class="toggle-btn btn-sm ${h.estado === 'Disponible' ? 'activo' : 'bloqueado'}"
                                onclick="toggleDisponibilidad(${h.id_habitacion})">
                            ${h.estado === 'Disponible' ? 'Bloquear' : 'Habilitar'}
                        </button>
                        <button class="btn btn-sm btn-danger"
                                onclick="eliminarHabitacion(${h.id_habitacion}, '${h.numero}')">
                            Eliminar
                        </button>
                    </div>
                </td>
            </tr>`).join("");

        document.getElementById("tabla-body").innerHTML =
            filas || `<tr><td colspan="7" style="text-align:center;color:#64748b;">No hay habitaciones registradas.</td></tr>`;

    } catch (err) {
        mostrarAlerta("No se pudo conectar con el servidor.", "error");
    }
}

// ── HU15: Guardar (crear o editar) ──
async function guardarHabitacion(e) {
    e.preventDefault();
    const idHab = document.getElementById("id-habitacion").value;
    const btn   = document.getElementById("btn-guardar");

    const payload = {
        numero:      document.getElementById("numero").value.trim(),
        tipo:        document.getElementById("tipo").value,
        precio_base: parseFloat(document.getElementById("precio_base").value),
        capacidad:   parseInt(document.getElementById("capacidad").value),
        estado:      document.getElementById("estado").value,
        descripcion: document.getElementById("descripcion").value.trim(),
    };

    btn.disabled = true;
    btn.textContent = "Guardando…";

    try {
        const url    = idHab
            ? `${API_BASE}/api/admin/habitaciones/${idHab}`
            : `${API_BASE}/api/admin/habitaciones`;
        const method = idHab ? "PUT" : "POST";

        const resp = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(payload),
        });
        const data = await resp.json();

        if (!resp.ok) {
            mostrarAlerta(data.error, "error");
        } else {
            window.location.href = `index.html?ok=1`;
        }
    } catch (err) {
        mostrarAlerta("Error de conexión.", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Guardar";
    }
}

// ── HU15: Cargar datos para editar ──
async function cargarHabitacionParaEditar(id) {
    try {
        const resp = await fetch(`${API_BASE}/api/habitaciones/${id}`);
        const h    = await resp.json();

        if (!resp.ok) { mostrarAlerta(h.error, "error"); return; }

        document.getElementById("numero").value      = h.numero;
        document.getElementById("tipo").value        = h.tipo;
        document.getElementById("precio_base").value = h.precio_base;
        document.getElementById("capacidad").value   = h.capacidad;
        document.getElementById("estado").value      = h.estado;
        document.getElementById("descripcion").value = h.descripcion;
    } catch {
        mostrarAlerta("Error al cargar la habitación.", "error");
    }
}

// ── HU18: Toggle disponibilidad ──
async function toggleDisponibilidad(id) {
    try {
        const resp = await fetch(`${API_BASE}/api/admin/habitaciones/${id}/disponibilidad`, {
            method: "PATCH",
        });
        const data = await resp.json();

        if (resp.ok) {
            mostrarAlerta(`Estado cambiado a ${data.nuevo_estado}`);
            cargarHabitaciones();
        } else {
            mostrarAlerta(data.error, "error");
        }
    } catch {
        mostrarAlerta("Error de conexión.", "error");
    }
}

// ── HU15: Eliminar habitación ──
async function eliminarHabitacion(id, numero) {
    if (!confirm(`¿Eliminar la habitación ${numero}? Esta acción no se puede deshacer.`)) return;

    try {
        const resp = await fetch(`${API_BASE}/api/admin/habitaciones/${id}`, { method: "DELETE" });
        const data = await resp.json();

        if (resp.ok) {
            mostrarAlerta("Habitación eliminada correctamente.");
            cargarHabitaciones();
        } else {
            mostrarAlerta(data.error, "error");
        }
    } catch {
        mostrarAlerta("Error de conexión.", "error");
    }
}

// Mostrar mensaje de éxito si viene de un guardado
window.addEventListener("DOMContentLoaded", function () {
    if (new URLSearchParams(window.location.search).get("ok")) {
        mostrarAlerta("Habitación guardada correctamente.");
        history.replaceState({}, "", "index.html");
    }
});
