// ── HU6 / HU7: Enviar reserva al backend ──

async function generarReserva() {
    const hab     = JSON.parse(localStorage.getItem("reserva_hab")     || "null");
    const cliente = JSON.parse(localStorage.getItem("reserva_cliente") || "null");
    const btn     = document.getElementById("btn-confirmar");
    const errEl   = document.getElementById("error-confirmar");

    if (!hab || !cliente) {
        window.location.href = "index.html";
        return;
    }

    // Evitar doble ejecución simultánea
    if (localStorage.getItem("_reserva_procesando") === "true") return;
    if (localStorage.getItem("reserva_resultado")) {
        window.location.href = "pago.html";
        return;
    }

    localStorage.setItem("_reserva_procesando", "true");
    btn.disabled   = true;
    btn.textContent = "Procesando…";
    errEl.style.display = "none";

    const payload = {
        id_habitacion: hab.id_habitacion,
        nombre:    cliente.nombre,
        apellido:  cliente.apellido,
        dni:       cliente.dni,
        correo:    cliente.correo,
        telefono:  cliente.telefono,
        checkin:   hab.checkin,
        checkout:  hab.checkout,
        personas:  hab.personas || 1,
    };

    try {
        const resp = await fetch(`${API_BASE}/api/reservas`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(payload),
        });
        const data = await resp.json();

        if (!resp.ok) {
            errEl.textContent = data.error || "Error al procesar la reserva.";
            errEl.style.display = "block";
            btn.disabled   = false;
            btn.textContent = "Generar reserva y pagar";
            localStorage.removeItem("_reserva_procesando");
            return;
        }

        localStorage.setItem("reserva_resultado", JSON.stringify(data));
        localStorage.removeItem("_reserva_procesando");
        window.location.href = "pago.html";

    } catch (err) {
        errEl.textContent = "No se pudo conectar con el servidor.";
        errEl.style.display = "block";
        btn.disabled   = false;
        btn.textContent = "Generar reserva y pagar";
        localStorage.removeItem("_reserva_procesando");
    }
}
