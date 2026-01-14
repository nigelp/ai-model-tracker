# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Build, Lint, Test Commands

**Build EXE:**
```bash
pyinstaller web_dashboard.spec --clean
```
Result: `dist/web_dashboard.exe` (includes auto-launch browser)

**Run directly:**
```bash
python web_dashboard.py
python model_scraper.py
```

**Installation:**
```bash
pip install -r requirements.txt
# or
install.bat  # Windows one-click installer
```

**Testing:** No test framework present. Manual testing required:
1. Run `python web_dashboard.py` and verify localhost:5000 loads
2. Run `python model_scraper.py` and check database is populated
3. Verify GGUF parsing with gguf-parser.exe in `tools/` folder

## Code Style Guidelines

### Import Order
Standard library → Third-party → Local modules:
```python
import os
import sys
from datetime import datetime
import sqlite3
import requests
from pathlib import Path
from gguf_parser import parse_gguf_from_hf
```

### Naming Conventions
- **Variables/Functions:** `snake_case` (e.g., `get_db_connection`, `model_dict`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONFIG`, `MAX_RETRIES`)
- **Classes:** `PascalCase` (rare in this codebase)
- **Private functions:** Leading underscore (e.g., `_migrate_gguf_columns`, `_run_parser`)

### Type Hints
Use type hints for function signatures:
```python
def parse_gguf_from_hf(repo: str, filename: str, retries: int = MAX_RETRIES) -> dict | None:
```

### Error Handling
1. **Optional dependencies:** Try/except ImportError with warning
```python
try:
    from gguf_parser import parse_gguf_from_hf
    GGUF_PARSER_AVAILABLE = True
except ImportError:
    GGUF_PARSER_AVAILABLE = False
    print("Warning: gguf_parser not available...")
```

2. **API calls:** Try/except with timeout and logging
```python
try:
    response = requests.get(url, timeout=30, headers={})
    if response.status_code == 200:
        data = response.json()
except Exception as e:
    print(f"Error fetching: {e}")
```

3. **Database operations:** Try/except specific exceptions (IntegrityError)
```python
try:
    cursor.execute(...)
except sqlite3.IntegrityError:
    pass  # Handle duplicates
except Exception as e:
    print(f"Error: {e}")
```

### Database Operations
- Use parameterized queries (never f-strings in SQL)
- `ON CONFLICT(url) DO UPDATE` for upserts
- Always close connections (`conn.close()`)
- Index frequently queried fields (source, category, release_date, is_gguf)
- Migrations with `ALTER TABLE` if column not exists

### File Paths
Always use `pathlib.Path` for cross-platform compatibility:
```python
from pathlib import Path
DB_PATH = Path(__file__).parent / "data" / "models.db"
```

### PyInstaller Bundling
Handle both development and EXE environments:
```python
if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent
```

### Configuration
Merge defaults with user config:
```python
return {**DEFAULT_CONFIG, **json.load(f)}
```

### GGUF Parser Integration
- Parser at `tools/gguf-parser.exe` is OPTIONAL
- Graceful fallback if missing (no crash)
- Wrapper handles retries with exponential backoff
- Prefer Q4_K_M quantization files

### Scraping Strategy
- Three-phase HuggingFace: popular by likes, recent by modified, GGUF-specific
- ModelScope uses inference API, not models API
- Size estimation: actual file sizes OR name patterns (0.5b, 1b, 7b, etc.)
- Chinese detection: qwen, deepseek, yi-, baichuan, chatglm, internlm keywords

### Web Dashboard
- Single-file Flask app with embedded HTML (no separate templates)
- Auto-refresh every 5 minutes via setInterval
- GGUF detection uses database field AND name fallback
- Stats API at `/api/stats`, models at `/api/models`, refresh at `/api/refresh`

### File Structure
- `data/` - SQLite database and reports
- `tools/` - External binaries (gguf-parser.exe)
- `venv/` - Virtual environment (created by install.bat)
- `dist/` - Compiled executables
