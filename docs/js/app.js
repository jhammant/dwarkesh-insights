// Dwarkesh Insights Web App
const PODCAST_CONFIG = {
    searchBase: 'dwarkesh podcast',
    ytChannel: '@DwarkeshPatel',
    spotifyShow: '6gFhKJwNahElu2iFRSpAWK',
    podcastName: 'The Dwarkesh Podcast'
};

function episodeLinks(title, guest, episodeId) {
    const q = encodeURIComponent((guest || '') + ' ' + PODCAST_CONFIG.searchBase);
    return `<a href="https://www.youtube.com/${PODCAST_CONFIG.ytChannel}/search?query=${encodeURIComponent(guest || title || '')}" target="_blank" title="Search on YouTube" style="text-decoration:none;">🔍</a> <a href="https://open.spotify.com/show/${PODCAST_CONFIG.spotifyShow}" target="_blank" title="Spotify" style="text-decoration:none;">🎧</a>`;
}

const PAGE_SIZE = 50;

class PodcastInsights {
    constructor() {
        this.data = { consensus: [], episodes: [], topics: {}, contrarian: [], advice: [], topInsights: [], guests: [] };
        this.currentView = 'consensus';
        this.pages = {};
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
            this.data.consensus = consensus;
            this.data.advice = advice;
            this.data.contrarian = contrarian;
            this.data.topics = topics;
            this.data.topInsights = topInsights;
            this.data.guests = guests;
            this.buildEpisodesList();
            this.populateFilters();
            this.updateStats();
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }

    buildEpisodesList() {
        const episodesMap = new Map();
        [...this.data.topInsights, ...this.data.advice, ...this.data.contrarian].forEach(item => {
            if (item.episode_id && !episodesMap.has(item.episode_id)) {
                episodesMap.set(item.episode_id, {
                    id: item.episode_id,
                    title: item.episode_title || item.episode_id,
                    guest: item.guest || '',
                    topics: item.topics || []
                });
            }
        });
        this.data.episodes = Array.from(episodesMap.values());
    }

    updateStats() {
        const uniqueEpisodes = new Set();
        [...this.data.topInsights, ...this.data.advice, ...this.data.contrarian].forEach(item => {
            if (item.episode_id) uniqueEpisodes.add(item.episode_id);
        });
        document.getElementById('statEpisodes').textContent = uniqueEpisodes.size || this.data.episodes.length;
        document.getElementById('statGuests').textContent = this.data.guests.length;
        document.getElementById('statInsights').textContent = this.data.topInsights.length;
        document.getElementById('statAdvice').textContent = this.data.advice.length;
    }

    populateFilters() {
        const topicSelect = document.getElementById('topicFilter');
        const adviceTopicSelect = document.getElementById('adviceTopicFilter');
        const allTopics = Object.keys(this.data.topics.topic_counts || {}).sort();
        const topTopics = allTopics.slice(0, 100);
        topTopics.forEach(topic => {
            [topicSelect, adviceTopicSelect].forEach(sel => {
                if (sel) {
                    const opt = document.createElement('option');
                    opt.value = topic;
                    opt.textContent = topic;
                    sel.appendChild(opt);
                }
            });
        });
        const guestExpertiseSelect = document.getElementById('guestExpertiseFilter');
        if (guestExpertiseSelect && this.data.guests.length > 0) {
            const areas = [...new Set(this.data.guests.map(g => g.expertise))].filter(e => e && e !== 'Unknown').sort();
            areas.slice(0, 50).forEach(exp => {
                const opt = document.createElement('option');
                opt.value = exp;
                opt.textContent = exp.length > 60 ? exp.slice(0, 57) + '...' : exp;
                guestExpertiseSelect.appendChild(opt);
            });
        }
    }

