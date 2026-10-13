#!/usr/bin/env python3
"""
Job Hunter AI - Serverless Cloud Run Pipeline
"""
import os
import sys
import json
import time
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

import requests
import feedparser
from bs4 import BeautifulSoup
import pandas as pd
from fpdf import FPDF
from groq import Groq
from google.cloud import bigquery

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "data-hunter-494609")
BQ_DATASET = os.environ.get("BQ_DATASET", "job_hunter_data_lake")
BQ_TABLE = os.environ.get("BQ_TABLE", "ofertas_historicas")
BQ_FULL_TABLE = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SMTP_USER = os.environ.get("SMTP_USER", "titorvc08@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS")
CV_BASE_PATH = os.environ.get("CV_BASE_PATH", "mi_cv.txt")
OUTPUT_DIR = "/tmp/generated_cvs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extraer_y_filtrar_vacantes():
    print("=" * 60)
    print("🚀 [PASO 1] Iniciando Extraccion Masiva (30 Fuentes APIs / RSS)...")
    print("=" * 60)
    
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
        {"url": "https://cryptojobslist.com/jobs/engineering.rss", "tipo": "rss"},
        {"url": "https://www.upwork.com/ab/feed/jobs/rss?q=machine+learning", "tipo": "rss"},
        {"url": "https://www.upwork.com/ab/feed/jobs/rss?q=data+scientist", "tipo": "rss"},
        {"url": "https://hnrss.org/whoishiring/jobs?q=Machine+Learning", "tipo": "rss"},
        {"url": "https://hnrss.org/whoishiring/jobs?q=AI", "tipo": "rss"},
        {"url": "https://weworkremotely.com/categories/remote-programming-jobs.rss", "tipo": "rss"},
        {"url": "https://nodesk.co/remote-jobs/python/feed.xml", "tipo": "rss"},
        {"url": "https://remoteok.com/api?tag=python", "tipo": "json"},
        {"url": "https://jobicy.com/api/v2/remote-jobs?count=50&category=engineering", "tipo": "json"},
        {"url": "https://workingnomads.com/jobs/api/v2/jobs/?category=machine-learning", "tipo": "json"}
    ]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    TIMEOUT_SECONDS = 30
    todos_los_trabajos = []

    for idx, f in enumerate(fuentes, 1):
        try:
            if f['tipo'] == "json":
                res = requests.get(f['url'], headers=headers, timeout=TIMEOUT_SECONDS)
                if res.status_code == 200:
                    datos = res.json()
                    jobs = datos.get('jobs', datos.get('data', datos.get('results', []))) if isinstance(datos, dict) else datos
                    if isinstance(jobs, list):
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
                res_rss = requests.get(f['url'], headers=headers, timeout=TIMEOUT_SECONDS)
                if res_rss.status_code == 200:
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
        except Exception:
            continue

    if not todos_los_trabajos:
        print("⚠️ No se pudieron extraer vacantes en este ciclo.")
        return pd.DataFrame()

    df = pd.DataFrame(todos_los_trabajos)
    print(f"📊 Total bruto extraido: {len(df)} vacantes. Aplicando Filtro de Titanio...")

    palabras_clave = ['data engineer', 'data analyst', 'analytics', 'etl', 'pipeline', 'business intelligence', 'bi developer', 'sql developer', 'airflow', 'machine learning', 'ai engineer', 'data architect', 'analytics engineer']
    df = df[df['titulo_puesto'].str.contains('|'.join(palabras_clave), case=False, na=False)]

    ruido_tecnico = ['ios', 'android', 'frontend', 'react', 'angular', 'vue', 'full stack', 'fullstack', 'web developer', 'django', 'ruby']
    df = df[~df['titulo_puesto'].str.contains('|'.join(ruido_tecnico), case=False, na=False)]

    ruido_seniority = ['manager', 'director', 'vp']
    df = df[~df['titulo_puesto'].str.contains('|'.join(ruido_seniority), case=False, na=False)]

    regiones_bloqueadas = ['only us', 'us only', 'usa only', 'europe only', 'uk only', 'canada only', 'germany', 'india', 'clearance', 'uk resident']
    df = df[~df['ubicacion'].str.contains('|'.join(regiones_bloqueadas), case=False, na=False)]

    df['descripcion'] = df['descripcion'].apply(lambda x: " ".join(BeautifulSoup(str(x), "html.parser").get_text(separator=" ").split()))
    df = df[df['url'].str.startswith("http", na=False)]
    df = df.drop_duplicates(subset=['url'])

    print(f"🎯 Vacantes filtradas y listas: {len(df)}")
    return df

