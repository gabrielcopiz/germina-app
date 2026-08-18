import os, sqlite3, csv, io, secrets
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, make_response, g)

app = Flask(__name__)
app.secret_key = os.environ.get('CW_SECRET_KEY', 'cannawaka-dev-2026')

DB_PATH   = os.environ.get('CW_DB_PATH', 'cannawaka.db')
ADMIN_USER = os.environ.get('CW_ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('CW_ADMIN_PASS', 'germina2026')
CLUB_NOMBRE = os.environ.get('CW_CLUB_NOMBRE', 'Cannawaka')

# ─── helpers ───────────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()

def fmt_fecha(d):
    if not d: return '—'
    try:
        dt = datetime.strptime(str(d)[:10], '%Y-%m-%d')
        meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        return f"{dt.day} {meses[dt.month-1]}"
    except: return str(d)[:10]

def fmt_fecha_larga(d):
    if not d: return '—'
    try:
        dt = datetime.strptime(str(d)[:10], '%Y-%m-%d')
        dias = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
        meses = ['enero','febrero','marzo','abril','mayo','junio',
                 'julio','agosto','septiembre','octubre','noviembre','diciembre']
        return f"{dias[dt.weekday()]} {dt.day} de {meses[dt.month-1]}"
    except: return str(d)[:10]

app.jinja_env.globals.update(fmt_fecha=fmt_fecha, fmt_fecha_larga=fmt_fecha_larga, club_nombre=CLUB_NOMBRE)

ETAPAS = ['solicitud','documentacion','en_revision','aprobado','activo','inactivo']
ETAPA_LABEL = {
    'solicitud':     'Solicitud recibida',
    'documentacion': 'Pendiente docs',
    'en_revision':   'En revisión',
    'aprobado':      'Aprobado',
    'activo':        'Socio activo',
    'inactivo':      'Inactivo',
}
ETAPA_COLOR = {
    'solicitud':     '#7A736C',
    'documentacion': '#B8953F',
    'en_revision':   '#4A7C5E',
    'aprobado':      '#1A3520',
    'activo':        '#2D5C38',
    'inactivo':      '#999',
}

TIPO_SOCIO_LABEL = {
    'paciente':  'Paciente',
    'productor': 'Autocultivador',
    'cuidador':  'Cuidador',
    'investigador': 'Investigador',
}

# ─── cultivos ──────────────────────────────────────────────────────────────

ETAPAS_CULTIVO = ['germinacion','plantula','vegetativo','prefloracion','floracion','cosecha','curado','finalizado']
ETAPA_CULTIVO_LABEL = {
    'germinacion':  'Germinación',
    'plantula':     'Plántula',
    'vegetativo':   'Vegetativo',
    'prefloracion': 'Pre-floración',
    'floracion':    'Floración',
    'cosecha':      'Cosecha',
    'curado':       'Curado',
    'finalizado':   'Finalizado',
}
ETAPA_CULTIVO_COLOR = {
    'germinacion':  '#7A736C',
    'plantula':     '#6BAA6B',
    'vegetativo':   '#2D5C38',
    'prefloracion': '#C8A44A',
    'floracion':    '#E07B30',
    'cosecha':      '#1A3520',
    'curado':       '#5C3D8F',
    'finalizado':   '#999',
}
ETAPA_CULTIVO_DIAS = {
    'germinacion': 7, 'plantula': 21, 'vegetativo': 45,
    'prefloracion': 14, 'floracion': 60, 'cosecha': 7, 'curado': 21,
}
GENETICA_LABEL = {
    'indica':       'Índica',
    'sativa':       'Sativa',
    'hibrido':      'Híbrido',
    'cbd_dominante':'CBD dominante',
    'auto':         'Autofloreciente',
}
TIPO_CULTIVO_LABEL = {
    'interior': 'Interior (indoor)',
    'exterior': 'Exterior (outdoor)',
    'invernadero': 'Invernadero',
}

ESTADOS_PEDIDO = ['pendiente', 'preparando', 'en_camino', 'entregado', 'cancelado']
ESTADO_PEDIDO_LABEL = {
    'pendiente':  'Pendiente',
    'preparando': 'Preparando',
    'en_camino':  'En camino',
    'entregado':  'Entregado',
    'cancelado':  'Cancelado',
}
ESTADO_PEDIDO_COLOR = {
    'pendiente':  '#C8A44A',
    'preparando': '#2D5C38',
    'en_camino':  '#E07B30',
    'entregado':  '#1A3520',
    'cancelado':  '#999',
}
ESTADO_PEDIDO_NEXT = {
    'pendiente':  'preparando',
    'preparando': 'en_camino',
    'en_camino':  'entregado',
}
FORMA_PAGO_LABEL = {
    'efectivo':     'Efectivo',
    'transferencia':'Transferencia',
    'debito':       'Débito',
    'credito':      'Crédito',
    'cuota':        'Cuota del club',
}
TIPO_ENTREGA_LABEL = {
    'delivery': 'Delivery a domicilio',
    'retiro':   'Retiro en punto',
}

# ─── DB init ───────────────────────────────────────────────────────────────

def _next_codigo(db):
    row = db.execute("SELECT MAX(CAST(SUBSTR(codigo,4) AS INTEGER)) FROM cultivos WHERE codigo LIKE 'CW-%'").fetchone()[0]
    return f"CW-{(row or 0)+1:04d}"

def _next_codigo_pedido(db):
    row = db.execute("SELECT MAX(CAST(SUBSTR(codigo,4) AS INTEGER)) FROM pedidos WHERE codigo LIKE 'PD-%'").fetchone()[0]
    return f"PD-{(row or 0)+1:04d}"

# Registrar globals que dependen de constantes (se llama al final del módulo)
def _register_globals():
    app.jinja_env.globals.update(
        estado_pedido_label=ESTADO_PEDIDO_LABEL,
        estado_pedido_color=ESTADO_PEDIDO_COLOR,
        forma_pago_label=FORMA_PAGO_LABEL,
        tipo_entrega_label=TIPO_ENTREGA_LABEL,
    )

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS socios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        -- datos personales
        nombre TEXT, apellido TEXT, dni TEXT, email TEXT, telefono TEXT,
        fecha_nac TEXT, genero TEXT, barrio TEXT, provincia TEXT,
        -- tipo y condición
        tipo_socio TEXT DEFAULT 'paciente',
        diagnostico TEXT, patologia_especifica TEXT,
        tiempo_condicion TEXT,
        -- médico
        medico_prescriptor TEXT, especialidad_medico TEXT, tiene_receta TEXT,
        -- cannábico
        experiencia_cannabis TEXT, metodo_consumo TEXT, frecuencia_uso TEXT,
        -- trazabilidad
        como_nos_conocio TEXT, referido_por TEXT, referidor_es_socio INTEGER DEFAULT 0,
        canal_detalle TEXT,
        -- notas y estado
        etapa TEXT DEFAULT 'solicitud',
        notas_solicitud TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        socio_id INTEGER NOT NULL,
        texto TEXT NOT NULL,
        profesional TEXT DEFAULT 'Admin',
        fecha TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (socio_id) REFERENCES socios(id)
    );
    CREATE TABLE IF NOT EXISTS documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        socio_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        estado TEXT DEFAULT 'pendiente',
        notas TEXT,
        fecha TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (socio_id) REFERENCES socios(id)
    );
    CREATE TABLE IF NOT EXISTS cultivos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        socio_id INTEGER NOT NULL,
        variedad TEXT NOT NULL,
        genetica TEXT DEFAULT 'hibrido',
        num_plantas INTEGER DEFAULT 1,
        tipo_cultivo TEXT DEFAULT 'interior',
        fecha_inicio TEXT NOT NULL,
        etapa_actual TEXT DEFAULT 'germinacion',
        fecha_etapa TEXT DEFAULT (date('now')),
        dias_en_etapa INTEGER DEFAULT 0,
        cosecha_estimada TEXT,
        ubicacion_detalle TEXT,
        sustrato TEXT,
        notas TEXT,
        estado TEXT DEFAULT 'activo',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS etapas_cultivo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cultivo_id INTEGER NOT NULL,
        etapa_anterior TEXT,
        etapa_nueva TEXT NOT NULL,
        fecha TEXT DEFAULT (datetime('now','localtime')),
        notas TEXT,
        registrado_por TEXT DEFAULT 'Admin',
        FOREIGN KEY (cultivo_id) REFERENCES cultivos(id)
    );
    CREATE TABLE IF NOT EXISTS cosechas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cultivo_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        num_plantas INTEGER DEFAULT 1,
        peso_humedo_g REAL DEFAULT 0,
        peso_seco_g REAL DEFAULT 0,
        calidad INTEGER DEFAULT 3,
        notas TEXT,
        registrado_por TEXT DEFAULT 'Admin',
        FOREIGN KEY (cultivo_id) REFERENCES cultivos(id)
    );
    CREATE TABLE IF NOT EXISTS dispensaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        socio_id INTEGER NOT NULL,
        variedad TEXT NOT NULL,
        gramos REAL NOT NULL,
        fecha TEXT DEFAULT (date('now')),
        notas TEXT,
        registrado_por TEXT DEFAULT 'Admin',
        FOREIGN KEY (socio_id) REFERENCES socios(id)
    );
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        socio_id INTEGER NOT NULL,
        variedad TEXT NOT NULL,
        gramos REAL NOT NULL,
        precio REAL DEFAULT 0,
        forma_pago TEXT DEFAULT 'efectivo',
        estado TEXT DEFAULT 'pendiente',
        tipo_entrega TEXT DEFAULT 'delivery',
        direccion_entrega TEXT,
        delivery_persona TEXT,
        fecha_pedido TEXT DEFAULT (datetime('now','localtime')),
        fecha_entrega TEXT,
        token_entrega TEXT UNIQUE,
        notas TEXT,
        registrado_por TEXT DEFAULT 'Admin',
        FOREIGN KEY (socio_id) REFERENCES socios(id)
    );
    ''')
    db.commit()
    db.close()

def _migrate():
    db = sqlite3.connect(DB_PATH)
    # socios extras
    cols = {r[1] for r in db.execute("PRAGMA table_info(socios)")}
    for col, typedef in {
        'provincia': "TEXT DEFAULT 'Buenos Aires'",
        'como_nos_conocio': 'TEXT',
        'canal_detalle': 'TEXT',
        'referidor_es_socio': 'INTEGER DEFAULT 0',
        'cupo_mensual_g': 'REAL DEFAULT 30',
        'direccion': 'TEXT',
        'referencias_entrega': 'TEXT',
    }.items():
        if col not in cols:
            db.execute(f'ALTER TABLE socios ADD COLUMN {col} {typedef}')
    # cultivos extras
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'cultivos' not in tables:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS cultivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            socio_id INTEGER NOT NULL,
            variedad TEXT NOT NULL,
            genetica TEXT DEFAULT 'hibrido',
            num_plantas INTEGER DEFAULT 1,
            tipo_cultivo TEXT DEFAULT 'interior',
            fecha_inicio TEXT NOT NULL,
            etapa_actual TEXT DEFAULT 'germinacion',
            fecha_etapa TEXT DEFAULT (date('now')),
            dias_en_etapa INTEGER DEFAULT 0,
            cosecha_estimada TEXT,
            ubicacion_detalle TEXT,
            sustrato TEXT,
            notas TEXT,
            estado TEXT DEFAULT 'activo',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS etapas_cultivo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cultivo_id INTEGER NOT NULL,
            etapa_anterior TEXT,
            etapa_nueva TEXT NOT NULL,
            fecha TEXT DEFAULT (datetime('now','localtime')),
            notas TEXT,
            registrado_por TEXT DEFAULT 'Admin'
        );
        CREATE TABLE IF NOT EXISTS cosechas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cultivo_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            num_plantas INTEGER DEFAULT 1,
            peso_humedo_g REAL DEFAULT 0,
            peso_seco_g REAL DEFAULT 0,
            calidad INTEGER DEFAULT 3,
            notas TEXT,
            registrado_por TEXT DEFAULT 'Admin'
        );
        ''')
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'dispensaciones' not in tables:
        db.execute('''CREATE TABLE dispensaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            socio_id INTEGER NOT NULL, variedad TEXT NOT NULL,
            gramos REAL NOT NULL, fecha TEXT DEFAULT (date('now')),
            notas TEXT, registrado_por TEXT DEFAULT 'Admin')''')
    if 'pedidos' not in tables:
        db.execute('''CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL, socio_id INTEGER NOT NULL,
            variedad TEXT NOT NULL, gramos REAL NOT NULL,
            precio REAL DEFAULT 0, forma_pago TEXT DEFAULT 'efectivo',
            estado TEXT DEFAULT 'pendiente',
            tipo_entrega TEXT DEFAULT 'delivery',
            direccion_entrega TEXT, delivery_persona TEXT,
            fecha_pedido TEXT DEFAULT (datetime('now','localtime')),
            fecha_entrega TEXT, token_entrega TEXT UNIQUE,
            notas TEXT, registrado_por TEXT DEFAULT 'Admin')''')
    db.commit()
    db.close()

