#!/usr/bin/env python3
"""
Build the web app from analysis data + config.
Outputs to docs/ for GitHub Pages.
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
DOCS_DATA = DOCS_DIR / "data"

def load_config(config_path=None):
    if config_path:
        with open(config_path) as f:
            return json.load(f)
    default = ROOT / "config.json"
    if default.exists():
        with open(default) as f:
            return json.load(f)
    return {"short_name": "Podcast", "emoji": "🎤"}

def build_web(config):
    """Copy analysis data to docs/data/ and generate index.html from template."""
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "css").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "js").mkdir(parents=True, exist_ok=True)

    # Copy analysis files
    analysis_files = [
        'consensus.json', 'advice.json', 'contrarian.json',
        'topics.json', 'top_insights.json', 'expertise.json'
    ]

    print(f"Building web app for {config.get('podcast_name', 'podcast')}...")
    copied = 0
    for filename in analysis_files:
        src = DATA_DIR / "analysis" / filename
        if src.exists():
            shutil.copy2(src, DOCS_DATA / filename)
            print(f"  ✓ {filename}")
            copied += 1
        else:
            print(f"  ✗ Missing {filename}")

    # guests.json should already be in docs/data/ from build_guests.py
    if (DOCS_DATA / "guests.json").exists():
        print(f"  ✓ guests.json (already built)")
    else:
        print(f"  ✗ Missing guests.json — run build_guests.py first!")

    # Generate index.html from config
    generate_index(config)
    generate_css(config)
    generate_js(config)

    print(f"\n✅ Web build complete ({copied} analysis files)")

def generate_index(config):
    """Generate index.html with config-driven branding."""
    name = config.get('short_name', 'Podcast')
    emoji = config.get('emoji', '🎤')
    subtitle = config.get('subtitle', f'AI-powered analysis of every episode')
    disclaimer = config.get('disclaimer', f'Not affiliated with {config.get("podcast_name", "this podcast")}')
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} Insights — {config.get("podcast_name", "Podcast")} Knowledge Base</title>
    <meta name="description" content="{subtitle}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{emoji} {name} <span>Insights</span></h1>
            <p class="subtitle">{subtitle}</p>
            <nav class="nav">
                <a href="#consensus" class="nav-link active" data-view="consensus">Top Insights</a>
                <a href="#guests" class="nav-link" data-view="guests">Guests</a>
                <a href="#episodes" class="nav-link" data-view="episodes">Episodes</a>
                <a href="#topics" class="nav-link" data-view="topics">Topics</a>
                <a href="#contrarian" class="nav-link" data-view="contrarian">Contrarian Corner</a>
                <a href="#advice" class="nav-link" data-view="advice">Actionable Advice</a>
            </nav>
        </header>

        <div class="stats-header" id="statsHeader">
            <div class="stat-card"><div class="stat-number" id="statEpisodes">-</div><div class="stat-label">Episodes</div></div>
            <div class="stat-card"><div class="stat-number" id="statGuests">-</div><div class="stat-label">Guests</div></div>
            <div class="stat-card"><div class="stat-number" id="statInsights">-</div><div class="stat-label">Insights</div></div>
            <div class="stat-card"><div class="stat-number" id="statAdvice">-</div><div class="stat-label">Advice Items</div></div>
        </div>

        <div class="search-container">
            <input type="text" id="searchInput" class="search-input" placeholder="Search insights, guests, topics...">
            <button id="searchBtn" class="search-btn">Search</button>
        </div>

        <main class="main-content">
            <div id="consensusView" class="view active">
                <h2 class="section-title">Top Consensus Themes</h2>
                <div id="topicFilter-container" style="margin-bottom:20px;">
                    <select id="topicFilter" class="filter-select"><option value="">All Topics</option></select>
                </div>
                <div id="consensusList" class="cards-grid"></div>
            </div>
            <div id="guestsView" class="view">
                <h2 class="section-title">Guest Directory</h2>
                <div style="display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;">
                    <input type="text" id="guestSearch" class="search-input" placeholder="Search guests..." style="flex:1;min-width:200px;">
                    <select id="guestExpertiseFilter" class="filter-select"><option value="">All Expertise</option></select>
                </div>
                <div id="guestsList" class="cards-grid"></div>
            </div>
            <div id="episodesView" class="view">
                <h2 class="section-title">All Episodes</h2>
                <div id="episodesList" class="cards-grid"></div>
            </div>
            <div id="topicsView" class="view">
                <h2 class="section-title">Topics Explorer</h2>
                <div id="topicsList" class="topics-grid"></div>
            </div>
            <div id="contrarianView" class="view">
                <h2 class="section-title">Contrarian Corner</h2>
                <div id="contrarianList" class="cards-grid"></div>
            </div>
            <div id="adviceView" class="view">
                <h2 class="section-title">Actionable Advice</h2>
                <div style="margin-bottom:20px;">
                    <select id="adviceTopicFilter" class="filter-select"><option value="">All Topics</option></select>
                </div>
                <div id="adviceList" class="cards-grid"></div>
            </div>
            <div id="searchView" class="view">
                <h2 class="section-title">Search Results</h2>
                <div id="searchResults"></div>
            </div>
        </main>

        <div id="insightModal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <div id="modalBody"></div>
            </div>
        </div>

        <footer style="text-align:center;padding:40px 20px;color:var(--text-secondary);font-size:0.85rem;">
            <p>{disclaimer}</p>
            <p style="margin-top:8px;">Built with AI-powered transcript analysis</p>
        </footer>
    </div>
    <script src="js/app.js"></script>
</body>
</html>'''
    
    (DOCS_DIR / "index.html").write_text(html)
    print(f"  ✓ Generated index.html")

def generate_css(config):
    """Generate CSS with config-driven design tokens."""
    d = config.get('design', {})
    primary = d.get('primary_color', '#d32f2f')
    accent = d.get('accent_color', '#ff6f00')
    highlight = d.get('highlight_color', '#ffc107')
    bg_dark = d.get('bg_dark', '#0a0a0a')
    bg_card = d.get('bg_card', '#141414')
    theme = d.get('theme', 'dark')
    
    if theme == 'light':
        bg_dark = '#faf7f2'
        bg_card = '#ffffff'
        text_primary = '#1a1a1a'
        text_secondary = '#666'
        border_color = '#e0d8cc'
    else:
        text_primary = '#e0e0e0'
        text_secondary = '#999'
        border_color = '#2a2a2a'
    
    css = f'''/* Auto-generated — do not edit manually */
:root {{
    --primary: {primary};
    --accent: {accent};
    --highlight: {highlight};
    --bg-dark: {bg_dark};
    --bg-card: {bg_card};
    --bg-body: {bg_dark};
    --text-primary: {text_primary};
    --text-secondary: {text_secondary};
    --border: {border_color};
    --radius: 12px;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Inter', -apple-system, sans-serif; background: var(--bg-body); color: var(--text-primary); line-height: 1.6; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
.header {{ text-align: center; padding: 40px 20px; }}
.header h1 {{ font-size: 3rem; font-weight: 800; letter-spacing: -1px; }}
.header h1 span {{ background: linear-gradient(135deg, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.subtitle {{ color: var(--text-secondary); font-size: 1.1rem; margin-top: 10px; }}
.nav {{ display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-top: 25px; }}
.nav-link {{ color: var(--text-secondary); text-decoration: none; padding: 8px 16px; border-radius: 20px; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; border: 1px solid var(--border); }}
.nav-link:hover, .nav-link.active {{ color: var(--primary); border-color: var(--primary); background: rgba({int(primary[1:3],16)},{int(primary[3:5],16)},{int(primary[5:7],16)},0.1); }}
.stats-header {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; margin: 30px 0; }}
.stat-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; text-align: center; }}
.stat-number {{ font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.stat-label {{ color: var(--text-secondary); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px; }}
.search-container {{ display: flex; gap: 10px; margin-bottom: 30px; }}
.search-input {{ flex: 1; padding: 12px 16px; border-radius: var(--radius); border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); font-size: 0.95rem; }}
.search-input:focus {{ outline: none; border-color: var(--primary); }}
.search-btn {{ padding: 12px 24px; border-radius: var(--radius); border: none; background: var(--primary); color: white; font-weight: 600; cursor: pointer; }}
.filter-select {{ padding: 10px 14px; border-radius: var(--radius); border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); font-size: 0.9rem; }}
.section-title {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 20px; }}
.view {{ display: none; }}
.view.active {{ display: block; }}
.cards-grid {{ display: flex; flex-direction: column; gap: 15px; }}
.card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; transition: border-color 0.2s; }}
.card:hover {{ border-color: var(--primary); }}
.card-title {{ font-size: 1.15rem; font-weight: 600; margin-bottom: 10px; }}
.card-meta {{ color: var(--text-secondary); font-size: 0.9rem; }}
.badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 500; margin: 2px; }}
.badge-count {{ background: rgba({int(primary[1:3],16)},{int(primary[3:5],16)},{int(primary[5:7],16)},0.15); color: var(--primary); }}
.badge-topic {{ background: rgba({int(accent[1:3],16)},{int(accent[3:5],16)},{int(accent[5:7],16)},0.15); color: var(--accent); }}
.quote {{ font-style: italic; color: var(--text-secondary); border-left: 3px solid var(--accent); padding-left: 15px; margin: 10px 0; }}
.guest-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }}
.guest-name {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 8px; }}
.guest-stats {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
.guest-stat {{ color: var(--text-secondary); font-size: 0.85rem; }}
.guest-episode-link {{ display: block; padding: 8px 12px; margin: 4px 0; border-radius: 8px; color: var(--accent); text-decoration: none; font-size: 0.9rem; background: var(--bg-dark); }}
.guest-episode-link:hover {{ background: rgba({int(accent[1:3],16)},{int(accent[3:5],16)},{int(accent[5:7],16)},0.1); }}
.topics-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
.topic-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; cursor: pointer; text-align: center; transition: all 0.2s; }}
.topic-card:hover {{ border-color: var(--primary); transform: translateY(-2px); }}
.topic-card-title {{ font-weight: 600; font-size: 1.05rem; }}
.topic-card-count {{ color: var(--text-secondary); font-size: 0.85rem; margin-top: 5px; }}
.modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); }}
.modal-content {{ background: var(--bg-card); margin: 10% auto; padding: 30px; border-radius: var(--radius); max-width: 700px; max-height: 70vh; overflow-y: auto; position: relative; }}
.close {{ position: absolute; right: 20px; top: 15px; font-size: 1.5rem; cursor: pointer; color: var(--text-secondary); }}
.empty-state {{ text-align: center; padding: 60px 20px; color: var(--text-secondary); }}
.empty-state-icon {{ font-size: 3rem; margin-bottom: 15px; }}

@media (max-width: 768px) {{
    .header h1 {{ font-size: 2rem; }}
    .stat-number {{ font-size: 1.8rem; }}
    .nav {{ gap: 5px; }}
    .nav-link {{ padding: 6px 12px; font-size: 0.8rem; }}
}}'''
    
    (DOCS_DIR / "css" / "styles.css").write_text(css)
    print(f"  ✓ Generated styles.css")

def generate_js(config):
    """Generate app.js with null-safe rendering and config-driven branding."""
    short = config.get('short_name', 'Podcast')
    slug = config.get('source_config', {}).get('podscripts_slug', config.get('slug', ''))
    
    js = '''// Auto-generated — Podcast Insights Web App
// Null-safe display helper
function safe(val, fallback = '') {
    if (val === null || val === undefined || val === 'null' || val === 'undefined' || val === 'N/A' || val === 'Unknown') return fallback;
    return String(val);
}

const PODCAST_SHORT = ''' + json.dumps(short) + ''';
const PODCAST_SLUG = ''' + json.dumps(slug) + ''';

class PodcastInsights {
    constructor() {
        this.data = { consensus: [], episodes: [], topics: {}, contrarian: [], advice: [], topInsights: [], guests: [] };
        this.currentView = 'consensus';
        this.init();
    }

    async init() {
        await this.loadData();
        this.setupEventListeners();
        this.renderView('consensus');
    }

    async loadData() {
        try {
            const [consensus, advice, contrarian, topics, topInsights, guests] = await Promise.all([
                fetch('data/consensus.json').then(r => r.json()),
                fetch('data/advice.json').then(r => r.json()),
                fetch('data/contrarian.json').then(r => r.json()),
                fetch('data/topics.json').then(r => r.json()),
                fetch('data/top_insights.json').then(r => r.json()),
                fetch('data/guests.json').then(r => r.json()).catch(() => [])
            ]);
            this.data = { consensus, advice, contrarian, topics, topInsights, guests, episodes: [] };
            this.buildEpisodesList();
            this.populateFilters();
            this.updateStats();
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }

    buildEpisodeTitle(item) {
        const t = item.episode_title;
        const bad = [null, undefined, '', 'N/A', 'Unknown', 'Episode', 'null', 'undefined'];
        if (bad.includes(t) || (t && t.startsWith('Episode #'))) {
            const match = (item.episode_id || '').match(/^(\\d+)/);
            const num = match ? `#${match[1]}` : '';
            const guest = safe(item.guest, '');
            if (num && guest) return `${PODCAST_SHORT} ${num} — ${guest}`;
            if (num) return `${PODCAST_SHORT} ${num}`;
            if (guest) return `${PODCAST_SHORT} — ${guest}`;
            return `${PODCAST_SHORT} Episode`;
        }
        return t;
    }

    buildEpisodesList() {
        const map = new Map();
        [...this.data.topInsights, ...this.data.advice, ...this.data.contrarian].forEach(item => {
            if (item.episode_id && !map.has(item.episode_id)) {
                map.set(item.episode_id, {
                    id: item.episode_id,
                    title: this.buildEpisodeTitle(item),
                    guest: safe(item.guest, 'Unknown Guest'),
                    url: item.episode_url || (PODCAST_SLUG ? `https://podscripts.co/podcasts/${PODCAST_SLUG}/${item.episode_id}` : ''),
                    topics: item.topics || []
                });
            }
        });
        this.data.episodes = Array.from(map.values()).sort((a, b) => {
            const na = parseInt(a.id.match(/^(\\d+)/)?.[1] || '0');
            const nb = parseInt(b.id.match(/^(\\d+)/)?.[1] || '0');
            return nb - na;
        });
    }

    updateStats() {
        const eps = new Set();
        [...this.data.topInsights, ...this.data.advice, ...this.data.contrarian].forEach(i => { if (i.episode_id) eps.add(i.episode_id); });
        document.getElementById('statEpisodes').textContent = eps.size || this.data.episodes.length;
        document.getElementById('statGuests').textContent = this.data.guests.length;
        document.getElementById('statInsights').textContent = this.data.topInsights.length;
        document.getElementById('statAdvice').textContent = this.data.advice.length;
    }

    populateFilters() {
        const topics = Object.keys(this.data.topics.topic_counts || {}).sort();
        ['topicFilter', 'adviceTopicFilter'].forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            topics.forEach(t => { const o = document.createElement('option'); o.value = t; o.textContent = t; el.appendChild(o); });
        });
        const expEl = document.getElementById('guestExpertiseFilter');
        if (expEl && this.data.guests.length) {
            const areas = [...new Set(this.data.guests.map(g => g.expertise))].filter(e => e && e !== 'Unknown' && e !== 'Various Topics').sort();
            areas.forEach(a => { const o = document.createElement('option'); o.value = a; o.textContent = a; expEl.appendChild(o); });
        }
    }

    setupEventListeners() {
        document.querySelectorAll('.nav-link').forEach(l => l.addEventListener('click', e => { e.preventDefault(); this.switchView(e.target.dataset.view); }));
        document.getElementById('searchBtn')?.addEventListener('click', () => this.performSearch());
        document.getElementById('searchInput')?.addEventListener('keypress', e => { if (e.key === 'Enter') this.performSearch(); });
        document.getElementById('topicFilter')?.addEventListener('change', () => this.renderConsensus());
        document.getElementById('adviceTopicFilter')?.addEventListener('change', () => this.renderAdvice());
        document.getElementById('guestExpertiseFilter')?.addEventListener('change', () => this.renderGuests());
        document.getElementById('guestSearch')?.addEventListener('input', () => this.renderGuests());
        document.querySelector('.close')?.addEventListener('click', () => this.closeModal());
        window.addEventListener('click', e => { if (e.target.className === 'modal') this.closeModal(); });
    }

    switchView(v) {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.toggle('active', l.dataset.view === v));
        document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
        this.currentView = v;
        this.renderView(v);
    }

    renderView(v) {
        const el = document.getElementById(`${v}View`);
        if (el) el.classList.add('active');
        const fn = { consensus: 'renderConsensus', guests: 'renderGuests', episodes: 'renderEpisodes', topics: 'renderTopics', contrarian: 'renderContrarian', advice: 'renderAdvice' };
        if (fn[v]) this[fn[v]]();
    }

    renderConsensus() {
        const c = document.getElementById('consensusList');
        if (!this.data.consensus.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📊</div><p>No data</p></div>'; return; }
        c.innerHTML = this.data.consensus.map(item => `
            <div class="card">
                <h3 class="card-title">${safe(item.theme || item.claim, 'Unknown Theme')}</h3>
                <div class="card-meta" style="margin:10px 0;">
                    <span class="badge badge-count">${item.count || 0} mentions</span>
                    <span class="badge badge-count">${item.episode_count || 0} episodes</span>
                </div>
                ${item.guests?.length ? `<p style="margin-bottom:15px;"><strong>Discussed by:</strong> ${item.guests.slice(0,10).join(', ')}${item.guests.length > 10 ? ` +${item.guests.length-10} more` : ''}</p>` : ''}
                ${(item.insights || item.examples || []).slice(0,3).map(ex => `
                    <div style="margin-top:12px;padding:15px;background:var(--bg-dark);border-radius:10px;">
                        ${ex.quote ? `<div class="quote">"${ex.quote}"</div>` : ex.text ? `<p style="margin-bottom:8px;">${ex.text}</p>` : ''}
                        <small style="color:var(--text-secondary);">— ${safe(ex.guest,'Unknown')} (${safe(ex.episode_title,'Episode')})</small>
                    </div>
                `).join('')}
            </div>
        `).join('');
    }

    renderGuests() {
        const c = document.getElementById('guestsList');
        let guests = this.data.guests;
        const ef = document.getElementById('guestExpertiseFilter')?.value || '';
        const sq = document.getElementById('guestSearch')?.value.toLowerCase() || '';
        if (ef) guests = guests.filter(g => g.expertise === ef);
        if (sq) guests = guests.filter(g => g.name.toLowerCase().includes(sq));
        if (!guests.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state-icon">👥</div><p>No guests</p></div>'; return; }
        c.innerHTML = guests.map(g => `
            <div class="guest-card">
                <h3 class="guest-name">${safe(g.name,'Unknown')}</h3>
                <div class="guest-stats">
                    <span class="badge badge-count">${g.episode_count} episode${g.episode_count!==1?'s':''}</span>
                    <span class="guest-stat">${g.insights_count||0} insights</span>
                    <span class="guest-stat">${g.advice_count||0} advice</span>
                    ${g.expertise && g.expertise !== 'Unknown' && g.expertise !== 'Various Topics' ? `<span class="badge badge-topic">${g.expertise}</span>` : ''}
                </div>
                ${g.topics?.length ? `<div style="margin-top:12px;">${g.topics.slice(0,5).map(t=>`<span class="badge badge-topic">${t}</span>`).join('')}</div>` : ''}
                <details style="margin-top:12px;">
                    <summary style="cursor:pointer;color:var(--primary);">View Episodes (${g.episode_count})</summary>
                    <div style="margin-top:8px;">${g.episodes.map(ep => ep.url ? `<a href="${ep.url}" target="_blank" class="guest-episode-link">${safe(ep.title,'Episode')}</a>` : `<div class="guest-episode-link" style="cursor:default;">${safe(ep.title,'Episode')}</div>`).join('')}</div>
                </details>
            </div>
        `).join('');
    }

    renderEpisodes() {
        const c = document.getElementById('episodesList');
        if (!this.data.episodes.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🎙️</div><p>No episodes</p></div>'; return; }
        c.innerHTML = this.data.episodes.map(ep => `
            <div class="card">
                <h3 class="card-title">${safe(ep.title,'Episode')}</h3>
                <div class="card-meta">
                    <p><strong>Guest:</strong> ${safe(ep.guest,'Unknown')}</p>
                    ${ep.url ? `<p style="margin-top:5px;"><a href="${ep.url}" target="_blank" style="color:var(--primary);text-decoration:none;">View Transcript →</a></p>` : ''}
                    ${ep.topics?.length ? `<div style="margin-top:8px;">${ep.topics.map(t=>`<span class="badge badge-topic">${t}</span>`).join('')}</div>` : ''}
                </div>
            </div>
        `).join('');
    }

    renderTopics() {
        const c = document.getElementById('topicsList');
        const t = this.data.topics.topic_counts || {};
        if (!Object.keys(t).length) { c.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🏷️</div><p>No topics</p></div>'; return; }
        c.innerHTML = Object.entries(t).sort((a,b)=>b[1]-a[1]).map(([topic,count]) => `
            <div class="topic-card" onclick="app.showTopicDetails('${topic.replace(/'/g,"\\\\'")}')">
                <div class="topic-card-title">${topic}</div>
                <div class="topic-card-count">${count} episodes</div>
            </div>
        `).join('');
    }

    renderContrarian() {
        const c = document.getElementById('contrarianList');
        if (!this.data.contrarian.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💡</div><p>No data</p></div>'; return; }
        c.innerHTML = this.data.contrarian.map(item => `
            <div class="card"><div class="card-body">
                <p style="font-size:1.1rem;margin-bottom:12px;">${safe(item.claim,'')}</p>
                <div class="card-meta">
                    <p><strong>${safe(item.guest,'Unknown')}</strong></p>
                    <p style="color:var(--text-secondary);font-size:0.9rem;">${safe(item.episode_title,'Episode')}</p>
                </div>
            </div></div>
        `).join('');
    }

    renderAdvice() {
        const c = document.getElementById('adviceList');
        const tf = document.getElementById('adviceTopicFilter')?.value || '';
        let items = this.data.advice;
        if (tf) items = items.filter(i => i.topics?.includes(tf));
        if (!items.length) { c.innerHTML = '<div class="empty-state"><div class="empty-state-icon">✅</div><p>No advice</p></div>'; return; }
        c.innerHTML = items.map(item => `
            <div class="card"><div class="card-body">
                <h3 class="card-title" style="font-size:1.1rem;">${safe(item.advice,'')}</h3>
                ${item.how_to ? `<p style="color:var(--text-secondary);margin:10px 0;"><strong>How:</strong> ${item.how_to}</p>` : ''}
                <div class="card-meta">
                    <p><strong>${safe(item.guest,'Unknown')}</strong></p>
                    <p style="font-size:0.85rem;">${safe(item.episode_title,'Episode')}</p>
                    ${item.topics?.length ? `<div style="margin-top:8px;">${item.topics.map(t=>`<span class="badge badge-topic">${t}</span>`).join('')}</div>` : ''}
                </div>
            </div></div>
        `).join('');
    }

    performSearch() {
        const q = document.getElementById('searchInput').value.toLowerCase().trim();
        if (!q) return;
        const results = [];
        this.data.topInsights.forEach(i => { if ((i.insight||'').toLowerCase().includes(q) || (i.quote||'').toLowerCase().includes(q) || (i.guest||'').toLowerCase().includes(q)) results.push({type:'insight',data:i}); });
        this.data.advice.forEach(i => { if ((i.advice||'').toLowerCase().includes(q) || (i.how_to||'').toLowerCase().includes(q)) results.push({type:'advice',data:i}); });
        this.data.guests.forEach(g => { if (g.name.toLowerCase().includes(q)) results.push({type:'guest',data:g}); });
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const sv = document.getElementById('searchView');
        sv.classList.add('active');
        const c = document.getElementById('searchResults');
        if (!results.length) { c.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No results for "${q}"</p></div>`; return; }
        c.innerHTML = `<p style="color:var(--text-secondary);margin-bottom:20px;">${results.length} result(s) for "${q}"</p>` + results.slice(0,50).map(r => {
            if (r.type==='insight') return `<div class="card"><p>${safe(r.data.insight,'')}</p>${r.data.quote?`<div class="quote">"${r.data.quote}"</div>`:''}<div class="card-meta"><p><strong>${safe(r.data.guest,'Unknown')}</strong></p></div></div>`;
            if (r.type==='advice') return `<div class="card"><h3 class="card-title">${safe(r.data.advice,'')}</h3>${r.data.how_to?`<p style="color:var(--text-secondary);">${r.data.how_to}</p>`:''}<div class="card-meta"><p><strong>${safe(r.data.guest,'Unknown')}</strong></p></div></div>`;
            if (r.type==='guest') return `<div class="card"><h3 class="card-title">${r.data.name}</h3><div class="card-meta"><p>${r.data.episode_count} episodes • ${r.data.insights_count||0} insights</p></div></div>`;
            return '';
        }).join('');
    }

    showTopicDetails(topic) {
        const eps = this.data.topics.topic_episodes?.[topic] || [];
        const m = document.getElementById('insightModal');
        document.getElementById('modalBody').innerHTML = `
            <h2 style="margin-bottom:20px;">${topic}</h2>
            <p style="color:var(--text-secondary);margin-bottom:20px;">${eps.length} episode(s)</p>
            ${eps.slice(0,20).map(ep => `<div style="padding:12px;background:var(--bg-dark);border-radius:8px;margin-bottom:10px;"><p style="font-weight:600;">${safe(ep.title||ep.episode_title,'Episode')}</p><p style="color:var(--text-secondary);font-size:0.9rem;">Guest: ${safe(ep.guest,'Unknown')}</p></div>`).join('')}
        `;
        m.style.display = 'block';
    }

    closeModal() { document.getElementById('insightModal').style.display = 'none'; }
}

let app;
document.addEventListener('DOMContentLoaded', () => { app = new PodcastInsights(); });
'''
    
    (DOCS_DIR / "js" / "app.js").write_text(js)
    print(f"  ✓ Generated app.js")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=None)
    args = parser.parse_args()
    config = load_config(args.config)
    build_web(config)

if __name__ == '__main__':
    main()
