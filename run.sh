#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# venv layout differs: bin/ on macOS/Linux, Scripts/ on Windows (Git Bash)
venv_python() {
    if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo .venv/Scripts/python; fi
}

if [ ! -f .venv/installed ]; then
    echo "First-time setup, this takes a minute or two..."
    # Test each candidate actually runs: on Windows "python3" can be a stub that opens the Microsoft Store
    PYTHON=""
    for candidate in python3 python; do
        if "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
            PYTHON=$candidate
            break
        fi
    done
    if [ -z "$PYTHON" ]; then
        echo "Python 3.10+ wasn't found. Install it from https://www.python.org/downloads/ and run this again."
        exit 1
    fi
    "$PYTHON" -m venv .venv
    "$(venv_python)" -m pip install --quiet -r requirements.txt
    "$(venv_python)" -m playwright install chromium
    touch .venv/installed
fi

exec "$(venv_python)" auto_enroll.py
