# VITS ERP Portal — Developer & Interview Instructions

This document provides a comprehensive overview of the VITS ERP web portal, explaining the architecture, core features, code file structure, utilized technologies, and specific Streamlit APIs used. It also includes interview preparation questions.

---

## 1. Streamlit Architecture & Technology Stack

### Is Streamlit 100% Python?
**Yes, it is 100% Python.** 
* You write all of the application logic, page routing, database queries, and data processing in pure Python (`streamlit_app.py`).
* Under the hood, Streamlit translates your Python code into a modern React-based web interface in the user's browser.
* In this specific codebase, we have also injected custom inline **HTML/CSS** inside `st.markdown()` calls to give the app a premium, custom glassmorphism design (with custom cards, colors, and gradients) that goes beyond Streamlit's default basic look.

### Specific Libraries Used (Dependencies)
These are imported at the top of our Python files to provide specialized functions:
* **`streamlit`**: Used to build the web interface, text inputs, selectors, columns, and navigation.
* **`plotly.express` & `plotly.graph_objects`**: Used to draw the premium **interactive progression charts**, Heatmaps, and Section Health graphs.
* **`pandas`**: Used to organize queried SQL rows into tabular structures (DataFrames) for feeding into graphs and tables.
* **`sqlite3`**: Connects the Python code to the local `vits_erp.db` database.
* **`reportlab.platypus`**: Renders the PDF documents dynamically (using Flowables, SimpleDocTemplate, and Paragraphs).
* **`requests` & `bs4` (BeautifulSoup)**: Used to make HTTP requests to the college portal and parse the HTML response during background scraping.
* **`datetime`**: Handles calendar dates for schedule lookups and DOB setups.

---

## 2. Core Features of the VITS ERP Application

### 🔐 Authentication & Session Management
* **Dual Portals**: Separate login portals for **Students** and **Admins**.
* **DOB Password Security**: Students log in using their roll number and Date of Birth (DOB) as their password.
* **Password Setup**: A dedicated onboarding page prompts new students to register their DOB on their first login.

### 🎓 Student Dashboard
* **Main Dashboard (Home)**:
  * **Branding Header**: Sticky, mobile-responsive branding header showing VITS logo, name, and student details.
  * **KPI Grid**: Glassmorphic cards displaying Overall Attendance, CGPA/SGPA, Credits Earned, and Backlogs count.
  * **Circular Progress Meter**: Visual rings displaying attendance and GPA progress side-by-side.
  * **Timetable Widget**: Displays the current day's class schedule automatically.
* **Attendance Tab**:
  * **Subject-wise health bars**: Visually represents attendance percentage for each subject.
  * **Skip Predictor Slider**: An interactive slider allowing students to simulate missing a specific number of days and see their projected attendance (displays Safe, Condonation, or Debarred status).
* **Academic Results (Marks) Tab**:
  * **Semester Toggle**: Syncs between Sem 1 and Sem 2 using session state selectboxes (both in the sidebar and directly next to the results header).
  * **Marks Progression Chart**: Interactive line graph tracking grades across Mid 1, Mid 2, and Final Examinations.
  * **Detailed Marks Tables**: Sectioned lists of scores for Mid 1, Mid 2, Lab Internals, and Final Exam grades.
* **SGPA Calculator Tab**:
  * Interactive sliders allowing students to simulate potential grades for each subject and calculate their projected SGPA/CGPA in real-time.
* **Analytics Tab**:
  * Charts showing attendance trends over time (Heatmaps and Line charts).
* **Timetable Tab**:
  * Full section weekly schedule view.
* **PDF Report Downloader**:
  * Generates a beautifully formatted PDF report containing the student's complete profile, attendance, and marks.

### ⚙️ Admin Console
* **Portal Analytics**: Statistics on active logins, page views, and downloaded reports.
* **Student Directory**: Allows admins to search, view, edit student details, and reset student passwords/DOBs.
* **Bulk Data Scraping**: Scraper tool to pull attendance/results directly from the main college server.
* **Section Health**: Interactive comparison charts analyzing average attendance across all branches and sections.
* **Direct SQL Console**: Allows admins to execute raw SQL queries to manage database tables directly.

---

## 3. Key Code Files & Their Roles

* **`streamlit_app.py`**: The **heart of the application**. It contains the entire UI routing, pages layout (Home, Results, Attendance, Admin console, etc.), styling customization (custom CSS classes), and interactivity logic.
* **`database.py` / `database_pg.py`**: Handles **all database operations**. It sets up SQL tables, manages connections (SQLite/PostgreSQL), and performs helper operations like `compute_cgpa()` and `gp_to_grade()`.
* **`pdf_generator.py`**: A helper code script that uses a library to draw tables, logos, and student details onto a **custom PDF layout** for downloads.
* **`harvester.py`**: The **data crawler (scraper)**. It connects directly to the college's parent ERP portal, automates credentials logging, parses the HTML, and saves timetable/marks/attendance data into our database.
* **`telegram_bot.py`**: Extends the app's functionality to Telegram, allowing students to check their marks and attendance by sending commands (like `/attendance` or `/marks`) to a Telegram bot.

