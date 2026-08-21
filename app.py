import os, sqlite3, csv, io, secrets, smtplib, json
from datetime import datetime, date, timedelta
from functools import wraps
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, make_response, g, Response, send_file)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = os.environ.get('CW_SECRET_KEY', 'cannawaka-dev-2026')

# ─── Rate limiting — protege contra bots, ataques de fuerza bruta y spam ────
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri='memory://',
    default_limits=[],
)

@app.errorhandler(429)
def demasiadas_solicitudes(e):
    if request.path.startswith('/api/') or request.path.startswith('/webhook/'):
        return jsonify({'ok': False, 'error': 'Demasiadas solicitudes. Intentá de nuevo en unos minutos.'}), 429
    return render_template('429.html'), 429

DB_PATH    = os.environ.get('CW_DB_PATH', 'cannawaka.db')
ADMIN_USER = os.environ.get('CW_ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('CW_ADMIN_PASS', 'germina2026')
MAIL_USER  = os.environ.get('MAIL_USER', 'besparkcreativa@gmail.com')
MAIL_PASS  = os.environ.get('MAIL_PASS', 'gihojbmsgweclmwu')
RENDER_URL = os.environ.get('RENDER_URL', 'https://germina-app.onrender.com')
CLUB_NOMBRE = os.environ.get('CW_CLUB_NOMBRE', 'Cannawaka')
CRM_USER      = os.environ.get('CRM_USER', 'germina')
CRM_PASS      = os.environ.get('CRM_PASS', 'spark2026')
GERMINA_PASS  = os.environ.get('GERMINA_PASS', 'germina-hq-2026')

PLANES = {
    'demo':       {'label': 'Demo',       'color': '#999',    'dias_max': 14},
    'basico':     {'label': 'Básico',     'color': '#B8860B', 'dias_max': None},
    'pro':        {'label': 'Pro',        'color': '#2D6A4F', 'dias_max': None},
    'enterprise': {'label': 'Enterprise', 'color': '#1A3520', 'dias_max': None},
}

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

@app.context_processor
def inject_demo_club():
    try:
        db = get_db()
        row = db.execute("SELECT value FROM config WHERE key='demo_club_nombre'").fetchone()
        return {
            'demo_club_nombre': row[0] if row else CLUB_NOMBRE,
            'current_role': current_role(),
            'current_username': current_username(),
        }
    except Exception:
        return {
            'demo_club_nombre': CLUB_NOMBRE,
            'current_role': 'admin',
            'current_username': 'Admin',
        }

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

# ─── Germina Autopilot — agentes, acciones y niveles ─────────────────────────

AGENTS = {
    'socios':         'Agente Socios',
    'administracion': 'Agente Administración',
    'patrones':       'Agente Patrones de Consumo',
    'reprocann':      'Agente REPROCANN',
    'whatsapp':       'Agente WhatsApp',
}
AGENT_ACTIONS = {
    'socios': [
        ('alta_socio',           'Alta de nuevo socio'),
        ('aviso_vencimiento',    'Aviso vencimiento de documento'),
        ('recordatorio_cuota',   'Recordatorio de cuota mensual'),
        ('seguimiento_inactivo', 'Seguimiento de socio inactivo'),
        ('renovacion',           'Gestión de renovación'),
        ('vencimiento_reprocann','Alerta vencimiento credencial REPROCANN'),
    ],
    'administracion': [
        ('alerta_stock',         'Alerta de stock bajo'),
        ('reporte_diario',       'Reporte diario automático'),
        ('prediccion_stock',     'Predicción de agotamiento de stock'),
        ('cuota_vencida',        'Seguimiento de cuota vencida'),
        ('pendientes_revision',  'Pendientes de revisión'),
    ],
    'patrones': [
        ('aumento_consumo',      'Aumento rápido de consumo detectado'),
        ('inactividad_prolongada','Inactividad prolongada de socio'),
        ('cese_abrupto',         'Cese abrupto de consumo'),
        ('recomendacion_variedad','Recomendación de variedad personalizada'),
    ],
    'reprocann': [
        ('informe_semestral',    'Informe semestral REPROCANN'),
    ],
    'whatsapp': [
        ('responder_consulta',   'Responder consultas de socios'),
        ('enviar_recordatorio',  'Enviar recordatorio por WhatsApp'),
        ('derivar_admin',        'Derivar al administrador'),
        ('solicitar_info',       'Solicitar información al socio'),
    ],
}
AUTOPILOT_LEVELS = {
    'RECOMENDAR': 'La IA detecta y sugiere. Vos decidís.',
    'PREPARAR':   'La IA prepara todo. Vos aprobás antes de que se ejecute.',
    'EJECUTAR':   'La IA ejecuta automáticamente sin pedirte permiso.',
}

# ─── DB init ───────────────────────────────────────────────────────────────

def _next_codigo(db):
    row = db.execute("SELECT MAX(CAST(SUBSTR(codigo,4) AS INTEGER)) FROM cultivos WHERE codigo LIKE 'CW-%'").fetchone()[0]
    return f"CW-{(row or 0)+1:04d}"

def _next_codigo_pedido(db):
    row = db.execute("SELECT MAX(CAST(SUBSTR(codigo,4) AS INTEGER)) FROM pedidos WHERE codigo LIKE 'PD-%'").fetchone()[0]
    return f"PD-{(row or 0)+1:04d}"

def _next_lote_codigo(db, fecha=None):
    """Genera número de lote internacional: LOT-AAAA-MM-XXXX"""
    if not fecha:
        fecha = date.today().isoformat()
    anio = fecha[:4]
    mes  = fecha[5:7]
    prefix = f"LOT-{anio}-{mes}-"
    row = db.execute(
        "SELECT MAX(CAST(SUBSTR(lote_codigo, ?) AS INTEGER)) FROM cosechas WHERE lote_codigo LIKE ?",
        (len(prefix) + 1, prefix + '%')
    ).fetchone()[0]
    return f"{prefix}{(row or 0)+1:04d}"

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
    CREATE TABLE IF NOT EXISTS variedades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        genetica TEXT DEFAULT 'hibrido',
        thc_pct REAL DEFAULT 0,
        cbd_pct REAL DEFAULT 0,
        descripcion TEXT,
        efectos TEXT,
        indicaciones TEXT,
        sabor TEXT,
        imagen_url TEXT,
        activa INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS cuotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        socio_id INTEGER NOT NULL,
        tipo TEXT DEFAULT 'mensual',
        monto REAL DEFAULT 0,
        fecha_pago TEXT,
        fecha_vencimiento TEXT,
        estado TEXT DEFAULT 'pagada',
        notas TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (socio_id) REFERENCES socios(id)
    );
    CREATE TABLE IF NOT EXISTS accesos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        socio_id INTEGER NOT NULL,
        tipo TEXT DEFAULT 'entrada',
        fecha TEXT DEFAULT (date('now')),
        hora TEXT DEFAULT (time('now','localtime')),
        registrado_por TEXT DEFAULT 'Admin',
        FOREIGN KEY (socio_id) REFERENCES socios(id)
    );
    CREATE TABLE IF NOT EXISTS variedad_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variedad_id INTEGER NOT NULL,
        socio_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comentario TEXT,
        fecha TEXT DEFAULT (date('now')),
        UNIQUE(variedad_id, socio_id),
        FOREIGN KEY (variedad_id) REFERENCES variedades(id),
        FOREIGN KEY (socio_id) REFERENCES socios(id)
    );
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    CREATE TABLE IF NOT EXISTS articulos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        titulo TEXT NOT NULL,
        resumen TEXT,
        contenido TEXT NOT NULL,
        keyword TEXT,
        meta_description TEXT,
        publicado INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS prospectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        email TEXT,
        whatsapp TEXT,
        club TEXT,
        pais TEXT,
        socios TEXT,
        mensaje TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    ''')
    db.commit()
    # Seed de artículos publicados (persisten aunque el contenedor se reinicie)
    _seed_articulos(db)
    db.close()

# Artículos publicados como seed — se insertan en cada deploy si no existen
_ARTICULOS_SEED = [
    {
        "slug": "como-legalizar-un-club-cannabico-en-argentina-la-guia-que-nadie-te-da",
        "titulo": "Cómo legalizar un club cannábico en Argentina: la guía que nadie te da",
        "resumen": "Marco legal, pasos concretos y errores que evitar para legalizar tu cannabis social club en Argentina.",
        "keyword": "cómo legalizar un club cannábico en Argentina",
        "meta_description": "Guía completa para legalizar un cannabis social club en Argentina: estatuto, IGJ, REPROCANN y cómo gestionar el cumplimiento desde el día 1.",
        "contenido": '<img class="art-img-hero" src="https://images.pexels.com/photos/7667721/pexels-photo-7667721.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1" alt="Técnico con guantes inspeccionando planta de cannabis medicinal" loading="lazy"><div class="art-hook"><p>Más de 200 cannabis social clubs operan hoy en Argentina. La mayoría comparte un secreto incómodo: están en una zona legal gris que expone personalmente a sus directivos cada vez que abren las puertas. No por falta de voluntad, sino por falta de información concreta sobre cómo dar el paso que los protege.</p></div><div class="art-stat"><span class="stat-num">8 de cada 10</span><span class="stat-label">clubs cannábicos en Argentina operan sin personería jurídica — y sus fundadores responden con su patrimonio personal ante cualquier reclamo.</span></div><p>En este artículo vas a encontrar exactamente lo que necesitás: el marco legal real, los pasos en orden y los errores que cometen los clubs que intentan hacerlo solos.</p><h2>¿Qué dice la ley argentina sobre los cannabis social clubs?</h2><p>Argentina no tiene una ley específica que regule los cannabis social clubs como figura jurídica. Lo que sí existe es un marco que los sostiene indirectamente: la <strong>Ley 27.350 de Uso Medicinal del Cannabis</strong> y su decreto reglamentario 883/2020, que reconocen el autocultivo y el cultivo solidario para fines medicinales.</p><p>Esto significa que los clubs no están en un vacío legal, pero tampoco tienen un paraguas explícito. La estrategia más sólida que encontró el sector es operar como <strong>asociación civil sin fines de lucro</strong>, amparada en los artículos 168 a 186 del Código Civil y Comercial de la Nación. Es el camino que usan los clubs más consolidados y el que recomiendan los abogados especializados.</p><div class="art-callout art-tip"><strong>Lo que no te dicen</strong>Algunas provincias como CABA, Córdoba y Santa Fe tienen criterios más flexibles al otorgar personería a asociaciones con objetos relacionados al cannabis medicinal. Empezar en una jurisdicción favorable puede reducir los tiempos a la mitad.</div><h2>Los 5 pasos reales para legalizar tu club</h2><h3>1. Redactar el estatuto social</h3><p>El estatuto es el documento fundacional. Debe incluir: nombre de la entidad, objeto social, domicilio legal, composición de la comisión directiva, condiciones de ingreso y egreso de socios, y régimen de cuotas. Un error en el objeto social puede hacer que la IGJ rechace la solicitud. Invertir en un abogado especializado en este paso vale cada peso.</p><h3>2. Asamblea constitutiva ante escribano</h3><p>Se necesitan mínimo tres socios fundadores. En la asamblea se aprueba el estatuto, se designa la primera comisión directiva y se labra el acta con firmas certificadas ante escribano público.</p><h3>3. Tramitar personería en la IGJ o equivalente provincial</h3><p>Con el estatuto y el acta, se presenta la solicitud ante la <strong>Inspección General de Justicia (IGJ)</strong> en CABA, o ante el organismo provincial correspondiente. El trámite incluye una tasa administrativa y un período de revisión de entre 30 y 90 días hábiles.</p><h3>4. CUIT de la asociación ante AFIP</h3><p>Una vez aprobada la personería, la asociación tramita su CUIT propio. Sin este número es imposible abrir una cuenta bancaria institucional, emitir recibos o firmar contratos como entidad.</p><h3>5. Inscripción en REPROCANN</h3><p>El Registro del Programa de Cannabis del Ministerio de Salud permite inscribir a los socios como cultivadores medicinales. Que el club pueda acreditar que sus socios están en el registro fortalece el marco de legitimidad ante cualquier control.</p><div class="art-callout art-warning"><strong>Error frecuente</strong>Varios clubs redactan el estatuto con un objeto social demasiado amplio o ambiguo respecto al cannabis, pensando que así evitan problemas. El resultado es el opuesto: la IGJ lo observa o rechaza, y el trámite se demora meses. El objeto debe ser específico, claro y coherente con la normativa de autocultivo medicinal.</div><blockquote class="art-quote">La personería jurídica no es un trámite burocrático. Es lo único que separa a los fundadores de un club de responder con su patrimonio personal si algo sale mal.</blockquote><h2>¿Qué pasa después de obtener la personería?</h2><img class="art-img-inline" src="https://images.pexels.com/photos/9259933/pexels-photo-9259933.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1" alt="Cannabis medicinal en tubo de laboratorio sobre balanza de precisión" loading="lazy"><p class="art-img-caption">El cumplimiento documental es tan importante como la constitución legal del club.</p><p>Legalizar el club es el primer paso, no el último. Una vez constituido, el cumplimiento operativo es continuo: mantener el padrón de socios actualizado, documentar cada dispensación, llevar los libros contables al día, hacer las asambleas anuales y presentar la memoria y balance ante el organismo de contralor.</p><p>Muchos clubs empiezan con cuadernos y planillas de Excel. A medida que suman socios y volumen, ese sistema colapsa: datos perdidos, registros inconsistentes, información inaccesible cuando más se necesita.</p><div class="art-cta-mid"><div><strong>¿Tu club ya tiene sistema de gestión digital?</strong><p>Germina centraliza el padrón de socios, las dispensaciones, el stock y los registros de cultivo. Todo con trazabilidad completa y accesible desde cualquier dispositivo.</p></div><a href="https://germina-clubs.netlify.app#contacto">Ver demo gratuita →</a></div><h2>La gestión digital como parte del cumplimiento</h2><p>Los organismos de contralor no evalúan solo si tenés personería: evalúan si podés demostrar cómo operás. Un club con registros ordenados, trazabilidad de dispensaciones y padrón actualizado tiene una posición infinitamente mejor ante cualquier requerimiento que uno que opera con Excel y buena voluntad.</p><p><strong>Germina</strong> es la plataforma diseñada para este escenario: gestión del padrón de socios con historial completo, registro de dispensaciones con fecha y cantidad, control de stock por variedad y portal personalizado para cada socio. Lo que antes requería horas de administración manual, Germina lo automatiza desde el primer día.</p><p>La legalización es el inicio del camino. Lo que viene después —el cumplimiento sostenido, la gestión ordenada, la capacidad de escalar sin caos— es lo que diferencia a los clubs que duran de los que no.</p><p><strong>Probá Germina gratis en germina-clubs.netlify.app — primer mes sin costo, sin tarjeta.</strong></p>',
    },
]

def _seed_articulos(db):
    for art in _ARTICULOS_SEED:
        db.execute(
            'INSERT OR IGNORE INTO articulos (slug,titulo,resumen,contenido,keyword,meta_description) VALUES (?,?,?,?,?,?)',
            (art['slug'], art['titulo'], art.get('resumen',''), art['contenido'],
             art.get('keyword',''), art.get('meta_description',''))
        )
    db.commit()

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
        'motivo_consumo': 'TEXT',
        'dosis_habitual_g': 'REAL',
        'frecuencia_uso': 'TEXT',
    }.items():
        if col not in cols:
            db.execute(f'ALTER TABLE socios ADD COLUMN {col} {typedef}')
    # trazabilidad de semillas en cultivos
    cols_c = {r[1] for r in db.execute("PRAGMA table_info(cultivos)")}
    for col, typedef in {
        'banco_genetico':        'TEXT',
        'tipo_semilla':          'TEXT',
        'num_semillas_compradas':'INTEGER',
        'num_semillas_germinadas':'INTEGER',
        'precio_semilla':        'REAL',
        'proveedor_semilla':     'TEXT',
        'fecha_compra_semilla':  'TEXT',
        'factura_numero':        'TEXT',
        'lote_semilla':          'TEXT',
        'url_banco':             'TEXT',
    }.items():
        if col not in cols_c:
            db.execute(f'ALTER TABLE cultivos ADD COLUMN {col} {typedef}')
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
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'variedades' not in tables:
        db.execute('''CREATE TABLE variedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            genetica TEXT DEFAULT 'hibrido',
            thc_pct REAL DEFAULT 0, cbd_pct REAL DEFAULT 0,
            descripcion TEXT, efectos TEXT, indicaciones TEXT, sabor TEXT,
            imagen_url TEXT, activa INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
    else:
        vcols = {r[1] for r in db.execute("PRAGMA table_info(variedades)")}
        if 'imagen_url' not in vcols:
            db.execute('ALTER TABLE variedades ADD COLUMN imagen_url TEXT')
    if 'cuotas' not in tables:
        db.execute('''CREATE TABLE cuotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            socio_id INTEGER NOT NULL,
            tipo TEXT DEFAULT 'mensual',
            monto REAL DEFAULT 0,
            fecha_pago TEXT, fecha_vencimiento TEXT,
            estado TEXT DEFAULT 'pagada', notas TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')))''')
    if 'accesos' not in tables:
        db.execute('''CREATE TABLE accesos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            socio_id INTEGER NOT NULL,
            tipo TEXT DEFAULT 'entrada',
            fecha TEXT DEFAULT (date('now')),
            hora TEXT DEFAULT (time('now','localtime')),
            registrado_por TEXT DEFAULT 'Admin')''')
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'variedad_ratings' not in tables:
        db.execute('''CREATE TABLE variedad_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variedad_id INTEGER NOT NULL, socio_id INTEGER NOT NULL,
            rating INTEGER NOT NULL, comentario TEXT,
            sabores TEXT, efectos_sentidos TEXT,
            intensidad TEXT, lo_repetiria TEXT,
            fecha TEXT DEFAULT (date('now')),
            UNIQUE(variedad_id, socio_id))''')
    else:
        vr_cols = {r[1] for r in db.execute("PRAGMA table_info(variedad_ratings)")}
        for col, typedef in {
            'sabores': 'TEXT', 'efectos_sentidos': 'TEXT',
            'intensidad': 'TEXT', 'lo_repetiria': 'TEXT',
        }.items():
            if col not in vr_cols:
                try:
                    db.execute(f'ALTER TABLE variedad_ratings ADD COLUMN {col} {typedef}')
                except Exception:
                    pass
    # origen del pedido (portal vs admin)
    ped_cols = {r[1] for r in db.execute("PRAGMA table_info(pedidos)")}
    if 'origen' not in ped_cols:
        try:
            db.execute("ALTER TABLE pedidos ADD COLUMN origen TEXT DEFAULT 'admin'")
        except Exception:
            pass
    # datos de pago del club
    club_cols = {r[1] for r in db.execute("PRAGMA table_info(clubs)")}
    for col, typedef in {
        'cbu': 'TEXT', 'alias_bancario': 'TEXT', 'mp_link': 'TEXT',
    }.items():
        if col not in club_cols:
            try:
                db.execute(f'ALTER TABLE clubs ADD COLUMN {col} {typedef}')
            except Exception:
                pass
    # tabla de informes REPROCANN
    tables2 = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'reprocann_reports' not in tables2:
        db.execute('''CREATE TABLE reprocann_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER DEFAULT 1,
            semestre TEXT NOT NULL,
            fecha_desde TEXT NOT NULL,
            fecha_hasta TEXT NOT NULL,
            generado_at TEXT DEFAULT (datetime('now','localtime')),
            contenido TEXT,
            status TEXT DEFAULT 'borrador'
        )''')
    # ── Columnas REPROCANN en socios ────────────────────────────────────────
    cols_s = {r[1] for r in db.execute("PRAGMA table_info(socios)")}
    for col, typedef in {
        'reprocann_codigo':       'TEXT',
        'reprocann_estado':       "TEXT DEFAULT 'sin_registro'",
        'reprocann_inicio':       'TEXT',
        'reprocann_vencimiento':  'TEXT',
        'plantas_autorizadas':    'INTEGER DEFAULT 9',
    }.items():
        if col not in cols_s:
            try:
                db.execute(f'ALTER TABLE socios ADD COLUMN {col} {typedef}')
            except Exception:
                pass

    # ── Columnas cromatográficas en cosechas ─────────────────────────────────
    cols_co = {r[1] for r in db.execute("PRAGMA table_info(cosechas)")}
    for col, typedef in {
        'thc_real_pct': 'REAL',
        'cbd_real_pct': 'REAL',
        'lote_codigo':  'TEXT',
        'laboratorio':  'TEXT',
    }.items():
        if col not in cols_co:
            try:
                db.execute(f'ALTER TABLE cosechas ADD COLUMN {col} {typedef}')
            except Exception:
                pass

    # ── Columnas m² y GACP en cultivos ──────────────────────────────────────
    cols_cu = {r[1] for r in db.execute("PRAGMA table_info(cultivos)")}
    for col, typedef in {
        'm2_interior':              'REAL',
        'm2_exterior':              'REAL',
        'gacp_fuente_agua':         'TEXT',
        'gacp_insumos':             'TEXT',
        'gacp_responsable_tecnico': 'TEXT',
        'gacp_lat':                 'REAL',
        'gacp_lon':                 'REAL',
        'gacp_altitud_m':           'REAL',
        'gacp_humedad_pct':         'REAL',
        'gacp_temp_min_c':          'REAL',
        'gacp_temp_max_c':          'REAL',
        'gacp_observaciones':       'TEXT',
    }.items():
        if col not in cols_cu:
            try:
                db.execute(f'ALTER TABLE cultivos ADD COLUMN {col} {typedef}')
            except Exception:
                pass

    # ── Campos CoA extendidos en cosechas ────────────────────────────────────
    cols_coa = {r[1] for r in db.execute("PRAGMA table_info(cosechas)")}
    for col, typedef in {
        'thc_real_pct':          'REAL',
        'cbd_real_pct':          'REAL',
        'lote_codigo':           'TEXT',
        'laboratorio':           'TEXT',
        'fecha_analisis':        'TEXT',
        'num_informe_lab':       'TEXT',
        'terpenos_pct':          'REAL',
        'pesticidas_status':     "TEXT DEFAULT 'pendiente'",
        'metales_status':        "TEXT DEFAULT 'pendiente'",
        'microbiologia_status':  "TEXT DEFAULT 'pendiente'",
        'humedad_muestra_pct':   'REAL',
        'coa_status':            "TEXT DEFAULT 'pendiente'",
        'responsable_cosecha':   'TEXT',
        'condiciones_almacenamiento': 'TEXT',
    }.items():
        if col not in cols_coa:
            try:
                db.execute(f'ALTER TABLE cosechas ADD COLUMN {col} {typedef}')
            except Exception:
                pass

    # ── Trazabilidad lote → dispensación ─────────────────────────────────────
    cols_disp = {r[1] for r in db.execute("PRAGMA table_info(dispensaciones)")}
    for col, typedef in {
        'cosecha_id':  'INTEGER',
        'lote_codigo': 'TEXT',
    }.items():
        if col not in cols_disp:
            try:
                db.execute(f'ALTER TABLE dispensaciones ADD COLUMN {col} {typedef}')
            except Exception:
                pass

    # ── Tabla checklist documentos REPROCANN (A–I) ───────────────────────────
    tables3 = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'reprocann_docs' not in tables3:
        db.execute('''CREATE TABLE reprocann_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER DEFAULT 1,
            tipo_doc TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            fecha_presentacion TEXT,
            fecha_vencimiento TEXT,
            notas TEXT,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        # Seed con los 9 documentos obligatorios
        _docs_reprocann = [
            ('A', 'Registro de inscripción ante el organismo de control + objeto social'),
            ('B', 'Nómina de beneficiarios registrados en la institución'),
            ('C', 'Declaración Jurada por cada beneficiario'),
            ('D', 'Nómina de domicilios de cultivo declarados (máx. 3)'),
            ('E', 'Antecedentes penales de directivos (sin condenas por Ley 23.737)'),
            ('F', 'Informe Técnico de las actividades de la persona jurídica'),
            ('G', 'Informe Cromatográfico + genética de semillas (DDJJ)'),
            ('H', 'Designación Director Médico + informe trimestral de pacientes vinculados'),
            ('I', 'Designación Responsable Técnico + plan de cultivo (DDJJ)'),
        ]
        for tipo, desc in _docs_reprocann:
            db.execute(
                "INSERT INTO reprocann_docs (club_id, tipo_doc, descripcion) VALUES (1,?,?)",
                (tipo, desc)
            )

    # ── Tabla Cartas de Porte ────────────────────────────────────────────────
    if 'cartas_porte' not in tables3:
        db.execute('''CREATE TABLE cartas_porte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER DEFAULT 1,
            pedido_id INTEGER,
            numero TEXT NOT NULL,
            fecha_emision TEXT NOT NULL,
            tipo_material TEXT DEFAULT 'flores_secas',
            cantidad REAL NOT NULL,
            unidad TEXT DEFAULT 'g',
            socio_nombre TEXT,
            socio_dni TEXT,
            direccion_destino TEXT,
            transportista_nombre TEXT,
            transportista_dni TEXT,
            vehiculo_patente TEXT,
            ruta TEXT,
            fecha_traslado TEXT,
            hora_inicio TEXT,
            hora_fin_estimada TEXT,
            estado TEXT DEFAULT 'activa',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')

    # Seed variedades de muestra si el catálogo está vacío
    if db.execute('SELECT COUNT(*) FROM variedades').fetchone()[0] == 0:
        db.executemany(
            'INSERT OR IGNORE INTO variedades (nombre,genetica,thc_pct,cbd_pct,descripcion,efectos,indicaciones,sabor,imagen_url,activa) VALUES (?,?,?,?,?,?,?,?,?,?)',
            [
                ('OG Kush','Hibrida',22.0,0.3,
                 'Cepa clásica californiana con efectos profundamente relajantes. Ideal para dolor crónico e insomnio. Aroma terroso con notas de pino y limón.',
                 'Relajante, Eufórico, Sedante','Dolor crónico, Insomnio, Estrés','Tierra, Pino, Cítrico',
                 'https://images.unsplash.com/photo-1536063211352-0b94219f3212?auto=format&fit=crop&w=600&q=80',1),
                ('Blue Dream','Sativa',19.0,1.0,
                 'Híbrida sativa que equilibra relajación corporal con estimulación mental suave. Perfecta para uso diurno, ansiedad y fatiga. Sabor dulce a frutas del bosque.',
                 'Energizante, Creativo, Equilibrado','Ansiedad, Depresión, Fatiga','Frutas, Dulce, Vainilla',
                 'https://images.unsplash.com/photo-1603909223429-69bb7101f420?auto=format&fit=crop&w=600&q=80',1),
                ('Northern Lights','Indica',18.0,0.5,
                 'Una de las índicas más puras del mundo. Efecto profundamente corporal y sedante. Muy usada para insomnio severo, dolor muscular y espasmos.',
                 'Sedante, Relajante, Somnífera','Insomnio severo, Espasmos, Dolor muscular','Tierra, Dulce, Resina',
                 'https://images.unsplash.com/photo-1591035897819-f4bdf739f446?auto=format&fit=crop&w=600&q=80',1),
                ('Charlotte Web','CBD',0.3,17.0,
                 'Variedad alta en CBD sin efectos psicoactivos. Pionera en el tratamiento de epilepsia refractaria, inflamación y ansiedad. Ideal para pacientes sensibles al THC.',
                 'Sin psicoactividad, Antiinflamatorio, Ansiolítico','Epilepsia, Inflamación, Ansiedad','Floral, Suave, Herbal',
                 'https://images.unsplash.com/photo-1616587894289-86480e533129?auto=format&fit=crop&w=600&q=80',1),
                ('Jack Herer','Sativa',21.0,0.8,
                 'Sativa legendaria que aporta claridad mental, enfoque y bienestar general. Utilizada para TDAH, depresión y fatiga crónica. Aroma a pino con notas especiadas.',
                 'Enfocado, Claro, Eufórico','TDAH, Depresión, Fatiga crónica','Pino, Madera, Especias',
                 'https://images.unsplash.com/photo-1611226077260-6b8b5a4b1a5d?auto=format&fit=crop&w=600&q=80',1),
                ('Amnesia Haze','Sativa',24.0,0.2,
                 'Sativa de alto THC con efecto cerebral intenso y duradero. Indicada para depresión, fatiga y falta de apetito. Sabor cítrico con notas de limón y menta.',
                 'Cerebral, Eufórico, Estimulante','Depresión, Falta de apetito, Fatiga','Limón, Menta, Cítrico',
                 'https://images.unsplash.com/photo-1569987516701-4e74f4ac0e15?auto=format&fit=crop&w=600&q=80',1),
            ]
        )
    # ── tablas Germina AI (se agregan si no existen — no tocan las existentes) ──
    db.executescript('''
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT (datetime('now','localtime')),
        club_id INTEGER DEFAULT 1,
        agent_id TEXT,
        action TEXT NOT NULL,
        actor TEXT DEFAULT 'Admin',
        entity_type TEXT,
        entity_id INTEGER,
        input_data TEXT,
        result TEXT,
        error TEXT,
        cost_usd REAL DEFAULT 0,
        tokens_in INTEGER DEFAULT 0,
        tokens_out INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT (datetime('now','localtime')),
        club_id INTEGER DEFAULT 1,
        event_type TEXT NOT NULL,
        entity_type TEXT,
        entity_id INTEGER,
        payload TEXT,
        status TEXT DEFAULT 'pending',
        processed_at TEXT,
        agent_id TEXT
    );
    CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id TEXT UNIQUE NOT NULL,
        jurisdiction TEXT NOT NULL DEFAULT 'AR',
        country TEXT NOT NULL DEFAULT 'Argentina',
        version INTEGER DEFAULT 1,
        effective_from TEXT,
        effective_until TEXT,
        source TEXT,
        description TEXT NOT NULL,
        condition_field TEXT,
        condition_operator TEXT,
        condition_value TEXT,
        action TEXT,
        severity TEXT DEFAULT 'WARNING',
        status TEXT DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS autopilot_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        club_id INTEGER DEFAULT 1,
        agent_id TEXT NOT NULL,
        action_id TEXT NOT NULL,
        level TEXT DEFAULT 'RECOMENDAR',
        UNIQUE(club_id, agent_id, action_id)
    );
    CREATE TABLE IF NOT EXISTS task_type_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type TEXT UNIQUE NOT NULL,
        human_minutes INTEGER DEFAULT 5,
        description TEXT
    );
    CREATE TABLE IF NOT EXISTS roi_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT (datetime('now','localtime')),
        club_id INTEGER DEFAULT 1,
        agent_id TEXT,
        task_type TEXT,
        audit_log_id INTEGER,
        human_minutes_saved REAL DEFAULT 0,
        automation_cost_usd REAL DEFAULT 0,
        net_value_usd REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS agent_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT (datetime('now','localtime')),
        club_id INTEGER DEFAULT 1,
        agent_id TEXT NOT NULL,
        task_type TEXT NOT NULL,
        entity_type TEXT,
        entity_id INTEGER,
        level TEXT DEFAULT 'RECOMENDAR',
        status TEXT DEFAULT 'pendiente',
        input_data TEXT,
        recommendation TEXT,
        approval_status TEXT,
        approved_by TEXT,
        approved_at TEXT,
        execution_result TEXT,
        error TEXT,
        cost_usd REAL DEFAULT 0,
        tokens_in INTEGER DEFAULT 0,
        tokens_out INTEGER DEFAULT 0,
        audit_log_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        pais TEXT DEFAULT 'AR',
        jurisdiction TEXT DEFAULT 'AR',
        email TEXT,
        whatsapp TEXT,
        admin_user TEXT,
        admin_pass TEXT,
        plan TEXT DEFAULT 'demo',
        activo INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS whatsapp_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        club_id INTEGER DEFAULT 1,
        phone_number_id TEXT,
        business_account_id TEXT,
        access_token TEXT,
        webhook_verify_token TEXT,
        activo INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS whatsapp_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        club_id INTEGER DEFAULT 1,
        socio_id INTEGER,
        direction TEXT DEFAULT 'out',
        from_number TEXT,
        to_number TEXT,
        message TEXT NOT NULL,
        status TEXT DEFAULT 'sent',
        wa_message_id TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    ''')

    # Reglas motor AR — esqueleto regulatorio (no inventamos normativa)
    _rules_ar = [
        ('AR-001', 'AR', 'Argentina', 1, 'Ley 27.350',
         'El socio debe tener diagnóstico médico para recibir cannabis medicinal',
         'tiene_diagnostico', 'eq', 'no', 'BLOCK', 'WARNING'),
        ('AR-002', 'AR', 'Argentina', 1, 'Ley 27.350 / Decreto 883/2020',
         'El autocultivo medicinal requiere inscripción activa en REPROCANN',
         'reprocann_activo', 'eq', 'no', 'WARN', 'WARNING'),
        ('AR-003', 'AR', 'Argentina', 1, 'Operativo interno',
         'La dispensación mensual no debe superar el cupo aprobado por el médico',
         'gramos_mes', 'gt', '40', 'WARN', 'WARNING'),
        ('AR-004', 'AR', 'Argentina', 1, 'Ley 27.350',
         'Todo movimiento de cannabis debe quedar registrado con trazabilidad completa',
         'trazabilidad', 'eq', 'no', 'BLOCK', 'WARNING'),
        ('UY-001', 'UY', 'Uruguay', 1, 'Ley 19.172',
         'El club cannábico no puede superar 45 socios',
         'total_socios', 'gt', '45', 'BLOCK', 'WARNING'),
        ('UY-002', 'UY', 'Uruguay', 1, 'Ley 19.172',
         'Cada socio no puede recibir más de 480g anuales (40g/mes)',
         'gramos_año', 'gt', '480', 'BLOCK', 'WARNING'),
    ]
    for r in _rules_ar:
        db.execute('''
            INSERT OR IGNORE INTO rules
            (rule_id,jurisdiction,country,version,source,description,
             condition_field,condition_operator,condition_value,action,severity)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', r)

    # Tiempos de trabajo humano equivalente por tipo de tarea
    _task_types = [
        ('alta_socio',           15, 'Procesar alta de nuevo socio (formulario + revisión de docs)'),
        ('aviso_vencimiento',     3, 'Revisar y enviar aviso de vencimiento de documento'),
        ('recordatorio_cuota',    2, 'Generar y enviar recordatorio de cuota mensual'),
        ('seguimiento_inactivo',  5, 'Revisar socio inactivo y decidir acción'),
        ('alerta_stock',          4, 'Revisar stock y tomar decisión sobre reabastecimiento'),
        ('reporte_diario',       10, 'Generar reporte diario del club'),
        ('cuota_vencida',         5, 'Revisar y gestionar cuota vencida'),
        ('responder_consulta',    3, 'Responder consulta de socio por WhatsApp o email'),
        ('enviar_recordatorio',   2, 'Preparar y enviar recordatorio personalizado'),
        ('dispensacion',          2, 'Registrar dispensación de cannabis medicinal'),
        ('cambio_etapa_cultivo',  3, 'Registrar cambio de etapa de cultivo'),
        ('nuevo_pedido',          4, 'Procesar nuevo pedido de socio'),
        ('cambio_etapa_socio',    3, 'Revisar y cambiar etapa de un socio'),
        ('registro_cosecha',      5, 'Registrar datos de cosecha en el sistema'),
    ]
    for tt in _task_types:
        db.execute('''
            INSERT OR IGNORE INTO task_type_config (task_type, human_minutes, description)
            VALUES (?,?,?)
        ''', tt)

    # Autopilot defaults — todos en RECOMENDAR (la autonomía se gana gradualmente)
    _autopilot_defaults = []
    for agent_id, actions in AGENT_ACTIONS.items():
        for action_id, _ in actions:
            _autopilot_defaults.append((1, agent_id, action_id, 'RECOMENDAR'))
    for ap in _autopilot_defaults:
        db.execute('''
            INSERT OR IGNORE INTO autopilot_config (club_id, agent_id, action_id, level)
            VALUES (?,?,?,?)
        ''', ap)

    # ── Tabla de usuarios con roles ──────────────────────────────────────────
    db.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER DEFAULT 1,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'operador',
            nombre TEXT,
            activo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(club_id, username)
        )
    ''')
    # Seed del admin existente (no lo pisa si ya existe)
    import hashlib as _hl
    _admin_hash = _hl.sha256(ADMIN_PASS.encode('utf-8')).hexdigest()
    db.execute(
        "INSERT OR IGNORE INTO usuarios (club_id, username, password_hash, role, nombre) "
        "VALUES (1,?,?,'admin','Administrador')",
        (ADMIN_USER, _admin_hash)
    )

    # ── Tabla fallback humano ─────────────────────────────────────────────────
    db.execute('''
        CREATE TABLE IF NOT EXISTS escalaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER DEFAULT 1,
            agent_task_id INTEGER,
            motivo TEXT,
            contexto TEXT,
            estado TEXT DEFAULT 'abierta',
            asignado_a TEXT,
            resolucion TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            resolved_at TEXT
        )
    ''')

    # ── Columnas extra en clubs (no-destructivo) ─────────────────────────────
    for col_def in [
        "ALTER TABLE clubs ADD COLUMN plan_vence TEXT",
        "ALTER TABLE clubs ADD COLUMN notas_internas TEXT",
        "ALTER TABLE clubs ADD COLUMN contacto_nombre TEXT",
        "ALTER TABLE clubs ADD COLUMN ultimo_acceso TEXT",
    ]:
        try:
            db.execute(col_def)
        except Exception:
            pass

    # Seed club_id=1 si no existe
    db.execute("""
        INSERT OR IGNORE INTO clubs (id, nombre, pais, jurisdiction, email, plan, activo)
        VALUES (1, ?, 'AR', 'AR', ?, 'pro', 1)
    """, (CLUB_NOMBRE, MAIL_USER))

    # Actualizar imágenes de variedades seed con URLs verificadas
    imagenes_seed = {
        'OG Kush':        'https://www.royalqueenseeds.com/149-3131-large/og-kush.jpg',
        'Blue Dream':     'https://seedsmanlive.gumlet.io/media/catalog/product/cache/c3b74a149799263175fb901c5bb6f5cb/1/6/169138_2631644_pimcore_1.jpg',
        'Northern Lights':'https://www.royalqueenseeds.com/119-2029-large/northern-light.jpg',
        'Charlotte Web':  'https://seedsmanlive.gumlet.io/media/catalog/product/cache/c3b74a149799263175fb901c5bb6f5cb/1/4/149283_2197226_pimcore_1_1.jpg',
        'Jack Herer':     'https://seedsmanlive.gumlet.io/media/catalog/product/cache/a74837f66b8aa9385d5c427840507caa/1/4/148437_2580929_pimcore_1_1.jpg',
        'Amnesia Haze':   'https://www.royalqueenseeds.com/115-2125-large/amnesia-haze.jpg',
    }
    for nombre, url in imagenes_seed.items():
        db.execute('UPDATE variedades SET imagen_url=? WHERE nombre=?', (url, nombre))
    db.commit()
    db.close()

# ─── auth y roles ─────────────────────────────────────────────────────────

import hashlib as _hashlib

def _hash_pw(p):
    return _hashlib.sha256(p.encode('utf-8')).hexdigest()

def current_role():
    return session.get('user_role', 'admin')

def current_username():
    return session.get('user_nombre', ADMIN_USER)

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapped

def role_required(*roles):
    """Decorator para rutas que solo pueden usar ciertos roles."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not session.get('admin'):
                return redirect(url_for('admin_login'))
            if roles and current_role() not in roles:
                return render_template('403.html', roles_requeridos=list(roles)), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

def write_required(f):
    """Bloquea solicitudes POST/PUT/DELETE para usuarios de solo lectura."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        if request.method in ('POST', 'PUT', 'DELETE') and current_role() == 'readonly':
            return render_template('403.html', roles_requeridos=['admin', 'operador']), 403
        return f(*args, **kwargs)
    return wrapped

# ─── Protección anti inyección de prompts ──────────────────────────────────

_INJECTION_PATTERNS = [
    'ignore previous', 'ignore all', 'forget instructions', 'system prompt',
    'new instructions', 'override', 'jailbreak', 'disregard', 'act as',
    'you are now', 'pretend you', 'roleplay', 'reveal', 'print your',
    'show your instructions', 'what are your', 'ignore the above',
]

def _sanitizar_input(texto, max_len=200):
    """Limpia texto de usuario antes de incluirlo en un prompt de IA."""
    if not texto:
        return ''
    texto = str(texto)[:max_len]
    lower = texto.lower()
    for patron in _INJECTION_PATTERNS:
        if patron in lower:
            return '[contenido filtrado]'
    return texto.strip()

# ═══════════════════════════════════════════════════════════════════════════
#  CARA PÚBLICA
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/manual')
def manual_usuario():
    from flask import send_from_directory
    return send_from_directory('.', 'manual-usuario.html')

@app.route('/unirme', methods=['GET','POST'])
@limiter.limit('5 per hour', methods=['POST'])
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
             motivo_consumo, dosis_habitual_g,
             como_nos_conocio, referido_por, canal_detalle, notas_solicitud)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            f.get('motivo_consumo',''),
            float(f.get('dosis_habitual_g',0) or 0),
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

