/* Google tag for Google Ads, same account as the old site. Only runs on the live domain,
   so previews and tests never count as visits or conversions. */
(function () {
  "use strict";
  var host = window.location.hostname;
  if (host !== "ocsllc.services" && host !== "www.ocsllc.services") return;
  var ADS_ID = "AW-18072622126";
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };
  window.gtag("js", new Date());
  window.gtag("config", ADS_ID);
  var script = document.createElement("script");
  script.async = true;
  script.src = "https://www.googletagmanager.com/gtag/js?id=" + ADS_ID;
  document.head.appendChild(script);

  // Rotor's form is on another site, so the page can't see it submit. Rotor's form settings send
  // people to /thanks/ afterward, and that visit counts as the quote conversion, once per visit.
  if (window.location.pathname === "/thanks/") {
    try {
      if (!sessionStorage.getItem("ocs_conv_form")) {
        window.gtag("event", "conversion", { send_to: ADS_ID + "/Ng3vCL_dgMocEK6o2alD" });
        sessionStorage.setItem("ocs_conv_form", "1");
      }
    } catch (e) { /* tracking never blocks the page */ }
  }
})();
