import sqlite3, secrets, random
from datetime import datetime, timedelta

DB = 'cannawaka.db'
db = sqlite3.connect(DB)

socios = [
    ('María', 'González', '28341122', 'maria.g@gmail.com', '+54 11 4523 8891', '1985-03-14', 'femenino', 'Palermo', 'paciente', 'epilepsia refractaria', 'Lleva 6 años con crisis, probé todo', '3_5', 'Dr. Hernán Soria', 'neurólogo', 'si', 'uso_actual', 'aceite', 'instagram', '', 'activo'),
    ('Carlos', 'Rivas', '31209847', 'carlosrivas@hotmail.com', '+54 11 5698 3344', '1978-07-22', 'masculino', 'Villa Urquiza', 'paciente', 'dolor crónico lumbar', 'Hernia L4-L5 operada dos veces', 'mas_5', 'Dra. Mónica Perez', 'algóloga', 'en_proceso', 'uso_actual', 'flores', 'recomendacion', 'María González', 'en_revision'),
    ('Sofía', 'Méndez', '35128904', 'sofiamendez@gmail.com', '+54 11 3344 5566', '1992-11-08', 'femenino', 'San Telmo', 'paciente', 'ansiedad generalizada', 'Diagnóstico en pandemia, no respondo bien a benzodiacepinas', '1_3', '', '', 'no', 'nunca', 'aceite', 'instagram', '', 'solicitud'),
    ('Facundo', 'Torres', '29876543', 'faco.torres@gmail.com', '+54 11 6677 8899', '1981-05-30', 'masculino', 'Belgrano', 'productor', 'Parkinson temprano', 'Diagnosticado a los 40, busco alternativas', '3_5', 'Dr. Lucas Vidal', 'neurólogo', 'si', 'experiencia', 'aceite', 'medico', '', 'aprobado'),
    ('Laura', 'Fernández', '38745120', 'laurita.fd@gmail.com', '+54 11 2233 4455', '1995-02-14', 'femenino', 'Caballito', 'paciente', 'endometriosis', 'Cirugías sin resultado, dolor crónico pélvico', '1_3', 'Dr. Ramiro Suárez', 'ginecólogo', 'si', 'algo', 'aceite', 'recomendacion', 'Carlos Rivas', 'documentacion'),
    ('Martín', 'López', '32567891', 'mlopez@outlook.com', '+54 11 7788 9900', '1988-09-03', 'masculino', 'Núñez', 'cuidador', 'esclerosis múltiple', 'Es para mi mamá, yo soy su cuidador', 'mas_5', 'Dra. Paula Ibáñez', 'neurologa', 'en_proceso', 'nunca', 'aceite', 'google', '', 'en_revision'),
    ('Valentina', 'Castro', '40123456', 'vale.castro@gmail.com', '+54 11 9988 7766', '1999-06-21', 'femenino', 'Flores', 'paciente', 'TDAH y depresión', 'Llevo 3 años con psicofármacos sin mejoría', '1_3', 'Lic. Andrea Moreno', 'psicóloga', 'no', 'algo', 'aceite', 'instagram', '', 'solicitud'),
    ('Roberto', 'Díaz', '25987654', 'rdiaz@gmail.com', '+54 11 5544 3322', '1970-12-18', 'masculino', 'Almagro', 'paciente', 'glaucoma', 'Presión ocular muy alta, medicación no alcanza', 'mas_5', 'Dr. Santiago Pérez', 'oftalmólogo', 'si', 'nunca', 'gotas', 'fecca', '', 'aprobado'),
    ('Jimena', 'Rodríguez', '37654321', 'jime.rod@gmail.com', '+54 11 4433 2211', '1993-04-09', 'femenino', 'Recoleta', 'investigador', 'investigación oncológica', 'Médica, quiero incorporar cannabis en mi práctica', '', 'Dra. Jimena Rodríguez', 'oncóloga', 'si', 'experiencia', 'aceite', 'evento', '', 'activo'),
    ('Pablo', 'Herrera', '30456789', 'pablo.h@icloud.com', '+54 11 6655 4433', '1983-08-25', 'masculino', 'Floresta', 'paciente', 'fibromialgia', 'Diagnóstico hace 2 años, dolor generalizado', '1_3', '', '', 'no', 'nunca', 'aceite', 'instagram', '', 'solicitud'),
    ('Daniela', 'Morales', '39876543', 'dani.morales@gmail.com', '+54 11 3322 1100', '1996-01-17', 'femenino', 'Villa del Parque', 'paciente', 'epilepsia refractaria', 'Desde los 8 años, medicación no controla', 'mas_5', 'Dr. Hernán Soria', 'neurólogo', 'si', 'uso_actual', 'aceite', 'recomendacion', 'María González', 'activo'),
    ('Sebastián', 'Ruiz', '33214567', 'seba.ruiz@gmail.com', '+54 11 2211 0099', '1987-03-31', 'masculino', 'Palermo', 'productor', 'autismo TEA', 'Para mi hijo de 12 años, quiero cultivar', '3_5', 'Lic. Carla Gómez', 'psicopedagoga', 'en_proceso', 'algo', 'aceite', 'instagram', '', 'documentacion'),
]

base_date = datetime.now() - timedelta(days=90)

for i, s in enumerate(socios):
    nombre, apellido, dni, email, telefono, fecha_nac, genero, barrio, tipo, diagnostico, notas_sol, tiempo, medico, especialidad, receta, experiencia, metodo, canal, referido, etapa = s
    created = base_date + timedelta(days=random.randint(0, 85))
    token = secrets.token_urlsafe(20)
    db.execute('''
        INSERT OR IGNORE INTO socios
        (token, nombre, apellido, dni, email, telefono, fecha_nac, genero, barrio,
         tipo_socio, diagnostico, notas_solicitud, tiempo_condicion,
         medico_prescriptor, especialidad_medico, tiene_receta,
         experiencia_cannabis, metodo_consumo, como_nos_conocio, referido_por,
         etapa, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (token, nombre, apellido, dni, email, telefono, fecha_nac, genero, barrio,
          tipo, diagnostico, notas_sol, tiempo, medico, especialidad, receta,
          experiencia, metodo, canal, referido, etapa,
          created.strftime('%Y-%m-%d %H:%M:%S'), created.strftime('%Y-%m-%d %H:%M:%S')))

db.commit()
print(f"✓ {len(socios)} socios demo cargados")
db.close()