# ─── auth ──────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapped

# ═══════════════════════════════════════════════════════════════════════════
#  CARA PÚBLICA
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/unirme', methods=['GET','POST'])
def solicitud():
    if request.method == 'POST':
        token = secrets.token_urlsafe(20)
        f = request.form
        db = get_db()
        db.execute('''
            INSERT INTO socios
            (token, nombre, apellido, dni, email, telefono, fecha_nac, genero, barrio, provincia,
             tipo_socio, diagnostico, patologia_especifica, tiempo_condicion,
             medico_prescriptor, especialidad_medico, tiene_receta,
             experiencia_cannabis, metodo_consumo, frecuencia_uso,
             como_nos_conocio, referido_por, canal_detalle, notas_solicitud)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            token,
            f.get('nombre','').strip(), f.get('apellido','').strip(),
            f.get('dni','').strip(), f.get('email','').strip(),
            f.get('telefono','').strip(), f.get('fecha_nac',''),
            f.get('genero',''), f.get('barrio','').strip(),
            f.get('provincia', 'Buenos Aires').strip(),
            f.get('tipo_socio','paciente'),
            f.get('diagnostico','').strip(), f.get('patologia_especifica','').strip(),
            f.get('tiempo_condicion',''),
            f.get('medico_prescriptor','').strip(), f.get('especialidad_medico','').strip(),
            f.get('tiene_receta',''),
            f.get('experiencia_cannabis',''), f.get('metodo_consumo',''),
            f.get('frecuencia_uso',''),
            f.get('como_nos_conocio',''), f.get('referido_por','').strip(),
            f.get('canal_detalle','').strip(), f.get('notas_solicitud','').strip(),
        ))
        db.commit()
        return redirect(url_for('confirmacion', token=token))
    return render_template('solicitud.html')

@app.route('/confirmacion/<token>')
def confirmacion(token):
    db = get_db()
    s = db.execute('SELECT * FROM socios WHERE token=?', (token,)).fetchone()
    if not s: return redirect(url_for('landing'))
    return render_template('confirmacion.html', s=s)

@app.route('/mi-estado/<token>')
def portal(token):
    db = get_db()
    s = db.execute('SELECT * FROM socios WHERE token=?', (token,)).fetchone()
    if not s: return redirect(url_for('landing'))
    docs = db.execute('SELECT * FROM documentos WHERE socio_id=? ORDER BY fecha DESC', (s['id'],)).fetchall()
    return render_template('portal.html', s=s, docs=docs,
                           etapa_label=ETAPA_LABEL, etapa_color=ETAPA_COLOR)

# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('user') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Credenciales incorrectas')
    return render_template('admin/login.html')

@app.route('/demo')
def demo_access():
    session['admin'] = True
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    db = get_db()
    hoy = date.today().isoformat()
    mes_inicio = date.today().replace(day=1).isoformat()

    total       = db.execute('SELECT COUNT(*) FROM socios').fetchone()[0]
    nuevos_mes  = db.execute('SELECT COUNT(*) FROM socios WHERE created_at >= ?', (mes_inicio,)).fetchone()[0]
    nuevos_hoy  = db.execute('SELECT COUNT(*) FROM socios WHERE DATE(created_at) = ?', (hoy,)).fetchone()[0]
    activos     = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]
    aprobados   = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='aprobado'").fetchone()[0]
    en_revision = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='en_revision'").fetchone()[0]

    tasa = round((activos / total * 100)) if total else 0

    funnel = {}
    for e in ETAPAS:
        funnel[e] = db.execute("SELECT COUNT(*) FROM socios WHERE etapa=?", (e,)).fetchone()[0]

    origenes = db.execute('''
        SELECT como_nos_conocio as origen, COUNT(*) as cnt
        FROM socios WHERE como_nos_conocio IS NOT NULL AND como_nos_conocio != ''
        GROUP BY como_nos_conocio ORDER BY cnt DESC LIMIT 8
    ''').fetchall()

    top_referidores = db.execute('''
        SELECT referido_por, COUNT(*) as cnt
        FROM socios WHERE referido_por IS NOT NULL AND referido_por != ''
        GROUP BY referido_por ORDER BY cnt DESC LIMIT 6
    ''').fetchall()

    tipos = db.execute('''
        SELECT tipo_socio, COUNT(*) as cnt FROM socios
        GROUP BY tipo_socio ORDER BY cnt DESC
    ''').fetchall()

    diagnosticos = db.execute('''
        SELECT diagnostico, COUNT(*) as cnt FROM socios
        WHERE diagnostico IS NOT NULL AND diagnostico != ''
        GROUP BY diagnostico ORDER BY cnt DESC LIMIT 8
    ''').fetchall()

    generos = db.execute('''
        SELECT genero, COUNT(*) as cnt FROM socios
        WHERE genero IS NOT NULL AND genero != ''
        GROUP BY genero ORDER BY cnt DESC
    ''').fetchall()

    barrios = db.execute('''
        SELECT barrio, COUNT(*) as cnt FROM socios
        WHERE barrio IS NOT NULL AND barrio != ''
        GROUP BY barrio ORDER BY cnt DESC LIMIT 8
    ''').fetchall()

    medicos = db.execute('''
        SELECT medico_prescriptor, especialidad_medico, COUNT(*) as cnt
        FROM socios WHERE medico_prescriptor IS NOT NULL AND medico_prescriptor != ''
        GROUP BY medico_prescriptor ORDER BY cnt DESC LIMIT 6
    ''').fetchall()

    ultimos = db.execute('''
        SELECT * FROM socios ORDER BY created_at DESC LIMIT 10
    ''').fetchall()

    # ── métricas de cultivos ──
    mes_inicio_s = date.today().replace(day=1).isoformat()
    total_plantas_activas = db.execute(
        "SELECT COALESCE(SUM(num_plantas),0) FROM cultivos WHERE estado='activo'"
    ).fetchone()[0]
    cultivos_activos = db.execute(
        "SELECT COUNT(*) FROM cultivos WHERE estado='activo'"
    ).fetchone()[0]
    cosecha_mes_g = db.execute(
        "SELECT COALESCE(SUM(peso_seco_g),0) FROM cosechas WHERE fecha >= ?", (mes_inicio_s,)
    ).fetchone()[0]
    cosecha_total_g = db.execute(
        "SELECT COALESCE(SUM(peso_seco_g),0) FROM cosechas"
    ).fetchone()[0]
    plantas_por_etapa = {}
    for e in ETAPAS_CULTIVO:
        plantas_por_etapa[e] = db.execute(
            "SELECT COALESCE(SUM(num_plantas),0) FROM cultivos WHERE etapa_actual=? AND estado='activo'", (e,)
        ).fetchone()[0]
    top_variedades = db.execute('''
        SELECT variedad, COUNT(*) as cnt, SUM(num_plantas) as plantas
        FROM cultivos GROUP BY variedad ORDER BY plantas DESC LIMIT 6
    ''').fetchall()
    proximas_cosechas = db.execute('''
        SELECT c.*, s.nombre, s.apellido
        FROM cultivos c JOIN socios s ON s.id=c.socio_id
        WHERE c.estado='activo' AND c.cosecha_estimada IS NOT NULL
          AND c.cosecha_estimada >= date('now')
        ORDER BY c.cosecha_estimada ASC LIMIT 6
    ''').fetchall()

    # ── alertas: stock bajo (<50g disponibles por variedad) ──
    alertas_stock_bajo = []
    for row in db.execute('''
        SELECT cu.variedad, COALESCE(SUM(co.peso_seco_g),0) as total_g
        FROM cosechas co JOIN cultivos cu ON cu.id = co.cultivo_id
        GROUP BY cu.variedad
    ''').fetchall():
        v = row['variedad']
        entregado = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE variedad=? AND estado='entregado'", (v,)
        ).fetchone()[0]
        reservado = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE variedad=? AND estado IN ('pendiente','preparando','en_camino')", (v,)
        ).fetchone()[0]
        disponible = round((row['total_g'] or 0) - entregado - reservado, 1)
        if disponible < 50:
            alertas_stock_bajo.append({'variedad': v, 'disponible_g': disponible})

    # ── alertas: cosechas en los próximos 14 días ──
    cosechas_urgentes = db.execute('''
        SELECT c.id, c.codigo, c.variedad, c.cosecha_estimada, c.num_plantas, s.nombre, s.apellido
        FROM cultivos c JOIN socios s ON s.id=c.socio_id
        WHERE c.estado='activo' AND c.cosecha_estimada IS NOT NULL
          AND c.cosecha_estimada >= date('now')
          AND c.cosecha_estimada <= date('now', '+14 days')
        ORDER BY c.cosecha_estimada ASC
    ''').fetchall()

    # ── pedidos que necesitan atención ──
    pedidos_pendientes = db.execute(
        "SELECT COUNT(*) FROM pedidos WHERE estado IN ('pendiente','preparando')"
    ).fetchone()[0]

    # ── Datos para gráfico de últimas 8 semanas ──
    chart_semanas = []
    for i in range(7, -1, -1):
        semana_inicio = (date.today() - timedelta(weeks=i)).isoformat()
        semana_fin = (date.today() - timedelta(weeks=i-1)).isoformat()
        cnt = db.execute(
            "SELECT COUNT(*) FROM socios WHERE DATE(created_at) >= ? AND DATE(created_at) < ?",
            (semana_inicio, semana_fin)
        ).fetchone()[0]
        label = f"S-{8-i}"
        chart_semanas.append({'label': label, 'cnt': cnt})

    # ── KPIs de hoy para el dashboard ──
    disp_hoy_count = db.execute(
        "SELECT COUNT(*) FROM dispensaciones WHERE fecha = ?", (hoy,)
    ).fetchone()[0]
    disp_hoy_g = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE fecha = ?", (hoy,)
    ).fetchone()[0]
    disp_hoy_socios = db.execute(
        "SELECT COUNT(DISTINCT socio_id) FROM dispensaciones WHERE fecha = ?", (hoy,)
    ).fetchone()[0]

    return render_template('admin/dashboard.html',
        total=total, nuevos_mes=nuevos_mes, nuevos_hoy=nuevos_hoy,
        activos=activos, aprobados=aprobados, en_revision=en_revision,
        tasa_activacion=tasa,
        funnel=funnel, origenes=origenes,
        top_referidores=top_referidores, tipos=tipos,
        diagnosticos=diagnosticos, generos=generos,
        barrios=barrios, medicos=medicos, ultimos=ultimos,
        etapa_label=ETAPA_LABEL, etapa_color=ETAPA_COLOR,
        tipo_socio_label=TIPO_SOCIO_LABEL,
        # cultivos
        total_plantas_activas=total_plantas_activas,
        cultivos_activos=cultivos_activos,
        cosecha_mes_g=round(cosecha_mes_g, 1),
        cosecha_total_g=round(cosecha_total_g, 1),
        plantas_por_etapa=plantas_por_etapa,
        top_variedades=top_variedades,
        proximas_cosechas=proximas_cosechas,
        etapas_cultivo=ETAPAS_CULTIVO,
        etapa_cultivo_label=ETAPA_CULTIVO_LABEL,
        etapa_cultivo_color=ETAPA_CULTIVO_COLOR,
        # alertas
        alertas_stock_bajo=alertas_stock_bajo,
        cosechas_urgentes=cosechas_urgentes,
        pedidos_pendientes=pedidos_pendientes,
        # gráfico actividad
        chart_semanas=chart_semanas,
        # kpis de hoy
        disp_hoy_count=disp_hoy_count,
        disp_hoy_g=round(disp_hoy_g, 1),
        disp_hoy_socios=disp_hoy_socios,
    )

@app.route('/admin/dispensario', methods=['GET','POST'])
@login_required
def admin_dispensario():
    db = get_db()
    hoy = date.today().isoformat()

    if request.method == 'POST':
        socio_id = request.form.get('socio_id')
        variedad = request.form.get('variedad','').strip()
        gramos   = float(request.form.get('gramos', 0) or 0)
        notas    = request.form.get('notas','').strip()
        if socio_id and variedad and gramos > 0:
            db.execute(
                "INSERT INTO dispensaciones (socio_id, variedad, gramos, fecha, notas) VALUES (?,?,?,?,?)",
                (socio_id, variedad, gramos, hoy, notas)
            )
            db.commit()
            flash(f'Dispensación registrada: {gramos}g de {variedad}')
        return redirect(url_for('admin_dispensario'))

    socios_activos = db.execute(
        "SELECT id, nombre, apellido, etapa, cupo_mensual_g FROM socios WHERE etapa IN ('activo','aprobado') ORDER BY nombre"
    ).fetchall()

    variedades_stock = db.execute('''
        SELECT DISTINCT cu.variedad
        FROM cosechas co JOIN cultivos cu ON cu.id = co.cultivo_id
        ORDER BY cu.variedad
    ''').fetchall()

    dispensaciones_hoy = db.execute('''
        SELECT d.*, s.nombre, s.apellido
        FROM dispensaciones d JOIN socios s ON s.id = d.socio_id
        WHERE d.fecha = ?
        ORDER BY d.id DESC
    ''', (hoy,)).fetchall()

    total_hoy_g = sum(d['gramos'] for d in dispensaciones_hoy)

    return render_template('admin/dispensario.html',
        socios_activos=[dict(s) for s in socios_activos],
        variedades_stock=variedades_stock,
        dispensaciones_hoy=dispensaciones_hoy,
        total_hoy_g=round(total_hoy_g, 1),
        hoy=hoy,
    )


@app.route('/admin/informe')
@login_required
def admin_informe():
    db = get_db()
    hoy = date.today().isoformat()
    fecha_param = request.args.get('fecha', hoy)

    dispensaciones = db.execute('''
        SELECT d.*, s.nombre, s.apellido
        FROM dispensaciones d JOIN socios s ON s.id = d.socio_id
        WHERE d.fecha = ?
        ORDER BY d.id ASC
    ''', (fecha_param,)).fetchall()

    resumen_variedades = db.execute('''
        SELECT variedad, COUNT(*) as cnt, SUM(gramos) as total_g
        FROM dispensaciones WHERE fecha = ?
        GROUP BY variedad ORDER BY total_g DESC
    ''', (fecha_param,)).fetchall()

    pedidos_entregados = db.execute('''
        SELECT p.*, s.nombre, s.apellido
        FROM pedidos p JOIN socios s ON s.id = p.socio_id
        WHERE DATE(p.fecha_entrega) = ? AND p.estado = 'entregado'
        ORDER BY p.fecha_entrega DESC
    ''', (fecha_param,)).fetchall()

    socios_atendidos = len(set(d['socio_id'] for d in dispensaciones))
    total_g = sum(d['gramos'] for d in dispensaciones)
    variedades_count = len(set(d['variedad'] for d in dispensaciones))

    return render_template('admin/informe.html',
        dispensaciones=dispensaciones,
        resumen_variedades=resumen_variedades,
        pedidos_entregados=pedidos_entregados,
        socios_atendidos=socios_atendidos,
        total_g=round(total_g, 1),
        variedades_count=variedades_count,
        pedidos_entregados_count=len(pedidos_entregados),
        fecha=fecha_param,
        hoy=hoy,
        forma_pago_label=FORMA_PAGO_LABEL,
    )


@app.route('/admin/socios')
@login_required
def admin_socios():
    db = get_db()
    etapa_f = request.args.get('etapa','')
    origen_f = request.args.get('origen','')
    q = request.args.get('q','').strip()

    sql = 'SELECT * FROM socios WHERE 1=1'
    params = []
    if etapa_f:
        sql += ' AND etapa=?'; params.append(etapa_f)
    if origen_f:
        sql += ' AND como_nos_conocio=?'; params.append(origen_f)
    if q:
        sql += ' AND (nombre LIKE ? OR apellido LIKE ? OR dni LIKE ? OR email LIKE ?)'
        params += [f'%{q}%']*4
    sql += ' ORDER BY created_at DESC'
    socios = db.execute(sql, params).fetchall()

    totales = {e: db.execute("SELECT COUNT(*) FROM socios WHERE etapa=?", (e,)).fetchone()[0] for e in ETAPAS}

    return render_template('admin/socios.html',
        socios=socios, etapa_f=etapa_f, origen_f=origen_f, q=q,
        etapas=ETAPAS, etapa_label=ETAPA_LABEL, etapa_color=ETAPA_COLOR,
        totales=totales, tipo_socio_label=TIPO_SOCIO_LABEL,
    )

@app.route('/admin/socio/<int:sid>')
@login_required
def admin_socio(sid):
    db = get_db()
    s = db.execute('SELECT * FROM socios WHERE id=?', (sid,)).fetchone()
    if not s: return redirect(url_for('admin_socios'))
    notas    = db.execute('SELECT * FROM notas WHERE socio_id=? ORDER BY fecha DESC', (sid,)).fetchall()
    docs     = db.execute('SELECT * FROM documentos WHERE socio_id=? ORDER BY fecha DESC', (sid,)).fetchall()
    cultivos = db.execute('SELECT * FROM cultivos WHERE socio_id=? ORDER BY created_at DESC', (sid,)).fetchall()
    pedidos = db.execute('''
        SELECT * FROM pedidos WHERE socio_id=? ORDER BY fecha_pedido DESC
    ''', (sid,)).fetchall()
    mes_inicio = date.today().replace(day=1).isoformat()
    consumido_mes = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND fecha_pedido >= ? AND estado='entregado'",
        (sid, mes_inicio)
    ).fetchone()[0]
    total_consumido = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND estado='entregado'", (sid,)
    ).fetchone()[0]
    total_gastado = db.execute(
        "SELECT COALESCE(SUM(precio),0) FROM pedidos WHERE socio_id=? AND estado='entregado'", (sid,)
    ).fetchone()[0]
    stock_variedades = db.execute('''
        SELECT cu.variedad,
               COALESCE(SUM(co.peso_seco_g),0)
               - COALESCE((SELECT SUM(gramos) FROM pedidos WHERE variedad=cu.variedad AND estado='entregado'),0)
               - COALESCE((SELECT SUM(gramos) FROM pedidos WHERE variedad=cu.variedad AND estado IN ('pendiente','preparando','en_camino')),0)
               as disponible_g
        FROM cosechas co JOIN cultivos cu ON cu.id = co.cultivo_id
        GROUP BY cu.variedad HAVING disponible_g > 0 ORDER BY cu.variedad
    ''').fetchall()
    member_url = url_for('portal', token=s['token'], _external=True)
    return render_template('admin/socio.html',
        s=s, notas=notas, docs=docs, cultivos=cultivos,
        pedidos=pedidos, consumido_mes=consumido_mes,
        total_consumido=total_consumido, total_gastado=total_gastado,
        stock_variedades=stock_variedades, member_url=member_url,
        etapas=ETAPAS, etapa_label=ETAPA_LABEL, etapa_color=ETAPA_COLOR,
        tipo_socio_label=TIPO_SOCIO_LABEL,
        etapas_cultivo=ETAPAS_CULTIVO,
        etapa_cultivo_label=ETAPA_CULTIVO_LABEL,
        etapa_cultivo_color=ETAPA_CULTIVO_COLOR,
        genetica_label=GENETICA_LABEL,
        tipo_cultivo_label=TIPO_CULTIVO_LABEL,
        estados_pedido=ESTADOS_PEDIDO,
        forma_pago_label=FORMA_PAGO_LABEL,
        tipo_entrega_label=TIPO_ENTREGA_LABEL,
    )

@app.route('/admin/socio/<int:sid>/etapa', methods=['POST'])
@login_required
def admin_set_etapa(sid):
    etapa = request.form.get('etapa','')
    if etapa in ETAPAS:
        get_db().execute('UPDATE socios SET etapa=?, updated_at=datetime("now","localtime") WHERE id=?', (etapa, sid))
        get_db().commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(ok=True)
    return redirect(url_for('admin_socio', sid=sid))

@app.route('/admin/socio/<int:sid>/nota', methods=['POST'])
@login_required
def admin_agregar_nota(sid):
    texto = request.form.get('texto','').strip()
    prof  = request.form.get('profesional','Admin').strip() or 'Admin'
    if texto:
        get_db().execute('INSERT INTO notas (socio_id, texto, profesional) VALUES (?,?,?)', (sid, texto, prof))
        get_db().commit()
    return redirect(url_for('admin_socio', sid=sid))

@app.route('/admin/socio/<int:sid>/documento', methods=['POST'])
@login_required
def admin_agregar_doc(sid):
    tipo   = request.form.get('tipo','').strip()
    estado = request.form.get('estado','pendiente')
    notas  = request.form.get('notas','').strip()
    if tipo:
        get_db().execute('INSERT INTO documentos (socio_id, tipo, estado, notas) VALUES (?,?,?,?)',
                        (sid, tipo, estado, notas))
        get_db().commit()
    return redirect(url_for('admin_socio', sid=sid))

@app.route('/admin/exportar')
@login_required
def admin_exportar():
    db = get_db()
    rows = db.execute('SELECT * FROM socios ORDER BY created_at DESC').fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    if rows:
        w.writerow(rows[0].keys())
        for r in rows: w.writerow(list(r))
    resp = make_response(out.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=cannawaka_socios_{date.today()}.csv'
    return resp

@app.route('/admin/exportar/cultivos')
@login_required
def admin_exportar_cultivos():
    db = get_db()
    rows = db.execute('''
        SELECT c.codigo, c.variedad, c.genetica, c.num_plantas, c.tipo_cultivo,
               c.fecha_inicio, c.etapa_actual, c.cosecha_estimada, c.sustrato,
               c.ubicacion_detalle, c.estado, c.notas, c.created_at,
               s.nombre, s.apellido, s.dni
        FROM cultivos c JOIN socios s ON s.id = c.socio_id
        ORDER BY c.created_at DESC
    ''').fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    if rows:
        w.writerow(rows[0].keys())
        for r in rows: w.writerow(list(r))
    resp = make_response(out.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=cannawaka_cultivos_{date.today()}.csv'
    return resp

@app.route('/admin/exportar/pedidos')
@login_required
def admin_exportar_pedidos():
    db = get_db()
    rows = db.execute('''
        SELECT p.codigo, p.variedad, p.gramos, p.precio, p.forma_pago,
               p.estado, p.tipo_entrega, p.direccion_entrega, p.delivery_persona,
               p.fecha_pedido, p.fecha_entrega, p.notas,
               s.nombre, s.apellido, s.dni, s.telefono
        FROM pedidos p JOIN socios s ON s.id = p.socio_id
        ORDER BY p.fecha_pedido DESC
    ''').fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    if rows:
        w.writerow(rows[0].keys())
        for r in rows: w.writerow(list(r))
    resp = make_response(out.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=cannawaka_pedidos_{date.today()}.csv'
    return resp

# ═══════════════════════════════════════════════════════════════════════════
#  CULTIVOS — TRAZABILIDAD
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/cultivos')
@login_required
def admin_cultivos():
    db = get_db()
    etapa_f  = request.args.get('etapa', '')
    estado_f = request.args.get('estado', 'activo')
    q        = request.args.get('q', '').strip()

    sql = '''
        SELECT c.*, s.nombre, s.apellido, s.dni, s.tipo_socio
        FROM cultivos c
        JOIN socios s ON s.id = c.socio_id
        WHERE 1=1
    '''
    params = []
    if estado_f:
        sql += ' AND c.estado=?'; params.append(estado_f)
    if etapa_f:
        sql += ' AND c.etapa_actual=?'; params.append(etapa_f)
    if q:
        sql += ' AND (c.variedad LIKE ? OR c.codigo LIKE ? OR s.nombre LIKE ? OR s.apellido LIKE ?)'
        params += [f'%{q}%']*4
    sql += ' ORDER BY c.created_at DESC'
    cultivos = db.execute(sql, params).fetchall()

    # métricas rápidas
    total_plantas   = db.execute("SELECT COALESCE(SUM(num_plantas),0) FROM cultivos WHERE estado='activo'").fetchone()[0]
    total_cosechado = db.execute("SELECT COALESCE(SUM(peso_seco_g),0) FROM cosechas").fetchone()[0]
    por_etapa = {}
    for e in ETAPAS_CULTIVO:
        por_etapa[e] = db.execute(
            "SELECT COALESCE(SUM(num_plantas),0) FROM cultivos WHERE etapa_actual=? AND estado='activo'", (e,)
        ).fetchone()[0]

    return render_template('admin/cultivos.html',
        cultivos=cultivos, etapa_f=etapa_f, estado_f=estado_f, q=q,
        total_plantas=total_plantas, total_cosechado=total_cosechado,
        por_etapa=por_etapa,
        etapas_cultivo=ETAPAS_CULTIVO,
        etapa_cultivo_label=ETAPA_CULTIVO_LABEL,
        etapa_cultivo_color=ETAPA_CULTIVO_COLOR,
        genetica_label=GENETICA_LABEL,
        tipo_cultivo_label=TIPO_CULTIVO_LABEL,
        tipo_socio_label=TIPO_SOCIO_LABEL,
    )

@app.route('/admin/cultivo/<int:cid>')
@login_required
def admin_cultivo(cid):
    db = get_db()
    c = db.execute('''
        SELECT c.*, s.nombre, s.apellido, s.dni, s.id as socio_id_real, s.tipo_socio
        FROM cultivos c JOIN socios s ON s.id = c.socio_id
        WHERE c.id=?
    ''', (cid,)).fetchone()
    if not c: return redirect(url_for('admin_cultivos'))

    log      = db.execute('SELECT * FROM etapas_cultivo WHERE cultivo_id=? ORDER BY fecha DESC', (cid,)).fetchall()
    cosechas = db.execute('SELECT * FROM cosechas WHERE cultivo_id=? ORDER BY fecha DESC', (cid,)).fetchall()
    total_seco   = sum(r['peso_seco_g'] for r in cosechas)
    total_humedo = sum(r['peso_humedo_g'] for r in cosechas)

    # días en etapa actual
    try:
        dias = (date.today() - datetime.strptime(c['fecha_etapa'][:10], '%Y-%m-%d').date()).days
    except:
        dias = 0

    return render_template('admin/cultivo.html',
        c=c, log=log, cosechas=cosechas,
        total_seco=total_seco, total_humedo=total_humedo,
        dias_etapa_actual=dias,
        today=date.today().isoformat(),
        etapas_cultivo=ETAPAS_CULTIVO,
        etapa_cultivo_label=ETAPA_CULTIVO_LABEL,
        etapa_cultivo_color=ETAPA_CULTIVO_COLOR,
        etapa_cultivo_dias=ETAPA_CULTIVO_DIAS,
        genetica_label=GENETICA_LABEL,
        tipo_cultivo_label=TIPO_CULTIVO_LABEL,
        tipo_socio_label=TIPO_SOCIO_LABEL,
    )

@app.route('/admin/socio/<int:sid>/cultivo/nuevo', methods=['POST'])
@login_required
def admin_nuevo_cultivo(sid):
    db = get_db()
    f = request.form
    variedad   = f.get('variedad','').strip()
    if not variedad:
        flash('La variedad es obligatoria')
        return redirect(url_for('admin_socio', sid=sid))

    codigo   = _next_codigo(db)
    fecha_i  = f.get('fecha_inicio', date.today().isoformat())
    genetica = f.get('genetica','hibrido')
    n_plant  = int(f.get('num_plantas', 1) or 1)
    tipo     = f.get('tipo_cultivo','interior')
    sustrato = f.get('sustrato','').strip()
    ubicacion= f.get('ubicacion_detalle','').strip()
    notas    = f.get('notas','').strip()

    # estimar cosecha: sumar días de todas las etapas
    dias_total = sum(ETAPA_CULTIVO_DIAS.values())
    try:
        cos_est = (datetime.strptime(fecha_i, '%Y-%m-%d') + timedelta(days=dias_total)).strftime('%Y-%m-%d')
    except:
        cos_est = None

    db.execute('''
        INSERT INTO cultivos
        (codigo, socio_id, variedad, genetica, num_plantas, tipo_cultivo,
         fecha_inicio, etapa_actual, fecha_etapa, cosecha_estimada,
         ubicacion_detalle, sustrato, notas, estado)
        VALUES (?,?,?,?,?,?,?,'germinacion',?,?,?,?,?,'activo')
    ''', (codigo, sid, variedad, genetica, n_plant, tipo,
          fecha_i, fecha_i, cos_est, ubicacion, sustrato, notas))

    cid = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    db.execute('''
        INSERT INTO etapas_cultivo (cultivo_id, etapa_anterior, etapa_nueva, notas, registrado_por)
        VALUES (?, NULL, 'germinacion', 'Cultivo iniciado', ?)
    ''', (cid, f.get('registrado_por','Admin')))
    db.commit()
    return redirect(url_for('admin_cultivo', cid=cid))

@app.route('/admin/cultivo/<int:cid>/etapa', methods=['POST'])
@login_required
def admin_cultivo_etapa(cid):
    db   = get_db()
    c    = db.execute('SELECT * FROM cultivos WHERE id=?', (cid,)).fetchone()
    if not c:
        return jsonify(ok=False), 404
    nueva    = request.form.get('etapa','')
    notas    = request.form.get('notas','').strip()
    prof     = request.form.get('registrado_por','Admin').strip() or 'Admin'
    if nueva not in ETAPAS_CULTIVO:
        return jsonify(ok=False, error='etapa inválida'), 400

    hoy = date.today().isoformat()
    db.execute('''
        UPDATE cultivos SET etapa_actual=?, fecha_etapa=?, estado=?
        WHERE id=?
    ''', (nueva, hoy, 'finalizado' if nueva == 'finalizado' else 'activo', cid))
    db.execute('''
        INSERT INTO etapas_cultivo (cultivo_id, etapa_anterior, etapa_nueva, notas, registrado_por)
        VALUES (?,?,?,?,?)
    ''', (cid, c['etapa_actual'], nueva, notas, prof))
    db.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(ok=True, etapa=nueva, label=ETAPA_CULTIVO_LABEL[nueva])
    return redirect(url_for('admin_cultivo', cid=cid))

@app.route('/admin/cultivo/<int:cid>/cosecha', methods=['POST'])
@login_required
def admin_registrar_cosecha(cid):
    db   = get_db()
    f    = request.form
    fecha      = f.get('fecha', date.today().isoformat())
    n_plant    = int(f.get('num_plantas', 1) or 1)
    peso_h     = float(f.get('peso_humedo_g', 0) or 0)
    peso_s     = float(f.get('peso_seco_g', 0) or 0)
    calidad    = int(f.get('calidad', 3) or 3)
    notas      = f.get('notas','').strip()
    prof       = f.get('registrado_por','Admin').strip() or 'Admin'

    db.execute('''
        INSERT INTO cosechas (cultivo_id, fecha, num_plantas, peso_humedo_g, peso_seco_g, calidad, notas, registrado_por)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (cid, fecha, n_plant, peso_h, peso_s, calidad, notas, prof))
    # avanza etapa a cosecha si no estaba
    c = db.execute('SELECT etapa_actual FROM cultivos WHERE id=?', (cid,)).fetchone()
    if c and c['etapa_actual'] not in ('cosecha','curado','finalizado'):
        db.execute("UPDATE cultivos SET etapa_actual='cosecha', fecha_etapa=? WHERE id=?",
                   (date.today().isoformat(), cid))
        db.execute('''INSERT INTO etapas_cultivo (cultivo_id, etapa_anterior, etapa_nueva, notas, registrado_por)
                      VALUES (?,?,'cosecha','Cosecha registrada',?)''',
                   (cid, c['etapa_actual'], prof))
    db.commit()
    return redirect(url_for('admin_cultivo', cid=cid))

