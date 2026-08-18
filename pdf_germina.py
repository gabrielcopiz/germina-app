from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, PageBreak)

# ── Paleta Germina ──
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

    H0  = _st('h0',  fontName='Helvetica-Bold', fontSize=26, textColor=G_MID,   spaceBefore=0,  spaceAfter=6,  leading=30)
    H1  = _st('h1',  fontName='Helvetica-Bold', fontSize=15, textColor=G_MID,   spaceBefore=20, spaceAfter=6,  leading=20)
    H2  = _st('h2',  fontName='Helvetica-Bold', fontSize=11, textColor=G_INK,   spaceBefore=14, spaceAfter=5,  leading=15)
    BOD = _st('bod', fontSize=10, textColor=G_INK,  spaceAfter=7, leading=15, alignment=TA_JUSTIFY)
    BUL = _st('bul', fontSize=10, textColor=G_INK,  spaceAfter=5, leading=14, leftIndent=14, firstLineIndent=-10)
    SML = _st('sml', fontName='Helvetica-Oblique', fontSize=8, textColor=G_GRIS, spaceAfter=5, leading=12)
    NOT = _st('not', fontName='Helvetica-Oblique', fontSize=9, textColor=G_GRIS, spaceAfter=6, leading=13)

    s = []
    fecha = _fecha_es()

    # ── PORTADA ──────────────────────────────────────────
    s.append(Spacer(1, 1.2*cm))
    s.append(Paragraph(
        '<font color="#1A3520"><b>Germi</b></font><font color="#C8A44A"><b>na</b></font>',
        _st('logo', fontName='Helvetica-Bold', fontSize=40, spaceAfter=4)))
    s.append(Paragraph('Plataforma de Gestión para Cannabis Social Clubs',
                        _st('lsub', fontSize=12, textColor=G_GRIS, spaceAfter=28)))
    s.append(HRFlowable(width='100%', thickness=2, color=G_MID, spaceAfter=28))
    s.append(Paragraph('Propuesta Comercial', H0))
    s.append(Paragraph(f'Preparada para <b>{club_nombre}</b>',
                        _st('dest', fontSize=13, textColor=G_GRIS, spaceAfter=6)))
    s.append(Paragraph(f'Atención: {contacto_nombre}',
                        _st('at', fontSize=11, textColor=G_GRIS, spaceAfter=4)))
    s.append(Paragraph(f'Fecha: {fecha}',
                        _st('fe', fontSize=10, textColor=G_GRIS, spaceAfter=36)))

    intro = [[Paragraph(
        f'<b>Germina</b> es la primera plataforma SaaS especializada en la gestión integral de '
        f'Asociaciones Cannábicas Medicinales en Argentina. Diseñada para cumplir con la Ley 27.350, '
        f'permite digitalizar y profesionalizar todas las operaciones del club — desde la admisión de '
        f'socios hasta el control de dispensaciones, cuotas y trazabilidad completa.',
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

    # ── QUÉ INCLUYE ──────────────────────────────────────
    s.append(Paragraph('¿Qué incluye la plataforma?', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))

    modulos = [
        ['Módulo', 'Descripción'],
        ['Panel de administración',   'Dashboard con KPIs en tiempo real: socios, dispensaciones, cuotas, alertas y aforo.'],
        ['Gestión de socios',         'Alta, edición, etapas del proceso (solicitud → activo), documentación y notas.'],
        ['Dispensario digital',        'Registro de cada dispensación con variedad, gramos y trazabilidad completa.'],
        ['Catálogo de variedades',     'Fichas por cepa: genética, THC/CBD, efectos, indicaciones y calificaciones.'],
        ['Control de cuotas',          'Registro de pagos, vencimientos y alertas de cuotas vencidas.'],
        ['Control de aforo',           'Entradas y salidas en tiempo real. Lista de socios presentes en el club.'],
        ['Portal del socio',           'App mobile con carnet digital, historial, catálogo y sistema de calificaciones.'],
        ['Pedidos y delivery',         'Gestión de pedidos con código único, estado y seguimiento.'],
        ['Reportes y exportación',     'Exportación CSV de socios, reportes de actividad y trazabilidad.'],
        ['Informe del día',            'Resumen diario automático de operaciones, alertas y estadísticas.'],
    ]
    s.append(_header_table(modulos, [5*cm, 10*cm]))
    s.append(Spacer(1, 0.8*cm))

    # ── PROPUESTAS ────────────────────────────────────────
    s.append(Paragraph('Propuestas comerciales', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Presentamos dos modelos adaptados a la realidad de las asociaciones cannábicas medicinales argentinas:', BOD))

    # A
    s.append(Paragraph('Propuesta A — Implementación Estándar', H2))
    pa = [
        ['Concepto', 'Valor'],
        ['Implementación completa + configuración inicial', 'USD 7.500'],
        ['Capacitación del equipo (hasta 3 personas)',      'Incluida'],
        ['Soporte técnico 3 meses post-lanzamiento',        'Incluido'],
        ['Mantenimiento mensual (desde mes 4)',              'USD 300–500 / mes'],
    ]
    ta = _header_table(pa, [10*cm, 5*cm])
    ta.setStyle(TableStyle([
        ('ALIGN',     (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME',  (1,1), (1,1),  'Helvetica-Bold'),
        ('TEXTCOLOR', (1,1), (1,1),  G_MID),
        ('FONTSIZE',  (1,1), (1,1),  11),
    ]), overrideFlowable=False)
    s.append(ta)

    s.append(Spacer(1, 0.3*cm))
    pago_a = [
        ['Modalidad de pago', 'Monto'],
        ['Pago único (sin recargo)', 'USD 7.500'],
        ['En 3 cuotas (recargo financiero 8%)', '3 × USD 2.700 = USD 8.100'],
    ]
    tp = _header_table(pago_a, [10*cm, 5*cm])
    s.append(tp)
    s.append(Paragraph(
        '* El recargo del 8% sobre la opción en cuotas corresponde al costo financiero de diferimiento del pago.',
        NOT))

    s.append(Spacer(1, 0.5*cm))

    # B
    s.append(Paragraph('Propuesta B — Modelo de Asociación', H2))
    s.append(Paragraph(
        'Diseñada para asociaciones cannábicas medicinales en etapa de crecimiento. Germina '
        'absorbe gran parte del costo de implementación a cambio de una participación mensual '
        'en las ganancias netas del club.', BOD))
    pb = [
        ['Concepto', 'Valor'],
        ['Costo de implementación (diferido)', 'USD 3.500'],
        ['Participación sobre ganancias netas',  '15 % mensual'],
        ['Mantenimiento mensual',                'Incluido en la participación'],
        ['Duración mínima del acuerdo',          '12 meses'],
    ]
    s.append(_header_table(pb, [10*cm, 5*cm]))
    s.append(Spacer(1, 0.3*cm))

    notas_b_data = [[Paragraph('<b>Aclaraciones importantes sobre la Propuesta B</b>',
                               _st('nb0', fontName='Helvetica-Bold', fontSize=9,
                                   textColor=colors.HexColor('#7A5C00')))],
                    [Paragraph(
        '•  El costo de implementación de USD 3.500 representa <b>aproximadamente la mitad</b> del valor '
        'estándar (USD 7.500). Germina absorbe la diferencia a cambio de la participación mensual.',
        _st('nb', fontSize=9, textColor=G_INK, leading=14))],
                    [Paragraph(
        '•  El 15 % de participación se calcula sobre las <b>ganancias netas del club</b>: ingresos por '
        'cuotas y dispensaciones registrados en el sistema, menos costos operativos directos acordados '
        'contractualmente. El método de cálculo y auditoría se define antes de la firma.',
        _st('nb', fontSize=9, textColor=G_INK, leading=14))]]
    tnb = Table(notas_b_data, colWidths=[15*cm])
    tnb.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (0,0),   colors.HexColor('#FEF9EE')),
        ('BACKGROUND',    (0,1), (-1,-1), colors.HexColor('#FFFCF5')),
        ('BOX',           (0,0), (-1,-1), 0.5, G_GOLD),
        ('INNERGRID',     (0,0), (-1,-1), 0.2, G_BORDER),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('RIGHTPADDING',  (0,0), (-1,-1), 12),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    s.append(tnb)
    s.append(PageBreak())

    # ── CRONOGRAMA ────────────────────────────────────────
    s.append(Paragraph('Cronograma de implementación', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph(
        'La implementación completa tiene una duración máxima de <b>4 semanas corridas desde la '
        'firma del acuerdo</b>.', BOD))
    crono = [
        ['Semana', 'Actividades'],
        ['Semana 1', 'Configuración del entorno · Carga inicial de datos · Definición de variedades y cupos'],
        ['Semana 2', 'Migración de socios existentes · Configuración del portal · Pruebas internas'],
        ['Semana 3', 'Capacitación del equipo · Ajustes · Prueba piloto con socios seleccionados'],
        ['Semana 4', 'Lanzamiento oficial · Soporte intensivo · Entrega de documentación y manual'],
    ]
    tc = _header_table(crono, [3.5*cm, 11.5*cm])
    tc.setStyle(TableStyle([
        ('FONTNAME',  (0,1), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,1), (0,-1), G_MID),
    ]), overrideFlowable=False)
    s.append(tc)
    s.append(Spacer(1, 0.4*cm))

    garantia = [[Paragraph(
        '🛡️  <b>Garantía de cumplimiento</b>: si la implementación no se completa dentro de las '
        '4 semanas corridas desde la firma, Germina devuelve el 20 % del pago inicial sin condiciones.',
        _st('gar', fontSize=10, textColor=G_INK, leading=15))]]
    tg = Table(garantia, colWidths=[15*cm])
    tg.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#EAF7EA')),
        ('BOX',           (0,0), (-1,-1), 1, colors.HexColor('#4A9A38')),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('RIGHTPADDING',  (0,0), (-1,-1), 14),
        ('TOPPADDING',    (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    s.append(tg)
    s.append(Spacer(1, 0.8*cm))

    # ── PRÓXIMOS PASOS ────────────────────────────────────
    s.append(Paragraph('Próximos pasos', H1))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    pasos = [
        ['1', 'Revisá esta propuesta y el manual de usuario adjunto para conocer la plataforma en detalle.'],
        ['2', 'Accedé al entorno de demostración con las credenciales que te enviamos en este mismo mail.'],
        ['3', 'Si tenés dudas, respondé este mail o escribinos directamente. Te respondemos en menos de 24 horas.'],
        ['4', 'Si decidís avanzar, firmamos el acuerdo y arrancamos la implementación en la semana siguiente.'],
    ]
    tpp = Table(pasos, colWidths=[0.8*cm, 14.2*cm])
    tpp.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (0,-1), G_MID),
        ('FONTSIZE',  (0,0), (-1,-1), 10),
        ('FONTNAME',  (1,0), (1,-1), 'Helvetica'),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('VALIGN',    (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,-2), 0.2, G_BORDER),
    ]))
    s.append(tpp)
    s.append(Spacer(1, 1*cm))

    # ── FOOTER ────────────────────────────────────────────
    s.append(HRFlowable(width='100%', thickness=1, color=G_MID, spaceAfter=10))
    footer = [[
        Paragraph('<b>Spark Creativa</b><br/>besparkcreativa@gmail.com',
                  _st('fl', fontSize=8, textColor=G_GRIS, leading=12)),
        Paragraph(f'<b>Germina</b> · germina-clubs.netlify.app<br/>Propuesta válida 30 días · {fecha}',
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

    # ── PORTADA ──────────────────────────────────────────
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

    # ── 1. ACCESO ─────────────────────────────────────────
    s.append(Paragraph('1. Acceso al sistema', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Para acceder al panel de administración ingresá a la URL de tu club en Render y completá los datos de acceso:', BOD))
    acceso = [
        ['Campo', 'Valor'],
        ['URL del panel',  'tu-club.onrender.com/admin'],
        ['Usuario',        'admin'],
        ['Contraseña',     'La que te asignamos durante la implementación'],
    ]
    s.append(_header_table(acceso, [5*cm, 10*cm]))
    s.append(_tip('Recomendamos cambiar la contraseña la primera vez que ingreses. Guardala en un lugar seguro y compartila solo con personal autorizado.'))

    # ── 2. DASHBOARD ──────────────────────────────────────
    s.append(Paragraph('2. Panel de control (Dashboard)', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('El Dashboard es la pantalla principal. Muestra el estado de tu club en tiempo real apenas ingresás al sistema.', BOD))
    s.append(Paragraph('Bloque HOY', H1))
    s.append(Paragraph('• <b>Nuevas solicitudes</b>: socios que enviaron su formulario de ingreso hoy.', BUL))
    s.append(Paragraph('• <b>Dispensaciones</b>: cantidad de retiros realizados en el día.', BUL))
    s.append(Paragraph('• <b>Aforo actual</b>: socios presentes en este momento (clic para ir al control de aforo).', BUL))
    s.append(Paragraph('• <b>Cuotas vencidas</b>: socios con cuota expirada que requieren atención.', BUL))
    s.append(Paragraph('Alertas', H1))
    s.append(Paragraph('Muestra situaciones urgentes: socios pendientes de aprobación, documentación faltante, cuotas vencidas y cupos por agotarse. Las alertas desaparecen cuando resolvés la situación.', BOD))
    s.append(_tip('Si el número de alertas está en rojo, hay algo que requiere atención inmediata. Revisá la sección de alertas antes de arrancar el día.'))
    s.append(Paragraph('Gráficos de actividad', H1))
    s.append(Paragraph('Evolución de altas, dispensaciones y recaudación en los últimos 30 días. Útil para detectar tendencias y planificar el stock de variedades.', BOD))

    # ── 3. SOCIOS ─────────────────────────────────────────
    s.append(PageBreak())
    s.append(Paragraph('3. Gestión de socios', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Socios</b>. Lista completa con búsqueda por nombre o DNI y filtros por etapa.', BOD))
    s.append(Paragraph('Etapas del proceso', H1))
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
    s.append(Paragraph('Ficha del socio', H1))
    s.append(Paragraph('Al hacer clic en cualquier socio accedés a su ficha completa:', BOD))
    s.append(Paragraph('• Datos personales completos (DNI, contacto, diagnóstico, médico prescriptor)', BUL))
    s.append(Paragraph('• Estado de cuota con alerta automática de vencimiento', BUL))
    s.append(Paragraph('• Cupo mensual disponible vs. consumido (este mes + histórico)', BUL))
    s.append(Paragraph('• Historial completo de dispensaciones', BUL))
    s.append(Paragraph('• Documentación entregada y su estado de aprobación', BUL))
    s.append(Paragraph('• Notas internas del equipo', BUL))
    s.append(_tip('Podés cambiar la etapa del socio directamente desde su ficha con un clic. El cambio queda registrado con fecha y hora automáticamente.'))

    # ── 4. DISPENSARIO ────────────────────────────────────
    s.append(PageBreak())
    s.append(Paragraph('4. Dispensario', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Dispensario</b>. Aquí registrás cada retiro de un socio.', BOD))
    s.append(Paragraph('Paso a paso:', H1))
    s.append(Paragraph('1. Buscá al socio por nombre o DNI en el campo de búsqueda.', BUL))
    s.append(Paragraph('2. Seleccioná la variedad desde el catálogo visual (tarjetas con foto, genética, THC/CBD y efectos).', BUL))
    s.append(Paragraph('3. Ingresá la cantidad en gramos a dispensar.', BUL))
    s.append(Paragraph('4. Confirmá el retiro. El sistema verifica que no supere el cupo mensual del socio.', BUL))
    s.append(Paragraph('5. La dispensación queda registrada en el historial del socio y en el informe del día.', BUL))
    s.append(_tip('Si el socio ya consumió su cupo mensual, el sistema lo alerta antes de permitir confirmar. No se puede superar el cupo sin autorización manual del administrador.'))

    # ── 5. VARIEDADES ─────────────────────────────────────
    s.append(Paragraph('5. Catálogo de variedades', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Variedades</b>. Cargá y administrá todas las cepas disponibles.', BOD))
    s.append(Paragraph('Datos de cada variedad:', H1))
    s.append(Paragraph('• <b>Nombre</b>: nombre de la cepa (ej: OG Kush, Charlotte Web)', BUL))
    s.append(Paragraph('• <b>Genética</b>: Sativa / Índica / Híbrida / Alto CBD', BUL))
    s.append(Paragraph('• <b>THC %</b> y <b>CBD %</b>: concentraciones verificadas', BUL))
    s.append(Paragraph('• <b>Descripción</b>: texto explicativo que ven los socios en su portal', BUL))
    s.append(Paragraph('• <b>Efectos</b>: lista separada por comas (ej: Relajante, Sedante, Eufórico)', BUL))
    s.append(Paragraph('• <b>Indicaciones</b>: condiciones para las que se recomienda (ej: Insomnio, Dolor crónico)', BUL))
    s.append(Paragraph('• <b>Sabor</b>: perfil aromático (ej: Tierra, Pino, Cítrico)', BUL))
    s.append(Paragraph('• <b>Imagen</b>: URL de una foto (Google Drive, Instagram, etc.)', BUL))
    s.append(_tip('Podés activar o desactivar variedades sin borrarlas. Las inactivas no aparecen en el dispensario ni en el portal del socio hasta que las reactives.'))

    # ── 6. CUOTAS ─────────────────────────────────────────
    s.append(PageBreak())
    s.append(Paragraph('6. Cuotas y membresías', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Cuotas</b>. Registrá y controlá los pagos de membresía de cada socio.', BOD))
    s.append(Paragraph('Tipos de cuota:', H1))
    cuotas_t = [
        ['Tipo', 'Duración', 'Vencimiento automático'],
        ['Mensual',    '1 mes',   '30 días desde el pago'],
        ['Trimestral', '3 meses', '90 días desde el pago'],
        ['Semestral',  '6 meses', '180 días desde el pago'],
        ['Anual',      '1 año',   '365 días desde el pago'],
    ]
    s.append(_header_table(cuotas_t, [4*cm, 4*cm, 7*cm]))
    s.append(Paragraph('Cómo registrar un pago:', H1))
    s.append(Paragraph('Desde la ficha del socio → sección "Cuota / membresía" → botón "+ Registrar pago". Completá el tipo, monto y fecha. El vencimiento se calcula automáticamente.', BOD))
    s.append(_tip('Las cuotas vencidas aparecen en el Dashboard como alerta. El portal del socio también muestra si su cuota está al día, por vencer (menos de 7 días) o vencida.'))

    # ── 7. AFORO ──────────────────────────────────────────
    s.append(Paragraph('7. Control de aforo', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Ruta: menú lateral → <b>Aforo</b>. Control de quiénes están físicamente en el club en tiempo real.', BOD))
    s.append(Paragraph('• El contador muestra entradas menos salidas del día actual.', BUL))
    s.append(Paragraph('• Registrá entradas y salidas buscando al socio por nombre.', BUL))
    s.append(Paragraph('• La lista "Socios dentro ahora" muestra quién está presente, con botón de salida individual.', BUL))
    s.append(Paragraph('• El historial del día (columna derecha) registra todos los movimientos con hora exacta.', BUL))
    s.append(_tip('El número de aforo aparece en el Dashboard. Haciendo clic en él llegás directo a esta pantalla.'))

    # ── 8. PORTAL DEL SOCIO ───────────────────────────────
    s.append(PageBreak())
    s.append(Paragraph('8. Portal del socio', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('Cada socio tiene su propio portal personal al que accede desde el celular ingresando su DNI en la landing del club. No requiere contraseña.', BOD))
    s.append(Paragraph('El portal tiene cuatro secciones:', H1))
    s.append(Paragraph('• <b>Inicio</b>: carnet digital con QR, estado de cuota, barra de cupo mensual y últimas operaciones.', BUL))
    s.append(Paragraph('• <b>Flores</b>: catálogo de variedades con fichas detalladas y sistema de calificación por estrellas (solo variedades que el socio ya retiró).', BUL))
    s.append(Paragraph('• <b>Historial</b>: todos los retiros agrupados por mes (dispensario + pedidos).', BUL))
    s.append(Paragraph('• <b>Perfil</b>: datos personales, estado de cuota, documentación y QR de identificación.', BUL))
    s.append(Paragraph('¿Cómo acceden los socios?', H1))
    s.append(Paragraph('Landing del club → botón <b>"Soy socio"</b> → ingresan su DNI → acceden a su portal.', BOD))
    s.append(_tip('El QR del carnet digital puede escanearse en el club para identificar al socio al momento del retiro, sin que tenga que ingresar datos.'))

    # ── 9. REPORTES ───────────────────────────────────────
    s.append(Paragraph('9. Reportes y exportación', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))
    s.append(Paragraph('• <b>Informe del día</b> (menú lateral): resumen automático de dispensaciones, altas, cuotas cobradas y movimientos de aforo del día.', BUL))
    s.append(Paragraph('• <b>Exportar CSV</b> (menú lateral): descarga la lista completa de socios en formato planilla para usar en Excel o Google Sheets.', BUL))
    s.append(_tip('El informe del día es ideal para la reunión semanal del equipo. Te da una foto completa sin necesidad de buscar dato por dato en el sistema.'))

    # ── 10. FAQ ───────────────────────────────────────────
    s.append(PageBreak())
    s.append(Paragraph('10. Preguntas frecuentes', H0))
    s.append(HRFlowable(width='100%', thickness=0.4, color=G_BORDER, spaceAfter=10))

    faqs = [
        ('¿Qué pasa si un socio intenta retirar más de su cupo mensual?',
         'El sistema lo detecta y muestra una alerta antes de permitir confirmar. No se puede superar el cupo sin que el administrador lo apruebe manualmente.'),
        ('¿Puedo migrar socios que ya tengo de antes de usar Germina?',
         'Sí. Durante la implementación te ayudamos a migrar tu base de socios existente. También podés cargarlos manualmente desde el panel en cualquier momento.'),
        ('¿Los datos de los socios están seguros?',
         'La base de datos está alojada en el servidor de Render con backups automáticos. Solo vos (con credenciales de admin) podés acceder.'),
        ('¿Puedo usar el panel desde el celular?',
         'El panel de administración está optimizado para desktop. El portal del socio sí está diseñado específicamente para celular.'),
        ('¿Qué hago si una variedad se agota?',
         'Desde el catálogo de variedades podés desactivarla con un clic. No aparecerá en el dispensario ni en el portal hasta que la reactives.'),
        ('¿Puedo tener más de un administrador?',
         'Por el momento el sistema tiene un único usuario administrador. Si necesitás múltiples usuarios con diferentes permisos, consultanos — está en el roadmap de la plataforma.'),
        ('¿Qué hago si olvidé la contraseña?',
         'Contactá a Germina y te reseteamos el acceso en el mismo día. Por esto recomendamos tener la contraseña guardada de forma segura desde el primer día.'),
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
