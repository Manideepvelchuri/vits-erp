# Technical Proposal: VITS Academic Hub & NotebookLM Integration

This document outlines the architecture, database design, user interface layout, and parsing workflow to integrate a comprehensive **Academic Hub** (Syllabus Tracker, MCQ/QB Quizzer, Lab Code Library, and NotebookLM support) into the existing **VITS Academic ERP Streamlit application**.

---

## 📋 1. Project Context & Objectives

The current application is a **VITS Academic ERP & Bunk Intelligence Dashboard** built using:
* **Frontend**: Streamlit (Python) with custom CSS styling and Plotly graphs.
* **Database**: SQLite locally (`vits_erp.db`) and Supabase PostgreSQL in production (dynamically routed via the `DATABASE_URL` environment variable).

We want to expand the **Student Dashboard** by adding a new page: **`📚 Academic Hub`**. 
This hub will leverage the student's branch and semester to dynamically serve syllabi, lab programs, descriptive question banks, and interactive MCQ practice quizzes loaded directly from their college Word documents (`.doc` and `.docx`).

---

## 📂 2. Available Local Source Materials

The user has provided a local folder: `academic_materials/I Year QB VR25 and VR23/` containing:
* **1.1 VR25 QB (Semester 1)**: `Chemistry QB.doc`, `EDC Question Bank -Mid 1.docx`, `PPS Question Bank 2025-26.doc`, etc.
* **1.2 VR25 QB (Semester 2)**: `DS.doc` (Data Structures), `EDC.docx` (Electronic Devices and Circuits), `PYTHON.doc` (Python Programming), `ECA-II.docx`, etc.

### Structure of `EDC.docx` (Sample):
1. **Header Details**: Class, Subject Code, Semester.
2. **Descriptive Question Bank**: Tables containing `[Q.No, Description, Marks, CO, PO, BTL]`.
3. **Objective Question Bank**:
   * **MCQs**: Numbered list (1, 2, 3...) containing question text followed by options `(a) ... (b) ... (c) ... (d) ...`.
   * **Fill-in-the-Blanks (FIB)**: Numbered list (11, 12, 13...) with blanks (`___`).
   * **Answer Key**: Tables containing `[Q.No., Answer, Q.No., Answer]`.

---

## ⚙️ 3. Proposed Database Schema

To support these features, the following database tables will be added to the SQLite and Supabase PostgreSQL databases:

```sql
-- 1. Subject-to-File mappings
CREATE TABLE academic_resources (
    id SERIAL PRIMARY KEY,
    branch TEXT,             -- e.g., 'ECE'
    semester INTEGER,        -- e.g., 2
    subject_code TEXT,       -- e.g., 'EC201'
    resource_type TEXT,      -- e.g., 'Syllabus', 'Lab Manual', 'Question Bank'
    file_name TEXT,          -- e.g., 'EDC.docx'
    file_url TEXT            -- Remote/local file path
);

-- 2. Syllabus topics for progress tracking
CREATE TABLE syllabus_topics (
    id SERIAL PRIMARY KEY,
    subject_code TEXT,
    unit INTEGER,            -- 1 to 5
    topic_text TEXT
);

-- 3. Student-specific syllabus study progress
CREATE TABLE student_syllabus_progress (
    roll_no TEXT,
    topic_id INTEGER,
    status TEXT DEFAULT 'NOT_STARTED', -- 'NOT_STARTED', 'IN_PROGRESS', 'MASTERED'
    PRIMARY KEY (roll_no, topic_id),
    FOREIGN KEY (topic_id) REFERENCES syllabus_topics(id)
);

-- 4. Question bank database (Descriptive & FIB)
CREATE TABLE question_banks (
    id SERIAL PRIMARY KEY,
    subject_code TEXT,
    unit INTEGER,
    q_type TEXT,            -- 'DESCRIPTIVE', 'FIB'
    question TEXT,
    answer_text TEXT,       -- Null for descriptive, populated for FIB
    marks TEXT,             -- e.g., '2M', '10M'
    co INTEGER,
    btl INTEGER
);

-- 5. Multiple choice questions for interactive practice
CREATE TABLE mcqs (
    id SERIAL PRIMARY KEY,
    subject_code TEXT,
    unit INTEGER,
    question TEXT,
    option_a TEXT,
    option_b TEXT,
    option_c TEXT,
    option_d TEXT,
    correct_option CHAR(1), -- 'A', 'B', 'C', or 'D'
    explanation TEXT        -- Optional explanation/formula
);
```

