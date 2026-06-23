// ── HU2: Buscar y mostrar habitaciones disponibles ──

async function buscarHabitaciones(checkin, checkout, tipo, precioMin, precioMax) {
    const contenedor = document.getElementById("contenedor-resultado");
    const infoEl     = document.getElementById("info-busqueda");

    if (!checkin || !checkout) {
        contenedor.innerHTML = `
            <div class="alert alert-info">
                Ingresa las fechas de check-in y check-out para buscar habitaciones.
            </div>`;
        return;
    }

    contenedor.innerHTML = `<p style="color:#64748b;text-align:center;padding:32px;">Buscando habitaciones disponibles…</p>`;

    const params = new URLSearchParams({ checkin, checkout });
    if (tipo)      params.append("tipo", tipo);
    if (precioMin) params.append("precio_min", precioMin);
    if (precioMax) params.append("precio_max", precioMax);

    try {
        const resp = await fetch(`${API_BASE}/api/habitaciones/disponibles?${params.toString()}`);
        const data = await resp.json();

        if (!resp.ok) {
            contenedor.innerHTML = `<div class="alert alert-error">${data.error}</div>`;
            return;
        }

        infoEl.textContent =
            `${data.total} habitación(es) disponible(s) para ${checkin} → ${checkout}`;

        if (data.total === 0) {
            contenedor.innerHTML = `
                <div class="alert alert-info" style="text-align:center;padding:32px;">
                    No hay habitaciones disponibles para las fechas y filtros seleccionados.
                    <br><a href="index.html" style="color:#0f4c81;font-weight:700;">Modificar búsqueda</a>
                </div>`;
            return;
        }

        const cards = data.habitaciones.map(h => {
            const iconos  = { Simple: "🛏️", Doble: "🛏️🛏️", Suite: "🌟" };
            const urlDetalle = `detalle.html?id=${h.id_habitacion}&checkin=${checkin}&checkout=${checkout}`;

            const imgHtml = h.imagen
                ? `<img src="${h.imagen}" alt="Habitación ${h.tipo}"
                        style="width:100%;height:100%;object-fit:cover;"
                        onerror="this.parentElement.innerHTML='<span style=font-size:54px>${iconos[h.tipo] || "🛏️"}</span>'">`
                : `<span style="font-size:54px;">${iconos[h.tipo] || "🛏️"}</span>`;

            return `
                <div class="habitacion-card">
                    <div class="habitacion-card-img">${imgHtml}</div>
                    <div class="habitacion-card-body">
                        <h3>Habitación ${h.numero} · ${h.tipo}</h3>
                        <p>${h.descripcion}</p>
                        <p style="margin-top:8px;font-size:12px;color:#64748b;">
                            👥 Hasta ${h.capacidad} persona(s)
                        </p>
                    </div>
                    <div class="habitacion-card-footer">
                        <div class="precio">S/ ${parseFloat(h.precio_base).toFixed(2)} <span>/ noche</span></div>
                        <a href="${urlDetalle}" class="btn btn-primary btn-sm">Ver detalle</a>
                    </div>
                </div>`;
        }).join("");

        contenedor.innerHTML = `<div class="habitaciones-grid">${cards}</div>`;

    } catch (err) {
        contenedor.innerHTML = `
            <div class="alert alert-error">
                No se pudo conectar con el servidor. Verifica que el backend esté activo.
            </div>`;
    }
}
