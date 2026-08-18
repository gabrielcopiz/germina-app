import sqlite3, secrets
from datetime import datetime, date, timedelta

DB = 'cannawaka.db'
db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row

hoy = date.today()

# Obtener IDs de socios activos/aprobados
socios = db.execute("SELECT id FROM socios WHERE etapa IN ('activo','aprobado')").fetchall()
sid1 = socios[0]['id'] if len(socios) > 0 else 1
sid2 = socios[1]['id'] if len(socios) > 1 else 1
sid3 = socios[2]['id'] if len(socios) > 2 else 1

# Limpiar datos anteriores
db.execute("DELETE FROM cultivos")
db.execute("DELETE FROM etapas_cultivo")
db.execute("DELETE FROM cosechas")
db.execute("DELETE FROM pedidos")
db.commit()

# ── CULTIVOS ──
cultivos = [
    ('CW-0001', sid1, 'OG Kush', 'indica', 4, 'interior',
     str(hoy - timedelta(days=120)), 'curado',
     str(hoy - timedelta(days=10)), str(hoy + timedelta(days=5)),
     'Grow tent 1.2x1.2 — Tent A', 'Coco + perlita', 'Excelente desarrollo vegetativo', 'activo'),
    ('CW-0002', sid1, 'White Widow', 'hibrido', 2, 'interior',
     str(hoy - timedelta(days=90)), 'floracion',
     str(hoy - timedelta(days=20)), str(hoy + timedelta(days=35)),
     'Grow tent 0.8x0.8 — Tent B', 'Tierra + lombricompuesto', 'Pistillos mostrando bien', 'activo'),
    ('CW-0003', sid2, 'CBD Therapy', 'cbd_dominante', 3, 'exterior',
     str(hoy - timedelta(days=60)), 'floracion',
     str(hoy - timedelta(days=5)), str(hoy + timedelta(days=45)),
     'Terraza norte', 'Tierra de jardín', 'Planta vigorosa, sin plagas', 'activo'),
    ('CW-0004', sid2, 'Northern Lights', 'indica', 6, 'interior',
     str(hoy - timedelta(days=30)), 'vegetativo',
     str(hoy - timedelta(days=10)), str(hoy + timedelta(days=90)),
     'Grow room principal', 'Hidropónico DWC', 'Raíces abundantes', 'activo'),
    ('CW-0005', sid3, 'Amnesia Haze', 'sativa', 2, 'invernadero',
     str(hoy - timedelta(days=150)), 'finalizado',
     str(hoy - timedelta(days=30)), None,
     'Invernadero sur', 'Coco', 'Cultivo finalizado correctamente', 'finalizado'),
    ('CW-0006', sid3, 'Gorilla Glue', 'hibrido', 3, 'interior',
     str(hoy - timedelta(days=15)), 'plantula',
     str(hoy - timedelta(days=5)), str(hoy + timedelta(days=140)),
     'Grow tent nueva', 'Tierra universal', 'Germinadas 3 de 3', 'activo'),
]

