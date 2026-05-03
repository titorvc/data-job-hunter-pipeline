# --- EL NUEVO PROMPT PARA GENERACIÓN DE DOCX ---
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
