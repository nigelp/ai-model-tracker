from flask import Flask, render_template_string, jsonify
import sqlite3
import json
import os
import sys
import threading
import webbrowser
from datetime import datetime

app = Flask(__name__)

# HTML template for the dashboard
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Model Tracker Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .filters {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .filter-group {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        select, input {
            padding: 10px 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            min-width: 150px;
        }
        .model-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        .model-card {
            background: white;
            border: 1px solid #e1e4e8;
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .model-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border-color: #667eea;
        }
        .model-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .model-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-hf { background: #ffd700; color: black; }
        .badge-ms { background: #ff6b6b; color: white; }
        .badge-chinese { background: #4ecdc4; color: white; }
        .badge-gguf { background: #17a2b8; color: white; }
        .badge-quant { background: #6f42c1; color: white; font-family: monospace; }
        .gguf-info {
            background: #f0f7ff;
            border-radius: 8px;
            padding: 10px;
            margin: 10px 0;
            font-size: 12px;
        }
        .gguf-info .gguf-row {
            display: flex;
            justify-content: space-between;
            margin: 4px 0;
        }
        .gguf-info .gguf-label { color: #666; }
        .gguf-info .gguf-value { font-weight: 600; color: #333; }
        .vram-ok { color: #28a745; }
        .vram-warning { color: #ffc107; }
        .vram-high { color: #dc3545; }
        .model-desc {
            color: #666;
            font-size: 14px;
            line-height: 1.5;
            margin: 10px 0;
        }
        .model-meta {
            color: #888;
            font-size: 12px;
            margin-top: 15px;
            display: flex;
            justify-content: space-between;
        }
        .size-indicator {
            height: 6px;
            background: #e9ecef;
            border-radius: 3px;
            margin: 10px 0;
        }
        .size-bar {
            height: 100%;
            background: #28a745;
            border-radius: 3px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #666;
            font-size: 14px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="color: #333; margin-bottom: 10px;">🤖 AI Model Tracker</h1>
            <p style="color: #666;">Live tracking of new AI models from Hugging Face, ModelScope, and more</p>
            <p style="color: #888; font-size: 14px; margin-top: 10px;">
                Last updated: <span id="last-updated">Loading...</span>
                <button onclick="refreshData()" id="refresh-btn" style="margin-left: 15px; padding: 5px 15px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">Refresh</button>
                <span id="scrape-status" style="margin-left: 10px; font-size: 12px;"></span>
            </p>
        </div>
        
        <div class="stats" id="stats">
            <div class="loading">Loading statistics...</div>
        </div>
        
        <div class="filters">
            <h3 style="margin-bottom: 15px; color: #333;">Filter Models</h3>
            <div class="filter-group">
                <select id="filter-source" onchange="filterModels()">
                    <option value="all">All Sources</option>
                    <option value="huggingface">Hugging Face</option>
                    <option value="modelscope">ModelScope</option>
                </select>
                
                <select id="filter-category" onchange="filterModels()">
                    <option value="all">All Categories</option>
                    <option value="text">Text Models</option>
                    <option value="image">Image Models</option>
                    <option value="coding">Coding Models</option>
                    <option value="multimodal">Multimodal</option>
                </select>
                
                <select id="filter-chinese" onchange="filterModels()">
                    <option value="all">All Models</option>
                    <option value="chinese">Chinese Only</option>
                    <option value="non-chinese">Non-Chinese</option>
                </select>

                <select id="filter-format" onchange="filterModels()">
                    <option value="all">All Formats</option>
                    <option value="gguf">GGUF Only</option>
                    <option value="non-gguf">Non-GGUF</option>
                </select>

                <select id="sort-by" onchange="filterModels()">
                    <option value="date-desc">Recently Modified</option>
                    <option value="date-asc">Oldest First</option>
                    <option value="downloads-desc">Most Downloads</option>
                    <option value="likes-desc">Most Likes</option>
                    <option value="name-asc">Name (A-Z)</option>
                    <option value="size-desc">Largest Size</option>
                </select>

                <input type="text" id="search" placeholder="Search models..." onkeyup="filterModels()" style="flex-grow: 1;">
            </div>
        </div>
        
        <div class="model-grid" id="model-list">
            <div class="loading">Loading models...</div>
        </div>
        
        <div class="footer">
            <p>Tracked from: Hugging Face • ModelScope • GitHub • Reddit</p>
            <p>Models suitable for local installation (≤24GB VRAM)</p>
            <p style="margin-top: 10px; font-size: 12px;">
                <a href="/api/models" style="color: #667eea;">JSON API</a> • 
                <a href="/api/stats" style="color: #667eea;">Statistics</a> • 
                <a href="javascript:exportData()" style="color: #667eea;">Export Data</a>
            </p>
        </div>
    </div>

    <script>
        let allModels = [];
        
        async function loadData() {
            try {
                const response = await fetch('/api/models');
                const data = await response.json();
                allModels = data.models;
                updateStats(data.stats);
                displayModels(allModels);
                document.getElementById('last-updated').textContent = new Date().toLocaleString();
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('model-list').innerHTML = 
                    '<div class="loading">Error loading data. Please refresh.</div>';
            }
        }
        
        function updateStats(stats) {
            document.getElementById('stats').innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${stats.total}</div>
                    <div>Total Models</div>
                </div>
                <div class="stat-card" style="border-left-color: #17a2b8;">
                    <div class="stat-number" style="color: #17a2b8;">${stats.gguf || 0}</div>
                    <div>GGUF Models</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.chinese}</div>
                    <div>Chinese Models</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.text}</div>
                    <div>Text Models</div>
                </div>
            `;
        }
        
        function displayModels(models) {
            const container = document.getElementById('model-list');
            
            if (models.length === 0) {
                container.innerHTML = '<div class="loading">No models found matching your filters.</div>';
                return;
            }
            
            container.innerHTML = models.map(model => `
                <div class="model-card" onclick="window.open('${model.url}', '_blank')">
                    <div class="model-header">
                        <div class="model-title">${model.name}</div>
                        <div>
                            ${(model.is_gguf || model.name.toLowerCase().includes('gguf')) ? '<span class="badge badge-gguf">GGUF</span>' : ''}
                            ${model.is_chinese ? '<span class="badge badge-chinese">中文</span>' : ''}
                            <span class="badge badge-${model.source === 'huggingface' ? 'hf' : 'ms'}">
                                ${model.source.toUpperCase()}
                            </span>
                        </div>
                    </div>

                    <div class="model-desc">
                        ${model.description || 'No description available'}
                    </div>

                    ${model.is_gguf && model.quantization ? `
                        <div class="gguf-info">
                            <div class="gguf-row">
                                <span class="gguf-label">Quantization</span>
                                <span class="badge badge-quant">${model.quantization}</span>
                            </div>
                            ${model.vram_required_gb ? `
                            <div class="gguf-row">
                                <span class="gguf-label">VRAM Required</span>
                                <span class="gguf-value ${model.vram_required_gb <= 8 ? 'vram-ok' : model.vram_required_gb <= 24 ? 'vram-warning' : 'vram-high'}">${model.vram_required_gb}GB</span>
                            </div>
                            ` : ''}
                            ${model.context_length ? `
                            <div class="gguf-row">
                                <span class="gguf-label">Context</span>
                                <span class="gguf-value">${(model.context_length / 1024).toFixed(0)}K</span>
                            </div>
                            ` : ''}
                            ${model.gguf_architecture ? `
                            <div class="gguf-row">
                                <span class="gguf-label">Architecture</span>
                                <span class="gguf-value">${model.gguf_architecture}</span>
                            </div>
                            ` : ''}
                        </div>
                    ` : ''}

                    ${!model.is_gguf && model.size_gb ? `
                        <div style="font-size: 12px; color: #666;">
                            Size: ~${model.size_gb}GB
                            <div class="size-indicator">
                                <div class="size-bar" style="width: ${Math.min(model.size_gb / 20 * 100, 100)}%"></div>
                            </div>
                        </div>
                    ` : ''}

                    <div class="model-meta">
                        <span>${model.category.toUpperCase()}</span>
                        <span>${model.release_date}</span>
                    </div>
                </div>
            `).join('');
        }
        
        function filterModels() {
            const source = document.getElementById('filter-source').value;
            const category = document.getElementById('filter-category').value;
            const chinese = document.getElementById('filter-chinese').value;
            const format = document.getElementById('filter-format').value;
            const search = document.getElementById('search').value.toLowerCase();
            const sortBy = document.getElementById('sort-by').value;

            let filtered = allModels.filter(model => {
                if (source !== 'all' && model.source !== source) return false;
                if (category !== 'all' && model.category !== category) return false;
                if (chinese === 'chinese' && !model.is_chinese) return false;
                if (chinese === 'non-chinese' && model.is_chinese) return false;

                // GGUF format filter (uses database field, fallback to name check)
                const isGguf = model.is_gguf || model.name.toLowerCase().includes('gguf');
                if (format === 'gguf' && !isGguf) return false;
                if (format === 'non-gguf' && isGguf) return false;

                if (search && !model.name.toLowerCase().includes(search) &&
                    !(model.description || '').toLowerCase().includes(search)) return false;
                return true;
            });

            // Sort the filtered results
            filtered.sort((a, b) => {
                switch(sortBy) {
                    case 'date-desc':
                        return (b.release_date || '').localeCompare(a.release_date || '');
                    case 'date-asc':
                        return (a.release_date || '').localeCompare(b.release_date || '');
                    case 'downloads-desc':
                        return (b.downloads || 0) - (a.downloads || 0);
                    case 'likes-desc':
                        return (b.likes || 0) - (a.likes || 0);
                    case 'name-asc':
                        return (a.name || '').localeCompare(b.name || '');
                    case 'size-desc':
                        return (b.size_gb || 0) - (a.size_gb || 0);
                    default:
                        return 0;
                }
            });

            displayModels(filtered);
        }
        
        function refreshData() {
            const btn = document.getElementById('refresh-btn');
            const status = document.getElementById('scrape-status');
            
            btn.disabled = true;
            btn.textContent = 'Refreshing...';
            status.textContent = 'Fetching new models from HuggingFace and ModelScope...';
            status.style.color = '#667eea';
            
            fetch('/api/refresh')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'already_running') {
                        status.textContent = 'Scraping already in progress...';
                        status.style.color = '#ffc107';
                    } else {
                        status.textContent = 'Scraping started - this may take a minute...';
                        status.style.color = '#28a745';
                    }
                    
                    // Poll for completion
                    pollScrapeStatus();
                })
                .catch(error => {
                    console.error('Error:', error);
                    status.textContent = 'Error starting refresh';
                    status.style.color = '#dc3545';
                    btn.disabled = false;
                    btn.textContent = 'Refresh';
                });
        }
        
        function pollScrapeStatus() {
            const checkStatus = () => {
                fetch('/api/scrape-status')
                    .then(response => response.json())
                    .then(data => {
                        const status = document.getElementById('scrape-status');
                        const btn = document.getElementById('refresh-btn');
                        
                        if (!data.in_progress) {
                            // Scraping complete
                            if (data.last_result && data.last_result.success) {
                                status.textContent = '✓ Updated successfully!';
                                status.style.color = '#28a745';
                                setTimeout(() => {
                                    status.textContent = '';
                                    loadData();
                                }, 2000);
                            } else {
                                status.textContent = '✗ Error during scraping';
                                status.style.color = '#dc3545';
                            }
                            btn.disabled = false;
                            btn.textContent = 'Refresh';
                        } else {
                            // Still scraping
                            setTimeout(checkStatus, 2000);
                        }
                    })
                    .catch(error => {
                        console.error('Error checking status:', error);
                        setTimeout(checkStatus, 2000);
                    });
            };
            
            setTimeout(checkStatus, 2000);
        }
        
        function exportData() {
            const dataStr = JSON.stringify(allModels, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            const exportFileDefaultName = 'ai-models-export.json';
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 5 minutes
        setInterval(loadData, 5 * 60 * 1000);
    </script>
</body>
</html>
'''

def get_db_connection():
    # Handle both development and PyInstaller frozen (EXE) environments
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        base_path = sys._MEIPASS
    else:
        # Running as Python script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    db_path = os.path.join(base_path, 'data', 'models.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/models')
def get_models():
    conn = get_db_connection()
    models = conn.execute('SELECT * FROM models ORDER BY release_date DESC').fetchall()
    conn.close()
    
    # Convert to list of dicts
    models_list = [dict(model) for model in models]
    
    # Calculate stats
    # GGUF count includes is_gguf=1 OR name contains 'gguf' (consistent with frontend filter)
    def is_gguf_model(m):
        return m.get('is_gguf') or 'gguf' in m.get('name', '').lower()

    stats = {
        'total': len(models_list),
        'gguf': sum(1 for m in models_list if is_gguf_model(m)),
        'chinese': sum(1 for m in models_list if m['is_chinese']),
        'text': sum(1 for m in models_list if m['category'] == 'text'),
        'image': sum(1 for m in models_list if m['category'] == 'image'),
        'coding': sum(1 for m in models_list if m['category'] == 'coding'),
        'multimodal': sum(1 for m in models_list if m['category'] == 'multimodal')
    }
    
    return jsonify({
        'models': models_list,
        'stats': stats,
        'last_updated': datetime.now().isoformat()
    })

@app.route('/api/stats')
def get_stats():
    conn = get_db_connection()
    
    # Get counts by source
    sources = conn.execute('SELECT source, COUNT(*) as count FROM models GROUP BY source').fetchall()
    categories = conn.execute('SELECT category, COUNT(*) as count FROM models GROUP BY category').fetchall()
    
    conn.close()
    
    return jsonify({
        'by_source': dict(sources),
        'by_category': dict(categories),
        'total': sum(s[1] for s in sources)
    })

# Global flag to track if scraping is in progress
scraping_in_progress = False
scraping_status = {'last_update': None, 'last_result': None}

@app.route('/api/refresh')
def refresh_data():
    global scraping_in_progress, scraping_status
    
    if scraping_in_progress:
        return jsonify({
            'status': 'already_running',
            'message': 'Scraping already in progress',
            'last_update': scraping_status['last_update']
        }), 400
    
    scraping_in_progress = True
    scraping_status['last_update'] = datetime.now().isoformat()
    
    # Run scraper in background thread
    def run_scraper():
        global scraping_in_progress, scraping_status
        try:
            # Import and run the scraper
            import model_scraper
            result = model_scraper.main()
            scraping_status['last_result'] = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'models_count': result
            }
        except Exception as e:
            scraping_status['last_result'] = {
                'success': False,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
        finally:
            scraping_in_progress = False
    
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'refresh_triggered',
        'timestamp': datetime.now().isoformat(),
        'message': 'Scraping started in background'
    })

@app.route('/api/scrape-status')
def scrape_status():
    global scraping_in_progress, scraping_status
    return jsonify({
        'in_progress': scraping_in_progress,
        'last_update': scraping_status['last_update'],
        'last_result': scraping_status['last_result']
    })

if __name__ == '__main__':
    print("=" * 50)
    print("AI Model Tracker Dashboard")
    print("=" * 50)
    print("Open your browser to: http://localhost:5000")
    print("Tracking models from Hugging Face, ModelScope, and more")
    print("Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    def open_browser():
        webbrowser.open('http://localhost:5000')

    threading.Timer(1.0, open_browser).start()

    if getattr(sys, 'frozen', False):
        app.run(debug=False, port=5000)
    else:
        app.run(debug=True, port=5000)