@app.route('/club-demo')
def club_landing():
    nombre = request.args.get('nombre', 'Club Raíz')
    return render_template('club_landing.html', club_nombre=nombre)

def _enviar_propuesta(club_nombre, contacto_nombre, email_dest):
    """Genera PDFs y los envía por email. Retorna True si ok, False si falla."""
    if not MAIL_USER or not MAIL_PASS:
        return False
    try:
        from pdf_germina import generar_propuesta, generar_manual
        pdf_prop  = generar_propuesta(club_nombre, contacto_nombre)
        pdf_man   = generar_manual()

        msg = MIMEMultipart('mixed')
        msg['Subject'] = f'Germina — Propuesta comercial para {club_nombre}'
        msg['From']    = f'Germina <{MAIL_USER}>'
        msg['To']      = email_dest

        cuerpo = f"""<html><body style="font-family:Arial,sans-serif;color:#1E1E1E;max-width:580px;margin:0 auto;">
<div style="background:#1A3520;padding:28px 32px;border-radius:12px 12px 0 0;">
  <h1 style="font-family:Georgia,serif;color:#F5F2EC;font-size:28px;margin:0;">
    Germi<span style="color:#C8A44A;">na</span>
  </h1>
  <p style="color:rgba(255,255,255,0.6);font-size:12px;margin:4px 0 0;">Plataforma de Gestión para Cannabis Social Clubs</p>
</div>
<div style="background:#fff;padding:32px;border:1px solid #D8D3C8;border-top:none;border-radius:0 0 12px 12px;">
  <p style="font-size:16px;">Hola <strong>{contacto_nombre}</strong>,</p>
  <p>Gracias por tu interés en Germina. Adjunto a este mail encontrás:</p>
  <ul style="line-height:2;">
    <li>📄 <strong>Propuesta comercial</strong> para {club_nombre}</li>
    <li>📘 <strong>Manual de usuario</strong> completo del panel de administración</li>
  </ul>
  <p>También podés explorar la plataforma ahora mismo con estas credenciales de demostración:</p>
  <div style="background:#F5F2EC;border:1px solid #D8D3C8;border-radius:10px;padding:16px 20px;margin:20px 0;">
    <strong>Panel de administración:</strong><br>
    🔗 URL: <a href="{RENDER_URL}/admin" style="color:#2D5C38;">{RENDER_URL}/admin</a><br>
    👤 Usuario: <code style="background:#EDE8DF;padding:2px 6px;border-radius:4px;">admin</code><br>
    🔑 Contraseña: <code style="background:#EDE8DF;padding:2px 6px;border-radius:4px;">germina2026</code>
  </div>
  <p>Si tenés dudas o querés que hablemos, respondé este mail o escribinos directamente.</p>
  <p style="margin-top:28px;">Saludos,<br><strong>Equipo Germina / Spark Creativa</strong><br>
  <span style="color:#6B6560;font-size:13px;">besparkcreativa@gmail.com</span></p>
</div>
</body></html>"""

        msg.attach(MIMEText(cuerpo, 'html', 'utf-8'))

        att1 = MIMEApplication(pdf_prop.read(), _subtype='pdf')
        att1.add_header('Content-Disposition', 'attachment',
                        filename=f'Germina_Propuesta_{club_nombre.replace(" ","_")}.pdf')
        msg.attach(att1)

        att2 = MIMEApplication(pdf_man.read(), _subtype='pdf')
        att2.add_header('Content-Disposition', 'attachment',
                        filename='Germina_Manual_de_Usuario.pdf')
        msg.attach(att2)

        with smtplib.SMTP('smtp.gmail.com', 587) as srv:
            srv.starttls()
            srv.login(MAIL_USER, MAIL_PASS)
            srv.send_message(msg)
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] {e}')
        return False

def _lead_to_email(data):
    try:
        msg = MIMEMultipart()
        msg['From']    = MAIL_USER
        msg['To']      = MAIL_USER
        msg['Subject'] = (f"GLEAD|{data.get('club','')}|{data.get('nombre','')}|"
                          f"{data.get('email','')}|{data.get('whatsapp','')}|"
                          f"{data.get('pais','')}|{data.get('socios','')}")
        msg.attach(MIMEText(data.get('mensaje','') or '', 'plain'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MAIL_USER, MAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print(f'[LEAD EMAIL ERROR] {e}')

def _get_prospectos_imap():
    import imaplib, email as _elib, re
    prospectos = []
    try:
        M = imaplib.IMAP4_SSL('imap.gmail.com')
        M.login(MAIL_USER, MAIL_PASS)
        M.select('INBOX')
        # Nuevos (formato GLEAD)
        _, nums = M.search(None, 'SUBJECT "GLEAD|"')
        for n in reversed(nums[0].split()):
            _, raw = M.fetch(n, '(RFC822)')
            msg = _elib.message_from_bytes(raw[0][1])
            parts = (msg['subject'] or '').split('|')
            if len(parts) >= 7:
                prospectos.append({
                    'created_at': str(msg['date'])[:20],
                    'club': parts[1], 'nombre': parts[2], 'email': parts[3],
                    'whatsapp': parts[4], 'pais': parts[5], 'socios': parts[6],
                    'mensaje': msg.get_payload() or '',
                })
        # Existentes (formato formsubmit.co "Tu propuesta Germina")
        _, nums2 = M.search(None, 'SUBJECT "Tu propuesta Germina"')
        for n in reversed(nums2[0].split()):
            _, raw = M.fetch(n, '(RFC822)')
            msg = _elib.message_from_bytes(raw[0][1])
            subj = msg['subject'] or ''
            club = re.sub(r'.*Tu propuesta Germina.*?—\s*', '', subj).strip()
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8','ignore'); break
            else:
                body = msg.get_payload(decode=True).decode('utf-8','ignore') if msg.get_payload(decode=True) else ''
            def _extract(tag, text):
                m = re.search(rf'{tag}\s*[:\|]\s*([^\n\r<]+)', text, re.IGNORECASE)
                return m.group(1).strip() if m else ''
            prospectos.append({
                'created_at': str(msg['date'])[:20],
                'club': club,
                'nombre':   _extract('Nombre', body),
                'email':    _extract('email', body),
                'whatsapp': _extract('WhatsApp', body),
                'pais':     _extract('Pa.s', body),
                'socios':   _extract('Socios', body),
                'mensaje':  _extract('Mensaje', body),
            })
        M.logout()
    except Exception as e:
        print(f'[IMAP ERROR] {e}')
    return prospectos

@app.route('/api/lead', methods=['POST', 'OPTIONS'])
@limiter.limit('10 per hour', methods=['POST'])
def api_lead():
    if request.method == 'OPTIONS':
        r = make_response()
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return r
    data = request.get_json(silent=True) or {}
    _lead_to_email(data)
    r = jsonify({'ok': True})
    r.headers['Access-Control-Allow-Origin'] = '*'
    return r

@app.route('/api/set-demo-club', methods=['POST', 'OPTIONS'])
@limiter.limit('10 per hour', methods=['POST'])
def api_set_demo_club():
    if request.method == 'OPTIONS':
        r = make_response()
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return r
    data = request.get_json(silent=True) or {}
    club = (data.get('club') or '').strip()[:120]
    if club:
        db = get_db()
        db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('demo_club_nombre', ?)", (club,))
        db.commit()
    r = jsonify({'ok': True})
    r.headers['Access-Control-Allow-Origin'] = '*'
    return r

@app.route('/contacto-club', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'])
def contacto_club():
    enviado = False
    error = None
    form = {}
    email_enviado = ''
    if request.method == 'POST':
        form = request.form.to_dict()
        club_nombre     = form.get('club_nombre', '').strip()
        contacto_nombre = form.get('contacto_nombre', '').strip()
        email_dest      = form.get('email', '').strip()
        if not club_nombre or not contacto_nombre or not email_dest:
            error = 'Completá los campos obligatorios (nombre del club, tu nombre y email).'
        else:
            ok = _enviar_propuesta(club_nombre, contacto_nombre, email_dest)
            if ok:
                db = get_db()
                db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('demo_club_nombre', ?)", (club_nombre,))
                db.commit()
                return redirect(url_for('club_landing', nombre=club_nombre))
            else:
                if not MAIL_USER:
                    error = 'El sistema de envío de emails no está configurado aún. Escribinos directamente a besparkcreativa@gmail.com'
                else:
                    error = 'Hubo un error al enviar el mail. Intentá de nuevo o escribinos directamente.'
    return render_template('contacto_club.html', enviado=enviado, error=error,
                           form=form, email_enviado=email_enviado)

@app.route('/acceso-socio', methods=['GET', 'POST'])
@limiter.limit('20 per minute; 100 per hour', methods=['POST'])
def acceso_socio():
    error = None
    if request.method == 'POST':
        dni = (request.form.get('dni') or '').strip().replace('.', '').replace('-', '').replace(' ', '')
        if not dni:
            error = 'Ingresá tu DNI para continuar.'
        else:
            db = get_db()
            socio = db.execute(
                "SELECT token FROM socios WHERE REPLACE(REPLACE(REPLACE(dni,'.',''),'-',''),' ','') = ?",
                (dni,)).fetchone()
            if socio:
                return redirect(url_for('portal', token=socio['token']))
            else:
                error = 'No encontramos un socio con ese DNI. Verificá que esté bien escrito o contactanos.'
    return render_template('acceso_socio.html', error=error)

@app.route('/mi-estado/<token>')
def portal(token):
    db = get_db()
    s = db.execute('SELECT * FROM socios WHERE token=?', (token,)).fetchone()
    if not s: return redirect(url_for('landing'))
    docs  = db.execute('SELECT * FROM documentos WHERE socio_id=? ORDER BY fecha DESC', (s['id'],)).fetchall()
    cuota_actual = db.execute(
        'SELECT * FROM cuotas WHERE socio_id=? ORDER BY fecha_vencimiento DESC LIMIT 1', (s['id'],)
    ).fetchone()
    hoy = date.today().isoformat()
    mes_inicio = date.today().replace(day=1).isoformat()
    consumido_mes = (db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=? AND fecha>=?",
        (s['id'], mes_inicio)).fetchone()[0] or 0) + (db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND fecha_pedido>=? AND estado='entregado'",
        (s['id'], mes_inicio)).fetchone()[0] or 0)
    total_consumido = (db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=?", (s['id'],)).fetchone()[0] or 0) + (
        db.execute("SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND estado='entregado'",
        (s['id'],)).fetchone()[0] or 0)
    # Historial combinado
    disp_hist = db.execute(
        "SELECT fecha, variedad, gramos, 'dispensario' as tipo FROM dispensaciones WHERE socio_id=? ORDER BY fecha DESC, id DESC",
        (s['id'],)).fetchall()
    ped_hist = db.execute(
        "SELECT fecha_entrega as fecha, variedad, gramos, 'pedido' as tipo FROM pedidos WHERE socio_id=? AND estado='entregado' ORDER BY fecha_entrega DESC",
        (s['id'],)).fetchall()
    historial = sorted([dict(r) for r in list(disp_hist)+list(ped_hist)],
                       key=lambda x: x['fecha'] or '0000', reverse=True)
    # Variedades con ratings
    variedades_raw = db.execute('SELECT * FROM variedades WHERE activa=1 ORDER BY nombre').fetchall()
    variedades_set = {r['variedad'] for r in disp_hist}
    variedades_set |= {r['variedad'] for r in ped_hist}
    variedades = []
    for v in variedades_raw:
        avg_row = db.execute('SELECT AVG(rating), COUNT(*) FROM variedad_ratings WHERE variedad_id=?', (v['id'],)).fetchone()
        mi_r = db.execute('SELECT rating, comentario, sabores, efectos_sentidos, intensidad, lo_repetiria FROM variedad_ratings WHERE variedad_id=? AND socio_id=?',
                          (v['id'], s['id'])).fetchone()
        variedades.append({
            **dict(v),
            'avg_rating': round(avg_row[0] or 0, 1),
            'rating_count': avg_row[1] or 0,
            'mi_rating': mi_r['rating'] if mi_r else 0,
            'mi_comentario': mi_r['comentario'] if mi_r else '',
            'mi_sabores': mi_r['sabores'] if mi_r else '',
            'mi_efectos': mi_r['efectos_sentidos'] if mi_r else '',
            'mi_intensidad': mi_r['intensidad'] if mi_r else '',
            'mi_lo_repetiria': mi_r['lo_repetiria'] if mi_r else '',
            'puede_votar': v['nombre'] in variedades_set,
        })
    # Pedidos activos del socio
    pedidos_activos = db.execute(
        "SELECT * FROM pedidos WHERE socio_id=? AND estado IN ('pendiente','preparando') ORDER BY fecha_pedido DESC",
        (s['id'],)).fetchall()
    pedidos_activos = [dict(p) for p in pedidos_activos]
    # Perfil de paladar
    all_ratings = db.execute(
        'SELECT sabores, efectos_sentidos, intensidad, lo_repetiria, rating FROM variedad_ratings WHERE socio_id=?',
        (s['id'],)).fetchall()
    sabores_count, efectos_count, intensidad_count = {}, {}, {}
    rep_si = rep_total = 0
    for r in all_ratings:
        if r['sabores']:
            for t in r['sabores'].split(','):
                t = t.strip()
                if t: sabores_count[t] = sabores_count.get(t, 0) + 1
        if r['efectos_sentidos']:
            for t in r['efectos_sentidos'].split(','):
                t = t.strip()
                if t: efectos_count[t] = efectos_count.get(t, 0) + 1
        if r['intensidad']:
            intensidad_count[r['intensidad']] = intensidad_count.get(r['intensidad'], 0) + 1
        if r['lo_repetiria']:
            rep_total += 1
            if r['lo_repetiria'] == 'si': rep_si += 1
    top_sabores = sorted(sabores_count.items(), key=lambda x: -x[1])[:6]
    top_efectos = sorted(efectos_count.items(), key=lambda x: -x[1])[:6]
    paladar = {
        'top_sabores': top_sabores,
        'top_efectos': top_efectos,
        'intensidad': max(intensidad_count, key=intensidad_count.get) if intensidad_count else None,
        'pct_repetiria': round(rep_si / rep_total * 100) if rep_total > 0 else None,
        'total_catas': len(all_ratings),
    }
    # Recomendaciones simples por tags
    rated_ids = {r['variedad_id'] for r in db.execute(
        'SELECT variedad_id FROM variedad_ratings WHERE socio_id=?', (s['id'],)).fetchall()}
    top_sab_set = {t.lower() for t, _ in top_sabores[:3]}
    top_ef_set = {t.lower() for t, _ in top_efectos[:3]}
    recomendaciones = []
    for v in variedades_raw:
        if v['id'] in rated_ids: continue
        score = 0
        for tag in (v['sabor'] or '').split(','):
            if tag.strip().lower() in top_sab_set: score += 2
        for tag in (v['efectos'] or '').split(','):
            if tag.strip().lower() in top_ef_set: score += 1.5
        if score > 0:
            recomendaciones.append({'id': v['id'], 'nombre': v['nombre'], 'genetica': v['genetica'], 'score': score})
    recomendaciones.sort(key=lambda x: -x['score'])
    recomendaciones = recomendaciones[:3]
    try:
        club = db.execute('SELECT cbu, alias_bancario, mp_link FROM clubs WHERE id=1').fetchone()
        club_pago = {
            'cbu': club['cbu'] if club else None,
            'alias': club['alias_bancario'] if club else None,
            'mp_link': club['mp_link'] if club else None,
        }
    except Exception:
        club_pago = {'cbu': None, 'alias': None, 'mp_link': None}
    return render_template('portal.html',
        s=s, docs=docs, cuota_actual=cuota_actual, hoy=hoy,
        consumido_mes=round(consumido_mes,1),
        total_consumido=round(total_consumido,1),
        historial=historial, variedades=variedades,
        pedidos_activos=pedidos_activos,
        paladar=paladar, recomendaciones=recomendaciones,
        club_pago=club_pago,
        token=token,
        etapa_label=ETAPA_LABEL, etapa_color=ETAPA_COLOR)

@app.route('/mi-estado/<token>/rating/<int:vid>', methods=['POST'])
def portal_rating(token, vid):
    db = get_db()
    s = db.execute('SELECT * FROM socios WHERE token=?', (token,)).fetchone()
    if not s: return jsonify(ok=False), 403
    data = request.json if request.is_json else request.form
    rating = int(data.get('rating', 0))
    comentario = (data.get('comentario', '') or '').strip()[:400]
    sabores = (data.get('sabores', '') or '').strip()[:200]
    efectos_sentidos = (data.get('efectos_sentidos', '') or '').strip()[:200]
    intensidad = (data.get('intensidad', '') or '').strip()[:20]
    lo_repetiria = (data.get('lo_repetiria', '') or '').strip()[:20]
    if not 1 <= rating <= 5: return jsonify(ok=False, msg='Rating inválido'), 400
    existing = db.execute('SELECT id FROM variedad_ratings WHERE variedad_id=? AND socio_id=?', (vid, s['id'])).fetchone()
    today = date.today().isoformat()
    if existing:
        db.execute(
            'UPDATE variedad_ratings SET rating=?,comentario=?,sabores=?,efectos_sentidos=?,intensidad=?,lo_repetiria=?,fecha=? WHERE id=?',
            (rating, comentario, sabores or None, efectos_sentidos or None, intensidad or None, lo_repetiria or None, today, existing['id']))
    else:
        db.execute(
            'INSERT INTO variedad_ratings (variedad_id,socio_id,rating,comentario,sabores,efectos_sentidos,intensidad,lo_repetiria) VALUES (?,?,?,?,?,?,?,?)',
            (vid, s['id'], rating, comentario, sabores or None, efectos_sentidos or None, intensidad or None, lo_repetiria or None))
    db.commit()
    avg = db.execute('SELECT AVG(rating), COUNT(*) FROM variedad_ratings WHERE variedad_id=?', (vid,)).fetchone()
    return jsonify(ok=True, avg=round(avg[0] or 0, 1), count=avg[1] or 0)

@app.route('/mi-estado/<token>/pedido', methods=['POST'])
def portal_pedido(token):
    db = get_db()
    s = db.execute('SELECT * FROM socios WHERE token=?', (token,)).fetchone()
    if not s: return jsonify(ok=False, msg='Sesión inválida'), 403
    if s['etapa'] not in ('activo', 'aprobado', 'pleno'):
        return jsonify(ok=False, msg='Tu cuenta no está activa para realizar pedidos'), 403
    data = request.json if request.is_json else request.form
    variedad = (data.get('variedad', '') or '').strip()[:100]
    gramos = float(data.get('gramos', 0) or 0)
    forma_pago = (data.get('forma_pago', 'efectivo') or 'efectivo').strip()[:30]
    notas = (data.get('notas', '') or '').strip()[:300]
    if not variedad or gramos <= 0:
        return jsonify(ok=False, msg='Datos incompletos'), 400
    cupo = s['cupo_mensual_g'] or 30
    mes_inicio = date.today().replace(day=1).isoformat()
    consumido = (db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=? AND fecha>=?",
        (s['id'], mes_inicio)).fetchone()[0] or 0)
    consumido += (db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND fecha_pedido>=? AND estado IN ('pendiente','preparando','entregado')",
        (s['id'], mes_inicio)).fetchone()[0] or 0)
    if consumido + gramos > cupo:
        disponible = max(0, cupo - consumido)
        return jsonify(ok=False, msg=f'Superás tu cupo mensual. Disponible: {disponible:.1f}g'), 400
    codigo = 'PED-' + ''.join(__import__('random').choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))
    db.execute(
        "INSERT INTO pedidos (codigo,socio_id,variedad,gramos,forma_pago,estado,tipo_entrega,notas,registrado_por,origen) VALUES (?,?,?,?,?,'pendiente','retiro_club',?,?,?)",
        (codigo, s['id'], variedad, gramos, forma_pago, notas, s['nombre'], 'portal'))
    db.commit()
    return jsonify(ok=True, codigo=codigo, msg=f'Pedido {codigo} registrado. El club lo confirmará pronto.')

# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET','POST'])
@limiter.limit('10 per minute; 30 per hour')
def admin_login():
    if request.method == 'POST':
        u = (request.form.get('user') or '').strip()
        p = (request.form.get('password') or '').strip()
        db = get_db()
        # Busca en tabla usuarios primero
        usuario = db.execute(
            "SELECT * FROM usuarios WHERE username=? AND club_id=1 AND activo=1",
            (u,)
        ).fetchone()
        autenticado = False
        if usuario and usuario['password_hash'] == _hash_pw(p):
            autenticado = True
            session['admin']      = True
            session['user_role']  = usuario['role']
            session['user_nombre']= usuario['nombre'] or usuario['username']
            session['user_id']    = usuario['id']
        elif u == ADMIN_USER and p == ADMIN_PASS:
            # Fallback para admin por variable de entorno
            autenticado = True
            session['admin']      = True
            session['user_role']  = 'admin'
            session['user_nombre']= 'Administrador'
            session['user_id']    = 0
        if autenticado:
            try:
                db.execute(
                    "UPDATE clubs SET ultimo_acceso=datetime('now','localtime') WHERE id=1"
                )
                db.commit()
            except Exception:
                pass
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

@app.route('/admin/ver-socio')
@login_required
def admin_ver_socio():
    db = get_db()
    s = db.execute("SELECT token FROM socios WHERE etapa='activo' ORDER BY id LIMIT 1").fetchone()
    if not s:
        s = db.execute("SELECT token FROM socios ORDER BY id LIMIT 1").fetchone()
    if s:
        return redirect(url_for('portal', token=s['token']))
    return redirect(url_for('admin_socios'))

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

    # ── cuotas vencidas ──
    cuotas_vencidas = db.execute(
        "SELECT COUNT(*) FROM cuotas WHERE fecha_vencimiento < ? AND estado='pagada'", (hoy,)
    ).fetchone()[0]
    # ── aforo actual ──
    entradas_hoy_d = db.execute(
        "SELECT COUNT(*) FROM accesos WHERE fecha=? AND tipo='entrada'", (hoy,)
    ).fetchone()[0]
    salidas_hoy_d = db.execute(
        "SELECT COUNT(*) FROM accesos WHERE fecha=? AND tipo='salida'", (hoy,)
    ).fetchone()[0]
    aforo_actual = max(0, entradas_hoy_d - salidas_hoy_d)

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
        # cuotas y aforo
        cuotas_vencidas=cuotas_vencidas,
        aforo_actual=aforo_actual,
    )

@app.route('/admin/variedades', methods=['GET','POST'])
@login_required
def admin_variedades():
    db = get_db()
    if request.method == 'POST':
        accion = request.form.get('accion','crear')
        if accion == 'crear':
            nombre = request.form.get('nombre','').strip()
            if nombre:
                try:
                    db.execute(
                        'INSERT INTO variedades (nombre,genetica,thc_pct,cbd_pct,descripcion,efectos,indicaciones,sabor,imagen_url) VALUES (?,?,?,?,?,?,?,?,?)',
                        (nombre,
                         request.form.get('genetica','hibrido'),
                         float(request.form.get('thc_pct',0) or 0),
                         float(request.form.get('cbd_pct',0) or 0),
                         request.form.get('descripcion','').strip(),
                         request.form.get('efectos','').strip(),
                         request.form.get('indicaciones','').strip(),
                         request.form.get('sabor','').strip(),
                         request.form.get('imagen_url','').strip() or None))
                    db.commit()
                    flash(f'Variedad "{nombre}" agregada al catálogo ✓')
                except Exception:
                    flash('Ya existe una variedad con ese nombre')
        return redirect(url_for('admin_variedades'))
    variedades = db.execute('SELECT * FROM variedades ORDER BY nombre').fetchall()
    return render_template('admin/variedades.html', variedades=variedades, genetica_label=GENETICA_LABEL)

@app.route('/admin/variedad/<int:vid>', methods=['POST'])
@login_required
def admin_variedad_edit(vid):
    db = get_db()
    accion = request.form.get('accion','')
    if accion == 'eliminar':
        db.execute('DELETE FROM variedades WHERE id=?', (vid,))
    elif accion == 'toggle':
        db.execute('UPDATE variedades SET activa = 1 - activa WHERE id=?', (vid,))
    elif accion == 'editar':
        db.execute(
            'UPDATE variedades SET nombre=?,genetica=?,thc_pct=?,cbd_pct=?,descripcion=?,efectos=?,indicaciones=?,sabor=?,imagen_url=? WHERE id=?',
            (request.form.get('nombre','').strip(),
             request.form.get('genetica','hibrido'),
             float(request.form.get('thc_pct',0) or 0),
             float(request.form.get('cbd_pct',0) or 0),
             request.form.get('descripcion','').strip(),
             request.form.get('efectos','').strip(),
             request.form.get('indicaciones','').strip(),
             request.form.get('sabor','').strip(),
             request.form.get('imagen_url','').strip() or None,
             vid))
    db.commit()
    return redirect(url_for('admin_variedades'))

@app.route('/admin/cuotas')
@login_required
def admin_cuotas():
    db = get_db()
    hoy = date.today().isoformat()
    estado_f = request.args.get('estado','')
    q = request.args.get('q','').strip()

    sql = '''SELECT c.*, s.nombre, s.apellido, s.etapa
             FROM cuotas c JOIN socios s ON s.id=c.socio_id
             WHERE 1=1'''
    params = []
    if estado_f == 'vencida':
        sql += ' AND c.fecha_vencimiento < ? AND c.estado != "cancelada"'
        params.append(hoy)
    elif estado_f:
        sql += ' AND c.estado=?'; params.append(estado_f)
    if q:
        sql += ' AND (s.nombre LIKE ? OR s.apellido LIKE ?)'
        params += [f'%{q}%', f'%{q}%']
    sql += ' ORDER BY c.fecha_vencimiento ASC, c.id DESC'
    cuotas = db.execute(sql, params).fetchall()

    total_recaudado = db.execute('SELECT COALESCE(SUM(monto),0) FROM cuotas WHERE estado="pagada"').fetchone()[0]
    vencidas_count  = db.execute('SELECT COUNT(*) FROM cuotas WHERE fecha_vencimiento < ? AND estado="pagada"', (hoy,)).fetchone()[0]
    sin_cuota_count = db.execute(
        "SELECT COUNT(*) FROM socios WHERE etapa='activo' AND id NOT IN (SELECT DISTINCT socio_id FROM cuotas WHERE fecha_vencimiento >= ?)", (hoy,)
    ).fetchone()[0]

    socios_activos = db.execute(
        "SELECT id,nombre,apellido FROM socios WHERE etapa IN ('activo','aprobado') ORDER BY nombre"
    ).fetchall()
    return render_template('admin/cuotas.html',
        cuotas=cuotas, estado_f=estado_f, q=q,
        total_recaudado=round(total_recaudado,2),
        vencidas_count=vencidas_count,
        sin_cuota_count=sin_cuota_count,
        socios_activos=socios_activos, hoy=hoy)

@app.route('/admin/socio/<int:sid>/cuota', methods=['POST'])
@login_required
def admin_agregar_cuota(sid):
    db = get_db()
    tipo  = request.form.get('tipo','mensual')
    monto = float(request.form.get('monto',0) or 0)
    fecha_pago = request.form.get('fecha_pago') or date.today().isoformat()
    dias = {'mensual':30,'trimestral':90,'semestral':180,'anual':365}.get(tipo,30)
    fecha_venc = (datetime.strptime(fecha_pago,'%Y-%m-%d') + timedelta(days=dias)).strftime('%Y-%m-%d')
    notas = request.form.get('notas','').strip()
    db.execute(
        'INSERT INTO cuotas (socio_id,tipo,monto,fecha_pago,fecha_vencimiento,estado,notas) VALUES (?,?,?,?,?,?,?)',
        (sid, tipo, monto, fecha_pago, fecha_venc, 'pagada', notas))
    db.commit()
    flash(f'Cuota {tipo} registrada — vence el {fecha_venc}')
    return redirect(url_for('admin_socio', sid=sid))

@app.route('/admin/aforo', methods=['GET','POST'])
@login_required
def admin_aforo():
    db = get_db()
    hoy = date.today().isoformat()
    if request.method == 'POST':
        socio_id = request.form.get('socio_id')
        tipo     = request.form.get('tipo','entrada')
        hora     = datetime.now().strftime('%H:%M')
        if socio_id:
            db.execute('INSERT INTO accesos (socio_id,tipo,fecha,hora) VALUES (?,?,?,?)',
                       (socio_id, tipo, hoy, hora))
            db.commit()
            s = db.execute('SELECT nombre,apellido FROM socios WHERE id=?', (socio_id,)).fetchone()
            flash(f'{"Entrada" if tipo=="entrada" else "Salida"} registrada: {s["nombre"] if s else ""}')
        return redirect(url_for('admin_aforo'))

    entradas_hoy = db.execute(
        'SELECT COUNT(*) FROM accesos WHERE fecha=? AND tipo="entrada"', (hoy,)
    ).fetchone()[0]
    salidas_hoy = db.execute(
        'SELECT COUNT(*) FROM accesos WHERE fecha=? AND tipo="salida"', (hoy,)
    ).fetchone()[0]
    aforo_actual = max(0, entradas_hoy - salidas_hoy)

    dentro = db.execute('''
        SELECT a.socio_id, a.hora, s.nombre, s.apellido
        FROM accesos a JOIN socios s ON s.id=a.socio_id
        WHERE a.fecha=? AND a.tipo='entrada'
          AND a.socio_id NOT IN (
              SELECT socio_id FROM accesos WHERE fecha=? AND tipo='salida'
          )
        ORDER BY a.hora ASC
    ''', (hoy, hoy)).fetchall()

    historial = db.execute('''
        SELECT a.*, s.nombre, s.apellido
        FROM accesos a JOIN socios s ON s.id=a.socio_id
        WHERE a.fecha=?
        ORDER BY a.id DESC LIMIT 50
    ''', (hoy,)).fetchall()

    socios_activos = db.execute(
        "SELECT id,nombre,apellido FROM socios WHERE etapa IN ('activo','aprobado') ORDER BY nombre"
    ).fetchall()

    return render_template('admin/aforo.html',
        dentro=dentro, historial=historial, aforo_actual=aforo_actual,
        entradas_hoy=entradas_hoy, salidas_hoy=salidas_hoy,
        socios_activos=[dict(s) for s in socios_activos], hoy=hoy)

