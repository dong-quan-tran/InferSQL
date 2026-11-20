set -eu
npm --prefix frontend ci --include=dev
VITE_API_BASE_URL=/api npm --prefix frontend run build
python -c 'import subprocess, sys, tomllib; deps = tomllib.load(open("backend/pyproject.toml", "rb"))["project"]["dependencies"]; subprocess.check_call([sys.executable, "-m", "pip", "install", *deps, "python-multipart", "google-genai"])'