---

## 4. Specific Streamlit API Components Used

### Layout & Structure
* **`st.columns([ratio1, ratio2, ...])`**: Splits the page layout into side-by-side columns (e.g., placing the semester selector next to the Results title, or splitting the Home page into 3 columns for the circular progress meter, subject health, and daily schedule).
* **`st.sidebar`**: Creates the left side navigation panel where the student profile card, menu options, and download buttons live.
* **`st.expander("Title")`**: Creates a collapsible/expandable drawer (used to hide/show details for each subject in the Attendance tab).

### Output & Visuals
* **`st.markdown(html_string, unsafe_allow_html=True)`**: Used extensively with `unsafe_allow_html=True` to bypass standard markdown and render **custom HTML/CSS**. This is how the premium college header, circular meters, glowing KPI cards, and custom tables are drawn.
* **`st.plotly_chart(figure)`**: Renders interactive Plotly charts (such as the Marks Progression line chart and Attendance bar charts).
* **`st.link_button("Label", "URL")`**: Renders a button that opens an external link in a new tab (used to open the college Cloud Drive).

### Inputs & Interactive Controls
* **`st.selectbox("Label", options)`**: Creates the dropdown menus (used for selecting the viewing semester and picking which day of the timetable to view).
* **`st.radio("Label", options)`**: Renders a radio list selector (used for the sidebar navigation links: *Home, Attendance, Marks, etc.*).
* **`st.slider("Label", min, max)`**: Creates sliders (used in the SGPA calculator and attendance skip predictor so students can drag and simulate grades/days missed).
* **`st.button("Label")`**: A clickable trigger (used for "Download Report PDF" and "Logout").
* **`st.text_input("Label", type="password")`**: Captures text inputs (used on the login screen for Roll Numbers and passwords).
* **`st.date_input("Label")`**: Opens a calendar date-picker widget (used during onboarding for the student to select their Date of Birth).

### Feedback & Status Displays
* **`st.success("Message")`**: Displays a green confirmation box (e.g., "Login Successful" or "Safe Zone").
* **`st.info("Message")`**: Displays a blue informational alert box (e.g., "No data found for this semester").
* **`st.warning("Message")`**: Displays a yellow warning alert box (e.g., "Risk Zone").
* **`st.error("Message")`**: Displays a red error box (e.g., "Incorrect roll number or password").

