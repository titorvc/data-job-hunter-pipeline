import streamlit as st
import pandas as pd
import os
import requests
import json
import streamlit.components.v1 as components
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Data Job Hunter", page_icon="⚡", layout="wide")

# Imagen abstracta oscura (Fluidos geométricos oscuros / 3D Abstract)
BACKGROUND_URL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop"

# --- INYECCIÓN DE CSS (ABSTRACT GLASSMORPHISM FORZADO) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

    /* 1. Hacer transparentes las capas base de Streamlit que bloquean la imagen */
    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: transparent !important;
        font-family: 'Inter', sans-serif;
    }}

    /* 2. Inyectar el fondo directamente en el contenedor de vista */
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background-image: url("{BACKGROUND_URL}");
        background-size: cover;
        background-position: center;
        filter: blur(8px) brightness(0.45);
        z-index: -1;
    }}

    header[data-testid="stHeader"] {{ background-color: transparent !important; }}

    /* 3. Barra Lateral */
    [data-testid="stSidebar"] {{
        background: rgba(10, 15, 25, 0.35) !important;
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }}

    h1, h2, h3, h4, h5, p, span, label, div {{ color: #F8FAFC !important; }}

    /* 4. Tarjetas de Métricas */
    div[data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        padding: 20px 25px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4) !important;
    }}

    div[data-testid="stMetricValue"] div {{
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        text-shadow: 0px 2px 10px rgba(0,0,0,0.5);
    }}

    /* 5. TABLA HTML TRANSPARENTE */
    .table-container {{
        overflow-x: auto;
        max-height: 500px;
        overflow-y: auto;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
    }}
    .glass-table {{
        width: 100%;
        border-collapse: collapse;
        color: #F8FAFC;
        font-size: 0.95rem;
    }}
    .glass-table th {{
        background: rgba(255, 255, 255, 0.04);
        padding: 15px;
        text-align: left;
        font-weight: 600;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        position: sticky;
        top: 0;
        z-index: 1;
    }}
    .glass-table td {{
        padding: 12px 15px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }}
    .glass-table tr:hover {{
        background: rgba(255, 255, 255, 0.06);
    }}
    .glass-table a {{
        color: #818CF8 !important;
        font-weight: bold;
        text-decoration: none;
    }}
    .glass-table a:hover {{ text-decoration: underline; }}

    /* 6. Estilo de los Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent !important;
        color: #94A3B8 !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border: none !important;
        padding-bottom: 10px !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: #FFFFFF !important;
        border-bottom: 3px solid #818CF8 !important;
    }}

    /* 7. Botones Glassmorphism */
    .stButton>button {{
        background: rgba(255, 255, 255, 0.05) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(15px) !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }}
    .stButton>button:hover {{
        background: rgba(255, 255, 255, 0.12) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3) !important;
    }}

    .block-container {{ padding-top: 3rem !important; }}
    </style>
    """, unsafe_allow_html=True)

DATA_LAKE = "./dags/data_lake"
REPORTE_PATH = f"{DATA_LAKE}/reporte_diario.csv"

# --- FUNCIONES DOCX ---
def insertar_linea_horizontal(paragraph):
    p = paragraph._element
    pPr = p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6') 
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pBdr.append(bottom)
    pPr.append(pBdr)

def generar_cv_docx(empresa, puesto, descripcion):
    url_ollama = "http://ollama:11434/api/generate"
    try:
        with open(f"{DATA_LAKE}/mi_cv.txt", 'r') as file: 
            mi_cv = file.read()
    except FileNotFoundError:
        st.error("No se encontró mi_cv.txt en el Data Lake.")
        return None

    # --- EL NUEVO PROMPT PARA GENERACIÓN DE DOCX (Indentación corregida) ---
    prompt = f"""
    Act as an Expert ATS Optimizer. Rewrite this CV in PROFESSIONAL ENGLISH.
    Candidate: Roberto Vargas. Context: Junior/Mid Data Engineer with high-impact architectural projects.
    Target Job: {puesto} at {empresa}.
    
    Instructions:
    1. Heavily emphasize his skills in: Apache Airflow, Docker, Python ETLs, PostgreSQL (pgvector), Google BigQuery, Metabase, and Local LLMs (Llama 3.2).
    2. Translate everything to professional English (C1 level).
    3. Tailor the summary and bullet points to match the target job description where truthful.
    4. Return ONLY a JSON object EXACTLY with this structure:
    {{
        "summary": "Your ATS-optimized summary here",
        "skills_list": ["skill1", "skill2"],
        "projects": [
            {{"name": "Project Name", "date": "Date", "bullets": ["Point 1", "Point 2"]}}
        ],
        "education": [
            {{"degree": "Degree Name", "date": "Date"}}
        ]
    }}
    
    CV DATA: {mi_cv}
    JOB DESCRIPTION: {descripcion[:2000]}
    """
    
    try:
        res = requests.post(url_ollama, json={"model": "llama3.2", "prompt": prompt, "format": "json", "stream": False}, timeout=400)
        cv_data = json.loads(res.json()['response'])
    except Exception as e:
        st.error(f"Error en el motor de IA o decodificando el JSON: {e}")
        return None

    doc = Document()
    
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)

    style = doc.styles['Normal']
    style.font.name = 'Arial' 
    style.font.size = Pt(11)
    style.paragraph_format.line_spacing = 1.15

    p_nombre = doc.add_paragraph()
    p_nombre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_n = p_nombre.add_run("ROBERTO VARGAS")
    run_n.font.size = Pt(26)
    run_n.bold = True

    p_c = doc.add_paragraph()
    p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_c.add_run("(55) 1234-5678 | Mérida, Mexico | roberto.vargas99@outlook.com | github.com/titorvc").font.size = Pt(10)

    def add_section(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        run = p.add_run(text.upper())
        run.bold = True
        run.font.size = Pt(14)
        insertar_linea_horizontal(p)

    # Summary
    add_section("Professional Summary")
    doc.add_paragraph(cv_data.get('summary', ''))

    # Skills 
    add_section("Technical Skills")
    skills = cv_data.get('skills_list', [])
    if isinstance(skills, list):
        doc.add_paragraph(", ".join(str(s) for s in skills))
    else:
        doc.add_paragraph(str(skills))

    # Projects 
    add_section("Data Engineering Projects")
    for proj in cv_data.get('projects', []):
        if isinstance(proj, dict):
            tbl = doc.add_table(rows=1, cols=2)
            tbl.width = Cm(16.5)
            c1, c2 = tbl.rows[0].cells
            
            p1 = c1.paragraphs[0]
            r1 = p1.add_run(proj.get('name', 'Project'))
            r1.bold = True
            r1.font.size = Pt(12)
            
            p2 = c2.paragraphs[0]
            p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r2 = p2.add_run(proj.get('date', ''))
            r2.font.italic = True
            
            bullets = proj.get('bullets', [])
            if isinstance(bullets, list):
                for bullet in bullets:
                    bp = doc.add_paragraph(str(bullet), style='List Bullet')
                    bp.paragraph_format.line_spacing = 1.15
                    bp.paragraph_format.left_indent = Cm(0.75)
            else:
                doc.add_paragraph(str(bullets))
            
            doc.add_paragraph().paragraph_format.space_after = Pt(8) 
        elif isinstance(proj, str):
            doc.add_paragraph(proj)

    # Education 
    add_section("Education")
    for edu in cv_data.get('education', []):
        p_edu = doc.add_paragraph()
        if isinstance(edu, dict):
            p_edu.add_run(edu.get('degree', '')).bold = True
            if edu.get('date'):
                p_edu.add_run(f" | {edu.get('date', '')}")
        elif isinstance(edu, str):
            p_edu.add_run(edu).bold = True

    file_name = f"CV_Roberto_{empresa.replace(' ', '_')}.docx"
    file_path = f"{DATA_LAKE}/{file_name}"
    doc.save(file_path)
    return file_path, file_name

# --- DASHBOARD UI ---
st.markdown("<h1 style='font-size: 3.5rem; font-weight: 800; letter-spacing: -1px;'>Welcome Back, Roberto!</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 1.2rem; color: #94A3B8 !important; margin-top: -15px; margin-bottom: 30px;'>Here's what's happening today in the data market.</p>", unsafe_allow_html=True)

if os.path.exists(REPORTE_PATH):
    df_completo = pd.read_csv(REPORTE_PATH)
    
    # --- SIDEBAR ---
    st.sidebar.markdown("<h2 style='font-size: 2rem; padding-bottom: 20px;'>Admin</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("### ⚙️ Radar Config")
    min_score = st.sidebar.slider("Match Threshold", 0, 100, 80)
    
    df_filtrado = df_completo[df_completo['score'] >= min_score].sort_values(by='score', ascending=False)
    
    # --- GLASS CARDS (MÉTRICAS) ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Extracted", len(df_completo))
    col2.metric("High Matches", len(df_filtrado))
    col3.metric("New Today", len(df_completo.head(5)))
    col4.metric("Avg Quality", f"{int(df_completo['score'].mean())}%")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["🚀 Recent Matches", "📊 Analytics", "📄 Resume Forger"])

    with tab1:
        st.markdown("### Top Opportunities")
        
        if not df_filtrado.empty:
            df_html = df_filtrado[['score', 'empresa', 'puesto', 'url', 'razon']].copy()
            df_html['url'] = df_html['url'].apply(lambda x: f'<a href="{x}" target="_blank">View Job ↗</a>')
            
            html_table = df_html.to_html(classes='glass-table', escape=False, index=False)
            
            st.markdown(f'<div class="table-container">{html_table}</div>', unsafe_allow_html=True)
        else:
            st.info("No matches found above the current threshold.")

    with tab2:
        st.markdown("### Market Insights")
        components.iframe("http://localhost:3000/public/question/bb07d518-1ccf-46b1-8b1d-d5410ee72c40", height=500, scrolling=True)

    with tab3:
        st.markdown("### Export Custom Application")
        if not df_filtrado.empty:
            df_filtrado['selector'] = df_filtrado['empresa'] + " - " + df_filtrado['puesto']
            opcion = st.selectbox("Select Target Job:", df_filtrado['selector'])
            if st.button("Generate .DOCX"):
                v = df_filtrado[df_filtrado['selector'] == opcion].iloc[0]
                with st.spinner("Compiling data..."):
                    resultado = generar_cv_docx(v['empresa'], v['puesto'], v['descripcion_full'])
                    if resultado:
                        path, name = resultado
                        with open(path, "rb") as f:
                            st.download_button("Download Resume", f, file_name=name)

else:
    st.warning("No data found. Please run the Airflow DAGs first.")
