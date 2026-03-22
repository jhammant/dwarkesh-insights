// Auto-generated — Podcast Insights Web App
// Null-safe display helper
function safe(val, fallback = '') {
    if (val === null || val === undefined || val === 'null' || val === 'undefined' || val === 'N/A' || val === 'Unknown') return fallback;
    return String(val);
}

const PODCAST_SHORT = "Dwarkesh";
const PODCAST_SLUG = "dwarkesh-podcast";

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
            const match = (item.episode_id || '').match(/^(\d+)/);
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
            const na = parseInt(a.id.match(/^(\d+)/)?.[1] || '0');
            const nb = parseInt(b.id.match(/^(\d+)/)?.[1] || '0');
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
            <div class="topic-card" onclick="app.showTopicDetails('${topic.replace(/'/g,"\\'")}')">
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
