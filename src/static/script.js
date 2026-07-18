'use strict';

const clockEl = document.getElementById('clock');
const stopInput = document.getElementById('stopInput');
const suggestions = document.getElementById('suggestions');
const routePillsContainer = document.getElementById('routePills');
const clearFilterBtn = document.getElementById('clearFilter');
const board = document.getElementById('board');

// Phosphor Icons - Regular weight (modern and clear)
// const ICONS = {
//     TRAM: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><path d='M80,216l-32,16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M176,216l32,16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M56,216H200a16,16,0,0,0,16-16V56a16,16,0,0,0-16-16H56A16,16,0,0,0,40,56V200A16,16,0,0,0,56,216Z' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='40' y1='152' x2='216' y2='152' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='128' y1='40' x2='128' y2='12' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><circle cx='84' cy='184' r='12'/><circle cx='172' cy='184' r='12'/><line x1='80' y1='88' x2='176' y2='88' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`,
    
//     BUS: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><rect x='40' y='40' width='176' height='152' rx='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='40' y1='136' x2='216' y2='136' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M80,192v24a8,8,0,0,1-8,8H56a8,8,0,0,1-8-8V192' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M208,192v24a8,8,0,0,1-8,8H184a8,8,0,0,1-8-8V192' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><circle cx='80' cy='164' r='12'/><circle cx='176' cy='164' r='12'/><line x1='80' y1='80' x2='176' y2='80' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`,
    
//     TROLLEYBUS: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><rect x='40' y='72' width='176' height='144' rx='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='40' y1='144' x2='216' y2='144' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='128' y1='72' x2='80' y2='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='128' y1='72' x2='176' y2='16' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><circle cx='80' cy='180' r='12'/><circle cx='176' cy='180' r='12'/></svg>`,
    
//     TRAIN: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><path d='M12,136c0-64,48-88,116-88s116,24,116,88' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><rect x='16' y='160' width='224' height='48' rx='8' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M16,160l32-72' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><path d='M240,160l-32-72' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/><line x1='104' y1='80' x2='152' y2='80' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`,
    
//     OTHER: `<svg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'><rect width='256' height='256' fill='none'/><circle cx='128' cy='128' r='96' fill='none' stroke='currentColor' stroke-miterlimit='10' stroke-width='16'/><polyline points='92 128 116 152 164 104' fill='none' stroke='currentColor' stroke-linecap='round' stroke-linejoin='round' stroke-width='16'/></svg>`
// };

