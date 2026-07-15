/* OCS LLC — one-page concept (sandbox/v3)
 * Scroll orchestration + review cycle + work gallery + gated instant estimate.
 * Pricing engine ported verbatim from /assets/instant-estimate.js — keep the math in sync.
 */
(function () {
  "use strict";

  var REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ================= Scroll progress ================= */
  var progressBar = document.querySelector(".scroll-progress");
  function paintProgress() {
    if (!progressBar) return;
    var doc = document.documentElement;
    var max = doc.scrollHeight - window.innerHeight;
    progressBar.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + "%";
  }
  window.addEventListener("scroll", paintProgress, { passive: true });
  window.addEventListener("resize", paintProgress);

  /* ================= Nav state ================= */
  var nav = document.querySelector("[data-nav]");
  function paintNav() {
    if (nav) nav.classList.toggle("scrolled", window.scrollY > 40);
  }
  window.addEventListener("scroll", paintNav, { passive: true });
  paintNav();

  /* Active section highlight */
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".nav-links a"));
  if ("IntersectionObserver" in window && navLinks.length) {
    var sectionFor = {};
    navLinks.forEach(function (link) {
      var id = link.getAttribute("href").slice(1);
      var sec = document.getElementById(id);
      if (sec) sectionFor[id] = link;
    });
    var activeObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var link = sectionFor[entry.target.id];
        if (!link) return;
        if (entry.isIntersecting) {
          navLinks.forEach(function (l) { l.removeAttribute("aria-current"); });
          link.setAttribute("aria-current", "true");
        }
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    Object.keys(sectionFor).forEach(function (id) {
      activeObserver.observe(document.getElementById(id));
    });
  }

  /* ================= Reveal on scroll ================= */
  var revealables = document.querySelectorAll("[data-reveal]");
  if (REDUCED_MOTION || !("IntersectionObserver" in window)) {
    revealables.forEach(function (el) { el.classList.add("in-view"); });
  } else {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          revealObserver.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    revealables.forEach(function (el) { revealObserver.observe(el); });
  }

  /* ================= Hero ambient video =================
   * Two equal-length clips alternate in 20-second windows. Each clip
   * resumes where it left off on its next turn; once both are exhausted
   * the whole cycle restarts from the top. B stacks above A and
   * crossfades via the .ready opacity transition; B's source is data-src
   * so it costs nothing until A's first window is half done. */
  var heroA = document.querySelector("[data-hero-video]");
  var heroB = document.querySelector("[data-hero-video-alt]");
  if (heroA && !REDUCED_MOTION && !heroB) {
    heroA.loop = true;
    var soloHero = function () {
      heroA.classList.add("ready");
      heroA.play().catch(function () {});
    };
    heroA.addEventListener("loadeddata", soloHero);
    if (heroA.readyState >= 2) soloHero();
  } else if (heroA && !REDUCED_MOTION) {
    var HERO_WINDOW = 20;
    var heroPos = { a: 0, b: 0 };
    var heroDone = { a: false, b: false };
    var heroTurnStart = 0;
    var heroActive = null;

    var heroKey = function (video) { return video === heroA ? "a" : "b"; };

    var armHeroB = function () {
      if (heroB.dataset.armed === "true") return;
      heroB.dataset.armed = "true";
      heroB.querySelectorAll("source[data-src]").forEach(function (source) {
        source.src = source.getAttribute("data-src");
      });
      heroB.preload = "auto";
      heroB.load();
    };

    var beginHeroTurn = function (video) {
      heroActive = video;
      heroTurnStart = heroPos[heroKey(video)];
      var go = function () {
        heroA.classList.add("ready");
        video.play().catch(function () {});
        /* B above A: adding .ready fades B in, removing fades it out */
        heroB.classList.toggle("ready", video === heroB);
        setTimeout(function () {
          (video === heroA ? heroB : heroA).pause();
        }, 1300);
      };
      if (Math.abs(video.currentTime - heroTurnStart) > 0.3) {
        var onSeeked = function () {
          video.removeEventListener("seeked", onSeeked);
          go();
        };
        video.addEventListener("seeked", onSeeked);
        try { video.currentTime = heroTurnStart; } catch (e) { go(); }
      } else {
        go();
      }
    };

    var endHeroTurn = function (video, ended) {
      if (video !== heroActive) return;
      heroActive = null;
      var key = heroKey(video);
      heroPos[key] = heroTurnStart + HERO_WINDOW;
      if (ended || (video.duration && heroPos[key] >= video.duration - 1)) heroDone[key] = true;

      if (heroDone.a && heroDone.b) {
        /* Both clips fully shown — restart the whole cycle */
        heroPos.a = 0; heroPos.b = 0;
        heroDone.a = false; heroDone.b = false;
      }

      var next = video === heroA ? heroB : heroA;
      var nextKey = heroKey(next);
      if (next === heroB && next.readyState < 2) {
        /* Partner not loaded yet — keep rolling on the same clip */
        armHeroB();
        if (heroDone[key]) { heroPos[key] = 0; heroDone[key] = false; }
        beginHeroTurn(video);
      } else if (heroDone[nextKey]) {
        if (heroDone[key]) { heroPos[key] = 0; heroDone[key] = false; }
        beginHeroTurn(video);
      } else {
        beginHeroTurn(next);
      }
    };

    [heroA, heroB].forEach(function (video) {
      video.addEventListener("timeupdate", function () {
        if (video === heroActive && video.currentTime >= heroTurnStart + HERO_WINDOW) {
          endHeroTurn(video, false);
        }
        if (video === heroA && video.currentTime > heroTurnStart + 8) armHeroB();
      });
      video.addEventListener("ended", function () { endHeroTurn(video, true); });
    });

    var startHero = function () {
      if (heroActive) return;
      beginHeroTurn(heroA);
    };
    heroA.addEventListener("loadeddata", startHero);
    if (heroA.readyState >= 2) startHero();
  }

  /* ================= In-view muted video loops =================
   * Sources use data-src so nothing downloads until the card nears the
   * viewport; playback starts/pauses as cards cross 40% visibility. */
  var loopVideos = document.querySelectorAll("[data-inview-video]");
  function armVideo(video) {
    if (video.dataset.armed === "true") return;
    video.dataset.armed = "true";
    video.querySelectorAll("source[data-src]").forEach(function (source) {
      source.src = source.getAttribute("data-src");
    });
    video.load();
  }
  if (!REDUCED_MOTION && "IntersectionObserver" in window && loopVideos.length) {
    var loopObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var video = entry.target;
        if (entry.isIntersecting && entry.intersectionRatio >= 0.4) {
          armVideo(video);
          video.play().catch(function () {});
        } else {
          video.pause();
        }
      });
    }, { threshold: [0, 0.4] });
    loopVideos.forEach(function (video) { loopObserver.observe(video); });
  }

  /* Keep visible review counts in sync with the bot-maintained JSON-LD */
  try {
    var ldScript = document.querySelector('script[type="application/ld+json"]');
    var biz = ldScript ? JSON.parse(ldScript.textContent) : null;
    var liveCount = biz && biz.aggregateRating && biz.aggregateRating.reviewCount;
    if (liveCount) {
      document.querySelectorAll("[data-review-count]").forEach(function (el) { el.textContent = liveCount; });
    }
  } catch (e) { /* leave the static count */ }

  /* ================= Reviews cycle ================= */
  var REVIEWS = [
    { name: "Stacie Sanders", text: "Barrett did a fantastic job on our windows and reasonably priced. We will for sure being hiring him again! 👍" },
    { name: "Geri Josephsen", text: "OCS LLC came this morning to clean my windows. He was very personable, on time, kept me updated on what was happening. Plus did a very thorough and great job! I will definitely be getting in touch with him again come spring!" },
    { name: "Jayden Jacobson", text: "Highly recommended, fantastic service in all ways; the window cleaning itself and the customer service. Great price as well, highly recommend" },
    { name: "Debbie Turner", text: "Barrett did an amazing job on my windows inside and out very polite and very hard-working. I definitely will use him again and I highly recommend him." },
    { name: "Angela Fleshman", text: "What a treat!!! It's funny how it just feels a little brighter when the window and screens are clean! Don't hesitate, book your service ASAP!!!" },
    { name: "Katerina Robinson", note: "Commercial", text: "Barrett did a fantastic job on my building, he was prompt, prepared and professional. My windows look amazing, thank you so much!" },
    { name: "Addie C", text: "Inside and outside our windows look so clear and beautiful! The job Barrett and his company did to clean our western facing widows exceeded our expectations. Really good communication throughout the project as well. Highly recommend" },
    { name: "Cheryl Klippenstein", text: "Barrett did such a great job cleaning our windows. He took his time, was very thorough. I would recommend his business to anyone." },
    { name: "Donna M", text: "He was very respectful of our property and did a beautiful job… rest assured not only will Barrett do a fantastic job, it will be for a fair price!" },
    { name: "Darel Handley", text: "Thank you so much for doing such an incredible job! Competitive pricing, thorough job, and very friendly. Will use you guys again and refer you to whoever is in need!!!" },
    { name: "Cohen Booth", text: "Barrett does a fantastic job at cleaning windows! OCS did my father in laws business and the windows look amazing!" },
    { name: "Josh Steffen", text: "Did a great job! Easy to communicate with, very impressed with the work done." }
  ];

  var stage = document.querySelector("[data-review-stage]");
  var dotsWrap = document.querySelector("[data-review-dots]");
  if (stage && dotsWrap) {
    REVIEWS.forEach(function (review, index) {
      var slide = document.createElement("figure");
      slide.className = "review-slide" + (index === 0 ? " active" : "");
      slide.style.margin = "0";
      slide.setAttribute("role", "group");
      slide.setAttribute("aria-label", "Review " + (index + 1) + " of " + REVIEWS.length);
      var stars = document.createElement("div");
      stars.className = "stars";
      stars.setAttribute("aria-label", "5 out of 5 stars");
      stars.textContent = "★★★★★";
      var quote = document.createElement("blockquote");
      quote.className = "review-quote";
      quote.style.margin = "0 0 1rem";
      quote.textContent = "“" + review.text + "”";
      var name = document.createElement("figcaption");
      name.className = "review-name";
      name.textContent = "— " + review.name;
      if (review.note) {
        var noteEl = document.createElement("small");
        noteEl.textContent = "  ·  " + review.note;
        name.appendChild(noteEl);
      }
      slide.appendChild(stars);
      slide.appendChild(quote);
      slide.appendChild(name);
      stage.appendChild(slide);

      var dot = document.createElement("button");
      dot.type = "button";
      dot.className = index === 0 ? "active" : "";
      dot.setAttribute("aria-label", "Show review " + (index + 1));
      dot.addEventListener("click", function () { showReview(index, true); });
      dotsWrap.appendChild(dot);
    });

    var slides = stage.querySelectorAll(".review-slide");
    var dots = dotsWrap.querySelectorAll("button");
    var current = 0;
    var timer = null;

    function showReview(index, userInitiated) {
      current = (index + REVIEWS.length) % REVIEWS.length;
      slides.forEach(function (slide, i) { slide.classList.toggle("active", i === current); });
      dots.forEach(function (dot, i) { dot.classList.toggle("active", i === current); });
      if (userInitiated) restartTimer();
    }
    function restartTimer() {
      if (timer) clearInterval(timer);
      if (REDUCED_MOTION) return;
      timer = setInterval(function () { showReview(current + 1); }, 5200);
    }
    document.querySelector("[data-review-prev]").addEventListener("click", function () { showReview(current - 1, true); });
    document.querySelector("[data-review-next]").addEventListener("click", function () { showReview(current + 1, true); });
    stage.addEventListener("mouseenter", function () { if (timer) clearInterval(timer); });
    stage.addEventListener("mouseleave", restartTimer);
    stage.addEventListener("focusin", function () { if (timer) clearInterval(timer); });
    stage.addEventListener("focusout", restartTimer);
    restartTimer();
  }

  /* ================= Work lightbox ================= */
  var lightbox = document.querySelector("[data-lightbox]");
  var lightboxVideo = document.querySelector("[data-lightbox-video]");
  var workCards = Array.prototype.slice.call(document.querySelectorAll(".work-card"));
  var lightboxIndex = 0;
  var lightboxTrigger = null;

  function openLightbox(index) {
    if (lightbox.hidden) lightboxTrigger = document.activeElement;
    lightboxIndex = (index + workCards.length) % workCards.length;
    lightboxVideo.src = workCards[lightboxIndex].getAttribute("data-clip");
    lightbox.hidden = false;
    lightbox.classList.add("open");
    document.body.style.overflow = "hidden";
    lightboxVideo.play().catch(function () {});
    document.querySelector("[data-lightbox-close]").focus();
  }
  function closeLightbox() {
    lightbox.classList.remove("open");
    lightbox.hidden = true;
    lightboxVideo.pause();
    lightboxVideo.removeAttribute("src");
    lightboxVideo.load();
    document.body.style.overflow = "";
    if (lightboxTrigger && lightboxTrigger.focus) lightboxTrigger.focus();
    lightboxTrigger = null;
  }
  if (lightbox && lightboxVideo && workCards.length) {
    workCards.forEach(function (card, index) {
      card.addEventListener("click", function () { openLightbox(index); });
    });
    document.querySelector("[data-lightbox-close]").addEventListener("click", closeLightbox);
    document.querySelector("[data-lightbox-prev]").addEventListener("click", function () { openLightbox(lightboxIndex - 1); });
    document.querySelector("[data-lightbox-next]").addEventListener("click", function () { openLightbox(lightboxIndex + 1); });
    lightbox.addEventListener("click", function (event) {
      if (event.target === lightbox) closeLightbox();
    });
    document.addEventListener("keydown", function (event) {
      if (lightbox.hidden) return;
      if (event.key === "Escape") { closeLightbox(); return; }
      if (event.key === "Tab") {
        /* Contain Tab inside the dialog */
        var focusables = lightbox.querySelectorAll("button, video");
        var first = focusables[0];
        var last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
        return;
      }
      /* Leave arrow keys to the player's own seek controls when it has focus */
      if (document.activeElement === lightboxVideo) return;
      if (event.key === "ArrowLeft") openLightbox(lightboxIndex - 1);
      if (event.key === "ArrowRight") openLightbox(lightboxIndex + 1);
    });
  }

  /* ============================================================
   * INSTANT ESTIMATE — pricing engine ported from
   * /assets/instant-estimate.js. The reveal is gated: contact info
   * is collected BEFORE the range is shown, and the lead fires to
   * the same two endpoints as the live estimate page.
   * ============================================================ */
  var SQFT_TIERS = [
    { max: 1000, both: 0.15, ext: 0.09, sqftLabel: "Up to 1,000 sqft",
      panes: [{ label: "6-10 panes", value: 8 }, { label: "11-15 panes", value: 13 }, { label: "16-20 panes", value: 18 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-6 screens", value: 4 }, { label: "7-12 screens", value: 10 }] },
    { max: 2000, both: 0.17, ext: 0.10, sqftLabel: "1,001-2,000 sqft",
      panes: [{ label: "12-18 panes", value: 15 }, { label: "19-25 panes", value: 22 }, { label: "26-32 panes", value: 29 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-5 screens", value: 3 }, { label: "6-12 screens", value: 9 }, { label: "13-20 screens", value: 16 }] },
    { max: 3000, both: 0.19, ext: 0.11, sqftLabel: "2,001-3,000 sqft",
      panes: [{ label: "20-28 panes", value: 24 }, { label: "29-36 panes", value: 33 }, { label: "37-45 panes", value: 41 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-9 screens", value: 5 }, { label: "10-18 screens", value: 14 }, { label: "19-28 screens", value: 24 }] },
    { max: 4000, both: 0.21, ext: 0.13, sqftLabel: "3,001-4,000 sqft",
      panes: [{ label: "30-38 panes", value: 34 }, { label: "39-48 panes", value: 44 }, { label: "49-60 panes", value: 55 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-14 screens", value: 7 }, { label: "15-25 screens", value: 20 }, { label: "26-38 screens", value: 32 }] },
    { max: 5000, both: 0.23, ext: 0.14, sqftLabel: "4,001-5,000 sqft",
      panes: [{ label: "40-50 panes", value: 45 }, { label: "51-62 panes", value: 56 }, { label: "63-75 panes", value: 69 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-19 screens", value: 10 }, { label: "20-32 screens", value: 26 }, { label: "33-48 screens", value: 40 }] },
    { max: 6000, both: 0.25, ext: 0.15, sqftLabel: "5,001-6,000 sqft",
      panes: [{ label: "50-65 panes", value: 58 }, { label: "66-80 panes", value: 73 }, { label: "81-100 panes", value: 90 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-24 screens", value: 12 }, { label: "25-40 screens", value: 32 }, { label: "41-60 screens", value: 50 }] },
    { max: 7000, both: 0.27, ext: 0.16, sqftLabel: "6,001-7,000 sqft",
      panes: [{ label: "60-78 panes", value: 69 }, { label: "79-96 panes", value: 88 }, { label: "97-120 panes", value: 108 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-29 screens", value: 15 }, { label: "30-48 screens", value: 39 }, { label: "49-72 screens", value: 60 }] },
    { max: 8000, both: 0.29, ext: 0.17, sqftLabel: "7,001-8,000 sqft",
      panes: [{ label: "70-90 panes", value: 80 }, { label: "91-112 panes", value: 101 }, { label: "113-140 panes", value: 126 }],
      screens: [{ label: "No screens", value: 0 }, { label: "1-34 screens", value: 17 }, { label: "35-56 screens", value: 45 }, { label: "57-84 screens", value: 70 }] }
  ];
  var DEFAULT_SQFT_NOTE = "Know the square footage? Enter it below. If not, choose the range your home falls in.";
  var OVERSIZE_SQFT_LABEL = "8,000+ sqft";
  var OVERSIZE_SQFT_NOTE = "Enter your best estimated square footage for the home, then choose the closest pane and screen ranges.";
  var PER_PANE = { ext: 8, both: 14, screen: 4 };
  var MIN_CHARGE = 150;

  function money(value) { return "$" + Math.round(value).toLocaleString(); }
  function roundTo(value, step) { return Math.round(value / step) * step; }

  var form = document.querySelector("[data-quote-form]");
  if (!form) return;

  function getNumber(name) {
    var field = form.elements[name];
    var value = field ? parseFloat(field.value) : 0;
    return Number.isFinite(value) && value > 0 ? value : 0;
  }
  function getValue(name) {
    var field = form.elements[name];
    if (!field) return "";
    if (field.length && field[0] && field[0].type === "radio") {
      for (var i = 0; i < field.length; i += 1) if (field[i].checked) return field[i].value;
      return "";
    }
    return field.value || "";
  }
  function getService() {
    var checked = form.querySelector('input[name="service"]:checked');
    return checked ? checked.value : "both";
  }

  function makeRangeLabel(low, high, unit, isPlus) {
    return low.toLocaleString() + "-" + high.toLocaleString() + (isPlus ? "+" : "") + " " + unit;
  }
  function makeRange(low, high, unit, factor, isPlus, keepLow) {
    var scaledLow = keepLow ? low : Math.max(1, Math.round(low * factor));
    var scaledHigh = Math.max(scaledLow, Math.round(high * factor));
    return { label: makeRangeLabel(scaledLow, scaledHigh, unit, isPlus), value: Math.round((scaledLow + scaledHigh) / 2) };
  }
  function makeExplicitRange(low, high, unit, isPlus) {
    return { label: makeRangeLabel(low, high, unit, isPlus), value: Math.round((low + high) / 2) };
  }
  function getOversizeGuidanceTier(sqft) {
    var factor = sqft && sqft > 8000 ? sqft / 8000 : 1;
    var paneHigh1 = Math.round(110 * factor);
    var paneHigh2 = Math.max(paneHigh1 + 1, Math.round(150 * factor));
    var paneHigh3 = Math.max(paneHigh2 + 1, Math.round(200 * factor));
    var screenHigh1 = Math.round(30 * factor);
    var screenHigh2 = Math.max(screenHigh1 + 1, Math.round(60 * factor));
    var screenHigh3 = Math.max(screenHigh2 + 1, Math.round(90 * factor));
    return {
      max: Infinity,
      sqftLabel: sqft && sqft > 8000 ? sqft.toLocaleString() + " sqft / 8,000+ home" : OVERSIZE_SQFT_LABEL,
      panes: [
        makeRange(80, 110, "panes", factor, false, false),
        makeExplicitRange(paneHigh1 + 1, paneHigh2, "panes", false),
        makeExplicitRange(paneHigh2 + 1, paneHigh3, "panes", true)
      ],
      screens: [
        { label: "No screens", value: 0 },
        makeExplicitRange(1, screenHigh1, "screens", false),
        makeExplicitRange(screenHigh1 + 1, screenHigh2, "screens", false),
        makeExplicitRange(screenHigh2 + 1, screenHigh3, "screens", true)
      ]
    };
  }
  function baseFromSqft(sqft, service) {
    if (!sqft) return 0;
    var tier = SQFT_TIERS.find(function (item) { return sqft <= item.max; });
    if (!tier) return null;
    return sqft * tier[service];
  }
  function getTierForSqft(sqft) {
    if (!sqft) return null;
    return SQFT_TIERS.find(function (item) { return sqft <= item.max; }) || getOversizeGuidanceTier(sqft);
  }
  function isOversizeTierSelected() { return getValue("sqft_tier") === OVERSIZE_SQFT_LABEL; }
  function getGuidanceTier() {
    if (isOversizeTierSelected()) return getOversizeGuidanceTier(getNumber("sqft"));
    return getTierForSqft(getNumber("sqft"));
  }
  function setHiddenValue(name, value) {
    var field = form.elements[name];
    if (field) field.value = value || "";
  }
  function withSurcharges(base) {
    var pct = 0;
    if (form.elements.stories && form.elements.stories.checked) pct += 0.10;
    if (form.elements.hard_water && form.elements.hard_water.checked) pct += 0.20;
    if (getValue("last_cleaned") === "5+ years") pct += 0.15;
    if (form.elements.post_construction && form.elements.post_construction.checked) pct += 0.25;
    return base + base * pct;
  }
  function getReviewFlags(result) {
    var flags = [];
    if (result && result.oversized) flags.push("over 8,000 sqft");
    if (form.elements.hard_water && form.elements.hard_water.checked) flags.push("hard water");
    if (getValue("last_cleaned") === "5+ years") flags.push("5+ years since cleaning");
    if (form.elements.post_construction && form.elements.post_construction.checked) flags.push("post-construction");
    if (form.elements.french && form.elements.french.checked) flags.push("divided-light panes");
    if (form.elements.stories && form.elements.stories.checked) flags.push("two or more stories");
    return flags;
  }
  function getConfidence(result) {
    if (!result || result.oversized) {
      return { label: "Needs details", text: "Large or unusual jobs are best confirmed by our team.", level: "low" };
    }
    var flags = getReviewFlags(result);
    if (result.sqft && result.panes && !flags.length) {
      return { label: "Tighter range", text: "Square footage and pane count are both included.", level: "high" };
    }
    if (result.sqft && !flags.length) {
      return { label: "Good starting range", text: "Text photos if you want us to tighten it further.", level: "medium" };
    }
    return { label: "We’ll confirm", text: flags.length ? "Flagged for " + flags.join(", ") + "." : "A quick review keeps the quote accurate.", level: "review" };
  }
  function compute() {
    var service = getService();
    var sqft = getNumber("sqft");
    var panes = getNumber("panes");
    var screens = getNumber("screens");
    var sqftBase = baseFromSqft(sqft, service);
    var paneBase = panes ? panes * PER_PANE[service] : 0;
    var paths = [];

    if (sqftBase === null) return { oversized: true };
    if (sqftBase) paths.push(withSurcharges(sqftBase));
    if (paneBase) paths.push(withSurcharges(paneBase));
    if (!paths.length) return null;

    var total = paths.reduce(function (sum, item) { return sum + item; }, 0) / paths.length;
    if (screens) total += screens * PER_PANE.screen;
    if (total < MIN_CHARGE) total = MIN_CHARGE;

    var low = Math.max(MIN_CHARGE, roundTo(total * 0.85, 5));
    var high = roundTo(total * 1.15, 5);
    if (high - low < 25) high = low + 25;

    return {
      low: low, high: high, total: total, service: service,
      sqft: sqft, panes: panes, screens: screens,
      averaged: sqftBase && paneBase,
      french: !!(form.elements.french && form.elements.french.checked)
    };
  }
  function updateHidden(result) {
    var confidence = getConfidence(result);
    setHiddenValue("estimate_range", result && !result.oversized ? money(result.low) + " - " + money(result.high) : "");
    setHiddenValue("estimate_internal_total", result && !result.oversized ? Math.round(result.total).toString() : "");
    setHiddenValue("estimate_service", result ? (result.service === "both" ? "Interior + exterior" : "Exterior only") : "Interior + exterior");
    setHiddenValue("estimate_accuracy", confidence.label);
    setHiddenValue("estimate_review_flags", getReviewFlags(result).join(", "));
    setHiddenValue("estimate_notes", result && result.french ? "REVIEW: divided-light/French panes may need manual price adjustment." : "");
  }

  /* ---------- Pane/screen suggestion chips ---------- */
  function setCountChoice(name, value, label) {
    if (form.elements[name]) form.elements[name].value = String(value);
    setHiddenValue(name === "panes" ? "pane_range" : "screen_range", label);
    form.querySelectorAll('[data-count-name="' + name + '"]').forEach(function (button) {
      button.classList.toggle("is-active", button.getAttribute("data-count-label") === label);
    });
  }
  function renderCountOptions() {
    var tier = getGuidanceTier();
    var paneWrap = form.querySelector("[data-pane-options]");
    var screenWrap = form.querySelector("[data-screen-options]");
    var paneNote = form.querySelector("[data-pane-note]");
    var screenNote = form.querySelector("[data-screen-note]");

    function paint(wrap, name, options) {
      if (!wrap) return;
      wrap.innerHTML = "";
      if (!options || !options.length) return;
      options.forEach(function (option) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "q-chip";
        button.setAttribute("data-count-name", name);
        button.setAttribute("data-count-label", option.label);
        button.textContent = option.label;
        button.addEventListener("click", function () { setCountChoice(name, option.value, option.label); });
        wrap.appendChild(button);
      });
    }

    if (!tier) {
      if (paneWrap) paneWrap.innerHTML = "";
      if (screenWrap) screenWrap.innerHTML = "";
      if (paneNote) paneNote.textContent = "Pick a home size above and we’ll suggest common pane-count ranges.";
      if (screenNote) screenNote.textContent = "Choose no screens if you don’t want screens cleaned.";
      return;
    }
    if (paneNote) paneNote.textContent = "Common ranges for " + tier.sqftLabel + " homes — choose the closest.";
    if (screenNote) screenNote.textContent = "Screen ranges for " + tier.sqftLabel + " homes.";
    paint(paneWrap, "panes", tier.panes);
    paint(screenWrap, "screens", tier.screens);

    ["pane_range", "screen_range"].forEach(function (hidden, i) {
      var currentLabel = getValue(hidden);
      var name = i === 0 ? "panes" : "screens";
      if (currentLabel) {
        form.querySelectorAll('[data-count-name="' + name + '"]').forEach(function (button) {
          button.classList.toggle("is-active", button.getAttribute("data-count-label") === currentLabel);
        });
      }
    });
  }
  function setSqftTierState(value, label) {
    form.querySelectorAll("[data-sqft-tier-value]").forEach(function (button) {
      button.classList.toggle("is-active", button.getAttribute("data-sqft-tier-value") === String(value));
    });
    setHiddenValue("sqft_tier", label);
  }
  function setSqftNote(message) {
    var note = form.querySelector("[data-sqft-note]");
    if (note) note.textContent = message || DEFAULT_SQFT_NOTE;
  }
  function applyTierDefaults(value) {
    var tier = value === "6000plus" ? getOversizeGuidanceTier(getNumber("sqft")) : getTierForSqft(parseFloat(value));
    if (!tier) return;
    var middlePane = tier.panes[1] || tier.panes[0];
    var noScreens = tier.screens[0];
    /* Only default the pane count when it's empty or was set by a chip
     * (pane_range non-empty) — never clobber a hand-typed count. */
    if (middlePane && form.elements.panes && (!form.elements.panes.value || getValue("pane_range"))) {
      form.elements.panes.value = String(middlePane.value);
      setHiddenValue("pane_range", middlePane.label);
    }
    if (noScreens && form.elements.screens && !form.elements.screens.value) {
      form.elements.screens.value = String(noScreens.value);
      setHiddenValue("screen_range", noScreens.label);
    }
  }

  form.querySelectorAll("[data-sqft-tier-value]").forEach(function (button) {
    button.addEventListener("click", function () {
      var value = button.getAttribute("data-sqft-tier-value");
      var label = button.getAttribute("data-sqft-tier-label");
      var isOversize = button.getAttribute("data-sqft-tier-oversize") === "true";
      if (form.elements.sqft) {
        if (isOversize) {
          if (getNumber("sqft") <= 8000) form.elements.sqft.value = "";
          form.elements.sqft.placeholder = "Example: 9200";
        } else {
          form.elements.sqft.value = value;
          form.elements.sqft.placeholder = "Example: 2200";
        }
      }
      setSqftTierState(value, label);
      setSqftNote(isOversize ? OVERSIZE_SQFT_NOTE : DEFAULT_SQFT_NOTE);
      applyTierDefaults(value);
      renderCountOptions();
      if (isOversize && form.elements.sqft) form.elements.sqft.focus();
    });
  });
  if (form.elements.sqft) {
    form.elements.sqft.addEventListener("input", function () {
      if (isOversizeTierSelected()) {
        setSqftNote(OVERSIZE_SQFT_NOTE);
        if (getNumber("sqft") > 8000) applyTierDefaults("6000plus");
        renderCountOptions();
        return;
      }
      form.elements.sqft.placeholder = "Example: 2200";
      setSqftNote(DEFAULT_SQFT_NOTE);
      setSqftTierState("", "");
      setHiddenValue("pane_range", "");
      setHiddenValue("screen_range", "");
      renderCountOptions();
    });
  }
  ["panes", "screens"].forEach(function (name) {
    if (!form.elements[name]) return;
    form.elements[name].addEventListener("input", function () {
      setHiddenValue(name === "panes" ? "pane_range" : "screen_range", "");
      form.querySelectorAll('[data-count-name="' + name + '"]').forEach(function (button) {
        button.classList.remove("is-active");
      });
    });
  });

  /* ---------- Wizard ---------- */
  var STEP_TITLES = ["Service", "Home size", "Details", "Almost there", "Your range"];
  var steps = Array.prototype.slice.call(form.querySelectorAll(".q-step"));
  var backBtn = form.querySelector("[data-q-back]");
  var nextBtn = form.querySelector("[data-q-next]");
  var revealBtn = form.querySelector("[data-q-reveal]");
  var errorBox = form.querySelector("[data-q-error]");
  var titleEl = form.querySelector("[data-q-title]");
  var countEl = form.querySelector("[data-q-count]");
  var barEl = form.querySelector("[data-q-bar]");
  var currentStep = 0;
  var GATE_STEP = 3;
  var REVEAL_STEP = 4;

  function setError(message) {
    errorBox.textContent = message || "";
    errorBox.hidden = !message;
  }
  function showStep(index, scroll) {
    currentStep = Math.max(0, Math.min(index, steps.length - 1));
    steps.forEach(function (step, i) { step.classList.toggle("active", i === currentStep); });
    titleEl.textContent = STEP_TITLES[currentStep];
    countEl.textContent = "Step " + (currentStep + 1) + " of " + steps.length;
    barEl.style.width = (((currentStep + 1) / steps.length) * 100) + "%";
    backBtn.hidden = currentStep === 0 || currentStep === REVEAL_STEP;
    nextBtn.hidden = currentStep >= GATE_STEP;
    revealBtn.hidden = currentStep !== GATE_STEP;
    if (scroll) {
      var card = form.closest(".quote-card") || form;
      var top = card.getBoundingClientRect().top + window.scrollY - 84;
      window.scrollTo({ top: top, behavior: REDUCED_MOTION ? "auto" : "smooth" });
    }
  }
  function canLeaveStep(index) {
    if (index === 1) {
      if (isOversizeTierSelected() && getNumber("sqft") <= 8000) {
        setError("Enter your best estimated square footage above 8,000 so we have enough context.");
        return false;
      }
      if (!getNumber("sqft") && !getNumber("panes")) {
        setError("Add a rough home size or pane count so your estimate stays useful.");
        return false;
      }
    }
    setError("");
    return true;
  }
  backBtn.addEventListener("click", function () {
    setError("");
    showStep(currentStep - 1, true);
  });
  nextBtn.addEventListener("click", function () {
    if (!canLeaveStep(currentStep)) return;
    if (currentStep + 1 === GATE_STEP) prepareGate();
    showStep(currentStep + 1, true);
  });
  form.addEventListener("input", function () {
    if (!errorBox.hidden && (getNumber("sqft") || getNumber("panes"))) setError("");
  });

  function prepareGate() {
    var result = compute();
    updateHidden(result);
    var gateTitle = form.querySelector("[data-gate-title]");
    var preview = form.querySelector("[data-gate-preview]");
    if (result && result.oversized) {
      gateTitle.textContent = "Your custom quote request is ready.";
      if (preview) preview.textContent = "Custom quote";
    } else {
      gateTitle.textContent = "Your estimate is ready.";
      if (preview && result) preview.textContent = money(result.low) + " – " + money(result.high);
    }
  }

  /* ---------- Lead submission + reveal ---------- */
  function getLeadMessage(data) {
    var pieces = [];
    if (data.estimate_range) pieces.push("Estimate range: " + data.estimate_range);
    if (data.estimate_accuracy) pieces.push("Accuracy: " + data.estimate_accuracy);
    if (data.estimate_review_flags) pieces.push("Review flags: " + data.estimate_review_flags);
    if (data.estimate_service) pieces.push("Service: " + data.estimate_service);
    if (data.sqft_tier) pieces.push("Home size tier: " + data.sqft_tier);
    if (data.sqft) pieces.push("Square footage: " + data.sqft);
    if (data.pane_range) pieces.push("Pane range: " + data.pane_range);
    else if (data.panes) pieces.push("Panes: " + data.panes);
    if (data.screen_range) pieces.push("Screen range: " + data.screen_range);
    else if (data.screens) pieces.push("Screens: " + data.screens);
    if (data.town) pieces.push("Town: " + data.town);
    if (data.service_address) pieces.push("Service address: " + data.service_address);
    if (data.last_cleaned) pieces.push("Last cleaned: " + data.last_cleaned);
    if (data.photos_available) pieces.push("Photos available: Yes");
    if (data.preferred_timing) pieces.push("Timing: " + data.preferred_timing);
    if (data.message) pieces.push("Notes: " + data.message);
    return pieces.join(" · ");
  }

  function optionalNumber(value) {
    var parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function crmLeadPayload(data) {
    var screenCount = Number(data.screens) || 0;
    var lastCleaned = data.last_cleaned === "1-4 years"
      ? "1-4 years"
      : data.last_cleaned === "5+ years"
        ? "5+ years"
        : data.last_cleaned === "Not sure" ? "not sure" : "recent";
    return {
      contact: {
        name: data.name || "",
        phone: data.phone || "",
        email: data.email || "",
        address: data.service_address || "",
        city: data.town || "",
        notes: data.message || "",
        company: data._honey || ""
      },
      booking: {
        service: data.service === "ext" ? "ext" : "both",
        sqft: optionalNumber(data.sqft),
        paneCount: optionalNumber(data.panes),
        stories2plus: data.stories === "Yes",
        hardWater: data.hard_water === "Yes",
        lastCleaned5yr: data.last_cleaned === "5+ years",
        postConstruction: data.post_construction === "Yes",
        wantsScreens: screenCount > 0,
        screenCount: screenCount,
        frenchPanes: data.french === "Yes",
        plan: "onetime",
        town: data.town || null,
        lastCleaned: lastCleaned,
        photosAvailable: data.photos_available === "Yes",
        preferredTiming: data.preferred_timing || null,
        serviceAddress: data.service_address || null,
        notes: data.message || null
      },
      source: "form"
    };
  }

  /* Fires the Google Ads form conversion the /thanks/ page normally fires.
   * Skipped on /sandbox paths, deduped per session — mirrors ads-conversion.js. */
  function fireFormConversion() {
    try {
      if (window.location.pathname.indexOf("/sandbox") === 0) return;
      if (sessionStorage.getItem("ocs_conv_form")) return;
      if (typeof window.gtag !== "function") return;
      window.gtag("event", "conversion", { send_to: "AW-18072622126/Ng3vCL_dgMocEK6o2alD" });
      sessionStorage.setItem("ocs_conv_form", "1");
    } catch (e) { /* never block the reveal */ }
  }

  function sendLead(data) {
    var tasks = [];

    var fd = new FormData();
    Object.keys(data).forEach(function (key) {
      if (key !== "_honey") fd.append(key, data[key]);
    });
    fd.set("_subject", "New OCS instant estimate request");
    fd.set("_template", "table");
    fd.set("_captcha", "false");
    tasks.push(fetch("https://formsubmit.co/ajax/barrett@ocsllc.services", {
      method: "POST", body: fd
    }).then(function (r) { return r.ok ? "formsubmit:ok" : "formsubmit:" + r.status; })
      .catch(function () { return "formsubmit:err"; }));

    tasks.push(fetch("https://ocs-crm.vercel.app/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(crmLeadPayload(data))
    }).then(function (r) { return r.ok ? "ocs:ok" : "ocs:" + r.status; })
      .catch(function () { return "ocs:err"; }));

    return Promise.all(tasks).then(function (results) {
      return results.some(function (result) { return result.slice(-3) === ":ok"; });
    });
  }

  function renderReveal(result) {
    var confidence = getConfidence(result);
    var priceEl = form.querySelector("[data-result-price]");
    var eyebrowEl = form.querySelector("[data-result-eyebrow]");
    var detailEl = form.querySelector("[data-result-detail]");
    var confEl = form.querySelector("[data-result-confidence]");
    var oversizeEl = form.querySelector("[data-q-oversize]");
    var nextEl = form.querySelector("[data-result-next]");

    oversizeEl.hidden = !(result && result.oversized);

    if (result && result.oversized) {
      eyebrowEl.textContent = "Your quote";
      priceEl.textContent = "Custom quote";
      detailEl.textContent = "Large homes get a custom confirmed price. Your square footage, pane range, and screen range are already with our team — we’ll come back with a firm number.";
    } else if (result) {
      eyebrowEl.textContent = "Your estimated range";
      priceEl.textContent = money(result.low) + " – " + money(result.high);
      var parts = [];
      parts.push(result.service === "both" ? "Interior + exterior" : "Exterior only");
      if (result.sqft) parts.push(result.sqft.toLocaleString() + " sqft");
      if (result.panes) parts.push(result.panes + " panes");
      if (result.screens) parts.push(result.screens + " screens");
      if (result.averaged) parts.push("sqft + pane count averaged");
      if (result.french) parts.push("divided panes flagged for review");
      detailEl.textContent = parts.join(" • ") + ".";
    }
    confEl.className = "q-confidence is-" + confidence.level;
    confEl.textContent = confidence.label + " — " + confidence.text;

    var firstName = (getValue("name") || "").trim().split(/\s+/)[0];
    nextEl.textContent = (firstName ? firstName + ", we" : "We") +
      "’ll text or call you the same day to confirm your final number and find a time that works. Most jobs schedule one to two weeks out.";
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (currentStep !== GATE_STEP) return;

    var name = (getValue("name") || "").trim();
    var phone = (getValue("phone") || "").trim();
    var serviceAddress = (getValue("service_address") || "").trim();
    if (!name || !phone) {
      setError("Add your name and phone number — that’s all it takes to unlock your range.");
      return;
    }
    if (!serviceAddress) {
      setError("Add the service address so we can prepare an accurate estimate.");
      return;
    }
    var emailField = form.elements.email;
    if (emailField && emailField.value && !emailField.checkValidity()) {
      setError("That email doesn’t look right — fix it or leave it blank.");
      return;
    }
    setError("");

    var result = compute();
    updateHidden(result);
    var data = Object.fromEntries(new FormData(form).entries());
    if (data._honey) return;

    revealBtn.disabled = true;
    revealBtn.textContent = "Unlocking…";

    var note = form.querySelector("[data-submit-note]");
    sendLead(data).then(function (ok) {
      if (ok) {
        note.className = "q-submit-note ok";
        note.textContent = "Sent — we have your details and will confirm your final number.";
        fireFormConversion();
      } else {
        note.className = "q-submit-note err";
        note.textContent = "We couldn’t auto-send your request — please call or text (406) 607-2151 to lock it in.";
      }
    });

    /* Reveal immediately — the range is computed in-browser and must
     * never wait on the network. */
    renderReveal(result);
    showStep(REVEAL_STEP, true);
    revealBtn.disabled = false;
    revealBtn.textContent = "Reveal my price range";
  });

  renderCountOptions();
  showStep(0);
})();
