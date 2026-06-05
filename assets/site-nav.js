/* OCS LLC top-nav: hamburger toggle + dropdown menus (click on mobile/touch, hover on desktop). */
(function () {
  function init() {
    var nav = document.querySelector(".site-nav");
    if (!nav) return;
    var toggle = nav.querySelector(".nav-toggle");
    var menu = nav.querySelector(".nav-menu");

    if (toggle && menu) {
      toggle.addEventListener("click", function () {
        var open = menu.classList.toggle("open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    nav.querySelectorAll(".nav-drop-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var drop = btn.closest(".nav-drop");
        var willOpen = !drop.classList.contains("open");
        nav.querySelectorAll(".nav-drop.open").forEach(function (d) {
          if (d !== drop) d.classList.remove("open");
        });
        drop.classList.toggle("open", willOpen);
        btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      });
    });

    // close menus on outside click
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".site-nav")) {
        nav.querySelectorAll(".nav-drop.open").forEach(function (d) { d.classList.remove("open"); });
        if (menu) menu.classList.remove("open");
      }
    });
    // close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        nav.querySelectorAll(".nav-drop.open").forEach(function (d) { d.classList.remove("open"); });
        if (menu) menu.classList.remove("open");
      }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
