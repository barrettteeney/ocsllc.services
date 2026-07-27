(function () {
  "use strict";

  var CRM_BASE = "https://ocs-crm.vercel.app";

  function createKey(kind) {
    var random = "";
    try {
      random = window.crypto && typeof window.crypto.randomUUID === "function"
        ? window.crypto.randomUUID()
        : Date.now().toString(36) + "_" + Math.random().toString(36).slice(2);
    } catch (error) {
      random = Date.now().toString(36) + "_" + Math.random().toString(36).slice(2);
    }
    return String(kind || "request") + "_" + random;
  }

  function setStatus(panel, text, state) {
    var status = panel.querySelector("[data-self-booking-status]");
    if (!status) return;
    status.className = "self-booking-status" + (state ? " is-" + state : "");
    status.textContent = text || "";
  }

  function friendlyError(error) {
    if (!error || !error.status) return "We couldn’t reach the live calendar. Please try again.";
    if (error.status === 429) return "The calendar is busy right now. Wait a moment, then try again.";
    return error.message || "The booking request could not be completed.";
  }

  function dayParts(dateISO) {
    var parts = String(dateISO || "").split("-").map(Number);
    if (parts.length !== 3 || !parts[0] || !parts[1] || !parts[2]) return null;
    return new Date(parts[0], parts[1] - 1, parts[2], 12);
  }

  function formatDay(dateISO) {
    var date = dayParts(dateISO);
    if (!date) return "";
    return new Intl.DateTimeFormat("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric"
    }).format(date);
  }

  function requestJson(path, options) {
    return fetch(CRM_BASE + path, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          var error = new Error(body.error || "The request could not be completed.");
          error.status = response.status;
          error.body = body;
          throw error;
        }
        return body;
      });
    });
  }

  function open(form, options) {
    options = options || {};
    var panel = form && form.querySelector("[data-self-booking]");
    if (!panel || !options.booking || !options.leadIdempotencyKey) return;

    var fields = panel.querySelector("[data-self-booking-fields]");
    var daysWrap = panel.querySelector("[data-self-booking-days]");
    var timeStep = panel.querySelector("[data-self-booking-time-step]");
    var timesWrap = panel.querySelector("[data-self-booking-times]");
    var submit = panel.querySelector("[data-self-booking-submit]");
    var duration = panel.querySelector("[data-self-booking-duration]");
    var summary = panel.querySelector("[data-self-booking-summary]");
    var eyebrow = panel.querySelector("[data-self-booking-eyebrow]");
    var heading = panel.querySelector("[data-self-booking-heading]");
    if (!fields || !daysWrap || !timesWrap || !submit) return;

    var bookingKey = createKey("booking");
    var slotRequestId = 0;
    var selectedSummary = "";
    var reservationIsMultiDay = false;
    var slotsByDay = {};
    var selectedDayISO = "";
    var selectedSlot = null;
    var nextFromISO = null;
    var renderedDays = {};
    var moreChip = null;

    panel.hidden = false;
    fields.hidden = true;
    submit.hidden = true;
    panel.setAttribute("aria-busy", "true");
    setStatus(panel, "Loading the next available options…");

    function updateSelection() {
      selectedSummary = selectedDayISO && selectedSlot
        ? formatDay(selectedDayISO) + " at " + selectedSlot.label
        : "";
      if (summary) {
        summary.hidden = !selectedSummary;
        summary.textContent = selectedSummary ? "You’re requesting " + selectedSummary + "." : "";
      }
      submit.disabled = !selectedSummary;
      submit.textContent = selectedSlot ? "Request " + selectedSlot.label : "Choose a time to continue";
    }

    function markActive(wrap, activeValue) {
      Array.prototype.forEach.call(wrap.children, function (child) {
        var isActive = child.getAttribute("data-value") === activeValue;
        child.classList.toggle("is-active", isActive);
        child.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    }

    function renderTimes(slots) {
      timesWrap.innerHTML = "";
      slots.forEach(function (slot) {
        var chip = document.createElement("button");
        chip.type = "button";
        chip.className = "self-booking-time";
        chip.setAttribute("data-value", slot.startISO);
        chip.setAttribute("aria-pressed", "false");
        chip.textContent = slot.label;
        chip.onclick = function () {
          selectedSlot = { startISO: slot.startISO, label: slot.label };
          markActive(timesWrap, slot.startISO);
          updateSelection();
          setStatus(panel, "Review the time below, then send your request.");
        };
        timesWrap.appendChild(chip);
      });
      timeStep.hidden = !slots.length;
      if (selectedSlot && !slots.some(function (slot) { return slot.startISO === selectedSlot.startISO; })) {
        selectedSlot = null;
      }
      if (selectedSlot) markActive(timesWrap, selectedSlot.startISO);
      updateSelection();
    }

    function updateMoreChip() {
      if (moreChip) { moreChip.remove(); moreChip = null; }
      if (!nextFromISO) return;
      moreChip = document.createElement("button");
      moreChip.type = "button";
      moreChip.className = "self-booking-day self-booking-day-more";
      var caption = document.createElement("span");
      caption.textContent = "Later";
      var arrow = document.createElement("small");
      arrow.textContent = "dates \u2192";
      moreChip.appendChild(caption);
      moreChip.appendChild(arrow);
      moreChip.onclick = loadMoreDays;
      daysWrap.appendChild(moreChip);
    }

    function loadMoreDays() {
      if (!nextFromISO || !moreChip) return;
      moreChip.disabled = true;
      moreChip.firstChild.textContent = "Loading";
      var payload = {};
      for (var key in options.booking) payload[key] = options.booking[key];
      payload.fromDateISO = nextFromISO;
      requestJson("/api/booking/availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (response) {
        nextFromISO = response.nextFromDateISO || null;
        appendDays(response.days || []);
        updateMoreChip();
        var lastChip = daysWrap.querySelector(".self-booking-day:nth-last-child(" + (nextFromISO ? 2 : 1) + ")");
        if (lastChip && lastChip.scrollIntoView) {
          try { lastChip.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "end" }); } catch (e) { /* optional */ }
        }
      }).catch(function (error) {
        updateMoreChip();
        setStatus(panel, friendlyError(error) + " You can still call or text (406) 607-2151.", "error");
      });
    }

    function appendDays(days) {
      days.forEach(function (day) {
        if (renderedDays[day.dateISO]) return;
        renderedDays[day.dateISO] = true;
        slotsByDay[day.dateISO] = day.slots || [];
        daysWrap.appendChild(makeDayChip(day));
      });
    }

    function renderDays(days) {
      daysWrap.innerHTML = "";
      renderedDays = {};
      moreChip = null;
      days.forEach(function (day) {
        renderedDays[day.dateISO] = true;
        daysWrap.appendChild(makeDayChip(day));
      });
      updateMoreChip();
    }

    function makeDayChip(day) {
      return (function (day) {
        var date = dayParts(day.dateISO);
        var chip = document.createElement("button");
        chip.type = "button";
        chip.className = "self-booking-day";
        chip.setAttribute("data-value", day.dateISO);
        chip.setAttribute("aria-pressed", "false");
        var weekday = document.createElement("span");
        weekday.textContent = date
          ? new Intl.DateTimeFormat("en-US", { weekday: "short" }).format(date)
          : "";
        var dateLabel = document.createElement("small");
        dateLabel.textContent = date
          ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date)
          : day.dateISO;
        chip.appendChild(weekday);
        chip.appendChild(dateLabel);
        chip.onclick = function () { selectDay(day.dateISO); };
        return chip;
      })(day);
    }

    function refreshSlotsForDay(dateISO, message) {
      var requestId = ++slotRequestId;
      panel.setAttribute("aria-busy", "true");
      if (message) setStatus(panel, message);
      return requestJson("/api/booking/slots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ booking: options.booking, dateISO: dateISO })
      }).then(function (response) {
        if (requestId !== slotRequestId || dateISO !== selectedDayISO) return;
        var slots = response.slots || [];
        slotsByDay[dateISO] = slots;
        renderTimes(slots);
        panel.setAttribute("aria-busy", "false");
        if (!slots.length) {
          setStatus(panel, "That day is full for a job this size. Try another day.", "notice");
          return;
        }
        setStatus(panel, reservationIsMultiDay
          ? slots.length + " start time" + (slots.length === 1 ? " can" : "s can") + " begin your reserved work day on this date."
          : slots.length + " start time" + (slots.length === 1 ? " fits" : "s fit") + " your complete job on this day.");
      }).catch(function (error) {
        if (requestId !== slotRequestId || dateISO !== selectedDayISO) return;
        panel.setAttribute("aria-busy", "false");
        setStatus(panel, friendlyError(error) + " You can still call or text (406) 607-2151.", "error");
      });
    }

    function selectDay(dateISO, initialMessage) {
      selectedDayISO = dateISO;
      selectedSlot = null;
      markActive(daysWrap, dateISO);
      renderTimes(slotsByDay[dateISO] || []);
      if (initialMessage) setStatus(panel, initialMessage);
      // Always reconcile against the live calendar in the background.
      refreshSlotsForDay(dateISO);
    }

    function loadAvailability(message) {
      fields.hidden = true;
      submit.hidden = true;
      panel.setAttribute("aria-busy", "true");
      setStatus(panel, message || "Loading the next available options…");
      return requestJson("/api/booking/availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(options.booking)
      }).then(function (response) {
        var quote = response.quote || {};
        reservationIsMultiDay = !!quote.mayTakeMultipleDays;
        duration.textContent = quote.durationNote
          ? quote.durationNote
          : "Available times are sized to the estimated work in your quote.";
        duration.className = "self-booking-duration"
          + (quote.fullDay ? " is-full-day" : "")
          + (quote.mayTakeMultipleDays ? " is-multiday" : "");

        if (quote.requiresInPerson) {
          panel.setAttribute("aria-busy", "false");
          setStatus(panel, "This project needs a custom confirmed quote before scheduling. We’ll contact you directly.");
          return;
        }

        var days = response.days || [];
        if (!days.length) {
          panel.setAttribute("aria-busy", "false");
          setStatus(panel, "No online times currently fit this job. Call or text (406) 607-2151 and we’ll find a time with you.", "error");
          return;
        }

        days.forEach(function (day) { slotsByDay[day.dateISO] = day.slots || []; });
        nextFromISO = response.nextFromDateISO || null;
        renderDays(days);
        panel.setAttribute("aria-busy", "false");
        fields.hidden = false;
        submit.hidden = false;
        selectDay(days[0].dateISO, "Next available day selected. Pick a start time or choose another day.");
      }).catch(function (error) {
        if (error.body && error.body.quote && error.body.quote.durationNote) {
          duration.textContent = error.body.quote.durationNote;
        }
        panel.setAttribute("aria-busy", "false");
        setStatus(panel, friendlyError(error) + " You can still call or text (406) 607-2151.", "error");
      });
    }

    loadAvailability();

    submit.onclick = function () {
      if (!selectedSlot) return;
      submit.disabled = true;
      submit.classList.add("is-loading");
      submit.textContent = "Sending your request…";
      panel.setAttribute("aria-busy", "true");
      setStatus(panel, "Checking that this time is still available…");

      requestJson("/api/booking/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": bookingKey
        },
        body: JSON.stringify({
          contact: options.contact,
          booking: options.booking,
          leadIdempotencyKey: options.leadIdempotencyKey,
          slotStartISO: selectedSlot.startISO
        })
      }).then(function (response) {
        panel.setAttribute("aria-busy", "false");
        submit.classList.remove("is-loading");
        fields.hidden = true;
        submit.hidden = true;
        if (summary) summary.hidden = true;
        if (eyebrow) eyebrow.textContent = "Request received";
        if (heading) heading.textContent = selectedSummary || "Your time is saved";
        setStatus(panel, (response.message || "Your requested time has been saved.") + " No payment was collected.", "success");
      }).catch(function (error) {
        panel.setAttribute("aria-busy", "false");
        submit.classList.remove("is-loading");
        setStatus(panel, friendlyError(error), "error");
        submit.disabled = false;
        updateSelection();
        if (error.status === 409 && /time|reserved/i.test(error.message || "")) {
          bookingKey = createKey("booking");
          refreshSlotsForDay(selectedDayISO, "That time was just taken. Refreshing this date’s available times…");
        }
      });
    };

    try {
      panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) { /* scrolling is optional */ }
  }

  window.OCSSelfBooking = {
    createKey: createKey,
    open: open
  };
})();
