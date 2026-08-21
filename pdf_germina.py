from io import BytesIO
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, PageBreak)

G_VERDE  = colors.HexColor('#1A3520')
G_MID    = colors.HexColor('#2D5C38')
G_LIGHT  = colors.HexColor('#4A7C5E')
G_GOLD   = colors.HexColor('#C8A44A')
G_CREAM  = colors.HexColor('#F5F2EC')
G_INK    = colors.HexColor('#1E1E1E')
G_GRIS   = colors.HexColor('#6B6560')
G_BORDER = colors.HexColor('#D8D3C8')
G_PALE   = colors.HexColor('#EDE8DF')

def _fecha_es():
    meses = ['','enero','febrero','marzo','abril','mayo','junio',
             'julio','agosto','septiembre','octubre','noviembre','diciembre']
    h = date.today()
    return f'{h.day} de {meses[h.month]} de {h.year}'

def _fecha_vencimiento():
    v = date.today() + timedelta(days=30)
    meses = ['','enero','febrero','marzo','abril','mayo','junio',
             'julio','agosto','septiembre','octubre','noviembre','diciembre']
    return f'{v.day} de {meses[v.month]} de {v.year}'

def _st(name, **kw):
    defaults = dict(fontName='Helvetica', fontSize=10, textColor=G_INK,
                    spaceAfter=6, leading=14)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)

