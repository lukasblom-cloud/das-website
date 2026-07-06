/* ============================================================
   DAS Events Calendar
   ------------------------------------------------------------
   ★ HOW TO ADD EVENTS ★
   Add a line to the EVENTS array below, save, and push:

     { date: "2026-08-14", title: "Peer support morning tea",
       type: "das", desc: "Optional longer description.",
       time: "10:00am – 12:00pm", where: "DAS office" },

   - date : YYYY-MM-DD
   - title: short name (shows on the calendar cell)
   - type : "das"        = DAS-run events (red)
            "community"  = local community events (purple)
            "conference" = sector conferences (dark)
            "keydate"    = NDIS / awareness key dates (melon)
   - desc, time, where, link : all optional, shown in the list

   ⚠ MOST DATES BELOW ARE SAMPLES TO CONFIRM — real event names
   from the DAS team, placeholder dates. Fix dates before launch.
   ============================================================ */

var EVENTS = [
  /* Real annual key dates only. DAS / community / conference event dates to be
     added by the DAS team once confirmed (see HOW TO ADD EVENTS above). */
  { date: "2026-07-01", title: "NDIS Pricing Arrangements update takes effect", type: "keydate", desc: "New price limits apply from today — check how your plan is affected." },
  { date: "2026-12-03", title: "International Day of People with Disability", type: "keydate", desc: "Global day celebrating the contributions and achievements of people with disability." }
];

/* ============================================================
   ICS EXPORT — keeps the "subscribe" feed in sync
   ------------------------------------------------------------
   ★ AFTER EDITING EVENTS: open the Events page, click
   "Download calendar file", and replace site/events.ics with
   the downloaded file before pushing. That keeps the
   subscribe-by-URL feed (/events.ics) up to date.
   ============================================================ */
