# 2-Day Trial: PDF → Questions Extractor (Robust)

## 1\) Overview

Build a small pipeline (minimal API) that ingests PDF files and extracts **questions** as structured JSON. Questions may include **LaTeX**, **inline/figure images**, **multiple-choice options**, **multi-part sub-questions**, and **tables**. Deliver a working baseline **plus at least one improvement**.

---

## 2\) Core Goals

* **AI aptitude:** sensible choices for text/structure/figure extraction and heuristics/LLM use (if any).  
* **Coding ability:** clean, runnable code; resilient parsing; edge-case handling (tables, MCQ, multipart).  
* **Communication:** clear assumptions, limitations, and prioritized next steps under tight time constraints.

---

## 3\) Constraints

* **Input:** Provided PDFs (mix: typed text, LaTeX markers, figures, tables, MCQs, multi-part).  
* **Output:** Valid JSON (**candidate-defined schema**) **plus extracted images as files** referenced from JSON. You must: (a) define your own JSON schema  
* **Runtime:** ≤ **3 minutes per PDF up to 10 pages**.  
* **Parallelism:** Support **≥ 5 PDFs in parallel** without crashes (graceful degradation allowed; log failures).  
* **Robustness targets:** Accurately represent **MCQ options**, **multi-part numbering** (e.g., `Q1(a)(i)`), **table structures**, and **figure references**.

---

## 4\) Deliverables

* **Code repo** (GitHub).  
* **README** (quickstart, dependencies, how to run API).  
* **NOTES.md** (≤1 page): approach, methods used, key trade-offs, baseline → improvement, what you’d do next.  
* **Outputs**: JSON files conforming to **your schema** \+ extracted image files (referenced by filename from JSON).  
* **Evaluation System Design**

---

## 5\) Interface

### Minimal API 

POST /extract

{

  "pdf\_path": "/path/to/input.pdf"

}

→

{ "status": "ok", "output\_json\_path": "...", "assets\_dir": "..." }

---

## 6\) Dev Set & Evaluation Protocol

We will provide a **dev set of 5 PDFs** covering:

* MCQs with varying option layouts  
* Multi-part questions with nested numbering  
* Tables (general)  
* Pages with embedded figures/captions  
* Light LaTeX markers in text

**Run requirements**

* Single command to process the set (e.g., `bash run_eval.sh pdfs/*.pdf outputs/`).  
* Print: per-PDF processing time and any validation errors.

---

## 7\) Grading Rubric (100 points) — **Key constraints weighted higher**

| Category | What we’re looking for | Weight |
| :---- | :---- | :---- |
| **Key Constraints Compliance** | Meets **runtime** (≤3 min / 10-page PDF), **parallelism** (≥5 PDFs concurrently) with stability & failure logging | **30** |
| **Correctness on Dev Set** | Structural fidelity on our 5 docs (MCQ options captured, multipart hierarchy preserved, tables structured, figures linked) | **25** |
| **Structural Correctness (Schema)** | JSON conforms to **your schema**; images referenced correctly (filenames; bbox optional) | **20** |
| **Code Quality & Runability** | Clean, modular, deterministic runs; batch script works; clear README | **15** |
| **Approach & Communication** | Clear assumptions, trade-offs, baseline → improvement; concise NOTES.md with limits & prioritized next steps | **10** |

---

## 8\) Timebox & Expectations (**2-day work trial**)

Plan for **2 days**. You won’t perfect everything — show judgment: make it run end-to-end, cover key edge cases, document gaps, and ship one meaningful improvement.

---

## 9\) Quick Checklist

* ✅ **Candidate-defined schema** \+ **JSON-Schema** file  
* ✅ Images exported and referenced by filename (bbox optional)  
* ✅ Tables & MCQs represented structurally (not just plaintext)  
* ✅ **Runtime & parallelism** constraints measured and reported; mitigations if not met  
* ✅ NOTES.md: what worked, failed, next steps (prioritized)  
* ✅ **Evaluation System Design**

---

## 10\) **Final Submission Must Include: Evaluation System Design (Detailed Document)**

Provide a separate document (**EVAL.md**, 1–2 pages) describing **how to evaluate your system**
