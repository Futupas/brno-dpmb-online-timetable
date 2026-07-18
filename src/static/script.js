'use strict';

const stopInput = document.getElementById('stopInput');
const suggestions = document.getElementById('suggestions');
const routePillsContainer = document.getElementById('routePills');
const clearFilterBtn = document.getElementById('clearFilter');
const board = document.getElementById('board');

const TYPE_ICONS = {
    '0': '🚋',
    '3': '🚌',
    '11': '🚎',
    '800': '🚎',
    '2': '🚆',
    '109': '🚆'
};

let debounceTimer;
let currentDepartures = [];
let selectedRoutes = new Set();

stopInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const query = stopInput.value.trim();
    if (query.length < 2) {
        suggestions.style.display = 'none';
        return;
    }
    debounceTimer = setTimeout(async () => {
        const response = await fetch(`/api/stops?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        renderSuggestions(data);
    }, 300);
});

clearFilterBtn.onclick = () => {
    selectedRoutes.clear();
    renderRoutePills();
    renderBoard();
};

function renderSuggestions(stops) {
    suggestions.innerHTML = '';
    if (stops.length === 0) {
        suggestions.style.display = 'none';
        return;
    }
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

async function fetchDepartures(stopName) {
    const response = await fetch(`/api/departures?stop_name=${encodeURIComponent(stopName)}`);
    currentDepartures = await response.json();
    renderRoutePills();
    renderBoard();
}

function renderRoutePills() {
    routePillsContainer.innerHTML = '';
    
    // Extract unique route names from departures
    const routes = [...new Set(currentDepartures.map(d => d.route))].sort((a, b) => {
        return a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'});
    });

    routes.forEach(route => {
        const pill = document.createElement('div');
        pill.className = `filter-pill ${selectedRoutes.has(route) ? 'active' : ''}`;
        pill.textContent = route;
        pill.onclick = () => {
            if (selectedRoutes.has(route)) {
                selectedRoutes.delete(route);
            } else {
                selectedRoutes.add(route);
            }
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
        .filter(dep => {
            if (selectedRoutes.size === 0) return true;
            return selectedRoutes.has(dep.route);
        })
        .sort((a, b) => a.minutes_left - b.minutes_left);

    filtered.forEach(dep => {
        const row = document.createElement('div');
        row.className = 'departure-row';
        
        const icon = TYPE_ICONS[dep.type_code] || '🚌';
        const platformHtml = dep.platform !== 'N/A' ? `<div class='platform-label'>P: ${dep.platform}</div>` : '';
        const waitTime = dep.minutes_left === 0 ? 'now' : `${dep.minutes_left}<span class='time-unit'>min</span>`;
        
        row.innerHTML = `
            <div class='type-icon'>${icon}</div>
            <div class='route-container'>
                <div class='route-pill' style='background-color: #${dep.color}; color: #${dep.text_color};'>
                    ${dep.route}
                </div>
                ${platformHtml}
            </div>
            <div class='headsign'>${dep.headsign}</div>
            <div class='time'>${waitTime}</div>
        `;
        board.appendChild(row);
    });
}