@app.route('/admin/cultivo/<int:cid>/estado', methods=['POST'])
@login_required
def admin_cultivo_estado(cid):
    estado = request.form.get('estado','activo')
    get_db().execute('UPDATE cultivos SET estado=? WHERE id=?', (estado, cid))
    get_db().commit()
    return redirect(url_for('admin_cultivo', cid=cid))

# ═══════════════════════════════════════════════════════════════════════════
#  STOCK E INVENTARIO
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/stock')
@login_required
def admin_stock():
    db = get_db()
    cosechado_rows = db.execute('''
        SELECT cu.variedad, COALESCE(SUM(co.peso_seco_g),0) as total_g
        FROM cosechas co JOIN cultivos cu ON cu.id = co.cultivo_id
        GROUP BY cu.variedad ORDER BY total_g DESC
    ''').fetchall()

    stock = []
    for row in cosechado_rows:
        v = row['variedad']
        total = row['total_g'] or 0
        entregado = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE variedad=? AND estado='entregado'", (v,)
        ).fetchone()[0]
        reservado = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE variedad=? AND estado IN ('pendiente','preparando','en_camino')", (v,)
        ).fetchone()[0]
        disponible = total - entregado - reservado
        stock.append({
            'variedad': v,
            'total_g': round(total, 1),
            'entregado_g': round(entregado, 1),
            'reservado_g': round(reservado, 1),
            'disponible_g': round(disponible, 1),
            'pct_usado': round(((entregado + reservado) / total * 100) if total else 0),
        })

    total_disponible = round(sum(r['disponible_g'] for r in stock), 1)
    total_cosechado  = round(sum(r['total_g'] for r in stock), 1)
    total_entregado  = round(sum(r['entregado_g'] for r in stock), 1)

    recientes = db.execute('''
        SELECT p.*, s.nombre, s.apellido
        FROM pedidos p JOIN socios s ON s.id = p.socio_id
        WHERE p.estado='entregado' ORDER BY p.fecha_entrega DESC LIMIT 15
    ''').fetchall()

    movimientos = db.execute('''
        SELECT 'entrada' as tipo, co.fecha, cu.variedad, co.peso_seco_g as gramos,
               cu.codigo as referencia, co.registrado_por, NULL as socio_nombre
        FROM cosechas co JOIN cultivos cu ON cu.id = co.cultivo_id
        UNION ALL
        SELECT 'salida' as tipo, p.fecha_entrega as fecha, p.variedad, p.gramos,
               p.codigo as referencia, p.registrado_por,
               s.nombre || ' ' || s.apellido as socio_nombre
        FROM pedidos p JOIN socios s ON s.id = p.socio_id
        WHERE p.estado = 'entregado' AND p.fecha_entrega IS NOT NULL
        ORDER BY fecha DESC
        LIMIT 40
    ''').fetchall()

    total_reservado = round(sum(r['reservado_g'] for r in stock), 1)

    return render_template('admin/stock.html',
        stock=stock,
        total_disponible=total_disponible,
        total_cosechado=total_cosechado,
        total_entregado=total_entregado,
        total_reservado=total_reservado,
        recientes=recientes,
        movimientos=movimientos,
    )

