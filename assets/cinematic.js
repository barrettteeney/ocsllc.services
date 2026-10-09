/* OCS LLC — cinematic motion layer (homepage only).
 * Lenis smooth scrolling + GSAP ScrollTrigger. Every scroll effect is scrubbed:
 * it moves exactly as far as the visitor scrolls, holds when they stop, and
 * reverses on the way back up. Only the opening intro runs on a timer.
 * Skipped entirely for prefers-reduced-motion or if a library fails to load.
 */
(function () {
  "use strict";

  var html = document.documentElement;
  var curtain = document.querySelector(".cine-curtain");

  function bail() {
    html.classList.remove("cine-pre");
    if (curtain) curtain.remove();
  }

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce || !window.gsap || !window.ScrollTrigger || !window.Lenis) { bail(); return; }

  window.__cineStarted = true;
  var gsap = window.gsap;
  var ScrollTrigger = window.ScrollTrigger;
  gsap.registerPlugin(ScrollTrigger);
  gsap.defaults({ force3D: true });

  var playIntro = html.classList.contains("cine-pre");
  var desktop = window.matchMedia("(min-width: 1024px) and (pointer: fine)").matches;
  var $ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* ================= Smooth scroll ================= */
  function isScrollable(node) {
    for (var el = node; el && el !== document.body && el.nodeType === 1; el = el.parentElement) {
      if (el.scrollHeight > el.clientHeight + 2) {
        var oy = getComputedStyle(el).overflowY;
        if (oy === "auto" || oy === "scroll") return true;
      }
    }
    return false;
  }
  var lenis = new window.Lenis({
    lerp: 0.075,
    smoothWheel: true,
    wheelMultiplier: 0.9,
    prevent: function (node) {
      return !!(node.closest && node.closest(".lightbox, select, textarea, iframe")) || isScrollable(node);
    }
  });
  window.ocsLenis = lenis;
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
  gsap.ticker.lagSmoothing(0);

  // In-page anchors glide with Lenis.
  document.addEventListener("click", function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey) return;
    var link = event.target.closest && event.target.closest('a[href^="#"]');
    if (!link) return;
    var hash = link.getAttribute("href");
    if (!hash || hash.length < 2) return;
    var target = document.getElementById(hash.slice(1));
    if (!target) return;
    event.preventDefault();
    lenis.scrollTo(hash === "#top" ? 0 : target, { offset: -64, duration: 1.9 });
    if (history.replaceState) history.replaceState(null, "", hash);
  });

  // Freeze page scroll while the video lightbox is open.
  var lightbox = document.querySelector("[data-lightbox]");
  if (lightbox && "MutationObserver" in window) {
    new MutationObserver(function () {
      if (lightbox.hidden) lenis.start(); else lenis.stop();
    }).observe(lightbox, { attributes: true, attributeFilter: ["hidden"] });
  }

  /* ================= Header hide/show ================= */
  var nav = document.querySelector("[data-nav]");
  if (nav) {
    lenis.on("scroll", function (l) {
      var y = l.scroll;
      if (y < 140 || l.direction < 0 || nav.matches(":focus-within")) nav.classList.remove("cine-nav-hidden");
      else if (l.direction > 0) nav.classList.add("cine-nav-hidden");
    });
  }

  /* ================= Scroll progress ================= */
  var progress = document.querySelector(".scroll-progress");
  if (progress) {
    gsap.fromTo(progress, { scaleX: 0 }, {
      scaleX: 1, ease: "none",
      scrollTrigger: { start: 0, end: "max", scrub: 0.3 }
    });
  }

  /* ================= Word splitting ================= */
  function splitWords(el) {
    if (el._cineWords) return el._cineWords;
    var words = [];
    function wrap(content) {
      var outer = document.createElement("span");
      outer.className = "cine-w";
      var inner = document.createElement("span");
      inner.className = "cine-wi";
      if (typeof content === "string") inner.textContent = content; else inner.appendChild(content);
      outer.appendChild(inner);
      words.push(inner);
      return outer;
    }
    Array.prototype.slice.call(el.childNodes).forEach(function (node) {
      if (node.nodeType === 3) {
        var frag = document.createDocumentFragment();
        node.textContent.split(/(\s+)/).forEach(function (part) {
          if (!part) return;
          if (/^\s+$/.test(part)) frag.appendChild(document.createTextNode(" "));
          else frag.appendChild(wrap(part));
        });
        node.parentNode.replaceChild(frag, node);
      } else if (node.nodeType === 1 && node.tagName !== "BR") {
        var holder = document.createElement("span");
        node.parentNode.replaceChild(holder, node);
        holder.parentNode.replaceChild(wrap(node), holder);
      }
    });
    el._cineWords = words;
    return words;
  }

  /* ================= Hero ================= */
  var hero = document.querySelector(".hero");
  var heroVideo = hero && hero.querySelector(".hero-video");
  var heroInner = hero && hero.querySelector(".hero-inner");
  var heroTitle = hero && hero.querySelector("h1");
  var heroWords = heroTitle ? splitWords(heroTitle) : [];
  var heroRest = hero ? $(".eyebrow, .hero-sub, .hero-slogan, .hero-trust, .hero-cta-row", hero) : [];

  function heroScroll() {
    if (!hero) return;
    if (heroVideo) {
      gsap.fromTo(heroVideo, { scale: 1, yPercent: 0 }, {
        scale: 1.12, yPercent: 9, ease: "none", immediateRender: false,
        scrollTrigger: { trigger: hero, start: "top top", end: "bottom top", scrub: 0.6 }
      });
    }
    if (heroInner) {
      gsap.fromTo(heroInner, { y: 0, opacity: 1 }, {
        y: -110, opacity: 0, ease: "none", immediateRender: false,
        scrollTrigger: { trigger: hero, start: "top top", end: "bottom 15%", scrub: 0.6 }
      });
    }
    var cue = hero.querySelector(".hero-scroll-cue");
    if (cue) {
      gsap.fromTo(cue, { opacity: 1 }, {
        opacity: 0, ease: "none", immediateRender: false,
        scrollTrigger: { trigger: hero, start: "top top", end: "20% top", scrub: 0.6 }
      });
    }
  }

  function runIntro() {
    lenis.stop();
    var mark = curtain && curtain.querySelector(".cine-curtain-mark");
    if (nav) gsap.set(nav, { opacity: 0 });
    gsap.set(heroWords, { yPercent: 115, rotate: 4 });
    gsap.set(heroRest, { y: 26, opacity: 0 });
    if (heroVideo) gsap.set(heroVideo, { scale: 1.16 });
    html.classList.remove("cine-pre");
    html.classList.add("cine");

    var tl = gsap.timeline({
      defaults: { ease: "power3.out" },
      onComplete: function () {
        if (curtain) curtain.remove();
        if (nav) gsap.set(nav, { clearProps: "all" });
        lenis.start();
        heroScroll();
        ScrollTrigger.refresh();
      }
    });
    if (mark) tl.to(mark, { opacity: 1, scale: 1, duration: 0.55 }, 0.1)
                .to(mark, { opacity: 0, scale: 0.92, duration: 0.35, ease: "power2.in" }, 0.95);
    if (curtain) tl.to(curtain, { yPercent: -100, duration: 1.05, ease: "expo.inOut" }, 1.05);
    if (heroVideo) tl.to(heroVideo, { scale: 1, duration: 2.2, ease: "power2.out" }, 1.3);
    tl.to(heroWords, { yPercent: 0, rotate: 0, duration: 1.05, stagger: 0.09 }, 1.55);
    tl.to(heroRest, { y: 0, opacity: 1, duration: 0.9, stagger: 0.08 }, 1.9);
    if (nav) tl.to(nav, { opacity: 1, duration: 0.8, ease: "power1.out" }, 2.1);
    if (gsap.utils.toArray(".hero-scroll-cue").length) tl.from(".hero-scroll-cue", { opacity: 0, duration: 0.6 }, 2.4);
  }

  if (playIntro) {
    runIntro();
  } else {
    html.classList.add("cine");
    if (curtain) curtain.remove();
    heroScroll();
  }

  /* ================= Sections: glide + accent line ================= */
  $("body > section:not(.hero)").forEach(function (section) {
    var inner = section.querySelector(":scope > .container");
    if (inner) {
      gsap.fromTo(inner, { y: 140 }, {
        y: 0, ease: "none",
        scrollTrigger: { trigger: section, start: "top bottom", end: "top 30%", scrub: 0.6 }
      });
    }
    var line = document.createElement("div");
    line.className = "cine-line";
    line.setAttribute("aria-hidden", "true");
    section.insertBefore(line, section.firstChild);
    gsap.fromTo(line, { scaleX: 0 }, {
      scaleX: 1, ease: "none",
      scrollTrigger: { trigger: section, start: "top 92%", end: "top 25%", scrub: 0.6 }
    });
  });

  /* ================= Section headings ================= */
  $("body > section:not(.hero) h2, .svc-copy h3, .addl > h3").forEach(function (heading) {
    var words = splitWords(heading);
    if (!words.length) return;
    gsap.fromTo(words, { yPercent: 110, rotate: 6 }, {
      yPercent: 0, rotate: 0, ease: "power2.out", stagger: 0.08,
      scrollTrigger: { trigger: heading, start: "top 92%", end: "top 57%", scrub: 0.6 }
    });
  });

  /* ================= Body content rise ================= */
  var riseSelectors = [
    ".trust-item",
    ".sec-head .eyebrow", ".sec-sub", ".reviews-head",
    ".svc-tag", ".svc-copy > p", ".svc-checks li", ".svc-link",
    ".addl-grid > *", ".addl > p:not(.sec-sub)",
    ".loc-grid > *", ".valley-band", ".map-wrap",
    ".review-stage", ".review-controls",
    ".work-grid > *",
    ".about-copy > .eyebrow", ".about-copy > p", ".about-values li", ".about-creds",
    ".quote-layout > *",
    ".footer-grid > *"
  ];
  var riseEls = $(riseSelectors.join(","));

  // Items sharing a row get offset start/end so they stagger left to right.
  function rowIndex(el) {
    var parent = el.parentElement;
    if (!parent) return 0;
    var top = el.offsetTop;
    var index = 0;
    for (var sib = parent.firstElementChild; sib && sib !== el; sib = sib.nextElementSibling) {
      if (riseEls.indexOf(sib) !== -1 && Math.abs(sib.offsetTop - top) < 8) index++;
    }
    return Math.min(index, 4);
  }

  riseEls.forEach(function (el) {
    var off = rowIndex(el) * 4;
    gsap.fromTo(el, { y: 90, opacity: 0, scale: 0.94 }, {
      y: 0, opacity: 1, scale: 1, ease: "power2.out",
      scrollTrigger: { trigger: el, start: "top " + (98 - off) + "%", end: "top " + (64 - off) + "%", scrub: 0.6 }
    });
  });

  /* ================= Photos: clip wipe + drift ================= */
  function photoReveal(frame, media, gentle, radius) {
    var r = radius ? " round " + radius : "";
    gsap.fromTo(frame, { clipPath: "inset(30% 22% 30% 22%" + r + ")" }, {
      clipPath: "inset(0% 0% 0% 0%" + r + ")", ease: "power2.out",
      scrollTrigger: { trigger: frame, start: "top 95%", end: "top 45%", scrub: 0.6 }
    });
    if (media) {
      gsap.fromTo(media,
        gentle ? { scale: 1.08, yPercent: 0 } : { scale: 1.3, yPercent: -5 },
        {
          scale: gentle ? 1 : 1.04, yPercent: gentle ? 0 : 5, ease: "none",
          scrollTrigger: { trigger: frame, start: "top bottom", end: "bottom top", scrub: 0.6 }
        });
    }
  }
  $(".about-photo").forEach(function (frame) {
    photoReveal(frame, frame.querySelector("img"), false, "22px");
  });
  // Phone-frame clips show on-screen text, so they get the gentle zoom.
  $(".svc-media .phone-frame").forEach(function (frame) {
    photoReveal(frame, frame.querySelector("video"), true, "22px");
  });

  /* ================= Desktop extras ================= */
  if (desktop) {
    // Cards in a row drift at slightly different speeds.
    var drift = [0, 9, 4, 12];
    $(".loc-grid, .addl-grid, .work-grid").forEach(function (grid) {
      var kids = Array.prototype.slice.call(grid.children);
      var lefts = kids.map(function (k) { return k.offsetLeft; })
        .filter(function (v, i, a) { return a.indexOf(v) === i; })
        .sort(function (a, b) { return a - b; });
      kids.forEach(function (kid) {
        var amount = drift[lefts.indexOf(kid.offsetLeft) % drift.length] || 0;
        if (!amount) return;
        gsap.fromTo(kid, { yPercent: amount }, {
          yPercent: -amount, ease: "none",
          scrollTrigger: { trigger: grid, start: "top bottom", end: "bottom top", scrub: 0.6 }
        });
      });
    });

    // Magnetic buttons.
    $(".btn-primary, .nav-cta, .q-next, .q-reveal").forEach(function (btn) {
      var toX = gsap.quickTo(btn, "x", { duration: 0.45, ease: "power3.out" });
      var toY = gsap.quickTo(btn, "y", { duration: 0.45, ease: "power3.out" });
      btn.addEventListener("mousemove", function (e) {
        var r = btn.getBoundingClientRect();
        toX((e.clientX - (r.left + r.width / 2)) * 0.22);
        toY((e.clientY - (r.top + r.height / 2)) * 0.3);
      });
      btn.addEventListener("mouseleave", function () { toX(0); toY(0); });
    });

    // Soft warm glow that follows the cursor.
    var glow = document.createElement("div");
    glow.className = "cine-glow";
    glow.setAttribute("aria-hidden", "true");
    document.body.appendChild(glow);
    var gx = gsap.quickTo(glow, "x", { duration: 0.8, ease: "power3.out" });
    var gy = gsap.quickTo(glow, "y", { duration: 0.8, ease: "power3.out" });
    var glowOn = false;
    window.addEventListener("mousemove", function (e) {
      if (!glowOn) { glowOn = true; gsap.set(glow, { x: e.clientX, y: e.clientY }); gsap.to(glow, { opacity: 1, duration: 0.6 }); }
      gx(e.clientX); gy(e.clientY);
    }, { passive: true });
    document.addEventListener("mouseleave", function () { glowOn = false; gsap.to(glow, { opacity: 0, duration: 0.4 }); });
  }

  /* ================= Keep measurements fresh ================= */
  ScrollTrigger.sort();
  var refreshTimer;
  function queueRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(function () { ScrollTrigger.refresh(); }, 180);
  }
  window.addEventListener("load", function () {
    ScrollTrigger.refresh();
    // Pre-decode lazy images while idle so nothing stutters mid-scroll.
    var idle = window.requestIdleCallback || function (fn) { return setTimeout(fn, 400); };
    idle(function () {
      $('img[loading="lazy"]').forEach(function (img) {
        img.addEventListener("load", queueRefresh, { once: true });
        img.loading = "eager";
        if (img.decode) img.decode().catch(function () {});
      });
    });
  });
  // The quote form changes height between steps; re-measure when the page grows or shrinks.
  if ("ResizeObserver" in window) {
    var lastH = 0;
    new ResizeObserver(function () {
      var h = document.body.scrollHeight;
      if (Math.abs(h - lastH) > 4) { lastH = h; queueRefresh(); }
    }).observe(document.body);
  }
})();
