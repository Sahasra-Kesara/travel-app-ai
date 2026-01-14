let map = L.map('tripMap').setView([7.8731, 80.7718], 7); // Sri Lanka
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let routeLayers = [];

// Draw a segment on map
function drawSegment(coords, mode) {
    if(!coords || coords.length === 0) return;
    let color = "#007bff"; // default blue
    if(mode === "train") color = "#28a745";
    if(mode === "bus") color = "#ffc107";
    if(mode === "highway_car") color = "#dc3545";

    let polyline = L.polyline(coords.map(c => [c[1], c[0]]), {
        color: color,
        weight: 5,
        opacity: 0.8,
        dashArray: mode === "bus" ? '10, 10' : null
    }).addTo(map);

    routeLayers.push(polyline);
    map.fitBounds(polyline.getBounds());
}

function clearRoutes() {
    routeLayers.forEach(l => map.removeLayer(l));
    routeLayers = [];
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

    for(let seg of data.segments) {
        drawSegment(seg.geometry, seg.mode);

        let stepDiv = document.createElement('div');
        stepDiv.classList.add('p-2', 'border', 'rounded-xl', 'bg-gray-50', 'cursor-pointer');
        stepDiv.innerHTML = `<strong>${seg.mode.toUpperCase()}:</strong> ${seg.from} → ${seg.to}`;
        tripStepsDiv.appendChild(stepDiv);
    }
});
