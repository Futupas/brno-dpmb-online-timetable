'use strict';

const clockEl = document.getElementById('clock');
const updateBtn = document.getElementById('updateBtn');
const stopInput = document.getElementById('stopInput');
const favBtn = document.getElementById('favBtn');
const suggestions = document.getElementById('suggestions');
const welcomeText = document.getElementById('welcomeText');
const loadingEl = document.getElementById('loading');
const emptyStateEl = document.getElementById('emptyState');
const routePillsContainer = document.getElementById('routePills');
const clearFilterBtn = document.getElementById('clearFilter');
const board = document.getElementById('board');
const contentArea = document.getElementById('contentArea');

const ICONS = {
    TRAM: `<svg viewBox='0 0 256 256'><rect width='256' height='256' fill='none'/><path d='M80,216l-32,16' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><path d='M176,216l32,16' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><path d='M56,216H200a16,16,0,0,0,16-16V56a16,16,0,0,0-16-16H56A16,16,0,0,0,40,56V200A16,16,0,0,0,56,216Z' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><line x1='40' y1='152' x2='216' y2='152' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><line x1='128' y1='40' x2='128' y2='12' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><circle cx='84' cy='184' r='12' stroke='currentColor' /><circle cx='172' cy='184' r='12' stroke='currentColor' /><line x1='80' y1='88' x2='176' y2='88' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/></svg>`,
    BUS: `<svg viewBox='0 0 256 256'><rect width='256' height='256' fill='none'/><rect x='40' y='40' width='176' height='152' rx='16' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><line x1='40' y1='136' x2='216' y2='136' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><path d='M80,192v24a8,8,0,0,1-8,8H56a8,8,0,0,1-8-8V192' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><path d='M208,192v24a8,8,0,0,1-8,8H184a8,8,0,0,1-8-8V192' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><circle cx='80' cy='164' r='12' stroke='currentColor' /><circle cx='176' cy='164' r='12' stroke='currentColor' /><line x1='80' y1='80' x2='176' y2='80' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/></svg>`,
    TROLLEYBUS: `<svg viewBox='0 0 256 256'><rect width='256' height='256' fill='none'/><rect x='40' y='72' width='176' height='144' rx='16' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><line x1='40' y1='144' x2='216' y2='144' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><line x1='128' y1='72' x2='80' y2='16' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><line x1='128' y1='72' x2='176' y2='16' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><circle cx='80' cy='180' r='12' stroke='currentColor' /><circle cx='176' cy='180' r='12' stroke='currentColor' /></svg>`,
    TRAIN: `<svg viewBox='0 0 256 256'><rect width='256' height='256' fill='none'/><path d='M12,136c0-64,48-88,116-88s116,24,116,88' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><rect x='16' y='160' width='224' height='48' rx='8' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><path d='M16,160l32-72' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><path d='M240,160l-32-72' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/><line x1='104' y1='80' x2='152' y2='80' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/></svg>`,
    OTHER: `<svg viewBox='0 0 256 256'><circle cx='128' cy='128' r='96' stroke='currentColor' stroke-miterlimit='10' /><polyline points='92 128 116 152 164 104' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round'/></svg>`
};

const TYPE_TO_ICON = { '0': ICONS.TRAM, '3': ICONS.BUS, '11': ICONS.TROLLEYBUS, '800': ICONS.TROLLEYBUS, '2': ICONS.TRAIN, '109': ICONS.TRAIN };

let currentDepartures = [];
let routeMetadata = new Map();
let selectedRoutes = new Set();
let lastFetchedStop = '';
let suggestionData = [];
let suggestionIndex = -1;
let favorites = JSON.parse(localStorage.getItem('brno_favorites') || '[]');

function formatUpdateTime() {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const date = now.getDate();
    let suffix = 'th';
    if (date % 10 === 1 && date !== 11) suffix = 'st';
    else if (date % 10 === 2 && date !== 12) suffix = 'nd';
    else if (date % 10 === 3 && date !== 13) suffix = 'rd';
    return `Valid as of: ${days[now.getDay()]}, ${date}${suffix} of ${months[now.getMonth()]} ${now.getFullYear()}, ${now.toTimeString().split(' ')[0]}`;
}

function updateHash() {
    const stop = encodeURIComponent(lastFetchedStop);
    const routes = selectedRoutes.size > 0 ? `/${Array.from(selectedRoutes).join(',')}` : '';
    window.location.hash = stop + routes;
}

function uncenterUI() {
    contentArea.classList.remove('centered');
    welcomeText.style.display = 'none';
}

function toggleFavorite() {
    if (!lastFetchedStop) return;
    if (favorites.includes(lastFetchedStop)) {
        favorites = favorites.filter(f => f !== lastFetchedStop);
        favBtn.textContent = '☆';
        favBtn.classList.remove('active');
    } else {
        favorites.push(lastFetchedStop);
        favBtn.textContent = '★';
        favBtn.classList.add('active');
    }
    localStorage.setItem('brno_favorites', JSON.stringify(favorites));
}

favBtn.onclick = toggleFavorite;

