"""
AI Model Tracker - Model Scraper
Scrapes models from Hugging Face, ModelScope, and other sources.
"""

import sqlite3
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Install with: pip install requests")
    exit(1)

# Import GGUF parser (optional - graceful fallback if not available)
try:
    from gguf_parser import parse_gguf_from_hf, parse_gguf_from_ms
    GGUF_PARSER_AVAILABLE = True
except ImportError:
    GGUF_PARSER_AVAILABLE = False
    print("Warning: gguf_parser not available. GGUF metadata will not be extracted.")

# Configuration
CONFIG_PATH = Path(__file__).parent / "config.json"
DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "models.db"

# Default configuration
DEFAULT_CONFIG = {
    "scrape_interval_hours": 6,
    "max_models_per_source": 100,
    "sources": {
        "huggingface": True,
        "modelscope": True
    },
    "vram_limit_gb": 24,
    "include_chinese": True
}

def load_config():
    """Load configuration from config.json or use defaults."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG

def ensure_data_dir():
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(exist_ok=True)

def init_database():
    """Initialize SQLite database with the required schema."""
    ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            description TEXT,
            category TEXT DEFAULT 'text',
            size_gb REAL,
            is_chinese INTEGER DEFAULT 0,
            release_date TEXT,
            downloads INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            tags TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_gguf INTEGER DEFAULT 0,
            quantization TEXT,
            gguf_architecture TEXT,
            context_length INTEGER,
            parameter_count INTEGER,
            vram_required_gb REAL,
            bits_per_weight REAL,
            gguf_file TEXT
        )
    ''')

    # Migration: Add GGUF columns to existing databases (must run before indexes)
    _migrate_gguf_columns(cursor)

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_models_source ON models(source)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_models_category ON models(category)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_models_release_date ON models(release_date)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_models_is_gguf ON models(is_gguf)
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def _migrate_gguf_columns(cursor):
    """Add GGUF columns to existing databases if they don't exist."""
    # Get existing columns
    cursor.execute("PRAGMA table_info(models)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # GGUF columns to add
    gguf_columns = [
        ("is_gguf", "INTEGER DEFAULT 0"),
        ("quantization", "TEXT"),
        ("gguf_architecture", "TEXT"),
        ("context_length", "INTEGER"),
        ("parameter_count", "INTEGER"),
        ("vram_required_gb", "REAL"),
        ("bits_per_weight", "REAL"),
        ("gguf_file", "TEXT")
    ]

    for col_name, col_type in gguf_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE models ADD COLUMN {col_name} {col_type}")
                print(f"  Added column: {col_name}")
            except sqlite3.OperationalError:
                pass  # Column already exists

def estimate_model_size(model_data):
    """Estimate model size in GB based on available information."""
    siblings = model_data.get('siblings', [])
    total_bytes = 0

    for file in siblings:
        size = file.get('size', 0)
        if size:
            total_bytes += size

    if total_bytes > 0:
        return round(total_bytes / (1024 ** 3), 1)

    name = model_data.get('id', '').lower()

    size_indicators = {
        '0.5b': 1, '1b': 2, '1.5b': 3, '2b': 4, '3b': 6,
        '4b': 8, '7b': 14, '8b': 16, '13b': 26, '14b': 28,
        '32b': 64, '34b': 68, '70b': 140, '72b': 144
    }

    for indicator, size in size_indicators.items():
        if indicator in name:
            return size

    return None

def detect_category(model_data):
    """Detect model category from tags and pipeline."""
    tags = model_data.get('tags', [])
    pipeline = model_data.get('pipeline_tag', '')

    if any(t in tags for t in ['diffusers', 'stable-diffusion', 'image-generation', 'text-to-image']):
        return 'image'
    if 'text-to-image' in pipeline or 'image-to-image' in pipeline:
        return 'image'

    if any(t in tags for t in ['code', 'coding', 'coder', 'code-generation']):
        return 'coding'
    if 'code' in model_data.get('id', '').lower():
        return 'coding'

    if any(t in tags for t in ['vision', 'multimodal', 'image-text-to-text', 'visual-question-answering']):
        return 'multimodal'
    if 'vision' in model_data.get('id', '').lower():
        return 'multimodal'

    return 'text'

def is_chinese_model(model_data):
    """Detect if model is Chinese-focused."""
    model_id = model_data.get('id', '').lower()
    tags = model_data.get('tags', [])

    chinese_indicators = [
        'qwen', 'baichuan', 'chatglm', 'yi-', 'deepseek',
        'chinese', 'minicpm', 'internlm', 'moss', 'tigerbot',
        'aquila', 'skywork', 'xverse', 'orion'
    ]

    for indicator in chinese_indicators:
        if indicator in model_id:
            return True

    if 'zh' in tags or 'chinese' in tags:
        return True

    return False


# ============================================
# GGUF Detection and Metadata Functions
# ============================================

def is_gguf_model(model_data):
    """Detect if model is a GGUF model based on name, tags, or files."""
    model_id = model_data.get('id', '').lower()
    tags = model_data.get('tags', [])

    # Check name
    if 'gguf' in model_id:
        return True

    # Check tags
    if 'gguf' in [t.lower() for t in tags]:
        return True

    # Check siblings (files) for .gguf extension
    siblings = model_data.get('siblings', [])
    for file in siblings:
        filename = file.get('rfilename', '').lower()
        if filename.endswith('.gguf'):
            return True

    return False


def get_gguf_files_from_hf(repo_id):
    """Get list of .gguf files from a HuggingFace repo."""
    try:
        response = requests.get(
            f"https://huggingface.co/api/models/{repo_id}",
            params={"expand": "siblings"},
            timeout=15,
            headers={"Accept": "application/json", "User-Agent": "AI-Model-Tracker/1.0"}
        )
        if response.status_code == 200:
            data = response.json()
            siblings = data.get('siblings', [])
            gguf_files = [
                f.get('rfilename') for f in siblings
                if f.get('rfilename', '').lower().endswith('.gguf')
            ]
            return gguf_files
    except Exception as e:
        print(f"  Error getting GGUF files from HF {repo_id}: {e}")
    return []


def get_gguf_files_from_ms(repo_id):
    """Get list of .gguf files from a ModelScope repo."""
    try:
        # ModelScope files API
        response = requests.get(
            f"https://modelscope.cn/api/v1/models/{repo_id}/repo/files",
            timeout=15,
            headers={"Accept": "application/json", "User-Agent": "AI-Model-Tracker/1.0"}
        )
        if response.status_code == 200:
            data = response.json()
            files = data.get('Data', {}).get('Files', [])
            gguf_files = [
                f.get('Name') for f in files
                if f.get('Name', '').lower().endswith('.gguf')
            ]
            return gguf_files
    except Exception as e:
        print(f"  Error getting GGUF files from MS {repo_id}: {e}")
    return []


def pick_representative_gguf_file(gguf_files):
    """Pick a representative GGUF file for metadata extraction.

    Prefers Q4_K_M or similar medium quantization for speed.
    """
    if not gguf_files:
        return None

    # Preference order: Q4_K_M > Q4_K_S > Q5_K_M > Q5_K_S > first file
    preferences = ['q4_k_m', 'q4_k_s', 'q5_k_m', 'q5_k_s', 'q4_0', 'q5_0']

    for pref in preferences:
        for f in gguf_files:
            if pref in f.lower():
                return f

    # Return first file if no preference match
    return gguf_files[0]


def enrich_model_with_gguf_metadata(model_dict, source='huggingface'):
    """Enrich a model dict with GGUF metadata if applicable.

    Args:
        model_dict: The model dictionary to enrich
        source: 'huggingface' or 'modelscope'

    Returns:
        Updated model dict with GGUF fields
    """
    if not GGUF_PARSER_AVAILABLE:
        return model_dict

    # Extract repo_id from URL
    url = model_dict.get('url', '')
    if source == 'huggingface':
        repo_id = url.replace('https://huggingface.co/', '')
        gguf_files = get_gguf_files_from_hf(repo_id)
        parse_fn = parse_gguf_from_hf
    else:  # modelscope
        repo_id = url.replace('https://modelscope.cn/models/', '').rstrip('/')
        gguf_files = get_gguf_files_from_ms(repo_id)
        parse_fn = parse_gguf_from_ms

    if not gguf_files:
        return model_dict

    # Pick representative file and parse
    gguf_file = pick_representative_gguf_file(gguf_files)
    if not gguf_file:
        return model_dict

    print(f"    Parsing GGUF metadata: {repo_id}/{gguf_file}")
    metadata = parse_fn(repo_id, gguf_file)

    if metadata:
        model_dict['is_gguf'] = True
        model_dict['quantization'] = metadata.get('quantization')
        model_dict['gguf_architecture'] = metadata.get('architecture')
        model_dict['context_length'] = metadata.get('context_length')
        model_dict['parameter_count'] = metadata.get('parameters')
        model_dict['vram_required_gb'] = metadata.get('vram_required_gb')
        model_dict['bits_per_weight'] = metadata.get('bits_per_weight')
        model_dict['gguf_file'] = gguf_file
    else:
        # Mark as GGUF even if parsing failed
        model_dict['is_gguf'] = True
        model_dict['gguf_file'] = gguf_file

    return model_dict


def scrape_huggingface(config, limit=50):
    """Scrape models from Hugging Face (by likes and by last modified)."""
    print("Scraping Hugging Face...")
    models = []
    seen_urls = set()

    # First, get popular models by likes
    try:
        response = requests.get(
            "https://huggingface.co/api/models",
            params={
                "sort": "likes",
                "direction": "-1",
                "limit": limit // 2
            },
            timeout=30,
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-Model-Tracker/1.0"
            }
        )

        if response.status_code == 200:
            data = response.json()
            for model in data:
                model_id = model.get('id', '')
                if not model_id:
                    continue

                url = f"https://huggingface.co/{model_id}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                size_gb = estimate_model_size(model)
                if size_gb and size_gb > config.get('vram_limit_gb', 24) * 2:
                    continue

                models.append({
                    'name': model_id.split('/')[-1],
                    'source': 'huggingface',
                    'url': url,
                    'description': model.get('description', '')[:500] if model.get('description') else None,
                    'category': detect_category(model),
                    'size_gb': size_gb,
                    'is_chinese': is_chinese_model(model),
                    'release_date': model.get('lastModified', datetime.now().isoformat())[:19].replace('T', ' '),
                    'downloads': model.get('downloads', 0),
                    'likes': model.get('likes', 0),
                    'tags': json.dumps(model.get('tags', [])[:10])
                })

            print(f"  Found {len(models)} popular models")

    except Exception as e:
        print(f"  Error fetching popular models: {e}")

    # Second, get recently modified models
    try:
        response = requests.get(
            "https://huggingface.co/api/models",
            params={
                "sort": "lastModified",
                "direction": "-1",
                "limit": limit // 2
            },
            timeout=30,
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-Model-Tracker/1.0"
            }
        )

        if response.status_code == 200:
            data = response.json()
            recent_count = 0

            for model in data:
                model_id = model.get('id', '')
                if not model_id:
                    continue

                url = f"https://huggingface.co/{model_id}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                size_gb = estimate_model_size(model)
                if size_gb and size_gb > config.get('vram_limit_gb', 24) * 2:
                    continue

                models.append({
                    'name': model_id.split('/')[-1],
                    'source': 'huggingface',
                    'url': url,
                    'description': model.get('description', '')[:500] if model.get('description') else None,
                    'category': detect_category(model),
                    'size_gb': size_gb,
                    'is_chinese': is_chinese_model(model),
                    'release_date': model.get('lastModified', datetime.now().isoformat())[:19].replace('T', ' '),
                    'downloads': model.get('downloads', 0),
                    'likes': model.get('likes', 0),
                    'tags': json.dumps(model.get('tags', [])[:10])
                })
                recent_count += 1

            print(f"  Found {recent_count} recently modified models")

    except Exception as e:
        print(f"  Error fetching recent models: {e}")

    # Third, get GGUF models specifically (for local deployment)
    try:
        response = requests.get(
            "https://huggingface.co/api/models",
            params={
                "search": "gguf",
                "sort": "likes",
                "direction": "-1",
                "limit": limit // 2
            },
            timeout=30,
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-Model-Tracker/1.0"
            }
        )

        if response.status_code == 200:
            data = response.json()
            gguf_count = 0

            for model in data:
                model_id = model.get('id', '')
                if not model_id:
                    continue

                url = f"https://huggingface.co/{model_id}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                size_gb = estimate_model_size(model)
                if size_gb and size_gb > config.get('vram_limit_gb', 24) * 2:
                    continue

                model_dict = {
                    'name': model_id.split('/')[-1],
                    'source': 'huggingface',
                    'url': url,
                    'description': model.get('description', '')[:500] if model.get('description') else None,
                    'category': detect_category(model),
                    'size_gb': size_gb,
                    'is_chinese': is_chinese_model(model),
                    'release_date': model.get('lastModified', datetime.now().isoformat())[:19].replace('T', ' '),
                    'downloads': model.get('downloads', 0),
                    'likes': model.get('likes', 0),
                    'tags': json.dumps(model.get('tags', [])[:10])
                }

                # Enrich GGUF models with metadata
                model_dict = enrich_model_with_gguf_metadata(model_dict, source='huggingface')
                models.append(model_dict)
                gguf_count += 1

            print(f"  Found {gguf_count} GGUF models (with metadata enrichment)")

    except Exception as e:
        print(f"  Error fetching GGUF models: {e}")

    print(f"  Total: {len(models)} models from Hugging Face")
    return models