### Backend Logic & Operations
* **`st.session_state`**: A global dictionary that stores persistent data across user interactions (e.g., tracking the logged-in student's ID, branch, name, and the currently selected semester).
* **`st.rerun()`**: Instantly restarts script execution from the top of the file so that changes made by one action (like switching tabs or semesters) reflect immediately on the screen.

---

## 5. Comprehensive Interview Preparation Q&As

### Category A: Project Architecture & System Design

#### Q1: Can you explain the end-to-end architecture of this portal?
* **Your Answer**: 
  > *"The system uses a 4-tier architecture: 
  > 1. **Data Source**: The official college ERP portal (external).
  > 2. **Data Harvester/Scraper (`harvester.py`)**: Connects to the ERP, scrapes attendance, marks, and timetables using BeautifulSoup, and formats it.
  > 3. **Database (`vits_erp.db`)**: A local SQLite relational database storing tables for students, attendance, marks, timetables, and SGPA.
  > 4. **User Interfaces**: A **Streamlit web portal** (`streamlit_app.py`) for student/admin visual access and a **Telegram Bot** (`telegram_bot.py`) for quick mobile lookups."*

#### Q2: Why did you choose SQLite, and how would you scale it for production?
* **Your Answer**:
  > *"SQLite was chosen because it is serverless, lightweight, has zero configuration, and stores data in a single local file, which is perfect for development and prototyping. To scale this for a real production environment with thousands of concurrent students, I would transition to a database server like **PostgreSQL** or **MySQL**. This would support concurrent write operations, connection pooling, and better security configurations."*

---

### Category B: Web Scraping & Data Fetching (`harvester.py`)

#### Q3: How does your web scraper log into the college portal and extract data?
* **Your Answer**:
  > *"The scraper uses Python’s **`requests.Session()`** to maintain session cookies across requests. It sends a POST request with the student's credentials to the college login endpoint. Once authenticated, it accesses the attendance and marks pages, reads the HTML content, and uses **`BeautifulSoup`** to locate and extract data from table elements via CSS classes and HTML tags."*

#### Q4: What happens if the college ERP portal changes its user interface or HTML structure?
* **Your Answer**:
  > *"Since web scrapers rely on the HTML structure (tags and classes) of the target site, any structural change on the college ERP will cause the scraper to fail. To handle this:
  > 1. I wrapped scraping calls in `try-except` blocks with error logging.
  > 2. The database acts as a cache—if the scraper fails, students can still access their cached data.
  > 3. In production, I would configure alerts to notify developers immediately of scraper failures so CSS selectors can be updated."*

---

### Category C: Database & Calculations

#### Q5: How did you implement the CGPA and SGPA calculation logic?
* **Your Answer**:
  > *"I implemented a credit-weighted grading system based on JNTUH regulations. In `database.py`:
  > 1. I converted marks to letter grades and grade points (e.g., Score $\ge 90$ is 'O', worth 10 points; $\ge 40$ is 'C', worth 5 points; $< 40$ is 'F', worth 0 points).
  > 2. **SGPA** is calculated as: $\frac{\sum (\text{Grade Points} \times \text{Subject Credits})}{\sum \text{Subject Credits}}$ for the current semester.
  > 3. **CGPA** is calculated by aggregating the credit-weighted grade points across all completed semesters."*

#### Q6: How does the system handle student backlogs (fails) in calculations?
* **Your Answer**:
  > *"If a student scores below 40% in a final exam, they receive an **'F' grade (0 grade points)**. The database logs this failed status. On the home page:
  > 1. The backlog is counted, and the student's status is set to 'Pending' (or backlogs are listed).
  > 2. The subject is flagged in red in the grades table.
  > 3. The SGPA calculation includes the 0 grade points in the numerator but includes the subject credits in the denominator, dragging down the overall average as per university rules."*

---

### Category D: PDF Generation (`pdf_generator.py`)

#### Q7: How did you generate and serve the PDF reports?
* **Your Answer**:
  > *"I used the **`reportlab`** library, which allows programmatic drawing of PDFs. I defined a layout template showing the college header, student details table, attendance summary table, and marks table. The PDF is compiled in memory as a binary stream and served to the user using Streamlit's native downloader trigger, meaning no temporary files clutter the server's hard drive."*

---

### Category E: Telegram Bot Integration (`telegram_bot.py`)

#### Q8: How does the Telegram Bot interact with the database?
* **Your Answer**:
  > *"The bot uses the **`pyTelegramBotAPI`** library running in a polling loop. When a student sends a message containing their roll number, the bot queries the SQLite database, formats their attendance and marks into clean, readable text messages, and replies back immediately. It provides a lightweight, data-friendly alternative to loading the web page."*

---

### Category F: Performance & Security

#### Q9: How did you optimize query speeds in the SQLite database?
* **Your Answer**:
  > *"I added **database indexes** on columns that are frequently used in `WHERE` clauses (such as `roll_no` in the `marks`, `attendance`, and `sgpa_records` tables). This reduces lookup times from $O(N)$ (scanning the whole table) to $O(\log N)$ (binary search index lookups), keeping the dashboard load times under 100 milliseconds."*

#### Q10: How do you handle student privacy and data security?
* **Your Answer**:
  > *"1. **Authentication**: Students must authenticate using their roll number and a password (DOB).
  > 2. **Session Guarding**: On every page load, the script checks if `st.session_state.user_id` exists. If not, it halts execution and renders the login screen, preventing unauthorized URL access.
  > 3. **SQL Injection Prevention**: All SQL queries use parameterized placeholders (`?`) instead of string interpolation (e.g., `execute('... WHERE roll_no = ?', (roll,))`), neutralizing SQL injection attacks."*

---

### Category G: Streamlit Portal Interactivity (The Recent Code Fixes)

#### Q11: How does Streamlit handle state, and how did you implement login sessions?
* **Your Answer**: 
  > *"By default, Streamlit is stateless and reruns the entire Python script from line 1 to the end whenever a user clicks a button or changes an input. Any local variables are lost. To maintain user login state and track who is logged in, I used **`st.session_state`** (e.g., storing `st.session_state.user_id` and `st.session_state.role`)."*

#### Q12: How did you synchronize the two semester dropdowns (sidebar and result page) dynamically?
* **Your Answer**:
  > *"Having two selectboxes modify the same state can cause a conflict because of execution order. I stored the master semester choice in `st.session_state['selected_sem']`. At the very top of the script (before any UI is rendered), I check if either widget key (`sidebar_sem_select` or `result_sem_select`) was changed by the user, update the master key, and set both widgets' default index to match. This ensures both dropdowns stay completely in sync in a single execution pass."*

#### Q13: How did you design a premium UI if Streamlit only supports generic layouts?
* **Your Answer**:
  > *"Streamlit's default UI is simple, so I customized it by injecting custom HTML templates and CSS code using **`st.markdown(html, unsafe_allow_html=True)`**. I built glassmorphic layout grids, styling tokens, custom dashboard cards, progress legends, and college headers entirely in CSS, keeping the backend logic in Python."*

#### Q14: Why do you need `st.rerun()`, and when did you use it?
* **Your Answer**:
  > *"Since Streamlit runs top-to-bottom, if a user clicks **'Logout'**, I delete the keys in `st.session_state` and call **`st.rerun()`** to force the script to restart immediately from line 1. This prevents the dashboard from throwing errors due to missing session variables and redirects the user to the login page instantly."*

#### Q15: How did you handle charts and prevent them from crashing when a semester has no data?
* **Your Answer**:
  > *"I integrated **Plotly Express** (`px.bar` and `px.line`) with Streamlit via **`st.plotly_chart`**. If a student switches to a semester with no data (like Sem 1), Plotly will throw an error because the DataFrame is empty. I added guard checks (`if subj_data:`) to bypass the chart drawing and display a clean message instead."*
