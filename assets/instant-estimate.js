(function () {
  var SQFT_TIERS = [
    { max: 1000, both: 0.15, ext: 0.09 },
    { max: 2000, both: 0.17, ext: 0.10 },
    { max: 3000, both: 0.19, ext: 0.11 },
    { max: 4000, both: 0.21, ext: 0.13 },
    { max: 5000, both: 0.23, ext: 0.14 },
    { max: 6000, both: 0.25, ext: 0.15 }
  ];
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
        label: "Needs review",
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
    var confidenceBox = form.querySelector("[data-estimate-confidence]");
    var confidenceLabel = form.querySelector("[data-confidence-label]");
    var confidenceText = form.querySelector("[data-confidence-text]");
    var flagsList = form.querySelector("[data-estimate-flags]");

    if (!box || !price || !detail) return;
    updateHidden(form, result);

    if (warning) warning.classList.toggle("show", !!(result && result.oversized));

    function renderConfidence(current) {
      var confidence = getConfidence(form, current);
      if (confidenceBox) {
        confidenceBox.className = "estimate-confidence is-" + confidence.level;
      }
      if (confidenceLabel) confidenceLabel.textContent = confidence.label;
      if (confidenceText) confidenceText.textContent = confidence.text;
      if (flagsList) {
        var flags = current ? getReviewFlags(form, current) : [];
        flagsList.textContent = flags.length ? "Review flags: " + flags.join(", ") : "No accuracy flags selected.";
      }
    }

    if (!result) {
      box.classList.add("is-empty");
      price.textContent = "Enter a size";
      detail.textContent = "Use a rough square footage or tap one of the common home sizes.";
      renderConfidence(result);
      return;
    }

    if (result.oversized) {
      box.classList.add("is-empty");
      price.textContent = "Custom quote";
      detail.textContent = "Homes over 6,000 sqft need a quick review so the price is accurate.";
      renderConfidence(result);
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
    renderConfidence(result);
  }

  function setSqftTierState(form, value, label) {
    form.querySelectorAll("[data-sqft-tier-value]").forEach(function (button) {
      button.classList.toggle("is-active", button.getAttribute("data-sqft-tier-value") === String(value));
    });
    if (form.elements.sqft_tier) form.elements.sqft_tier.value = label || "";
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
    var confidence = grid.querySelector(":scope > [data-estimate-confidence]");
    var warning = grid.querySelector(":scope > [data-estimate-warning]");
    var steps = [
      { title: "Service", items: [fieldsets[0]] },
      { title: "Home size", items: [rows[0]] },
      { title: "Screens + town", items: [rows[1]] },
      { title: "Condition", items: [fieldsets[1]] },
      { title: "Estimate", items: [result, confidence, warning] },
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
      if (steps[index] && steps[index].title === "Home size" && !getNumber(form, "sqft") && !getNumber(form, "panes")) {
        setError("Add a rough home size or pane count so the estimate stays useful.");
        return false;
      }
      setError("");
      return true;
    }

    function showStep(index) {
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
    }

    prev.addEventListener("click", function () {
      setError("");
      showStep(current - 1);
    });

    next.addEventListener("click", function () {
      if (!canLeaveStep(current)) return;
      render(form);
      showStep(current + 1);
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
    if (data.sqft) pieces.push("Sqft: " + data.sqft);
    if (data.panes) pieces.push("Panes: " + data.panes);
    if (data.screens) pieces.push("Screens: " + data.screens);
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
        if (form.elements.sqft) form.elements.sqft.value = value;
        setSqftTierState(form, value, label);
        render(form);
      });
    });
    if (form.elements.sqft) {
      form.elements.sqft.addEventListener("input", function () {
        setSqftTierState(form, "", "");
      });
    }
    makeWizard(form);
    wireSubmit(form);
    render(form);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".instant-estimate").forEach(init);
  });
})();