@app.route('/admin/dispensario', methods=['GET','POST'])
@login_required
@write_required
def admin_dispensario():
    db = get_db()
    hoy = date.today().isoformat()

    if request.method == 'POST':
        socio_id   = request.form.get('socio_id')
        variedad   = (request.form.get('variedad','') or request.form.get('variedad_manual','')).strip()
        gramos     = float(request.form.get('gramos', 0) or 0)
        notas      = request.form.get('notas','').strip()
        cosecha_id = request.form.get('cosecha_id','').strip() or None
        lote_cod   = None
        if cosecha_id:
            row = db.execute('SELECT lote_codigo FROM cosechas WHERE id=?', (cosecha_id,)).fetchone()
            if row:
                lote_cod = row['lote_codigo']
        if socio_id and variedad and gramos > 0:
            db.execute(
                "INSERT INTO dispensaciones (socio_id, variedad, gramos, fecha, notas, cosecha_id, lote_codigo) VALUES (?,?,?,?,?,?,?)",
                (socio_id, variedad, gramos, hoy, notas, cosecha_id, lote_cod)
            )
            _log_tarea(db, 'dispensacion', entity_type='socio', entity_id=int(socio_id),
                       result=f'{gramos}g de {variedad}' + (f' — Lote {lote_cod}' if lote_cod else ''))
            db.commit()
            flash(f'Dispensación registrada: {gramos}g de {variedad}' + (f' (Lote {lote_cod})' if lote_cod else ''))
        return redirect(url_for('admin_dispensario'))

    socios_activos = db.execute(
        "SELECT id, nombre, apellido, etapa, cupo_mensual_g FROM socios WHERE etapa IN ('activo','aprobado') ORDER BY nombre"
    ).fetchall()

    variedades_catalogo = db.execute(
        'SELECT * FROM variedades WHERE activa=1 ORDER BY nombre'
    ).fetchall()

    dispensaciones_hoy = db.execute('''
        SELECT d.*, s.nombre, s.apellido
        FROM dispensaciones d JOIN socios s ON s.id = d.socio_id
        WHERE d.fecha = ?
        ORDER BY d.id DESC
    ''', (hoy,)).fetchall()

    total_hoy_g = sum(d['gramos'] for d in dispensaciones_hoy)

    # Lotes con stock disponible para selección en dispensario
    lotes_disponibles_raw = db.execute('''
        SELECT co.id, co.lote_codigo, co.fecha, co.peso_seco_g, co.coa_status,
               cu.variedad,
               COALESCE((SELECT SUM(d.gramos) FROM dispensaciones d WHERE d.cosecha_id = co.id), 0) as entregado_g
        FROM cosechas co JOIN cultivos cu ON cu.id = co.cultivo_id
        WHERE co.lote_codigo IS NOT NULL
        ORDER BY cu.variedad, co.fecha DESC
    ''').fetchall()
    lotes_disponibles = {}
    for l in lotes_disponibles_raw:
        disp = round((l['peso_seco_g'] or 0) - (l['entregado_g'] or 0), 1)
        if disp > 0:
            v = l['variedad']
            if v not in lotes_disponibles:
                lotes_disponibles[v] = []
            lotes_disponibles[v].append({
                'id': l['id'],
                'lote': l['lote_codigo'],
                'fecha': l['fecha'],
                'disponible_g': disp,
                'coa': l['coa_status'],
            })

    return render_template('admin/dispensario.html',
        socios_activos=[dict(s) for s in socios_activos],
        variedades_catalogo=[dict(v) for v in variedades_catalogo],
        dispensaciones_hoy=dispensaciones_hoy,
        total_hoy_g=round(total_hoy_g, 1),
        hoy=hoy,
        lotes_disponibles=lotes_disponibles,
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
    consumido_mes_pedidos = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND fecha_pedido >= ? AND estado='entregado'",
        (sid, mes_inicio)
    ).fetchone()[0]
    consumido_mes_disp = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=? AND fecha >= ?",
        (sid, mes_inicio)
    ).fetchone()[0]
    consumido_mes = consumido_mes_pedidos + consumido_mes_disp
    total_consumido_pedidos = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND estado='entregado'", (sid,)
    ).fetchone()[0]
    total_consumido_disp = db.execute(
        "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=?", (sid,)
    ).fetchone()[0]
    total_consumido = total_consumido_pedidos + total_consumido_disp
    total_gastado = db.execute(
        "SELECT COALESCE(SUM(precio),0) FROM pedidos WHERE socio_id=? AND estado='entregado'", (sid,)
    ).fetchone()[0]
    dispensaciones_socio = db.execute(
        'SELECT * FROM dispensaciones WHERE socio_id=? ORDER BY fecha DESC, id DESC LIMIT 30',
        (sid,)
    ).fetchall()
    cuota_actual = db.execute(
        'SELECT * FROM cuotas WHERE socio_id=? ORDER BY fecha_vencimiento DESC LIMIT 1', (sid,)
    ).fetchone()
    todas_cuotas = db.execute(
        'SELECT * FROM cuotas WHERE socio_id=? ORDER BY fecha_pago DESC', (sid,)
    ).fetchall()
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
    # Calcular días hasta vencimiento REPROCANN
    reprocann_dias = None
    if s['reprocann_vencimiento'] if 'reprocann_vencimiento' in s.keys() else None:
        try:
            reprocann_dias = (date.fromisoformat(s['reprocann_vencimiento']) - date.today()).days
        except Exception:
            pass
    return render_template('admin/socio.html',
        s=s, notas=notas, docs=docs, cultivos=cultivos,
        pedidos=pedidos, consumido_mes=consumido_mes,
        total_consumido=total_consumido, total_gastado=total_gastado,
        stock_variedades=stock_variedades, member_url=member_url,
        dispensaciones_socio=dispensaciones_socio,
        cuota_actual=cuota_actual, todas_cuotas=todas_cuotas,
        reprocann_dias=reprocann_dias,
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
@write_required
def admin_set_etapa(sid):
    etapa = request.form.get('etapa','')
    if etapa in ETAPAS:
        db2 = get_db()
        db2.execute('UPDATE socios SET etapa=?, updated_at=datetime("now","localtime") WHERE id=?', (etapa, sid))
        _log_tarea(db2, 'cambio_etapa_socio', entity_type='socio', entity_id=sid,
                   result=f'→ {ETAPA_LABEL.get(etapa, etapa)}')
        _emit_event(db2, 'MEMBER_UPDATED', entity_type='socio', entity_id=sid,
                    payload={'etapa': etapa})
        if etapa == 'activo':
            _emit_event(db2, 'MEMBER_ACTIVATED', entity_type='socio', entity_id=sid)
        db2.commit()
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

@app.route('/admin/socio/<int:sid>/reprocann', methods=['POST'])
@login_required
@write_required
def admin_actualizar_reprocann(sid):
    f = request.form
    codigo       = f.get('reprocann_codigo','').strip()
    estado       = f.get('reprocann_estado','sin_registro')
    inicio       = f.get('reprocann_inicio','').strip()
    vencimiento  = f.get('reprocann_vencimiento','').strip()
    plantas      = f.get('plantas_autorizadas','9').strip()
    try: plantas = int(plantas)
    except Exception: plantas = 9
    db = get_db()
    db.execute('''UPDATE socios SET
        reprocann_codigo=?, reprocann_estado=?, reprocann_inicio=?,
        reprocann_vencimiento=?, plantas_autorizadas=?,
        updated_at=datetime('now','localtime')
        WHERE id=?''',
        (codigo or None, estado, inicio or None, vencimiento or None, plantas, sid))
    db.commit()
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

@app.route('/admin/exportar/dispensaciones')
@login_required
def admin_exportar_dispensaciones():
    db = get_db()
    rows = db.execute('''
        SELECT d.id, d.fecha, d.variedad, d.gramos, d.lote_codigo,
               s.nombre, s.apellido, s.dni, s.reprocann_codigo,
               d.notas, d.registrado_por
        FROM dispensaciones d JOIN socios s ON s.id = d.socio_id
        ORDER BY d.fecha DESC, d.id DESC
    ''').fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['ID','Fecha','Variedad','Gramos','Lote','Nombre','Apellido','DNI','REPROCANN','Notas','Registrado por'])
    for r in rows: w.writerow(list(r))
    resp = make_response(out.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=germina_dispensaciones_{date.today()}.csv'
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
    # trazabilidad semilla
    banco_genetico         = f.get('banco_genetico','').strip()
    tipo_semilla           = f.get('tipo_semilla','')
    num_semillas_compradas = int(f.get('num_semillas_compradas', 0) or 0)
    num_semillas_germinadas= int(f.get('num_semillas_germinadas', 0) or 0)
    precio_semilla         = float(f.get('precio_semilla', 0) or 0)
    proveedor_semilla      = f.get('proveedor_semilla','').strip()
    fecha_compra_semilla   = f.get('fecha_compra_semilla','')
    factura_numero         = f.get('factura_numero','').strip()
    lote_semilla           = f.get('lote_semilla','').strip()
    url_banco              = f.get('url_banco','').strip()

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
         ubicacion_detalle, sustrato, notas, estado,
         banco_genetico, tipo_semilla, num_semillas_compradas, num_semillas_germinadas,
         precio_semilla, proveedor_semilla, fecha_compra_semilla,
         factura_numero, lote_semilla, url_banco)
        VALUES (?,?,?,?,?,?,?,'germinacion',?,?,?,?,?,'activo',?,?,?,?,?,?,?,?,?,?)
    ''', (codigo, sid, variedad, genetica, n_plant, tipo,
          fecha_i, fecha_i, cos_est, ubicacion, sustrato, notas,
          banco_genetico, tipo_semilla, num_semillas_compradas, num_semillas_germinadas,
          precio_semilla, proveedor_semilla, fecha_compra_semilla,
          factura_numero, lote_semilla, url_banco))

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
    _log_tarea(db, 'cambio_etapa_cultivo', actor=prof, entity_type='cultivo', entity_id=cid,
               result=f'→ {ETAPA_CULTIVO_LABEL.get(nueva, nueva)}')
    _emit_event(db, 'CULTIVO_STAGE_CHANGED', entity_type='cultivo', entity_id=cid,
                payload={'etapa_nueva': nueva})
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
    lote       = _next_lote_codigo(db, fecha)
    thc        = f.get('thc_real_pct','').strip() or None
    cbd        = f.get('cbd_real_pct','').strip() or None
    lab        = f.get('laboratorio','').strip() or None
    resp_cos   = f.get('responsable_cosecha','').strip() or prof
    cond_alm   = f.get('condiciones_almacenamiento','').strip() or None

    db.execute('''
        INSERT INTO cosechas (cultivo_id, fecha, num_plantas, peso_humedo_g, peso_seco_g,
            calidad, notas, registrado_por, lote_codigo, thc_real_pct, cbd_real_pct,
            laboratorio, responsable_cosecha, condiciones_almacenamiento, coa_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pendiente')
    ''', (cid, fecha, n_plant, peso_h, peso_s, calidad, notas, prof,
          lote, thc, cbd, lab, resp_cos, cond_alm))
    # avanza etapa a cosecha si no estaba
    c = db.execute('SELECT etapa_actual FROM cultivos WHERE id=?', (cid,)).fetchone()
    if c and c['etapa_actual'] not in ('cosecha','curado','finalizado'):
        db.execute("UPDATE cultivos SET etapa_actual='cosecha', fecha_etapa=? WHERE id=?",
                   (date.today().isoformat(), cid))
        db.execute('''INSERT INTO etapas_cultivo (cultivo_id, etapa_anterior, etapa_nueva, notas, registrado_por)
                      VALUES (?,?,'cosecha','Cosecha registrada',?)''',
                   (cid, c['etapa_actual'], prof))
    _log_tarea(db, 'registro_cosecha', entity_type='cultivo', entity_id=cid,
               result=f'{peso_s}g secos — Lote {lote}')
    db.commit()
    flash(f'Cosecha registrada. Lote asignado: {lote}')
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
@write_required
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
    _log_tarea(db, 'nuevo_pedido' if nuevo == 'pendiente' else 'dispensacion',
               entity_type='pedido', entity_id=pid,
               result=f'Estado → {ESTADO_PEDIDO_LABEL.get(nuevo, nuevo)}')
    _emit_event(db, 'ORDER_STATUS_CHANGED', entity_type='pedido', entity_id=pid,
                payload={'estado': nuevo})
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

# ─── Germina AI — helpers de registro ────────────────────────────────────────

def _log_tarea(db, task_type, actor='Admin', agent_id=None,
               entity_type=None, entity_id=None, result=None, club_id=1):
    """Registra una acción en audit_log y calcula tiempo humano ahorrado en roi_tasks."""
    db.execute('''
        INSERT INTO audit_log
        (club_id, agent_id, action, actor, entity_type, entity_id, result)
        VALUES (?,?,?,?,?,?,?)
    ''', (club_id, agent_id, task_type, actor, entity_type, entity_id,
          result if isinstance(result, str) else json.dumps(result) if result else None))
    log_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    cfg = db.execute('SELECT human_minutes FROM task_type_config WHERE task_type=?',
                     (task_type,)).fetchone()
    human_min = cfg['human_minutes'] if cfg else 3
    db.execute('''
        INSERT INTO roi_tasks (club_id, agent_id, task_type, audit_log_id, human_minutes_saved)
        VALUES (?,?,?,?,?)
    ''', (club_id, agent_id, task_type, log_id, human_min))
    return log_id

def _emit_event(db, event_type, entity_type=None, entity_id=None, payload=None, club_id=1):
    """Emite un evento al motor de eventos para que los agentes puedan procesarlo."""
    db.execute('''
        INSERT INTO events (club_id, event_type, entity_type, entity_id, payload)
        VALUES (?,?,?,?,?)
    ''', (club_id, event_type, entity_type, entity_id,
          json.dumps(payload) if payload else None))

def _evaluar_reglas(db, field, value, jurisdiction='AR'):
    """Evalúa el motor de reglas. Retorna lista de reglas violadas."""
    rules = db.execute('''
        SELECT * FROM rules
        WHERE jurisdiction=? AND status='active' AND condition_field=?
        AND (effective_until IS NULL OR effective_until >= date('now'))
    ''', (jurisdiction, field)).fetchall()
    violations = []
    for r in rules:
        try:
            op, val = r['condition_operator'], r['condition_value']
            v_num = float(value) if value not in (None,'') else 0
            c_num = float(val) if val not in (None,'') else 0
            hit = (
                (op == 'gt'  and v_num >  c_num) or
                (op == 'gte' and v_num >= c_num) or
                (op == 'lt'  and v_num <  c_num) or
                (op == 'lte' and v_num <= c_num) or
                (op == 'eq'  and str(value) == str(val))
            )
            if hit:
                violations.append(dict(r))
        except Exception:
            pass
    return violations

# ─── BLOG SEO ──────────────────────────────────────────────────────────────

ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Taxonomía profesional de keywords por cluster temático.
# cluster: agrupa temas para construir autoridad topical (Google premia sitios que cubren temas en profundidad)
# intent: informational = educa y atrae tráfico | commercial = investigan soluciones | transactional = listos para contratar
# priority: 1=alta (long-tail, más fácil de rankear, conversión más alta) / 2=media / 3=baja (short-tail, muy competida)
KEYWORDS_SEO = [
    # ── CLUSTER 1: Legal y Regulatorio (Argentina) ──────────────────────────
    # Búsquedas de personas que quieren saber si es legal / cómo cumplir. Alto volumen informacional.
    {"kw": "cómo legalizar un club cannábico en Argentina",             "cluster": "legal",      "intent": "informational", "priority": 1},
    {"kw": "requisitos legales cannabis social club Argentina 2026",    "cluster": "legal",      "intent": "informational", "priority": 1},
    {"kw": "marco legal asociaciones cannábicas medicinales Argentina",  "cluster": "legal",      "intent": "informational", "priority": 2},
    {"kw": "habilitaciones club cannabis medicinal Argentina",          "cluster": "legal",      "intent": "informational", "priority": 2},
    {"kw": "ley cannabis social club Argentina estatuto modelo",        "cluster": "legal",      "intent": "informational", "priority": 3},

    # ── CLUSTER 2: Gestión Operativa ────────────────────────────────────────
    # Directivos de clubes buscando cómo resolver problemas concretos del día a día.
    {"kw": "cómo gestionar un cannabis social club paso a paso",        "cluster": "gestion",    "intent": "informational", "priority": 1},
    {"kw": "gestión de socios club cannábico digital",                  "cluster": "gestion",    "intent": "informational", "priority": 1},
    {"kw": "control de stock cannabis medicinal asociación",            "cluster": "gestion",    "intent": "informational", "priority": 2},
    {"kw": "onboarding de nuevos socios club cannábico",               "cluster": "gestion",    "intent": "informational", "priority": 2},
    {"kw": "sistema de turnos y entregas dispensario cannabis",         "cluster": "gestion",    "intent": "informational", "priority": 2},
    {"kw": "administración financiera asociación cannábica",            "cluster": "gestion",    "intent": "informational", "priority": 3},
    {"kw": "trazabilidad cultivos cannabis social club registro",       "cluster": "gestion",    "intent": "informational", "priority": 3},

    # ── CLUSTER 3: Tecnología y Software ────────────────────────────────────
    # Intención comercial: ya saben que necesitan software, están eligiendo cuál.
    {"kw": "software para clubes cannábicos Argentina",                 "cluster": "tecnologia", "intent": "commercial",    "priority": 1},
    {"kw": "digitalizar club de cannabis medicinal herramientas",       "cluster": "tecnologia", "intent": "commercial",    "priority": 1},
    {"kw": "sistema de gestión de socios club cannábico",               "cluster": "tecnologia", "intent": "commercial",    "priority": 1},
    {"kw": "portal web para socios cannabis social club",               "cluster": "tecnologia", "intent": "commercial",    "priority": 2},
    {"kw": "app gestión cannabis social club Argentina",                "cluster": "tecnologia", "intent": "commercial",    "priority": 2},
    {"kw": "software trazabilidad cannabis medicinal LATAM",            "cluster": "tecnologia", "intent": "commercial",    "priority": 2},
    {"kw": "dispensario cannabis medicinal software gestión integral",  "cluster": "tecnologia", "intent": "commercial",    "priority": 3},

    # ── CLUSTER 4: Mercado y Tendencias LATAM ───────────────────────────────
    # Contenido de industria: posiciona Germina como referente del sector.
    {"kw": "cannabis social clubs Argentina crecimiento 2026",          "cluster": "mercado",    "intent": "informational", "priority": 1},
    {"kw": "tendencias cannabis medicinal Argentina 2026",              "cluster": "mercado",    "intent": "informational", "priority": 1},
    {"kw": "cannabis social clubs modelo España aplicado en Argentina", "cluster": "mercado",    "intent": "informational", "priority": 2},
    {"kw": "herramientas gestión asociaciones cannabis LATAM",          "cluster": "mercado",    "intent": "informational", "priority": 2},
    {"kw": "futuro del cannabis medicinal en Argentina regulación",     "cluster": "mercado",    "intent": "informational", "priority": 3},

    # ── CLUSTER 5: Conversión (fondo de embudo) ──────────────────────────────
    # Búsquedas de personas listas para contratar: máxima prioridad de conversión.
    {"kw": "mejor software gestión cannabis social club Argentina",     "cluster": "conversion", "intent": "transactional", "priority": 1},
    {"kw": "alternativas a Excel para gestionar club cannábico",        "cluster": "conversion", "intent": "commercial",    "priority": 1},
    {"kw": "beneficios digitalizar asociación cannábica medicinal",     "cluster": "conversion", "intent": "commercial",    "priority": 2},
    {"kw": "cuánto cuesta software cannabis social club",               "cluster": "conversion", "intent": "commercial",    "priority": 2},
    {"kw": "por qué digitalizar tu club cannábico con Germina",        "cluster": "conversion", "intent": "transactional", "priority": 3},
]

# Orden en que se cubren los clusters (primero los que más tráfico traen)
_CLUSTER_ORDER = ["legal", "gestion", "tecnologia", "mercado", "conversion"]

# ─── SEO IMAGE POOL (5 fotos Pexels por cluster, rotación automática) ────────
_IMAGES_SEO = {
    "legal": [
        {"id": "7667721",  "alt": "Técnico con guantes inspeccionando planta de cannabis medicinal"},
        {"id": "5411141",  "alt": "Primer plano de planta de cannabis en entorno profesional"},
        {"id": "29359795", "alt": "Planta de cannabis sativa saludable al aire libre"},
        {"id": "8849944",  "alt": "Vista superior de planta de cannabis en etapa de crecimiento"},
        {"id": "9259989",  "alt": "Pinzas sobre planta de cannabis en proceso de control de calidad"},
    ],
    "gestion": [
        {"id": "33965725", "alt": "Trabajador concentrado en cultivo indoor de cannabis medicinal"},
        {"id": "9260000",  "alt": "Persona manejando cannabis con pinzas en entorno profesional"},
        {"id": "7667885",  "alt": "Cultivador sosteniendo planta de cannabis verde en invernadero"},
        {"id": "28862111", "alt": "Flor de cannabis en invernadero profesional de cultivo medicinal"},
        {"id": "18512077", "alt": "Detalle de planta de cannabis en sistema de gestión de cultivo"},
    ],
    "tecnologia": [
        {"id": "9259933",  "alt": "Cannabis medicinal en tubo de laboratorio sobre balanza de precisión"},
        {"id": "9259936",  "alt": "Cannabis en frasco de tubo para análisis de laboratorio"},
        {"id": "33930123", "alt": "Marihuana medicinal en frasco de prescripción sobre fondo blanco"},
        {"id": "9259854",  "alt": "Macro fotografía de cannabis medicinal para análisis de trazabilidad"},
        {"id": "3047447",  "alt": "Fotografía macro de cogollo de cannabis para trazabilidad digital"},
    ],
    "mercado": [
        {"id": "33325757", "alt": "Campo de cannabis medicinal bajo cielo azul en plantación profesional"},
        {"id": "33326126", "alt": "Vista aérea de campo de cáñamo en cosecha industrial"},
        {"id": "8658545",  "alt": "Planta de cannabis al aire libre en cultivo de mercado emergente"},
        {"id": "9550945",  "alt": "Hojas verdes de cannabis en producción medicinal de escala"},
        {"id": "33314138", "alt": "Planta de cannabis exuberante representando la industria cannábica Argentina"},
    ],
    "conversion": [
        {"id": "8140284",  "alt": "Cannabis en frasco de vidrio transparente — gestión profesional de stock"},
        {"id": "4173868",  "alt": "Señalización de cannabis social club en fachada de local"},
        {"id": "11251682", "alt": "Cartel institucional de cannabis social club en pared verde"},
        {"id": "4618418",  "alt": "Plantas organizadas en espacio profesional de gestión cannábica"},
        {"id": "9058867",  "alt": "Planta de cannabis en maceta en club cannábico profesional"},
    ],
}
_PEXELS_URL = "https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1"

def _elegir_imagen(cluster, db):
    """Retorna (hero_url, hero_alt, inline_url, inline_alt) del pool del cluster.
    El índice se avanza en config SOLO al publicar (llamar desde /api/publicar-articulo)."""
    pool = _IMAGES_SEO.get(cluster, _IMAGES_SEO["legal"])
    n = len(pool)
    key = f"img_idx_{cluster}"
    row = db.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    idx = int(row[0]) if row else 0
    hero   = pool[idx % n]
    inline = pool[(idx + 1) % n]
    next_idx = (idx + 1) % n
    db.execute("INSERT OR REPLACE INTO config (key,value) VALUES (?,?)", (key, str(next_idx)))
    return (
        _PEXELS_URL.format(id=hero["id"]),   hero["alt"],
        _PEXELS_URL.format(id=inline["id"]), inline["alt"],
    )

def _elegir_keyword(db):
    """Selección estratégica de keyword:
    1. Cubre clusters vacíos en orden antes de repetir cualquier cluster.
    2. Dentro de cada cluster: prioridad 1 antes de 2 y 3; informational antes de commercial.
    3. Si todos los clusters tienen artículos: vuelve al cluster con el artículo más antiguo.
    4. Si todas las keywords tienen artículo: empieza la segunda vuelta por las más antiguas."""
    rows = db.execute('SELECT keyword, created_at FROM articulos ORDER BY created_at DESC').fetchall()
    usadas_fecha = {r[0]: r[1] for r in rows}

    clusters = {c: [] for c in _CLUSTER_ORDER}
    for item in KEYWORDS_SEO:
        clusters[item['cluster']].append(item)

    # Fecha del artículo más reciente por cluster (None si el cluster no tiene artículos)
    cluster_ultima_fecha = {}
    for item in KEYWORDS_SEO:
        if item['kw'] in usadas_fecha:
            c = item['cluster']
            f = usadas_fecha[item['kw']]
            if c not in cluster_ultima_fecha or f > cluster_ultima_fecha[c]:
                cluster_ultima_fecha[c] = f

    def _candidatos_sin_usar(c):
        return [k for k in clusters[c] if k['kw'] not in usadas_fecha]

    def _mejor_de(lista):
        # informational primero, luego commercial, luego transactional; dentro de cada intent, prioridad ascendente
        intent_order = {"informational": 0, "commercial": 1, "transactional": 2}
        lista.sort(key=lambda x: (intent_order.get(x['intent'], 9), x['priority']))
        return lista[0]['kw']

    # Paso 1: clusters con cero artículos, en orden canónico
    for c in _CLUSTER_ORDER:
        if c not in cluster_ultima_fecha:
            candidatos = _candidatos_sin_usar(c)
            if candidatos:
                return _mejor_de(candidatos)

    # Paso 2: todos los clusters tienen al menos un artículo → elegir el cluster más rezagado
    cluster_rezagado = min(cluster_ultima_fecha, key=lambda c: cluster_ultima_fecha[c])
    candidatos = _candidatos_sin_usar(cluster_rezagado)
    if candidatos:
        return _mejor_de(candidatos)

    # Paso 3: todas las keywords usadas → segunda vuelta por fecha de publicación más antigua
    todas_con_fecha = [(item, usadas_fecha.get(item['kw'], '1970-01-01')) for item in KEYWORDS_SEO]
    todas_con_fecha.sort(key=lambda x: x[1])
    return todas_con_fecha[0][0]['kw']


def _generar_articulo_ia(keyword, intent='informational'):
    import urllib.request, json as _json, re, unicodedata

    intent_instruccion = {
        'informational': "Tono educativo. Respondé la pregunta del lector en profundidad con datos concretos.",
        'commercial':    "Tono comparativo. Mostrá por qué digitalizar es superior a Excel/papel, con ejemplos reales.",
        'transactional': "Tono persuasivo. Urgencia real, primer mes gratis sin tarjeta, beneficios concretos desde el día 1.",
    }.get(intent, '')

    prompt = f"""Sos redactor senior de contenidos SEO especializado en cannabis medicinal y SaaS para Argentina y LATAM.
Escribí un artículo editorial de 950-1100 palabras sobre: "{keyword}"
Intención: {intent} — {intent_instruccion}

ESTRUCTURA OBLIGATORIA — usá exactamente estas clases CSS en el HTML:

1. HOOK (obligatorio al inicio): un párrafo impactante con un dato sorprendente, una pregunta provocadora o un escenario real. Envolvelo en: <div class="art-hook"><p>texto del hook</p></div>

2. ESTADÍSTICA DESTACADA (obligatoria, una sola): un número o porcentaje real o estimado sobre el sector. Formato: <div class="art-stat"><span class="stat-num">73%</span><span class="stat-label">de los cannabis social clubs en Argentina operan sin personería jurídica — y no lo saben</span></div>

3. CUERPO: 4 a 5 secciones con <h2> descriptivos. Usá <p>, <ul>, <li>, <strong> normalmente.

4. CALLOUT TIP (obligatorio, uno o dos): recuadro de consejo práctico. Formato: <div class="art-callout art-tip"><strong>Lo que no te dicen:</strong> texto del consejo concreto y accionable</div>

5. CALLOUT WARNING (obligatorio, uno): alerta sobre error frecuente. Formato: <div class="art-callout art-warning"><strong>Error frecuente:</strong> descripción del error y sus consecuencias reales</div>

6. PULL QUOTE (obligatorio, uno): la frase más poderosa del artículo, con fuerza editorial. Formato: <blockquote class="art-quote">frase memorable aquí</blockquote>

7. CTA INLINE (obligatorio, uno en el centro del artículo): <div class="art-cta-mid"><div><strong>¿Tu club ya tiene sistema de gestión?</strong><p>Germina es la plataforma diseñada para clubs cannábicos en Argentina. Primer mes gratis.</p></div><a href="https://germina-clubs.netlify.app#contacto">Ver demo gratuita →</a></div>

8. CIERRE: párrafo final que retoma el hook y cierra el círculo narrativo, con mención natural de Germina.

REGLAS:
- NO uses markdown, NO uses CSS inline, NO uses imágenes
- El H1 debe incluir la keyword de forma natural
- Germina se menciona máximo 3 veces en todo el artículo
- Tono: profesional pero humano, como un asesor que conoce el sector

Respondé SOLO con JSON válido sin texto extra:
{{"titulo": "...", "resumen": "...(100-140 chars)", "meta_description": "...(120-155 chars)", "contenido": "...(HTML completo, todo en una sola línea)"}}"""

    body = _json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2500,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'x-api-key': ANTHROPIC_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
    )
    resp = _json.loads(urllib.request.urlopen(req, timeout=30).read())
    text = resp['content'][0]['text'].strip()
    # extraer JSON aunque venga con markdown
    m = re.search(r'\{[\s\S]+\}', text)
    data = _json.loads(m.group(0)) if m else _json.loads(text)

    # generar slug
    slug_base = unicodedata.normalize('NFD', data['titulo'].lower())
    slug_base = ''.join(c for c in slug_base if unicodedata.category(c) != 'Mn')
    slug_base = re.sub(r'[^a-z0-9]+', '-', slug_base).strip('-')[:80]

    return {
        'slug':             slug_base,
        'titulo':           data['titulo'],
        'resumen':          data.get('resumen', '')[:200],
        'contenido':        data['contenido'],
        'keyword':          keyword,
        'meta_description': data.get('meta_description', '')[:160],
    }

@app.route('/api/publicar-articulo', methods=['POST'])
@limiter.limit('30 per hour')
def api_publicar_articulo():
    import re, unicodedata
    data = request.get_json(silent=True) or {}
    if data.get('secret') != CRM_PASS:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 403
    titulo    = (data.get('titulo') or '').strip()
    contenido = (data.get('contenido') or '').strip()
    if not titulo or not contenido:
        return jsonify({'ok': False, 'error': 'missing fields'}), 400

    db = get_db()

    # Asignar imágenes automáticamente desde el pool del cluster
    cluster = data.get('cluster', 'legal')
    hero_url, hero_alt, inline_url, inline_alt = _elegir_imagen(cluster, db)

    # Inyectar hero al inicio del contenido
    hero_html = f'<img class="art-img-hero" src="{hero_url}" alt="{hero_alt}" loading="lazy">'
    contenido = hero_html + contenido

    # Inyectar inline justo antes del CTA central
    inline_html = f'<img class="art-img-inline" src="{inline_url}" alt="{inline_alt}" loading="lazy"><p class="art-img-caption">{inline_alt}.</p>'
    if '<div class="art-cta-mid">' in contenido:
        contenido = contenido.replace('<div class="art-cta-mid">', inline_html + '<div class="art-cta-mid">', 1)

    slug_base = unicodedata.normalize('NFD', titulo.lower())
    slug_base = ''.join(c for c in slug_base if unicodedata.category(c) != 'Mn')
    slug_base = re.sub(r'[^a-z0-9]+', '-', slug_base).strip('-')[:80]

    db.execute(
        'INSERT OR IGNORE INTO articulos (slug,titulo,resumen,contenido,keyword,meta_description) VALUES (?,?,?,?,?,?)',
        (slug_base, titulo, data.get('resumen','')[:200], contenido,
         data.get('keyword',''), data.get('meta_description','')[:160])
    )
    db.commit()
    return jsonify({'ok': True, 'slug': slug_base})

@app.route('/api/next-keyword')
def api_next_keyword():
    """Devuelve la próxima keyword a trabajar según criterio estratégico de SEO."""
    if request.args.get('secret') != CRM_PASS:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 403
    db = get_db()
    keyword = _elegir_keyword(db)
    meta = next((k for k in KEYWORDS_SEO if k['kw'] == keyword), {})
    return jsonify({'ok': True, 'keyword': keyword, 'cluster': meta.get('cluster'), 'intent': meta.get('intent')})

@app.route('/api/generar-articulo', methods=['POST'])
@limiter.limit('10 per hour')
def api_generar_articulo():
    import re as _re, unicodedata as _uni
    secret = request.json.get('secret') if request.is_json else request.form.get('secret')
    if secret != CRM_PASS:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 403
    if not ANTHROPIC_KEY:
        return jsonify({'ok': False, 'error': 'ANTHROPIC_API_KEY no configurada en Render'}), 500
    db = get_db()
    keyword = _elegir_keyword(db)
    meta = next((k for k in KEYWORDS_SEO if k['kw'] == keyword), {})
    cluster = meta.get('cluster', 'legal')
    try:
        art = _generar_articulo_ia(keyword, intent=meta.get('intent', 'informational'))
        contenido = art['contenido']

        # Inyectar imágenes del pool del cluster
        hero_url, hero_alt, inline_url, inline_alt = _elegir_imagen(cluster, db)
        hero_html = f'<img class="art-img-hero" src="{hero_url}" alt="{hero_alt}" loading="lazy">'
        contenido = hero_html + contenido
        inline_html = f'<img class="art-img-inline" src="{inline_url}" alt="{inline_alt}" loading="lazy"><p class="art-img-caption">{inline_alt}.</p>'
        if '<div class="art-cta-mid">' in contenido:
            contenido = contenido.replace('<div class="art-cta-mid">', inline_html + '<div class="art-cta-mid">', 1)

        db.execute(
            'INSERT OR IGNORE INTO articulos (slug,titulo,resumen,contenido,keyword,meta_description) VALUES (?,?,?,?,?,?)',
            (art['slug'], art['titulo'], art['resumen'], contenido, art['keyword'], art['meta_description'])
        )
        db.commit()
        return jsonify({'ok': True, 'slug': art['slug'], 'titulo': art['titulo'], 'keyword': keyword})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/blog')
def blog():
    db = get_db()
    articulos = db.execute(
        'SELECT id,slug,titulo,resumen,keyword,created_at FROM articulos WHERE publicado=1 ORDER BY id DESC'
    ).fetchall()
    return render_template('blog/index.html', articulos=articulos)

@app.route('/sitemap.xml')
def sitemap():
    db = get_db()
    arts = db.execute(
        'SELECT slug, created_at FROM articulos WHERE publicado=1 ORDER BY id DESC'
    ).fetchall()
    base = 'https://germina-app.onrender.com'
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'<url><loc>{base}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>',
        f'<url><loc>{base}/blog</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
    ]
    for a in arts:
        lastmod = a['created_at'][:10] if a['created_at'] else date.today().isoformat()
        lines.append(f'<url><loc>{base}/blog/{a["slug"]}</loc><lastmod>{lastmod}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
    lines.append('</urlset>')
    return Response('\n'.join(lines), mimetype='application/xml')

@app.route('/blog/<slug>')
def blog_articulo(slug):
    db = get_db()
    art = db.execute('SELECT * FROM articulos WHERE slug=? AND publicado=1', (slug,)).fetchone()
    if not art:
        return redirect(url_for('blog'))
    recientes = db.execute(
        'SELECT slug,titulo FROM articulos WHERE publicado=1 AND slug!=? ORDER BY id DESC LIMIT 4', (slug,)
    ).fetchall()
    return render_template('blog/articulo.html', art=art, recientes=recientes)

# ─── CRM INTERNO GERMINA ───────────────────────────────────────────────────

@app.route('/crm/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute; 30 per hour', methods=['POST'])
def crm_login():
    error = None
    if request.method == 'POST':
        if request.form.get('u') == CRM_USER and request.form.get('p') == CRM_PASS:
            session['crm_ok'] = True
            return redirect(url_for('crm_prospectos'))
        error = 'Credenciales incorrectas'
    return render_template('crm_login.html', error=error)

@app.route('/crm/logout')
def crm_logout():
    session.pop('crm_ok', None)
    return redirect(url_for('crm_login'))

@app.route('/crm')
@app.route('/crm/prospectos')
def crm_prospectos():
    if not session.get('crm_ok'):
        return redirect(url_for('crm_login'))
    prospectos = _get_prospectos_imap()
    return render_template('crm_prospectos.html', prospectos=prospectos)

# ═══════════════════════════════════════════════════════════════════════════
#  CENTRO DE CONTROL
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/centro-control')
@login_required
def admin_centro_control():
    db  = get_db()
    hoy = date.today().isoformat()
    mes_inicio = date.today().replace(day=1).isoformat()

    # ── Tareas registradas hoy (audit_log + acciones manuales) ──────────────
    tareas_ai_hoy = db.execute(
        "SELECT COUNT(*) FROM audit_log WHERE DATE(timestamp)=?", (hoy,)
    ).fetchone()[0]
    disp_hoy = db.execute("SELECT COUNT(*) FROM dispensaciones WHERE fecha=?", (hoy,)).fetchone()[0]
    accesos_hoy = db.execute("SELECT COUNT(*) FROM accesos WHERE fecha=?", (hoy,)).fetchone()[0]
    total_tareas_hoy = tareas_ai_hoy + disp_hoy + accesos_hoy

    # ── Tiempo ahorrado (en minutos, de roi_tasks) ──────────────────────────
    tiempo_ahorrado_min = db.execute(
        "SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks WHERE DATE(timestamp)=?", (hoy,)
    ).fetchone()[0] or 0
    tiempo_ahorrado_semana = db.execute(
        "SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks WHERE timestamp >= date('now','-7 days')"
    ).fetchone()[0] or 0

    # ── Últimas acciones del log ─────────────────────────────────────────────
    log_reciente = db.execute('''
        SELECT al.*, tt.human_minutes, tt.description as task_desc
        FROM audit_log al
        LEFT JOIN task_type_config tt ON tt.task_type = al.action
        ORDER BY al.id DESC LIMIT 20
    ''').fetchall()

    # ── Eventos pendientes de procesamiento ──────────────────────────────────
    eventos_pendientes = db.execute(
        "SELECT COUNT(*) FROM events WHERE status='pending'"
    ).fetchone()[0]

    # ── Cosas que necesitan atención del admin ────────────────────────────────
    socios_pendientes = db.execute(
        "SELECT COUNT(*) FROM socios WHERE etapa IN ('solicitud','documentacion','en_revision')"
    ).fetchone()[0]
    cuotas_vencidas = db.execute(
        "SELECT COUNT(*) FROM cuotas WHERE fecha_vencimiento < ? AND estado='pagada'", (hoy,)
    ).fetchone()[0]
    cosechas_urgentes = db.execute(
        "SELECT COUNT(*) FROM cultivos WHERE estado='activo' AND cosecha_estimada IS NOT NULL "
        "AND cosecha_estimada >= date('now') AND cosecha_estimada <= date('now','+14 days')"
    ).fetchone()[0]
    pedidos_activos = db.execute(
        "SELECT COUNT(*) FROM pedidos WHERE estado IN ('pendiente','preparando')"
    ).fetchone()[0]

    # Stock bajo (< 50g disponibles)
    alertas_stock = []
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
        disp_g = round((row['total_g'] or 0) - entregado - reservado, 1)
        if disp_g < 50:
            alertas_stock.append({'variedad': v, 'disponible_g': disp_g})

    total_para_revisar = socios_pendientes + cuotas_vencidas + cosechas_urgentes + pedidos_activos + len(alertas_stock)

    # ── Impacto del mes ──────────────────────────────────────────────────────
    dispensaciones_mes = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(gramos),0) FROM dispensaciones WHERE fecha >= ?", (mes_inicio,)
    ).fetchone()
    socios_nuevos_mes = db.execute(
        "SELECT COUNT(*) FROM socios WHERE created_at >= ?", (mes_inicio,)
    ).fetchone()[0]
    roi_mes_min = db.execute(
        "SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks WHERE timestamp >= ?", (mes_inicio,)
    ).fetchone()[0] or 0

    # ── Últimos socios con evento ─────────────────────────────────────────────
    socios_recientes = db.execute('''
        SELECT * FROM socios ORDER BY updated_at DESC LIMIT 5
    ''').fetchall()

    return render_template('admin/centro_control.html',
        hoy=hoy,
        total_tareas_hoy=total_tareas_hoy,
        tareas_ai_hoy=tareas_ai_hoy,
        disp_hoy=disp_hoy,
        accesos_hoy=accesos_hoy,
        tiempo_ahorrado_min=round(tiempo_ahorrado_min),
        tiempo_ahorrado_semana=round(tiempo_ahorrado_semana),
        log_reciente=log_reciente,
        eventos_pendientes=eventos_pendientes,
        socios_pendientes=socios_pendientes,
        cuotas_vencidas=cuotas_vencidas,
        cosechas_urgentes=cosechas_urgentes,
        pedidos_activos=pedidos_activos,
        alertas_stock=alertas_stock,
        total_para_revisar=total_para_revisar,
        dispensaciones_mes=dispensaciones_mes,
        socios_nuevos_mes=socios_nuevos_mes,
        roi_mes_min=round(roi_mes_min),
        socios_recientes=socios_recientes,
        etapa_label=ETAPA_LABEL,
        etapa_color=ETAPA_COLOR,
    )

# ═══════════════════════════════════════════════════════════════════════════
#  GERMINA AUTOPILOT
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/autopilot')
@role_required('admin')
def admin_autopilot():
    db = get_db()
    config_rows = db.execute(
        "SELECT agent_id, action_id, level FROM autopilot_config WHERE club_id=1 ORDER BY agent_id, action_id"
    ).fetchall()
    config = {(r['agent_id'], r['action_id']): r['level'] for r in config_rows}

    rules = db.execute(
        "SELECT * FROM rules WHERE status='active' ORDER BY jurisdiction, rule_id"
    ).fetchall()

    roi_total = db.execute(
        "SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks"
    ).fetchone()[0] or 0
    tareas_total = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]

    return render_template('admin/autopilot.html',
        agents=AGENTS,
        agent_actions=AGENT_ACTIONS,
        autopilot_levels=AUTOPILOT_LEVELS,
        config=config,
        rules=rules,
        roi_total_min=round(roi_total),
        tareas_total=tareas_total,
    )

@app.route('/admin/autopilot/update', methods=['POST'])
@role_required('admin')
def admin_autopilot_update():
    db = get_db()
    agent_id  = request.form.get('agent_id','').strip()
    action_id = request.form.get('action_id','').strip()
    level     = request.form.get('level','RECOMENDAR')
    if agent_id in AGENTS and level in AUTOPILOT_LEVELS:
        db.execute('''
            INSERT INTO autopilot_config (club_id, agent_id, action_id, level)
            VALUES (1,?,?,?)
            ON CONFLICT(club_id, agent_id, action_id) DO UPDATE SET level=excluded.level
        ''', (agent_id, action_id, level))
        db.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(ok=True, level=level, label=AUTOPILOT_LEVELS.get(level,''))
    return redirect(url_for('admin_autopilot'))

# ═══════════════════════════════════════════════════════════════════════════
#  AUDITORÍA
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/auditoria')
@login_required
def admin_auditoria():
    db = get_db()
    logs = db.execute('''
        SELECT al.*, tt.human_minutes, tt.description as task_desc
        FROM audit_log al
        LEFT JOIN task_type_config tt ON tt.task_type = al.action
        ORDER BY al.id DESC LIMIT 200
    ''').fetchall()
    total_min = db.execute("SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks").fetchone()[0] or 0
    total_tareas = db.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    return render_template('admin/auditoria.html',
        logs=logs,
        total_min=round(total_min),
        total_tareas=total_tareas,
    )

# ═══════════════════════════════════════════════════════════════════════════
#  GERMINA AI — MOTOR DE AGENTES
# ═══════════════════════════════════════════════════════════════════════════

def _send_email_simple(to, subject, body):
    """Envía un email simple de texto plano."""
    msg = MIMEMultipart()
    msg['From']    = MAIL_USER
    msg['To']      = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.starttls()
        s.login(MAIL_USER, MAIL_PASS)
        s.send_message(msg)

def _llamar_llm(prompt, max_tokens=400):
    """Llama a Claude Haiku. Retorna (texto, tokens_in, tokens_out, cost_usd)."""
    import urllib.request as _ur, json as _j
    if not ANTHROPIC_KEY:
        return ('Sin clave de IA configurada', 0, 0, 0.0)
    # Límite de seguridad: no enviar prompts excesivamente grandes
    if len(prompt) > 4000:
        prompt = prompt[:4000] + '\n[contexto truncado por seguridad]'
    body = _j.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': prompt}]
    }).encode()
    req = _ur.Request('https://api.anthropic.com/v1/messages', data=body, headers={
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    })
    resp = _j.loads(_ur.urlopen(req, timeout=25).read())
    text = resp['content'][0]['text'].strip()
    tin  = resp['usage']['input_tokens']
    tout = resp['usage']['output_tokens']
    cost = (tin * 0.00000025) + (tout * 0.00000125)
    return (text, tin, tout, cost)

def _crear_tarea_agente(db, agent_id, task_type, entity_type, entity_id,
                        input_data, recommendation, level, club_id=1):
    db.execute('''
        INSERT INTO agent_tasks (club_id, agent_id, task_type, entity_type, entity_id,
            level, input_data, recommendation)
        VALUES (?,?,?,?,?,?,?,?)
    ''', (club_id, agent_id, task_type, entity_type, entity_id, level,
          json.dumps(input_data) if isinstance(input_data, dict) else str(input_data),
          recommendation))
    return db.execute('SELECT last_insert_rowid()').fetchone()[0]

def _agente_socios_scan(db, club_id=1):
    """Escanea el club y genera tareas automáticas para el Agente Socios."""
    hoy = date.today().isoformat()
    generadas = 0

    def _level(action_id):
        r = db.execute(
            "SELECT level FROM autopilot_config WHERE club_id=? AND agent_id='socios' AND action_id=?",
            (club_id, action_id)).fetchone()
        return r['level'] if r else 'RECOMENDAR'

    # Solicitudes sin revisar > 24hs
    solicitudes = db.execute('''
        SELECT id, nombre, apellido, dni, email, created_at FROM socios
        WHERE etapa='solicitud' AND created_at <= datetime('now','-1 day')
        AND id NOT IN (
            SELECT entity_id FROM agent_tasks
            WHERE agent_id='socios' AND task_type='alta_socio' AND DATE(timestamp)=?
        )
    ''', (hoy,)).fetchall()

    lv = _level('alta_socio')
    for s in solicitudes:
        nombre_s = _sanitizar_input(f"{s['nombre']} {s['apellido']}")
        prompt = (f"Sos el Agente Socios de un cannabis social club en Argentina. "
                  f"El socio [DATOS: {nombre_s}] envió su solicitud el {s['created_at']} "
                  f"y lleva más de 24hs sin revisión. Redactá una recomendación de 2 oraciones para el administrador. "
                  f"Español, tono profesional.")
        try:
            rec, tin, tout, cost = _llamar_llm(prompt, 150)
        except Exception:
            rec = f"Solicitud de {s['nombre']} {s['apellido']} pendiente desde {s['created_at']}. Revisar documentación."
            tin = tout = cost = 0
        tid = _crear_tarea_agente(db, 'socios', 'alta_socio', 'socio', s['id'],
            {'nombre': f"{s['nombre']} {s['apellido']}", 'email': s['email']}, rec, lv)
        _log_tarea(db, 'alta_socio', actor='Agente Socios', agent_id='socios',
                   entity_type='socio', entity_id=s['id'], result=f'Tarea #{tid}', club_id=club_id)
        generadas += 1

    # Recordatorio cuotas vencidas
    cuotas = db.execute('''
        SELECT s.id, s.nombre, s.apellido, s.email, q.fecha_vencimiento
        FROM socios s
        JOIN cuotas q ON q.socio_id = s.id
        WHERE s.etapa='activo' AND q.tipo='mensual'
        AND q.fecha_vencimiento < date('now') AND q.estado != 'pagada'
        AND s.id NOT IN (
            SELECT entity_id FROM agent_tasks
            WHERE agent_id='socios' AND task_type='recordatorio_cuota' AND DATE(timestamp)=?
        )
        LIMIT 5
    ''', (hoy,)).fetchall()

    lv = _level('recordatorio_cuota')
    for s in cuotas:
        rec = (f"{s['nombre']} {s['apellido']} tiene una cuota mensual vencida "
               f"(vencimiento: {s['fecha_vencimiento']}). Recordarle para regularizar.")
        tid = _crear_tarea_agente(db, 'socios', 'recordatorio_cuota', 'socio', s['id'],
            {'nombre': f"{s['nombre']} {s['apellido']}", 'email': s['email']}, rec, lv)
        _log_tarea(db, 'recordatorio_cuota', actor='Agente Socios', agent_id='socios',
                   entity_type='socio', entity_id=s['id'], result=f'Tarea #{tid}', club_id=club_id)
        generadas += 1

    # Socios inactivos > 60 días
    inactivos = db.execute('''
        SELECT id, nombre, apellido, email FROM socios
        WHERE etapa='activo' AND updated_at <= datetime('now','-60 days')
        AND id NOT IN (
            SELECT entity_id FROM agent_tasks
            WHERE agent_id='socios' AND task_type='seguimiento_inactivo' AND DATE(timestamp)=?
        )
        LIMIT 3
    ''', (hoy,)).fetchall()

    lv = _level('seguimiento_inactivo')
    for s in inactivos:
        rec = (f"{s['nombre']} {s['apellido']} no registra actividad hace más de 60 días. "
               f"¿Querés contactarle para ver si sigue participando del club?")
        tid = _crear_tarea_agente(db, 'socios', 'seguimiento_inactivo', 'socio', s['id'],
            {'nombre': f"{s['nombre']} {s['apellido']}", 'email': s['email']}, rec, lv)
        _log_tarea(db, 'seguimiento_inactivo', actor='Agente Socios', agent_id='socios',
                   entity_type='socio', entity_id=s['id'], result=f'Tarea #{tid}', club_id=club_id)
        generadas += 1

    # Credenciales REPROCANN por vencer (≤60 días)
    hoy_d = date.today()
    proximos_60 = (hoy_d + timedelta(days=60)).isoformat()
    por_vencer = []
    try:
        por_vencer = db.execute('''
            SELECT id, nombre, apellido, reprocann_vencimiento
            FROM socios WHERE etapa='activo'
            AND reprocann_vencimiento IS NOT NULL AND reprocann_vencimiento != ''
            AND reprocann_vencimiento BETWEEN ? AND ?
            AND id NOT IN (
                SELECT entity_id FROM agent_tasks
                WHERE agent_id='socios' AND task_type='vencimiento_reprocann' AND DATE(timestamp)=?
            )
        ''', (hoy, proximos_60, hoy)).fetchall()
    except Exception:
        pass

    lv = _level('vencimiento_reprocann')
    for s in por_vencer:
        try:
            dias_rest = (date.fromisoformat(s['reprocann_vencimiento']) - hoy_d).days
        except Exception:
            dias_rest = 0
        rec = (f"La credencial REPROCANN de {s['nombre']} {s['apellido']} vence el "
               f"{s['reprocann_vencimiento']} ({dias_rest} días restantes). "
               f"Gestionar renovación con el médico prescriptor cuanto antes.")
        tid = _crear_tarea_agente(db, 'socios', 'vencimiento_reprocann', 'socio', s['id'],
            {'nombre': f"{s['nombre']} {s['apellido']}", 'vencimiento': s['reprocann_vencimiento']}, rec, lv)
        _log_tarea(db, 'vencimiento_reprocann', actor='Agente Socios', agent_id='socios',
                   entity_type='socio', entity_id=s['id'], result=f'Vence en {dias_rest} días', club_id=club_id)
        generadas += 1

    db.commit()
    return generadas

def _agente_admin_scan(db, club_id=1):
    """Escanea el club y genera alertas/reportes para el Agente Administración."""
    hoy = date.today().isoformat()
    generadas = 0

    def _level(action_id):
        r = db.execute(
            "SELECT level FROM autopilot_config WHERE club_id=? AND agent_id='administracion' AND action_id=?",
            (club_id, action_id)).fetchone()
        return r['level'] if r else 'RECOMENDAR'

    # Alertas de stock bajo
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
        disp_g = round((row['total_g'] or 0) - entregado - reservado, 1)
        if disp_g < 50:
            ya = db.execute(
                "SELECT id FROM agent_tasks WHERE agent_id='administracion' AND task_type='alerta_stock' AND DATE(timestamp)=? AND input_data LIKE ?",
                (hoy, f'%{v}%')
            ).fetchone()
            if not ya:
                lv = _level('alerta_stock')
                rec = f"Stock de {v} bajo: solo {disp_g}g disponibles. Revisar cronograma de cosechas."
                _crear_tarea_agente(db, 'administracion', 'alerta_stock', 'variedad', None,
                    {'variedad': v, 'disponible_g': disp_g}, rec, lv)
                _log_tarea(db, 'alerta_stock', actor='Agente Administración', agent_id='administracion',
                           result=f'{v}: {disp_g}g disponibles', club_id=club_id)
                generadas += 1

    # Predicción de agotamiento de stock (días restantes por variedad)
    lv_pred = _level('prediccion_stock')
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
        disp_g = round((row['total_g'] or 0) - entregado - reservado, 1)
        if disp_g <= 0:
            continue
        # Consumo últimos 30 días
        consumo_30d = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE variedad=? AND estado='entregado' AND fecha_pedido>=date('now','-30 days')", (v,)
        ).fetchone()[0] or 0
        consumo_30d += db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE variedad=? AND fecha>=date('now','-30 days')", (v,)
        ).fetchone()[0] or 0
        if consumo_30d <= 0:
            continue
        tasa_diaria = consumo_30d / 30.0
        dias_rest = int(disp_g / tasa_diaria)
        if dias_rest < 30:
            ya_pred = db.execute(
                "SELECT id FROM agent_tasks WHERE agent_id='administracion' AND task_type='prediccion_stock' AND DATE(timestamp)=? AND input_data LIKE ?",
                (hoy, f'%{v}%')
            ).fetchone()
            if not ya_pred:
                rec_pred = (f"ALERTA PREDICTIVA: la variedad {v} se agotaría en aproximadamente {dias_rest} días "
                            f"(stock: {disp_g}g, tasa de consumo: {tasa_diaria:.1f}g/día). "
                            f"Revisá el cronograma de cosechas o ajustá el cupo mensual por socio.")
                _crear_tarea_agente(db, 'administracion', 'prediccion_stock', 'variedad', None,
                    {'variedad': v, 'disponible_g': disp_g, 'tasa_diaria_g': round(tasa_diaria,1),
                     'dias_restantes': dias_rest}, rec_pred, lv_pred)
                _log_tarea(db, 'prediccion_stock', actor='Agente Administración', agent_id='administracion',
                           result=f'{v}: {dias_rest} días restantes', club_id=club_id)
                generadas += 1

    # Reporte diario (una vez por día)
    ya_reporte = db.execute(
        "SELECT id FROM agent_tasks WHERE agent_id='administracion' AND task_type='reporte_diario' AND DATE(timestamp)=?",
        (hoy,)).fetchone()
    if not ya_reporte:
        lv = _level('reporte_diario')
        activos = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]
        d_hoy   = db.execute("SELECT COUNT(*) FROM dispensaciones WHERE fecha=?", (hoy,)).fetchone()[0]
        p_pend  = db.execute("SELECT COUNT(*) FROM pedidos WHERE estado='pendiente'").fetchone()[0]
        rec = f"Resumen {hoy} — Socios activos: {activos} · Dispensaciones hoy: {d_hoy} · Pedidos pendientes: {p_pend}"
        _crear_tarea_agente(db, 'administracion', 'reporte_diario', 'club', club_id,
            {'fecha': hoy, 'socios_activos': activos, 'dispensaciones_hoy': d_hoy, 'pedidos_pendientes': p_pend},
            rec, lv)
        _log_tarea(db, 'reporte_diario', actor='Agente Administración', agent_id='administracion',
                   result=rec, club_id=club_id)
        generadas += 1

    db.commit()
    return generadas

def _agente_patrones_scan(db, club_id=1):
    """Detecta patrones anómalos de consumo usando IA real (Claude Haiku)."""
    from datetime import date, timedelta
    hoy = date.today()
    hoy_s = hoy.isoformat()
    hace30 = (hoy - timedelta(days=30)).isoformat()
    hace60 = (hoy - timedelta(days=60)).isoformat()
    generadas = 0

    def _level(action_id):
        r = db.execute(
            "SELECT level FROM autopilot_config WHERE club_id=? AND agent_id='patrones' AND action_id=?",
            (club_id, action_id)).fetchone()
        return r['level'] if r else 'RECOMENDAR'

    socios_activos = db.execute(
        "SELECT id, nombre, apellido, diagnostico, cupo_mensual_g FROM socios WHERE etapa='activo'"
    ).fetchall()

    for s in socios_activos:
        sid = s['id']
        nombre = f"{s['nombre']} {s['apellido']}"

        # Consumo período actual (últimos 30 días)
        actual = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND estado='entregado' AND fecha_pedido>=?",
            (sid, hace30)).fetchone()[0] or 0
        actual += db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=? AND fecha>=?",
            (sid, hace30)).fetchone()[0] or 0

        # Consumo período anterior (30-60 días atrás)
        anterior = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE socio_id=? AND estado='entregado' AND fecha_pedido>=? AND fecha_pedido<?",
            (sid, hace60, hace30)).fetchone()[0] or 0
        anterior += db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=? AND fecha>=? AND fecha<?",
            (sid, hace60, hace30)).fetchone()[0] or 0

        ya_hoy = db.execute(
            "SELECT id FROM agent_tasks WHERE agent_id='patrones' AND entity_id=? AND DATE(timestamp)=?",
            (sid, hoy_s)).fetchone()
        if ya_hoy:
            continue

        tipo_alerta = None
        # Aumento rápido: consumo actual más del 50% mayor que anterior (y anterior > 0)
        if anterior > 0 and actual > anterior * 1.5 and actual > 5:
            tipo_alerta = 'aumento_consumo'
        # Inactividad prolongada: activo en período anterior pero nada en los últimos 30 días
        elif anterior > 0 and actual == 0:
            tipo_alerta = 'inactividad_prolongada'
        # Cese abrupto: consumía con regularidad (>10g en período anterior) y paró
        elif anterior >= 10 and actual == 0:
            tipo_alerta = 'cese_abrupto'

        if not tipo_alerta:
            continue

        diagnostico = s['diagnostico'] or 'no registrado'
        prompt = (
            f"Sos el asistente clínico de un cannabis social club en Argentina bajo la Ley 27.350.\n"
            f"Detectaste el siguiente patrón en el socio {nombre} (diagnóstico: {diagnostico}):\n"
            f"- Consumo últimos 30 días: {actual:.1f}g\n"
            f"- Consumo 30-60 días previos: {anterior:.1f}g\n"
            f"- Tipo de alerta: {tipo_alerta.replace('_',' ')}\n\n"
            f"Redactá una recomendación breve (2-3 oraciones) para el administrador del club sobre "
            f"qué acción tomar. Tono profesional y clínico. Solo la recomendación, sin saludos."
        )
        try:
            rec, tin, tout, cost = _llamar_llm(prompt, 200)
        except Exception:
            variaciones = {
                'aumento_consumo': f"{nombre} aumentó su consumo un {((actual-anterior)/anterior*100):.0f}% respecto al mes anterior ({anterior:.1f}g → {actual:.1f}g). Considerar una entrevista de seguimiento.",
                'inactividad_prolongada': f"{nombre} no registra consumo en los últimos 30 días (consumía {anterior:.1f}g en el período anterior). Podría haber abandonado el club.",
                'cese_abrupto': f"{nombre} cesó abruptamente su consumo (de {anterior:.1f}g a {actual:.1f}g). Verificar estado y continuidad del tratamiento.",
            }
            rec = variaciones.get(tipo_alerta, f"Patrón anómalo detectado en {nombre}.")
            tin = tout = cost = 0

        lv = _level(tipo_alerta)
        tid = _crear_tarea_agente(db, 'patrones', tipo_alerta, 'socio', sid,
            {'nombre': nombre, 'consumo_actual_g': actual, 'consumo_anterior_g': anterior,
             'diagnostico': diagnostico}, rec, lv)
        _log_tarea(db, tipo_alerta, actor='Agente Patrones', agent_id='patrones',
                   entity_type='socio', entity_id=sid, result=f'Tarea #{tid}', club_id=club_id)
        generadas += 1

    # Recomendaciones de variedades personalizadas (una vez por día por club)
    ya_rec = db.execute(
        "SELECT id FROM agent_tasks WHERE agent_id='patrones' AND task_type='recomendacion_variedad' AND DATE(timestamp)=?",
        (hoy_s,)).fetchone()
    if not ya_rec:
        lv = _level('recomendacion_variedad')
        # Socios con diagnóstico y ratings registrados
        candidatos = db.execute('''
            SELECT s.id, s.nombre, s.apellido, s.diagnostico,
                   GROUP_CONCAT(DISTINCT vr.sabores) as sabores_hist,
                   GROUP_CONCAT(DISTINCT vr.efectos_sentidos) as efectos_hist
            FROM socios s
            JOIN variedad_ratings vr ON vr.socio_id = s.id
            WHERE s.etapa='activo' AND s.diagnostico IS NOT NULL
              AND vr.lo_repetiria IN ('Sí','si','yes')
            GROUP BY s.id
            LIMIT 5
        ''').fetchall()

        for c in candidatos:
            variedades_disp = db.execute(
                "SELECT nombre, genetica, efectos, indicaciones, sabor FROM variedades WHERE activa=1 LIMIT 10"
            ).fetchall()
            vars_texto = '; '.join([f"{v['nombre']} ({v['genetica']}, efectos: {v['efectos']}, indicaciones: {v['indicaciones']})" for v in variedades_disp])
            prompt2 = (
                f"Sos asesor de un cannabis social club en Argentina (Ley 27.350).\n"
                f"Socio: {c['nombre']} {c['apellido']}, diagnóstico: {c['diagnostico']}.\n"
                f"Historial de sabores que le gustaron: {c['sabores_hist'] or 'sin datos'}.\n"
                f"Efectos que reportó positivamente: {c['efectos_hist'] or 'sin datos'}.\n"
                f"Variedades disponibles: {vars_texto}.\n"
                f"Recomendá 1-2 variedades específicas para este socio con justificación clínica breve. "
                f"Solo la recomendación, sin saludos ni intro."
            )
            try:
                rec2, tin2, tout2, cost2 = _llamar_llm(prompt2, 200)
            except Exception:
                rec2 = f"Recomendación basada en perfil de {c['nombre']} {c['apellido']} (diagnóstico: {c['diagnostico']}). Revisar historial de ratings para sugerencia manual."
            _crear_tarea_agente(db, 'patrones', 'recomendacion_variedad', 'socio', c['id'],
                {'nombre': f"{c['nombre']} {c['apellido']}", 'diagnostico': c['diagnostico']},
                rec2, lv)
            generadas += 1

    db.commit()
    return generadas

def _agente_reprocann_scan(db, club_id=1):
    """Genera alerta si se acerca el semestre y no hay informe REPROCANN registrado."""
    from datetime import date
    hoy = date.today()
    hoy_s = hoy.isoformat()
    generadas = 0

    def _level(action_id):
        r = db.execute(
            "SELECT level FROM autopilot_config WHERE club_id=? AND agent_id='reprocann' AND action_id=?",
            (club_id, action_id)).fetchone()
        return r['level'] if r else 'RECOMENDAR'

    # Determinar semestre actual
    if hoy.month <= 6:
        sem_label = f"{hoy.year}-S1"
        sem_fin = date(hoy.year, 6, 30)
    else:
        sem_label = f"{hoy.year}-S2"
        sem_fin = date(hoy.year, 12, 31)

    dias_para_fin = (sem_fin - hoy).days

    # Alertar si faltan ≤45 días para el cierre del semestre y no hay informe generado
    if dias_para_fin > 45:
        return 0

    ya_informe = db.execute(
        "SELECT id FROM reprocann_reports WHERE club_id=? AND semestre=?",
        (club_id, sem_label)).fetchone()

    ya_tarea = db.execute(
        "SELECT id FROM agent_tasks WHERE agent_id='reprocann' AND task_type='informe_semestral' AND input_data LIKE ?",
        (f'%{sem_label}%',)).fetchone()

    if ya_informe or ya_tarea:
        return 0

    lv = _level('informe_semestral')
    rec = (f"Faltan {dias_para_fin} días para cerrar el semestre {sem_label}. "
           f"La Ley 27.350 y el Decreto 883/2020 exigen presentar el informe semestral al REPROCANN "
           f"con datos de socios, diagnósticos, producción y distribución. "
           f"Entrá a Agentes → REPROCANN para generar el informe automáticamente.")
    _crear_tarea_agente(db, 'reprocann', 'informe_semestral', 'club', club_id,
        {'semestre': sem_label, 'dias_restantes': dias_para_fin, 'fecha_limite': sem_fin.isoformat()},
        rec, lv)
    _log_tarea(db, 'informe_semestral', actor='Agente REPROCANN', agent_id='reprocann',
               entity_type='club', entity_id=club_id,
               result=f'Alerta semestre {sem_label}', club_id=club_id)
    generadas += 1
    db.commit()
    return generadas

def _ejecutar_tarea_agente(db, task):
    """Ejecuta una tarea aprobada (nivel EJECUTAR o aprobada manualmente en PREPARAR)."""
    task_type  = task['task_type']
    input_data = json.loads(task['input_data']) if task['input_data'] else {}

    if task_type == 'recordatorio_cuota':
        email  = input_data.get('email', '')
        nombre = input_data.get('nombre', '')
        if email:
            try:
                _send_email_simple(
                    email,
                    f"Recordatorio de cuota — {CLUB_NOMBRE}",
                    f"Hola {nombre},\n\nTe recordamos que tenés una cuota mensual pendiente en {CLUB_NOMBRE}.\n"
                    f"Regularizá tu situación para seguir disfrutando de todos los beneficios del club.\n\n"
                    f"Saludos,\n{CLUB_NOMBRE}"
                )
                return 'Email de recordatorio enviado correctamente'
            except Exception as e:
                return f'Error al enviar email: {e}'
        return 'Socio sin email de contacto registrado'

    if task_type == 'alta_socio':
        return 'Revisá el socio en el panel de socios para completar el alta manualmente'

    if task_type in ('aumento_consumo', 'inactividad_prolongada', 'cese_abrupto'):
        email  = input_data.get('email', '')
        nombre = input_data.get('nombre', '')
        if email:
            try:
                asunto_map = {
                    'aumento_consumo': f'Seguimiento de consumo — {CLUB_NOMBRE}',
                    'inactividad_prolongada': f'Te extrañamos en {CLUB_NOMBRE}',
                    'cese_abrupto': f'¿Todo bien? Te contactamos desde {CLUB_NOMBRE}',
                }
                cuerpo_map = {
                    'aumento_consumo': f"Hola {nombre},\n\nNuestro equipo registró un cambio en tu patrón de consumo y queremos hacer un seguimiento.\nSi tenés alguna consulta o necesitás ajustar tu plan, no dudes en contactarnos.\n\nSaludos,\n{CLUB_NOMBRE}",
                    'inactividad_prolongada': f"Hola {nombre},\n\nHace un tiempo que no te vemos por el club. Esperamos que estés bien.\nSi necesitás algo, respondé este email o acercate cuando puedas.\n\nSaludos,\n{CLUB_NOMBRE}",
                    'cese_abrupto': f"Hola {nombre},\n\nNotamos que no has retirado producto últimamente y queremos asegurarnos de que todo esté bien.\nSi tomaste la decisión de pausar tu tratamiento, podemos ayudarte a documentarlo correctamente.\n\nSaludos,\n{CLUB_NOMBRE}",
                }
                _send_email_simple(email, asunto_map[task_type], cuerpo_map[task_type])
                return 'Email de seguimiento enviado correctamente'
            except Exception as e:
                return f'Error al enviar email: {e}'
        return 'Recomendación registrada. El socio no tiene email para notificar.'

    if task_type == 'recomendacion_variedad':
        return 'Recomendación de variedad generada. Podés comunicársela al socio en su próxima visita.'

    if task_type == 'prediccion_stock':
        return 'Alerta de predicción registrada. Revisá el stock y el cronograma de cosechas.'

    if task_type == 'alerta_stock':
        return 'Alerta de stock bajo registrada. Revisá el inventario en el panel de stock.'

    if task_type == 'informe_semestral':
        return 'Alerta REPROCANN registrada. Generá el informe desde Configuración → REPROCANN.'

    if task_type == 'seguimiento_inactivo':
        email  = input_data.get('email', '')
        nombre = input_data.get('nombre', '')
        if email:
            try:
                _send_email_simple(
                    email,
                    f"Te extrañamos en {CLUB_NOMBRE}",
                    f"Hola {nombre},\n\n¿Todo bien? Hace un tiempo que no te vemos por el club.\n"
                    f"Si necesitás algo o querés ponerte al día, respondé este email o acercate cuando puedas.\n\n"
                    f"Saludos,\n{CLUB_NOMBRE}"
                )
                return 'Email de seguimiento enviado correctamente'
            except Exception as e:
                return f'Error al enviar email: {e}'
        return 'Socio sin email de contacto registrado'

    return 'Acción registrada (sin automatización directa disponible para este tipo)'

# ─── Agentes — panel y cola de tareas ─────────────────────────────────────────

@app.route('/admin/agentes')
@login_required
def admin_agentes():
    db = get_db()
    hoy = date.today().isoformat()

    stats = {}
    for agent_id in AGENTS:
        total = db.execute(
            "SELECT COUNT(*) FROM agent_tasks WHERE agent_id=?", (agent_id,)
        ).fetchone()[0]
        hoy_cnt = db.execute(
            "SELECT COUNT(*) FROM agent_tasks WHERE agent_id=? AND DATE(timestamp)=?",
            (agent_id, hoy)
        ).fetchone()[0]
        pendientes = db.execute(
            "SELECT COUNT(*) FROM agent_tasks WHERE agent_id=? AND status='pendiente'",
            (agent_id,)
        ).fetchone()[0]
        ultimo = db.execute(
            "SELECT timestamp FROM agent_tasks WHERE agent_id=? ORDER BY id DESC LIMIT 1",
            (agent_id,)
        ).fetchone()
        stats[agent_id] = {
            'total': total,
            'hoy': hoy_cnt,
            'pendientes': pendientes,
            'ultimo': ultimo['timestamp'] if ultimo else None,
        }

    ultimo_scan = db.execute(
        "SELECT timestamp FROM audit_log WHERE agent_id IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()

    return render_template('admin/agentes.html',
        agents=AGENTS,
        agent_actions=AGENT_ACTIONS,
        stats=stats,
        ultimo_scan=ultimo_scan['timestamp'] if ultimo_scan else None,
    )

@app.route('/admin/tareas')
@login_required
def admin_tareas():
    db  = get_db()
    filtro = request.args.get('filtro', 'pendiente')
    agente = request.args.get('agente', '')

    q = "SELECT * FROM agent_tasks WHERE 1=1"
    params = []
    if filtro and filtro != 'todos':
        q += " AND status=?"
        params.append(filtro)
    if agente:
        q += " AND agent_id=?"
        params.append(agente)
    q += " ORDER BY id DESC LIMIT 100"
    tareas = db.execute(q, params).fetchall()

    total_pend = db.execute("SELECT COUNT(*) FROM agent_tasks WHERE status='pendiente'").fetchone()[0]
    total_aprobadas = db.execute("SELECT COUNT(*) FROM agent_tasks WHERE approval_status='aprobado'").fetchone()[0]
    total_rechazadas = db.execute("SELECT COUNT(*) FROM agent_tasks WHERE approval_status='rechazado'").fetchone()[0]

    return render_template('admin/tareas.html',
        tareas=tareas,
        agents=AGENTS,
        agent_actions=AGENT_ACTIONS,
        autopilot_levels=AUTOPILOT_LEVELS,
        filtro=filtro,
        agente=agente,
        total_pend=total_pend,
        total_aprobadas=total_aprobadas,
        total_rechazadas=total_rechazadas,
    )

@app.route('/admin/tareas/<int:task_id>/aprobar', methods=['POST'])
@login_required
@write_required
def admin_tarea_aprobar(task_id):
    db = get_db()
    task = db.execute('SELECT * FROM agent_tasks WHERE id=?', (task_id,)).fetchone()
    if not task:
        flash('Tarea no encontrada')
        return redirect(url_for('admin_tareas'))

    resultado = _ejecutar_tarea_agente(db, task)
    db.execute('''
        UPDATE agent_tasks
        SET approval_status='aprobado', approved_by='Admin',
            approved_at=datetime('now','localtime'),
            execution_result=?, status='ejecutado'
        WHERE id=?
    ''', (resultado, task_id))
    _log_tarea(db, task['task_type'], actor='Admin', agent_id=task['agent_id'],
               entity_type=task['entity_type'], entity_id=task['entity_id'],
               result=f'Aprobado y ejecutado: {resultado}')
    db.commit()
    flash(f'Tarea aprobada — {resultado}')
    return redirect(url_for('admin_tareas'))

@app.route('/admin/tareas/<int:task_id>/rechazar', methods=['POST'])
@login_required
def admin_tarea_rechazar(task_id):
    db = get_db()
    task = db.execute('SELECT * FROM agent_tasks WHERE id=?', (task_id,)).fetchone()
    if not task:
        flash('Tarea no encontrada')
        return redirect(url_for('admin_tareas'))
    razon = request.form.get('razon', 'Rechazado por el administrador')
    db.execute('''
        UPDATE agent_tasks
        SET approval_status='rechazado', approved_by='Admin',
            approved_at=datetime('now','localtime'),
            execution_result=?, status='rechazado'
        WHERE id=?
    ''', (razon, task_id))
    db.commit()
    flash('Tarea rechazada')
    return redirect(url_for('admin_tareas'))

# ─── RBAC — gestión de usuarios ───────────────────────────────────────────────

ROLES = {
    'admin':    'Administrador completo — acceso a todo',
    'operador': 'Operador — gestión diaria (no puede cambiar configuración de IA ni usuarios)',
    'readonly': 'Solo lectura — puede ver todo pero no modificar nada',
}

@app.route('/admin/usuarios')
@role_required('admin')
def admin_usuarios():
    db = get_db()
    usuarios = db.execute(
        "SELECT id, username, role, nombre, activo, created_at FROM usuarios WHERE club_id=1 ORDER BY id"
    ).fetchall()
    return render_template('admin/usuarios.html', usuarios=usuarios, roles=ROLES)

@app.route('/admin/usuarios/nuevo', methods=['POST'])
@role_required('admin')
def admin_usuario_nuevo():
    db  = get_db()
    u   = (request.form.get('username') or '').strip().lower()
    p   = (request.form.get('password') or '').strip()
    rol = request.form.get('role', 'operador')
    nom = (request.form.get('nombre') or '').strip()
    if not u or not p or rol not in ROLES:
        flash('Completá todos los campos')
        return redirect(url_for('admin_usuarios'))
    try:
        db.execute(
            "INSERT INTO usuarios (club_id, username, password_hash, role, nombre) VALUES (1,?,?,?,?)",
            (u, _hash_pw(p), rol, nom)
        )
        db.commit()
        flash(f'Usuario "{u}" creado correctamente')
    except Exception:
        flash(f'El usuario "{u}" ya existe')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/<int:uid>/editar', methods=['POST'])
@role_required('admin')
def admin_usuario_editar(uid):
    db  = get_db()
    rol = request.form.get('role', 'operador')
    nom = (request.form.get('nombre') or '').strip()
    activo = 1 if request.form.get('activo') else 0
    nueva_pw = (request.form.get('password') or '').strip()
    if rol not in ROLES:
        flash('Rol inválido')
        return redirect(url_for('admin_usuarios'))
    if nueva_pw:
        db.execute(
            "UPDATE usuarios SET role=?, nombre=?, activo=?, password_hash=? WHERE id=? AND club_id=1",
            (rol, nom, activo, _hash_pw(nueva_pw), uid)
        )
    else:
        db.execute(
            "UPDATE usuarios SET role=?, nombre=?, activo=? WHERE id=? AND club_id=1",
            (rol, nom, activo, uid)
        )
    db.commit()
    flash('Usuario actualizado')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuarios/<int:uid>/eliminar', methods=['POST'])
@role_required('admin')
def admin_usuario_eliminar(uid):
    db = get_db()
    usuario = db.execute("SELECT username FROM usuarios WHERE id=? AND club_id=1", (uid,)).fetchone()
    if usuario and usuario['username'] == ADMIN_USER:
        flash('No podés eliminar el usuario administrador principal')
        return redirect(url_for('admin_usuarios'))
    db.execute("DELETE FROM usuarios WHERE id=? AND club_id=1", (uid,))
    db.commit()
    flash('Usuario eliminado')
    return redirect(url_for('admin_usuarios'))

# ─── Fallback humano — escalación de tareas ───────────────────────────────────

@app.route('/admin/tareas/<int:task_id>/escalar', methods=['POST'])
@login_required
def admin_tarea_escalar(task_id):
    db     = get_db()
    task   = db.execute('SELECT * FROM agent_tasks WHERE id=?', (task_id,)).fetchone()
    if not task:
        flash('Tarea no encontrada')
        return redirect(url_for('admin_tareas'))
    motivo = (request.form.get('motivo') or 'El administrador necesita asistencia humana').strip()
    contexto = f"Agente: {task['agent_id']} | Tipo: {task['task_type']} | Recomendación: {task['recommendation']}"
    db.execute('''
        INSERT INTO escalaciones (club_id, agent_task_id, motivo, contexto)
        VALUES (1,?,?,?)
    ''', (task_id, motivo, contexto))
    db.execute(
        "UPDATE agent_tasks SET status='escalado', approval_status='escalado', execution_result=? WHERE id=?",
        (f'Escalado: {motivo}', task_id)
    )
    db.commit()
    # Notificar por email al admin
    try:
        _send_email_simple(
            MAIL_USER,
            f'[Germina] Tarea escalada — requiere atención humana',
            f'Una tarea del agente necesita tu atención:\n\n'
            f'Tipo: {task["task_type"]}\n'
            f'Recomendación original: {task["recommendation"]}\n\n'
            f'Motivo de escalación: {motivo}\n\n'
            f'Revisá en: germina-app.onrender.com/admin/tareas'
        )
    except Exception:
        pass
    flash('Tarea escalada. Vas a recibir un email con el detalle.')
    return redirect(url_for('admin_tareas'))

@app.route('/admin/escalaciones')
@login_required
def admin_escalaciones():
    db = get_db()
    escalaciones = db.execute('''
        SELECT e.*, at.agent_id, at.task_type, at.recommendation
        FROM escalaciones e
        LEFT JOIN agent_tasks at ON at.id = e.agent_task_id
        WHERE e.club_id=1 ORDER BY e.id DESC LIMIT 50
    ''').fetchall()
    abiertas = db.execute(
        "SELECT COUNT(*) FROM escalaciones WHERE club_id=1 AND estado='abierta'"
    ).fetchone()[0]
    return render_template('admin/escalaciones.html',
        escalaciones=escalaciones,
        abiertas=abiertas,
        agents=AGENTS,
    )

@app.route('/admin/escalaciones/<int:eid>/resolver', methods=['POST'])
@login_required
def admin_escalacion_resolver(eid):
    db = get_db()
    resolucion = (request.form.get('resolucion') or 'Resuelto').strip()
    db.execute('''
        UPDATE escalaciones SET estado='resuelta', resolucion=?,
            resolved_at=datetime('now','localtime'), asignado_a=?
        WHERE id=? AND club_id=1
    ''', (resolucion, current_username(), eid))
    db.commit()
    flash('Escalación resuelta')
    return redirect(url_for('admin_escalaciones'))

@app.route('/api/agentes/scan', methods=['POST', 'GET'])
def api_agentes_scan():
    secret = request.args.get('secret') or (request.get_json(silent=True) or {}).get('secret', '')
    if secret != CRM_PASS:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 403
    db = get_db()
    socios_n   = _agente_socios_scan(db)
    admin_n    = _agente_admin_scan(db)
    patrones_n = _agente_patrones_scan(db)
    repro_n    = _agente_reprocann_scan(db)
    total = socios_n + admin_n + patrones_n + repro_n
    return jsonify({'ok': True, 'tareas_generadas': total,
                    'agente_socios': socios_n, 'agente_admin': admin_n,
                    'agente_patrones': patrones_n, 'agente_reprocann': repro_n})

# ─── Importar socios CSV ──────────────────────────────────────────────────────

COLUMNAS_SOCIO = {
    'nombre': 'Nombre',
    'apellido': 'Apellido',
    'dni': 'DNI',
    'email': 'Email',
    'telefono': 'Teléfono',
    'fecha_nac': 'Fecha de nacimiento',
    'genero': 'Género',
    'barrio': 'Barrio',
    'provincia': 'Provincia',
    'tipo_socio': 'Tipo de socio',
    'diagnostico': 'Diagnóstico',
    'medico_prescriptor': 'Médico prescriptor',
    'como_nos_conocio': 'Cómo nos conoció',
}

@app.route('/admin/importar', methods=['GET', 'POST'])
@login_required
@limiter.limit('20 per hour', methods=['POST'])
def admin_importar():
    if request.method == 'GET':
        return render_template('admin/importar.html', columnas=COLUMNAS_SOCIO)

    archivo = request.files.get('archivo')
    if not archivo or not archivo.filename:
        flash('Seleccioná un archivo CSV o Excel')
        return redirect(url_for('admin_importar'))

    try:
        contenido = archivo.read().decode('utf-8-sig', errors='replace')
        sample = io.StringIO(contenido)
        dialect = csv.Sniffer().sniff(sample.read(2048), delimiters=',;\t')
        sample.seek(0)
        reader = csv.DictReader(sample, dialect=dialect)
        encabezados = reader.fieldnames or []
        filas = list(reader)[:5]
        session['_import_csv'] = contenido
        return render_template('admin/importar.html',
            columnas=COLUMNAS_SOCIO,
            encabezados=encabezados,
            filas=filas,
            modo='mapear')
    except Exception as e:
        flash(f'Error al leer el archivo: {e}')
        return redirect(url_for('admin_importar'))

@app.route('/admin/importar/confirmar', methods=['POST'])
@login_required
def admin_importar_confirmar():
    contenido = session.pop('_import_csv', None)
    if not contenido:
        flash('Sesión expirada. Subí el archivo de nuevo.')
        return redirect(url_for('admin_importar'))

    mapeo = {}
    for col in COLUMNAS_SOCIO:
        src = request.form.get(f'map_{col}', '').strip()
        if src:
            mapeo[col] = src

    if 'nombre' not in mapeo:
        flash('El campo Nombre es obligatorio para importar')
        return redirect(url_for('admin_importar'))

    try:
        sample  = io.StringIO(contenido)
        dialect = csv.Sniffer().sniff(sample.read(2048), delimiters=',;\t')
        sample.seek(0)
        reader  = csv.DictReader(sample, dialect=dialect)
        filas   = list(reader)
    except Exception as e:
        flash(f'Error al procesar CSV: {e}')
        return redirect(url_for('admin_importar'))

    db = get_db()
    importados = 0
    duplicados = 0
    errores = []

    for i, fila in enumerate(filas, 1):
        datos = {}
        for col, src in mapeo.items():
            datos[col] = (fila.get(src) or '').strip()

        dni = datos.get('dni', '')
        if dni:
            existe = db.execute('SELECT id FROM socios WHERE dni=?', (dni,)).fetchone()
            if existe:
                duplicados += 1
                continue

        tok = secrets.token_urlsafe(20)
        try:
            db.execute('''
                INSERT INTO socios (token, nombre, apellido, dni, email, telefono,
                    fecha_nac, genero, barrio, provincia, tipo_socio, diagnostico,
                    medico_prescriptor, como_nos_conocio, etapa)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'solicitud')
            ''', (tok,
                  datos.get('nombre',''), datos.get('apellido',''), datos.get('dni',''),
                  datos.get('email',''), datos.get('telefono',''), datos.get('fecha_nac',''),
                  datos.get('genero',''), datos.get('barrio',''),
                  datos.get('provincia','Buenos Aires'),
                  datos.get('tipo_socio','paciente'),
                  datos.get('diagnostico',''), datos.get('medico_prescriptor',''),
                  datos.get('como_nos_conocio','')))
            importados += 1
        except Exception as e:
            errores.append(f'Fila {i}: {e}')

    db.commit()
    _log_tarea(db, 'alta_socio', actor='Admin (importación masiva)', result=f'{importados} socios importados')
    db.commit()

    flash(f'Importación completada: {importados} socios nuevos, {duplicados} duplicados omitidos'
          + (f', {len(errores)} errores' if errores else ''))
    return redirect(url_for('admin_socios'))

# ─── Dashboard de ROI ────────────────────────────────────────────────────────

@app.route('/admin/roi')
@login_required
def admin_roi():
    db  = get_db()
    hoy = date.today().isoformat()
    mes = date.today().replace(day=1).isoformat()

    total_min     = db.execute("SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks").fetchone()[0] or 0
    total_tareas  = db.execute("SELECT COUNT(*) FROM roi_tasks").fetchone()[0]
    min_mes       = db.execute("SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks WHERE timestamp>=?", (mes,)).fetchone()[0] or 0
    min_hoy       = db.execute("SELECT COALESCE(SUM(human_minutes_saved),0) FROM roi_tasks WHERE DATE(timestamp)=?", (hoy,)).fetchone()[0] or 0
    costo_llm_total = db.execute("SELECT COALESCE(SUM(cost_usd),0) FROM agent_tasks").fetchone()[0] or 0

    por_tipo = db.execute('''
        SELECT r.task_type, COUNT(*) as cnt, COALESCE(SUM(r.human_minutes_saved),0) as minutos,
               tt.description, tt.human_minutes as min_unitario
        FROM roi_tasks r
        LEFT JOIN task_type_config tt ON tt.task_type = r.task_type
        GROUP BY r.task_type ORDER BY minutos DESC
    ''').fetchall()

    ultimos_7d = db.execute('''
        SELECT DATE(timestamp) as dia, COALESCE(SUM(human_minutes_saved),0) as minutos, COUNT(*) as tareas
        FROM roi_tasks
        WHERE timestamp >= date('now','-7 days')
        GROUP BY DATE(timestamp) ORDER BY dia ASC
    ''').fetchall()

    tareas_agente = db.execute('''
        SELECT agent_id, COUNT(*) as cnt, COALESCE(SUM(human_minutes_saved),0) as minutos
        FROM roi_tasks WHERE agent_id IS NOT NULL
        GROUP BY agent_id ORDER BY minutos DESC
    ''').fetchall()

    horas_totales    = round(total_min / 60, 1)
    valor_hora_usd   = 15
    valor_ahorrado   = round(horas_totales * valor_hora_usd, 0)

    return render_template('admin/roi.html',
        total_min=round(total_min),
        total_tareas=total_tareas,
        min_mes=round(min_mes),
        min_hoy=round(min_hoy),
        horas_totales=horas_totales,
        valor_ahorrado=valor_ahorrado,
        valor_hora_usd=valor_hora_usd,
        costo_llm_total=round(costo_llm_total, 4),
        por_tipo=por_tipo,
        ultimos_7d=ultimos_7d,
        tareas_agente=tareas_agente,
        agents=AGENTS,
    )

# ─── WhatsApp config ─────────────────────────────────────────────────────────

@app.route('/admin/whatsapp', methods=['GET', 'POST'])
@role_required('admin')
def admin_whatsapp():
    db = get_db()
    cfg = db.execute("SELECT * FROM whatsapp_config WHERE club_id=1").fetchone()

    if request.method == 'POST':
        phone_number_id      = request.form.get('phone_number_id','').strip()
        business_account_id  = request.form.get('business_account_id','').strip()
        access_token         = request.form.get('access_token','').strip()
        webhook_token        = request.form.get('webhook_verify_token','').strip()
        activo               = 1 if request.form.get('activo') else 0

        if cfg:
            db.execute('''
                UPDATE whatsapp_config SET phone_number_id=?, business_account_id=?,
                    access_token=?, webhook_verify_token=?, activo=?
                WHERE club_id=1
            ''', (phone_number_id, business_account_id, access_token, webhook_token, activo))
        else:
            db.execute('''
                INSERT INTO whatsapp_config (club_id, phone_number_id, business_account_id,
                    access_token, webhook_verify_token, activo)
                VALUES (1,?,?,?,?,?)
            ''', (phone_number_id, business_account_id, access_token, webhook_token, activo))
        db.commit()
        flash('Configuración de WhatsApp guardada')
        cfg = db.execute("SELECT * FROM whatsapp_config WHERE club_id=1").fetchone()

    mensajes_recientes = db.execute(
        "SELECT * FROM whatsapp_messages WHERE club_id=1 ORDER BY id DESC LIMIT 20"
    ).fetchall()

    return render_template('admin/whatsapp.html',
        cfg=cfg,
        mensajes=mensajes_recientes,
    )

@app.route('/webhook/whatsapp', methods=['GET', 'POST'])
@limiter.limit('120 per minute')
def webhook_whatsapp():
    db = get_db()
    cfg = db.execute("SELECT * FROM whatsapp_config WHERE club_id=1").fetchone()

    if request.method == 'GET':
        mode      = request.args.get('hub.mode')
        token     = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and cfg and token == cfg['webhook_verify_token']:
            return challenge, 200
        return 'Unauthorized', 403

    try:
        data = request.get_json(silent=True) or {}
        entry = (data.get('entry') or [{}])[0]
        changes = (entry.get('changes') or [{}])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        for msg in messages:
            from_num = msg.get('from', '')
            text     = (msg.get('text') or {}).get('body', '')
            wa_id    = msg.get('id', '')
            if text:
                socio = db.execute(
                    "SELECT id FROM socios WHERE telefono LIKE ?", (f'%{from_num[-8:]}%',)
                ).fetchone()
                db.execute('''
                    INSERT INTO whatsapp_messages
                    (club_id, socio_id, direction, from_number, message, wa_message_id)
                    VALUES (1,?,?,?,?,?)
                ''', (socio['id'] if socio else None, 'in', from_num, text, wa_id))
                _emit_event(db, 'WHATSAPP_RECEIVED',
                    entity_type='socio', entity_id=socio['id'] if socio else None,
                    payload={'from': from_num, 'message': text})
        db.commit()
    except Exception as e:
        print(f'[WEBHOOK WA] {e}')
    return jsonify({'status': 'ok'})

# ─── Onboarding self-service ──────────────────────────────────────────────────

@app.route('/nuevo-club', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'])
def nuevo_club():
    if request.method == 'GET':
        return render_template('nuevo_club.html')

    nombre    = request.form.get('nombre','').strip()
    email     = request.form.get('email','').strip()
    whatsapp  = request.form.get('whatsapp','').strip()
    pais      = request.form.get('pais','AR')

    if not nombre or not email:
        flash('Nombre del club y email son obligatorios')
        return render_template('nuevo_club.html', error=True)

    db = get_db()
    try:
        db.execute('''
            INSERT INTO clubs (nombre, pais, jurisdiction, email, whatsapp, plan)
            VALUES (?,?,?,?,?,'demo')
        ''', (nombre, pais, pais, email, whatsapp))
        db.commit()
    except Exception:
        pass

    _lead_to_email({'club': nombre, 'nombre': nombre, 'email': email,
                    'whatsapp': whatsapp, 'pais': pais, 'socios': '?'})
    db.execute("INSERT OR REPLACE INTO config (key,value) VALUES ('demo_club_nombre',?)", (nombre,))
    db.commit()
    return redirect(url_for('admin_dashboard'))

# ═══════════════════════════════════════════════════════════════════════════
#  GERMINA HQ — Panel de control interno (solo equipo Germina)
# ═══════════════════════════════════════════════════════════════════════════

def germina_login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('germina_admin'):
            return redirect(url_for('germina_login'))
        return f(*args, **kwargs)
    return wrapped

@app.route('/germina/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute; 20 per hour')
def germina_login():
    if session.get('germina_admin'):
        return redirect(url_for('germina_dashboard'))
    if request.method == 'POST':
        pw = (request.form.get('password') or '').strip()
        if pw == GERMINA_PASS:
            session['germina_admin'] = True
            return redirect(url_for('germina_dashboard'))
        flash('Contraseña incorrecta')
    return render_template('germina/login.html')

@app.route('/germina/logout')
def germina_logout():
    session.pop('germina_admin', None)
    session.pop('germina_soporte_club', None)
    session.pop('admin', None)
    session.pop('user_role', None)
    session.pop('user_nombre', None)
    return redirect(url_for('germina_login'))

@app.route('/germina/')
@germina_login_required
def germina_index():
    return redirect(url_for('germina_dashboard'))

@app.route('/germina/dashboard')
@germina_login_required
def germina_dashboard():
    db = get_db()
    clubs_raw = db.execute("SELECT * FROM clubs ORDER BY created_at DESC").fetchall()

    mes_inicio = date.today().replace(day=1).isoformat()
    clubs_data = []
    for c in clubs_raw:
        cid = c['id']
        # socios y dispensaciones no tienen club_id en el esquema actual (un club por DB)
        total_socios = db.execute("SELECT COUNT(*) FROM socios").fetchone()[0]
        activos = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]
        disp_mes = db.execute(
            "SELECT COUNT(*) FROM dispensaciones WHERE fecha>=?", (mes_inicio,)
        ).fetchone()[0]
        tareas_mes = db.execute(
            "SELECT COUNT(*) FROM agent_tasks WHERE club_id=? AND timestamp>=?",
            (cid, mes_inicio)
        ).fetchone()[0]
        try:
            created = datetime.strptime(c['created_at'][:10], '%Y-%m-%d')
            dias = (datetime.now() - created).days
        except Exception:
            dias = 0

        ultimo = c['ultimo_acceso']
        if ultimo:
            try:
                ultima_dt = datetime.strptime(ultimo[:16], '%Y-%m-%d %H:%M')
                dias_sin_acceso = (datetime.now() - ultima_dt).days
            except Exception:
                dias_sin_acceso = None
        else:
            dias_sin_acceso = None

        score = min(100, activos * 4 + disp_mes * 3 + tareas_mes * 2)
        churn_riesgo = dias_sin_acceso is not None and dias_sin_acceso >= 7

        clubs_data.append({
            'club': c,
            'total_socios': total_socios,
            'activos': activos,
            'disp_mes': disp_mes,
            'tareas_mes': tareas_mes,
            'dias': dias,
            'ultimo': ultimo,
            'dias_sin_acceso': dias_sin_acceso,
            'score': score,
            'churn_riesgo': churn_riesgo,
        })

    total_clubs       = len(clubs_raw)
    clubs_activos_n   = sum(1 for d in clubs_data if d['score'] > 0 and d['club']['activo'])
    total_socios_g    = sum(d['total_socios'] for d in clubs_data)
    total_disp_g      = sum(d['disp_mes'] for d in clubs_data)
    en_riesgo_n       = sum(1 for d in clubs_data if d['churn_riesgo'])

    return render_template('germina/dashboard.html',
        clubs_data=clubs_data,
        planes=PLANES,
        total_clubs=total_clubs,
        clubs_activos_n=clubs_activos_n,
        total_socios_g=total_socios_g,
        total_disp_g=total_disp_g,
        en_riesgo_n=en_riesgo_n,
    )

@app.route('/germina/club/<int:club_id>')
@germina_login_required
def germina_club(club_id):
    db = get_db()
    club = db.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    if not club:
        flash('Club no encontrado')
        return redirect(url_for('germina_dashboard'))

    mes_inicio = date.today().replace(day=1).isoformat()

    # socios/dispensaciones/cultivos no tienen club_id (un club por instancia de DB)
    total_socios = db.execute("SELECT COUNT(*) FROM socios").fetchone()[0]
    activos      = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]

    por_etapa = {e: db.execute(
        "SELECT COUNT(*) FROM socios WHERE etapa=?", (e,)
    ).fetchone()[0] for e in ETAPAS}

    row = db.execute(
        "SELECT COUNT(*), COALESCE(SUM(gramos),0) FROM dispensaciones WHERE fecha>=?",
        (mes_inicio,)
    ).fetchone()
    disp_count, disp_g = row[0], round(row[1], 1)

    cosechado_g = db.execute(
        "SELECT COALESCE(SUM(co.peso_seco_g),0) FROM cosechas co "
        "JOIN cultivos cu ON cu.id=co.cultivo_id"
    ).fetchone()[0]

    cultivos_activos = db.execute(
        "SELECT COUNT(*) FROM cultivos WHERE estado='activo'"
    ).fetchone()[0]

    tareas_total = db.execute("SELECT COUNT(*) FROM agent_tasks WHERE club_id=?", (club_id,)).fetchone()[0]
    tareas_mes   = db.execute(
        "SELECT COUNT(*) FROM agent_tasks WHERE club_id=? AND timestamp>=?",
        (club_id, mes_inicio)
    ).fetchone()[0]

    actividad_semanal = []
    for i in range(7, -1, -1):
        desde = (date.today() - timedelta(weeks=i+1)).isoformat()
        hasta = (date.today() - timedelta(weeks=i)).isoformat()
        n = db.execute(
            "SELECT COUNT(*) FROM dispensaciones WHERE fecha>=? AND fecha<?",
            (desde, hasta)
        ).fetchone()[0]
        actividad_semanal.append({'semana': f"S-{i}", 'n': n})
    max_act = max((a['n'] for a in actividad_semanal), default=1) or 1

    actividades = db.execute(
        "SELECT * FROM audit_log WHERE club_id=? ORDER BY id DESC LIMIT 25", (club_id,)
    ).fetchall()

    return render_template('germina/club.html',
        club=club,
        planes=PLANES,
        total_socios=total_socios,
        activos=activos,
        por_etapa=por_etapa,
        etapa_label=ETAPA_LABEL,
        disp_count=disp_count,
        disp_g=disp_g,
        cosechado_g=round(cosechado_g, 1),
        cultivos_activos=cultivos_activos,
        tareas_total=tareas_total,
        tareas_mes=tareas_mes,
        actividad_semanal=actividad_semanal,
        max_act=max_act,
        actividades=actividades,
    )

@app.route('/germina/club/<int:club_id>/plan', methods=['POST'])
@germina_login_required
def germina_club_plan(club_id):
    db = get_db()
    plan           = request.form.get('plan', 'demo')
    plan_vence     = request.form.get('plan_vence', '').strip() or None
    activo         = 1 if request.form.get('activo') else 0
    notas          = (request.form.get('notas_internas') or '').strip()
    contacto       = (request.form.get('contacto_nombre') or '').strip()
    db.execute(
        "UPDATE clubs SET plan=?, plan_vence=?, activo=?, notas_internas=?, contacto_nombre=? WHERE id=?",
        (plan, plan_vence, activo, notas, contacto, club_id)
    )
    db.commit()
    flash('Club actualizado correctamente')
    return redirect(url_for('germina_club', club_id=club_id))

@app.route('/germina/club/<int:club_id>/acceder')
@germina_login_required
def germina_soporte_acceder(club_id):
    db = get_db()
    club = db.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    if not club:
        return redirect(url_for('germina_dashboard'))
    session['germina_soporte_club'] = {'id': club_id, 'nombre': club['nombre']}
    session['admin']      = True
    session['user_role']  = 'admin'
    session['user_nombre'] = f'Soporte [{club["nombre"]}]'
    session['user_id']    = 0
    return redirect(url_for('admin_dashboard'))

@app.route('/germina/salir-soporte')
def germina_salir_soporte():
    session.pop('germina_soporte_club', None)
    session.pop('admin', None)
    session.pop('user_role', None)
    session.pop('user_nombre', None)
    session.pop('user_id', None)
    if session.get('germina_admin'):
        return redirect(url_for('germina_dashboard'))
    return redirect(url_for('germina_login'))


@app.route('/germina/datos')
@germina_login_required
def germina_datos():
    db = get_db()
    hoy = date.today()
    mes_inicio = hoy.replace(day=1).isoformat()

    # KPIs globales
    total_socios    = db.execute("SELECT COUNT(*) FROM socios").fetchone()[0]
    total_activos   = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]
    row = db.execute("SELECT COUNT(*), COALESCE(SUM(gramos),0) FROM dispensaciones").fetchone()
    total_disp, total_g = row[0], round(row[1], 1)
    prom_g = round(total_g / total_activos, 1) if total_activos else 0

    # Top variedades (por gramos dispensados)
    top_variedades = db.execute("""
        SELECT variedad, COUNT(*) n, COALESCE(SUM(gramos),0) gramos_total
        FROM dispensaciones GROUP BY variedad ORDER BY gramos_total DESC LIMIT 10
    """).fetchall()

    # Evolución mensual — últimos 12 meses
    evolucion = []
    for i in range(11, -1, -1):
        d = hoy.replace(day=1) - timedelta(days=i*28)
        mes_str = d.strftime('%Y-%m')
        n = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE strftime('%Y-%m',fecha)=?",
            (mes_str,)).fetchone()[0]
        evolucion.append({'mes': d.strftime('%b %y'), 'gramos': round(n, 1)})

    # Distribución por motivo_consumo
    motivos = db.execute("""
        SELECT COALESCE(motivo_consumo,'no_informado') motivo, COUNT(*) n
        FROM socios GROUP BY motivo ORDER BY n DESC
    """).fetchall()

    # Distribución por tipo_socio
    tipos = db.execute("""
        SELECT COALESCE(tipo_socio,'no_informado') tipo, COUNT(*) n
        FROM socios GROUP BY tipo ORDER BY n DESC
    """).fetchall()

    # Top diagnósticos / condiciones
    diagnosticos = db.execute("""
        SELECT diagnostico, COUNT(*) n FROM socios
        WHERE diagnostico IS NOT NULL AND diagnostico != ''
        GROUP BY diagnostico ORDER BY n DESC LIMIT 12
    """).fetchall()

    # Distribución por método de consumo
    metodos = db.execute("""
        SELECT COALESCE(metodo_consumo,'no_informado') metodo, COUNT(*) n
        FROM socios WHERE metodo_consumo IS NOT NULL AND metodo_consumo != ''
        GROUP BY metodo ORDER BY n DESC
    """).fetchall()

    # Distribución por frecuencia de uso
    frecuencias = db.execute("""
        SELECT COALESCE(frecuencia_uso,'no_informado') frecuencia, COUNT(*) n
        FROM socios WHERE frecuencia_uso IS NOT NULL AND frecuencia_uso != ''
        GROUP BY frecuencia ORDER BY n DESC
    """).fetchall()

    # Distribución por género
    generos = db.execute("""
        SELECT COALESCE(genero,'no_informado') genero, COUNT(*) n
        FROM socios GROUP BY genero ORDER BY n DESC
    """).fetchall()

    # Distribución por provincia (top 10)
    provincias = db.execute("""
        SELECT COALESCE(provincia,'no_informada') provincia, COUNT(*) n
        FROM socios GROUP BY provincia ORDER BY n DESC LIMIT 10
    """).fetchall()

    # Distribución por rango etario
    rangos_etarios = []
    rangos = [('18-25',18,25),('26-35',26,35),('36-45',36,45),('46-55',46,55),('55+',55,120)]
    for label, min_a, max_a in rangos:
        n = db.execute("""
            SELECT COUNT(*) FROM socios
            WHERE fecha_nac IS NOT NULL AND fecha_nac != ''
            AND (strftime('%Y','now') - strftime('%Y',fecha_nac)) >= ?
            AND (strftime('%Y','now') - strftime('%Y',fecha_nac)) < ?
        """, (min_a, max_a)).fetchone()[0]
        rangos_etarios.append({'label': label, 'n': n})

    max_var = max((r['gramos_total'] for r in top_variedades), default=1) or 1
    max_evo = max((e['gramos'] for e in evolucion), default=1) or 1

    # Tabla interna completa con dispensaciones por socio
    socios_raw = db.execute("SELECT * FROM socios ORDER BY id").fetchall()
    socios_completos = []
    for s in socios_raw:
        n_disp = db.execute(
            "SELECT COUNT(*) FROM dispensaciones WHERE socio_id=?", (s['id'],)).fetchone()[0]
        socios_completos.append({**dict(s), 'n_disp': n_disp})

    return render_template('germina/datos.html',
        total_socios=total_socios, total_activos=total_activos,
        total_disp=total_disp, total_g=total_g, prom_g=prom_g,
        top_variedades=top_variedades, max_var=max_var,
        evolucion=evolucion, max_evo=max_evo,
        motivos=motivos, tipos=tipos, diagnosticos=diagnosticos,
        metodos=metodos, frecuencias=frecuencias,
        generos=generos, provincias=provincias, rangos_etarios=rangos_etarios,
        socios_completos=socios_completos,
    )


@app.route('/germina/datos/export-completo')
@germina_login_required
def germina_datos_export_completo():
    db = get_db()
    hoy = date.today().isoformat()
    socios = db.execute("SELECT * FROM socios ORDER BY id").fetchall()

    output = io.StringIO()
    w = csv.writer(output)
    w.writerow([
        'id','nombre','apellido','dni','email','telefono','fecha_nac','genero',
        'barrio','provincia','tipo_socio','diagnostico','patologia_especifica',
        'tiempo_condicion','medico_prescriptor','especialidad_medico','tiene_receta',
        'experiencia_cannabis','metodo_consumo','frecuencia_uso','motivo_consumo',
        'dosis_habitual_g','como_nos_conocio','referido_por','etapa',
        'gramos_historico','num_dispensaciones','variedad_principal',
        'dias_en_club','created_at'
    ])
    for s in socios:
        dias = ''
        if s['created_at']:
            try: dias = (date.today() - date.fromisoformat(s['created_at'][:10])).days
            except: pass

        row_d = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=?",
            (s['id'],)).fetchone()
        n_disp, g_hist = row_d[0], round(row_d[1], 1)

        var_row = db.execute(
            "SELECT variedad FROM dispensaciones WHERE socio_id=? GROUP BY variedad ORDER BY SUM(gramos) DESC LIMIT 1",
            (s['id'],)).fetchone()
        variedad_p = var_row[0] if var_row else ''

        w.writerow([
            s['id'], s['nombre'] or '', s['apellido'] or '', s['dni'] or '',
            s['email'] or '', s['telefono'] or '', s['fecha_nac'] or '',
            s['genero'] or '', s['barrio'] or '', s['provincia'] or '',
            s['tipo_socio'] or '', s['diagnostico'] or '', s['patologia_especifica'] or '',
            s['tiempo_condicion'] or '', s['medico_prescriptor'] or '',
            s['especialidad_medico'] or '', s['tiene_receta'] or '',
            s['experiencia_cannabis'] or '', s['metodo_consumo'] or '',
            s['frecuencia_uso'] or '', s['motivo_consumo'] or '',
            s['dosis_habitual_g'] or '', s['como_nos_conocio'] or '',
            s['referido_por'] or '', s['etapa'] or '',
            g_hist, n_disp, variedad_p, dias, s['created_at'] or ''
        ])

    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=germina_datos_completos_{hoy}.csv'
    return resp


@app.route('/germina/datos/export')
@germina_login_required
def germina_datos_export():
    db = get_db()
    hoy = date.today().isoformat()
    socios = db.execute("SELECT * FROM socios").fetchall()

    output = io.StringIO()
    w = csv.writer(output)
    w.writerow([
        'id_anonimo','rango_edad','genero','provincia','tipo_socio',
        'diagnostico','patologia_especifica','motivo_consumo',
        'metodo_consumo','frecuencia_uso','dosis_habitual_g',
        'tiene_receta','experiencia_cannabis',
        'gramos_historico','num_dispensaciones','variedad_principal',
        'dias_en_club','etapa_actual'
    ])
    for s in socios:
        # calcular edad
        rango = ''
        if s['fecha_nac']:
            try:
                edad = (date.today() - date.fromisoformat(s['fecha_nac'][:10])).days // 365
                if edad < 26: rango = '18-25'
                elif edad < 36: rango = '26-35'
                elif edad < 46: rango = '36-45'
                elif edad < 56: rango = '46-55'
                else: rango = '55+'
            except Exception: rango = ''

        # días en el club
        dias = ''
        if s['created_at']:
            try:
                dias = (date.today() - date.fromisoformat(s['created_at'][:10])).days
            except Exception: pass

        # dispensaciones
        row_d = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(gramos),0) FROM dispensaciones WHERE socio_id=?",
            (s['id'],)).fetchone()
        n_disp, g_hist = row_d[0], round(row_d[1], 1)

        # variedad principal
        var_row = db.execute(
            "SELECT variedad FROM dispensaciones WHERE socio_id=? GROUP BY variedad ORDER BY SUM(gramos) DESC LIMIT 1",
            (s['id'],)).fetchone()
        variedad_p = var_row[0] if var_row else ''

        w.writerow([
            f"SOC-{s['id']:04d}", rango, s['genero'] or '', s['provincia'] or '',
            s['tipo_socio'] or '', s['diagnostico'] or '', s['patologia_especifica'] or '',
            s['motivo_consumo'] or '', s['metodo_consumo'] or '', s['frecuencia_uso'] or '',
            s['dosis_habitual_g'] or '', s['tiene_receta'] or '', s['experiencia_cannabis'] or '',
            g_hist, n_disp, variedad_p, dias, s['etapa'] or ''
        ])

    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=germina_datos_{hoy}.csv'
    return resp


@app.route('/admin/configuracion', methods=['GET', 'POST'])
@login_required
def admin_configuracion():
    db = get_db()
    club = db.execute('SELECT * FROM clubs WHERE id=1').fetchone()
    msg = None
    if request.method == 'POST':
        campos = {
            'nombre': request.form.get('nombre', '').strip(),
            'email': request.form.get('email', '').strip(),
            'whatsapp': request.form.get('whatsapp', '').strip(),
            'cbu': request.form.get('cbu', '').strip(),
            'alias_bancario': request.form.get('alias_bancario', '').strip(),
            'mp_link': request.form.get('mp_link', '').strip(),
        }
        if club:
            db.execute(
                'UPDATE clubs SET nombre=?,email=?,whatsapp=?,cbu=?,alias_bancario=?,mp_link=? WHERE id=1',
                (campos['nombre'], campos['email'], campos['whatsapp'],
                 campos['cbu'] or None, campos['alias_bancario'] or None, campos['mp_link'] or None))
        else:
            db.execute(
                'INSERT INTO clubs (id,nombre,email,whatsapp,cbu,alias_bancario,mp_link) VALUES (1,?,?,?,?,?,?)',
                (campos['nombre'], campos['email'], campos['whatsapp'],
                 campos['cbu'] or None, campos['alias_bancario'] or None, campos['mp_link'] or None))
        db.commit()
        club = db.execute('SELECT * FROM clubs WHERE id=1').fetchone()
        msg = 'Configuración guardada correctamente.'
    return render_template('admin/configuracion.html', club=club, msg=msg)


@app.route('/admin/reprocann', methods=['GET', 'POST'])
@login_required
def admin_reprocann():
    db = get_db()
    from datetime import date, timedelta

    # Determinar semestre actual y anterior
    hoy = date.today()
    if hoy.month <= 6:
        sem_actual   = f"{hoy.year}-S1"
        desde_actual = date(hoy.year, 1, 1).isoformat()
        hasta_actual = date(hoy.year, 6, 30).isoformat()
        sem_anterior = f"{hoy.year-1}-S2"
        desde_ant    = date(hoy.year-1, 7, 1).isoformat()
        hasta_ant    = date(hoy.year-1, 12, 31).isoformat()
    else:
        sem_actual   = f"{hoy.year}-S2"
        desde_actual = date(hoy.year, 7, 1).isoformat()
        hasta_actual = date(hoy.year, 12, 31).isoformat()
        sem_anterior = f"{hoy.year}-S1"
        desde_ant    = date(hoy.year, 1, 1).isoformat()
        hasta_ant    = date(hoy.year, 6, 30).isoformat()

    # Seleccionar semestre a mostrar
    sem_sel = request.args.get('semestre', sem_actual)
    if sem_sel == sem_actual:
        desde, hasta = desde_actual, hasta_actual
    else:
        desde, hasta = desde_ant, hasta_ant

    informe = None
    msg = None

    if request.method == 'POST':
        accion = request.form.get('accion', 'generar')

        if accion == 'generar':
            # Recolectar datos del período
            club = db.execute('SELECT * FROM clubs WHERE id=1').fetchone()
            nombre_club = club['nombre'] if club else 'Cannabis Social Club'

            socios_activos = db.execute(
                "SELECT nombre, apellido, dni, diagnostico, medico_prescriptor, tipo_socio "
                "FROM socios WHERE etapa='activo' ORDER BY apellido"
            ).fetchall()
            total_socios = len(socios_activos)

            # Diagnósticos agrupados
            diagn_raw = db.execute(
                "SELECT diagnostico, COUNT(*) as cnt FROM socios WHERE etapa='activo' AND diagnostico IS NOT NULL GROUP BY diagnostico ORDER BY cnt DESC"
            ).fetchall()
            diagnosticos = [{'nombre': d['diagnostico'], 'cantidad': d['cnt']} for d in diagn_raw]

            # Médicos prescriptores
            medicos_raw = db.execute(
                "SELECT medico_prescriptor, COUNT(*) as cnt FROM socios WHERE etapa='activo' AND medico_prescriptor IS NOT NULL GROUP BY medico_prescriptor ORDER BY cnt DESC"
            ).fetchall()
            medicos = [{'nombre': m['medico_prescriptor'], 'pacientes': m['cnt']} for m in medicos_raw]

            # Producción: cosechas en el período
            cosechas_raw = db.execute('''
                SELECT cu.variedad, COUNT(co.id) as num_cosechas,
                       COALESCE(SUM(co.peso_seco_g),0) as total_seco_g,
                       COALESCE(SUM(co.peso_humedo_g),0) as total_humedo_g,
                       COALESCE(SUM(co.num_plantas),0) as plantas
                FROM cosechas co JOIN cultivos cu ON cu.id=co.cultivo_id
                WHERE co.fecha>=? AND co.fecha<=?
                GROUP BY cu.variedad ORDER BY total_seco_g DESC
            ''', (desde, hasta)).fetchall()
            produccion = [{'variedad': c['variedad'], 'cosechas': c['num_cosechas'],
                           'gramos_secos': round(c['total_seco_g'],1),
                           'gramos_humedos': round(c['total_humedo_g'],1),
                           'plantas': c['plantas']} for c in cosechas_raw]
            total_produccion_g = sum(p['gramos_secos'] for p in produccion)

            # Distribución: pedidos+dispensaciones en el período
            dist_raw = db.execute('''
                SELECT variedad, COALESCE(SUM(gramos),0) as total_g, COUNT(*) as cant
                FROM pedidos WHERE estado='entregado' AND fecha_pedido>=? AND fecha_pedido<=?
                GROUP BY variedad
            ''', (desde, hasta)).fetchall()
            disp_raw = db.execute('''
                SELECT variedad, COALESCE(SUM(gramos),0) as total_g, COUNT(*) as cant
                FROM dispensaciones WHERE fecha>=? AND fecha<=?
                GROUP BY variedad
            ''', (desde, hasta)).fetchall()
            dist_dict = {}
            for r in dist_raw:
                dist_dict[r['variedad']] = {'variedad': r['variedad'], 'gramos': r['total_g'], 'entregas': r['cant']}
            for r in disp_raw:
                v = r['variedad']
                if v in dist_dict:
                    dist_dict[v]['gramos'] += r['total_g']
                    dist_dict[v]['entregas'] += r['cant']
                else:
                    dist_dict[v] = {'variedad': v, 'gramos': r['total_g'], 'entregas': r['cant']}
            distribucion = sorted(dist_dict.values(), key=lambda x: x['gramos'], reverse=True)
            total_distribucion_g = sum(d['gramos'] for d in distribucion)

            # Stock actual
            stock_actual = []
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
                disp_g = round((row['total_g'] or 0) - entregado - reservado, 1)
                stock_actual.append({'variedad': v, 'disponible_g': disp_g})

            # Cultivos activos
            cultivos_activos = db.execute(
                "SELECT COUNT(*) FROM cultivos WHERE estado='activo'"
            ).fetchone()[0]
            plantas_activas = db.execute(
                "SELECT COALESCE(SUM(num_plantas),0) FROM cultivos WHERE estado='activo'"
            ).fetchone()[0]

            # Generar texto con IA
            socios_texto = '\n'.join([f"  - {s['apellido']}, {s['nombre']} (DNI: {s['dni'] or 'N/D'}) — {s['diagnostico'] or 'sin diagnóstico'} — Dr/a. {s['medico_prescriptor'] or 'sin prescriptor'}" for s in socios_activos[:20]])
            if len(socios_activos) > 20:
                socios_texto += f"\n  ... y {len(socios_activos)-20} socios más"

            prompt = (
                f"Sos el asesor legal de un Cannabis Social Club en Argentina, registrado bajo la Ley 27.350 y el Decreto 883/2020.\n"
                f"Generá el INFORME SEMESTRAL para el REPROCANN correspondiente al período {desde} al {hasta} ({sem_sel}).\n\n"
                f"DATOS DEL CLUB: {nombre_club}\n"
                f"PERÍODO: {desde} al {hasta}\n\n"
                f"SOCIOS ACTIVOS ({total_socios}):\n{socios_texto}\n\n"
                f"PRODUCCIÓN DEL PERÍODO:\n"
                + '\n'.join([f"  - {p['variedad']}: {p['gramos_secos']}g secos ({p['cosechas']} cosechas, {p['plantas']} plantas)" for p in produccion])
                + f"\n  TOTAL: {total_produccion_g:.1f}g\n\n"
                f"DISTRIBUCIÓN DEL PERÍODO:\n"
                + '\n'.join([f"  - {d['variedad']}: {d['gramos']:.1f}g en {d['entregas']} entregas" for d in distribucion])
                + f"\n  TOTAL DISTRIBUIDO: {total_distribucion_g:.1f}g\n\n"
                f"STOCK ACTUAL:\n"
                + '\n'.join([f"  - {s['variedad']}: {s['disponible_g']}g disponibles" for s in stock_actual])
                + f"\n\nCULTIVOS ACTIVOS: {cultivos_activos} cultivos, {plantas_activas} plantas en curso.\n\n"
                f"Redactá el informe completo con las secciones que exige el REPROCANN:\n"
                f"1. Datos del club\n2. Registro de pacientes del período\n3. Diagnósticos y médicos prescriptores\n"
                f"4. Datos de producción (cultivo y cosecha)\n5. Datos de distribución\n6. Stock actual\n"
                f"7. Declaración de cumplimiento normativo\n\n"
                f"Formato: texto formal, en español, listo para presentar ante autoridad sanitaria argentina."
            )

            try:
                contenido, tin, tout, cost = _llamar_llm(prompt, 1500)
            except Exception as e:
                contenido = f"[Error al generar con IA: {e}]\n\nINFORME SEMESTRAL {sem_sel}\nClub: {nombre_club}\nSocios activos: {total_socios}\nProducción total: {total_produccion_g:.1f}g\nDistribución total: {total_distribucion_g:.1f}g"

            # Guardar en DB (reemplazar si ya existe)
            ya = db.execute("SELECT id FROM reprocann_reports WHERE club_id=1 AND semestre=?", (sem_sel,)).fetchone()
            if ya:
                db.execute("UPDATE reprocann_reports SET contenido=?, generado_at=datetime('now','localtime'), status='generado' WHERE id=?",
                           (contenido, ya['id']))
            else:
                db.execute("INSERT INTO reprocann_reports (club_id,semestre,fecha_desde,fecha_hasta,contenido,status) VALUES (1,?,?,?,?,'generado')",
                           (sem_sel, desde, hasta, contenido))
            db.commit()
            msg = f'Informe {sem_sel} generado con IA.'

        elif accion == 'cerrar':
            db.execute("UPDATE reprocann_reports SET status='presentado' WHERE club_id=1 AND semestre=?", (sem_sel,))
            db.commit()
            msg = f'Informe {sem_sel} marcado como presentado.'

    informe = db.execute(
        "SELECT * FROM reprocann_reports WHERE club_id=1 AND semestre=? ORDER BY generado_at DESC LIMIT 1",
        (sem_sel,)).fetchone()

    historial = db.execute(
        "SELECT semestre, generado_at, status FROM reprocann_reports WHERE club_id=1 ORDER BY semestre DESC LIMIT 10"
    ).fetchall()

    return render_template('admin/reprocann.html',
        sem_actual=sem_actual, sem_anterior=sem_anterior, sem_sel=sem_sel,
        desde=desde, hasta=hasta, informe=informe, historial=historial, msg=msg)


# ─── Panel de Cumplimiento REPROCANN (checklist 9 documentos A-I) ────────────

@app.route('/admin/cumplimiento', methods=['GET','POST'])
@login_required
def admin_cumplimiento():
    db = get_db()
    msg = None

    if request.method == 'POST':
        doc_id  = request.form.get('doc_id', type=int)
        estado  = request.form.get('estado','pendiente')
        fecha_p = request.form.get('fecha_presentacion','').strip() or None
        fecha_v = request.form.get('fecha_vencimiento','').strip() or None
        notas   = request.form.get('notas','').strip() or None
        if doc_id:
            db.execute('''UPDATE reprocann_docs SET estado=?, fecha_presentacion=?,
                fecha_vencimiento=?, notas=?, updated_at=datetime('now','localtime')
                WHERE id=? AND club_id=1''',
                (estado, fecha_p, fecha_v, notas, doc_id))
            db.commit()
            msg = 'Documento actualizado.'

    docs = db.execute("SELECT * FROM reprocann_docs WHERE club_id=1 ORDER BY tipo_doc").fetchall()

    # Calcular score de cumplimiento
    total = len(docs)
    presentados = sum(1 for d in docs if d['estado'] == 'presentado')
    pct = round(presentados / total * 100) if total else 0

    # Socios activos con credencial REPROCANN vigente
    socios_reprocann = db.execute('''
        SELECT nombre, apellido, reprocann_estado, reprocann_vencimiento, plantas_autorizadas
        FROM socios WHERE etapa='activo' AND reprocann_codigo IS NOT NULL AND reprocann_codigo != ''
        ORDER BY apellido
    ''').fetchall()
    total_socios_activos = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]
    socios_en_reprocann  = len(socios_reprocann)

    # m² totales en cultivos activos
    m2_total_int = db.execute("SELECT COALESCE(SUM(m2_interior),0) FROM cultivos WHERE estado='activo'").fetchone()[0] or 0
    m2_total_ext = db.execute("SELECT COALESCE(SUM(m2_exterior),0) FROM cultivos WHERE estado='activo'").fetchone()[0] or 0

    return render_template('admin/cumplimiento.html',
        docs=docs, pct=pct, presentados=presentados, total_docs=total,
        socios_reprocann=socios_reprocann,
        total_socios_activos=total_socios_activos,
        socios_en_reprocann=socios_en_reprocann,
        m2_total_int=m2_total_int, m2_total_ext=m2_total_ext,
        msg=msg)


# ─── Generador de Carta de Porte ─────────────────────────────────────────────

@app.route('/admin/carta-porte', methods=['GET','POST'])
@login_required
def admin_carta_porte():
    db = get_db()
    msg = None
    carta_nueva = None

    if request.method == 'POST':
        accion = request.form.get('accion','crear')

        if accion == 'crear':
            # Número autoincremental
            ultimo = db.execute("SELECT MAX(id) FROM cartas_porte WHERE club_id=1").fetchone()[0] or 0
            numero = f"CP-{date.today().year}-{ultimo+1:04d}"

            db.execute('''INSERT INTO cartas_porte
                (club_id, pedido_id, numero, fecha_emision, tipo_material, cantidad, unidad,
                 socio_nombre, socio_dni, direccion_destino,
                 transportista_nombre, transportista_dni, vehiculo_patente,
                 ruta, fecha_traslado, hora_inicio, hora_fin_estimada)
                VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                request.form.get('pedido_id') or None,
                numero,
                date.today().isoformat(),
                request.form.get('tipo_material','flores_secas'),
                float(request.form.get('cantidad', 0) or 0),
                'g' if request.form.get('tipo_material') == 'flores_secas' else 'ml',
                request.form.get('socio_nombre','').strip() or None,
                request.form.get('socio_dni','').strip() or None,
                request.form.get('direccion_destino','').strip() or None,
                request.form.get('transportista_nombre','').strip() or None,
                request.form.get('transportista_dni','').strip() or None,
                request.form.get('vehiculo_patente','').strip() or None,
                request.form.get('ruta','').strip() or None,
                request.form.get('fecha_traslado','').strip() or None,
                request.form.get('hora_inicio','').strip() or None,
                request.form.get('hora_fin_estimada','').strip() or None,
            ))
            db.commit()
            carta_nueva = db.execute("SELECT * FROM cartas_porte WHERE numero=?", (numero,)).fetchone()
            msg = f'Carta de Porte {numero} generada.'

        elif accion == 'anular':
            carta_id = request.form.get('carta_id', type=int)
            if carta_id:
                db.execute("UPDATE cartas_porte SET estado='anulada' WHERE id=? AND club_id=1", (carta_id,))
                db.commit()
                msg = 'Carta anulada.'

    cartas = db.execute('''
        SELECT * FROM cartas_porte WHERE club_id=1 ORDER BY created_at DESC LIMIT 50
    ''').fetchall()
    socios_activos = db.execute('''
        SELECT id, nombre, apellido, dni, direccion FROM socios WHERE etapa='activo' ORDER BY apellido
    ''').fetchall()
    pedidos_en_camino = db.execute('''
        SELECT p.id, p.codigo, p.variedad, p.gramos, p.tipo_entrega, p.direccion_entrega,
               s.nombre, s.apellido, s.dni
        FROM pedidos p JOIN socios s ON s.id=p.socio_id
        WHERE p.estado IN ('preparando','en_camino') AND p.tipo_entrega='delivery'
        ORDER BY p.fecha_pedido DESC
    ''').fetchall()
    club = db.execute("SELECT * FROM clubs WHERE id=1").fetchone()

    return render_template('admin/carta-porte.html',
        cartas=cartas, socios_activos=socios_activos,
        pedidos_en_camino=pedidos_en_camino, club=club,
        carta_nueva=carta_nueva, msg=msg)


