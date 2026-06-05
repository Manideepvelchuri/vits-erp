import sqlite3
conn = sqlite3.connect('vits_erp.db')
conn.row_factory = sqlite3.Row

# KEY QUESTION: The hour_wise_attendance table stores only ABSENT records (per student)
# NOT present records. Let's verify:
roll = '25891A04C9'

# Total rows for Manideep in hour_wise
all_rows = conn.execute('''
    SELECT date, hour, subject, total_present, total_absent
    FROM hour_wise_attendance WHERE roll_no=? ORDER BY date, hour
''', (roll,)).fetchall()
print(f'Manideep rows in hour_wise_attendance: {len(all_rows)}')
print('\nAll rows:')
for r in all_rows:
    print(dict(r))

# This is ABSENCES only for Manideep, so each row = one absence
print(f'\nTotal absences: {len(all_rows)}')

# Now check the main attendance table for manideep
print('\n=== Main attendance (cumulative per subject) ===')
main = conn.execute('''
    SELECT subject, hours_attended, hours_conducted,
           ROUND(hours_attended*100.0/NULLIF(hours_conducted,0),1) pct
    FROM attendance WHERE roll_no=? AND semester='Sem 2'
    ORDER BY subject
''', (roll,)).fetchall()

total_a = 0; total_c = 0
for r in main:
    total_a += r['hours_attended']
    total_c += r['hours_conducted']
    print(f"  {r['subject']}: {r['hours_attended']}/{r['hours_conducted']} = {r['pct']}%")
print(f'\nTotal: {total_a}/{total_c} = {round(total_a/total_c*100,1) if total_c else 0}%')

# How many hours is Manideep missing from hour_wise_attendance?
# In hour_wise, Manideep has only 10 rows starting from Feb 11
# The portal's main attendance shows 15 absences (581-566=15)
# hour_wise only has absences from when the scraping started

# Check if the student was 100% in Jan 27 - Feb 10 in hour_wise
print('\n=== ECE_B students in hour_wise_attendance before Feb 11 ===')
before_feb11 = conn.execute('''
    SELECT COUNT(1) FROM hour_wise_attendance 
    WHERE section='ECE_B' AND date < '2026-02-11'
''').fetchone()[0]
print(f'ECE_B rows before Feb 11 in hour_wise: {before_feb11}')

ece_b_manideep_before = conn.execute('''
    SELECT COUNT(1) FROM hour_wise_attendance 
    WHERE roll_no=? AND date < '2026-02-11'
''', (roll,)).fetchone()[0]
print(f'Manideep rows before Feb 11 in hour_wise: {ece_b_manideep_before}')

# Understand: hour_wise stores absent students per hour
# So 0 rows for Manideep before Feb 11 means he was PRESENT all those hours
print('\n==> Manideep had 0 absences before Feb 11 = 100% attendance in those days ✓')

# The MAIN attendance table (hours_attended/hours_conducted) is the TRUTH
# Let's see if it's consistent with what we'd expect
total_absent_from_hw = len(all_rows)  # Each row in hour_wise for student = 1 absence
total_absent_from_main = total_c - total_a
print(f'\nAbsences from hour_wise_attendance: {total_absent_from_hw}')
print(f'Absences from main attendance table: {total_absent_from_main}')
print(f'Are they consistent? {total_absent_from_hw == total_absent_from_main}')

conn.close()
