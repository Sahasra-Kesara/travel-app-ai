const map = L.map("tripMap").setView([7.8731, 80.7718], 7);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

const routeLayer = L.layerGroup().addTo(map);
const stopMarkers = L.layerGroup().addTo(map);

// Transport color map
const colors = {
  train: "green",
  bus: "blue",
  highway_car: "red",
  normal_car: "gray"
};

// Handle form submit
document.getElementById("tripForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  routeLayer.clearLayers();
  stopMarkers.clearLayers();
  document.getElementById("tripSteps").innerHTML = "";

  const start = document.getElementById("startCity").value.trim();
  const end = document.getElementById("endCity").value.trim();
  if (!start || !end) return alert("Enter both start and end cities");

  // Call AI trip planner
  const res = await fetch("/user/ai-trip-plan", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ start, end })
  });

  const data = await res.json();
  if (!data.success || !data.segments.length) return alert("No route found");

  let stepCounter = 1;

  data.segments.forEach((seg) => {
    const points = seg.geometry; // [[lat, lon], ...]

    // Draw segment line
    L.polyline(points, { color: colors[seg.mode], weight: 5 }).addTo(routeLayer);

    // Add markers at start and end
    [points[0], points[points.length-1]].forEach((pt, idx) => {
      const icon = L.divIcon({
        html: `<div class="bg-${colors[seg.mode]}-600 text-white w-7 h-7 flex items-center justify-center rounded-full text-sm">${stepCounter++}</div>`
      });
      L.marker(pt, {icon}).addTo(stopMarkers)
        .on("click", () => loadStopDetails(seg.from));
    });

    // Add step to sidebar
    document.getElementById("tripSteps").innerHTML += `
      <div class="p-3 bg-gray-50 rounded-xl">
        <b>Segment ${stepCounter-1}</b> (${seg.mode.replace("_"," ")})<br>
        From: ${seg.from}<br>To: ${seg.to}
      </div>
    `;
  });

  // Fit map to route
  const allPoints = data.segments.flatMap(s => s.geometry);
  const bounds = L.latLngBounds(allPoints);
  map.fitBounds(bounds, { padding: [50, 50] });
});

// Load stop details
async function loadStopDetails(name){
  const res = await fetch("/admin/route-stop-details", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ destination: name })
  });

  const data = await res.json();
  if(!data.success) return;

  scTitle.innerText = data.data.name;
  scDesc.innerText = data.data.description;
  scTime.innerText = data.data.best_time;

  document.getElementById("stopCard").classList.remove("hidden");
}

function closeStopCard(){
  document.getElementById("stopCard").classList.add("hidden");
}
