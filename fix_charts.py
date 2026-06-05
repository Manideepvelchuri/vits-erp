with open('streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()
new = content.replace('"displayModeBar": False', '"displayModeBar": True')
print('Fixed:', content.count('"displayModeBar": False'), 'occurrences')
with open('streamlit_app.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(new)
print('Done')