// From https://icon-sets.iconify.design/
const ICONS = {
    TRAM: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none" /><path fill="currentColor" d="M4 17.5V8q0-2.425 2.125-3.175T11 4l.75-1.5H7V1h10v1.5h-3.25L13 4q2.975.075 4.988.813T20 8v9.5q0 1.475-1.012 2.488T16.5 21l1.5 1.5v.5h-2l-2-2h-4l-2 2H6v-.5L7.5 21q-1.475 0-2.488-1.012T4 17.5M16.5 14H6h12zm-3.437 3.563q.437-.438.437-1.063t-.437-1.062T12 15t-1.062.438T10.5 16.5t.438 1.063T12 18t1.063-.437M11.95 7h5.7H6.4zM6 12h12V9H6zm1.5 7h9q.65 0 1.075-.425T18 17.5V14H6v3.5q0 .65.425 1.075T7.5 19m4.45-13q-3.35 0-4.3.363T6.4 7h11.25q-.3-.35-1.3-.675T11.95 6" /></svg>`,
    
    BUS: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none" /><path fill="currentColor" fill-rule="evenodd" d="M11.944 1.25h.112c1.838 0 3.294 0 4.433.153c1.172.158 2.121.49 2.87 1.238c.748.749 1.08 1.698 1.238 2.87c.103.764.136 1.67.147 2.739H21c.966 0 1.75.784 1.75 1.75v1c0 .55-.26 1.07-.7 1.4l-1.303.977c-.007 1.232-.036 2.26-.15 3.112c-.158 1.172-.49 2.121-1.238 2.87q-.285.284-.609.493V21A1.75 1.75 0 0 1 17 22.75h-1.5A1.75 1.75 0 0 1 13.75 21v-.256q-.786.007-1.694.006h-.112q-.909.002-1.694-.006V21a1.75 1.75 0 0 1-1.75 1.75H7A1.75 1.75 0 0 1 5.25 21v-1.148a3.7 3.7 0 0 1-.609-.493c-.748-.749-1.08-1.698-1.238-2.87c-.114-.852-.143-1.88-.15-3.112L1.95 12.4c-.44-.33-.7-.85-.7-1.4v-1c0-.966.784-1.75 1.75-1.75h.255c.012-1.069.045-1.975.148-2.739c.158-1.172.49-2.121 1.238-2.87c.749-.748 1.698-1.08 2.87-1.238c1.14-.153 2.595-.153 4.433-.153M3.25 9.75H3a.25.25 0 0 0-.25.25v1a.25.25 0 0 0 .1.2l.4.3zm1.506 4c.01 1.034.042 1.858.134 2.54c.135 1.005.389 1.585.812 2.008s1.003.677 2.009.812c1.028.138 2.382.14 4.289.14s3.262-.002 4.29-.14c1.005-.135 1.585-.389 2.008-.812s.677-1.003.812-2.009c.092-.68.123-1.505.134-2.539zm14.494-1.5H4.75V10c0-1.883.002-3.227.135-4.25h14.23c.133 1.023.135 2.367.135 4.25zm1.5-.75l.4-.3a.25.25 0 0 0 .1-.2v-1a.25.25 0 0 0-.25-.25h-.25zm-2.049-7.25a2.3 2.3 0 0 0-.403-.548c-.423-.423-1.003-.677-2.009-.812c-1.028-.138-2.382-.14-4.289-.14s-3.261.002-4.29.14c-1.005.135-1.585.389-2.008.812a2.3 2.3 0 0 0-.403.548zM6.75 20.46V21c0 .138.112.25.25.25h1.5a.25.25 0 0 0 .25-.25v-.296a15 15 0 0 1-1.239-.107a8 8 0 0 1-.761-.137m8.5.244V21c0 .138.112.25.25.25H17a.25.25 0 0 0 .25-.25v-.54q-.363.084-.761.137a15 15 0 0 1-1.239.107M6.25 16a.75.75 0 0 1 .75-.75h1.5a.75.75 0 0 1 0 1.5H7a.75.75 0 0 1-.75-.75m8.5 0a.75.75 0 0 1 .75-.75H17a.75.75 0 0 1 0 1.5h-1.5a.75.75 0 0 1-.75-.75" clip-rule="evenodd" /></svg>`,
    
    TROLLEYBUS: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 16 16"><path d="M0 0h16v16H0z" fill="none" /><path fill="currentColor" d="M8 1a.5.5 0 0 0-.45.283l-.888 1.776A1 1 0 0 0 6 4H5a2 2 0 0 0-2 2v8.5a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5V14h6v.5a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5V6a2 2 0 0 0-2-2h-1a1 1 0 0 0-.323-.736l.767-1.535a.5.5 0 1 0-.894-.446L8.691 3h-.882l.635-1.271A.5.5 0 0 0 8 1M6.499 5H9.5a.5.5 0 0 1 .001 1H6.5a.5.5 0 0 1-.001-1M4 8a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v1.5a1.5 1.5 0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 4 9.5zm0 4.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 0 1h-1a.5.5 0 0 1-.5-.5m6 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 0 1h-1a.5.5 0 0 1-.5-.5" /></svg>`,
    
    TRAIN: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none" /><path fill="currentColor" d="M4 15.5V6q0-1.325.688-2.113t1.812-1.2t2.563-.55T12 2q1.65 0 3.113.138t2.55.55t1.712 1.2T20 6v9.5q0 1.475-1.012 2.488T16.5 19l1.5 1.5v.5h-2l-2-2h-4l-2 2H6v-.5L7.5 19q-1.475 0-2.488-1.012T4 15.5M12 4q-2.65 0-3.875.313T6.45 5h11.2q-.375-.425-1.612-.712T12 4m-6 6h5V7H6zm10.5 2H6h12zM13 10h5V7h-5zm-3.425 5.575Q10 15.15 10 14.5t-.425-1.075T8.5 13t-1.075.425T7 14.5t.425 1.075T8.5 16t1.075-.425m7 0Q17 15.15 17 14.5t-.425-1.075T15.5 13t-1.075.425T14 14.5t.425 1.075T15.5 16t1.075-.425M7.5 17h9q.65 0 1.075-.425T18 15.5V12H6v3.5q0 .65.425 1.075T7.5 17M12 5h5.65h-11.2z" /></svg>`,
    
    OTHER: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"></svg>`
};

const TYPE_TO_ICON = {
    '0': ICONS.TRAM,
    '3': ICONS.BUS,
    '11': ICONS.TROLLEYBUS,
    '800': ICONS.TROLLEYBUS,
    '2': ICONS.TRAIN,
    '109': ICONS.TRAIN
};

let debounceTimer;
let currentDepartures = [];
let routeMetadata = new Map();
let selectedRoutes = new Set();

function formatUpdateTime() {
    const now = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    
    const dayName = days[now.getDay()];
    const monthName = months[now.getMonth()];
    const date = now.getDate();
    const year = now.getFullYear();
    const time = now.toTimeString().split(' ')[0];

    let suffix = 'th';
    if (date % 10 === 1 && date !== 11) suffix = 'st';
    else if (date % 10 === 2 && date !== 12) suffix = 'nd';
    else if (date % 10 === 3 && date !== 13) suffix = 'rd';

    return `Actual for: ${dayName}, ${date}${suffix} of ${monthName} ${year}, ${time}`;
}

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
    
    // Update clock only when data is fetched
    clockEl.textContent = formatUpdateTime();

    routeMetadata.clear();
    currentDepartures.forEach(d => {
        if (!routeMetadata.has(d.route)) {
            routeMetadata.set(d.route, { color: d.color, text: d.text_color });
        }
    });

    renderRoutePills();
    renderBoard();
}

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
        
        if (selectedRoutes.has(route)) {
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

function renderBoard() {
    board.innerHTML = '';
    
    const filtered = currentDepartures
        .filter(dep => selectedRoutes.size === 0 || selectedRoutes.has(dep.route))
        .sort((a, b) => a.minutes_left - b.minutes_left);

    filtered.forEach(dep => {
        const row = document.createElement('div');
        row.className = 'departure-row';
        
        const iconSvg = TYPE_TO_ICON[dep.type_code] || ICONS.OTHER;
        const headsignText = dep.platform !== 'N/A' ? `${dep.headsign} (Pt. ${dep.platform})` : dep.headsign;
        const waitTime = dep.minutes_left === 0 ? 'now' : `${dep.minutes_left}<span class='time-unit'>min</span>`;
        
        row.innerHTML = `
            <div class='type-icon'>${iconSvg}</div>
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
