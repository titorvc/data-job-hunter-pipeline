import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
from sqlalchemy import create_engine
import os

def send_top_matches_email():
    print("Buscando Top Matches para enviar por correo...")
    engine = create_engine('postgresql+psycopg2://roberto:superpassword123@postgres:5432/job_hunter')
    
    # Buscar los matches con score >= 85 que no han sido notificados
    try:
        df_top = pd.read_sql("SELECT * FROM ofertas_empleo WHERE score >= 70 AND notificado = FALSE AND url IS NOT NULL AND url != '' AND url != 'http://example.com/job1' ORDER BY score DESC LIMIT 10", con=engine)
    except Exception as e:
        print(f"Error al leer base de datos: {e}")
        return

    if df_top.empty:
        print("No hay vacantes > 85 de score hoy para notificar.")
        return
        
    # Obtener credenciales desde variables de entorno o archivos (placeholder)
    # Por ahora se asume que se configurarán en el entorno de Airflow
    SMTP_USER = os.environ.get("SMTP_USER", "tu_correo@gmail.com")
    SMTP_PASS = os.environ.get("SMTP_PASS", "tu_app_password")
    
    if SMTP_PASS == "tu_app_password":
        print("ADVERTENCIA: Contraseña de SMTP no configurada. Saltando envío de correo.")
        print(f"Vacantes encontradas que se habrían enviado:\n{df_top[['titulo_puesto', 'empresa', 'score']].to_string()}")
        return

    # Preparar el correo HTML
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_USER
    msg['Subject'] = f"🚀 Job Hunter IA: {len(df_top)} Nuevos Top Matches Encontrados"

    html_content = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f4f9; color: #333; padding: 20px; }
            h2 { color: #2c3e50; }
            .job-card { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid #27ae60; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .score { font-weight: bold; color: #27ae60; font-size: 1.2em; }
            .company { font-weight: bold; color: #7f8c8d; }
            a { color: #2980b9; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2>🤖 Tu Cerebro IA ha encontrado oportunidades</h2>
        <p>Estas son las vacantes con mayor nivel de compatibilidad con tu perfil técnico:</p>
        
        <h3>📋 Resumen Rápido:</h3>
        <ul>
    """
    
    # Primera pasada para la lista rápida con links explícitos
    for _, row in df_top.iterrows():
        html_content += f"<li><strong>{row['titulo_puesto']}</strong> en {row['empresa']} - <a href='{row['url']}'>{row['url']}</a></li>"
        
    html_content += """
        </ul>
        <hr>
        <h3>🔍 Detalles de Evaluación:</h3>
    """

    # Segunda pasada para las tarjetas detalladas
    for _, row in df_top.iterrows():
        html_content += f"""
        <div class="job-card">
            <h3>{row['titulo_puesto']}</h3>
            <p class="company">🏢 {row['empresa']} | <span class="score">⭐ Score: {row['score']}%</span></p>
            <p><strong>Razón del Match:</strong> {row['razon']}</p>
            <p><a href="{row['url']}" target="_blank">➡️ Postularse Ahora ({row['url']})</a></p>
        </div>
        """

    html_content += """
    </body>
    </html>
    """

    msg.attach(MIMEText(html_content, 'html'))
    
    # Adjuntar PDFs de la carpeta generada
    OUTPUT_DIR = "/opt/airflow/dags/data_lake/generated_cvs"
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith(".pdf"):
                file_path = os.path.join(OUTPUT_DIR, f)
                try:
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename= {f}")
                    msg.attach(part)
                except Exception as e:
                    print(f"Error adjuntando {f}: {e}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print("Correo enviado exitosamente.")
        
        # Marcar las vacantes como notificadas
        ids_notificados = df_top['id'].tolist()
        if ids_notificados:
            from sqlalchemy import text
            try:
                id_list = ', '.join(map(str, ids_notificados))
                with engine.begin() as conn:
                    res = conn.execute(text(f"UPDATE ofertas_empleo SET notificado = TRUE WHERE id IN ({id_list})"))
                print(f"Se marcaron {res.rowcount} vacantes como notificadas exitosamente. IDs: {id_list}")
            except Exception as db_err:
                print(f"Error específico actualizando BD: {db_err}")
                
    except Exception as e:
        print(f"Error crítico al enviar correo: {e}")

if __name__ == "__main__":
    send_top_matches_email()