def scrape_modelscope(config, limit=100):
    """Scrape models from ModelScope (Chinese models)."""
    print("Scraping ModelScope...")
    models = []

    try:
        # Use the inference API which lists available models
        response = requests.get(
            "https://api-inference.modelscope.cn/v1/models",
            timeout=15,
            headers={
                "Accept": "application/json",
                "User-Agent": "AI-Model-Tracker/1.0"
            }
        )

        if response.status_code == 200:
            data = response.json()
            model_list = data.get('data', [])

            for model in model_list[:limit]:
                model_id = model.get('id', '')

                if not model_id:
                    continue

                # Parse org/name from id like "deepseek-ai/DeepSeek-R1-0528"
                parts = model_id.split('/')
                if len(parts) >= 2:
                    org = parts[0]
                    name = parts[-1]
                else:
                    org = ''
                    name = model_id

                # Convert Unix timestamp to datetime string
                created_ts = model.get('created', 0)
                if created_ts:
                    release_date = datetime.fromtimestamp(created_ts).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    release_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Detect category from model name
                name_lower = name.lower()
                if any(x in name_lower for x in ['coder', 'code', 'starcoder']):
                    category = 'coding'
                elif any(x in name_lower for x in ['vision', 'vl', 'image', 'diffusion']):
                    category = 'multimodal'
                else:
                    category = 'text'

                # Detect if Chinese model
                is_chinese = any(x in name_lower for x in [
                    'qwen', 'deepseek', 'yi-', 'glm', 'baichuan', 'internlm',
                    'minicpm', 'chinese', 'llama-chinese'
                ]) or any(x in org.lower() for x in ['qwen', 'deepseek', 'thudm', 'baichuan'])

                # Detect if GGUF model
                is_gguf_model_flag = 'gguf' in name_lower

                model_dict = {
                    'name': name,
                    'source': 'modelscope',
                    'url': f"https://modelscope.cn/models/{model_id}",
                    'description': f"ModelScope model: {model_id}",
                    'category': category,
                    'size_gb': None,
                    'is_chinese': is_chinese,
                    'release_date': release_date,
                    'downloads': 0,
                    'likes': 0,
                    'tags': json.dumps([org] if org else [])
                }

                # Enrich GGUF models with metadata
                if is_gguf_model_flag:
                    model_dict = enrich_model_with_gguf_metadata(model_dict, source='modelscope')

                models.append(model_dict)

            gguf_count = sum(1 for m in models if m.get('is_gguf'))
            print(f"  Found {len(models)} models from ModelScope ({gguf_count} GGUF)")
        else:
            print(f"  Error: HTTP {response.status_code}")

    except Exception as e:
        print(f"  Error scraping ModelScope: {e}")

    return models

