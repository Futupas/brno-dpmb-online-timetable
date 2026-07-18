'use strict';

const clockEl = document.getElementById('clock');
const updateBtn = document.getElementById('updateBtn');
const stopInput = document.getElementById('stopInput');
const suggestions = document.getElementById('suggestions');
const routePillsContainer = document.getElementById('routePills');
const clearFilterBtn = document.getElementById('clearFilter');
const board = document.getElementById('board');


// Phosphor Icons - Regular weight (modern and clear)
const ICONS = {
    TRAM: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><path d='M80,216l-32,16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M176,216l32,16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M56,216H200a16,16,0,0,0,16-16V56a16,16,0,0,0-16-16H56A16,16,0,0,0,40,56V200A16,16,0,0,0,56,216Z' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='40' y1='152' x2='216' y2='152' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='128' y1='40' x2='128' y2='12' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><circle cx='84' cy='184' r='12'/><circle cx='172' cy='184' r='12'/><line x1='80' y1='88' x2='176' y2='88' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`,
    
    BUS: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><rect x='40' y='40' width='176' height='152' rx='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='40' y1='136' x2='216' y2='136' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M80,192v24a8,8,0,0,1-8,8H56a8,8,0,0,1-8-8V192' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M208,192v24a8,8,0,0,1-8,8H184a8,8,0,0,1-8-8V192' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><circle cx='80' cy='164' r='12'/><circle cx='176' cy='164' r='12'/><line x1='80' y1='80' x2='176' y2='80' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`,
    
    TROLLEYBUS: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><rect x='40' y='72' width='176' height='144' rx='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='40' y1='144' x2='216' y2='144' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='128' y1='72' x2='80' y2='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='128' y1='72' x2='176' y2='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><circle cx='80' cy='180' r='12'/><circle cx='176' cy='180' r='12'/></svg>`,
    
    TRAIN: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><path d='M12,136c0-64,48-88,116-88s116,24,116,88' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><rect x='16' y='160' width='224' height='48' rx='8' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M16,160l32-72' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M240,160l-32-72' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='104' y1='80' x2='152' y2='80' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`,
    
    OTHER: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><circle cx='128' cy='128' r='96' fill='none' stroke='currentColor' stroke-miterlimit='10' stroke-width='16'/><polyline points='92 128 116 152 164 104' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`
};


const TYPE_TO_ICON = { '0': ICONS.TRAM, '3': ICONS.BUS, '11': ICONS.TROLLEYBUS, '800': ICONS.TROLLEYBUS, '2': ICONS.TRAIN, '109': ICONS.TRAIN };

let currentDepartures = [];
let routeMetadata = new Map();
let selectedRoutes = new Set();
let lastFetchedStop = '';

function formatUpdateTime() {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const date = now.getDate();
    let suffix = 'th';
    if (date % 10 === 1 && date !== 11) suffix = 'st';
    else if (date % 10 === 2 && date !== 12) suffix = 'nd';
    else if (date % 10 === 3 && date !== 13) suffix = 'rd';
    return `Actual for: ${days[now.getDay()]}, ${date}${suffix} of ${months[now.getMonth()]} ${now.getFullYear()}, ${now.toTimeString().split(' ')[0]}`;
}

async function fetchDepartures(stopName, updateHash = true) {
    if (!stopName) return;
    const response = await fetch(`/api/departures?stop_name=${encodeURIComponent(stopName)}`);
    currentDepartures = await response.json();
    lastFetchedStop = stopName;
    clockEl.textContent = formatUpdateTime();
    updateBtn.style.display = 'inline';
    if (updateHash) window.location.hash = encodeURIComponent(stopName);
    
    routeMetadata.clear();
    currentDepartures.forEach(d => { if (!routeMetadata.has(d.route)) routeMetadata.set(d.route, { color: d.color, text: d.text_color }); });
    renderRoutePills();
    renderBoard();
}

window.addEventListener('load', () => {
    if (window.location.hash) {
        const stopName = decodeURIComponent(window.location.hash.substring(1));
        stopInput.value = stopName;
        fetchDepartures(stopName, false);
    }
});

updateBtn.onclick = (e) => {
    e.preventDefault();
    fetchDepartures(lastFetchedStop, false);
};

stopInput.addEventListener('input', () => {
    const query = stopInput.value.trim();
    if (query.length < 2) { suggestions.style.display = 'none'; return; }
    clearTimeout(window.debounceTimer);
    window.debounceTimer = setTimeout(async () => {
        const response = await fetch(`/api/stops?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        renderSuggestions(data);
    }, 300);
});

function renderSuggestions(stops) {
    suggestions.innerHTML = '';
    if (stops.length === 0) { suggestions.style.display = 'none'; return; }
    stops.forEach(stop => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.textContent = `${stop.name} (${stop.zone})`;
        div.onclick = () => {
            stopInput.value = stop.name;
            suggestions.style.display = 'none';
            selectedRoutes.clear();
            fetchDepartures(stop.name);
        };
        suggestions.appendChild(div);
    });
    suggestions.style.display = 'block';
}

clearFilterBtn.onclick = () => { selectedRoutes.clear(); renderRoutePills(); renderBoard(); };

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
            renderRoutePills();
            renderBoard();
        };
        routePillsContainer.appendChild(pill);
    });
    clearFilterBtn.style.display = selectedRoutes.size > 0 ? 'block' : 'none';
}

function renderBoard() {
    board.innerHTML = '';
    currentDepartures
        .filter(dep => selectedRoutes.size === 0 || selectedRoutes.has(dep.route))
        .sort((a, b) => a.minutes_left - b.minutes_left)
        .forEach(dep => {
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
