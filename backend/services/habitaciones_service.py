ESTADO_BLOQUEADA = "Bloqueada"


def habitacion_disponible_para_reserva(habitacion):
    return habitacion.get("estado") != ESTADO_BLOQUEADA


def filtrar_disponibles(habitaciones):
    return [h for h in habitaciones if habitacion_disponible_para_reserva(h)]
