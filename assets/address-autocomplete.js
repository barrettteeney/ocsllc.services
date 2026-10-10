/* OCS LLC: "powered by Google" address lookup for the estimate form.
 *
 * Off until a browser API key is added below. To turn it on:
 *   1. In Google Cloud, enable "Places API (New)" and "Maps JavaScript API".
 *   2. Create an API key restricted to HTTP referrers ocsllc.services/* and
 *      www.ocsllc.services/*, and to those two APIs only.
 *   3. Paste the key into GOOGLE_MAPS_KEY and publish.
 * With no key, the address box stays a normal text field.
 */
(function () {
  "use strict";
  var GOOGLE_MAPS_KEY = "";
  if (!GOOGLE_MAPS_KEY) return;

  var input = document.querySelector("[data-address-input]");
  if (!input) return;

  function loadMaps() {
    return new Promise(function (resolve, reject) {
      if (window.google && window.google.maps && window.google.maps.importLibrary) return resolve();
      window.__ocsMapsReady = resolve;
      var s = document.createElement("script");
      s.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(GOOGLE_MAPS_KEY) +
        "&loading=async&libraries=places&callback=__ocsMapsReady";
      s.async = true;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function attach() {
    return google.maps.importLibrary("places").then(function (places) {
      if (!places.PlaceAutocompleteElement) return;
      var el = new places.PlaceAutocompleteElement({
        includedRegionCodes: ["us"],
        locationBias: { center: { lat: 48.25, lng: -114.2 }, radius: 60000 }
      });
      el.setAttribute("aria-label", "Address of the job");
      input.type = "hidden";
      input.parentNode.insertBefore(el, input);
      el.addEventListener("gmp-select", function (event) {
        var place = event.placePrediction && event.placePrediction.toPlace();
        if (!place) return;
        place.fetchFields({ fields: ["formattedAddress"] }).then(function () {
          input.value = place.formattedAddress || "";
          input.dispatchEvent(new Event("input", { bubbles: true }));
        });
      });
    });
  }

  /* Load only when someone reaches the estimate, so the homepage stays fast. */
  var started = false;
  function start() {
    if (started) return;
    started = true;
    loadMaps().then(attach).catch(function () { /* keep the plain field */ });
  }
  var quote = document.getElementById("quote");
  if ("IntersectionObserver" in window && quote) {
    var io = new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) { io.disconnect(); start(); }
    }, { rootMargin: "400px" });
    io.observe(quote);
  } else {
    start();
  }
})();