def filtrar_solo_nuevas_en_bigquery(df_vacantes):
    if df_vacantes.empty:
        return df_vacantes

    print("=" * 60)
    print("🔍 [PASO 2] Consultando BigQuery para deduplicacion historica...")
    print("=" * 60)

    try:
        client = bigquery.Client(project=GCP_PROJECT_ID)
        query = f"SELECT DISTINCT url FROM `{BQ_FULL_TABLE}` WHERE url IS NOT NULL"
        query_job = client.query(query)
        urls_existentes = set(row.url for row in query_job)
        print(f"📚 URLs historicas registradas en BigQuery: {len(urls_existentes)}")

        df_nuevas = df_vacantes[~df_vacantes['url'].isin(urls_existentes)].copy()
        print(f"✨ Vacantes estrictamente NUEVAS: {len(df_nuevas)}")
        return df_nuevas
    except Exception as e:
        print(f"⚠️ Nota de BigQuery: {e}")
        return df_vacantes

def evaluar_con_groq(df_nuevas):
    if df_nuevas.empty:
        return df_nuevas

    print("=" * 60)
    print(f"🧠 [PASO 3] Evaluando {len(df_nuevas)} vacantes con Groq LLM...")
    print("=" * 60)

    if not GROQ_API_KEY:
        print("❌ Error: GROQ_API_KEY no configurada.")
        return df_nuevas

    if not os.path.exists(CV_BASE_PATH):
        print(f"❌ Error: Archivo de CV base no encontrado en {CV_BASE_PATH}")
        return df_nuevas

    with open(CV_BASE_PATH, "r") as f:
        cv_roberto = f.read()

    client = Groq(api_key=GROQ_API_KEY)
    scores = []
    razones = []

    for idx, row in df_nuevas.iterrows():
        puesto = row['titulo_puesto']
        empresa = row['empresa']
        descripcion = str(row['descripcion'])[:2000]

        prompt = f"""Act as an Expert IT Recruiter for Data Engineering roles. 
Evaluate if the candidate (Roberto) is a good fit for this role: {puesto} at {empresa}.

Candidate Context: Roberto is a Data Engineer capable of building end-to-end ecosystems. 
Core Stack: Apache Airflow, Docker, Python, PostgreSQL, Google BigQuery, pgvector, Metabase, and Streamlit.

Compare the Candidate CV with the Job Description.
Strictly return ONLY a valid JSON with two keys:
- "score": Integer from 0 to 100 representing match percentage.
- "reason": Brief 2-sentence explanation of why in Spanish.

CANDIDATE CV:
{cv_roberto}

JOB DESCRIPTION:
{descripcion}
"""

        score = -1
        razon = "No evaluado"
        for attempt in range(3):
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You must strictly output valid JSON with keys 'score' and 'reason'."},
                        {"role": "user", "content": prompt}
                    ],
                    model="qwen/qwen3.6-27b",
                    response_format={"type": "json_object"}
                )
                res_json = json.loads(chat_completion.choices[0].message.content)
                score = int(res_json.get('score', 0))
                razon = str(res_json.get('reason', ''))
                break
            except Exception:
                time.sleep(2 * (attempt + 1))

        scores.append(score)
        razones.append(razon)
        print(f"  -> [{empresa}] {puesto} => Score: {score}")
        time.sleep(1)

    df_nuevas['score'] = scores
    df_nuevas['razon'] = razones
    df_nuevas['fecha_extraccion'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    return df_nuevas

class PDF(FPDF):
    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, title, 0, 1, 'L')
        x = self.get_x()
        y = self.get_y()
        self.line(x, y - 1, 210 - x, y - 1)
        self.ln(3)

