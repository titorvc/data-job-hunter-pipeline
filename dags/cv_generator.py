import pandas as pd
import time
from sqlalchemy import create_engine
import os
import json
import re
from groq import Groq
from fpdf import FPDF

# Ensure output directory exists
OUTPUT_DIR = "/opt/airflow/dags/data_lake/generated_cvs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# SECTION LABELS PER LANGUAGE
# ═══════════════════════════════════════════════════════════════════
LABELS = {
    "en": {
        "summary_title": "PROFESSIONAL SUMMARY",
        "skills_title": "TECHNICAL SKILLS",
        "experience_title": "EXPERIENCE",
        "projects_title": "DATA ENGINEERING PROJECTS",
        "education_title": "EDUCATION",
        "prompt_lang": "Write the CV entirely in English.",
    },
    "es": {
        "summary_title": "RESUMEN PROFESIONAL",
        "skills_title": "HABILIDADES TECNICAS",
        "experience_title": "EXPERIENCIA",
        "projects_title": "PROYECTOS DE INGENIERIA DE DATOS",
        "education_title": "EDUCACION",
        "prompt_lang": "Escribe el CV completamente en español.",
    },
}


def remove_old_cvs():
    """Removes previous day's CVs to keep the folder clean."""
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".pdf"):
            os.remove(os.path.join(OUTPUT_DIR, f))


# ═══════════════════════════════════════════════════════════════════
# GROQ: GENERATE TAILORED CV JSON
# ═══════════════════════════════════════════════════════════════════
def generate_tailored_cv(puesto, empresa, descripcion, base_cv, lang="en"):
    """Groq API rewrites the CV and outputs structured JSON for formatting."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("CRITICAL: GROQ_API_KEY not set.")
        return None

    client = Groq(api_key=api_key)
    lang_instruction = LABELS[lang]["prompt_lang"]

    prompt = f"""
    Act as an expert Resume Writer. Your task is to rewrite Roberto Vargas's CV to make it perfectly tailored for the position of '{puesto}' at '{empresa}'.
    
    {lang_instruction}
    
    JOB DESCRIPTION:
    {descripcion}
    
    BASE CV:
    {base_cv}
    
    INSTRUCTIONS:
    - You MUST output a strictly valid JSON object. Do not include markdown formatting or explanations, just the JSON.
    - DO NOT summarize excessively. Keep the descriptions long, robust, and detailed so that the CV looks full and professional.
    - Write exactly 3 to 4 substantial, detailed bullet points per project. 
    - Keep Roberto's real experience, but rephrase bullets and emphasize the skills mentioned in the job description.
    - Do not invent experience he does not have.
    
    JSON STRUCTURE:
    {{
      "name": "ROBERTO VARGAS",
      "contact": "+52 999 640 5649 | Merida, Mexico | roberto.vargas99@outlook.com | github.com/titorvc",
      "summary": "A 2-3 sentence paragraph emphasizing fit for this specific job...",
      "skills": "List of core skills, comma separated...",
      "projects": [
        {{
          "title": "Project Name",
          "date": "2023 - 2024",
          "bullets": ["Bullet 1...", "Bullet 2..."]
        }}
      ],
      "education": "B.S. in Data Engineering | 2023-Present"
    }}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="qwen/qwen3.6-27b",
            temperature=0.2,
            max_tokens=1000,
        )
        content = chat_completion.choices[0].message.content.strip()

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        json_str = json_match.group(0) if json_match else content

        try:
            cv_data = json.loads(json_str)
        except Exception:
            print("Failed to parse JSON, returning fallback")
            cv_data = _fallback_cv(lang)
        return cv_data
    except Exception as e:
        print(f"Error generating CV for {empresa}: {e}")
        return None


