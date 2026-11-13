/* OCS LLC — site behaviour (no dependencies) */
(function () {
  "use strict";

  var doc = document;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Header: shadow on scroll + mobile menu ---------- */
  var header = doc.querySelector("[data-header]");
  var toggle = doc.querySelector("[data-nav-toggle]");

  if (header) {
    var onScroll = function () { header.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  function setMenu(open) {
    if (!header || !toggle) return;
    header.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.querySelector(".sr-only").textContent = open ? "Close menu" : "Open menu";
  }
  if (toggle) {
    toggle.addEventListener("click", function () { setMenu(toggle.getAttribute("aria-expanded") !== "true"); });
    doc.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && header.classList.contains("is-open")) { setMenu(false); toggle.focus(); }
    });
    doc.addEventListener("click", function (e) {
      if (header.classList.contains("is-open") && !header.contains(e.target)) setMenu(false);
    });
    window.addEventListener("resize", function () { if (window.innerWidth >= 880) setMenu(false); });
  }

  /* ---------- Footer year ---------- */
  doc.querySelectorAll("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* ---------- Reveal on scroll ---------- */
  var reveals = doc.querySelectorAll("[data-reveal]");
  if (reveals.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      reveals.forEach(function (el) { el.classList.add("is-in"); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { entry.target.classList.add("is-in"); io.unobserve(entry.target); }
        });
      }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
      reveals.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---------- Reviews: cycles through every review, one at a time ---------- */
  doc.querySelectorAll("[data-reviews]").forEach(function (root) {
    var row = root.querySelector(".rev-row");
    var cards = Array.prototype.slice.call(row.querySelectorAll(".rev-card"));
    var status = root.querySelector("[data-rev-status]");
    var pauseBtn = root.querySelector("[data-rev-pause]");
    var DELAY = 5000;
    var userPaused = reduceMotion;   // reduced motion: never moves unless asked
    var hovering = false, focused = false, onScreen = false, lastTouch = 0;
    if (!cards.length) return;

    function step() {
      var gap = parseFloat(getComputedStyle(row).columnGap) || 0;
      return cards[0].offsetWidth + gap;
    }
    function perView() { return Math.max(1, Math.round((row.clientWidth + 1) / step())); }
    function lastIndex() { return Math.max(0, cards.length - perView()); }
    function current() { return Math.round(row.scrollLeft / step()); }
    function updateStatus() {
      var first = current() + 1, last = Math.min(cards.length, current() + perView());
      status.textContent = (first === last ? first : first + "–" + last) + " of " + cards.length;
    }
    function closeAll() {
      cards.forEach(function (card) {
        card.classList.remove("is-open");
        card.querySelector(".rev-more").textContent = "Read more";
      });
    }
    function go(i) {
      var max = lastIndex();
      if (i > max) i = 0;
      if (i < 0) i = max;
      closeAll();
      row.scrollTo({ left: i * step(), behavior: reduceMotion ? "auto" : "smooth" });
    }
    function markLong() {
      cards.forEach(function (card) {
        if (card.classList.contains("is-open")) return;
        var quote = card.querySelector("blockquote");
        card.querySelector(".rev-more").hidden = quote.scrollHeight <= quote.clientHeight + 2;
      });
    }

    root.querySelector("[data-rev-next]").addEventListener("click", function () { go(current() + 1); });
    root.querySelector("[data-rev-prev]").addEventListener("click", function () { go(current() - 1); });
    row.addEventListener("click", function (e) {
      if (!e.target.classList.contains("rev-more")) return;
      var card = e.target.closest(".rev-card");
      var open = card.classList.toggle("is-open");
      e.target.textContent = open ? "Show less" : "Read more";
    });

    var scrollTimer;
    row.addEventListener("scroll", function () {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(updateStatus, 80);
    }, { passive: true });
    window.addEventListener("resize", function () { markLong(); updateStatus(); });
    if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(markLong);
    markLong();
    updateStatus();

    // Stops for anything that means someone is reading: hover, focus, touch, or an open review.
    if (window.matchMedia("(hover: hover)").matches) {
      root.addEventListener("mouseenter", function () { hovering = true; });
      root.addEventListener("mouseleave", function () { hovering = false; });
    }
    root.addEventListener("focusin", function (e) { focused = e.target !== pauseBtn; });
    root.addEventListener("focusout", function () { focused = false; });
    row.addEventListener("touchstart", function () { lastTouch = Date.now(); }, { passive: true });
    row.addEventListener("touchmove", function () { lastTouch = Date.now(); }, { passive: true });

    pauseBtn.hidden = false;
    function drawPause() { pauseBtn.textContent = userPaused ? "Play" : "Pause"; }
    pauseBtn.addEventListener("click", function () { userPaused = !userPaused; drawPause(); });
    drawPause();

    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) { onScreen = entries[0].isIntersecting; }, { threshold: 0.2 }).observe(root);
    } else {
      onScreen = true;
    }
    setInterval(function () {
      if (userPaused || hovering || focused || !onScreen || doc.hidden) return;
      if (Date.now() - lastTouch < 8000 || root.querySelector(".rev-card.is-open")) return;
      go(current() + 1);
    }, DELAY);
  });

  /* ---------- 4 step process: numbered line switches the step ---------- */
  doc.querySelectorAll("[data-process]").forEach(function (root) {
    var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
    var nav = root.querySelector(".process-nav");
    var videos = Array.prototype.slice.call(root.querySelectorAll("video"));
    var inView = false;
    // Videos play silently on a loop, only for the open step and only while on screen.
    // With reduced motion they stay paused and keep their controls.
    function syncVideos() {
      if (reduceMotion) return;
      videos.forEach(function (video) {
        var active = video.closest(".process-panel").classList.contains("is-active");
        if (active && inView) {
          var playing = video.play();
          if (playing && playing.catch) playing.catch(function () {});
        } else {
          video.pause();
        }
      });
    }
    if (!reduceMotion) {
      videos.forEach(function (video) { video.removeAttribute("controls"); });
      if ("IntersectionObserver" in window) {
        new IntersectionObserver(function (entries) {
          inView = entries[0].isIntersecting;
          syncVideos();
        }, { threshold: 0.25 }).observe(root);
      }
    }
    function show(i, focus) {
      tabs.forEach(function (tab, n) {
        var on = n === i;
        tab.setAttribute("aria-selected", String(on));
        tab.tabIndex = on ? 0 : -1;
        doc.getElementById(tab.getAttribute("aria-controls")).classList.toggle("is-active", on);
      });
      nav.style.setProperty("--progress", (i / (tabs.length - 1)) * 100 + "%");
      if (focus) tabs[i].focus();
      syncVideos();
    }
    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { show(i); });
      tab.addEventListener("keydown", function (e) {
        if (e.key === "ArrowRight") { e.preventDefault(); show((i + 1) % tabs.length, true); }
        if (e.key === "ArrowLeft") { e.preventDefault(); show((i - 1 + tabs.length) % tabs.length, true); }
      });
    });
    show(0);
  });

  /* ---------- Recent work: arrows scroll the photo row ---------- */
  doc.querySelectorAll("[data-work]").forEach(function (root) {
    var row = root.querySelector(".work-row");
    function move(dir) {
      row.scrollBy({ left: dir * row.clientWidth * 0.8, behavior: reduceMotion ? "auto" : "smooth" });
    }
    root.querySelector("[data-work-prev]").addEventListener("click", function () { move(-1); });
    root.querySelector("[data-work-next]").addEventListener("click", function () { move(1); });
  });

  /* ---------- Form helpers ---------- */
  function collect(form) {
    // Builds a flat object; checkbox groups are joined into one readable line.
    var data = {};
    new FormData(form).forEach(function (value, key) {
      if (key === "_next" || key === "_captcha") return;
      value = String(value).trim();
      if (!value) return;
      data[key] = data[key] ? data[key] + ", " + value : value;
    });
    return data;
  }

  function send(form, payload) {
    return fetch(form.getAttribute("data-endpoint"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        if (!res.ok || !(body.success === true || body.success === "true")) {
          throw new Error(body.message || "Request failed");
        }
        return body;
      });
    });
  }

  // Email and any extra destination go out together. Either one getting through is
  // enough, so a problem with one never loses the request.
  function deliver(form, payload, extraSend) {
    var sends = [send(form, payload)];
    if (extraSend) {
      var extra = extraSend(payload);
      if (extra) sends.push(extra);
    }
    return Promise.allSettled(sends).then(function (results) {
      var delivered = results.some(function (r) { return r.status === "fulfilled"; });
      if (!delivered) throw new Error("All deliveries failed");
    });
  }

  function wireSubmit(form, buildPayload, extraSend) {
    var button = form.querySelector("[type=submit]");
    var errorEl = form.querySelector("[data-form-error]");
    var success = doc.getElementById(form.getAttribute("data-success"));
    var email = form.getAttribute("data-email") || "barrett@ocsllc.services";
    var idle = button ? button.innerHTML : "";

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;
      if (errorEl) errorEl.textContent = "";

      var finish = function () {
        form.hidden = true;
        if (success) { success.hidden = false; success.focus(); success.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" }); }
      };

      // Honeypot filled → silently "succeed" without sending.
      var trap = form.querySelector("[name=_honey]");
      if (trap && trap.value) { finish(); return; }

      if (button) { button.disabled = true; button.textContent = "Sending…"; }
      deliver(form, buildPayload ? buildPayload(form) : collect(form), extraSend)
        .then(function () {
          finish();
        })
        .catch(function () {
          if (errorEl) {
            errorEl.innerHTML = 'We couldn’t send that just now. Please try again, or email <a href="mailto:' + email + '">' + email + "</a>.";
          }
        })
        .then(function () { if (button) { button.disabled = false; button.innerHTML = idle; } });
    });
  }

  /* ---------- Simple AJAX forms (contact) ---------- */
  doc.querySelectorAll("[data-ajax-form]").forEach(function (form) { wireSubmit(form); });

  /* ---------- Quote page: reminds people which plan they picked ---------- */
  var planHint = doc.querySelector("[data-plan-hint]");
  if (planHint) {
    var PLANS = { "quarterly": "that you’d like the Quarterly plan", "twice-a-year": "that you’d like the Twice a Year plan", "one-time": "that you’d like a one-time cleaning" };
    var picked = new URLSearchParams(window.location.search).get("plan");
    if (PLANS[picked]) planHint.textContent = PLANS[picked];
  }

})();
