"""
GGUF Parser Wrapper
Calls gguf-parser-go CLI to extract metadata from GGUF files on HuggingFace and ModelScope.
"""

import subprocess
import json
import time
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the gguf-parser executable
# Handle both development and PyInstaller frozen (EXE) environments
if getattr(sys, 'frozen', False):
    # Running as compiled EXE
    base_path = Path(sys._MEIPASS)
else:
    # Running as Python script
    base_path = Path(__file__).parent

PARSER_PATH = base_path / "tools" / "gguf-parser.exe"

# Configuration
PARSER_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds, doubles each retry


def parse_gguf_from_hf(repo: str, filename: str, retries: int = MAX_RETRIES) -> dict | None:
    """
    Parse GGUF metadata from a HuggingFace repository.

    Args:
        repo: HuggingFace repo in format "org/model" (e.g., "TheBloke/Llama-2-7B-GGUF")
        filename: GGUF filename (e.g., "llama-2-7b.Q4_K_M.gguf")
        retries: Number of retry attempts on failure

    Returns:
        Dict with parsed metadata or None if parsing fails
    """
    return _run_parser_with_retry(["--hf-repo", repo, "--hf-file", filename], retries)


def parse_gguf_from_ms(repo: str, filename: str, retries: int = MAX_RETRIES) -> dict | None:
    """
    Parse GGUF metadata from a ModelScope repository.

    Args:
        repo: ModelScope repo in format "org/model" (e.g., "Xorbits/Qwen-7B-Chat-GGUF")
        filename: GGUF filename - CASE SENSITIVE! (e.g., "Qwen-7B-Chat.Q4_K_M.gguf")
        retries: Number of retry attempts on failure

    Returns:
        Dict with parsed metadata or None if parsing fails
    """
    return _run_parser_with_retry(["--ms-repo", repo, "--ms-file", filename], retries)


def parse_gguf_local(filepath: str) -> dict | None:
    """
    Parse GGUF metadata from a local file.

    Args:
        filepath: Path to local GGUF file

    Returns:
        Dict with parsed metadata or None if parsing fails
    """
    return _run_parser_with_retry(["--path", filepath], retries=1)  # No retry for local files


def _run_parser_with_retry(args: list, retries: int = MAX_RETRIES) -> dict | None:
    """
    Run the parser with retry logic for transient failures.

    Args:
        args: CLI arguments
        retries: Number of retry attempts

    Returns:
        Dict with parsed metadata or None if all attempts fail
    """
    delay = RETRY_DELAY

    for attempt in range(retries):
        result = _run_parser(args)

        # Success - return result
        if result is not None and "_error" not in result:
            return result

        # Non-retryable error (404, etc.) - stop immediately
        if result is not None and result.get("_error") == "not_found":
            return None

        # Retryable failure
        if attempt < retries - 1:
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff

    return None


def _run_parser(args: list) -> dict | None:
    """
    Run the gguf-parser CLI and return parsed JSON (single attempt).

    Args:
        args: List of CLI arguments

    Returns:
        Dict with parsed metadata or None if parsing fails
    """
    if not PARSER_PATH.exists():
        logger.error(f"gguf-parser not found at {PARSER_PATH}")
        return None

    cmd = [str(PARSER_PATH)] + args + ["--json"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PARSER_TIMEOUT
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            # Don't retry on 404 (file not found)
            if "404" in stderr:
                logger.error(f"File not found (404): {stderr}")
                return {"_error": "not_found", "_message": stderr}
            logger.warning(f"Parser error: {stderr}")
            return None

        raw_data = json.loads(result.stdout)
        return _extract_metadata(raw_data)

    except subprocess.TimeoutExpired:
        logger.warning(f"Parser timeout after {PARSER_TIMEOUT}s")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"Parser exception: {e}")
        return None


def _extract_metadata(raw: dict) -> dict:
    """
    Extract relevant fields from raw parser output.

    Args:
        raw: Raw JSON output from gguf-parser

    Returns:
        Cleaned dict with key metadata fields
    """
    metadata = raw.get("metadata", {})
    architecture = raw.get("architecture", {})
    estimate = raw.get("estimate", {})

    # Calculate VRAM in GB from bytes
    vram_bytes = 0
    if estimate.get("items"):
        vrams = estimate["items"][0].get("vrams", [])
        if vrams:
            vram_bytes = vrams[0].get("nonuma", 0)
    vram_gb = round(vram_bytes / (1024 ** 3), 2) if vram_bytes else None

    # Calculate RAM in GB
    ram_bytes = 0
    if estimate.get("items"):
        ram_info = estimate["items"][0].get("ram", {})
        ram_bytes = ram_info.get("nonuma", 0)
    ram_gb = round(ram_bytes / (1024 ** 3), 2) if ram_bytes else None

    # Format parameter count (e.g., 6738415616 -> "6.7B")
    params = metadata.get("parameters", 0)
    if params >= 1_000_000_000:
        params_str = f"{params / 1_000_000_000:.1f}B"
    elif params >= 1_000_000:
        params_str = f"{params / 1_000_000:.0f}M"
    else:
        params_str = str(params)

    return {
        "architecture": metadata.get("architecture") or architecture.get("architecture"),
        "quantization": metadata.get("fileTypeDetail"),
        "parameters": metadata.get("parameters"),
        "parameters_str": params_str,
        "context_length": architecture.get("maximumContextLength"),
        "embedding_length": architecture.get("embeddingLength"),
        "file_size_bytes": metadata.get("fileSize"),
        "file_size_gb": round(metadata.get("fileSize", 0) / (1024 ** 3), 2) if metadata.get("fileSize") else None,
        "bits_per_weight": round(metadata.get("bitsPerWeight", 0), 2) if metadata.get("bitsPerWeight") else None,
        "vram_required_gb": vram_gb,
        "ram_required_gb": ram_gb,
        "model_name": metadata.get("name"),
        "flash_attention": estimate.get("flashAttention", False),
        "fully_offloadable": estimate.get("items", [{}])[0].get("fullOffloaded", False)
    }


# Test function
if __name__ == "__main__":
    print("Testing HuggingFace parsing...")
    hf_result = parse_gguf_from_hf("TheBloke/Llama-2-7B-GGUF", "llama-2-7b.Q4_K_M.gguf")
    if hf_result:
        print("HuggingFace SUCCESS:")
        print(json.dumps(hf_result, indent=2))
    else:
        print("HuggingFace FAILED")

    print("\nTesting ModelScope parsing...")
    ms_result = parse_gguf_from_ms("Xorbits/Qwen-7B-Chat-GGUF", "Qwen-7B-Chat.Q4_K_M.gguf")
    if ms_result:
        print("ModelScope SUCCESS:")
        print(json.dumps(ms_result, indent=2))
    else:
        print("ModelScope FAILED")
