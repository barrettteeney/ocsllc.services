(function () {
  var SQFT_TIERS = [
    {
      max: 1000,
      both: 0.15,
      ext: 0.09,
      sqftLabel: "Up to 1,000 sqft",
      panes: [
        { label: "6-10 panes", value: 8 },
        { label: "11-15 panes", value: 13 },
        { label: "16-20 panes", value: 18 }
      ],
      screens: [
        { label: "No screens", value: 0 },
        { label: "1-6 screens", value: 4 },
        { label: "7-12 screens", value: 10 }
      ]
    },
    {
      max: 2000,
      both: 0.17,
      ext: 0.10,
      sqftLabel: "1,001-2,000 sqft",
      panes: [
        { label: "12-18 panes", value: 15 },
        { label: "19-25 panes", value: 22 },
        { label: "26-32 panes", value: 29 }
      ],
      screens: [
        { label: "No screens", value: 0 },
        { label: "1-5 screens", value: 3 },
        { label: "6-12 screens", value: 9 },
        { label: "13-20 screens", value: 16 }
      ]
    },
    {
      max: 3000,
      both: 0.19,
      ext: 0.11,
      sqftLabel: "2,001-3,000 sqft",
      panes: [
        { label: "20-28 panes", value: 24 },
        { label: "29-36 panes", value: 33 },
        { label: "37-45 panes", value: 41 }
      ],
      screens: [
        { label: "No screens", value: 0 },
        { label: "1-9 screens", value: 5 },
        { label: "10-18 screens", value: 14 },
        { label: "19-28 screens", value: 24 }
      ]
    },
    {
      max: 4000,
      both: 0.21,
      ext: 0.13,
      sqftLabel: "3,001-4,000 sqft",
      panes: [
        { label: "30-38 panes", value: 34 },
        { label: "39-48 panes", value: 44 },
        { label: "49-60 panes", value: 55 }
      ],
      screens: [
        { label: "No screens", value: 0 },
        { label: "1-14 screens", value: 7 },
        { label: "15-25 screens", value: 20 },
        { label: "26-38 screens", value: 32 }
      ]
    },
    {
      max: 5000,
      both: 0.23,
      ext: 0.14,
      sqftLabel: "4,001-5,000 sqft",
      panes: [
        { label: "40-50 panes", value: 45 },
        { label: "51-62 panes", value: 56 },
        { label: "63-75 panes", value: 69 }
      ],
      screens: [
        { label: "No screens", value: 0 },
        { label: "1-19 screens", value: 10 },
        { label: "20-32 screens", value: 26 },
        { label: "33-48 screens", value: 40 }
      ]
    },
    {
      max: 6000,
      both: 0.25,
      ext: 0.15,
      sqftLabel: "5,001-6,000 sqft",
      panes: [
        { label: "50-65 panes", value: 58 },
        { label: "66-80 panes", value: 73 },
        { label: "81-100 panes", value: 90 }
      ],
      screens: [
        { label: "No screens", value: 0 },
        { label: "1-24 screens", value: 12 },
        { label: "25-40 screens", value: 32 },
        { label: "41-60 screens", value: 50 }
      ]
    }
  ];
  var DEFAULT_SQFT_NOTE = "Know the square footage? Enter it above. If not, choose the range your home falls in.";
  var OVERSIZE_SQFT_LABEL = "6,000+ sqft";
  var OVERSIZE_SQFT_NOTE = "Enter your best estimated square footage for the home, then choose the closest pane and screen ranges below.";
  var PER_PANE = { ext: 8, both: 14, screen: 4 };
  var MIN_CHARGE = 150;

  function money(value) {
    return "$" + Math.round(value).toLocaleString();
  }

  function roundTo(value, step) {
    return Math.round(value / step) * step;
  }

  function getNumber(form, name) {
    var field = form.elements[name];
    var value = field ? parseFloat(field.value) : 0;
    return Number.isFinite(value) && value > 0 ? value : 0;
  }

  function getValue(form, name) {
    var field = form.elements[name];
    if (!field) return "";
    if (field.length) {
      for (var i = 0; i < field.length; i += 1) {
        if (field[i].checked) return field[i].value;
      }
      return "";
    }
    return field.value || "";
  }

  function makeRangeLabel(low, high, unit, isPlus) {
    return low.toLocaleString() + "-" + high.toLocaleString() + (isPlus ? "+" : "") + " " + unit;
  }

  function makeRange(low, high, unit, factor, isPlus, keepLow) {
    var scaledLow = keepLow ? low : Math.max(1, Math.round(low * factor));
    var scaledHigh = Math.max(scaledLow, Math.round(high * factor));
    return {
      label: makeRangeLabel(scaledLow, scaledHigh, unit, isPlus),
      value: Math.round((scaledLow + scaledHigh) / 2)
    };
  }

  function makeExplicitRange(low, high, unit, isPlus) {
    return {
      label: makeRangeLabel(low, high, unit, isPlus),
      value: Math.round((low + high) / 2)
    };
  }

  function getOversizeGuidanceTier(sqft) {
    var factor = sqft && sqft > 6000 ? sqft / 6000 : 1;
    var paneHigh1 = Math.round(110 * factor);
    var paneHigh2 = Math.max(paneHigh1 + 1, Math.round(150 * factor));
    var paneHigh3 = Math.max(paneHigh2 + 1, Math.round(200 * factor));
    var screenHigh1 = Math.round(30 * factor);
    var screenHigh2 = Math.max(screenHigh1 + 1, Math.round(60 * factor));
    var screenHigh3 = Math.max(screenHigh2 + 1, Math.round(90 * factor));
    return {
      max: Infinity,
      sqftLabel: sqft && sqft > 6000 ? sqft.toLocaleString() + " sqft / 6,000+ home" : OVERSIZE_SQFT_LABEL,
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

  function getService(form) {
    var checked = form.querySelector('input[name="service"]:checked');
    return checked ? checked.value : "both";
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

  function isOversizeTierSelected(form) {
    return getValue(form, "sqft_tier") === OVERSIZE_SQFT_LABEL;
  }

  function getGuidanceTier(form) {
    if (isOversizeTierSelected(form)) return getOversizeGuidanceTier(getNumber(form, "sqft"));
    return getTierForSqft(getNumber(form, "sqft"));
  }

  function setHiddenValue(form, name, value) {
    var field = form.elements[name];
    if (field) field.value = value || "";
  }

  function setSqftNote(form, message) {
    var note = form.querySelector("[data-sqft-note]");
    if (note) note.textContent = message || DEFAULT_SQFT_NOTE;
  }

  function setCountChoice(form, name, value, label) {
    if (form.elements[name]) form.elements[name].value = String(value);
    setHiddenValue(form, name === "panes" ? "pane_range" : "screen_range", label);
    form.querySelectorAll('[data-count-name="' + name + '"]').forEach(function (button) {
      button.classList.toggle("is-active", button.getAttribute("data-count-label") === label);
    });
    render(form);
  }

  function renderCountOptions(form) {
    var tier = getGuidanceTier(form);
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
        button.className = "estimate-chip";
        button.setAttribute("data-count-name", name);
        button.setAttribute("data-count-label", option.label);
        button.setAttribute("data-count-value", String(option.value));
        button.textContent = option.label;
        button.addEventListener("click", function () {
          setCountChoice(form, name, option.value, option.label);
        });
        wrap.appendChild(button);
      });
    }

    if (!tier) {
      if (paneWrap) paneWrap.innerHTML = "";
      if (screenWrap) screenWrap.innerHTML = "";
      if (paneNote) paneNote.textContent = "Pick a home size above and we will suggest common pane-count ranges.";
      if (screenNote) screenNote.textContent = "Choose no screens or tap a common range after selecting home size.";
      return;
    }

    if (paneNote) paneNote.textContent = "Common pane-count ranges for " + tier.sqftLabel + ". Choose the closest one.";
    if (screenNote) screenNote.textContent = "Screen ranges for " + tier.sqftLabel + ". Choose no screens if you do not want screens cleaned.";
    paint(paneWrap, "panes", tier.panes);
    paint(screenWrap, "screens", tier.screens);

    var currentPaneRange = getValue(form, "pane_range");
    var currentScreenRange = getValue(form, "screen_range");
    if (currentPaneRange) {
      form.querySelectorAll('[data-count-name="panes"]').forEach(function (button) {
        button.classList.toggle("is-active", button.getAttribute("data-count-label") === currentPaneRange);
      });
    }
    if (currentScreenRange) {
      form.querySelectorAll('[data-count-name="screens"]').forEach(function (button) {
        button.classList.toggle("is-active", button.getAttribute("data-count-label") === currentScreenRange);
      });
    }
  }

  function withSurcharges(base, form) {
    var pct = 0;
    if (form.elements.stories && form.elements.stories.checked) pct += 0.10;
    if (form.elements.hard_water && form.elements.hard_water.checked) pct += 0.20;
    if ((form.elements.neglected && form.elements.neglected.checked) || getValue(form, "last_cleaned") === "5+ years") pct += 0.15;
    if (form.elements.post_construction && form.elements.post_construction.checked) pct += 0.25;
    return base + base * pct;
  }

  function getReviewFlags(form, result) {
    var flags = [];
    if (result && result.oversized) flags.push("over 6,000 sqft");
    if (form.elements.hard_water && form.elements.hard_water.checked) flags.push("hard water");
    if (getValue(form, "last_cleaned") === "5+ years" || (form.elements.neglected && form.elements.neglected.checked)) flags.push("5+ years since cleaning");
    if (form.elements.post_construction && form.elements.post_construction.checked) flags.push("post-construction");
    if (form.elements.french && form.elements.french.checked) flags.push("divided-light panes");
    if (form.elements.stories && form.elements.stories.checked) flags.push("two or more stories");
    return flags;
  }

  function getConfidence(form, result) {
    if (!result || result.oversized) {
      return {
        label: "Needs details",
        text: "Enter a home size to start. Large or unusual jobs are best confirmed by Barrett.",
        level: "low"
      };
    }

    var flags = getReviewFlags(form, result);
    if (result.sqft && result.panes && !flags.length) {
      return {
        label: "Tighter range",
        text: "Square footage and pane count are both included.",
        level: "high"
      };
    }
    if (result.sqft && !flags.length) {
      return {
        label: "Good starting range",
        text: "Add a pane count or text photos if you want Barrett to tighten it.",
        level: "medium"
      };
    }
    return {
      label: "Barrett should confirm",
      text: flags.length ? "Flagged for " + flags.join(", ") + "." : "A quick review will keep the quote accurate.",
      level: "review"
    };
  }

  function compute(form) {
    var service = getService(form);
    var sqft = getNumber(form, "sqft");
    var panes = getNumber(form, "panes");
    var screens = getNumber(form, "screens");
    var sqftBase = baseFromSqft(sqft, service);
    var paneBase = panes ? panes * PER_PANE[service] : 0;
    var paths = [];

    if (sqftBase === null) {
      return { oversized: true };
    }

    if (sqftBase) paths.push(withSurcharges(sqftBase, form));
    if (paneBase) paths.push(withSurcharges(paneBase, form));
    if (!paths.length) return null;

    var total = paths.reduce(function (sum, item) { return sum + item; }, 0) / paths.length;
    if (screens) total += screens * PER_PANE.screen;
    if (total < MIN_CHARGE) total = MIN_CHARGE;

    var low = Math.max(MIN_CHARGE, roundTo(total * 0.85, 5));
    var high = roundTo(total * 1.15, 5);
    if (high - low < 25) high = low + 25;

    return {
      low: low,
      high: high,
      total: total,
      service: service,
      sqft: sqft,
      panes: panes,
      screens: screens,
      averaged: sqftBase && paneBase,
      french: !!(form.elements.french && form.elements.french.checked),
      flags: getReviewFlags(form, null)
    };
  }

  function updateHidden(form, result) {
    var confidence = getConfidence(form, result);
    var fields = {
      estimate_range: result && !result.oversized ? money(result.low) + " - " + money(result.high) : "",
      estimate_internal_total: result && !result.oversized ? Math.round(result.total).toString() : "",
      estimate_service: result ? (result.service === "both" ? "Interior + exterior" : "Exterior only") : "",
      estimate_accuracy: confidence.label,
      estimate_review_flags: result ? getReviewFlags(form, result).join(", ") : "",
      estimate_notes: result && result.french ? "REVIEW: divided-light/French panes may need manual price adjustment." : ""
    };

    Object.keys(fields).forEach(function (name) {
      var input = form.querySelector('input[name="' + name + '"]');
      if (input) input.value = fields[name];
    });
  }

  function render(form) {
    var result = compute(form);
    var box = form.querySelector("[data-estimate-result]");
    var price = form.querySelector("[data-estimate-price]");
    var detail = form.querySelector("[data-estimate-detail]");
    var warning = form.querySelector("[data-estimate-warning]");
    renderCountOptions(form);

    if (!box || !price || !detail) return;
    updateHidden(form, result);

    if (warning) warning.classList.toggle("show", !!(result && result.oversized));

    if (!result) {
      box.classList.add("is-empty");
      price.textContent = "Enter a size";
      detail.textContent = "Use a rough square footage or tap one of the common home sizes.";
      return;
    }

    if (result.oversized) {
      box.classList.add("is-empty");
      price.textContent = "Custom quote";
      detail.textContent = "Large homes need Barrett to confirm the final price. Your sqft, pane range, and screen range still help tighten the quote.";
      return;
    }

    box.classList.remove("is-empty");
    price.textContent = money(result.low) + " - " + money(result.high);

    var parts = [];
    parts.push(result.service === "both" ? "Interior + exterior" : "Exterior only");
    if (result.sqft) parts.push(result.sqft.toLocaleString() + " sqft");
    if (result.panes) parts.push(result.panes + " panes");
    if (result.screens) parts.push(result.screens + " screens");
    if (result.averaged) parts.push("sqft + pane count averaged");
    if (result.french) parts.push("divided panes flagged for review");
    detail.textContent = parts.join(" • ") + ". Final price may change after an on-site look.";
  }

  function setSqftTierState(form, value, label) {
    form.querySelectorAll("[data-sqft-tier-value]").forEach(function (button) {
      button.classList.toggle("is-active", button.getAttribute("data-sqft-tier-value") === String(value));
    });
    if (form.elements.sqft_tier) form.elements.sqft_tier.value = label || "";
  }

  function applyTierDefaults(form, value) {
    var tier = value === "6000plus" ? getOversizeGuidanceTier(getNumber(form, "sqft")) : getTierForSqft(parseFloat(value));
    if (!tier) return;
    var middlePane = tier.panes[1] || tier.panes[0];
    var noScreens = tier.screens[0];
    if (middlePane) {
      if (form.elements.panes) form.elements.panes.value = String(middlePane.value);
      setHiddenValue(form, "pane_range", middlePane.label);
    }
    if (noScreens && form.elements.screens && !form.elements.screens.value) {
      form.elements.screens.value = String(noScreens.value);
      setHiddenValue(form, "screen_range", noScreens.label);
    }
  }

  function makeWizard(form) {
    var grid = form.querySelector(".estimate-grid");
    var actions = form.querySelector(".estimate-actions");
    var submit = form.querySelector(".estimate-submit");
    if (!grid || !actions || !submit || form.dataset.wizardReady === "true") return;

    var fieldsets = Array.prototype.slice.call(grid.querySelectorAll(":scope > .estimate-fieldset"));
    var rows = Array.prototype.slice.call(grid.querySelectorAll(":scope > .estimate-row"));
    var notes = grid.querySelector(":scope > label .estimate-textarea");
    var noteWrap = notes ? notes.closest("label") : null;
    var result = grid.querySelector(":scope > [data-estimate-result]");
    var warning = grid.querySelector(":scope > [data-estimate-warning]");
    var steps = [
      { title: "Service", items: [fieldsets[0]] },
      { title: "Home size", items: [rows[0]] },
      { title: "Screens + town", items: [rows[1]] },
      { title: "Condition", items: [fieldsets[1]] },
      { title: "Estimate", items: [result, warning] },
      { title: "Contact", items: [rows[2], rows[3], noteWrap] }
    ].map(function (step) {
      step.items = step.items.filter(Boolean);
      return step;
    }).filter(function (step) {
      return step.items.length;
    });

    if (steps.length < 2) return;

    form.dataset.wizardReady = "true";
    form.classList.add("is-wizard");

    steps.forEach(function (step, index) {
      step.items.forEach(function (item) {
        item.classList.add("estimate-step");
        item.setAttribute("data-step-index", String(index));
      });
    });

    var progress = document.createElement("div");
    progress.className = "estimate-progress";
    progress.setAttribute("aria-live", "polite");
    progress.innerHTML = '<span data-step-count></span><strong data-step-title></strong><span class="estimate-progress-bar"><span data-step-bar></span></span>';
    grid.parentNode.insertBefore(progress, grid);

    var error = document.createElement("div");
    error.className = "estimate-wizard-error";
    error.setAttribute("role", "alert");
    error.hidden = true;
    progress.insertAdjacentElement("afterend", error);

    var prev = document.createElement("button");
    prev.type = "button";
    prev.className = "estimate-back";
    prev.textContent = "Back";

    var next = document.createElement("button");
    next.type = "button";
    next.className = "estimate-next";
    next.textContent = "Next";

    actions.insertBefore(prev, actions.firstChild);
    actions.insertBefore(next, submit);

    var current = 0;

    function setError(message) {
      error.textContent = message || "";
      error.hidden = !message;
    }

    function canLeaveStep(index) {
      if (steps[index] && steps[index].title === "Home size") {
        if (isOversizeTierSelected(form) && getNumber(form, "sqft") <= 6000) {
          setError("Enter your best estimated square footage above 6,000 so Barrett has enough context.");
          return false;
        }
        if (!getNumber(form, "sqft") && !getNumber(form, "panes")) {
          setError("Add a rough home size or pane count so the estimate stays useful.");
          return false;
        }
      }
      setError("");
      return true;
    }

    function showStep(index, shouldScroll) {
      current = Math.max(0, Math.min(index, steps.length - 1));
      steps.forEach(function (step, stepIndex) {
        step.items.forEach(function (item) {
          item.hidden = stepIndex !== current;
        });
      });

      var count = progress.querySelector("[data-step-count]");
      var title = progress.querySelector("[data-step-title]");
      var bar = progress.querySelector("[data-step-bar]");
      if (count) count.textContent = "Step " + (current + 1) + " of " + steps.length;
      if (title) title.textContent = steps[current].title;
      if (bar) bar.style.width = (((current + 1) / steps.length) * 100) + "%";

      prev.hidden = current === 0;
      next.hidden = current === steps.length - 1;
      submit.hidden = current !== steps.length - 1;
      if (current === steps.length - 1) submit.textContent = "Send estimate request";
      if (shouldScroll && progress.scrollIntoView) {
        setTimeout(function () {
          progress.scrollIntoView({ block: "start", behavior: "smooth" });
        }, 0);
      }
    }

    prev.addEventListener("click", function () {
      setError("");
      showStep(current - 1, true);
    });

    next.addEventListener("click", function () {
      if (!canLeaveStep(current)) return;
      render(form);
      showStep(current + 1, true);
    });

    form.addEventListener("input", function () {
      if (!error.hidden && (getNumber(form, "sqft") || getNumber(form, "panes"))) setError("");
    });

    showStep(0);
  }

  function getLeadMessage(form, data) {
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
    if (data.last_cleaned) pieces.push("Last cleaned: " + data.last_cleaned);
    if (data.preferred_timing) pieces.push("Timing: " + data.preferred_timing);
    if (data.message) pieces.push("Notes: " + data.message);
    return pieces.join(" · ");
  }

  function wireSubmit(form) {
    if (form.dataset.submitReady === "true") return;
    form.dataset.submitReady = "true";

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      render(form);

      var data = Object.fromEntries(new FormData(form).entries());
      if (data._honey) return;

      var submit = form.querySelector(".estimate-submit");
      var originalText = submit ? submit.textContent : "";
      if (submit) {
        submit.disabled = true;
        submit.textContent = "Sending...";
      }

      var status = form.querySelector("[data-estimate-submit-status]");
      if (!status) {
        status = document.createElement("div");
        status.className = "estimate-submit-status";
        status.setAttribute("data-estimate-submit-status", "");
        form.querySelector(".estimate-actions").insertAdjacentElement("beforebegin", status);
      }
      status.className = "estimate-submit-status";
      status.textContent = "Sending your estimate request...";

      var leadMessage = getLeadMessage(form, data);
      var tasks = [];

      var fd = new FormData();
      Object.keys(data).forEach(function (key) {
        if (key !== "_honey") fd.append(key, data[key]);
      });
      fd.set("_subject", "New OCS instant estimate request");
      fd.set("_template", "table");
      fd.set("_captcha", "false");
      tasks.push(fetch("https://formsubmit.co/ajax/barrett@ocsllc.services", {
        method: "POST",
        body: fd
      }).then(function (response) {
        return response.ok ? "formsubmit:ok" : "formsubmit:" + response.status;
      }).catch(function () {
        return "formsubmit:err";
      }));

      tasks.push(fetch("https://ocs-crm.vercel.app/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: data.name || "",
          phone: data.phone || "",
          email: data.email || "",
          city: data.town || "",
          message: leadMessage,
          source: "form",
          company: data._honey || ""
        })
      }).then(function (response) {
        return response.ok ? "ocs:ok" : "ocs:" + response.status;
      }).catch(function () {
        return "ocs:err";
      }));

      Promise.all(tasks).then(function (results) {
        var ok = results.some(function (result) { return result.slice(-3) === ":ok"; });
        if (!ok) throw new Error("All lead endpoints failed");
        status.className = "estimate-submit-status is-success";
        status.textContent = "Thanks. We got it and will text or call you back the same day.";
        form.reset();
        render(form);
        setTimeout(function () {
          window.location.href = "/thanks/";
        }, 900);
      }).catch(function () {
        status.className = "estimate-submit-status is-error";
        status.textContent = "Something went wrong. Please call or text (406) 607-2151.";
        if (submit) {
          submit.disabled = false;
          submit.textContent = originalText || "Send estimate request";
        }
      });
    });
  }

  function init(form) {
    form.addEventListener("input", function () { render(form); });
    form.addEventListener("change", function () { render(form); });
    form.querySelectorAll("[data-sqft-tier-value]").forEach(function (button) {
      button.addEventListener("click", function () {
        var value = button.getAttribute("data-sqft-tier-value");
        var label = button.getAttribute("data-sqft-tier-label");
        var isOversize = button.getAttribute("data-sqft-tier-oversize") === "true";
        if (form.elements.sqft) {
          if (isOversize) {
            if (getNumber(form, "sqft") <= 6000) form.elements.sqft.value = "";
            form.elements.sqft.placeholder = "Example: 7200";
          } else {
            form.elements.sqft.value = value;
            form.elements.sqft.placeholder = "Example: 2200";
          }
        }
        setSqftTierState(form, value, label);
        setSqftNote(form, isOversize ? OVERSIZE_SQFT_NOTE : DEFAULT_SQFT_NOTE);
        applyTierDefaults(form, value);
        render(form);
        if (isOversize && form.elements.sqft) form.elements.sqft.focus();
      });
    });
    if (form.elements.sqft) {
      form.elements.sqft.addEventListener("input", function () {
        if (isOversizeTierSelected(form)) {
          setSqftNote(form, OVERSIZE_SQFT_NOTE);
          if (getNumber(form, "sqft") > 6000) applyTierDefaults(form, "6000plus");
          return;
        }
        form.elements.sqft.placeholder = "Example: 2200";
        setSqftNote(form, DEFAULT_SQFT_NOTE);
        setSqftTierState(form, "", "");
        setHiddenValue(form, "pane_range", "");
        setHiddenValue(form, "screen_range", "");
      });
    }
    ["panes", "screens"].forEach(function (name) {
      if (!form.elements[name]) return;
      form.elements[name].addEventListener("input", function () {
        setHiddenValue(form, name === "panes" ? "pane_range" : "screen_range", "");
        form.querySelectorAll('[data-count-name="' + name + '"]').forEach(function (button) {
          button.classList.remove("is-active");
        });
      });
    });
    makeWizard(form);
    wireSubmit(form);
    render(form);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".instant-estimate").forEach(init);
  });
})();