async function fetchDepartures(stopName) {
    if (!stopName) return;
    
    uncenterUI();
    board.innerHTML = '';
    emptyStateEl.style.display = 'none';
    loadingEl.style.display = 'block';

    const response = await fetch(`/api/departures?stop_name=${encodeURIComponent(stopName)}`);
    currentDepartures = await response.json();
    
    loadingEl.style.display = 'none';
    lastFetchedStop = stopName;
    clockEl.textContent = formatUpdateTime();
    updateBtn.style.display = 'inline';
    
    favBtn.style.display = 'flex';
    if (favorites.includes(stopName)) {
        favBtn.textContent = '★';
        favBtn.classList.add('active');
    } else {
        favBtn.textContent = '☆';
        favBtn.classList.remove('active');
    }

    updateHash();
    
    routeMetadata.clear();
    currentDepartures.forEach(d => { if (!routeMetadata.has(d.route)) routeMetadata.set(d.route, { color: d.color, text: d.text_color }); });
    renderRoutePills();
    renderBoard();
}

window.addEventListener('load', () => {
    if (window.location.hash) {
        const parts = window.location.hash.substring(1).split('/');
        const stopName = decodeURIComponent(parts[0]);
        if (parts[1]) {
            parts[1].split(',').forEach(r => selectedRoutes.add(r));
        }
        stopInput.value = stopName;
        fetchDepartures(stopName);
    }
});

updateBtn.onclick = (e) => { e.preventDefault(); fetchDepartures(lastFetchedStop); };

stopInput.addEventListener('keydown', (e) => {
    if (suggestions.style.display === 'none') return;
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        suggestionIndex = Math.min(suggestionIndex + 1, suggestionData.length - 1);
        highlightSuggestion();
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        suggestionIndex = Math.max(suggestionIndex - 1, -1);
        highlightSuggestion();
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (suggestionIndex >= 0) {
            selectStop(suggestionData[suggestionIndex].name);
        }
    }
});

function highlightSuggestion() {
    const items = suggestions.querySelectorAll('.suggestion-item');
    items.forEach((item, idx) => {
        item.classList.toggle('highlighted', idx === suggestionIndex);
    });
}

function selectStop(name) {
    stopInput.value = name;
    suggestions.style.display = 'none';
    selectedRoutes.clear();
    fetchDepartures(name);
}

stopInput.addEventListener('input', () => {
    uncenterUI();
    const query = stopInput.value.trim();
    if (query.length < 2) { suggestions.style.display = 'none'; return; }
    
    clearTimeout(window.debounceTimer);
    window.debounceTimer = setTimeout(async () => {
        const response = await fetch(`/api/stops?q=${encodeURIComponent(query)}`);
        const rawStops = await response.json();
        
        // Sort favorites to the top
        suggestionData = rawStops.sort((a, b) => {
            const aFav = favorites.includes(a.name);
            const bFav = favorites.includes(b.name);
            if (aFav && !bFav) return -1;
            if (!aFav && bFav) return 1;
            return 0;
        });

        suggestionIndex = -1;
        renderSuggestions();
    }, 300);
});

function renderSuggestions() {
    suggestions.innerHTML = '';
    if (suggestionData.length === 0) { suggestions.style.display = 'none'; return; }
    suggestionData.forEach((stop) => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        
        const isFav = favorites.includes(stop.name);
        const favIcon = isFav ? `<span class="fav-indicator">★</span>` : '';
        
        div.innerHTML = `<div>${favIcon} ${stop.name} <span style="color:var(--text-muted); font-size:12px;">(${stop.zone})</span></div>`;
        div.onclick = () => selectStop(stop.name);
        suggestions.appendChild(div);
    });
    suggestions.style.display = 'block';
}

clearFilterBtn.onclick = () => { selectedRoutes.clear(); updateHash(); renderRoutePills(); renderBoard(); };

function renderRoutePills() {
    routePillsContainer.innerHTML = '';
    const sorted = [...routeMetadata.keys()].sort((a, b) => a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'}));
    sorted.forEach(route => {
        const pill = document.createElement('div');
        pill.className = 'filter-pill';
        pill.textContent = route;
        if (selectedRoutes.has(route)) {
            const m = routeMetadata.get(route);
            pill.style.backgroundColor = `#${m.color}`;
            pill.style.color = `#${m.text}`;
            pill.style.fontWeight = 'bold';
        }
        pill.onclick = () => {
            if (selectedRoutes.has(route)) selectedRoutes.delete(route);
            else selectedRoutes.add(route);
            updateHash();
            renderRoutePills();
            renderBoard();
        };
        routePillsContainer.appendChild(pill);
    });
    clearFilterBtn.style.display = selectedRoutes.size > 0 ? 'block' : 'none';
}

function renderBoard() {
    board.innerHTML = '';
    
    const filtered = currentDepartures
        .filter(dep => selectedRoutes.size === 0 || selectedRoutes.has(dep.route))
        .sort((a, b) => a.minutes_left - b.minutes_left);

    if (filtered.length === 0 && currentDepartures.length > 0) {
        emptyStateEl.style.display = 'block';
        return;
    } else {
        emptyStateEl.style.display = 'none';
    }

    filtered.forEach(dep => {
        const row = document.createElement('div');
        row.className = 'departure-row';
        const wait = dep.minutes_left === 0 ? 'now' : `${dep.minutes_left}<span class='time-unit'>min</span>`;
        row.innerHTML = `
            <div class='type-icon'>${TYPE_TO_ICON[dep.type_code] || ICONS.OTHER}</div>
            <div class='route-container'><div class='route-pill' style='background-color: #${dep.color}; color: #${dep.text_color};'>${dep.route}</div></div>
            <div class='headsign'>${dep.headsign} ${dep.platform !== 'N/A' ? `(Pt. ${dep.platform})` : ''}</div>
            <div class='time'>${wait}</div>`;
        board.appendChild(row);
    });
}
