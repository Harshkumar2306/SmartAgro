import re
with open('src/index.css', 'r') as f:
    css = f.read()
# Add newlines after } and { for readability
css = css.replace('{', ' {\n  ').replace('}', '\n}\n').replace(';', ';\n  ')
with open('src/index.css', 'w') as f:
    f.write(css)
