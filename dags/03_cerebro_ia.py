import os
import pandas as pd
from sqlalchemy import create_engine
import requests
import json
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

DATA_LAKE_PATH = '/opt/airflow/dags/data_lake'
REPORTE_PATH = f"{DATA_LAKE_PATH}/reporte_diario.csv"

def evaluar_vacantes():
    print("Iniciando Evaluación Cognitiva (Memoria Acumulativa)...")
    url_ollama = "http://ollama:11434/api/generate"

    with open(f"{DATA_LAKE_PATH}/mi_cv.txt", 'r') as file:
        mi_cv = file.read()

    engine = create_engine('postgresql+psycopg2://roberto:superpassword123@postgres:5432/job_hunter')
    df_db = pd.read_sql("SELECT * FROM ofertas_empleo", con=engine)

    evaluadas_urls = []
    if os.path.exists(REPORTE_PATH):
        try:
            df_reporte_previo = pd.read_csv(REPORTE_PATH)
            evaluadas_urls = df_reporte_previo['url'].tolist()
        except Exception as e:
            print(f"Error leyendo reporte previo: {e}")

    df_nuevas = df_db[~df_db['url'].isin(evaluadas_urls)]

    if df_nuevas.empty:
        print("No hay vacantes nuevas para evaluar. El Cerebro IA está al día.")
        return

    df_lote = df_nuevas.head(40)
    print(f"Se encontraron vacantes nuevas. Evaluando lote de {len(df_lote)} oportunidades...")

    resultados = []
    for _, row in df_lote.iterrows():
        print(f"Evaluando: {row['titulo_puesto']} en {row['empresa']}...")
        prompt = f"""
        Act as a Senior Technical Recruiter. Evaluate this Entry-Level candidate for the following remote job.
        Candidate: Roberto Vargas (Mérida, Mexico). NO formal corporate experience, but highly advanced technical portfolio: Docker, Apache Airflow, Kafka, PostgreSQL with pgvector, n8n.
        Job: {row['titulo_puesto']} at {row['empresa']}
        Description: {row['descripcion'][:1500]}
        
        Evaluate honestly if his strong foundation in Airflow, Python, SQL, and Docker makes him a solid junior match.
        Return ONLY JSON: {{"score": 0-100, "razon": "Breve explicación en español"}}
        """
        try:
            res = requests.post(url_ollama, json={"model": "llama3.2", "prompt": prompt, "format": "json", "stream": False}, timeout=300)
            datos = json.loads(res.json()['response'])
            
            resultados.append({
                'empresa': row['empresa'], 'puesto': row['titulo_puesto'], 'url': row['url'],
                'score': datos.get('score', 0), 'razon': datos.get('razon', ''),
                'descripcion_full': row['descripcion']
            })
        except Exception as e:
            print(f"Error en {row['empresa']}: {e}")

    if resultados:
        df_nuevos_resultados = pd.DataFrame(resultados)
        if os.path.exists(REPORTE_PATH):
            df_final = pd.concat([pd.read_csv(REPORTE_PATH), df_nuevos_resultados], ignore_index=True)
        else:
            df_final = df_nuevos_resultados

        df_final = df_final.sort_values(by='score', ascending=False).drop_duplicates(subset=['url'])
        df_final.to_csv(REPORTE_PATH, index=False)
        print(f"Evaluación terminada. {len(resultados)} nuevas vacantes añadidas al Dashboard.")

with DAG(dag_id='03_cerebro_ia', start_date=datetime(2024, 1, 1), schedule=None, catchup=False) as dag:
    PythonOperator(task_id='evaluar_vacantes', python_callable=evaluar_vacantes)