def add_sample_models():
    """Add sample/popular models to ensure there's always data."""
    return [
        {
            'name': 'Llama-3.2-3B',
            'source': 'huggingface',
            'url': 'https://huggingface.co/meta-llama/Llama-3.2-3B',
            'description': 'Meta Llama 3.2 3B - Compact yet powerful language model optimized for efficiency',
            'category': 'text',
            'size_gb': 6,
            'is_chinese': False,
            'release_date': '2024-09-25 12:00:00',
            'downloads': 1000000,
            'likes': 5000,
            'tags': json.dumps(['llama', 'meta', 'text-generation'])
        },
        {
            'name': 'Qwen2.5-7B-Instruct',
            'source': 'huggingface',
            'url': 'https://huggingface.co/Qwen/Qwen2.5-7B-Instruct',
            'description': 'Qwen 2.5 7B Instruct - Alibaba latest multilingual model with excellent Chinese support',
            'category': 'text',
            'size_gb': 14,
            'is_chinese': True,
            'release_date': '2024-09-19 10:30:00',
            'downloads': 500000,
            'likes': 3000,
            'tags': json.dumps(['qwen', 'chinese', 'text-generation'])
        },
        {
            'name': 'DeepSeek-Coder-V2-Lite',
            'source': 'huggingface',
            'url': 'https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct',
            'description': 'DeepSeek Coder V2 Lite - Excellent code generation model from DeepSeek',
            'category': 'coding',
            'size_gb': 16,
            'is_chinese': True,
            'release_date': '2024-06-17 08:00:00',
            'downloads': 300000,
            'likes': 2000,
            'tags': json.dumps(['deepseek', 'code', 'coding'])
        },
        {
            'name': 'Stable-Diffusion-3-Medium',
            'source': 'huggingface',
            'url': 'https://huggingface.co/stabilityai/stable-diffusion-3-medium',
            'description': 'Stable Diffusion 3 Medium - High quality image generation with improved text rendering',
            'category': 'image',
            'size_gb': 4,
            'is_chinese': False,
            'release_date': '2024-06-12 14:00:00',
            'downloads': 800000,
            'likes': 4000,
            'tags': json.dumps(['stable-diffusion', 'image', 'diffusers'])
        },
        {
            'name': 'Mistral-7B-Instruct-v0.3',
            'source': 'huggingface',
            'url': 'https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3',
            'description': 'Mistral 7B Instruct v0.3 - Fast and efficient instruction-following model',
            'category': 'text',
            'size_gb': 14,
            'is_chinese': False,
            'release_date': '2024-05-22 16:00:00',
            'downloads': 2000000,
            'likes': 8000,
            'tags': json.dumps(['mistral', 'text-generation', 'instruct'])
        },
        {
            'name': 'Phi-3-mini-4k-instruct',
            'source': 'huggingface',
            'url': 'https://huggingface.co/microsoft/Phi-3-mini-4k-instruct',
            'description': 'Microsoft Phi-3 Mini - Compact 3.8B model with impressive performance',
            'category': 'text',
            'size_gb': 7,
            'is_chinese': False,
            'release_date': '2024-04-23 09:00:00',
            'downloads': 1500000,
            'likes': 6000,
            'tags': json.dumps(['phi', 'microsoft', 'text-generation'])
        },
        {
            'name': 'FLUX.1-schnell',
            'source': 'huggingface',
            'url': 'https://huggingface.co/black-forest-labs/FLUX.1-schnell',
            'description': 'FLUX.1 Schnell - Ultra-fast high quality image generation',
            'category': 'image',
            'size_gb': 12,
            'is_chinese': False,
            'release_date': '2024-08-01 11:00:00',
            'downloads': 600000,
            'likes': 3500,
            'tags': json.dumps(['flux', 'image', 'diffusers', 'text-to-image'])
        },
        {
            'name': 'Llama-3.2-11B-Vision',
            'source': 'huggingface',
            'url': 'https://huggingface.co/meta-llama/Llama-3.2-11B-Vision',
            'description': 'Meta Llama 3.2 Vision - Multimodal model for image understanding',
            'category': 'multimodal',
            'size_gb': 22,
            'is_chinese': False,
            'release_date': '2024-09-25 13:00:00',
            'downloads': 400000,
            'likes': 2500,
            'tags': json.dumps(['llama', 'vision', 'multimodal'])
        },
        {
            'name': 'Yi-1.5-9B-Chat',
            'source': 'huggingface',
            'url': 'https://huggingface.co/01-ai/Yi-1.5-9B-Chat',
            'description': 'Yi 1.5 9B Chat - Excellent bilingual (Chinese/English) chat model',
            'category': 'text',
            'size_gb': 18,
            'is_chinese': True,
            'release_date': '2024-05-13 07:00:00',
            'downloads': 250000,
            'likes': 1500,
            'tags': json.dumps(['yi', 'chinese', 'chat'])
        },
        {
            'name': 'MiniCPM-V-2_6',
            'source': 'huggingface',
            'url': 'https://huggingface.co/openbmb/MiniCPM-V-2_6',
            'description': 'MiniCPM-V 2.6 - Tiny but capable vision-language model',
            'category': 'multimodal',
            'size_gb': 5,
            'is_chinese': True,
            'release_date': '2024-08-06 15:00:00',
            'downloads': 150000,
            'likes': 1000,
            'tags': json.dumps(['minicpm', 'vision', 'chinese', 'multimodal'])
        }
    ]

