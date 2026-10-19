/* OCS LLC: "powered by Google" address lookup for the estimate form.
 *
 * Suggests real addresses as the customer types into the normal address box.
 * Typing a full address by hand still works, so the form never depends on Google.
 *
 * The key below is a browser key. Google designs these to be public; it is
 * protected in Google Cloud (project "My First Project"):
 *   - only works on ocsllc.services and www.ocsllc.services
 *   - only allowed to call Maps JavaScript API + Places API (New)
 *   - capped at 300 autocomplete + 300 place lookups per day (inside the free tier)
 * Set GOOGLE_MAPS_KEY to "" to switch the lookup off.
 */
(function () {
  "use strict";
  var GOOGLE_MAPS_KEY = "AIzaSyDBh-usvS_Owv-TOZTAm2imvaJC4DmeNEQ";
  if (!GOOGLE_MAPS_KEY) return;

  var input = document.querySelector("[data-address-input]");
  if (!input) return;

  var MIN_CHARS = 4;
  var DEBOUNCE_MS = 300;
  var BIAS = { center: { lat: 48.25, lng: -114.2 }, radius: 50000 }; // Flathead Valley

  var places = null;
  var sessionToken = null;
  var timer = null;
  var lastQuery = "";
  var items = [];
  var active = -1;
  var picked = false;

  /* ---------- dropdown ---------- */
  var wrap = input.parentNode;
  wrap.style.position = "relative";
  var list = document.createElement("div");
  list.className = "addr-suggest";
  list.setAttribute("role", "listbox");
  list.id = "addr-suggest-list";
  list.hidden = true;
  wrap.appendChild(list);
  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-controls", list.id);
  input.setAttribute("aria-expanded", "false");
  input.setAttribute("autocomplete", "off");

  var css = document.createElement("style");
  css.textContent =
    ".addr-suggest{position:absolute;left:0;right:0;top:100%;z-index:30;background:#fff;border:1px solid #9FA8AC;border-top:0;box-shadow:0 10px 24px rgba(0,0,0,.18);text-align:left}" +
    ".addr-suggest button{display:block;width:100%;padding:.7rem .85rem;border:0;border-bottom:1px solid #EEF1F2;background:#fff;color:#161616;font:inherit;font-size:.95rem;line-height:1.3;text-align:left;cursor:pointer}" +
    ".addr-suggest button small{display:block;color:#5B6468;font-size:.8rem;margin-top:.1rem}" +
    ".addr-suggest button[aria-selected=true],.addr-suggest button:hover{background:#F2FBFD}" +
    ".addr-suggest .addr-attrib{padding:.4rem .85rem;font-size:.72rem;color:#5B6468;text-align:right;font-family:Roboto,Arial,sans-serif}";
  document.head.appendChild(css);

  function close() {
    list.hidden = true;
    list.innerHTML = "";
    items = [];
    active = -1;
    input.setAttribute("aria-expanded", "false");
  }

  function highlight(i) {
    var btns = list.querySelectorAll("button");
    for (var b = 0; b < btns.length; b++) btns[b].setAttribute("aria-selected", b === i ? "true" : "false");
    active = i;
  }

  function render(suggestions) {
    list.innerHTML = "";
    items = [];
    suggestions.forEach(function (s) {
      var p = s.placePrediction;
      if (!p) return;
      var idx = items.length;
      var main = p.mainText ? p.mainText.toString() : p.text.toString();
      var sub = p.secondaryText ? p.secondaryText.toString() : "";
      var btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("role", "option");
      btn.id = "addr-opt-" + idx;
      btn.textContent = main;
      if (sub) {
        var small = document.createElement("small");
        small.textContent = sub;
        btn.appendChild(small);
      }
      btn.addEventListener("mousedown", function (e) { e.preventDefault(); });
      btn.addEventListener("click", function () { choose(idx); });
      list.appendChild(btn);
      items.push(p);
    });
    if (!items.length) return close();
    var attrib = document.createElement("div");
    attrib.className = "addr-attrib";
    attrib.textContent = "powered by Google";
    list.appendChild(attrib);
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    active = -1;
  }

  function choose(i) {
    var p = items[i];
    if (!p) return;
    var fallback = p.text ? p.text.toString() : input.value;
    input.value = fallback;
    picked = true;
    close();
    var place = p.toPlace();
    place.fetchFields({ fields: ["formattedAddress"] }).then(function () {
      if (place.formattedAddress) input.value = place.formattedAddress.replace(/, USA$/, "");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }).catch(function () { /* keep the suggestion text */ });
    sessionToken = null; // a pick ends the billing session
  }

  /* ---------- Google loading ---------- */
  function loadMaps() {
    return new Promise(function (resolve, reject) {
      if (window.google && google.maps && google.maps.importLibrary) return resolve();
      window.__ocsMapsReady = resolve;
      var s = document.createElement("script");
      s.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(GOOGLE_MAPS_KEY) +
        "&loading=async&v=weekly&callback=__ocsMapsReady";
      s.async = true;
      s.onerror = reject;
      document.head.appendChild(s);
    }).then(function () {
      return google.maps.importLibrary("places");
    }).then(function (lib) {
      if (!lib.AutocompleteSuggestion) throw new Error("no AutocompleteSuggestion");
      places = lib;
    });
  }

  function lookup(q) {
    if (!places) return;
    if (!sessionToken) sessionToken = new places.AutocompleteSessionToken();
    lastQuery = q;
    places.AutocompleteSuggestion.fetchAutocompleteSuggestions({
      input: q,
      sessionToken: sessionToken,
      includedRegionCodes: ["us"],
      locationBias: BIAS
    }).then(function (res) {
      if (q !== lastQuery || input.value.trim() !== q) return;
      render((res && res.suggestions) || []);
    }).catch(function () { close(); });
  }

  input.addEventListener("input", function (e) {
    if (picked && e.isTrusted === false) return;
    picked = false;
    clearTimeout(timer);
    var q = input.value.trim();
    if (q.length < MIN_CHARS || !places) return close();
    timer = setTimeout(function () { lookup(q); }, DEBOUNCE_MS);
  });

  input.addEventListener("keydown", function (e) {
    if (list.hidden || !items.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); highlight((active + 1) % items.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); highlight((active - 1 + items.length) % items.length); }
    else if (e.key === "Enter" && active >= 0) { e.preventDefault(); choose(active); }
    else if (e.key === "Escape") { close(); }
  });

  input.addEventListener("blur", function () { setTimeout(close, 150); });

  /* Load Google only when someone reaches the estimate, so the homepage stays fast. */
  var started = false;
  function start() {
    if (started) return;
    started = true;
    loadMaps().catch(function () { places = null; /* plain text box keeps working */ });
  }
  var quote = document.getElementById("quote");
  if ("IntersectionObserver" in window && quote) {
    var io = new IntersectionObserver(function (entries) {
      if (entries.some(function (en) { return en.isIntersecting; })) { io.disconnect(); start(); }
    }, { rootMargin: "400px" });
    io.observe(quote);
  } else {
    start();
  }
  input.addEventListener("focus", start);
})();
