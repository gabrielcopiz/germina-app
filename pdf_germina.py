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
    s.append(Paragraph('Plataforma de Gestión para Cannabis Social Clubs',
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
        f'<b>Germina</b> es la primera plataforma SaaS especializada en la gestión integral de '
        f'Cannabis Social Clubs (CSC) en Argentina. Diseñada para cumplir con la Ley 27.350, '
        f'digitaliza y profesionaliza todas las operaciones del club: admisión de socios, '
        f'trazabilidad completa del ciclo productivo, dispensario, cuotas, portal del socio '
        f'y reportería. Todo en un solo lugar, sin servidores propios, sin inversión en IT.',
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
    # DIAGNÓSTICO
    # ══════════════════════════════════════════════
    s.append(Paragraph('Los clubes que más crecen son los primeros en perder el control', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'A medida que un CSC crece, la operación manual deja de ser sostenible. '
        'Lo que antes se manejaba con una planilla y buena voluntad, hoy genera errores, '
        'riesgos legales y socios insatisfechos. Estos son los cuatro problemas que vemos '
        'repetirse en casi todos los clubes:', BOD))

    dolores = [
        ['Problema', 'Consecuencia real'],
        ['Trazabilidad manual o inexistente',
         'No podés demostrar de dónde viene cada gramo ni a quién fue. '
         'Ante una inspección o demanda legal, eso es indefendible.'],
        ['Stock sin control: mermas invisibles',
         'Sin registro digital, los errores y mermas se acumulan en silencio. '
         'Los clubes pierden entre 8 y 15 % de su producción sin saberlo.'],
        ['Gestión de socios en planillas o papel',
         'Cuotas vencidas que nadie cobra, documentación incompleta, socios activos '
         'que no deberían estarlo. Cada error es una responsabilidad del club.'],
        ['Imagen institucional desactualizada',
         'Los socios comparan tu club con cualquier servicio digital que usan. '
         'Un WhatsApp y una planilla no generan confianza ni fidelización.'],
    ]
    td = _header_table(dolores, [4.5*cm, 10.5*cm])
    s.append(td)
    s.append(Spacer(1, 0.4*cm))
    s.append(_tip('Ninguno de estos problemas requiere más personal. Requieren el sistema correcto.'))
    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # LA SOLUCIÓN
    # ══════════════════════════════════════════════
    s.append(Paragraph('La plataforma Germina: todo lo que tu club necesita', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))

    modulos = [
        ['Módulo', 'Qué resuelve'],
        ['Panel de administración',   'Dashboard con KPIs en tiempo real: socios, dispensaciones, cuotas, alertas de aforo. Vista completa del club en una pantalla.'],
        ['Gestión de socios',         'Alta, etapas del proceso (solicitud → activo), documentación, notas internas y control de cupos. Sin planillas.'],
        ['Dispensario digital',        'Cada dispensación queda registrada con variedad, gramos, socio y fecha. Trazabilidad completa en tiempo real.'],
        ['Ciclo productivo',           'Registro del flujo Semilla → Germinación → Vegetativa → Floración → Cosecha → Curado → Stock → Entrega.'],
        ['Catálogo de variedades',     'Fichas con genética, THC/CBD, efectos, indicaciones y fotos. Visible para administradores y socios.'],
        ['Control de cuotas',          'Registro de pagos, vencimientos automáticos y alertas. El socio ve su estado en tiempo real desde su portal.'],
        ['Control de aforo',           'Entradas y salidas en tiempo real. Lista de socios presentes con hora exacta. Registro histórico diario.'],
        ['Portal del socio (mobile)',  'App web desde el celular: carnet digital con QR, cupo disponible, catálogo con calificaciones e historial personal.'],
        ['Pedidos y delivery',         'Gestión de pedidos con código único, estado y seguimiento. El socio recibe su orden sin pasar por el club.'],
        ['Reportes y exportación',     'Informe del día automático. Exportación CSV de socios y dispensaciones. Todo listo para tu contador o auditoría.'],
    ]
    s.append(_header_table(modulos, [4.5*cm, 10.5*cm]))
    s.append(Spacer(1, 0.5*cm))

    # Antes / Después
    s.append(Paragraph('Antes y después de implementar Germina', H2))
    comp = [
        ['Sin Germina', 'Con Germina'],
        ['12 horas semanales en administración manual', '< 1 hora semanal. El sistema hace el registro solo.'],
        ['Mermas invisibles: 8–15% del stock sin explicación', 'Trazabilidad total. Cada gramo tiene origen, destino y fecha.'],
        ['Socios gestionados en WhatsApp y papel', 'Portal digital con carnet QR, historial y cuota en tiempo real.'],
        ['Cuotas que se cobran cuando alguien se acuerda', 'Alertas automáticas. El socio ve su vencimiento desde el celular.'],
        ['Imagen informal que genera desconfianza', 'Club profesional que fideliza socios y atrae nuevos por reputación.'],
        ['Imposible escalar más de 30–40 socios sin caos', 'Sistema diseñado para crecer: funciona igual con 20 o 300 socios.'],
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
    # PROPUESTA A
    # ══════════════════════════════════════════════
    s.append(Paragraph('Propuesta A — Implementación Estándar', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Acceso completo a la plataforma con implementación guiada, '
        'configuración a medida del club y soporte dedicado durante los primeros 3 meses.', BOD))

    # Desglose
    s.append(Paragraph('Desglose de la implementación (USD 7.500)', H2))
    desglose = [
        ['Concepto', 'Detalle', 'Valor'],
        ['Configuración del entorno',
         'Setup del servidor, dominio, base de datos y backup automático.',
         'USD 800'],
        ['Migración de socios',
         'Carga e importación de socios existentes (hasta 200). Validación de datos.',
         'USD 600'],
        ['Configuración del portal del socio',
         'Identidad visual del club, variedades iniciales y QR de socios.',
         'USD 700'],
        ['Integración del ciclo productivo',
         'Configuración del flujo completo Semilla → Entrega según tu operación.',
         'USD 900'],
        ['Capacitación del equipo',
         'Hasta 3 sesiones de 90 minutos con el equipo. Manual incluido.',
         'USD 500'],
        ['Desarrollo a medida + ajustes',
         'Adaptaciones específicas del club durante la implementación.',
         'USD 1.500'],
        ['Soporte técnico 3 meses',
         'Respuesta en menos de 24 horas. Canal directo con el equipo.',
         'USD 900'],
        ['Licencia primer año',
         'Acceso completo a la plataforma y actualizaciones incluidas.',
         'USD 1.600'],
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

    # ROI
    s.append(Paragraph('Retorno sobre la inversión (ROI estimado)', H2))
    s.append(Paragraph(
        'El siguiente cálculo es conservador y se basa en un club con 40 socios y cuota mensual '
        'de $8.000 ARS (≈ USD 8). Ajustá los números a tu realidad:', BOD))
    roi = [
        ['Concepto', 'Mensual', 'Anual'],
        ['Ingresos por cuotas (40 socios × USD 8)', 'USD 320', 'USD 3.840'],
        ['Ahorro en tiempo admin (10h/semana × USD 5/h)', 'USD 200', 'USD 2.400'],
        ['Reducción de mermas (10% de USD 500 en stock)', 'USD 50', 'USD 600'],
        ['Total beneficio estimado', 'USD 570', 'USD 6.840'],
        ['Mantenimiento mensual (desde mes 4)', '–USD 300', '–USD 2.700'],
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
    s.append(NOT)
    s.append(Paragraph(
        '* Cálculo estimativo. Los valores reales variarán según el tamaño del club, '
        'cuota, stock y eficiencia del equipo.', NOT))
    s.append(Spacer(1, 0.4*cm))

    # Pago
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
        'Diseñada para CSC en crecimiento que prefieren reducir la inversión inicial. '
        'Germina absorbe gran parte del costo de implementación y a cambio participa '
        'mensualmente en los ingresos que el club genera a través de la plataforma. '
        'Es un modelo de <b>piel en el juego</b>: nos va bien cuando a vos te va bien.', BOD))

    pb = [
        ['Concepto', 'Condición'],
        ['Costo de implementación',      'USD 3.500 (Germina absorbe USD 4.000 del valor total)'],
        ['Participación mensual',         '15% sobre ingresos netos del sistema'],
        ['Mantenimiento mensual',         'Incluido en la participación (sin costo adicional)'],
        ['Duración mínima del acuerdo',   '12 meses calendario desde la firma'],
        ['Renovación',                    'Automática mes a mes a partir del mes 13'],
        ['Cláusula de salida',            'Preaviso de 30 días a partir del mes 13'],
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
        'los datos de sus socios y operaciones. Germina no tiene acceso a la información '
        'individual de socios ni puede utilizarla con ningún fin comercial. '
        'Si el acuerdo termina, el club recibe una exportación completa de toda su base de datos '
        'en formato abierto (CSV/JSON) dentro de las 48 horas.',
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
    s.append(Paragraph('Resultados del club piloto', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'Germina está operativo en producción real. A continuación compartimos '
        'los resultados del club piloto con el que desarrollamos y validamos la plataforma '
        '(datos anonimizados por acuerdo de confidencialidad):', BOD))

    piloto = [
        ['Dato del club piloto', 'Detalle'],
        ['Localización',          'Gran Buenos Aires (zona norte)'],
        ['Socios al inicio',      '38 socios activos gestionados manualmente'],
        ['Tiempo de implementación', '4 semanas (dentro del plazo garantizado)'],
    ]
    s.append(_header_table(piloto, [6*cm, 9*cm]))
    s.append(Spacer(1, 0.4*cm))

    resultados = [
        ['Métrica', 'Antes', 'Después (90 días)', 'Variación'],
        ['Tiempo admin semanal',    '14 horas',   '1.5 horas',  '–89%'],
        ['Socios con cuota al día', '61%',        '94%',        '+33 pp'],
        ['Mermas no explicadas',    '12% del stock', '< 1%',    '–91%'],
        ['Satisfacción del socio',  'Sin medir',  '4.7/5 ★',   'Nuevo KPI'],
        ['Tiempo de alta de socio', '3–5 días',   '< 2 horas', '–90%'],
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
    s.append(NOT)
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
         'El portal del socio funciona desde el celular del socio con cualquier conexión.'),
        ('¿Puedo seguir usando el sistema si no renuevo el mantenimiento?',
         'El acceso al sistema está vinculado al pago del mantenimiento mensual. '
         'Si elegís no renovar, acordamos un período de 30 días para exportar todos tus datos '
         'antes del cierre de acceso. Nunca perdés información.'),
        ('¿Germina tiene acceso a los datos de salud de mis socios?',
         'No. Los datos de diagnóstico, médico prescriptor y documentación de los socios '
         'están alojados en el servidor del club. Germina no tiene acceso a esa información '
         'y no puede utilizarla con ningún fin. El club es el único responsable de su custodia.'),
    ]

    for q, a in faqs:
        s.append(Paragraph(f'❓ {q}', FAQ_Q))
        s.append(Paragraph(a, FAQ_A))

    s.append(PageBreak())

    # ══════════════════════════════════════════════
    # CRONOGRAMA + GARANTÍAS
    # ══════════════════════════════════════════════
    s.append(Paragraph('Implementación en 4 semanas', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    crono = [
        ['Semana', 'Actividades'],
        ['Semana 1', 'Configuración del entorno · Carga inicial de datos · Definición de variedades y cupos'],
        ['Semana 2', 'Migración de socios · Configuración del portal del socio · Pruebas internas'],
        ['Semana 3', 'Capacitación del equipo · Ajustes específicos · Prueba piloto con socios seleccionados'],
        ['Semana 4', 'Lanzamiento oficial · Soporte intensivo · Entrega de documentación y manual'],
    ]
    tc = _header_table(crono, [3.5*cm, 11.5*cm])
    tc.setStyle(TableStyle([
        ('FONTNAME',  (0,1), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,1), (0,-1), G_MID),
    ]), overrideFlowable=False)
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
    s.append(Paragraph('El siguiente paso es simple', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        f'Esta propuesta tiene validez hasta el <b>{validez}</b>. '
        f'Después de esa fecha los valores pueden ajustarse.', BOD))
    s.append(Paragraph(
        'Te proponemos una demo de 30 minutos por videollamada. '
        'Sin presentaciones de PowerPoint: te mostramos la plataforma funcionando en vivo, '
        'con datos reales, respondemos todas tus dudas y si decidís avanzar '
        'arrancamos en la semana siguiente.', BOD))

    pasos = [
        ['1', f'Respondé este mail o escribinos al WhatsApp confirmando que querés la demo. Te enviamos link de videollamada en el día.'],
        ['2', f'Demo de 30 minutos. Te mostramos todo en vivo. Sin compromiso.'],
        ['3', f'Si querés avanzar, elegís Propuesta A o B, firmamos el acuerdo y arrancamos la implementación.'],
        ['4', f'En 4 semanas tu club está operando con Germina.'],
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
        '🌐  germina-app.onrender.com/contacto-club',
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
        Paragraph(f'<b>Germina</b> · germina-app.onrender.com<br/>'
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