# ─── Informe Trimestral Director Médico ──────────────────────────────────────

@app.route('/admin/informe-director', methods=['GET','POST'])
@login_required
def admin_informe_director():
    db = get_db()
    from datetime import date, timedelta
    msg = None
    informe_texto = None

    hoy = date.today()
    # Trimestres del año
    trimestres = [
        ('T1', f'{hoy.year}-01-01', f'{hoy.year}-03-31'),
        ('T2', f'{hoy.year}-04-01', f'{hoy.year}-06-30'),
        ('T3', f'{hoy.year}-07-01', f'{hoy.year}-09-30'),
        ('T4', f'{hoy.year}-10-01', f'{hoy.year}-12-31'),
    ]
    trim_actual = f'T{((hoy.month-1)//3)+1}'
    trim_sel = request.args.get('trimestre', trim_actual)
    desde_t, hasta_t = next(((d, h) for t,d,h in trimestres if t == trim_sel), (trimestres[0][1], trimestres[0][2]))

    if request.method == 'POST':
        director = request.form.get('director_nombre','Dr./Dra.').strip()
        matricula = request.form.get('matricula','').strip()

        # Recolectar datos del trimestre
        club = db.execute("SELECT * FROM clubs WHERE id=1").fetchone()
        nombre_club = club['nombre'] if club else 'Cannabis Social Club'

        socios_activos = db.execute(
            "SELECT nombre, apellido, dni, diagnostico, medico_prescriptor, reprocann_codigo, reprocann_estado FROM socios WHERE etapa='activo' ORDER BY apellido"
        ).fetchall()

        # Dispensaciones del trimestre
        disp_trim = db.execute(
            "SELECT s.nombre, s.apellido, s.diagnostico, d.variedad, SUM(d.gramos) as total_g "
            "FROM dispensaciones d JOIN socios s ON s.id=d.socio_id "
            "WHERE d.fecha BETWEEN ? AND ? GROUP BY d.socio_id, d.variedad ORDER BY s.apellido",
            (desde_t, hasta_t)
        ).fetchall()
        pedidos_trim = db.execute(
            "SELECT s.nombre, s.apellido, s.diagnostico, p.variedad, SUM(p.gramos) as total_g "
            "FROM pedidos p JOIN socios s ON s.id=p.socio_id "
            "WHERE p.estado='entregado' AND p.fecha_entrega BETWEEN ? AND ? GROUP BY p.socio_id, p.variedad ORDER BY s.apellido",
            (desde_t, hasta_t)
        ).fetchall()

        total_pacientes = len(socios_activos)
        total_disp_g = sum(r['total_g'] for r in disp_trim) + sum(r['total_g'] for r in pedidos_trim)

        # Diagnósticos agrupados
        diagn_raw = db.execute(
            "SELECT diagnostico, COUNT(*) as cnt FROM socios WHERE etapa='activo' AND diagnostico IS NOT NULL GROUP BY diagnostico ORDER BY cnt DESC"
        ).fetchall()

        prompt = (
            f"Sos el Director Médico de '{nombre_club}', un cannabis social club en Argentina habilitado bajo Ley 27.350 y Decreto 883/2020. "
            f"Tu matrícula es: {_sanitizar_input(matricula, 50) or 'N/A'}. "
            f"Redactá el informe trimestral {trim_sel} {hoy.year} para presentar al REPROCANN / Ministerio de Salud. "
            f"Período: {desde_t} al {hasta_t}. "
            f"Datos: {total_pacientes} pacientes vinculados. "
            f"Distribución total del trimestre: {total_disp_g:.1f}g. "
            f"Diagnósticos: {', '.join(f'{d[0]}: {d[1]}' for d in diagn_raw[:5])}. "
            f"Redactá 7 secciones: 1) Identificación del director médico, 2) Nombre del club y período, "
            f"3) Nómina de pacientes con diagnóstico y tratamiento, 4) Variedades y dosis por paciente, "
            f"5) Evolución clínica general (sin revelar datos individuales), "
            f"6) Conclusiones y adherencia al tratamiento, 7) Declaración de responsabilidad. "
            f"Formato: texto formal en español, para autoridad sanitaria. Aproximadamente 500 palabras."
        )
        try:
            informe_texto, _, _, _ = _llamar_llm(prompt, 1200)
        except Exception as e:
            informe_texto = f"[Error al generar con IA: {e}]\n\nINFORME TRIMESTRAL {trim_sel} {hoy.year}\nClub: {nombre_club}\nDirector Médico: {director}\nPacientes: {total_pacientes}\nDistribución: {total_disp_g:.1f}g"
        msg = f'Informe {trim_sel} {hoy.year} generado.'

    return render_template('admin/informe-director.html',
        trimestres=trimestres, trim_sel=trim_sel, trim_actual=trim_actual,
        desde_t=desde_t, hasta_t=hasta_t,
        informe_texto=informe_texto, msg=msg)


