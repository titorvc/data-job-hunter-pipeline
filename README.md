# ⚡ Data Job Hunter Pro

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Apache Airflow](https://img.shields.io/badge/Airflow-2.8-017CEE?style=for-the-badge&logo=apache-airflow)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-316192?style=for-the-badge&logo=postgresql)
![Google BigQuery](https://img.shields.io/badge/BigQuery-OLAP-4285F4?style=for-the-badge&logo=google-cloud)
![Ollama](https://img.shields.io/badge/AI-Llama_3.2-black?style=for-the-badge&logo=meta)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=for-the-badge&logo=streamlit)

## 📌 Overview
Data Job Hunter Pro is an end-to-end, AI-powered Data Engineering ETL pipeline and local Agentic Dashboard. It automates the discovery, extraction, cognitive evaluation, and application process for Remote Data Engineering and Data Analytics roles.

Built entirely on local microservices, it fetches real-time data from 30 global APIs and RSS feeds, filters noise using Pandas, stores historical data in a dual OLTP/OLAP architecture, and uses local LLMs to score job matches and dynamically generate ATS-optimized `.docx` resumes.

## 🏗️ Architecture & Workflow

1. **Massive Radar (Airflow DAG 02):** 
   - Scrapes 30 Remote-First APIs (Himalayas, RemoteOK, Upwork, etc.). 
   - Applies a strict "Titanium Filter" (NLP) to isolate Data/Analytics roles compatible with LATAM/UTC-6, removing senior-level noise and geographically restricted roles.
2. **Dual Load (Upsert Engine):** 
   - Identifies unique URLs to prevent duplicates. 
   - Saves actionable jobs to local **PostgreSQL** (OLTP) and backs up historical data to **Google BigQuery** (OLAP).
3. **Cognitive Evaluation (Airflow DAG 03):** 
   - Reads new entries and utilizes a local **Llama 3.2 (via Ollama)** to evaluate the job description against the candidate's core stack (Airflow, Docker, Python, SQL, n8n). 
   - Assigns a Match Score (0-100) and provides reasoning.
4. **Command Center (Streamlit + Metabase):** 
   - Features a custom **Abstract Glassmorphism UI**.
   - Integrates Metabase for deep market analytics.
   - Includes an **"ATS Resume Forger"** that forces the LLM to rewrite project experiences into a tailored `.docx` file specific to the selected company.

## 🚀 Local Setup (Docker Compose)
*Note: `.env`, local databases, and GCP credentials are git-ignored for security reasons.*
```bash
# 1. Build and start the cluster (6 containers)
docker compose up -d --build

# 2. Access the Ecosystem:
# - Airflow (ETL Orchestration): http://localhost:8081
# - Streamlit (Glassmorphism Dashboard): http://localhost:8501
# - Metabase (Business Intelligence): http://localhost:3000
