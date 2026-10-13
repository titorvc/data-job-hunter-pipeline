from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import requests
import json
import os
from groq import Groq
import sys
sys.path.append("/opt/airflow/dags")
import email_notifier
import cv_generator

def evaluar_con_ia():
    print("Iniciando evaluación cognitiva con Llama 3.2...")
    engine = create_engine('postgresql+psycopg2://roberto:superpassword123@postgres:5432/job_hunter')
    
    try:
        # Extraer vacantes que aún no han sido evaluadas
        df_nuevas = pd.read_sql("SELECT * FROM ofertas_empleo WHERE score IS NULL", con=engine)
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

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("CRÍTICO: GROQ_API_KEY no configurada en el entorno.")
        return
        
    client = Groq(api_key=api_key)

    resultados = []

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

        import time
        max_retries = 5
        base_delay = 5
        score = -1
        razon = "Error de conexión con la IA de Groq tras múltiples intentos."

        for attempt in range(max_retries):
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You must strictly output valid JSON with keys 'score' and 'reason'."},
                        {"role": "user", "content": prompt}
                    ],
                    model="qwen/qwen3.6-27b",
                    response_format={"type": "json_object"}
                )
                
                respuesta_json = json.loads(chat_completion.choices[0].message.content)
                score = int(respuesta_json.get('score', 0))
                razon = str(respuesta_json.get('reason', 'Sin razonamiento devuelto.'))
                break # Éxito, rompemos el bucle de reintentos
                
            except Exception as e:
                error_msg = str(e).lower()
                # Si es un error de rate limit, too many requests, o timeout, aplicamos backoff
                if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg or "timeout" in error_msg:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"Límite de Groq alcanzado o timeout en {empresa}. Reintentando en {wait_time}s... (Intento {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"Error irrecoverable evaluando {empresa}: {e}")
                    score = -1
                    razon = f"Error crítico: {e}"
                    break
        
        # Pausa constante de 3 segundos entre cada vacante para un ritmo moderado y seguro
        time.sleep(3)

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

with DAG(dag_id='03_cerebro_ia', start_date=datetime(2024, 1, 1), schedule='0 14,23 * * *', catchup=False) as dag:
    t1 = PythonOperator(task_id='evaluar_vacantes', python_callable=evaluar_con_ia)
    t2 = PythonOperator(task_id='generar_cvs', python_callable=cv_generator.generate_all_cvs)
    t3 = PythonOperator(task_id='enviar_notificacion', python_callable=email_notifier.send_top_matches_email)
    
    t1 >> t2 >> t3