# ─── Nómina de Beneficiarios REPROCANN ───────────────────────────────────────

@app.route('/admin/nomina')
@login_required
def admin_nomina():
    db = get_db()
    from datetime import date

    socios = db.execute('''
        SELECT id, nombre, apellido, dni, diagnostico, medico_prescriptor,
               tipo_socio, etapa, reprocann_codigo, reprocann_estado,
               reprocann_inicio, reprocann_vencimiento, plantas_autorizadas,
               created_at
        FROM socios WHERE etapa='activo'
        ORDER BY apellido, nombre
    ''').fetchall()

    club = db.execute("SELECT * FROM clubs WHERE id=1").fetchone()
    hoy = date.today().isoformat()

    # Si piden CSV
    if request.args.get('formato') == 'csv':
        import csv, io
        output = io.StringIO()
        w = csv.writer(output)
        w.writerow(['Apellido','Nombre','DNI','Diagnóstico','Médico prescriptor',
                    'Tipo socio','Código REPROCANN','Estado REPROCANN',
                    'Inicio credencial','Vencimiento','Plantas autorizadas','Alta en club'])
        for s in socios:
            w.writerow([
                s['apellido'], s['nombre'], s['dni'] or '', s['diagnostico'] or '',
                s['medico_prescriptor'] or '', s['tipo_socio'] or '',
                s['reprocann_codigo'] or '', s['reprocann_estado'] or '',
                s['reprocann_inicio'] or '', s['reprocann_vencimiento'] or '',
                s['plantas_autorizadas'] or 9, s['created_at'][:10] if s['created_at'] else ''
            ])
        resp = make_response(output.getvalue())
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resp.headers['Content-Disposition'] = f'attachment; filename=nomina-reprocann-{hoy}.csv'
        return resp

    return render_template('admin/nomina.html',
        socios=socios, club=club, hoy=hoy,
        tipo_socio_label=TIPO_SOCIO_LABEL)


