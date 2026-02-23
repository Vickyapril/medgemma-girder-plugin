# medgemma-girder-plugin
From Upload to Research-Ready: Agentic Medical Data Governance with MedGemma
# From Upload to Research-Ready: Agentic Medical Data Governance with MedGemma

A privacy-first, local workflow for radiology DICOM governance triage using Girder, Apache Airflow, Linux worker execution, and MedGemma.

> **Safety statement:** This system does not perform diagnosis. It performs dataset governance triage.

---

## Demo Video

- **3-minute demo:** `<PASTE_YOUTUBE_LINK_HERE>`

---

## Architecture

![High-Level Architecture](./docs/assets/architecture/architecture_simple.png)

**Figure:** User triggers from Girder, Airflow orchestrates processing, Linux worker runs MedGemma governance reasoning, and results are written back to Girder.

---

## Problem

Medical imaging datasets are difficult to reuse for research due to:
- anonymization uncertainty
- inconsistent metadata quality
- slow and expensive manual review workflows

This project automates governance triage to accelerate research readiness in privacy-sensitive environments.

---

## What We Built

A local agentic workflow that:
1. Starts from a Girder item action (`Run MedGemma Triage`)
2. Triggers Airflow DAG orchestration
3. Executes DICOM processing + MedGemma governance reasoning on Linux
4. Produces structured triage outputs back in Girder

**Governance outputs include:**
- anonymization risk
- research usability assessment
- manual review recommendation
- structured artifacts for auditability

---

## Key Components

- **Girder (Kitware):** dataset management, item actions, metadata/artifact storage
- **Apache Airflow:** orchestration, retries, status, cleanup
- **Linux Worker:** data extraction, file handling, model execution
- **MedGemma:** governance-oriented reasoning over representative medical images

---

## Repository Structure

medgemma-girder-plugin/
├── src/
│   ├── girder_plugin.py
│   ├── airflow_integration.py
│   ├── medgemma_client.py
│   ├── dicom_processor.py
│   ├── dicom_anonymizer.py
│   └── zip_processor.py
├── web_client/
├── requirements.txt
├── setup.py
├── README.md
└── docs/
    └── assets/
        ├── architecture/
        └── screenshots/