def generate_pdf_for_candidate(cv_data, filepath):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=10)
    
    def safe(text):
        if not text: return ""
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font('Helvetica', 'B', 26)
    pdf.cell(0, 12, safe(cv_data.get('name', 'ROBERTO VARGAS')), 0, 1, 'C')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, safe(cv_data.get('contact', '(52) 999 640 5649 | Merida, Mexico | roberto.vargas99@outlook.com | github.com/titorvc')), 0, 1, 'C')
    pdf.ln(4)
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.line(x, y, 210 - x, y)
    pdf.ln(5)

    pdf.chapter_title('PROFESSIONAL SUMMARY')
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(0, 5, safe(cv_data.get('summary', '')))
    pdf.ln(5)

    pdf.chapter_title('TECHNICAL SKILLS')
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(0, 5, safe(cv_data.get('skills', '')))
    pdf.ln(5)

    pdf.chapter_title('DATA ENGINEERING PROJECTS')
    for proj in cv_data.get('projects', []):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(140, 5, safe(proj.get('title', '')), 0, 0, 'L')
        pdf.set_font('Helvetica', 'I', 10)
        pdf.cell(0, 5, safe(proj.get('date', '')), 0, 1, 'R')
        pdf.set_font('Helvetica', '', 10)
        for bullet in proj.get('bullets', []):
            pdf.set_x(15)
            pdf.cell(5, 5, "-", 0, 0, 'L')
            pdf.multi_cell(0, 5, safe(bullet))
        pdf.ln(2)

    pdf.chapter_title('EDUCATION')
    pdf.set_font('Helvetica', 'B', 10)
    pdf.multi_cell(0, 5, safe(cv_data.get('education', 'B.S. in Data Engineering - Universidad Politecnica de Yucatan | 2023-Present')))

    pdf.output(filepath)
    return filepath

def generar_cvs_destacados(df_evaluadas):
    df_top = df_evaluadas[df_evaluadas['score'] >= 80]
    if df_top.empty:
        return []

    print("=" * 60)
    print(f"📄 [PASO 4] Generando CVs personalizados para {len(df_top)} Top Matches (Score >= 80)...")
    print("=" * 60)

    client = Groq(api_key=GROQ_API_KEY)
    with open(CV_BASE_PATH, "r") as f:
        base_cv = f.read()

    generated_files = []
    for _, row in df_top.head(5).iterrows():
        puesto = row['titulo_puesto']
        empresa = row['empresa']
        descripcion = str(row['descripcion'])[:2000]

        prompt = f"""Act as an expert Resume Writer. Your task is to rewrite Roberto Vargas's CV to make it perfectly tailored for the position of '{puesto}' at '{empresa}'.
JOB DESCRIPTION: {descripcion}
BASE CV: {base_cv}
Output strictly ONLY valid JSON with keys: 'name', 'contact', 'summary', 'skills', 'projects' (array of objects with 'title', 'date', 'bullets'), 'education'.
"""
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="qwen/qwen3.6-27b",
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            cv_data = json.loads(chat_completion.choices[0].message.content)
            safe_empresa = "".join(x for x in empresa if x.isalnum()) or "Job"
            filename = os.path.join(OUTPUT_DIR, f"CV_Roberto_Vargas_{safe_empresa}.pdf")
            generate_pdf_for_candidate(cv_data, filename)
            generated_files.append(filename)
            print(f"  ✅ Generado PDF: {filename}")
        except Exception as e:
            print(f"  ⚠️ Error generando CV para {empresa}: {e}")

    return generated_files