def _tip(text):
    data = [[Paragraph(f'💡  {text}',
                       _st('t', fontSize=9, textColor=colors.HexColor('#7A5C00'), leading=13))]]
    t = Table(data, colWidths=[15*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF9EE')),
        ('BOX', (0,0), (-1,-1), 0.5, G_GOLD),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    return t

def _alert(text, bg='#EAF7EA', border='#4A9A38'):
    data = [[Paragraph(text, _st('al', fontSize=10, textColor=G_INK, leading=15))]]
    t = Table(data, colWidths=[15*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor(bg)),
        ('BOX',           (0,0), (-1,-1), 1, colors.HexColor(border)),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('RIGHTPADDING',  (0,0), (-1,-1), 14),
        ('TOPPADDING',    (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    return t

def _header_table(data, col_widths):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  9),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, G_CREAM]),
        ('GRID',          (0,0), (-1,-1), 0.3, G_BORDER),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t


# ═══════════════════════════════════════════════════
#  PROPUESTA COMERCIAL
# ═══════════════════════════════════════════════════

def generar_propuesta(club_nombre, contacto_nombre):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2*cm, bottomMargin=2.5*cm)

    H0  = _st('h0',  fontName='Helvetica-Bold', fontSize=22, textColor=G_MID,   spaceBefore=0,  spaceAfter=6,  leading=26)
    H1  = _st('h1',  fontName='Helvetica-Bold', fontSize=14, textColor=G_MID,   spaceBefore=18, spaceAfter=5,  leading=18)
    H2  = _st('h2',  fontName='Helvetica-Bold', fontSize=11, textColor=G_INK,   spaceBefore=12, spaceAfter=4,  leading=15)
    BOD = _st('bod', fontSize=10, textColor=G_INK,  spaceAfter=7, leading=15, alignment=TA_JUSTIFY)
    BUL = _st('bul', fontSize=10, textColor=G_INK,  spaceAfter=5, leading=14, leftIndent=14, firstLineIndent=-10)
    SML = _st('sml', fontName='Helvetica-Oblique', fontSize=8.5, textColor=G_GRIS, spaceAfter=5, leading=12)
    NOT = _st('not', fontName='Helvetica-Oblique', fontSize=9, textColor=G_GRIS, spaceAfter=6, leading=13)
    FAQ_Q = _st('fq', fontName='Helvetica-Bold', fontSize=10, textColor=G_MID, spaceBefore=10, spaceAfter=3, leading=14)
    FAQ_A = _st('fa', fontSize=10, textColor=G_INK, spaceAfter=8, leading=14, leftIndent=10)

    s = []
    fecha = _fecha_es()
    validez = _fecha_vencimiento()

    # ══════════════════════════════════════════════
    # PORTADA
    # ══════════════════════════════════════════════
    s.append(Spacer(1, 1.2*cm))
    s.append(Paragraph(
        '<font color="#1A3520"><b>Germi</b></font><font color="#C8A44A"><b>na</b></font>',
        _st('logo', fontName='Helvetica-Bold', fontSize=42, spaceAfter=4)))
    s.append(Paragraph('La infraestructura digital completa de tu Cannabis Social Club',
                        _st('lsub', fontSize=12, textColor=G_GRIS, spaceAfter=28)))
    s.append(HRFlowable(width='100%', thickness=2, color=G_MID, spaceAfter=28))
    s.append(Paragraph('Propuesta Comercial Personalizada', H0))
    s.append(Paragraph(f'Preparada para <b>{club_nombre}</b>',
                        _st('dest', fontSize=13, textColor=G_GRIS, spaceAfter=6)))
    s.append(Paragraph(f'Atención: {contacto_nombre}',
                        _st('at', fontSize=11, textColor=G_GRIS, spaceAfter=4)))
    s.append(Paragraph(f'Fecha: {fecha}   ·   Válida hasta: <b>{validez}</b>',
                        _st('fe', fontSize=10, textColor=G_GRIS, spaceAfter=36)))

    intro = [[Paragraph(
        f'<b>Germina</b> no es un programa más. Es todo lo que tu club necesita para dejar de '
        f'improvisar y empezar a operar con la seriedad que su trabajo merece: '
        f'su propio sistema de gestión, su propia presencia digital, trazabilidad completa, '
        f'una aplicación exclusiva para sus socios y un panel donde ves todo en tiempo real. '
        f'Todo junto. Sin depender de cinco proveedores distintos. Sin WhatsApp como sistema operativo.',
        BOD)]]
    ti = Table(intro, colWidths=[15*cm])
    ti.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), G_CREAM),
        ('BOX',           (0,0), (-1,-1), 0.5, G_BORDER),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
    ]))
    s.append(ti)
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # DIAGNÓSTICO — 8 DOLORES
    # ══════════════════════════════════════════════
    s.append(Paragraph('Si tu club creció, pero tu operación sigue igual — esto es para vos', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'No hace falta que tu club tenga problemas graves para necesitar Germina. '
        'Alcanza con que alguno de estos ocho puntos te resulte familiar:', BOD))

    dolores = [
        ['El problema', 'Por qué importa'],
        ['No sabés exactamente cuánto stock tenés',
         'Si el stock teórico no coincide con el real, estás perdiendo producto y dinero '
         'sin poder demostrar dónde ni cuándo. Cada gramo que no se puede explicar es una pérdida invisible.'],
        ['Tenés trazabilidad, pero no podés demostrarla',
         'La información está en planillas, WhatsApp y la cabeza del equipo. '
         'Cuando te la piden, tenés que reconstruirla. Eso no es trazabilidad: es suerte.'],
        ['Las mermas no tienen origen ni destino',
         'Toda diferencia de peso, descarte o pérdida que no queda registrada se convierte '
         'en un agujero invisible. Germina te permite saber exactamente dónde se está yendo el producto.'],
        ['Los socios viven en planillas y WhatsApp',
         'Altas pendientes, documentación incompleta, cuotas vencidas que nadie cobra, '
         'socios activos que no deberían estarlo. Cada error es una responsabilidad del club.'],
        ['WhatsApp no puede ser el sistema operativo del club',
         'WhatsApp sirve para comunicarse, no para gestionar. Cuando la información importante '
         'vive en conversaciones, se pierde, se duplica y depende de quién tenga el teléfono con esa charla.'],
        ['El dueño del club no sabe qué está pasando en tiempo real',
         'Tener que revisar cinco planillas, preguntar a tres personas y reconstruir información '
         'para saber cuánto stock tenés, cuánto produciste, cuánto entregaste y cuánto perdiste '
         'no es gestión: es improvisación. Germina te da esa información en una pantalla.'],
        ['El club tiene operación seria pero presencia digital improvisada',
         'Instagram y WhatsApp no alcanzan para transmitir imagen institucional. '
         'Tu club merece su propia presencia digital: sitio propio, identidad propia, '
         'proceso de membresía propio. No una página genérica: la tuya.'],
        ['Los socios no tienen ninguna experiencia digital con el club',
         'Cada socio sigue dependiendo de un mensaje de WhatsApp para saber su cupo, '
         'su estado de cuota o qué variedades hay disponibles. '
         'Tu club puede darles algo mejor: su propio portal, en su celular, con toda su información.'],
    ]
    td = _header_table(dolores, [4.8*cm, 10.2*cm])
    s.append(td)
    s.append(Spacer(1, 0.4*cm))
    s.append(_tip('Ninguno de estos problemas se resuelve con más personal. Se resuelven con el sistema correcto.'))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # LA SOLUCIÓN — 7 PILARES
    # ══════════════════════════════════════════════
    s.append(Paragraph('Germina. Todo lo que hoy está disperso, en un solo lugar.', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=8))
    s.append(Paragraph(
        'No necesitás contratar distintos proveedores para resolver cada problema. '
        'Germina concentra en un solo lugar todo lo que tu club necesita para operar con seriedad:', BOD))

    modulos = [
        ['Qué resuelve', 'Cómo lo resuelve Germina'],
        ['Dejá de buscar información de socios en WhatsApp y planillas',
         'Expediente digital por socio: etapa, documentación, cuota, notas internas y cupo. '
         'Alta, seguimiento y baja en un solo lugar.'],
        ['Sabé exactamente cuánto tenés, dónde está y qué salió',
         'Control de stock con trazabilidad por lote. Cada gramo registrado con origen, destino y fecha. '
         'Las mermas quedan documentadas, no desaparecen.'],
        ['Registrá cada entrega con trazabilidad completa',
         'Dispensario digital: variedad, gramos, socio y fecha. Sin anotaciones. '
         'El sistema verifica cupos y registra automáticamente.'],
        ['Conocé el ciclo completo de tu producción',
         'Módulo de ciclo productivo: Semilla → Cultivo → Cosecha → Curado → Stock → Entrega. '
         'Cada etapa documentada. Podés reconstruir el historial completo de cualquier lote.'],
        ['Tu club necesita presencia digital a la altura de la seriedad con la que trabajás',
         'Landing personalizada con identidad propia del club, formulario de membresía, '
         'catálogo de variedades y acceso al portal del socio. No una plantilla: la de tu club.'],
        ['Tu club también vive en el celular de cada socio',
         'App exclusiva para socios: carnet digital con QR, cupo mensual, catálogo de flores '
         'con calificaciones e historial de retiros. Sin descargar nada. Desde el celular.'],
        ['Todo el club bajo control desde un solo lugar',
         'Panel central con todos los indicadores en tiempo real: socios activos, stock, '
         'dispensaciones del día, cuotas vencidas, aforo y alertas. Dejás de preguntar qué pasa. Lo ves.'],
    ]
    s.append(_header_table(modulos, [5.5*cm, 9.5*cm]))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # ANTES Y DESPUÉS
    # ══════════════════════════════════════════════
    s.append(Paragraph('Antes y después: la diferencia en concreto', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))

    comp = [
        ['Sin Germina', 'Con Germina'],
        ['WhatsApp + Excel + papel + memoria del equipo',
         'Un solo sistema. Todo registrado. Todo accesible desde cualquier lugar.'],
        ['Stock teórico que no coincide con el real',
         'Sabés cuánto tenés, cuánto salió y dónde está la diferencia.'],
        ['Mermas que nadie puede explicar',
         'Cada gramo tiene origen, destino y responsable. Las pérdidas quedan documentadas.'],
        ['Socios gestionados en conversaciones y planillas',
         'Expediente digital: documentación, cuota, cupo e historial en un solo lugar.'],
        ['El dueño reconstruye información para tomar decisiones',
         'El dashboard muestra todo en tiempo real. Dejás de preguntar. Lo ves.'],
        ['Instagram y WhatsApp como única presencia digital',
         'Landing personalizada del club con identidad propia y proceso de membresía.'],
        ['Socios que dependen de un mensaje para saber su estado',
         'Cada socio tiene su portal: cupo, carnet, catálogo e historial desde el celular.'],
        ['Imposible escalar más de 30–40 socios sin caos',
         'Diseñado para crecer: funciona igual con 20 o con 300 socios.'],
    ]
    tc2 = Table(comp, colWidths=[7.5*cm, 7.5*cm])
    tc2.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  9),
        ('BACKGROUND',    (0,1), (0,-1),  colors.HexColor('#FEF2F2')),
        ('BACKGROUND',    (1,1), (1,-1),  colors.HexColor('#F0FDF4')),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 9),
        ('GRID',          (0,0), (-1,-1), 0.3, G_BORDER),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    s.append(tc2)
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # LANDING PERSONALIZADA
    # ══════════════════════════════════════════════
    s.append(Paragraph('Tu club necesita su propia presencia digital', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Germina no te da una página genérica. Crea la presencia digital propia de tu club: '
        'con tu nombre, tu identidad, tu información y tu proceso de membresía.', BOD))

    landing_items = [
        ['Qué incluye', 'Para qué sirve'],
        ['Identidad visual propia del club',
         'Tu nombre, tu imagen, tu color. No una plantilla: la presencia digital de tu club específicamente.'],
        ['Información institucional del club',
         'Quiénes son, cómo funciona el club, qué variedades tienen, cómo asociarse.'],
        ['Formulario de membresía integrado',
         'Los interesados completan sus datos directamente. El club los recibe en el sistema, listos para procesar.'],
        ['Catálogo de variedades visible',
         'Las flores disponibles, con genética, efectos e indicaciones. Tu club se muestra profesional desde el primer contacto.'],
        ['Acceso al portal del socio',
         'Quienes ya son socios acceden directamente a su portal desde la landing. Todo conectado.'],
        ['Conexión directa con el sistema de gestión',
         'Cada formulario enviado llega al panel de administración. Sin copiar datos. Sin perder información.'],
    ]
    s.append(_header_table(landing_items, [5*cm, 10*cm]))
    s.append(Spacer(1, 0.4*cm))
    s.append(_alert(
        '⚠️  <b>Importante:</b> No recibís una plantilla que comparte la estética de otro club. '
        'Germina desarrolla la presencia digital específica de tu club. '
        'Con tu identidad. Con tu nombre en grande. Con tu proceso de contacto y membresía.'))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # APP EXCLUSIVA PARA SOCIOS
    # ══════════════════════════════════════════════
    s.append(Paragraph('Tu club en el bolsillo de cada socio', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Cada socio tiene acceso a su propio portal digital, conectado directamente con el sistema del club. '
        'Sin descargar nada. Ingresa con su DNI desde cualquier celular y tiene todo en un lugar.', BOD))

    app_items = [
        ['Función', 'Qué ve y puede hacer el socio'],
        ['Carnet digital con QR',
         'Su credencial de socio siempre disponible. Se escanea en el club para identificarlo en segundos.'],
        ['Estado de cupo mensual',
         'Sabe cuántos gramos consumió y cuántos le quedan. Sin preguntar al club por WhatsApp.'],
        ['Estado de cuota',
         'Ve si su membresía está al día, cuándo vence y cuál es su estado. Sin llamadas.'],
        ['Catálogo de variedades',
         'Accede a las flores disponibles con genética, THC/CBD, efectos e indicaciones. '
         'Puede calificar las variedades que ya probó.'],
        ['Historial de retiros',
         'Todos sus retiros agrupados por mes. Su tratamiento documentado y accesible.'],
        ['Perfil e información personal',
         'Sus datos, su médico prescriptor y su documentación disponibles desde el celular.'],
    ]
    s.append(_header_table(app_items, [4.5*cm, 10.5*cm]))
    s.append(Spacer(1, 0.4*cm))
    s.append(_tip(
        'El resultado: el socio deja de depender de un mensaje de WhatsApp para saber su estado. '
        'Y el club deja de responder mensajes repetitivos que el sistema puede responder solo.'))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # DASHBOARD Y TRAZABILIDAD
    # ══════════════════════════════════════════════
    s.append(Paragraph('El centro de control de tu club', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=8))
    s.append(Paragraph(
        'Dejás de preguntar qué está pasando. Lo ves. '
        'El panel central muestra todo el club en tiempo real desde una sola pantalla:', BOD))

    dash_items = [
        ['Indicador', 'Qué te dice'],
        ['Socios activos y en proceso',        'Cuántos socios operativos tenés y cuántos están pendientes de completar el proceso.'],
        ['Dispensaciones del día',             'Cuántos retiros hubo hoy, qué variedad y cuántos gramos.'],
        ['Stock disponible por variedad',      'Cuánto tenés de cada cepa. En tiempo real, no cuando alguien lo anota.'],
        ['Cuotas vencidas y por vencer',       'Quiénes tienen la membresía vencida. Quiénes vencen en los próximos días.'],
        ['Documentación pendiente',            'Qué socio tiene documentación incompleta. Para que nada se pierda.'],
        ['Aforo en tiempo real',               'Cuántos socios hay en el club ahora mismo. Registro de entradas y salidas.'],
        ['Alertas de stock bajo',              'Cuando una variedad está por agotarse, el sistema te avisa. Sin sorpresas.'],
    ]
    s.append(_header_table(dash_items, [5*cm, 10*cm]))
    s.append(Spacer(1, 0.5*cm))

    s.append(Paragraph('Trazabilidad completa: de la semilla a la entrega', H2))
    s.append(Paragraph(
        'Podés reconstruir el recorrido completo de cualquier lote. Cada etapa tiene su registro, '
        'su responsable y su fecha:', BOD))

    traza = [
        ['Etapa', 'Qué se registra'],
        ['Semilla / Genética',   'Origen, banco, cepa y fecha de inicio del ciclo.'],
        ['Cultivo',              'Técnica, responsable, insumos y fechas por etapa (germinación, vegetativa, floración).'],
        ['Cosecha',              'Fecha, gramos húmedos, responsable y lote asignado.'],
        ['Secado y curado',      'Peso inicial y final, mermas documentadas, tiempo del proceso.'],
        ['Stock',                'Ingreso al inventario con código único de lote, cantidad y estado.'],
        ['Entrega al socio',     'Socio, variedad, gramos, fecha y número de lote. Cupo descontado automáticamente.'],
    ]
    s.append(_header_table(traza, [4*cm, 11*cm]))
    s.append(Spacer(1, 0.3*cm))
    s.append(_tip(
        'Germina organiza y documenta tu operación. No garantiza cumplimiento legal automático, '
        'pero te da las herramientas para poder demostrar lo que hacés cuando lo necesitás.'))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # PROPUESTA A
    # ══════════════════════════════════════════════
    s.append(Paragraph('Propuesta A — Implementación Estándar', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Acceso completo a toda la infraestructura Germina: sistema de gestión, landing personalizada del club, '
        'portal del socio, trazabilidad, dashboard y capacitación del equipo. '
        'Implementación guiada en 4 semanas con soporte dedicado los primeros 3 meses.', BOD))

    s.append(Paragraph('Qué incluye la implementación (USD 7.500)', H2))
    desglose = [
        ['Concepto', 'Detalle', 'Valor'],
        ['Configuración del entorno',
         'Setup del servidor, dominio, base de datos y backup automático.',
         'USD 800'],
        ['Migración de socios',
         'Carga e importación de socios existentes (hasta 200). Validación de datos.',
         'USD 600'],
        ['Landing personalizada del club',
         'Presencia digital propia: identidad, catálogo, formulario de membresía y acceso al portal del socio.',
         'USD 700'],
        ['Portal del socio + app mobile',
         'Configuración del portal con variedades, carnet QR y cupos por socio.',
         'USD 700'],
        ['Integración del ciclo productivo',
         'Configuración del flujo completo Semilla → Entrega según la operación del club.',
         'USD 900'],
        ['Capacitación del equipo',
         'Hasta 3 sesiones de 90 minutos con el equipo. Manual de usuario incluido.',
         'USD 500'],
        ['Desarrollo a medida + ajustes',
         'Adaptaciones específicas del club durante la implementación.',
         'USD 1.500'],
        ['Soporte técnico 3 meses',
         'Respuesta en menos de 24 horas. Canal directo con el equipo de Germina.',
         'USD 800'],
        ['TOTAL', '', 'USD 7.500'],
    ]
    td2 = Table(desglose, colWidths=[4.5*cm, 7.5*cm, 3*cm])
    td2.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),   G_MID),
        ('TEXTCOLOR',     (0,0), (-1,0),   colors.white),
        ('FONTNAME',      (0,0), (-1,0),   'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1),  9),
        ('ROWBACKGROUNDS',(0,1), (-1,-2),  [colors.white, G_CREAM]),
        ('BACKGROUND',    (0,-1),(-1,-1),  G_VERDE),
        ('TEXTCOLOR',     (0,-1),(-1,-1),  colors.white),
        ('FONTNAME',      (0,-1),(-1,-1),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,-1),(-1,-1),  10),
        ('GRID',          (0,0), (-1,-1),  0.3, G_BORDER),
        ('LEFTPADDING',   (0,0), (-1,-1),  8),
        ('RIGHTPADDING',  (0,0), (-1,-1),  8),
        ('TOPPADDING',    (0,0), (-1,-1),  6),
        ('BOTTOMPADDING', (0,0), (-1,-1),  6),
        ('VALIGN',        (0,0), (-1,-1),  'MIDDLE'),
        ('ALIGN',         (2,0), (2,-1),   'RIGHT'),
    ]))
    s.append(td2)
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('Retorno sobre la inversión (estimado referencial)', H2))
    s.append(Paragraph(
        'Cálculo conservador para un club con 40 socios y cuota mensual de $8.000 ARS (≈ USD 8). '
        'Ajustá los números a la realidad de tu club:', BOD))
    roi = [
        ['Concepto', 'Mensual', 'Anual'],
        ['Cuotas cobradas (40 socios × USD 8)',       'USD 320', 'USD 3.840'],
        ['Ahorro en administración (10h/sem × USD 5)', 'USD 200', 'USD 2.400'],
        ['Reducción de mermas (10% de USD 500 stock)', 'USD 50',  'USD 600'],
        ['Total beneficio estimado',                   'USD 570', 'USD 6.840'],
        ['Mantenimiento mensual (desde mes 4)',        '–USD 299','–USD 2.691'],
        ['Recupero de implementación', 'En 13–15 meses con estos números', ''],
    ]
    troi = Table(roi, colWidths=[8*cm, 3.5*cm, 3.5*cm])
    troi.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1), (-1,-3), [colors.white, G_CREAM]),
        ('BACKGROUND',    (0,-3),(-1,-3), colors.HexColor('#F0FDF4')),
        ('FONTNAME',      (0,-3),(-1,-3), 'Helvetica-Bold'),
        ('BACKGROUND',    (0,-2),(-1,-2), colors.HexColor('#FEF9EE')),
        ('BACKGROUND',    (0,-1),(-1,-1), colors.HexColor('#EDE8DF')),
        ('FONTNAME',      (0,-1),(-1,-1), 'Helvetica-Oblique'),
        ('GRID',          (0,0), (-1,-1), 0.3, G_BORDER),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',         (1,0), (2,-1),  'CENTER'),
        ('SPAN',          (1,-1),(2,-1)),
    ]))
    s.append(troi)
    s.append(Paragraph(
        '* Cálculo estimativo. Los resultados reales varían según el tamaño, cuota, '
        'stock y eficiencia de cada club. No prometemos resultados económicos específicos.', NOT))
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('Modalidades de pago', H2))
    pago_a = [
        ['Opción', 'Monto', 'Detalle'],
        ['Pago único (recomendado)', 'USD 7.500', 'Sin recargo. Implementación inicia en 72 hs.'],
        ['En 3 cuotas', '3 × USD 2.700 = USD 8.100', 'Recargo financiero del 8%. Inicio en 72 hs.'],
    ]
    s.append(_header_table(pago_a, [5.5*cm, 5*cm, 4.5*cm]))
    s.append(Paragraph('Mantenimiento mensual (desde el mes 4): <b>USD 299/mes</b>. '
                        'Incluye soporte, actualizaciones y backup diario.', SML))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # PROPUESTA B
    # ══════════════════════════════════════════════
    s.append(Paragraph('Propuesta B — Modelo de Sociedad', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Para clubes que quieren toda la infraestructura Germina con menor inversión inicial. '
        'Germina absorbe gran parte del costo de implementación y participa mensualmente '
        'en los ingresos del club. Es un modelo de <b>piel en el juego</b>: '
        'nos va bien cuando a vos te va bien.', BOD))

    pb = [
        ['Concepto', 'Condición'],
        ['Costo de implementación',      'USD 3.500 (Germina absorbe USD 4.000 del valor total)'],
        ['Participación mensual',         '15% sobre ingresos netos del sistema'],
        ['Mantenimiento mensual',         'Incluido en la participación (sin costo adicional)'],
        ['Duración mínima del acuerdo',   '12 meses calendario desde la firma'],
        ['Renovación',                    'Automática mes a mes a partir del mes 13'],
        ['Cláusula de salida',            'Preaviso de 30 días a partir del mes 13. Sin penalidades.'],
        ['Exclusividad territorial',      'A definir por zona geográfica en el contrato'],
    ]
    s.append(_header_table(pb, [6.5*cm, 8.5*cm]))
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('¿Cómo se calcula el 15%?', H2))
    s.append(Paragraph(
        'La base de cálculo son los <b>ingresos netos del sistema</b>: suma de cuotas cobradas '
        'y dispensaciones registradas en Germina durante el mes calendario, menos los costos '
        'operativos directos acordados contractualmente (insumos registrados en el sistema). '
        '<b>No incluye</b> donaciones, aportes de socios fundadores ni ingresos externos al sistema.', BOD))
    s.append(Paragraph(
        'La liquidación es mensual, dentro de los primeros 5 días hábiles del mes siguiente. '
        'El club recibe un reporte detallado con el cálculo antes de cada pago. '
        'El método de auditoría se define y firma antes del inicio.', BOD))
    s.append(Spacer(1, 0.3*cm))

    garants_b = [[Paragraph(
        '🔒  <b>Tu operación, tus datos.</b> El club mantiene el 100% de la propiedad de todos '
        'los datos de sus socios y su operación. Germina no accede a la información individual '
        'de los socios ni puede utilizarla con ningún fin. '
        'Si el acuerdo termina, el club recibe una exportación completa de toda su base de datos '
        'en formato CSV/JSON dentro de las 48 horas. Sin condiciones.',
        _st('gb', fontSize=9.5, textColor=G_INK, leading=14))]]
    tgb = Table(garants_b, colWidths=[15*cm])
    tgb.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#EAF7EA')),
        ('BOX',           (0,0), (-1,-1), 1, colors.HexColor('#4A9A38')),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('RIGHTPADDING',  (0,0), (-1,-1), 14),
        ('TOPPADDING',    (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    s.append(tgb)
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # PRUEBA SOCIAL
    # ══════════════════════════════════════════════
    s.append(Paragraph('Lo que pasó en el club donde ya está funcionando', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Germina está operativo en producción real. Estos son los resultados del club piloto '
        'con el que desarrollamos y validamos la plataforma '
        '(datos anonimizados por acuerdo de confidencialidad):', BOD))

    piloto = [
        ['Dato del club piloto', 'Detalle'],
        ['Localización',            'Gran Buenos Aires (zona norte)'],
        ['Socios al inicio',        '38 socios activos gestionados manualmente'],
        ['Tiempo de implementación','4 semanas (dentro del plazo garantizado)'],
    ]
    s.append(_header_table(piloto, [6*cm, 9*cm]))
    s.append(Spacer(1, 0.4*cm))

    resultados = [
        ['Métrica', 'Antes', 'Después (90 días)', 'Cambio'],
        ['Tiempo admin semanal',    '14 horas',      '1.5 horas',  '–89%'],
        ['Socios con cuota al día', '61%',           '94%',        '+33 pp'],
        ['Mermas sin explicación',  '12% del stock', '< 1%',       '–91%'],
        ['Satisfacción del socio',  'Sin medir',     '4.7/5 ★',    'Nuevo KPI'],
        ['Alta de nuevo socio',     '3–5 días',      '< 2 horas',  '–90%'],
    ]
    tr = Table(resultados, colWidths=[5*cm, 3*cm, 4*cm, 3*cm])
    tr.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, G_CREAM]),
        ('BACKGROUND',    (3,1), (3,-1),  colors.HexColor('#F0FDF4')),
        ('FONTNAME',      (3,1), (3,-1),  'Helvetica-Bold'),
        ('TEXTCOLOR',     (3,1), (3,-1),  colors.HexColor('#166534')),
        ('GRID',          (0,0), (-1,-1), 0.3, G_BORDER),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',         (1,0), (3,-1),  'CENTER'),
    ]))
    s.append(tr)
    s.append(Spacer(1, 0.3*cm))
    s.append(Paragraph(
        '* Datos del club piloto anonimizados. Los resultados son específicos de ese contexto '
        'y pueden variar según el tamaño, estructura y operación de cada club.', NOT))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # FAQ OBJECIONES
    # ══════════════════════════════════════════════
    s.append(Paragraph('Preguntas frecuentes antes de decidir', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=12))

    faqs = [
        ('¿Qué pasa si quiero salir del acuerdo antes de los 12 meses?',
         'La Propuesta B tiene un período mínimo de 12 meses. Si el club decide salir antes, '
         'se liquida el saldo adeudado de implementación (la diferencia entre los USD 3.500 '
         'pagados y el valor real de USD 7.500). A partir del mes 13, la salida es libre con '
         '30 días de preaviso y sin penalidades.'),
        ('¿Cómo se calcula exactamente el 15% de la Propuesta B?',
         'Se toma la suma de cuotas cobradas + dispensaciones registradas en el sistema durante '
         'el mes, menos costos operativos directos definidos en el contrato. Te enviamos un '
         'reporte con el cálculo detallado antes de cada liquidación. Podés auditar los datos '
         'directamente desde el panel en cualquier momento.'),
        ('¿Puedo exportar todos mis datos si decido no renovar?',
         'Sí, incondicionalmente. Si el acuerdo termina por cualquier motivo, te entregamos '
         'una exportación completa de toda tu base de datos (socios, dispensaciones, cuotas, '
         'historial) en formato CSV/JSON dentro de las 48 horas. Los datos son 100% tuyos.'),
        ('¿Cuánto tiempo lleva migrar los socios que ya tengo?',
         'Para clubes con menos de 100 socios, la migración se completa en la primera semana '
         'de implementación. Para bases más grandes, coordinamos el proceso en paralelo con '
         'la operación para no interrumpir el funcionamiento del club.'),
        ('¿El sistema funciona si no tenemos buena conexión a internet?',
         'La plataforma requiere conexión a internet. Es una aplicación web alojada en la nube. '
         'Para el control de aforo presencial recomendamos tener WiFi en el club. '
         'El portal del socio funciona desde el celular con cualquier conexión.'),
        ('¿Puedo seguir usando el sistema si no renuevo el mantenimiento?',
         'El acceso está vinculado al pago mensual. Si elegís no renovar, acordamos 30 días '
         'para exportar todos tus datos antes del cierre. Nunca perdés información.'),
        ('¿Germina tiene acceso a los datos de salud de mis socios?',
         'No. Los datos de diagnóstico, médico prescriptor y documentación de los socios '
         'están alojados en el servidor del club. Germina no accede a esa información '
         'y no puede utilizarla con ningún fin. El club es el único responsable de su custodia.'),
    ]

    for q, a in faqs:
        s.append(Paragraph(f'❓ {q}', FAQ_Q))
        s.append(Paragraph(a, FAQ_A))

    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # CRONOGRAMA + GARANTÍAS
    # ══════════════════════════════════════════════
    s.append(Paragraph('De la firma al club operando: 4 semanas', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    crono = [
        ['Semana', 'Qué pasa'],
        ['Semana 1', 'Configuración del entorno · Carga inicial de datos · Definición de variedades y cupos · Landing del club'],
        ['Semana 2', 'Migración de socios · Configuración del portal del socio · Pruebas internas'],
        ['Semana 3', 'Capacitación del equipo · Ajustes específicos · Prueba piloto con socios seleccionados'],
        ['Semana 4', 'Lanzamiento oficial · Soporte intensivo · Entrega del manual del usuario'],
    ]
    tc = _header_table(crono, [3.5*cm, 11.5*cm])
    s.append(tc)
    s.append(Spacer(1, 0.5*cm))

    s.append(Paragraph('Garantías incluidas', H2))
    s.append(_alert(
        '🛡️  <b>Garantía de implementación</b>: si la implementación completa supera '
        'las 4 semanas corridas desde la firma del acuerdo por causas imputables a Germina, '
        'devolvemos el 20% del pago inicial sin condiciones ni trámites.'))
    s.append(Spacer(1, 0.3*cm))
    s.append(_alert(
        '🔒  <b>Garantía de datos</b>: ante cualquier incidente de seguridad imputable '
        'a Germina, notificamos en menos de 24 horas y gestionamos la resolución sin costo '
        'adicional para el club.'))
    s.append(Spacer(1, 0.8*cm))

    # ══════════════════════════════════════════════
    # CTA FINAL
    # ══════════════════════════════════════════════
    s.append(Paragraph('Si seguís trabajando como hasta ahora, seguís con los mismos problemas', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Tu club ya creció. Ahora necesita infraestructura para acompañar ese crecimiento. '
        'Germina no viene a cambiar la forma en que tu club trabaja. '
        'Viene a quitarte de encima el trabajo que nunca deberías haber tenido que hacer manualmente.',
        BOD))
    s.append(Paragraph(
        f'Esta propuesta tiene validez hasta el <b>{validez}</b>. '
        f'Te proponemos una demo de 30 minutos por videollamada: '
        f'te mostramos la plataforma funcionando en vivo, con datos reales, '
        f'respondemos todas tus dudas y si decidís avanzar arrancamos en la semana siguiente.',
        BOD))

    pasos = [
        ['1', 'Respondé este mail o escribinos al WhatsApp. Te enviamos el link de la videollamada en el día.'],
        ['2', 'Demo de 30 minutos en vivo. Sin PowerPoint: el sistema funcionando con datos reales.'],
        ['3', 'Elegís Propuesta A o B, firmamos el acuerdo y arrancamos en la semana siguiente.'],
        ['4', 'En 4 semanas tu club está operando con Germina.'],
    ]
    tpp = Table(pasos, colWidths=[0.8*cm, 14.2*cm])
    tpp.setStyle(TableStyle([
        ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR',     (0,0), (0,-1), G_MID),
        ('FONTSIZE',      (0,0), (-1,-1), 10),
        ('FONTNAME',      (1,0), (1,-1), 'Helvetica'),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW',     (0,0), (-1,-2), 0.2, G_BORDER),
    ]))
    s.append(tpp)
    s.append(Spacer(1, 0.6*cm))

    contacto_box = [[Paragraph(
        '📧  <b>besparkcreativa@gmail.com</b><br/>'
        '📱  Respondé este mail y te pasamos el WhatsApp directo<br/>'
        '🌐  germina-clubs.netlify.app',
        _st('ct', fontSize=10, textColor=G_INK, leading=17))]]
    tct = Table(contacto_box, colWidths=[15*cm])
    tct.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), G_CREAM),
        ('BOX',           (0,0), (-1,-1), 1.5, G_MID),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
    ]))
    s.append(tct)
    s.append(Spacer(1, 1*cm))

    s.append(HRFlowable(width='100%', thickness=1, color=G_MID, spaceAfter=10))
    footer = [[
        Paragraph('<b>Spark Creativa</b><br/>besparkcreativa@gmail.com',
                  _st('fl', fontSize=8, textColor=G_GRIS, leading=12)),
        Paragraph(f'<b>Germina</b> · germina-clubs.netlify.app<br/>'
                  f'Propuesta válida hasta {validez}',
                  _st('fr', fontSize=8, textColor=G_GRIS, leading=12, alignment=TA_RIGHT)),
    ]]
    tf = Table(footer, colWidths=[7.5*cm, 7.5*cm])
    tf.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 2)]))
    s.append(tf)

    doc.build(s)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════
