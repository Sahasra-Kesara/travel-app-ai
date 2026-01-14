let map = L.map('tripMap').setView([7.8731, 80.7718], 7); // Sri Lanka
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let routeLayers = [];
let stopMarkers = [];

function drawSegment(coords, mode, stops) {
    if (!coords || coords.length === 0) return;

    // Color by mode
    let color = {
        "normal_car": "#007bff",
        "train": "#28a745",
        "bus": "#ffc107",
        "highway_car": "#dc3545"
    }[mode] || "#000000";

    // Draw polyline
    let polyline = L.polyline(coords.map(c => [c[1], c[0]]), {
        color: color,
        weight: 5,
        opacity: 0.8,
        dashArray: mode === "bus" ? '10,10' : null
    }).addTo(map);

    routeLayers.push(polyline);

    // Draw stops as markers
    if(stops && stops.length){
        stops.forEach(stop => {
            fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(stop)}&format=json&limit=1`)
                .then(res => res.json())
                .then(data => {
                    if(data.length>0){
                        let marker = L.marker([parseFloat(data[0].lat), parseFloat(data[0].lon)])
                            .addTo(map)
                            .bindPopup(`<strong>${stop}</strong><br>${mode}`);
                        stopMarkers.push(marker);
                    }
                });
        });
    }

    map.fitBounds(polyline.getBounds());
}

function clearRoutes() {
    routeLayers.forEach(l => map.removeLayer(l));
    routeLayers = [];
    stopMarkers.forEach(m => map.removeLayer(m));
    stopMarkers = [];

    // Clear stop checkboxes
    let stopDiv = document.getElementById('stopSelection');
    if(stopDiv) stopDiv.innerHTML = '';
}

document.getElementById('tripForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    clearRoutes();

    let start = document.getElementById('startCity').value;
    let end = document.getElementById('endCity').value;

    let res = await fetch('/user/ai-trip-plan', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({start, end})
    });

    let data = await res.json();
    let tripStepsDiv = document.getElementById('tripSteps');
    tripStepsDiv.innerHTML = '';

    let stopDiv = document.getElementById('stopSelection');
    stopDiv.innerHTML = '';

    for (let seg of data.segments) {
        drawSegment(seg.geometry, seg.mode, seg.stops);

        // Populate AI suggested stops as checkboxes
        if(seg.stops && seg.stops.length){
            seg.stops.forEach(stop => {
                let cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.name = 'stops';
                cb.value = stop;
                cb.checked = true;

                let label = document.createElement('label');
                label.innerText = stop;
                label.prepend(cb);

                stopDiv.appendChild(label);
                stopDiv.appendChild(document.createElement('br'));
            });
        }

        // Create clickable step for each segment
        let stepDiv = document.createElement('div');
        stepDiv.classList.add('p-2', 'border', 'rounded-xl', 'bg-gray-50', 'cursor-pointer');
        stepDiv.innerHTML = `<strong>${seg.mode.toUpperCase()}:</strong> ${seg.from} → ${seg.to}`;
        tripStepsDiv.appendChild(stepDiv);

        // Zoom to this segment on click
        stepDiv.addEventListener('click', () => {
            if(seg.geometry.length) map.fitBounds(seg.geometry.map(c => [c[1], c[0]]));
        });
    }
});