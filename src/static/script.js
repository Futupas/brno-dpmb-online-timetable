const stopInput = document.getElementById('stopInput');
const suggestions = document.getElementById('suggestions');
const board = document.getElementById('board');

let debounceTimer;

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
        div.textContent = stop;
        div.onclick = () => {
            stopInput.value = stop;
            suggestions.style.display = 'none';
            fetchDepartures(stop);
        };
        suggestions.appendChild(div);
    });
    suggestions.style.display = 'block';
}

async function fetchDepartures(stopName) {
    const response = await fetch(`/api/departures?stop_name=${encodeURIComponent(stopName)}`);
    let data = await response.json();
    
    // 1. Sort by minutes_left (FE sorting as requested)
    data.sort((a, b) => a.minutes_left - b.minutes_left);
    
    // 2. Group by platform
    const groups = data.reduce((acc, dep) => {
        const p = dep.platform || 'N/A';
        if (!acc[p]) acc[p] = [];
        acc[p].push(dep);
        return acc;
    }, {});

    renderBoard(groups);
}

function renderBoard(groups) {
    board.innerHTML = '';
    
    Object.keys(groups).sort().forEach(platform => {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'platform-group';
        
        groupDiv.innerHTML = `<div class='platform-header'>Platform ${platform}</div>`;
        
        groups[platform].forEach(dep => {
            const row = document.createElement('div');
            row.className = 'departure-row';
            
            const waitTime = dep.minutes_left === 0 ? 'now' : `${dep.minutes_left}<span class='time-unit'>min</span>`;
            
            row.innerHTML = `
                <div class='route-pill' style='background-color: #${dep.color}; color: #${dep.text_color};'>
                    ${dep.route}
                </div>
                <div class='headsign'>${dep.headsign}</div>
                <div class='time'>${waitTime}</div>
            `;
            groupDiv.appendChild(row);
        });
        
        board.appendChild(groupDiv);
    });
}
