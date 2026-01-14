const map = L.map("tripMap").setView([7.8731, 80.7718], 7);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
  .addTo(map);

const routeLayer = L.layerGroup().addTo(map);

document.getElementById("tripForm").addEventListener("submit", async e => {
  e.preventDefault();

  routeLayer.clearLayers();
  document.getElementById("tripSteps").innerHTML = "";

  const query = tripQuery.value.trim();
  if (!query) return;

  const res = await fetch("/admin/ai-assistant", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ query, task_type:"trip" })
  });

  const data = await res.json();
  const points = [];

  data.results.forEach((stop, i) => {
    points.push([stop.lat, stop.lon]);

    const icon = L.divIcon({
      html:`<div class="bg-blue-600 text-white
                  w-7 h-7 flex items-center justify-center
                  rounded-full text-sm">${i+1}</div>`
    });

    L.marker([stop.lat, stop.lon], {icon})
      .addTo(routeLayer)
      .on("click", () => loadStopDetails(stop.name));

    document.getElementById("tripSteps").innerHTML += `
      <div class="p-3 bg-gray-50 rounded-xl">
        <b>Stop ${i+1}</b><br>
        ${stop.name}
      </div>`;
  });

  if (points.length > 1) {
    L.polyline(points, {weight:5}).addTo(routeLayer);
    map.fitBounds(points, {padding:[50,50]});
  }
});

async function loadStopDetails(name){
  const res = await fetch("/admin/route-stop-details", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ destination:name })
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
