import os
import re

def find_bad_markdown(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find all st.markdown calls
                # This is a bit tricky with multiline calls, so we'll look for st.markdown( then look ahead for unsafe_allow_html=True
                calls = re.finditer(r'st\.markdown\s*\(', content)
                for call in calls:
                    start = call.start()
                    # Find matching closing parenthesis
                    depth = 1
                    end = start + len(call.group())
                    while depth > 0 and end < len(content):
                        if content[end] == '(':
                            depth += 1
                        elif content[end] == ')':
                            depth -= 1
                        end += 1
                    
                    full_call = content[start:end]
                    if 'unsafe_allow_html=True' not in full_call:
                        # Check if it actually contains HTML
                        if '<' in full_call and '>' in full_call:
                            line_no = content.count('\n', 0, start) + 1
                            print(f"{path}:{line_no}: Potential missing unsafe_allow_html=True in:\n{full_call}\n")

find_bad_markdown('.')