#  MANUAL DE USUARIO
# ═══════════════════════════════════════════════════

def generar_manual():
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2*cm, bottomMargin=2.5*cm)

    H0  = _st('h0', fontName='Helvetica-Bold', fontSize=20, textColor=G_MID,  spaceBefore=22, spaceAfter=6,  leading=24)
    H1  = _st('h1', fontName='Helvetica-Bold', fontSize=13, textColor=G_MID,  spaceBefore=16, spaceAfter=5,  leading=17)
    BOD = _st('bd', fontSize=10, textColor=G_INK, spaceAfter=7, leading=15, alignment=TA_JUSTIFY)
    BUL = _st('bl', fontSize=10, textColor=G_INK, spaceAfter=5, leading=14, leftIndent=14, firstLineIndent=-10)
    FAQ_Q = _st('fq', fontName='Helvetica-Bold', fontSize=10, textColor=G_MID, spaceBefore=10, spaceAfter=3, leading=14)
    FAQ_A = _st('fa', fontSize=10, textColor=G_INK, spaceAfter=6, leading=14, leftIndent=10)

    s = []

    s.append(Spacer(1, 2*cm))
    s.append(Paragraph(
        '<font color="#1A3520"><b>Germi</b></font><font color="#C8A44A"><b>na</b></font>',
        _st('logo', fontName='Helvetica-Bold', fontSize=42, spaceAfter=6)))
    s.append(Paragraph('Manual de Usuario — Panel de Administración',
                        _st('mt', fontName='Helvetica-Bold', fontSize=20, textColor=G_INK, spaceAfter=6)))
    s.append(Paragraph('Guía completa para gestionar tu Cannabis Social Club con Germina',
                        _st('ms', fontSize=12, textColor=G_GRIS, spaceAfter=30)))
    s.append(HRFlowable(width='100%', thickness=2, color=G_MID, spaceAfter=20))

    indice = [
        ['#', 'Sección'],
        ['1', 'Acceso al sistema'],
        ['2', 'Panel de control (Dashboard)'],
        ['3', 'Gestión de socios'],
        ['4', 'Dispensario'],
        ['5', 'Catálogo de variedades'],
        ['6', 'Cuotas y membresías'],
        ['7', 'Control de aforo'],
        ['8', 'Portal del socio'],
        ['9', 'Reportes y exportación'],
        ['10','Preguntas frecuentes'],
    ]
    s.append(_header_table(indice, [1.5*cm, 13.5*cm]))
    s.append(PageBreak())

    s.append(Paragraph('1. Acceso al sistema', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Para acceder al panel de administración ingresá a la URL de tu club y completá los datos de acceso:', BOD))
    acceso = [
        ['Campo', 'Valor'],
        ['URL del panel',  'tu-club.onrender.com/admin'],
        ['Usuario',        'admin'],
        ['Contraseña',     'La que te asignamos durante la implementación'],
    ]
    s.append(_header_table(acceso, [5*cm, 10*cm]))
    s.append(_tip('Recomendamos cambiar la contraseña la primera vez que ingreses. Compartila solo con personal autorizado.'))

    s.append(Paragraph('2. Panel de control (Dashboard)', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('El Dashboard es la pantalla principal. Muestra el estado de tu club en tiempo real.', BOD))
    s.append(Paragraph('Bloque HOY', H1))
    s.append(Paragraph('• <b>Nuevas solicitudes</b>: socios que enviaron su formulario de ingreso hoy.', BUL))
    s.append(Paragraph('• <b>Dispensaciones</b>: cantidad de retiros realizados en el día.', BUL))
    s.append(Paragraph('• <b>Aforo actual</b>: socios presentes en este momento.', BUL))
    s.append(Paragraph('• <b>Cuotas vencidas</b>: socios con cuota expirada que requieren atención.', BUL))
    s.append(_tip('Si el número de alertas está en rojo, hay algo que requiere atención inmediata. Revisá la sección antes de arrancar el día.'))

    s.append(PageBreak())
    s.append(Paragraph('3. Gestión de socios', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Socios</b>. Lista completa con búsqueda por nombre o DNI.', BOD))
    etapas = [
        ['Etapa', 'Significado', 'Acción recomendada'],
        ['Solicitud',         'Formulario recibido, pendiente',         'Revisar y contactar al interesado'],
        ['En proceso',        'Completando documentación',              'Hacer seguimiento y asistir'],
        ['Documentación OK',  'Docs entregados y verificados',          'Aprobar y activar la membresía'],
        ['Activo',            'Socio habilitado para retirar',          'Ninguna — socio operativo'],
        ['Suspendido',        'Membresía pausada',                      'Revisar motivo y reactivar'],
        ['Inactivo',          'Sin actividad prolongada',               'Contactar para retener o dar de baja'],
    ]
    s.append(_header_table(etapas, [3.5*cm, 5.5*cm, 6*cm]))
    s.append(_tip('Podés cambiar la etapa del socio directamente desde su ficha. El cambio queda registrado con fecha y hora.'))

    s.append(PageBreak())
    s.append(Paragraph('4. Dispensario', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Dispensario</b>. Aquí registrás cada retiro de un socio.', BOD))
    s.append(Paragraph('1. Buscá al socio por nombre o DNI.', BUL))
    s.append(Paragraph('2. Seleccioná la variedad del catálogo visual.', BUL))
    s.append(Paragraph('3. Ingresá la cantidad en gramos a dispensar.', BUL))
    s.append(Paragraph('4. Confirmá el retiro. El sistema verifica que no supere el cupo mensual.', BUL))
    s.append(Paragraph('5. La dispensación queda registrada con trazabilidad completa.', BUL))
    s.append(_tip('Si el socio ya consumió su cupo mensual, el sistema lo alerta antes de permitir confirmar.'))

    s.append(Paragraph('5. Catálogo de variedades', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Variedades</b>. Cargá y administrá todas las cepas disponibles.', BOD))
    s.append(Paragraph('• <b>Nombre</b>, <b>Genética</b> (Sativa/Índica/Híbrida/Alto CBD)', BUL))
    s.append(Paragraph('• <b>THC %</b> y <b>CBD %</b>: concentraciones verificadas', BUL))
    s.append(Paragraph('• <b>Efectos</b>, <b>Indicaciones</b>, <b>Sabor</b>, <b>Imagen</b> (URL)', BUL))
    s.append(_tip('Podés desactivar variedades sin borrarlas. Las inactivas no aparecen en el dispensario ni en el portal.'))

    s.append(PageBreak())
    s.append(Paragraph('6. Cuotas y membresías', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    cuotas_t = [
        ['Tipo', 'Duración', 'Vencimiento automático'],
        ['Mensual',    '1 mes',   '30 días desde el pago'],
        ['Trimestral', '3 meses', '90 días desde el pago'],
        ['Semestral',  '6 meses', '180 días desde el pago'],
        ['Anual',      '1 año',   '365 días desde el pago'],
    ]
    s.append(_header_table(cuotas_t, [4*cm, 4*cm, 7*cm]))
    s.append(_tip('Las cuotas vencidas aparecen en el Dashboard. El portal del socio también muestra su estado de cuota.'))

    s.append(Paragraph('7. Control de aforo', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Aforo</b>. Control de socios presentes en tiempo real.', BOD))
    s.append(Paragraph('• El contador muestra entradas menos salidas del día.', BUL))
    s.append(Paragraph('• Registrá entradas y salidas buscando al socio por nombre.', BUL))
    s.append(Paragraph('• La lista "Socios dentro ahora" muestra quién está presente.', BUL))
    s.append(_tip('El número de aforo aparece en el Dashboard. Haciendo clic llegás directo a esta pantalla.'))

    s.append(PageBreak())
    s.append(Paragraph('8. Portal del socio', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Cada socio tiene su portal personal desde el celular. Accede ingresando su DNI. No requiere contraseña.', BOD))
    s.append(Paragraph('• <b>Inicio</b>: carnet digital con QR, estado de cuota y cupo mensual.', BUL))
    s.append(Paragraph('• <b>Flores</b>: catálogo con fichas y calificación por estrellas.', BUL))
    s.append(Paragraph('• <b>Historial</b>: todos los retiros agrupados por mes.', BUL))
    s.append(Paragraph('• <b>Perfil</b>: datos personales, documentación y QR de identificación.', BUL))
    s.append(Paragraph('<b>Acceso del socio</b>: Landing del club → botón "Soy socio" → ingresan DNI → acceden al portal.', BOD))
    s.append(_tip('El QR del carnet puede escanearse en el club para identificar al socio sin que ingrese datos.'))

    s.append(Paragraph('9. Reportes y exportación', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('• <b>Informe del día</b>: resumen automático de dispensaciones, altas, cuotas y aforo.', BUL))
    s.append(Paragraph('• <b>Exportar CSV</b>: lista completa de socios para Excel o Google Sheets.', BUL))
    s.append(_tip('El informe del día es ideal para la reunión semanal del equipo.'))

    s.append(PageBreak())
    s.append(Paragraph('10. Preguntas frecuentes', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))

    faqs = [
        ('¿Qué pasa si un socio intenta retirar más de su cupo mensual?',
         'El sistema lo detecta y muestra una alerta antes de confirmar. No se puede superar el cupo sin aprobación manual del administrador.'),
        ('¿Puedo migrar socios que ya tengo?',
         'Sí. Durante la implementación te ayudamos a migrar tu base existente. También podés cargarlos manualmente en cualquier momento.'),
        ('¿Los datos de los socios están seguros?',
         'La base de datos está alojada en servidor con backups automáticos. Solo vos (con credenciales de admin) podés acceder.'),
        ('¿Puedo usar el panel desde el celular?',
         'El panel de administración está optimizado para desktop. El portal del socio sí está diseñado para celular.'),
        ('¿Qué hago si una variedad se agota?',
         'Desde el catálogo podés desactivarla con un clic. No aparece en el dispensario ni en el portal hasta que la reactives.'),
        ('¿Qué hago si olvidé la contraseña?',
         'Contactá a Germina y te reseteamos el acceso en el mismo día.'),
    ]
    for q, a in faqs:
        s.append(Paragraph(f'P: {q}', FAQ_Q))
        s.append(Paragraph(f'R: {a}', FAQ_A))

    s.append(Spacer(1, 1*cm))
    s.append(HRFlowable(width='100%', thickness=1, color=G_MID, spaceAfter=10))
    s.append(Paragraph(
        '¿Necesitás ayuda? Escribinos a <b>besparkcreativa@gmail.com</b><br/>'
        'Respondemos en menos de 24 horas hábiles.',
        _st('ct', fontSize=10, textColor=G_GRIS, alignment=TA_CENTER, leading=15)))

    doc.build(s)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════
#  LIBRO DE MOVIMIENTOS
# ═══════════════════════════════════════════════════

def generar_libro_movimientos(entradas, salidas, desde, hasta):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.8*cm, bottomMargin=2*cm)

    H0  = _st('h0', fontName='Helvetica-Bold', fontSize=16, textColor=G_MID, spaceBefore=0,  spaceAfter=4)
    H1  = _st('h1', fontName='Helvetica-Bold', fontSize=11, textColor=G_MID, spaceBefore=14, spaceAfter=4)
    SML = _st('sm', fontName='Helvetica-Oblique', fontSize=8, textColor=G_GRIS, spaceAfter=4, leading=11)
    s = []

    s.append(Paragraph('<font color="#1A3520"><b>Germi</b></font><font color="#C8A44A"><b>na</b></font> — Libro de Movimientos', H0))
    s.append(HRFlowable(width='100%', thickness=1.5, color=G_MID, spaceAfter=6))
    s.append(Paragraph(f'Período: {desde} al {hasta}   ·   Emitido: {date.today().isoformat()}', SML))
    s.append(Spacer(1, 0.4*cm))

    total_e = round(sum(float(r['gramos'] or 0) for r in entradas), 1)
    total_s = round(sum(float(r['gramos'] or 0) for r in salidas), 1)
    stock   = round(total_e - total_s, 1)
    kpi_data = [
        ['Total ingresado', 'Total distribuido', 'Stock actual', 'Lotes'],
        [f'{total_e} g', f'{total_s} g', f'{stock} g', str(len(entradas))],
    ]
    kt = Table(kpi_data, colWidths=[3.8*cm]*4)
    kt.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('FONTNAME',      (0,1), (-1,1),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,1), (-1,1),  13),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND',    (0,1), (-1,1),  G_CREAM),
        ('GRID',          (0,0), (-1,-1), 0.3, G_BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    s.append(kt)
    s.append(Spacer(1, 0.5*cm))

    s.append(Paragraph('Entradas — Cosechas registradas', H1))
    e_data = [['Fecha', 'Lote', 'Variedad', 'Cultivador', 'Peso seco', 'CoA', 'THC%', 'CBD%', 'Laboratorio']]
    for r in entradas:
        e_data.append([
            str(r['fecha'] or ''),
            str(r['lote_codigo'] or '—'),
            str(r['variedad'] or ''),
            str(r['responsable'] or '—'),
            f"{float(r['gramos'] or 0):.1f} g",
            str(r['coa_status'] or 'pendiente'),
            f"{r['thc_real_pct']}%" if r['thc_real_pct'] else '—',
            f"{r['cbd_real_pct']}%" if r['cbd_real_pct'] else '—',
            str(r['laboratorio'] or '—'),
        ])
    et = _header_table(e_data, [1.8*cm, 2.8*cm, 2.5*cm, 2.5*cm, 1.8*cm, 1.7*cm, 1.2*cm, 1.2*cm, 2.5*cm])
    s.append(et)
    s.append(Spacer(1, 0.5*cm))

    s.append(Paragraph('Salidas — Dispensaciones y pedidos entregados', H1))
    sal_data = [['Fecha', 'Lote origen', 'Variedad', 'Socio', 'DNI', 'Gramos', 'Registrado por']]
    for r in salidas:
        sal_data.append([
            str(r['fecha'] or ''),
            str(r['lote_codigo'] or '—'),
            str(r['variedad'] or ''),
            str(r['socio'] or ''),
            str(r['dni'] or '—'),
            f"{float(r['gramos'] or 0):.1f} g",
            str(r['registrado_por'] or '—'),
        ])
    st2 = _header_table(sal_data, [1.8*cm, 2.8*cm, 2.8*cm, 3.5*cm, 2.2*cm, 1.8*cm, 3.1*cm])
    s.append(st2)
    s.append(Spacer(1, 0.3*cm))
    s.append(Paragraph(f'TOTAL SALIDAS: {total_s} g',
                        _st('tot', fontName='Helvetica-Bold', fontSize=9, textColor=G_MID, spaceAfter=6)))

    s.append(Spacer(1, 1*cm))
    s.append(HRFlowable(width='100%', thickness=0.5, color=G_BORDER, spaceAfter=6))
    s.append(Paragraph('Firma responsable: ___________________________   Fecha: _______________   Sello:',
                        _st('fi', fontSize=9, textColor=G_GRIS, spaceAfter=4)))

    doc.build(s)
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════
#  INFORME INCB
# ═══════════════════════════════════════════════════

def generar_informe_incb(nombre_club, anio, lotes, produccion, distribucion, total_socios, socios_reprocann):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.8*cm, bottomMargin=2*cm)

    H0  = _st('h0', fontName='Helvetica-Bold', fontSize=15, textColor=G_MID, spaceBefore=0,  spaceAfter=4)
    H1  = _st('h1', fontName='Helvetica-Bold', fontSize=11, textColor=G_MID, spaceBefore=14, spaceAfter=4)
    BOD = _st('bd', fontSize=9,  textColor=G_INK, spaceAfter=5, leading=13)
    SML = _st('sm', fontName='Helvetica-Oblique', fontSize=8, textColor=G_GRIS, spaceAfter=4, leading=11)
    s = []

    s.append(Paragraph('<font color="#1A3520"><b>Germi</b></font><font color="#C8A44A"><b>na</b></font> — Informe INCB', H0))
    s.append(HRFlowable(width='100%', thickness=1.5, color=G_MID, spaceAfter=4))
    s.append(Paragraph('JUNTA INTERNACIONAL DE FISCALIZACIÓN DE ESTUPEFACIENTES', _st('sub', fontName='Helvetica-Bold', fontSize=8, textColor=G_GRIS, spaceAfter=2)))
    s.append(Paragraph(f'Año de referencia: {anio}   ·   Emitido: {date.today().isoformat()}', SML))
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('1. Datos del establecimiento', H1))
    club_data = [
        ['Club', nombre_club],
        ['País', 'Argentina'],
        ['Marco legal', 'Ley 27.350 — Programa REPROCANN'],
        ['Socios activos', str(total_socios)],
        ['Socios con REPROCANN', str(socios_reprocann)],
        ['Período informado', f'01/01/{anio} — 31/12/{anio}'],
    ]
    ct = Table(club_data, colWidths=[5*cm, 12*cm])
    ct.setStyle(TableStyle([
        ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('GRID',          (0,0), (-1,-1), 0.3, G_BORDER),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [colors.white, G_CREAM]),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    s.append(ct)
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('2. Producción — Cannabis cosechado', H1))
    prod_data = [['Variedad', 'Peso seco total (g)', 'N° lotes']]
    total_prod = 0
    for p in produccion:
        prod_data.append([str(p['variedad']), f"{float(p['total_g']):.1f}", str(p['lotes'])])
        total_prod += float(p['total_g'])
    prod_data.append(['TOTAL', f'{round(total_prod,1):.1f}', str(len(lotes))])
    pt = Table(prod_data, colWidths=[8*cm, 5*cm, 4*cm])
    pt.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0),  (-1,0),  colors.white),
        ('FONTNAME',      (0,0),  (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),  (-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),  (-1,-2), [colors.white, G_CREAM]),
        ('BACKGROUND',    (0,-1), (-1,-1), G_VERDE),
        ('TEXTCOLOR',     (0,-1), (-1,-1), colors.white),
        ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID',          (0,0),  (-1,-1), 0.3, G_BORDER),
        ('LEFTPADDING',   (0,0),  (-1,-1), 8),
        ('TOPPADDING',    (0,0),  (-1,-1), 6),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 6),
        ('ALIGN',         (1,0),  (2,-1),  'CENTER'),
    ]))
    s.append(pt)
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('3. Distribución — Cannabis dispensado a socios', H1))
    dist_data = [['Variedad', 'Total distribuido (g)']]
    total_dist = 0
    for d in distribucion:
        dist_data.append([str(d['variedad']), f"{float(d['total_g']):.1f}"])
        total_dist += float(d['total_g'])
    dist_data.append(['TOTAL', f'{round(total_dist,1):.1f}'])
    dt = Table(dist_data, colWidths=[10*cm, 7*cm])
    dt.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0),  (-1,0),  colors.white),
        ('FONTNAME',      (0,0),  (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),  (-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),  (-1,-2), [colors.white, G_CREAM]),
        ('BACKGROUND',    (0,-1), (-1,-1), G_VERDE),
        ('TEXTCOLOR',     (0,-1), (-1,-1), colors.white),
        ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID',          (0,0),  (-1,-1), 0.3, G_BORDER),
        ('LEFTPADDING',   (0,0),  (-1,-1), 8),
        ('TOPPADDING',    (0,0),  (-1,-1), 6),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 6),
        ('ALIGN',         (1,0),  (1,-1),  'CENTER'),
    ]))
    s.append(dt)
    s.append(Spacer(1, 0.4*cm))

    stock_g = round(total_prod - total_dist, 1)
    s.append(Paragraph('4. Reconciliación de existencias', H1))
    bal_data = [
        ['Concepto', 'Gramos (g)'],
        ['Producción total (entradas)', f'{round(total_prod,1):.1f}'],
        ['Distribución total (salidas)', f'–{round(total_dist,1):.1f}'],
        ['Stock disponible estimado', f'{stock_g:.1f}'],
    ]
    bt = Table(bal_data, colWidths=[10*cm, 7*cm])
    bt.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0),  G_MID),
        ('TEXTCOLOR',     (0,0),  (-1,0),  colors.white),
        ('FONTNAME',      (0,0),  (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),  (-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),  (-1,-2), [colors.white, G_CREAM]),
        ('BACKGROUND',    (0,-1), (-1,-1), colors.HexColor('#EAF7EA')),
        ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID',          (0,0),  (-1,-1), 0.3, G_BORDER),
        ('LEFTPADDING',   (0,0),  (-1,-1), 8),
        ('TOPPADDING',    (0,0),  (-1,-1), 6),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 6),
        ('ALIGN',         (1,0),  (1,-1),  'CENTER'),
    ]))
    s.append(bt)
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('5. Registro de lotes — Certificados de Análisis (CoA)', H1))
    lot_data = [['Lote', 'Variedad', 'Fecha', 'THC%', 'CBD%', 'CoA', 'Pesticidas', 'Metales', 'Microb.']]
    for l in lotes:
        lot_data.append([
            str(l['lote_codigo'] or ''),
            str(l['variedad'] or ''),
            str(l['fecha'] or ''),
            f"{l['thc_real_pct']}%" if l['thc_real_pct'] else '—',
            f"{l['cbd_real_pct']}%" if l['cbd_real_pct'] else '—',
            str(l['coa_status'] or 'pendiente'),
            str(l['pesticidas_status'] or '—'),
            str(l['metales_status'] or '—'),
            str(l['microbiologia_status'] or '—'),
        ])
    if lotes:
        lt = _header_table(lot_data, [2.8*cm, 2.5*cm, 1.8*cm, 1.3*cm, 1.3*cm, 1.8*cm, 2*cm, 1.8*cm, 1.7*cm])
        s.append(lt)
    else:
        s.append(Paragraph('Sin lotes registrados en el período.', BOD))
    s.append(Spacer(1, 0.4*cm))

    s.append(Paragraph('6. Declaración de cumplimiento', H1))
    checks = [
        ['✓', 'Trazabilidad seed-to-sale documentada por lote (GACP/GMP)'],
        ['✓', 'Registro de cosechas con número de lote LOT-AAAA-MM-XXXX'],
        ['✓', 'Certificados de Análisis (CoA) por lote: THC%, CBD%, pesticidas, metales, microbiología'],
        ['✓', 'Dispensaciones vinculadas a lote de origen con ID de socio y REPROCANN'],
        ['✓', 'Libro de Movimientos (entradas/salidas) disponible para auditoría'],
        ['✓', 'Socios registrados bajo Ley 27.350 — REPROCANN'],
    ]
    cht = Table(checks, colWidths=[0.6*cm, 16.4*cm])
    cht.setStyle(TableStyle([
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('TEXTCOLOR',     (0,0), (0,-1),  colors.HexColor('#166534')),
        ('FONTNAME',      (0,0), (0,-1),  'Helvetica-Bold'),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW',     (0,0), (-1,-2), 0.2, G_BORDER),
    ]))
    s.append(cht)
    s.append(Spacer(1, 0.8*cm))

    firma_data = [[
        Paragraph('Responsable técnico:\n\n\n___________________________\nNombre y firma', SML),
        Paragraph('Director / Presidente:\n\n\n___________________________\nNombre y firma', SML),
        Paragraph('Sello del club:\n\n\n\n', SML),
    ]]
    ft = Table(firma_data, colWidths=[5.5*cm, 5.5*cm, 6*cm])
    ft.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('TOPPADDING', (0,0), (-1,-1), 4)]))
    s.append(ft)
    s.append(Spacer(1, 0.4*cm))
    s.append(HRFlowable(width='100%', thickness=0.5, color=G_BORDER, spaceAfter=6))
    s.append(Paragraph(f'Generado por Germina · Sistema de gestión GACP/REPROCANN · {date.today().isoformat()}',
                        _st('fo', fontSize=7, textColor=G_GRIS, alignment=TA_CENTER, leading=10)))

    doc.build(s)
    buf.seek(0)
    return buf
