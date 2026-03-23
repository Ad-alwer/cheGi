

TEMPLATES = {
    "Python": """
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
ENV/
.env
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
""",
    "Node": """
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.env
dist/
build/
""",
    "Go": """
*.exe
*.exe~
*.dll
*.so
*.dylib
bin/
pkg/
""",
    "Rust": """
/target/
**/*.rs.bk
Cargo.lock
""",
    "C++": """
*.o
*.obj
*.exe
*.out
*.app
*.a
*.lib
*.so
*.dylib
build/
bin/
.vscode/
.idea/
""",
    "Ruby": """
*.gem
.bundle/
vendor/bundle/
log/
tmp/
db/*.sqlite3
coverage/
""",
    "C#": """
bin/
obj/
*.user
*.suo
*.sln.docstates
packages/
""",
    "Global (OS/IDE)": """
.DS_Store
Thumbs.db
.vscode/
.idea/
*.swp
*.log
"""
}