def enviar_notificacion_email(df_evaluadas, archivos_pdf):
    df_notificar = df_evaluadas[df_evaluadas['score'] >= 70].sort_values(by='score', ascending=False)
    if df_notificar.empty:
        print("ℹ️ No hay vacantes con Score >= 70 para notificar en este ciclo.")
        return

    print("=" * 60)
    print(f"📧 [PASO 5] Enviando correo con {len(df_notificar)} Top Matches a {SMTP_USER}...")
    print("=" * 60)

    if not SMTP_PASS:
        print("⚠️ SMTP_PASS no configurada. Omitiendo envio de correo.")
        return

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_USER
    msg['Subject'] = f"🚀 Data Job Hunter: {len(df_notificar)} Oportunidades Encontradas"

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; padding: 20px; }}
            h2 {{ color: #1a5276; }}
            .job-card {{ background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #27ae60; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .score {{ font-weight: bold; color: #27ae60; font-size: 1.2em; }}
            .company {{ font-weight: bold; color: #7f8c8d; }}
            a {{ color: #2980b9; text-decoration: none; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>🤖 Radar de Vacantes Serverless - Nuevas Oportunidades</h2>
        <p>Se han analizado las 30 fuentes remotas y se encontraron las siguientes vacantes con alta afinidad tecnica:</p>
        <hr>
    """

    for _, row in df_notificar.iterrows():
        html_content += f"""
        <div class="job-card">
            <h3>{row['titulo_puesto']}</h3>
            <p class="company">🏢 {row['empresa']} | <span class="score">⭐ Match Score: {row['score']}%</span></p>
            <p><strong>Razon de compatibilidad:</strong> {row['razon']}</p>
            <p><a href="{row['url']}" target="_blank">➡️ Ver y Postularse ({row['url']})</a></p>
        </div>
        """

    html_content += """
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html'))

    for f in archivos_pdf:
        if os.path.exists(f):
            try:
                with open(f, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(f)}")
                msg.attach(part)
            except Exception as e:
                print(f"Error adjuntando {f}: {e}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print("✅ Correo electronico enviado exitosamente.")
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")

def guardar_en_bigquery(df_evaluadas):
    if df_evaluadas.empty:
        return

    print("=" * 60)
    print(f"💾 [PASO 6] Guardando {len(df_evaluadas)} vacantes evaluadas en BigQuery...")
    print("=" * 60)

    try:
        columnas = ['titulo_puesto', 'empresa', 'url', 'descripcion', 'score', 'razon', 'fecha_extraccion']
        df_upload = df_evaluadas[[c for c in columnas if c in df_evaluadas.columns]].copy()
        
        client = bigquery.Client(project=GCP_PROJECT_ID)
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            autodetect=True
        )
        job = client.load_table_from_dataframe(df_upload, BQ_FULL_TABLE, job_config=job_config)
        job.result()
        print(f"✅ Sincronizacion exitosa en BigQuery ({BQ_FULL_TABLE}).")
    except Exception as e:
        print(f"⚠️ Error al guardar en BigQuery: {e}")

def main():
    print("🏁 Iniciando ejecucion de Data Job Hunter en Cloud Run...")
    df_raw = extraer_y_filtrar_vacantes()
    if df_raw.empty:
        print("Proceso finalizado (sin vacantes nuevas).")
        return

    df_nuevas = filtrar_solo_nuevas_en_bigquery(df_raw)
    if df_nuevas.empty:
        print("Proceso finalizado (todas las vacantes ya existian en BigQuery).")
        return

    df_evaluadas = evaluar_con_groq(df_nuevas)
    archivos_pdf = generar_cvs_destacados(df_evaluadas)
    enviar_notificacion_email(df_evaluadas, archivos_pdf)
    guardar_en_bigquery(df_evaluadas)
    print("🎉 Pipeline completado con exito.")

if __name__ == "__main__":
    main()
