"""pdf_generator.py — ReportLab PDF report card"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER

BRAND_BLUE = colors.HexColor('#00D8C6')
BRAND_DARK = colors.HexColor('#111111')
BRAND_GRAY = colors.HexColor('#6B7280')
LIGHT_BG   = colors.HexColor('#f0fdfa')
SUCCESS    = colors.HexColor('#10B981')
WARNING    = colors.HexColor('#F59E0B')
DANGER     = colors.HexColor('#EF4444')
PURPLE     = colors.HexColor('#8B5CF6')


def _att_color(pct):
    if pct >= 75: return SUCCESS
    if pct >= 65: return WARNING
    return DANGER


def generate_report_pdf(student, attendance_rows, marks_by_type, sgpa, cgpa, semester='Sem 2', attendance_semester=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story  = []

    title = ParagraphStyle('T', parent=styles['Normal'], fontSize=20,
        textColor=BRAND_BLUE, alignment=TA_CENTER,
        fontName='Helvetica-Bold', spaceAfter=4)
    sub = ParagraphStyle('S', parent=styles['Normal'], fontSize=10,
        textColor=BRAND_GRAY, alignment=TA_CENTER, spaceAfter=2)
    section = ParagraphStyle('Sec', parent=styles['Normal'], fontSize=12,
        textColor=BRAND_DARK, fontName='Helvetica-Bold',
        spaceBefore=12, spaceAfter=6)

    story.append(Paragraph('VITS Academic ERP', title))
    story.append(Paragraph('Vignan Institute of Technology and Science — Code: 891', sub))
    story.append(HRFlowable(width='100%', thickness=1, color=BRAND_BLUE, spaceAfter=10))

    info_data = [
        ['Name',     student.get('name','-'),    'Roll No', student.get('roll_no','-')],
        ['Section',  student.get('section','-'), 'Branch',  student.get('branch','-')],
        ['Semester', semester,                   '',        ''],
    ]
    info_t = Table(info_data, colWidths=[3*cm, 7*cm, 3*cm, 5*cm])
    info_t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1),  'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1),  'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), BRAND_GRAY),
        ('TEXTCOLOR', (2,0), (2,-1), BRAND_GRAY),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [LIGHT_BG, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('SPAN', (1,2), (3,2)),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 12))

    # Attendance
    att_sem_label = attendance_semester if attendance_semester else semester
    story.append(Paragraph(f'Attendance Summary ({att_sem_label})', section))
    att_data = [['Subject','Conducted','Attended','%','Status']]
    tc = ta = 0
    for r in attendance_rows:
        c = r['hours_conducted'] or 0
        a = r['hours_attended']  or 0
        tc += c
        ta += a
        pct = round(a/c*100, 1) if c > 0 else 0.0
        status = 'Good' if pct >= 75 else 'Condonation' if pct >= 65 else 'Debarred'
        att_data.append([r['subject'], str(c), str(a), f'{pct}%', status])
    overall = round(ta/tc*100, 1) if tc > 0 else 0.0
    att_data.append(['OVERALL', str(tc), str(ta), f'{overall}%', ''])

    att_t = Table(att_data, colWidths=[6*cm, 2.5*cm, 2.5*cm, 2*cm, 4*cm])
    att_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BRAND_BLUE),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, LIGHT_BG]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e2e8f0')),
        ('FONTNAME',   (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID',       (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('PADDING',    (0,0), (-1,-1), 5),
    ])
    for i, row in enumerate(att_data[1:-1], start=1):
        try:
            pv = float(row[3].replace('%', ''))
            col = _att_color(pv)
            att_style.add('TEXTCOLOR', (3,i), (3,i), col)
            att_style.add('TEXTCOLOR', (4,i), (4,i), col)
        except Exception:
            pass
    att_t.setStyle(att_style)
    story.append(att_t)
    story.append(Spacer(1, 12))

    # Marks
    from database import SUBJECT_CREDITS
    final_exam_type = f"{semester} Final Examinations"
    for et in ['Mid 1', 'Mid 2', 'Lab Internals', final_exam_type]:
        rows = marks_by_type.get(et, [])
        if not rows:
            continue
        story.append(Paragraph(et, section))
        mdata = [['Subject','Score','Grade','GP','Credits']]
        for r in rows:
            score   = r.get('score')
            gp      = r.get('grade_point') or 0.0
            grade   = r.get('grade', '-')
            credits = SUBJECT_CREDITS.get(r['subject'], 0.0)
            mdata.append([r['subject'],
                         str(score) if score is not None else 'Ab',
                         grade, str(gp), str(credits)])
        mt = Table(mdata, colWidths=[6*cm, 2.5*cm, 2.5*cm, 2*cm, 4*cm])
        mt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PURPLE),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('ALIGN',      (1,0), (-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(mt)
        story.append(Spacer(1, 8))

    # SGPA / CGPA
    story.append(HRFlowable(width='100%', thickness=1, color=BRAND_BLUE, spaceBefore=8))
    # Check if student has failed semesters
    from database import get_db_connection
    conn = get_db_connection()
    try:
        failed_row = conn.execute(
            'SELECT failed FROM sgpa_records WHERE roll_no=? AND semester=?',
            (student.get('roll_no'), semester)
        ).fetchone()
        has_failed_sem = conn.execute(
            'SELECT COUNT(*) FROM sgpa_records WHERE roll_no=? AND failed=1',
            (student.get('roll_no'),)
        ).fetchone()[0] > 0
    except Exception:
        failed_row = None
        has_failed_sem = False
    finally:
        conn.close()
        
    is_failed_sem = failed_row['failed'] if failed_row else False
    sgpa_str = "Pending" if is_failed_sem else (f"{sgpa:.2f}" if sgpa > 0 else "-")
    cgpa_str = "Pending" if has_failed_sem else (f"{cgpa:.2f}" if cgpa > 0 else "-")
    gpa_data = [['SGPA', sgpa_str, 'CGPA', cgpa_str]]
    gpa_t = Table(gpa_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
    gpa_t.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0,0), (-1,-1), 11),
        ('TEXTCOLOR', (0,0), (0,0), BRAND_GRAY),
        ('TEXTCOLOR', (1,0), (1,0), PURPLE),
        ('TEXTCOLOR', (2,0), (2,0), BRAND_GRAY),
        ('TEXTCOLOR', (3,0), (3,0), PURPLE),
        ('ALIGN',     (0,0), (-1,-1), 'CENTER'),
        ('PADDING',   (0,0), (-1,-1), 8),
    ]))
    story.append(gpa_t)
    story.append(Spacer(1, 16))
    story.append(Paragraph('Generated by VITS Academic ERP',
        ParagraphStyle('F', parent=styles['Normal'],
            fontSize=8, textColor=BRAND_GRAY, alignment=TA_CENTER)))

    doc.build(story)
    buf.seek(0)
    return buf
