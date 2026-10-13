# 1. Usamos la imagen oficial de Airflow
FROM apache/airflow:2.9.0

# 2. Nos ponemos el sombrero de Administrador (Root) del Sistema Operativo
USER root

# 3. Instalamos los compiladores de C++ y las librerías gráficas de Linux para los PDFs
RUN apt-get update && \
    apt-get install -y gcc g++ libcairo2-dev pkg-config python3-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 4. Regresamos al usuario seguro de Airflow
USER airflow

# 5. Ahora sí, instalamos las librerías de Python (PyCairo ya podrá compilarse)
RUN pip install --no-cache-dir pandas requests sqlalchemy psycopg2-binary markdown xhtml2pdf feedparser beautifulsoup4 pandas-gbq db-dtypes fpdf2 groq
