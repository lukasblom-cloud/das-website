/* ============================================================
   DAS Submissions Register
   ------------------------------------------------------------
   ★ HOW TO ADD A SUBMISSION ★
   Add a line to the SUBMISSIONS array below, save, and push.
   Put the PDF in /submissions/ and reference it as
   "../submissions/your-file.pdf".

     { date: "2026-03", title: "Submission to the NDIS Review",
       to: "Department of Social Services",
       topic: "NDIS", pdf: "../submissions/ndis-review-2026.pdf" },

   - date : YYYY-MM (shown as "Mar 2026", used by the Year filter)
   - title: full submission title
   - to   : who it was submitted to
   - topic: one word/phrase — becomes a filter option automatically
   - pdf  : optional link to the document (PDF or external URL)

   ⚠ The entries below are SAMPLE DATA so the table and filters
   can be seen working. Replace them with DAS's real submissions
   before launch.
   ============================================================ */

var SUBMISSIONS = [];

(function () {
  "use strict";
  var tableEl = document.getElementById("submissions-table");
  if (!tableEl) return;

  var MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  var topicSel = document.getElementById("f-topic");
  var yearSel = document.getElementById("f-year");
  var searchEl = document.getElementById("f-search");
  var countEl = document.getElementById("f-count");

  var sorted = SUBMISSIONS.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; });

  /* Build filter options from data */
  var topics = [], years = [];
  sorted.forEach(function (s) {
    if (topics.indexOf(s.topic) === -1) topics.push(s.topic);
    var y = s.date.slice(0, 4);
    if (years.indexOf(y) === -1) years.push(y);
  });
  topics.sort();
  topics.forEach(function (t) { topicSel.insertAdjacentHTML("beforeend", '<option value="' + t + '">' + t + "</option>"); });
  years.forEach(function (y) { yearSel.insertAdjacentHTML("beforeend", '<option value="' + y + '">' + y + "</option>"); });

  function fmtDate(d) {
    var p = d.split("-");
    return MONTHS[+p[1] - 1] + " " + p[0];
  }

  function render() {
    var topic = topicSel.value, year = yearSel.value;
    var q = (searchEl.value || "").toLowerCase().trim();

    var rows = sorted.filter(function (s) {
      if (topic && s.topic !== topic) return false;
      if (year && s.date.slice(0, 4) !== year) return false;
      if (q && (s.title + " " + s.to + " " + s.topic).toLowerCase().indexOf(q) === -1) return false;
      return true;
    });

    countEl.textContent = rows.length === 1 ? "1 submission" : rows.length + " submissions";

    if (!rows.length) {
      tableEl.innerHTML = '<div class="subs-empty"><p>No submissions have been published yet — check back soon.</p></div>';
      document.getElementById("f-clear").addEventListener("click", function () {
        topicSel.value = ""; yearSel.value = ""; searchEl.value = ""; render();
      });
      return;
    }

    var html = '<div class="subs-scroll"><table class="subs"><thead><tr>' +
      '<th scope="col">Date</th><th scope="col">Submission</th><th scope="col">Submitted to</th><th scope="col">Topic</th><th scope="col"><span class="visually-hidden">Document</span></th>' +
      "</tr></thead><tbody>";
    rows.forEach(function (s) {
      html += "<tr>" +
        '<td class="nowrap">' + fmtDate(s.date) + "</td>" +
        '<td class="t">' + s.title + "</td>" +
        "<td>" + s.to + "</td>" +
        '<td><span class="chip">' + s.topic + "</span></td>" +
        "<td>" + (s.pdf ? '<a class="dl-link" href="' + s.pdf + '" target="_blank" rel="noopener">Download</a>' : '<span class="muted">On request</span>') + "</td>" +
        "</tr>";
    });
    html += "</tbody></table></div>";
    tableEl.innerHTML = html;
  }

  topicSel.addEventListener("change", render);
  yearSel.addEventListener("change", render);
  searchEl.addEventListener("input", render);
  render();
})();