function buildDasICS() {
  var lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Disability Advocacy Service Inc//Events//EN",
    "CALSCALE:GREGORIAN",
    "X-WR-CALNAME:DAS Events",
    "X-WR-TIMEZONE:Australia/Darwin"
  ];
  function esc(s) { return String(s || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n"); }
  EVENTS.forEach(function (e) {
    var d = e.date.replace(/-/g, "");
    var next = new Date(+e.date.slice(0, 4), +e.date.slice(5, 7) - 1, +e.date.slice(8, 10) + 1);
    var dEnd = next.getFullYear() + String(next.getMonth() + 1).padStart(2, "0") + String(next.getDate()).padStart(2, "0");
    var descParts = [];
    if (e.time) descParts.push("Time: " + e.time);
    if (e.desc) descParts.push(e.desc);
    if (e.link) descParts.push(e.link);
    lines.push(
      "BEGIN:VEVENT",
      "UID:" + d + "-" + esc(e.title).replace(/[^A-Za-z0-9]/g, "").slice(0, 24) + "@das.org.au",
      "DTSTAMP:" + d + "T000000Z",
      "DTSTART;VALUE=DATE:" + d,
      "DTEND;VALUE=DATE:" + dEnd,
      "SUMMARY:" + esc(e.title),
      descParts.length ? "DESCRIPTION:" + esc(descParts.join(" \u2014 ")) : null,
      e.where ? "LOCATION:" + esc(e.where) : null,
      "END:VEVENT"
    );
  });
  lines.push("END:VCALENDAR");
  return lines.filter(Boolean).join("\r\n");
}

(function () {
  "use strict";
  var calEl = document.getElementById("calendar");
  var listEl = document.getElementById("events-list");
  if (!calEl) return;

  var MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  var DOW = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  var TYPES = {
    das:        { label: "DAS events",        cls: "" },
    community:  { label: "Community",         cls: "community" },
    conference: { label: "Conferences",       cls: "workshop" },
    keydate:    { label: "Key dates",         cls: "keydate" }
  };
  var today = new Date();
  var view = new Date(today.getFullYear(), today.getMonth(), 1);
  var active = { das: true, community: true, conference: true, keydate: true };

  function iso(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  }

  function visible() {
    return EVENTS.filter(function (e) { return active[e.type] !== false; });
  }

  function eventsOn(dateStr) {
    return visible().filter(function (e) { return e.date === dateStr; });
  }

  function renderFilters() {
    var html = '<div class="cal-filters" role="group" aria-label="Filter events by type">';
    Object.keys(TYPES).forEach(function (k) {
      html += '<button type="button" class="cal-chip cal-chip--' + k + (active[k] ? " is-on" : "") + '" data-type="' + k + '" aria-pressed="' + (active[k] ? "true" : "false") + '"><span class="dot" aria-hidden="true"></span>' + TYPES[k].label + "</button>";
    });
    html += "</div>";
    return html;
  }

  function render() {
    var y = view.getFullYear(), m = view.getMonth();
    var first = new Date(y, m, 1);
    var startOffset = (first.getDay() + 6) % 7; // Monday-first
    var start = new Date(y, m, 1 - startOffset);

    var html = renderFilters();

    html += '<div class="cal-head">' +
      '<h2 id="cal-title">' + MONTHS[m] + " " + y + "</h2>" +
      '<div class="cal-nav">' +
      '<button type="button" id="cal-prev" aria-label="Previous month">‹</button>' +
      '<button type="button" id="cal-today" aria-label="Go to current month">Today</button>' +
      '<button type="button" id="cal-next" aria-label="Next month">›</button>' +
      "</div></div>";

    html += '<table class="cal" aria-labelledby="cal-title"><thead><tr>';
    DOW.forEach(function (d) { html += "<th scope=\"col\">" + d + "</th>"; });
    html += "</tr></thead><tbody>";

    var d = new Date(start);
    for (var w = 0; w < 6; w++) {
      html += "<tr>";
      for (var i = 0; i < 7; i++) {
        var inMonth = d.getMonth() === m;
        var dateStr = iso(d);
        var isToday = dateStr === iso(today);
        var cls = (inMonth ? "" : "dim") + (isToday ? " today" : "");
        html += '<td class="' + cls.trim() + '"><span class="d">' + d.getDate() + "</span>";
        eventsOn(dateStr).forEach(function (e) {
          var t = TYPES[e.type] && TYPES[e.type].cls ? " " + TYPES[e.type].cls : "";
          if (e.link) html += '<a class="evt' + t + '" href="' + e.link + '">' + e.title + "</a>";
          else html += '<span class="evt' + t + '">' + e.title + "</span>";
        });
        html += "</td>";
        d.setDate(d.getDate() + 1);
      }
      html += "</tr>";
      if (d.getMonth() !== m && d.getDay() === 1) break;
    }
    html += "</tbody></table>";
    calEl.innerHTML = html;

    document.getElementById("cal-prev").addEventListener("click", function () {
      view = new Date(view.getFullYear(), view.getMonth() - 1, 1); render();
    });
    document.getElementById("cal-next").addEventListener("click", function () {
      view = new Date(view.getFullYear(), view.getMonth() + 1, 1); render();
    });
    document.getElementById("cal-today").addEventListener("click", function () {
      view = new Date(today.getFullYear(), today.getMonth(), 1); render();
    });
    calEl.querySelectorAll(".cal-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var t = chip.getAttribute("data-type");
        active[t] = !active[t];
        render();
      });
    });

    renderList();
  }

  function renderList() {
    if (!listEl) return;
    var todayStr = iso(today);
    var upcoming = visible().filter(function (e) { return e.date >= todayStr; })
      .sort(function (a, b) { return a.date < b.date ? -1 : 1; })
      .slice(0, 8);

    if (!upcoming.length) {
      listEl.innerHTML =
        '<div class="events-empty-panel">' +
        '<div class="cal-icon" aria-hidden="true"><div class="top">DAS</div><div class="bd">—</div></div>' +
        "<div><h3>No upcoming events match your filters.</h3>" +
        '<p>Check back soon, or follow us on <a href="https://www.facebook.com/DisabilityAdvocacyCentralAustralia/">Facebook</a> to be the first to know when something is on.</p></div></div>';
      return;
    }

    var html = '<h2 class="upcoming-title">Coming up</h2>';
    upcoming.forEach(function (e) {
      var p = e.date.split("-");
      var meta = [];
      if (e.time) meta.push(e.time);
      if (e.where) meta.push(e.where);
      html += '<div class="evt-row evt-row--' + e.type + '">' +
        '<div class="when"><span class="mo">' + MONTHS[+p[1] - 1].slice(0, 3) + '</span><span class="dd">' + (+p[2]) + "</span></div>" +
        "<div><h3>" + (e.link ? '<a href="' + e.link + '">' + e.title + "</a>" : e.title) + "</h3>" +
        (meta.length ? '<p class="meta">' + meta.join(" · ") + "</p>" : "") +
        (e.desc ? "<p>" + e.desc + "</p>" : "") +
        '</div><span class="type-badge type-badge--' + e.type + '">' + TYPES[e.type].label.replace(/s$/, "") + "</span></div>";
    });
    listEl.innerHTML = html;
  }

  render();

  /* ---- ICS download + subscribe tools ---- */
  var dlBtn = document.getElementById("ics-download");
  if (dlBtn) {
    dlBtn.addEventListener("click", function () {
      var blob = new Blob([buildDasICS()], { type: "text/calendar;charset=utf-8" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "events.ics";
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    });
  }
  var copyBtn = document.getElementById("ics-copy");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var url = new URL("../events.ics", location.href).href;
      (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () {
        copyBtn.textContent = "Copied!";
        setTimeout(function () { copyBtn.textContent = "Copy feed link"; }, 2000);
      }).catch(function () {
        prompt("Copy this link:", url);
      });
    });
  }
})();
