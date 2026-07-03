/* ===========================================================================
   OCS LLC — Google tag + Google Ads conversion tracking (v2).

   Loads gtag.js site-wide (promo requirement: "install the Google tag"),
   then fires Google Ads conversions for the three ways a customer converts:

     1. FORM  — /estimate/ form submitted successfully. instant-estimate.js
                redirects to /thanks/ on success, so we fire when /thanks/
                loads. Guarded by sessionStorage so a refresh of /thanks/
                doesn't double-count.
     2. CALL  — customer taps any tel: link (click-to-call).
     3. SMS   — customer taps any sms: link (click-to-text).

   TO ACTIVATE the three conversion events, create the matching conversion
   actions in Google Ads (Goals > Conversions > New conversion action >
   Website) and paste each action's conversion label below. Any label still
   containing "XXXX" simply stays dormant — safe to deploy with placeholders.
   =========================================================================== */
(function () {
  // ── PASTE YOUR CONVERSION LABELS HERE ────────────────────────────────────
  var ADS_ID          = "AW-18072622126";      // Google Ads conversion ID (existing)
  var CONV_FORM_LABEL = "-t31CJXghLkcEK6o2alD"; // "Book appointment" action (form submit fires it)
  var CONV_CALL_LABEL = "XXXXXXXXXXXXXXXXXXX"; // label for "Phone call click"
  var CONV_SMS_LABEL  = "XXXXXXXXXXXXXXXXXXX"; // label for "Text/SMS click"
  // ─────────────────────────────────────────────────────────────────────────

  function isSet(v) { return v && v.indexOf("XXXX") < 0; }
  if (!isSet(ADS_ID)) return; // nothing to do without an Ads ID

  // 1) Load gtag.js once, site-wide.
  if (!window.__ocsGtag) {
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

  function fire(label, dedupeKey) {
    if (!isSet(label) || typeof window.gtag !== "function") return;
    if (dedupeKey) {
      try {
        if (sessionStorage.getItem(dedupeKey)) return;
        sessionStorage.setItem(dedupeKey, "1");
      } catch (e) { /* private-mode: fire anyway */ }
    }
    window.gtag("event", "conversion", { send_to: ADS_ID + "/" + label });
  }

  // 2) FORM conversion — /thanks/ is only reachable after a successful submit.
  var path = (location.pathname || "").toLowerCase();
  if (path === "/thanks" || path.indexOf("/thanks/") === 0) {
    fire(CONV_FORM_LABEL, "ocs_conv_form");
  }

  // 3) CALL + SMS conversions — delegated listener catches every tel:/sms:
  //    link on any page, including ones added later.
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
    if (!a) return;
    var href = (a.getAttribute("href") || "").toLowerCase();
    if (href.indexOf("tel:") === 0) fire(CONV_CALL_LABEL, "ocs_conv_call");
    else if (href.indexOf("sms:") === 0) fire(CONV_SMS_LABEL, "ocs_conv_sms");
  }, true);
})();