# Inicializar DB siempre al arrancar — funciona con Gunicorn y ejecución directa
init_db()
# ═══════════════════════════════════════════════════════════════════════════
#  TRAZABILIDAD INTERNACIONAL
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/admin/cosecha/<int:cid>/coa', methods=['POST'])
@login_required
@write_required
def admin_cosecha_coa(cid):
    """Actualiza el Certificado de Análisis de una cosecha."""
    db = get_db()
    f  = request.form
    db.execute('''
        UPDATE cosechas SET
            thc_real_pct         = ?,
            cbd_real_pct         = ?,
            terpenos_pct         = ?,
            laboratorio          = ?,
            num_informe_lab      = ?,
            fecha_analisis       = ?,
            pesticidas_status    = ?,
            metales_status       = ?,
            microbiologia_status = ?,
            humedad_muestra_pct  = ?,
            condiciones_almacenamiento = ?,
            responsable_cosecha  = ?,
            coa_status           = ?
        WHERE id = ?
    ''', (
        f.get('thc_real_pct','').strip() or None,
        f.get('cbd_real_pct','').strip() or None,
        f.get('terpenos_pct','').strip() or None,
        f.get('laboratorio','').strip() or None,
        f.get('num_informe_lab','').strip() or None,
        f.get('fecha_analisis','').strip() or None,
        f.get('pesticidas_status','pendiente'),
        f.get('metales_status','pendiente'),
        f.get('microbiologia_status','pendiente'),
        f.get('humedad_muestra_pct','').strip() or None,
        f.get('condiciones_almacenamiento','').strip() or None,
        f.get('responsable_cosecha','').strip() or None,
        f.get('coa_status','pendiente'),
        cid,
    ))
    db.commit()
    # Detectar cultivo padre para redirigir
    cos = db.execute('SELECT cultivo_id FROM cosechas WHERE id=?', (cid,)).fetchone()
    flash('Certificado de Análisis actualizado.')
    return redirect(url_for('admin_cultivo', cid=cos['cultivo_id']) if cos else url_for('admin_cultivos'))


