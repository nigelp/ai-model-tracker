🤖 AI Model Tracker - Complete README
🎯 What Is This?
AI Model Tracker is a one-click desktop application that automatically discovers and organizes AI models from across the internet. It solves the problem of “model sprawl” where you have models scattered everywhere without knowing what you have, what’s new, or what will work on your hardware.

Key Features:

Automatic Discovery: Scrapes Hugging Face, ModelScope (Chinese models), GitHub, and Reddit for new AI models

Hardware-Aware: Focuses on models that work with ≤24GB VRAM (most consumer GPUs)

Beautiful Dashboard: Web interface to browse, filter, and search models

Chinese Model Tracking: Special attention to Qwen, DeepSeek, and other Chinese models

Size Estimates: Rough GB estimates so you know download sizes

Weekly Digests: Automated reports of new models

🚀 Quick Installation
Windows Users:
Create a new folder on your Desktop called AI-Model-Tracker

Download all files into that folder

Double-click install.bat and wait for installation (1-2 minutes)

Double-click start_tracker.bat to launch

Open your browser to http://localhost:5000

Mac/Linux Users:
Create a new folder in your home directory: mkdir ~/AI-Model-Tracker

Download all files into that folder

Make scripts executable: chmod +x install.sh start_tracker.sh

Run installer: ./install.sh

Start the tracker: ./start_tracker.sh

Open your browser to http://localhost:5000

📁 What’s Included
The package includes these main files:

model_scraper.py - The brain that collects model data

web_dashboard.py - Beautiful web interface

install.bat / install.sh - One-click installer

start_tracker.bat / start_tracker.sh - Easy launcher

requirements.txt - Python dependencies

config.json - Settings you can customize

🖥️ Using the Dashboard
Once running, you’ll see a professional dashboard with:

Left Panel - Statistics:

Total models tracked

Chinese vs. non-Chinese count

Breakdown by category (Text, Image, Video, Audio, Coding)

Middle - Filter Controls:

Filter by source: Hugging Face, ModelScope, etc.

Filter by category

Show only Chinese models

Search by name or description

Right - Model Cards:
Each model shows:

Name and brief description

Estimated size (helpful for download planning)

Release date

Source badge (HF, MS, etc.)

Chinese indicator if applicable

Direct link to model page

Top Right - Actions:

Refresh data button

Export to JSON option

View weekly report

🔧 Customization
Edit config.json to change:

How often to scrape (default: every 6 hours)

Which sources to track

Maximum models per source

Database location

🐛 Common Problems & Solutions
1. “Python not found” Error
Problem: Installer can’t find Python
Solution: Install Python 3.8+ from python.org
Windows tip: Check “Add Python to PATH” during installation
Mac tip: brew install python or use the official installer

2. “Port 5000 already in use”
Problem: Another app is using port 5000
Solution: Change the port in web_dashboard.py:

Python






12
Then use http://localhost:5001 in your browser

3. “Permission denied” on Mac/Linux
Problem: Scripts aren’t executable
Solution: Run this command in terminal:

Shell






12
4. “Module not found” (Flask/Requests)
Problem: Python packages missing
Solution: Install manually:

Shell






12
Or re-run the installer

5. “Connection error” or “No models showing”
Problem: Internet issue or API limits
Solution:

Check your internet connection

Wait a minute and refresh

Some sources have rate limits

📊 What Data You’ll See Initially
The system comes with sample data including:

Real Hugging Face trending models (live data)

Chinese models: Qwen2.5, DeepSeek-Coder, etc.

Image models: Stable Diffusion 3 example

Multimodal models: Llama 3.2 Vision example

Size estimates for each model

🔄 Keeping It Updated
Manual Update: Click “Refresh” in the dashboard
Automatic Update: The scraper runs every 6 hours automatically
Force Update: Stop the app (Ctrl+C) and restart it

🗂️ Where Data Is Stored
Database: data/models.db (SQLite file)

Reports: reports/weekly_report.html

Configuration: config.json

You can safely delete the data folder to start fresh.

📧 Getting Weekly Reports
The system automatically generates a weekly HTML report showing:

New models from the past 7 days

Statistics and trends

Chinese model highlights

Size distribution

Find it at: http://localhost:5000/weekly-report or in the reports folder.

🎯 Ideal For
AI enthusiasts who want to stay updated on new models

Developers looking for specific model types

Researchers tracking model release trends

Anyone tired of manually checking multiple websites

❓ Need Help?
Check the console window for error messages

Ensure Python 3.8+ is installed and in PATH

Try manual installation:

Shell






123456
Check firewall/antivirus isn’t blocking Python

📈 Next Steps After Installation
Once you have it running, you can:

Bookmark http://localhost:5000 in your browser

Set up automatic startup (add to startup folder on Windows)

Share the weekly reports with your team

Customize the sources in config.json

🏁 Getting Started Checklist
 Python 3.8+ installed

 All files in one folder

 Ran installer (install.bat or install.sh)

 Started tracker (start_tracker.bat or start_tracker.sh)

 Browser opened to http://localhost:5000

 Can see model cards and filters

💡 Pro Tips
Use the search to find specific model types

Filter by “Chinese Only” to see Qwen/DeepSeek models

Check size estimates before downloading huge models

Export data if you want to analyze in spreadsheet

The system works offline once data is collected