---

## 🛠️ 4. Detailed Feature Design

### Feature A: ECE Resource Center & Lab Reference Library
* **UI**: Clean card grid for each current subject. Includes filter fields and quick download links.
* **Lab Code Tab**: A sidebar or split screen showing lab programs. On click, the code displays inside a dark code block with syntax highlighting:
  ```python
  st.code(program_code, language='python')
  ```
  Includes a **Copy** button and a **Download (.py)** button.

### Feature B: Interactive Syllabus Tracker
* **UI**: Collapsible accordions for Unit 1 to Unit 5. Inside is a checkbox list of topics.
* **UX**: Checkboxes toggle completion status dynamically. A primary progress bar updates instantly.
* **State**: Uses `student_syllabus_progress` to fetch and store selections per student.

### Feature C: Question Bank Quizzer & MCQ Practice Engine
* **Descriptive Study Mode**: Displays questions with a collapsible `"Reveal Answer"` accordion containing tips or step-by-step solutions.
* **MCQ Practice Mode**:
  * Renders one question at a time using `st.radio` for options.
  * Shows instant feedback when `Check Answer` is clicked (Green `st.success` if correct, Red `st.error` showing the right key if wrong).
  * Saves mistakes to `st.session_state.quiz_history` for final review.
  * Generates a **Quiz Scoreboard** at the end with topic recommendations.

### Feature D: NotebookLM AI Integration
Google’s **NotebookLM** is a powerful tool for document analysis and AI audio generation. Since NotebookLM doesn't have an API yet, we will integrate it via:
1. **Export for NotebookLM**: A button called `"Generate NotebookLM Package"`. It compiles a student's syllabus topics, flagged question bank questions, and MCQ wrong answers into a single, clean `.md` markdown file for download. The student simply uploads this single file to NotebookLM to generate custom audio briefings or study sheets.
2. **AI Audio Briefing Player**: The admin can generate an Audio Overview (podcast) in NotebookLM, save the `.mp3`, place it in the folder, and we will stream/play it directly on the dashboard via `st.audio()`.

---

## 🧪 5. Discussion Points & Questions for Alternative AIs

*If you are copying this document to another AI, paste these questions to brainstorm optimizations:*

1. **How should we parse the old binary `.doc` files?** 
   Since `python-docx` only supports `.docx`, what is the best python-native solution to parse `.doc` question banks on a Linux cloud container (where Microsoft Word is not installed)? (e.g., should we use `pandoc`, `docx2txt`, `striprtf`, or pre-convert them using a local script before deploying?)
2. **What is the cleanest way to manage Streamlit's state for the MCQ Quiz?**
   Streamlit notoriously reruns scripts from top-to-bottom on every interaction. What state structure using `st.session_state` prevents the quiz from resetting when a student switches tabs or interacts with other parts of the dashboard?
3. **How can we write a highly robust parser for docx tables?**
   docx tables have merged cells, missing headers, or nested formats. Can you write a Python script using `python-docx` to reliably parse descriptive questions from tables with `[Q.No, Description, Marks, CO]` and handle merged cells safely?
4. **How can we correlate syllabus topics with attendance?**
   If a student is absent on a specific date, how can we map that date to the syllabus table to show them which topics they missed and need to study?
