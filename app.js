/* Small vanilla-JS helpers: filter, sort, clickable rows, confirm, seat map. */
(function () {
  "use strict";

  // 1. Live filter: <input data-filter="table-id">
  document.querySelectorAll("input[data-filter]").forEach(function (box) {
    var table = document.getElementById(box.dataset.filter);
    if (!table) return;
    var empty = document.createElement("p");
    empty.className = "muted";
    empty.hidden = true;
    empty.textContent = "No matching rows.";
    table.parentNode.after(empty);

    function run() {
      var q = box.value.trim().toLowerCase(), shown = 0;
      table.querySelectorAll("tbody tr").forEach(function (tr) {
        var hit = tr.textContent.toLowerCase().indexOf(q) !== -1;
        tr.hidden = !hit;
        if (hit) shown++;
      });
      empty.hidden = shown !== 0;
    }
    box.addEventListener("input", run);
    run();
  });

  // 2. Click a column title to sort (data-sort="num" sorts as numbers)
  document.querySelectorAll("table th[data-sort]").forEach(function (th) {
    th.addEventListener("click", function () {
      var table = th.closest("table"), idx = th.cellIndex;
      var numeric = th.dataset.sort === "num";
      var dir = th.dataset.dir === "asc" ? "desc" : "asc";
      table.querySelectorAll("th").forEach(function (h) { delete h.dataset.dir; });
      th.dataset.dir = dir;
      var body = table.tBodies[0];
      var rows = Array.prototype.slice.call(body.rows);
      rows.sort(function (a, b) {
        var x = a.cells[idx].textContent.trim(), y = b.cells[idx].textContent.trim();
        var c = numeric ? parseFloat(x) - parseFloat(y) : x.localeCompare(y);
        return dir === "asc" ? c : -c;
      });
      rows.forEach(function (r) { body.appendChild(r); });
    });
  });

  // 3. Whole row is clickable: <tr data-href="...">
  document.querySelectorAll("tr[data-href]").forEach(function (tr) {
    tr.addEventListener("click", function (e) {
      if (e.target.closest("a, button, form")) return;
      window.location.href = tr.dataset.href;
    });
  });

  // 4. Ask before destructive actions: <form data-confirm="Are you sure?">
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (!window.confirm(f.dataset.confirm)) e.preventDefault();
    });
  });

  // 5. Seat map on the bus page
  var map = document.getElementById("seatmap");
  if (map) {
    var dateBox = document.getElementById("travel_date");
    var seatBox = document.getElementById("seat_number");
    var status = document.getElementById("seat-status");
    var capacity = parseInt(map.dataset.capacity, 10);
    var taken = [];

    function paint() {
      var chosen = parseInt(seatBox.value, 10);
      map.innerHTML = "";
      for (var n = 1; n <= capacity; n++) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "seat";
        b.textContent = n;
        b.dataset.n = n;
        if (taken.indexOf(n) !== -1) {
          b.classList.add("taken");
          b.disabled = true;
        } else if (n === chosen) {
          b.classList.add("pick");
        }
        map.appendChild(b);
        if (n % 4 === 2) {
          var gap = document.createElement("span");
          gap.className = "aisle";
          map.appendChild(gap);
        }
      }
    }

    function load() {
      if (!dateBox.value) return;
      status.textContent = "Loading seats...";
      fetch(map.dataset.api + "?date=" + encodeURIComponent(dateBox.value))
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.error) { status.textContent = d.error; return; }
          taken = d.taken;
          if (taken.indexOf(parseInt(seatBox.value, 10)) !== -1) seatBox.value = "";
          status.textContent = (capacity - taken.length) + " of " + capacity +
                               " seats free on " + dateBox.value;
          paint();
        })
        .catch(function () { status.textContent = "Could not load seats."; });
    }

    map.addEventListener("click", function (e) {
      var b = e.target.closest("button.seat");
      if (!b || b.disabled) return;
      seatBox.value = b.dataset.n;
      paint();
    });
    seatBox.addEventListener("input", paint);
    dateBox.addEventListener("change", load);
    load();
  }
})();