# ═══════════════════════════════════════════════════════════════════════════
#  PEDIDOS — CICLO COMPLETO DE DISTRIBUCIÓN
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/pedidos')
@login_required
def admin_pedidos():
    db = get_db()
    estado_f   = request.args.get('estado','')
    q          = request.args.get('q','').strip()
    variedad_f = request.args.get('variedad','')

    sql = '''SELECT p.*, s.nombre, s.apellido, s.dni, s.telefono, s.barrio
             FROM pedidos p JOIN socios s ON s.id = p.socio_id WHERE 1=1'''
    params = []
    if estado_f:
        sql += ' AND p.estado=?'; params.append(estado_f)
    if variedad_f:
        sql += ' AND p.variedad=?'; params.append(variedad_f)
    if q:
        sql += ' AND (s.nombre LIKE ? OR s.apellido LIKE ? OR p.codigo LIKE ? OR p.variedad LIKE ?)'
        params += [f'%{q}%']*4
    sql += ' ORDER BY p.fecha_pedido DESC'
    pedidos = db.execute(sql, params).fetchall()

    # Contadores por estado
    contadores = {e: db.execute("SELECT COUNT(*) FROM pedidos WHERE estado=?", (e,)).fetchone()[0] for e in ESTADOS_PEDIDO}
    mes_inicio = date.today().replace(day=1).isoformat()
    ingresos_mes = db.execute(
        "SELECT COALESCE(SUM(precio),0) FROM pedidos WHERE estado='entregado' AND fecha_entrega >= ?", (mes_inicio,)
    ).fetchone()[0]
    variedades = db.execute('SELECT DISTINCT variedad FROM pedidos ORDER BY variedad').fetchall()

    return render_template('admin/pedidos.html',
        pedidos=pedidos, contadores=contadores,
        estado_f=estado_f, q=q, variedad_f=variedad_f,
        variedades=variedades,
        ingresos_mes=round(ingresos_mes, 2),
        estados_pedido=ESTADOS_PEDIDO,
        estado_pedido_next=ESTADO_PEDIDO_NEXT,
    )

