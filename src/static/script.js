'use strict';

const clockEl = document.getElementById('clock');
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
let routeMetadata = new Map();
let selectedRoutes = new Set();

// --- Clock Logic ---
function updateClock() {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    
    const dayName = days[now.getDay()];
    const monthName = months[now.getMonth()];
    const date = now.getDate();
    const year = now.getFullYear();
    const time = now.toTimeString().split(' ')[0];

    // Ordinal suffix logic
    let suffix = 'th';
    if (date % 10 === 1 && date !== 11) suffix = 'st';
    else if (date % 10 === 2 && date !== 12) suffix = 'nd';
    else if (date % 10 === 3 && date !== 13) suffix = 'rd';

    clockEl.textContent = `${dayName}, ${date}${suffix} of ${monthName} ${year}, ${time}`;
}

setInterval(updateClock, 1000);
updateClock();

// --- Search Logic ---
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
    
    // Build metadata map for colors
    routeMetadata.clear();
    currentDepartures.forEach(d => {
        if (!routeMetadata.has(d.route)) {
            routeMetadata.set(d.route, { color: d.color, text: d.text_color });
        }
    });

    renderRoutePills();
    renderBoard();
}

// --- Filter Logic ---
clearFilterBtn.onclick = () => {
    selectedRoutes.clear();
    renderRoutePills();
    renderBoard();
};

function renderRoutePills() {
    routePillsContainer.innerHTML = '';
    const sortedRoutes = [...routeMetadata.keys()].sort((a, b) => 
        a.localeCompare(b, undefined, {numeric: true, sensitivity: 'base'})
    );

    sortedRoutes.forEach(route => {
        const pill = document.createElement('div');
        pill.className = 'filter-pill';
        pill.textContent = route;
        
        const isSelected = selectedRoutes.has(route);
        if (isSelected) {
            const meta = routeMetadata.get(route);
            pill.style.backgroundColor = `#${meta.color}`;
            pill.style.color = `#${meta.text}`;
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

// --- Board Logic ---
function renderBoard() {
    board.innerHTML = '';
    
    const filtered = currentDepartures
        .filter(dep => selectedRoutes.size === 0 || selectedRoutes.has(dep.route))
        .sort((a, b) => a.minutes_left - b.minutes_left);

    filtered.forEach(dep => {
        const row = document.createElement('div');
        row.className = 'departure-row';
        
        const icon = TYPE_ICONS[dep.type_code] || '🚌';
        const headsignText = dep.platform !== 'N/A' ? `${dep.headsign} (Pt. ${dep.platform})` : dep.headsign;
        const waitTime = dep.minutes_left === 0 ? 'now' : `${dep.minutes_left}<span class='time-unit'>min</span>`;
        
        row.innerHTML = `
            <div class='type-icon'>${icon}</div>
            <div class='route-container'>
                <div class='route-pill' style='background-color: #${dep.color}; color: #${dep.text_color};'>
                    ${dep.route}
                </div>
            </div>
            <div class='headsign'>${headsignText}</div>
            <div class='time'>${waitTime}</div>
        `;
        board.appendChild(row);
    });
}
