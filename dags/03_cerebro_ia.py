from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import requests
import json

def evaluar_con_ia():
    print("Iniciando evaluación cognitiva con Llama 3.2...")
    engine = create_engine('postgresql+psycopg2://roberto:superpassword123@postgres:5432/job_hunter')
    
    try:
        # Extraer vacantes que aún no han sido evaluadas
        df_nuevas = pd.read_sql("SELECT * FROM ofertas_empleo WHERE score IS NULL OR score = 0", con=engine)
    except Exception as e:
        print(f"Error o no hay vacantes nuevas: {e}")
        return

    if df_nuevas.empty:
        print("No hay vacantes nuevas para evaluar hoy.")
        return

    try:
        with open("/opt/airflow/dags/data_lake/mi_cv.txt", "r") as file:
            cv_roberto = file.read()
    except FileNotFoundError:
        print("CRÍTICO: No se encontró el archivo mi_cv.txt")
        return

    resultados = []
    url_ollama = "http://ollama:11434/api/generate"

    for index, row in df_nuevas.iterrows():
        puesto = row['titulo_puesto']
        empresa = row['empresa']
        descripcion = str(row['descripcion'])[:2000] # Limitamos para no saturar contexto

        # --- EL NUEVO PROMPT COGNITIVO ---
        prompt = f"""
        Act as an Expert IT Recruiter for Data Engineering roles. 
        Evaluate if the candidate (Roberto) is a good fit for this role: {puesto} at {empresa}.
        
        Candidate Context: Roberto is a Data Engineer capable of building end-to-end ecosystems. 
        Core Stack to look for: Apache Airflow, Docker, Python, PostgreSQL, Google BigQuery (OLAP), pgvector, Metabase, and Streamlit.
        
        Compare the Candidate CV with the Job Description.
        Strictly return ONLY a valid JSON with two keys:
        - "score": Integer from 0 to 100 representing the match percentage.
        - "reason": A brief 2-sentence explanation of why in Spanish.
        
        CANDIDATE CV:
        {cv_roberto}
        
        JOB DESCRIPTION:
        {descripcion}
        """

        try:
            res = requests.post(url_ollama, json={
                "model": "llama3.2",
                "prompt": prompt,
                "format": "json",
                "stream": False
            }, timeout=120)
            
            respuesta_json = json.loads(res.json()['response'])
            score = int(respuesta_json.get('score', 0))
            razon = str(respuesta_json.get('reason', 'Sin razonamiento devuelto.'))
            
        except Exception as e:
            print(f"Error evaluando {empresa}: {e}")
            score = 0
            razon = "Error de conexión con la IA local."

        resultados.append({'url': row['url'], 'score': score, 'razon': razon})
        print(f"Evaluado: {empresa} - Score: {score}")

    # Actualizar la base de datos con los resultados
    with engine.begin() as conn:
        for r in resultados:
            query = text("UPDATE ofertas_empleo SET score = :score, razon = :razon WHERE url = :url")
            conn.execute(query, {"score": r['score'], "razon": r['razon'], "url": r['url']})

    # Generar el CSV maestro para el Dashboard de Streamlit
    df_completo = pd.read_sql("SELECT * FROM ofertas_empleo WHERE score > 0 ORDER BY score DESC", con=engine)
    df_completo.to_csv('/opt/airflow/dags/data_lake/reporte_diario.csv', index=False)
    print(f"Evaluación terminada. {len(resultados)} vacantes procesadas. Reporte generado.")

with DAG(dag_id='03_cerebro_ia', start_date=datetime(2024, 1, 1), schedule='0 3 * * *', catchup=False) as dag:
    PythonOperator(task_id='evaluar_vacantes', python_callable=evaluar_con_ia)
