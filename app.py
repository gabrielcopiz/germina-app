import os, sqlite3, csv, io, secrets, smtplib
from datetime import datetime, date, timedelta
from functools import wraps
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, make_response, g)

app = Flask(__name__)
app.secret_key = os.environ.get('CW_SECRET_KEY', 'cannawaka-dev-2026')

DB_PATH    = os.environ.get('CW_DB_PATH', 'cannawaka.db')
ADMIN_USER = os.environ.get('CW_ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('CW_ADMIN_PASS', 'germina2026')
MAIL_USER  = os.environ.get('MAIL_USER', 'besparkcreativa@gmail.com')
MAIL_PASS  = os.environ.get('MAIL_PASS', 'gihojbmsgweclmwu')
RENDER_URL = os.environ.get('RENDER_URL', 'https://germina-app.onrender.com')
CLUB_NOMBRE = os.environ.get('CW_CLUB_NOMBRE', 'Cannawaka')
CRM_USER   = os.environ.get('CRM_USER', 'germina')
CRM_PASS   = os.environ.get('CRM_PASS', 'spark2026')

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
        return {'demo_club_nombre': row[0] if row else CLUB_NOMBRE}
    except Exception:
        return {'demo_club_nombre': CLUB_NOMBRE}

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
            fecha TEXT DEFAULT (date('now')),
            UNIQUE(variedad_id, socio_id))''')
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
        mi_r = db.execute('SELECT rating, comentario FROM variedad_ratings WHERE variedad_id=? AND socio_id=?',
                          (v['id'], s['id'])).fetchone()
        variedades.append({
            **dict(v),
            'avg_rating': round(avg_row[0] or 0, 1),
            'rating_count': avg_row[1] or 0,
            'mi_rating': mi_r['rating'] if mi_r else 0,
            'mi_comentario': mi_r['comentario'] if mi_r else '',
            'puede_votar': v['nombre'] in variedades_set,
        })
    return render_template('portal.html',
        s=s, docs=docs, cuota_actual=cuota_actual, hoy=hoy,
        consumido_mes=round(consumido_mes,1),
        total_consumido=round(total_consumido,1),
        historial=historial, variedades=variedades,
        token=token,
        etapa_label=ETAPA_LABEL, etapa_color=ETAPA_COLOR)

@app.route('/mi-estado/<token>/rating/<int:vid>', methods=['POST'])
def portal_rating(token, vid):
    db = get_db()
    s = db.execute('SELECT * FROM socios WHERE token=?', (token,)).fetchone()
    if not s: return jsonify(ok=False), 403
    rating = int(request.json.get('rating', 0) if request.is_json else request.form.get('rating', 0))
    comentario = (request.json.get('comentario','') if request.is_json else request.form.get('comentario','')).strip()[:400]
    if not 1 <= rating <= 5: return jsonify(ok=False, msg='Rating inválido'), 400
    existing = db.execute('SELECT id FROM variedad_ratings WHERE variedad_id=? AND socio_id=?', (vid, s['id'])).fetchone()
    today = date.today().isoformat()
    if existing:
        db.execute('UPDATE variedad_ratings SET rating=?,comentario=?,fecha=? WHERE id=?',
                   (rating, comentario, today, existing['id']))
    else:
        db.execute('INSERT INTO variedad_ratings (variedad_id,socio_id,rating,comentario) VALUES (?,?,?,?)',
                   (vid, s['id'], rating, comentario))
    db.commit()
    avg = db.execute('SELECT AVG(rating), COUNT(*) FROM variedad_ratings WHERE variedad_id=?', (vid,)).fetchone()
    return jsonify(ok=True, avg=round(avg[0] or 0, 1), count=avg[1] or 0)

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
def admin_dispensario():
    db = get_db()
    hoy = date.today().isoformat()

    if request.method == 'POST':
        socio_id = request.form.get('socio_id')
        variedad = (request.form.get('variedad','') or request.form.get('variedad_manual','')).strip()
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

    return render_template('admin/dispensario.html',
        socios_activos=[dict(s) for s in socios_activos],
        variedades_catalogo=[dict(v) for v in variedades_catalogo],
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
    return render_template('admin/socio.html',
        s=s, notas=notas, docs=docs, cultivos=cultivos,
        pedidos=pedidos, consumido_mes=consumido_mes,
        total_consumido=total_consumido, total_gastado=total_gastado,
        stock_variedades=stock_variedades, member_url=member_url,
        dispensaciones_socio=dispensaciones_socio,
        cuota_actual=cuota_actual, todas_cuotas=todas_cuotas,
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

if __name__ == '__main__':
    init_db()
    _migrate()
    port = int(os.environ.get('PORT', 5002))
    app.run(debug=False, host='0.0.0.0', port=port)
