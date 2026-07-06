/* ============================================================
   DAS site JS
   ------------------------------------------------------------
   ★ ORGANISATION DETAILS LIVE HERE — ONE PLACE. ★
   When DAS moves (~20 Jul 2026), update ORG below and every
   page updates. (The same text also exists as static fallback
   in each page's HTML for no-JS visitors — a find-and-replace
   of the old street address covers those.)
   ============================================================ */

var DAS_ORG = {
  addressLines: "3/11 Railway Tce,<br>(Opposite McDonalds)<br>Alice Springs, NT 0870",
  addressInline: "3/11 Railway Tce, Alice Springs, NT 0870 (opposite McDonalds)",
  mapUrl: "https://maps.app.goo.gl/xrYGv6QfevFYsygX8",
  phoneDisplay: "(08) 8953 – 1422",
  phoneHref: "tel:0889531422",
  email: "admin@das.org.au",
  hours: "Mon – Fri\u00A0 8:30am – 4:30pm"
};

(function () {
  "use strict";

  /* ---- Fill org details ---- */
  function fillOrg() {
    var map = {
      "address-lines": function (el) { el.innerHTML = DAS_ORG.addressLines; },
      "address-inline": function (el) { el.textContent = DAS_ORG.addressInline; },
      "phone": function (el) {
        el.textContent = DAS_ORG.phoneDisplay;
        if (el.tagName === "A") el.setAttribute("href", DAS_ORG.phoneHref);
      },
      "email": function (el) {
        el.textContent = DAS_ORG.email;
        if (el.tagName === "A") el.setAttribute("href", "mailto:" + DAS_ORG.email);
      },
      "hours": function (el) { el.textContent = DAS_ORG.hours; },
      "map-url": function (el) { el.setAttribute("href", DAS_ORG.mapUrl); }
    };
    Object.keys(map).forEach(function (key) {
      var els = document.querySelectorAll('[data-org="' + key + '"]');
      for (var i = 0; i < els.length; i++) map[key](els[i]);
    });
  }

  /* ---- Mobile nav ---- */
  function initNav() {
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector("nav.primary");
    if (!toggle || !nav) return;
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("open")) {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  /* ---- Footer year ---- */
  function initYear() {
    var els = document.querySelectorAll("[data-year]");
    for (var i = 0; i < els.length; i++) els[i].textContent = new Date().getFullYear();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      fillOrg(); initNav(); initYear();
    });
  } else {
    fillOrg(); initNav(); initYear();
  }
})();