@app.route('/admin/pedido/<int:pid>')
@login_required
def admin_pedido(pid):
    db = get_db()
    p = db.execute('''
        SELECT p.*, s.nombre, s.apellido, s.dni, s.telefono, s.barrio,
               s.direccion, s.referencias_entrega, s.cupo_mensual_g
        FROM pedidos p JOIN socios s ON s.id = p.socio_id WHERE p.id=?
    ''', (pid,)).fetchone()
    if not p: return redirect(url_for('admin_pedidos'))
    delivery_url = url_for('delivery_view', token=p['token_entrega'], _external=True) if p['token_entrega'] else None
    return render_template('admin/pedido.html',
        p=p, delivery_url=delivery_url,
        estados_pedido=ESTADOS_PEDIDO,
        estado_pedido_next=ESTADO_PEDIDO_NEXT,
        forma_pago_label=FORMA_PAGO_LABEL,
        tipo_entrega_label=TIPO_ENTREGA_LABEL,
    )

@app.route('/admin/socio/<int:sid>/pedido/nuevo', methods=['POST'])
@login_required
def admin_nuevo_pedido(sid):
    db  = get_db()
    f   = request.form
    variedad = f.get('variedad','').strip()
    gramos   = float(f.get('gramos', 0) or 0)

    if not variedad or gramos <= 0:
        flash('Especificá variedad y cantidad válida.')
        return redirect(url_for('admin_socio', sid=sid))

    s = db.execute('SELECT * FROM socios WHERE id=?', (sid,)).fetchone()
    cupo = (s['cupo_mensual_g'] or 30) if s else 30
    mes_inicio = date.today().replace(day=1).isoformat()
    consumido = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND fecha_pedido >= ? AND estado NOT IN ('cancelado')",
        (sid, mes_inicio)
    ).fetchone()[0]
    if consumido + gramos > cupo:
        flash(f'Supera el cupo mensual ({cupo}g). Ya tiene {round(consumido,1)}g pedidos este mes.')
        return redirect(url_for('admin_socio', sid=sid))

    disponible = db.execute('''
        SELECT COALESCE(SUM(co.peso_seco_g),0)
               - COALESCE((SELECT SUM(gramos) FROM pedidos WHERE variedad=? AND estado IN ('entregado','pendiente','preparando','en_camino')),0) as disp
        FROM cosechas co JOIN cultivos cu ON cu.id=co.cultivo_id WHERE cu.variedad=?
    ''', (variedad, variedad)).fetchone()[0]
    if gramos > (disponible or 0):
        flash(f'Sin stock suficiente. Disponible: {round(disponible or 0, 1)}g de {variedad}.')
        return redirect(url_for('admin_socio', sid=sid))

    codigo         = _next_codigo_pedido(db)
    token_entrega  = secrets.token_urlsafe(16)
    precio         = float(f.get('precio', 0) or 0)
    forma_pago     = f.get('forma_pago', 'efectivo')
    tipo_entrega   = f.get('tipo_entrega', 'delivery')
    direccion      = f.get('direccion_entrega', '').strip() or (s['direccion'] if s else '')
    delivery_pers  = f.get('delivery_persona','').strip()
    notas          = f.get('notas','').strip()
    prof           = f.get('registrado_por','Admin').strip() or 'Admin'

    # Guardar dirección en perfil del socio si se cambió
    if direccion and s and direccion != s['direccion']:
        db.execute('UPDATE socios SET direccion=? WHERE id=?', (direccion, sid))

    db.execute('''
        INSERT INTO pedidos (codigo, socio_id, variedad, gramos, precio, forma_pago,
            tipo_entrega, direccion_entrega, delivery_persona, token_entrega, notas, registrado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (codigo, sid, variedad, gramos, precio, forma_pago,
          tipo_entrega, direccion, delivery_pers, token_entrega, notas, prof))
    db.commit()
    flash(f'Pedido {codigo} creado — {gramos}g de {variedad}.')
    return redirect(url_for('admin_pedido', pid=db.execute('SELECT last_insert_rowid()').fetchone()[0]))

@app.route('/admin/pedido/<int:pid>/estado', methods=['POST'])
@login_required
def admin_pedido_estado(pid):
    db     = get_db()
    nuevo  = request.form.get('estado','')
    p      = db.execute('SELECT * FROM pedidos WHERE id=?', (pid,)).fetchone()
    if not p or nuevo not in ESTADOS_PEDIDO:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(ok=False), 400
        return redirect(url_for('admin_pedidos'))

    updates = 'estado=?'
    params  = [nuevo]
    if nuevo == 'entregado':
        updates += ', fecha_entrega=?'
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    params.append(pid)
    db.execute(f'UPDATE pedidos SET {updates} WHERE id=?', params)
    db.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(ok=True, estado=nuevo, label=ESTADO_PEDIDO_LABEL[nuevo], color=ESTADO_PEDIDO_COLOR[nuevo])
    flash(f'Pedido actualizado a: {ESTADO_PEDIDO_LABEL[nuevo]}')
    return redirect(url_for('admin_pedido', pid=pid))

@app.route('/admin/socio/<int:sid>/cupo', methods=['POST'])
@login_required
def admin_set_cupo(sid):
    cupo = float(request.form.get('cupo_mensual_g', 30) or 30)
    db = get_db()
    db.execute('UPDATE socios SET cupo_mensual_g=? WHERE id=?', (cupo, sid))
    # Update address/references too if provided
    if request.form.get('direccion'):
        db.execute('UPDATE socios SET direccion=?, referencias_entrega=? WHERE id=?',
                   (request.form.get('direccion','').strip(),
                    request.form.get('referencias_entrega','').strip(), sid))
    db.commit()
    flash(f'Cupo actualizado a {cupo}g/mes.')
    return redirect(url_for('admin_socio', sid=sid))

@app.route('/admin/distribuciones')
@login_required
def admin_distribuciones():
    return redirect(url_for('admin_pedidos'))

# ─── Confirmación de entrega (pública, sin login) ─────────────────────────

@app.route('/delivery/<token>')
def delivery_view(token):
    db = get_db()
    p = db.execute('''
        SELECT p.*, s.nombre, s.apellido, s.dni
        FROM pedidos p JOIN socios s ON s.id = p.socio_id
        WHERE p.token_entrega=?
    ''', (token,)).fetchone()
    if not p: return render_template('delivery.html', error=True)
    return render_template('delivery.html', p=p, error=False,
        estado_pedido_label=ESTADO_PEDIDO_LABEL,
        estado_pedido_color=ESTADO_PEDIDO_COLOR,
        tipo_entrega_label=TIPO_ENTREGA_LABEL)

@app.route('/delivery/<token>/confirmar', methods=['POST'])
def delivery_confirmar(token):
    db = get_db()
    p = db.execute('SELECT * FROM pedidos WHERE token_entrega=?', (token,)).fetchone()
    if not p or p['estado'] == 'entregado':
        return redirect(url_for('delivery_view', token=token))
    db.execute(
        "UPDATE pedidos SET estado='entregado', fecha_entrega=? WHERE token_entrega=?",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), token)
    )
    db.commit()
    return redirect(url_for('delivery_view', token=token))

# ═══════════════════════════════════════════════════════════════════════════

_register_globals()

if __name__ == '__main__':
    init_db()
    _migrate()
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=False, host='0.0.0.0', port=port)
