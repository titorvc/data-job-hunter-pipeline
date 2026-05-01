from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine, text

def extraer_vacantes_api():
    print("Iniciando Radar Masivo V3 (30 Fuentes - Timeout Balanceado 60s)...")
    todos_los_trabajos = []

    # =================================================================
    # MATRIZ DE 30 FUENTES (APIs y RSS)
    # =================================================================
    fuentes = [
        {"url": "https://remotive.com/api/remote-jobs?category=data&limit=250", "tipo": "json"},
        {"url": "https://remotive.com/api/remote-jobs?category=software-dev&limit=250", "tipo": "json"},
        {"url": "https://remoteok.com/api", "tipo": "json"},
        {"url": "https://www.arbeitnow.com/api/job-board-api", "tipo": "json"},
        {"url": "https://jobicy.com/api/v2/remote-jobs?count=100&category=data", "tipo": "json"},
        {"url": "https://jobicy.com/api/v2/remote-jobs?count=100&category=dev", "tipo": "json"},
        {"url": "https://himalayas.app/api/jobs", "tipo": "json"},
        {"url": "https://workingnomads.com/jobs/api/v2/jobs/?category=development", "tipo": "json"},
        {"url": "https://weworkremotely.com/categories/remote-data-jobs.rss", "tipo": "rss"},
        {"url": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss", "tipo": "rss"},
        {"url": "https://www.python.org/jobs/feed/rss/", "tipo": "rss"},
        {"url": "https://jobspresso.co/feed/", "tipo": "rss"},
        {"url": "https://berlinstartupjobs.com/engineering/feed/", "tipo": "rss"},
        {"url": "https://www.upwork.com/ab/feed/jobs/rss?q=data+engineering", "tipo": "rss"},
        {"url": "https://www.upwork.com/ab/feed/jobs/rss?q=python+backend", "tipo": "rss"},
        {"url": "https://hnrss.org/whoishiring/jobs?q=Data", "tipo": "rss"},
        {"url": "https://hnrss.org/whoishiring/jobs?q=Python", "tipo": "rss"},
        {"url": "https://nodesk.co/remote-jobs/engineering/feed.xml", "tipo": "rss"},
        {"url": "https://djangojobs.net/jobs/feeds/latest/", "tipo": "rss"},
        {"url": "https://workingnomads.com/jobs/api/v2/jobs/?category=data", "tipo": "json"},
        {"url": "https://jobspresso.co/job-category/data/feed/", "tipo": "rss"},
        {"url": "https://remotive.com/api/remote-jobs?category=devops", "tipo": "json"},
        {"url": "https://www.upwork.com/ab/feed/jobs/rss?q=ETL", "tipo": "rss"},
        {"url": "https://www.upwork.com/ab/feed/jobs/rss?q=Airflow", "tipo": "rss"},
        {"url": "https://www.freelancer.com/rss.xml?q=python", "tipo": "rss"},
        {"url": "https://www.freelancer.com/rss.xml?q=data+engineering", "tipo": "rss"},
        {"url": "https://www.guru.com/rss/jobs/category/programming-development/", "tipo": "rss"},
        {"url": "https://remote.co/remote-jobs/it/feed/", "tipo": "rss"},
        {"url": "https://authenticjobs.com/feed/", "tipo": "rss"},
        {"url": "https://cryptojobslist.com/jobs/engineering.rss", "tipo": "rss"}
    ]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    TIMEOUT_SECONDS = 60 # Nuevo umbral de tolerancia

    for idx, f in enumerate(fuentes, 1):
        try:
            print(f"[{idx}/30] Escaneando: {f['url'][:50]}...")
            if f['tipo'] == "json":
                # Aplicamos el timeout de 60s
                res = requests.get(f['url'], headers=headers, timeout=TIMEOUT_SECONDS)
                datos = res.json()
                jobs = datos.get('jobs', datos.get('data', datos.get('results', []))) if isinstance(datos, dict) else datos
                for j in jobs:
                    if not isinstance(j, dict) or 'legal' in j: continue
                    todos_los_trabajos.append({
                        'titulo_puesto': str(j.get('title', j.get('position', j.get('role', '')))),
                        'empresa': str(j.get('company_name', j.get('company', 'No especificada'))),
                        'url': str(j.get('url', j.get('link', ''))),
                        'descripcion': str(j.get('description', j.get('text', ''))),
                        'ubicacion': str(j.get('candidate_required_location', j.get('location', 'Worldwide')))
                    })
            else:
                # Aplicamos el timeout de 60s también a las fuentes RSS
                res_rss = requests.get(f['url'], headers=headers, timeout=TIMEOUT_SECONDS)
                feed = feedparser.parse(res_rss.content)
                
                for e in feed.entries:
                    raw_title = str(e.get('title', ''))
                    empresa_rss = str(e.get('author', 'No especificada'))
                    titulo_puesto = raw_title
                    
                    if ' at ' in raw_title:
                        partes = raw_title.split(' at ')
                        titulo_puesto = partes[0].strip()
                        empresa_rss = partes[-1].strip()
                    elif ':' in raw_title and empresa_rss == 'No especificada':
                        partes = raw_title.split(':')
                        empresa_rss = partes[0].strip()
                        titulo_puesto = partes[1].strip()
                        
                    todos_los_trabajos.append({
                        'titulo_puesto': titulo_puesto,
                        'empresa': empresa_rss,
                        'url': str(e.get('link', '')),
                        'descripcion': str(e.get('summary', e.get('description', ''))),
                        'ubicacion': 'Remote / Worldwide'
                    })
        except Exception as e: 
            print(f"  -> Omisión temporal por timeout (>60s) o estructura en fuente {idx}")

    df = pd.DataFrame(todos_los_trabajos)
    if df.empty: 
        print("No se extrajeron datos de ninguna fuente.")
        return
        
    print(f"Total bruto extraído: {len(df)} vacantes. Aplicando Filtro de Titanio...")
    
    # =================================================================
    # EL FILTRO DE TITANIO (Precisión Absoluta)
    # =================================================================
    palabras_clave = ['data engineer', 'data analyst', 'analytics', 'etl', 'pipeline', 'business intelligence', 'bi developer', 'sql developer', 'airflow']
    df = df[df['titulo_puesto'].str.contains('|'.join(palabras_clave), case=False, na=False)]
    
    ruido_tecnico = ['ios', 'android', 'frontend', 'react', 'angular', 'vue', 'full stack', 'fullstack', 'web developer', 'django', 'ruby']
    df = df[~df['titulo_puesto'].str.contains('|'.join(ruido_tecnico), case=False, na=False)]

    ruido_seniority = ['senior', 'sr', 'lead', 'manager', 'principal', 'head', 'architect', 'director', 'vp', 'staff']
    df = df[~df['titulo_puesto'].str.contains('|'.join(ruido_seniority), case=False, na=False)]
    
    regiones_bloqueadas = ['only us', 'us only', 'usa only', 'europe only', 'uk only', 'canada only', 'germany', 'india', 'clearance', 'uk resident']
    df = df[~df['ubicacion'].str.contains('|'.join(regiones_bloqueadas), case=False, na=False)]
    
    # =================================================================

    df['descripcion'] = df['descripcion'].apply(lambda x: " ".join(BeautifulSoup(str(x), "html.parser").get_text(separator=' ').split()))
    df_nuevas = df[['titulo_puesto', 'empresa', 'url', 'descripcion']].drop_duplicates(subset=['url'])

    # --- CARGA INTELIGENTE LOCAL (POSTGRESQL) ---
    engine = create_engine('postgresql+psycopg2://roberto:superpassword123@postgres:5432/job_hunter')
    
    try:
        df_existentes = pd.read_sql("SELECT url FROM ofertas_empleo", con=engine)
        urls_conocidas = df_existentes['url'].tolist()
        df_final = df_nuevas[~df_nuevas['url'].isin(urls_conocidas)].copy()
    except:
        df_final = df_nuevas.copy()

    if df_final.empty:
        print("El radar barrió las 30 fuentes, pero ninguna nueva cumple con el estándar estricto de Data/Junior.")
    else:
        df_final.to_sql('ofertas_empleo', con=engine, if_exists='append', index=False)
        print(f"¡Éxito! {len(df_final)} vacantes NUEVAS de Datos añadidas a tu radar.")

        # --- RESPALDO HISTÓRICO (BIGQUERY) ---
        try:
            df_final['fecha_extraccion'] = pd.Timestamp.now().strftime('%Y-%m-%d')
            gcp_project_id = 'data-hunter-494609'
            bq_table = 'job_hunter_data_lake.ofertas_historicas'
            df_final.to_gbq(destination_table=bq_table, project_id=gcp_project_id, if_exists='append')
            print("Sincronización con BigQuery completada.")
        except Exception as e:
            print(f"Error cargando a BigQuery: {e}")

with DAG(dag_id='02_etl_job_hunter', start_date=datetime(2024, 1, 1), schedule='0 2 * * *', catchup=False) as dag:
    PythonOperator(task_id='extraer_vacantes_remotas', python_callable=extraer_vacantes_api)
