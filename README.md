# 🤖 AI Model Tracker

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/badge/release-v1.0.0-orange.svg)](https://github.com/nigelp/ai-model-tracker/releases)

![aitrackerscreen](https://github.com/user-attachments/assets/4a3c6ff9-6763-4efe-8bbf-94eaa2e0133b)

**AI Model Tracker** is a one-click desktop application that automatically discovers and organizes AI models from across the internet. It solves the problem of "model sprawl" where you have models scattered everywhere without knowing what you have, what's new, or what will work on your hardware.

## ✨ Key Features

- **Automatic Discovery** - Scrapes Hugging Face, ModelScope (Chinese models), and more for new AI models
- **Hardware-Aware** - Focuses on models that work with ≤24GB VRAM (most consumer GPUs)
- **Beautiful Dashboard** - Web interface to browse, filter, and search models
- **Chinese Model Tracking** - Special attention to Qwen, DeepSeek, and other Chinese models
- **Size Estimates** - Rough GB estimates so you know download sizes
- **GGUF Metadata** - Extracts detailed GGUF quantization information
- **Auto-Launch** - Automatically opens browser when started
- **Weekly Digests** - Automated reports of new models

## 🚀 Quick Start

### Windows Users

1. **Clone the repository**
   ```bash
   git clone https://github.com/nigelp/ai-model-tracker.git
   cd ai-model-tracker
   ```

2. **Install**
   ```bash
   install.bat
   ```

3. **Start**
   ```bash
   start_tracker.bat
   ```

4. **Open your browser** to http://localhost:5000

### Linux/Mac Users

1. **Clone the repository**
   ```bash
   git clone https://github.com/nigelp/ai-model-tracker.git
   cd ai-model-tracker
   ```

2. **Install**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Start**
   ```bash
   chmod +x start_tracker.sh
   ./start_tracker.sh
   ```

4. **Open your browser** to http://localhost:5000

## 📁 Project Structure

```
ai-model-tracker/
├── web_dashboard.py      # Web interface with Flask
├── model_scraper.py      # Model discovery scraper
├── gguf_parser.py       # GGUF metadata extraction
├── install.bat          # Windows installer
├── start_tracker.bat    # Windows launcher
├── config.json          # Configuration settings
├── requirements.txt     # Python dependencies
├── web_dashboard.spec   # PyInstaller spec
├── data/              # SQLite database (gitignored)
├── tools/              # External binaries
└── reports/            # Generated reports (gitignored)
```

## 🖥️ Using the Dashboard

Once running, you'll see a professional dashboard with:

**Left Panel - Statistics:**
- Total models tracked
- Chinese vs. non-Chinese count
- Breakdown by category (Text, Image, Video, Audio, Coding)
- GGUF model count

**Middle - Filter Controls:**
- Filter by source: Hugging Face, ModelScope
- Filter by category
- Show only Chinese models
- Filter by GGUF format
- Search by name or description
- Sort by date, downloads, likes, name, or size

**Right - Model Cards:**
Each model shows:
- Name and brief description
- Estimated size (helpful for download planning)
- Release date
- Source badge (HF, MS)
- GGUF badge with quantization details
- VRAM requirements
- Context length
- Chinese indicator if applicable
- Direct link to model page

**Top Right - Actions:**
- Refresh data button
- Export to JSON option

## ⚙️ Configuration

Edit `config.json` to change settings:

```json
{
  "scrape_interval_hours": 6,        // How often to refresh
  "max_models_per_source": 100,      // Models per source
  "vram_limit_gb": 24,             // VRAM limit for filtering
  "include_chinese": true,           // Include Chinese models
  "sources": {
    "huggingface": true,             // Enable HF scraping
    "modelscope": true               // Enable ModelScope scraping
  }
}
```

## 🛠️ Building the Executable

If you want to build the standalone Windows executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller web_dashboard.spec --clean

# Result: dist/web_dashboard.exe (includes auto-launch browser)
```

## 🐛 Common Problems

### "Python not found" Error
**Problem:** Installer can't find Python
**Solution:** Install Python 3.8+ from [python.org](https://www.python.org/downloads/)
- Windows: Check "Add Python to PATH" during installation

### "Port 5000 already in use"
**Problem:** Another app is using port 5000
**Solution:** Change port in `web_dashboard.py` line 619:
```python
app.run(debug=True, port=5001)  # Change to 5001
```
Then use http://localhost:5001 in your browser

### "Permission denied" on Mac/Linux
**Problem:** Scripts aren't executable
**Solution:** Run this command:
```bash
chmod +x install.sh start_tracker.sh
```

### "Module not found" (Flask/Requests)
**Problem:** Python packages missing
**Solution:** Install manually:
```bash
pip install -r requirements.txt
```
Or re-run the installer

### "Connection error" or "No models showing"
**Problem:** Internet issue or API limits
**Solution:**
- Check your internet connection
- Wait a minute and refresh
- Some sources have rate limits

## 📊 Initial Data

The system comes with sample data including:
- Real Hugging Face trending models (live data)
- Chinese models: Qwen2.5, DeepSeek-Coder, etc.
- Image models: Stable Diffusion 3 example
- Multimodal models: Llama 3.2 Vision example
- Size estimates for each model

## 🔄 Updates

**Manual Update:** Click "Refresh" in dashboard

**Automatic Update:** The scraper runs every 6 hours automatically

**Force Update:** Stop the app (Ctrl+C) and restart it

## 📧 Reports

The system automatically generates a weekly HTML report showing:
- New models from past 7 days
- Statistics and trends
- Chinese model highlights
- Size distribution

Find it at: http://localhost:5000/weekly-report or in the `reports/` folder.

## 🗂️ Data Storage

- **Database:** `data/models.db` (SQLite file)
- **Reports:** `reports/weekly_report.html`
- **Configuration:** `config.json`

You can safely delete the `data` folder to start fresh.

## 👥 Ideal For

- AI enthusiasts who want to stay updated on new models
- Developers looking for specific model types
- Researchers tracking model release trends
- Anyone tired of manually checking multiple websites

## 💡 Pro Tips

- Use search to find specific model types
- Filter by "Chinese Only" to see Qwen/DeepSeek models
- Check size estimates before downloading huge models
- Export data if you want to analyze in a spreadsheet
- The system works offline once data is collected

## 🤝 Acknowledgments

This project uses the following open-source tools:

- **[gpustack/gguf-parser-go](https://github.com/gpustack/gguf-parser-go)** - GGUF metadata extraction
  - This project would not have detailed GGUF support without this excellent parser
  - Licensed under Apache 2.0

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Getting Help

- Check the console window for error messages
- Ensure Python 3.8+ is installed and in PATH
- Try manual installation with `pip install -r requirements.txt`
- Check firewall/antivirus isn't blocking Python

## 📈 Next Steps After Installation

Once you have it running, you can:
- Bookmark http://localhost:5000 in your browser
- Set up automatic startup (add to startup folder on Windows)
- Share weekly reports with your team
- Customize sources in `config.json`

## 🏁 Getting Started Checklist

- [ ] Python 3.8+ installed
- [ ] Repository cloned
- [ ] Ran installer (`install.bat` or `install.sh`)
- [ ] Started tracker (`start_tracker.bat` or `start_tracker.sh`)
- [ ] Browser opened to http://localhost:5000
- [ ] Can see model cards and filters
- [ ] Refresh data successfully

**Enjoy tracking AI models! 🚀**
