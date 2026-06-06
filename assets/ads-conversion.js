/* ===========================================================================
   OCS LLC — Google Ads conversion tracking.

   Fires a Google Ads conversion when a customer COMPLETES a booking in the
   embedded app form (ocs-crm.vercel.app/book), which postMessages a success
   event up to this page. This is the accurate "actually booked a job" signal.

   TO ACTIVATE — paste your two Google Ads values below:
     1. ADS_ID            e.g. "AW-123456789"   (Google Ads > Goals > Conversions > Tag setup)
     2. CONVERSION_LABEL  e.g. "AbC-D_efG12hIjkLM"  (the label of your "Booking" conversion action)
   Until both are set (no "XXXX"), this stays dormant and loads nothing.

   NOTE: it also requires the app's /book form to send the success message
   (see APP-ADD-CONVERSION-POSTMESSAGE.md). Both sides must be in place.
   =========================================================================== */
(function () {
  var ADS_ID = "AW-18072622126";              // OCS LLC Google Ads conversion ID
  var CONVERSION_LABEL = "-t31CJXghLkcEK6o2alD"; // "Book appointment" conversion label
  var APP_ORIGIN = "https://ocs-crm.vercel.app";

  var configured = ADS_ID.indexOf("XXXX") < 0 && CONVERSION_LABEL.indexOf("XXXX") < 0;

  // Load gtag.js once (only when configured), site-wide, so ad clicks are tracked
  // and the conversion linker is in place on whatever page the ad lands on.
  if (configured && !window.__ocsGtag) {
    window.__ocsGtag = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + ADS_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", ADS_ID);
  }

  // Fire the conversion when the embedded booking form reports a completed booking.
  window.addEventListener("message", function (e) {
    if (e.origin !== APP_ORIGIN) return;
    var d = e.data || {};
    if (d.type !== "ocs-booking-complete") return;

    if (configured && typeof window.gtag === "function") {
      window.gtag("event", "conversion", {
        send_to: ADS_ID + "/" + CONVERSION_LABEL,
        value: typeof d.value === "number" ? d.value : undefined,
        currency: "USD",
        transaction_id: d.id || undefined, // de-dupes if the message arrives twice
      });
    }
    if (window.console && window.console.log) {
      console.log("[OCS] booking-complete received", d, configured ? "(conversion fired)" : "(Ads ID not set yet)");
    }
  });
})();