def save_models_to_db(models):
    """Save scraped models to the database."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    saved_count = 0
    updated_count = 0

    for model in models:
        try:
            cursor.execute('''
                INSERT INTO models (name, source, url, description, category, size_gb,
                                   is_chinese, release_date, downloads, likes, tags, updated_at,
                                   is_gguf, quantization, gguf_architecture, context_length,
                                   parameter_count, vram_required_gb, bits_per_weight, gguf_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    downloads = excluded.downloads,
                    likes = excluded.likes,
                    updated_at = excluded.updated_at,
                    is_gguf = excluded.is_gguf,
                    quantization = excluded.quantization,
                    gguf_architecture = excluded.gguf_architecture,
                    context_length = excluded.context_length,
                    parameter_count = excluded.parameter_count,
                    vram_required_gb = excluded.vram_required_gb,
                    bits_per_weight = excluded.bits_per_weight,
                    gguf_file = excluded.gguf_file
            ''', (
                model['name'],
                model['source'],
                model['url'],
                model['description'],
                model['category'],
                model['size_gb'],
                1 if model['is_chinese'] else 0,
                model['release_date'],
                model['downloads'],
                model['likes'],
                model['tags'],
                datetime.now().isoformat(),
                1 if model.get('is_gguf') else 0,
                model.get('quantization'),
                model.get('gguf_architecture'),
                model.get('context_length'),
                model.get('parameter_count'),
                model.get('vram_required_gb'),
                model.get('bits_per_weight'),
                model.get('gguf_file')
            ))

            if cursor.rowcount > 0:
                saved_count += 1
            else:
                updated_count += 1

        except sqlite3.IntegrityError:
            updated_count += 1
        except Exception as e:
            print(f"  Error saving {model['name']}: {e}")

    conn.commit()
    conn.close()

    return saved_count, updated_count

def run_scraper():
    """Main scraper function."""
    print("\n" + "=" * 50)
    print("AI Model Tracker - Model Scraper")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    config = load_config()
    init_database()

    all_models = []

    if config.get('sources', {}).get('huggingface', True):
        hf_models = scrape_huggingface(config, limit=config.get('max_models_per_source', 100))
        all_models.extend(hf_models)

    if config.get('sources', {}).get('modelscope', True):
        ms_models = scrape_modelscope(config, limit=100)
        all_models.extend(ms_models)

    if len(all_models) < 5:
        print("\nAdding curated sample models...")
        sample_models = add_sample_models()
        all_models.extend(sample_models)

    print(f"\nSaving {len(all_models)} models to database...")
    saved, updated = save_models_to_db(all_models)

    print(f"\nScraping complete!")
    print(f"  New models: {saved}")
    print(f"  Updated: {updated}")
    print(f"  Total processed: {len(all_models)}")
    print(f"\nDatabase: {DB_PATH}")
    print("=" * 50 + "\n")

    return all_models

def main():
    """Main entry point for the scraper."""
    return run_scraper()

if __name__ == "__main__":
    main()