for c in cultivos:
    db.execute('''
        INSERT INTO cultivos (codigo, socio_id, variedad, genetica, num_plantas,
        tipo_cultivo, fecha_inicio, etapa_actual, fecha_etapa, cosecha_estimada,
        ubicacion_detalle, sustrato, notas, estado)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', c)

db.commit()

# ── HISTORIAL DE ETAPAS ──
logs = [
    (1, None, 'germinacion', str(hoy - timedelta(days=120)), 'Cultivo iniciado', 'Admin'),
    (1, 'germinacion', 'plantula', str(hoy - timedelta(days=113)), 'Germinacion exitosa 4/4', 'Admin'),
    (1, 'plantula', 'vegetativo', str(hoy - timedelta(days=92)), 'Trasplante a maceta definitiva', 'Admin'),
    (1, 'vegetativo', 'prefloracion', str(hoy - timedelta(days=55)), 'Cambio a 12/12', 'Admin'),
    (1, 'prefloracion', 'floracion', str(hoy - timedelta(days=40)), 'Pistillos visibles', 'Admin'),
    (1, 'floracion', 'cosecha', str(hoy - timedelta(days=18)), 'Tricomas ámbar 70%', 'Admin'),
    (1, 'cosecha', 'curado', str(hoy - timedelta(days=10)), 'Colgado a secar 10 dias', 'Admin'),
    (2, None, 'germinacion', str(hoy - timedelta(days=90)), 'Cultivo iniciado', 'Admin'),
    (2, 'germinacion', 'vegetativo', str(hoy - timedelta(days=69)), 'Desarrollo normal', 'Admin'),
    (2, 'vegetativo', 'floracion', str(hoy - timedelta(days=20)), 'Cambio a 12/12', 'Admin'),
    (3, None, 'germinacion', str(hoy - timedelta(days=60)), 'Cultivo exterior iniciado', 'Admin'),
    (3, 'germinacion', 'vegetativo', str(hoy - timedelta(days=40)), 'Buen arraigo', 'Admin'),
    (3, 'vegetativo', 'floracion', str(hoy - timedelta(days=5)), 'Inicio de floracion natural', 'Admin'),
    (4, None, 'germinacion', str(hoy - timedelta(days=30)), 'Cultivo hidro iniciado', 'Admin'),
    (4, 'germinacion', 'plantula', str(hoy - timedelta(days=23)), 'Sistema radicular excelente', 'Admin'),
    (4, 'plantula', 'vegetativo', str(hoy - timedelta(days=10)), 'Transplante a DWC', 'Admin'),
    (5, None, 'germinacion', str(hoy - timedelta(days=150)), 'Cultivo invernadero', 'Admin'),
    (5, 'floracion', 'cosecha', str(hoy - timedelta(days=45)), 'Cosecha programada', 'Admin'),
    (5, 'cosecha', 'curado', str(hoy - timedelta(days=38)), 'Secado completado', 'Admin'),
    (5, 'curado', 'finalizado', str(hoy - timedelta(days=30)), 'Curado 8 dias, listo', 'Admin'),
    (6, None, 'germinacion', str(hoy - timedelta(days=15)), 'Semillas premium importadas', 'Admin'),
    (6, 'germinacion', 'plantula', str(hoy - timedelta(days=5)), '3/3 germinadas', 'Admin'),
]

for cid, e_ant, e_nueva, fecha, notas, prof in logs:
    db.execute('''INSERT INTO etapas_cultivo (cultivo_id, etapa_anterior, etapa_nueva, fecha, notas, registrado_por)
                  VALUES (?,?,?,?,?,?)''', (cid, e_ant, e_nueva, fecha, notas, prof))

db.commit()

# ── COSECHAS ──
cosechas = [
    (1, str(hoy - timedelta(days=18)), 4, 480.0, 105.0, 5, 'OG Kush premium, tricomas perfectos', 'Admin'),
    (5, str(hoy - timedelta(days=45)), 2, 310.0, 68.0, 4, 'Amnesia buena produccion', 'Admin'),
    (5, str(hoy - timedelta(days=44)), 2, 290.0, 62.0, 4, 'Segunda pasada cosecha', 'Admin'),
]
for cos in cosechas:
    db.execute('''INSERT INTO cosechas (cultivo_id, fecha, num_plantas, peso_humedo_g, peso_seco_g, calidad, notas, registrado_por)
                  VALUES (?,?,?,?,?,?,?,?)''', cos)

db.commit()

# ── PEDIDOS ──
todos_socios = db.execute("SELECT id, nombre, apellido, direccion FROM socios LIMIT 8").fetchall()

pedidos_data = [
    ('PD-0001', todos_socios[0]['id'], 'OG Kush', 10.0, 3500, 'transferencia', 'entregado',
     'delivery', 'Av. Corrientes 1234 Piso 3', 'Miguel', str(hoy - timedelta(days=5)),
     str(hoy - timedelta(days=4)), 'Entregado sin novedad'),
    ('PD-0002', todos_socios[1]['id'], 'OG Kush', 15.0, 5250, 'efectivo', 'entregado',
     'retiro', '', '', str(hoy - timedelta(days=3)),
     str(hoy - timedelta(days=3)), 'Retiro en punto'),
    ('PD-0003', todos_socios[2]['id'] if len(todos_socios) > 2 else todos_socios[0]['id'],
     'Amnesia Haze', 8.0, 2800, 'debito', 'en_camino',
     'delivery', 'Perón 456 Depto 2B', 'Miguel', str(hoy - timedelta(days=1)),
     None, 'Sale hoy a la tarde'),
    ('PD-0004', todos_socios[3]['id'] if len(todos_socios) > 3 else todos_socios[0]['id'],
     'OG Kush', 12.0, 4200, 'transferencia', 'preparando',
     'delivery', 'Av. Santa Fe 789', 'Carlos', str(hoy.isoformat()),
     None, 'Preparando para salida'),
    ('PD-0005', todos_socios[0]['id'], 'Amnesia Haze', 10.0, 3500, 'cuota', 'pendiente',
     'retiro', '', '', str(hoy.isoformat()),
     None, 'Confirmar disponibilidad'),
]

tok1 = secrets.token_urlsafe(16)
tok2 = secrets.token_urlsafe(16)
tok3 = secrets.token_urlsafe(16)
tok4 = secrets.token_urlsafe(16)
tok5 = secrets.token_urlsafe(16)
tokens = [tok1, tok2, tok3, tok4, tok5]

for i, p in enumerate(pedidos_data):
    codigo, sid, variedad, gramos, precio, pago, estado, tipo_e, direccion, repartidor, fecha_p, fecha_e, notas = p
    db.execute('''
        INSERT INTO pedidos (codigo, socio_id, variedad, gramos, precio, forma_pago,
        estado, tipo_entrega, direccion_entrega, delivery_persona,
        fecha_pedido, fecha_entrega, token_entrega, notas, registrado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (codigo, sid, variedad, gramos, precio, pago, estado, tipo_e,
          direccion, repartidor, fecha_p, fecha_e, tokens[i], notas, 'Admin'))

db.commit()

total_s = db.execute("SELECT COUNT(*) FROM socios").fetchone()[0]
total_c = db.execute("SELECT COUNT(*) FROM cultivos").fetchone()[0]
total_cos = db.execute("SELECT COUNT(*) FROM cosechas").fetchone()[0]
total_p = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]

print(f"Demo cargado: {total_s} socios | {total_c} cultivos | {total_cos} cosechas | {total_p} pedidos")
db.close()