    setupEventListeners() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchView(e.target.dataset.view);
            });
        });
        document.getElementById('searchBtn').addEventListener('click', () => this.performSearch());
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        document.getElementById('topicFilter')?.addEventListener('change', () => this.renderEpisodes());
        document.getElementById('adviceTopicFilter')?.addEventListener('change', () => this.renderAdvice());
        document.getElementById('guestExpertiseFilter')?.addEventListener('change', () => this.renderGuests());
        document.getElementById('guestSearch')?.addEventListener('input', () => this.renderGuests());
        document.querySelector('.close').addEventListener('click', () => this.closeModal());
        window.addEventListener('click', (e) => { if (e.target.className === 'modal') this.closeModal(); });
    }

    switchView(viewName) {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.view === viewName);
        });
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        this.currentView = viewName;
        this.renderView(viewName);
    }

    renderView(viewName) {
        const el = document.getElementById(`${viewName}View`);
        if (el) el.classList.add('active');
        switch (viewName) {
            case 'consensus': this.renderConsensus(); break;
            case 'guests': this.renderGuests(); break;
            case 'episodes': this.renderEpisodes(); break;
            case 'topics': this.renderTopics(); break;
            case 'contrarian': this.renderContrarian(); break;
            case 'advice': this.renderAdvice(); break;
        }
    }

    paginate(items, view) {
        const page = this.pages[view] || 0;
        const start = page * PAGE_SIZE;
        const paged = items.slice(start, start + PAGE_SIZE);
        const totalPages = Math.ceil(items.length / PAGE_SIZE);
        let paginationHtml = '';
        if (totalPages > 1) {
            paginationHtml = `<div class="pagination">
                <button onclick="app.setPage('${view}', ${page - 1})" ${page === 0 ? 'disabled' : ''}>← Prev</button>
                <span style="padding:10px;color:var(--text-secondary);">Page ${page + 1} of ${totalPages} (${items.length} total)</span>
                <button onclick="app.setPage('${view}', ${page + 1})" ${page >= totalPages - 1 ? 'disabled' : ''}>Next →</button>
            </div>`;
        }
        return { items: paged, paginationHtml };
    }

    setPage(view, page) {
        this.pages[view] = Math.max(0, page);
        this.renderView(view);
        window.scrollTo({ top: 200, behavior: 'smooth' });
    }

    renderConsensus() {
        const container = document.getElementById('consensusList');
        if (this.data.consensus.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📊</div><p>No consensus data available yet</p></div>';
            return;
        }
        const { items, paginationHtml } = this.paginate(this.data.consensus, 'consensus');
        container.innerHTML = items.map(item => {
            const claim = item.claim || item.canonical_claim || item.theme || 'Untitled';
            const guestCount = item.guest_count || (item.guests && item.guests.length) || item.count || 0;
            const epCount = item.episode_count || 0;
            const guests = item.guests || [];
            const examples = item.examples || item.insights || [];
            const topics = item.topics || [];
            return `<div class="card">
                <div class="card-header">
                    <div style="flex:1;">
                        <h3 class="card-title">${claim}</h3>
                        <div class="card-meta" style="margin-top:10px;">
                            <span class="badge badge-count">${guestCount} guest${guestCount !== 1 ? 's' : ''} agree</span>
                            ${epCount ? `<span class="badge badge-count">${epCount} episode${epCount !== 1 ? 's' : ''}</span>` : ''}
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    ${guests.length > 0 ? `<p style="margin-bottom:15px;"><strong>Validated by:</strong> ${guests.slice(0, 10).join(', ')}${guests.length > 10 ? ' +' + (guests.length - 10) + ' more' : ''}</p>` : ''}
                    ${topics.length > 0 ? `<div style="margin-bottom:15px;">${topics.map(t => `<span class="badge badge-topic">${t}</span>`).join('')}</div>` : ''}
                    ${examples.length > 0 ? `<div class="insights-preview"><strong style="color:var(--text-secondary);font-size:0.9rem;">Key Insights:</strong>${examples.slice(0, 3).map(ex => `
                        <div style="margin-top:15px;padding:15px;background:var(--bg-hover);border-radius:10px;">
                            ${ex.text || ex.original ? `<p style="margin-bottom:8px;">${ex.text || ex.original}</p>` : ''}
                            ${ex.quote ? `<div class="quote">"${ex.quote}"</div>` : ''}
                            <small style="color:var(--text-secondary);">— ${ex.guest} ${episodeLinks(ex.episode_title, ex.guest, ex.episode_id)}</small>
                        </div>
                    `).join('')}</div>` : ''}
                </div>
            </div>`;
        }).join('') + paginationHtml;
    }

    renderGuests() {
        const container = document.getElementById('guestsList');
        if (this.data.guests.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">👥</div><p>No guests data available</p></div>';
            return;
        }
        const expertiseFilter = document.getElementById('guestExpertiseFilter')?.value || '';
        const searchQuery = document.getElementById('guestSearch')?.value.toLowerCase() || '';
        let filtered = this.data.guests;
        if (expertiseFilter) filtered = filtered.filter(g => g.expertise === expertiseFilter);
        if (searchQuery) filtered = filtered.filter(g => g.name.toLowerCase().includes(searchQuery));
        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No guests match your filters</p></div>';
            return;
        }
        const { items, paginationHtml } = this.paginate(filtered, 'guests');
        container.innerHTML = items.map(guest => `
            <div class="guest-card">
                <h3 class="guest-name">${guest.name}</h3>
                <div class="guest-stats">
                    <span class="badge badge-count">${guest.episode_count} episode${guest.episode_count !== 1 ? 's' : ''}</span>
                    <span class="guest-stat">${guest.insights_count} insights</span>
                    <span class="guest-stat">${guest.advice_count} advice</span>
                    ${guest.expertise && guest.expertise !== 'Unknown' ? `<span class="badge badge-topic">${guest.expertise.length > 50 ? guest.expertise.slice(0, 47) + '...' : guest.expertise}</span>` : ''}
                </div>
                ${guest.topics && guest.topics.length > 0 ? `<div style="margin-top:15px;"><strong style="color:var(--text-secondary);font-size:0.9rem;">Topics:</strong> ${guest.topics.slice(0, 5).map(t => `<span class="badge badge-topic">${t}</span>`).join('')}</div>` : ''}
                <div class="guest-episodes">
                    <details>
                        <summary style="cursor:pointer;color:var(--accent-primary);margin-top:15px;">View Episodes (${guest.episode_count})</summary>
                        <div style="margin-top:10px;">
                            ${guest.episodes.map(ep => `<div class="guest-episode-link" style="display:flex;align-items:center;gap:8px;"><span style="flex:1;">${ep.title || ep.id}</span>${episodeLinks(ep.title, guest.name, ep.id)}</div>`).join('')}
                        </div>
                    </details>
                </div>
            </div>
        `).join('') + paginationHtml;
    }

    renderEpisodes() {
        const container = document.getElementById('episodesList');
        const topicFilter = document.getElementById('topicFilter')?.value || '';
        let filtered = this.data.episodes;
        if (topicFilter) filtered = filtered.filter(ep => ep.topics && ep.topics.includes(topicFilter));
        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🎙️</div><p>No episodes available</p></div>';
            return;
        }
        const { items, paginationHtml } = this.paginate(filtered, 'episodes');
        container.innerHTML = items.map(ep => `
            <div class="card">
                <h3 class="card-title">${ep.title || ep.id} ${episodeLinks(ep.title, ep.guest, ep.id)}</h3>
                <div class="card-meta">
                    <p><strong>Guest:</strong> ${ep.guest || 'N/A'}</p>
                    ${ep.topics && ep.topics.length > 0 ? `<div style="margin-top:10px;">${ep.topics.slice(0, 5).map(t => `<span class="badge badge-topic">${t}</span>`).join('')}</div>` : ''}
                </div>
            </div>
        `).join('') + paginationHtml;
    }

    renderTopics() {
        const container = document.getElementById('topicsList');
        const topics = this.data.topics.topic_counts || {};
        if (Object.keys(topics).length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🏷️</div><p>No topics available</p></div>';
            return;
        }
        const sorted = Object.entries(topics).sort((a, b) => b[1] - a[1]).slice(0, 100);
        container.innerHTML = sorted.map(([topic, count]) => `
            <div class="topic-card" onclick="app.showTopicDetails('${topic.replace(/'/g, "\\'")}')">
                <div class="topic-card-title">${topic}</div>
                <div class="topic-card-count">${count} episode${count !== 1 ? 's' : ''}</div>
            </div>
        `).join('');
    }

    renderContrarian() {
        const container = document.getElementById('contrarianList');
        if (this.data.contrarian.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💡</div><p>No contrarian views available</p></div>';
            return;
        }
        const { items, paginationHtml } = this.paginate(this.data.contrarian, 'contrarian');
        container.innerHTML = items.map(item => `
            <div class="card">
                <div class="card-body">
                    <p style="font-size:1.1rem;margin-bottom:15px;">${item.claim}</p>
                    ${item.context ? `<p style="color:var(--text-secondary);font-size:0.9rem;margin-bottom:15px;font-style:italic;">${item.context}</p>` : ''}
                    <div class="card-meta">
                        <p><strong>${item.guest}</strong></p>
                        <p style="color:var(--text-secondary);font-size:0.9rem;">${item.episode_title || ''} ${episodeLinks(item.episode_title, item.guest, item.episode_id)}</p>
                    </div>
                </div>
            </div>
        `).join('') + paginationHtml;
    }

    renderAdvice() {
        const container = document.getElementById('adviceList');
        const topicFilter = document.getElementById('adviceTopicFilter')?.value || '';
        let filtered = this.data.advice;
        if (topicFilter) filtered = filtered.filter(item => item.topics && item.topics.includes(topicFilter));
        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">✅</div><p>No advice available</p></div>';
            return;
        }
        const { items, paginationHtml } = this.paginate(filtered, 'advice');
        container.innerHTML = items.map(item => `
            <div class="card">
                <div class="card-body">
                    <h3 class="card-title" style="font-size:1.1rem;">${item.advice}</h3>
                    ${item.how_to ? `<p style="color:var(--text-secondary);margin:15px 0;"><strong>How:</strong> ${item.how_to}</p>` : ''}
                    <div class="card-meta">
                        ${item.guests && item.guests.length > 0 ? `<p><strong>Endorsed by:</strong> ${item.guests.slice(0, 5).join(', ')}</p>` : item.guest ? `<p><strong>${item.guest}</strong></p>` : ''}
                        ${item.episode_title ? `<p style="font-size:0.85rem;margin-top:5px;">${item.episode_title} ${episodeLinks(item.episode_title, item.guest, item.episode_id)}</p>` : ''}
                        ${item.topics && item.topics.length > 0 ? `<div style="margin-top:10px;">${item.topics.slice(0, 5).map(t => `<span class="badge badge-topic">${t}</span>`).join('')}</div>` : ''}
                    </div>
                </div>
            </div>
        `).join('') + paginationHtml;
    }

    performSearch() {
        const query = document.getElementById('searchInput').value.toLowerCase().trim();
        if (!query) return;
        const results = [];
        this.data.topInsights.forEach(item => {
            if ((item.insight && item.insight.toLowerCase().includes(query)) ||
                (item.quote && item.quote.toLowerCase().includes(query)) ||
                (item.guest && item.guest.toLowerCase().includes(query))) {
                results.push({ type: 'insight', data: item });
            }
        });
        this.data.advice.forEach(item => {
            if ((item.advice && item.advice.toLowerCase().includes(query)) ||
                (item.how_to && item.how_to.toLowerCase().includes(query)) ||
                (item.guest && item.guest.toLowerCase().includes(query))) {
                results.push({ type: 'advice', data: item });
            }
        });
        this.displaySearchResults(results.slice(0, 100), query);
    }

    displaySearchResults(results, query) {
        const container = document.getElementById('searchResults');
        const searchView = document.getElementById('searchView');
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        searchView.classList.add('active');
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        if (results.length === 0) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No results found for "${query}"</p></div>`;
            return;
        }
        container.innerHTML = `<p style="color:var(--text-secondary);margin-bottom:20px;">Found ${results.length} result(s) for "${query}"</p>` +
            results.map(result => {
                if (result.type === 'insight') {
                    return `<div class="card">
                        <p style="font-size:1.1rem;margin-bottom:10px;">${result.data.insight}</p>
                        ${result.data.quote ? `<div class="quote">"${result.data.quote}"</div>` : ''}
                        <div class="card-meta">
                            <p><strong>${result.data.guest}</strong></p>
                            <p style="font-size:0.85rem;">${result.data.episode_title || ''} ${episodeLinks(result.data.episode_title, result.data.guest, result.data.episode_id)}</p>
                        </div>
                    </div>`;
                } else {
                    return `<div class="card">
                        <h3 class="card-title" style="font-size:1.1rem;">${result.data.advice}</h3>
                        ${result.data.how_to ? `<p style="color:var(--text-secondary);">${result.data.how_to}</p>` : ''}
                        <div class="card-meta">
                            <p><strong>${result.data.guest || ''}</strong></p>
                            ${result.data.episode_title ? `<p style="font-size:0.85rem;margin-top:5px;">${result.data.episode_title} ${episodeLinks(result.data.episode_title, result.data.guest, result.data.episode_id)}</p>` : ''}
                        </div>
                    </div>`;
                }
            }).join('');
    }

    showTopicDetails(topic) {
        const episodes = (this.data.topics.topic_episodes || {})[topic] || [];
        const modal = document.getElementById('insightModal');
        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <h2 style="margin-bottom:20px;">${topic}</h2>
            <p style="color:var(--text-secondary);margin-bottom:20px;">${episodes.length} episode(s) tagged with this topic</p>
            <div>${episodes.slice(0, 50).map(ep => `
                <div style="padding:15px;background:var(--bg-hover);border-radius:10px;margin-bottom:15px;">
                    <p style="font-weight:600;margin-bottom:5px;">${ep.title || ep.id} ${episodeLinks(ep.title, ep.guest, ep.id)}</p>
                    <p style="color:var(--text-secondary);font-size:0.9rem;">Guest: ${ep.guest}</p>
                </div>
            `).join('')}</div>
        `;
        modal.style.display = 'block';
    }

    closeModal() {
        document.getElementById('insightModal').style.display = 'none';
    }
}

let app;
document.addEventListener('DOMContentLoaded', () => { app = new PodcastInsights(); });