@app.route('/admin/cultivo/<int:cid>/gacp', methods=['POST'])
@login_required
@write_required
def admin_cultivo_gacp(cid):
    """Guarda campos GACP del cultivo."""
    db = get_db()
    f  = request.form
    db.execute('''
        UPDATE cultivos SET
            gacp_fuente_agua         = ?,
            gacp_insumos             = ?,
            gacp_responsable_tecnico = ?,
            gacp_lat                 = ?,
            gacp_lon                 = ?,
            gacp_altitud_m           = ?,
            gacp_humedad_pct         = ?,
            gacp_temp_min_c          = ?,
            gacp_temp_max_c          = ?,
            gacp_observaciones       = ?
        WHERE id = ?
    ''', (
        f.get('gacp_fuente_agua','').strip() or None,
        f.get('gacp_insumos','').strip() or None,
        f.get('gacp_responsable_tecnico','').strip() or None,
        f.get('gacp_lat','').strip() or None,
        f.get('gacp_lon','').strip() or None,
        f.get('gacp_altitud_m','').strip() or None,
        f.get('gacp_humedad_pct','').strip() or None,
        f.get('gacp_temp_min_c','').strip() or None,
        f.get('gacp_temp_max_c','').strip() or None,
        f.get('gacp_observaciones','').strip() or None,
        cid,
    ))
    db.commit()
    flash('Datos GACP actualizados.')
    return redirect(url_for('admin_cultivo', cid=cid))


@app.route('/admin/libro-movimientos')
@login_required
def admin_libro_movimientos():
    """Libro de Movimientos formal (estándar GACP/GMP internacional)."""
    db = get_db()
    desde = request.args.get('desde', (date.today() - timedelta(days=90)).isoformat())
    hasta = request.args.get('hasta', date.today().isoformat())
    var_fil = request.args.get('variedad', '')

    # Entradas: cosechas
    q_ent = '''
        SELECT co.id, co.fecha, co.lote_codigo, cu.variedad, cu.codigo as cultivo_cod,
               co.peso_seco_g as gramos, co.coa_status, co.thc_real_pct, co.cbd_real_pct,
               co.laboratorio, co.num_informe_lab, s.nombre || ' ' || s.apellido as responsable
        FROM cosechas co
        JOIN cultivos cu ON cu.id = co.cultivo_id
        JOIN socios s ON s.id = cu.socio_id
        WHERE co.fecha BETWEEN ? AND ?
    '''
    params_ent = [desde, hasta]
    if var_fil:
        q_ent += ' AND cu.variedad = ?'
        params_ent.append(var_fil)
    q_ent += ' ORDER BY co.fecha DESC'
    entradas = [dict(r) for r in db.execute(q_ent, params_ent).fetchall()]

    # Salidas: dispensaciones
    q_sal = '''
        SELECT d.id, d.fecha, d.lote_codigo, d.variedad, d.gramos,
               s.nombre || ' ' || s.apellido as socio, s.dni,
               d.notas, d.registrado_por, d.cosecha_id
        FROM dispensaciones d JOIN socios s ON s.id = d.socio_id
        WHERE d.fecha BETWEEN ? AND ?
    '''
    params_sal = [desde, hasta]
    if var_fil:
        q_sal += ' AND d.variedad = ?'
        params_sal.append(var_fil)
    q_sal += ' ORDER BY d.fecha DESC'
    salidas_disp = [dict(r) for r in db.execute(q_sal, params_sal).fetchall()]

    # Salidas: pedidos entregados
    q_ped = '''
        SELECT p.id, p.fecha_entrega as fecha, NULL as lote_codigo, p.variedad, p.gramos,
               s.nombre || ' ' || s.apellido as socio, s.dni,
               p.notas, p.registrado_por, NULL as cosecha_id
        FROM pedidos p JOIN socios s ON s.id = p.socio_id
        WHERE p.estado='entregado' AND p.fecha_entrega BETWEEN ? AND ?
    '''
    params_ped = [desde, hasta]
    if var_fil:
        q_ped += ' AND p.variedad = ?'
        params_ped.append(var_fil)
    q_ped += ' ORDER BY p.fecha_entrega DESC'
    salidas_ped = [dict(r) for r in db.execute(q_ped, params_ped).fetchall()]

    salidas = sorted(salidas_disp + salidas_ped, key=lambda x: x['fecha'] or '', reverse=True)

    # Balance por variedad (todo el historial, no filtrado por fecha)
    variedades_stock = db.execute('''
        SELECT cu.variedad,
               COALESCE(SUM(co.peso_seco_g),0) as total_entrada_g
        FROM cosechas co JOIN cultivos cu ON cu.id = co.cultivo_id
        GROUP BY cu.variedad
    ''').fetchall()

    balance = []
    for row in variedades_stock:
        v = row['variedad']
        salida_disp = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM dispensaciones WHERE variedad=?", (v,)
        ).fetchone()[0] or 0
        salida_ped = db.execute(
            "SELECT COALESCE(SUM(gramos),0) FROM pedidos WHERE variedad=? AND estado='entregado'", (v,)
        ).fetchone()[0] or 0
        total_e = round(row['total_entrada_g'], 1)
        total_s = round(salida_disp + salida_ped, 1)
        balance.append({
            'variedad': v,
            'entrada_g': total_e,
            'salida_g': total_s,
            'stock_g': round(total_e - total_s, 1),
        })
    balance.sort(key=lambda x: x['variedad'])

    total_entrada = round(sum(b['entrada_g'] for b in balance), 1)
    total_salida  = round(sum(b['salida_g'] for b in balance), 1)
    total_stock   = round(total_entrada - total_salida, 1)

    variedades_list = [r[0] for r in db.execute(
        "SELECT DISTINCT cu.variedad FROM cosechas co JOIN cultivos cu ON cu.id=co.cultivo_id ORDER BY cu.variedad"
    ).fetchall()]

    club = db.execute("SELECT * FROM clubs WHERE id=1").fetchone()

    return render_template('admin/libro-movimientos.html',
        entradas=entradas, salidas=salidas,
        balance=balance,
        total_entrada=total_entrada, total_salida=total_salida, total_stock=total_stock,
        desde=desde, hasta=hasta, var_fil=var_fil,
        variedades_list=variedades_list,
        club=club,
        hoy=date.today().isoformat(),
    )


@app.route('/admin/informe-incb')
@login_required
def admin_informe_incb():
    """Informe para la INCB (Junta Internacional de Fiscalización de Estupefacientes)."""
    db = get_db()
    anio = request.args.get('anio', str(date.today().year))
    desde = f'{anio}-01-01'
    hasta = f'{anio}-12-31'

    club = db.execute("SELECT * FROM clubs WHERE id=1").fetchone()
    nombre_club = club['nombre'] if club else 'Cannabis Social Club'

    # Lotes del período con CoA
    lotes = db.execute('''
        SELECT co.lote_codigo, co.fecha, cu.variedad, co.peso_seco_g,
               co.thc_real_pct, co.cbd_real_pct, co.laboratorio,
               co.num_informe_lab, co.fecha_analisis,
               co.pesticidas_status, co.metales_status, co.microbiologia_status,
               co.coa_status, cu.codigo as cultivo_cod,
               s.nombre || ' ' || s.apellido as cultivador,
               cu.gacp_responsable_tecnico,
               COALESCE((SELECT SUM(d.gramos) FROM dispensaciones d WHERE d.cosecha_id=co.id),0) as dispensado_g
        FROM cosechas co
        JOIN cultivos cu ON cu.id = co.cultivo_id
        JOIN socios s ON s.id = cu.socio_id
        WHERE co.fecha BETWEEN ? AND ? AND co.lote_codigo IS NOT NULL
        ORDER BY co.fecha
    ''', (desde, hasta)).fetchall()

    # Producción total por variedad
    produccion = db.execute('''
        SELECT cu.variedad,
               COUNT(co.id) as num_lotes,
               COALESCE(SUM(co.peso_seco_g),0) as total_g,
               COALESCE(SUM(co.num_plantas),0) as plantas
        FROM cosechas co JOIN cultivos cu ON cu.id=co.cultivo_id
        WHERE co.fecha BETWEEN ? AND ?
        GROUP BY cu.variedad ORDER BY total_g DESC
    ''', (desde, hasta)).fetchall()

    # Distribución total por variedad
    disp = db.execute('''
        SELECT variedad, COALESCE(SUM(gramos),0) as total_g, COUNT(*) as eventos
        FROM dispensaciones WHERE fecha BETWEEN ? AND ?
        GROUP BY variedad ORDER BY total_g DESC
    ''', (desde, hasta)).fetchall()
    ped = db.execute('''
        SELECT variedad, COALESCE(SUM(gramos),0) as total_g, COUNT(*) as eventos
        FROM pedidos WHERE estado='entregado' AND fecha_pedido BETWEEN ? AND ?
        GROUP BY variedad ORDER BY total_g DESC
    ''', (desde, hasta)).fetchall()
    dist_dict = {}
    for r in list(disp) + list(ped):
        v = r['variedad']
        if v not in dist_dict:
            dist_dict[v] = {'variedad': v, 'total_g': 0, 'eventos': 0}
        dist_dict[v]['total_g'] += r['total_g']
        dist_dict[v]['eventos'] += r['eventos']
    distribucion = sorted(dist_dict.values(), key=lambda x: x['total_g'], reverse=True)

    # Balance global
    total_produccion_g = sum(p['total_g'] for p in produccion)
    total_distribucion_g = sum(d['total_g'] for d in distribucion)
    total_stock_g = round(total_produccion_g - total_distribucion_g, 1)

    # Socios activos con REPROCANN
    socios_reprocann = db.execute(
        "SELECT COUNT(*) FROM socios WHERE etapa='activo' AND reprocann_codigo IS NOT NULL AND reprocann_codigo != ''"
    ).fetchone()[0]
    total_socios = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]

    # Cultivos activos
    cultivos_activos = db.execute("SELECT COUNT(*) FROM cultivos WHERE estado='activo'").fetchone()[0]
    plantas_activas = db.execute(
        "SELECT COALESCE(SUM(num_plantas),0) FROM cultivos WHERE estado='activo'"
    ).fetchone()[0]

    # CoA coverage
    lotes_con_coa = sum(1 for l in lotes if l['coa_status'] == 'aprobado')
    lotes_total   = len(lotes)

    anios = list(range(date.today().year, date.today().year - 5, -1))

    return render_template('admin/informe-incb.html',
        club=club, nombre_club=nombre_club,
        anio=anio, desde=desde, hasta=hasta,
        lotes=lotes,
        produccion=produccion,
        distribucion=distribucion,
        total_produccion_g=round(total_produccion_g, 1),
        total_distribucion_g=round(total_distribucion_g, 1),
        total_stock_g=total_stock_g,
        socios_reprocann=socios_reprocann,
        total_socios=total_socios,
        cultivos_activos=cultivos_activos,
        plantas_activas=plantas_activas,
        lotes_con_coa=lotes_con_coa,
        lotes_total=lotes_total,
        hoy=date.today().isoformat(),
        anios=anios,
    )


@app.route('/admin/libro-movimientos/pdf')
@login_required
def admin_libro_movimientos_pdf():
    from pdf_germina import generar_libro_movimientos
    db = get_db()
    desde = request.args.get('desde', (date.today() - timedelta(days=90)).isoformat())
    hasta = request.args.get('hasta', date.today().isoformat())
    var_fil = request.args.get('variedad', '')
    q_e = 'SELECT c.fecha, c.lote_codigo, c.variedad, c.responsable_cosecha as responsable, c.gramos_secos as gramos, c.thc_real_pct, c.cbd_real_pct, c.laboratorio, c.coa_status, cu.codigo as cultivo_cod FROM cosechas c LEFT JOIN cultivos cu ON cu.id=c.cultivo_id WHERE c.fecha BETWEEN ? AND ?'
    args = [desde, hasta]
    if var_fil:
        q_e += ' AND c.variedad=?'; args.append(var_fil)
    entradas = db.execute(q_e + ' ORDER BY c.fecha DESC', args).fetchall()
    q_d = 'SELECT d.fecha, d.variedad, d.gramos, d.lote_codigo, d.notas, d.registrado_por, s.nombre||" "||s.apellido as socio, s.dni FROM dispensaciones d JOIN socios s ON s.id=d.socio_id WHERE d.fecha BETWEEN ? AND ?'
    args2 = [desde, hasta]
    if var_fil:
        q_d += ' AND d.variedad=?'; args2.append(var_fil)
    salidas_d = db.execute(q_d + ' ORDER BY d.fecha DESC', args2).fetchall()
    buf = generar_libro_movimientos(list(entradas), list(salidas_d), desde, hasta)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f'libro_movimientos_{desde}_{hasta}.pdf')

@app.route('/admin/informe-incb/pdf')
@login_required
def admin_informe_incb_pdf():
    from pdf_germina import generar_informe_incb
    db = get_db()
    anio = request.args.get('anio', str(date.today().year))
    desde = f'{anio}-01-01'; hasta = f'{anio}-12-31'
    club = db.execute('SELECT * FROM configuracion LIMIT 1').fetchone()
    nombre_club = club['club_nombre'] if club and 'club_nombre' in club.keys() else 'Cannabis Social Club'
    lotes = db.execute('''SELECT c.lote_codigo, c.variedad, c.fecha, c.gramos_secos,
        c.thc_real_pct, c.cbd_real_pct, c.coa_status, c.pesticidas_status,
        c.metales_status, c.microbiologia_status, c.laboratorio, c.num_informe_lab
        FROM cosechas c WHERE c.fecha BETWEEN ? AND ? AND c.lote_codigo IS NOT NULL ORDER BY c.fecha''',
        (desde, hasta)).fetchall()
    produccion = db.execute('''SELECT variedad, COALESCE(SUM(gramos_secos),0) as total_g, COUNT(*) as lotes
        FROM cosechas WHERE fecha BETWEEN ? AND ? GROUP BY variedad ORDER BY total_g DESC''',
        (desde, hasta)).fetchall()
    disp = db.execute('''SELECT variedad, COALESCE(SUM(gramos),0) as total_g FROM dispensaciones
        WHERE fecha BETWEEN ? AND ? GROUP BY variedad''', (desde, hasta)).fetchall()
    ped  = db.execute('''SELECT variedad, COALESCE(SUM(gramos),0) as total_g FROM pedidos
        WHERE estado='entregado' AND fecha_pedido BETWEEN ? AND ? GROUP BY variedad''', (desde, hasta)).fetchall()
    dist_dict = {}
    for r in list(disp) + list(ped):
        v = r['variedad']
        if v not in dist_dict: dist_dict[v] = {'variedad':v,'total_g':0}
        dist_dict[v]['total_g'] += r['total_g']
    distribucion = sorted(dist_dict.values(), key=lambda x: x['total_g'], reverse=True)
    total_socios = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo'").fetchone()[0]
    socios_reprocann = db.execute("SELECT COUNT(*) FROM socios WHERE etapa='activo' AND reprocann_codigo IS NOT NULL AND reprocann_codigo!=''").fetchone()[0]
    buf = generar_informe_incb(nombre_club, anio, list(lotes), list(produccion), distribucion, total_socios, socios_reprocann)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f'informe_incb_{anio}.pdf')


_migrate()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=False, host='0.0.0.0', port=port)