def _fallback_cv(lang="en"):
    """Returns a safe fallback CV if Groq parsing fails."""
    if lang == "es":
        return {
            "name": "ROBERTO VARGAS",
            "contact": "+52 999 640 5649 | Merida, Mexico | roberto.vargas99@outlook.com | github.com/titorvc",
            "summary": "Ingeniero de Datos e IA enfocado en disenar ecosistemas de datos reproducibles y escalables. Experiencia en pipelines ETL, orquestacion multi-agente con LangGraph y automatizacion inteligente con Airflow, Docker y Groq.",
            "skills": "Python, SQL, Bash, Apache Airflow, Docker, PostgreSQL, pgvector, LangGraph, FastAPI, Groq API, Pandas, Git, Streamlit, n8n, Linux",
            "experience": [
                {
                    "title": "Pasante de Investigacion de Datos",
                    "company": "Preparatoria No. 2, UADY",
                    "date": "Ene 2025 - May 2025",
                    "bullets": [
                        "Realice analisis y visualizacion de datos educativos con Python y Pandas.",
                        "Construi scripts automatizados para extraccion y limpieza masiva de datos de rendimiento estudiantil.",
                        "Aplique metodos estadisticos para identificar patrones y genere reportes analiticos integrales.",
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Job Hunter AI (Pipeline RAG Autonomo)",
                    "date": "2026 - Presente",
                    "bullets": [
                        "Disene un sistema de reclutamiento pasivo automatizado con Apache Airflow y Docker.",
                        "Construi un pipeline RAG con scraping de 30+ fuentes, PostgreSQL (pgvector) y Groq API.",
                        "Automatice el envio diario de vacantes con CVs en PDF optimizados para ATS.",
                    ],
                },
                {
                    "title": "Plataforma de Consultoria IA Agentica",
                    "date": "2026 - Presente",
                    "bullets": [
                        "Arquitecte un sistema multi-agente con LangGraph para flujos de consultoria B2B.",
                        "Implemente agentes especializados con compuertas de aprobacion humana (human-in-the-loop).",
                        "Construi la API con FastAPI y la interfaz con Streamlit.",
                    ],
                },
                {
                    "title": "Sistema de Automatizacion de Agendas",
                    "date": "2025 - Presente",
                    "bullets": [
                        "Desarrolle automatizacion integral en Python para crear y despachar agendas operativas.",
                        "Integre ReportLab para generacion profesional de PDFs A5.",
                    ],
                },
                {
                    "title": "Laboratorio de Datos Agentico",
                    "date": "2025 - 2026",
                    "bullets": [
                        "Desplegue un laboratorio de datos local usando microservicios Docker para flujos de IA.",
                        "Integre n8n como motor de orquestacion y Browserless para web scraping programatico avanzado.",
                    ],
                }
            ],
            "education": "Ing. en Ciencia de Datos - Universidad Politecnica de Yucatan (UPY) | 2023 - Presente",
        }
    else:
        return {
            "name": "ROBERTO VARGAS",
            "contact": "+52 999 640 5649 | Merida, Mexico | roberto.vargas99@outlook.com | github.com/titorvc",
            "summary": "Data & AI Engineer focused on designing reproducible, scalable data ecosystems. Experienced in end-to-end ETL pipelines, multi-agent orchestration with LangGraph, and intelligent automation with Airflow, Docker, and Groq.",
            "skills": "Python, SQL, Bash, Apache Airflow, Docker, PostgreSQL, pgvector, LangGraph, FastAPI, Groq API, Pandas, Git, Streamlit, n8n, Linux",
            "experience": [
                {
                    "title": "Data Research Intern",
                    "company": "Preparatoria No. 2, UADY",
                    "date": "Jan 2025 - May 2025",
                    "bullets": [
                        "Conducted educational data analysis and visualization to support institutional decision-making.",
                        "Built automated scripts for massive data extraction and cleaning of student performance datasets.",
                        "Applied statistical methods to identify academic patterns and generated comprehensive reports.",
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Job Hunter AI (Autonomous RAG Pipeline)",
                    "date": "2026 - Present",
                    "bullets": [
                        "Designed an end-to-end recruitment automation system with Apache Airflow and Docker.",
                        "Built a complete RAG pipeline with 30+ source scraping, PostgreSQL (pgvector), and Groq API.",
                        "Automated daily delivery of top-matched vacancies with ATS-optimized PDF resumes.",
                    ],
                },
                {
                    "title": "Agentic AI Consulting Platform",
                    "date": "2026 - Present",
                    "bullets": [
                        "Architected a multi-agent AI system using LangGraph for B2B consulting workflows.",
                        "Implemented specialized agents with human-in-the-loop approval gates.",
                        "Built the backend API with FastAPI and client interface with Streamlit.",
                    ],
                },
                {
                    "title": "Schedule Automation System",
                    "date": "2025 - Present",
                    "bullets": [
                        "Developed comprehensive Python automation for creating and dispatching operational schedules.",
                        "Integrated ReportLab for professional A5 PDF generation with branded templates.",
                    ],
                },
                {
                    "title": "Agentic Data Lab",
                    "date": "2025 - 2026",
                    "bullets": [
                        "Deployed a local data lab using Docker microservices tailored for AI development workflows.",
                        "Integrated n8n orchestration engine and Browserless for advanced programmatic web scraping.",
                    ],
                }
            ],
            "education": "B.S. in Data Engineering - Universidad Politecnica de Yucatan (UPY) | 2023 - Present",
        }


# ═══════════════════════════════════════════════════════════════════
# PDF GENERATOR WITH MINIMALIST DESIGN
# ═══════════════════════════════════════════════════════════════════
class StyledPDF(FPDF):
    """Custom PDF class with minimalist divider bars and clean typography."""

    # ── Colors ──
    BLACK = (30, 30, 30)
    DARK_GRAY = (80, 80, 80)
    MID_GRAY = (140, 140, 140)
    LIGHT_GRAY = (210, 210, 210)
    ACCENT = (50, 50, 50)

    def _draw_divider(self, thickness=0.4, top_margin=2, bottom_margin=4):
        """Draws a thin minimalist horizontal divider line."""
        y = self.get_y() + top_margin
        self.set_draw_color(*self.LIGHT_GRAY)
        self.set_line_width(thickness)
        self.line(15, y, 195, y)
        self.set_y(y + bottom_margin)

    def _draw_thick_divider(self, thickness=0.8, top_margin=1, bottom_margin=3):
        """Draws a slightly thicker divider for the header area."""
        y = self.get_y() + top_margin
        self.set_draw_color(*self.ACCENT)
        self.set_line_width(thickness)
        self.line(15, y, 195, y)
        self.set_y(y + bottom_margin)

    def section_title(self, title):
        """Renders a section title with a divider underneath."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.BLACK)
        self.cell(0, 7, title.upper(), 0, 1, "L")
        self._draw_divider(thickness=0.3, top_margin=0, bottom_margin=3)


def safe_text(text):
    if not text:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def generate_pdf(cv_data, filename, lang="en"):
    """Generates a clean, minimalist PDF with thin divider bars."""
    labels = LABELS[lang]
    pdf = StyledPDF()
    pdf.add_page()
    # Reducimos un poco los márgenes para que haya más espacio y aumentamos la fuente
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── Header: Name ──
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*StyledPDF.BLACK)
    name = cv_data.get("name", "ROBERTO VARGAS")
    pdf.cell(0, 14, safe_text(name), 0, 1, "C")

    # ── Header: Contact ──
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*StyledPDF.MID_GRAY)
    contact = cv_data.get("contact", "")
    pdf.cell(0, 6, safe_text(contact), 0, 1, "C")
    pdf.ln(2)

    # ── Thick header divider ──
    pdf._draw_thick_divider()
    pdf.ln(3)

    # ── Professional Summary ──
    pdf.section_title(labels["summary_title"])
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*StyledPDF.DARK_GRAY)
    pdf.multi_cell(0, 5.5, safe_text(cv_data.get("summary", "")))
    pdf.ln(6)

    # ── Technical Skills ──
    pdf.section_title(labels["skills_title"])
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*StyledPDF.DARK_GRAY)
    pdf.multi_cell(0, 5.5, safe_text(cv_data.get("skills", "")))
    pdf.ln(6)
    
    # ── Experience ──
    if "experience" in cv_data and cv_data["experience"]:
        pdf.section_title(labels["experience_title"])
        for i, exp in enumerate(cv_data.get("experience", [])):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*StyledPDF.BLACK)
            title = safe_text(exp.get("title", ""))
            date = safe_text(exp.get("date", ""))
            company = safe_text(exp.get("company", ""))
            
            pdf.cell(140, 6, f"{title} | {company}", 0, 0, "L")
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(*StyledPDF.MID_GRAY)
            pdf.cell(0, 6, date, 0, 1, "R")
    
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*StyledPDF.DARK_GRAY)
            for bullet in exp.get("bullets", []):
                pdf.set_x(18)
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(4, 5.5, chr(149), 0, 0, "L")
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 5.5, safe_text(bullet))
                
            if i < len(cv_data.get("experience", [])) - 1:
                pdf.ln(2)
                pdf._draw_divider(thickness=0.15, top_margin=1, bottom_margin=3)
        pdf.ln(6)

    # ── Projects ──
    pdf.section_title(labels["projects_title"])
    for i, proj in enumerate(cv_data.get("projects", [])):
        # Project title + date on same line
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*StyledPDF.BLACK)
        title = safe_text(proj.get("title", ""))
        date = safe_text(proj.get("date", ""))
        pdf.cell(140, 6, title, 0, 0, "L")
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*StyledPDF.MID_GRAY)
        pdf.cell(0, 6, date, 0, 1, "R")

        # Bullet points
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*StyledPDF.DARK_GRAY)
        for bullet in proj.get("bullets", []):
            pdf.set_x(18)
            # Small bullet dot
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(4, 5.5, chr(149), 0, 0, "L")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 5.5, safe_text(bullet))

        # Thin divider between projects (not after the last one)
        if i < len(cv_data.get("projects", [])) - 1:
            pdf.ln(2)
            pdf._draw_divider(thickness=0.15, top_margin=1, bottom_margin=3)

    pdf.ln(6)

    # ── Education ──
    pdf.section_title(labels["education_title"])
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*StyledPDF.DARK_GRAY)
    edu = cv_data.get("education", "")
    pdf.multi_cell(0, 4.8, safe_text(edu))

    pdf.output(filename)
    print(f"PDF saved: {filename}")
    return filename


# ═══════════════════════════════════════════════════════════════════
# MAIN: GENERATE ALL CVs (EN + ES)
# ═══════════════════════════════════════════════════════════════════
def generate_all_cvs():
    print("Starting bilingual CV generation (EN + ES)...")
    engine = create_engine(
        "postgresql+psycopg2://roberto:superpassword123@postgres:5432/job_hunter"
    )

    try:
        df_top = pd.read_sql("SELECT * FROM ofertas_empleo WHERE score >= 85", con=engine)
    except Exception as e:
        print(f"Error reading vacancies: {e}")
        return

    if df_top.empty:
        print("No vacancies with score >= 85 today.")
        return

    # Load both CV bases
    cv_bases = {}
    for lang, fname in [("en", "mi_cv.txt"), ("es", "mi_cv_es.txt")]:
        try:
            with open(f"/opt/airflow/dags/data_lake/{fname}", "r") as file:
                cv_bases[lang] = file.read()
        except FileNotFoundError:
            try:
                with open(f"/opt/airflow/dags/{fname}", "r") as file:
                    cv_bases[lang] = file.read()
            except FileNotFoundError:
                print(f"WARNING: {fname} not found, skipping {lang} CVs.")

    if not cv_bases:
        print("CRITICAL: No CV base files found.")
        return

    remove_old_cvs()

    for index, row in df_top.iterrows():
        puesto = row["titulo_puesto"]
        empresa = row["empresa"]
        descripcion = str(row["descripcion"])[:2000]

        for lang, base_cv in cv_bases.items():
            suffix = "EN" if lang == "en" else "ES"
            print(f"Generating {suffix} CV for: {empresa} - {puesto}")
            cv_data = generate_tailored_cv(puesto, empresa, descripcion, base_cv, lang)

            if cv_data:
                safe_empresa = "".join(x for x in empresa if x.isalnum())
                filename = os.path.join(
                    OUTPUT_DIR, f"ATS_CV_{suffix}_{safe_empresa}.pdf"
                )
                generate_pdf(cv_data, filename, lang)

            # Rate limit: Groq free tier = 1000 output tokens/min
            print("  Waiting 65s for Groq rate limit...")
            time.sleep(65)

    print("Bilingual CV generation completed.")


if __name__ == "__main__":
    generate_all_cvs()
