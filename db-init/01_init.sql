-- 1. Habilitar la extensión mágica para el RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- TABLA 1: TU CEREBRO (Donde guardaremos tus Chunks)
CREATE TABLE cv_chunks (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(50), -- Ej: 'Tecnologías', 'Soft Skills', 'Experiencia'
    contenido TEXT NOT NULL,
    embedding VECTOR(768) -- Aquí vivirán las coordenadas matemáticas de Gemini
);

-- TABLA 2: EL BOTÍN (Donde Airflow/Pandas guardarán las vacantes que raspen)
CREATE TABLE ofertas_empleo (
    id SERIAL PRIMARY KEY,
    plataforma VARCHAR(50), -- Ej: 'LinkedIn', 'Indeed'
    titulo_puesto VARCHAR(200),
    empresa VARCHAR(200),
    descripcion TEXT,
    url TEXT UNIQUE, -- Unique evita que guardemos la misma vacante dos veces
    fecha_extraccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    procesado BOOLEAN DEFAULT FALSE -- n8n cambiará esto a TRUE cuando la lea
);

-- TABLA 3: EL REGISTRO DE ACCIONES (Lo que hizo n8n por ti)
CREATE TABLE postulaciones (
    id SERIAL PRIMARY KEY,
    id_oferta INTEGER REFERENCES ofertas_empleo(id),
    match_score DECIMAL(5,2), -- Ej: 85.50 (Porcentaje de afinidad de tu RAG)
    estado VARCHAR(50), -- Ej: 'CV Generado', 'Aplicado'
    fecha_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
