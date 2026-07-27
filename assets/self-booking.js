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

  function formatDay(dateISO) {
    var parts = String(dateISO || "").split("-").map(Number);
    if (parts.length !== 3 || !parts[0] || !parts[1] || !parts[2]) return "";
    return new Intl.DateTimeFormat("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric"
    }).format(new Date(parts[0], parts[1] - 1, parts[2], 12));
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
    var dayInput = panel.querySelector("[data-self-booking-day]");
    var timeSelect = panel.querySelector("[data-self-booking-time]");
    var submit = panel.querySelector("[data-self-booking-submit]");
    var duration = panel.querySelector("[data-self-booking-duration]");
    var summary = panel.querySelector("[data-self-booking-summary]");
    var eyebrow = panel.querySelector("[data-self-booking-eyebrow]");
    var heading = panel.querySelector("[data-self-booking-heading]");
    var bookingKey = createKey("booking");
    var slotRequestId = 0;
    var selectedSummary = "";
    var reservationIsMultiDay = false;

    panel.hidden = false;
    fields.hidden = true;
    submit.hidden = true;
    panel.setAttribute("aria-busy", "true");
    setStatus(panel, "Loading the next available options…");

    function updateSelection() {
      var selected = timeSelect.options[timeSelect.selectedIndex];
      selectedSummary = dayInput.value && timeSelect.value && selected
        ? formatDay(dayInput.value) + " at " + selected.textContent
        : "";
      if (summary) {
        summary.hidden = !selectedSummary;
        summary.textContent = selectedSummary ? "You’re requesting " + selectedSummary + "." : "";
      }
      submit.disabled = !selectedSummary;
      submit.textContent = selectedSummary ? "Request " + selected.textContent : "Choose a time to continue";
    }

    function renderTimes(slots) {
      timeSelect.innerHTML = "";
      var prompt = document.createElement("option");
      prompt.value = "";
      prompt.textContent = slots.length ? "Choose a start time" : "No times available";
      prompt.disabled = true;
      prompt.selected = true;
      timeSelect.appendChild(prompt);
      slots.forEach(function (slot) {
        var option = document.createElement("option");
        option.value = slot.startISO;
        option.textContent = slot.label;
        timeSelect.appendChild(option);
      });
      timeSelect.disabled = !slots.length;
      updateSelection();
    }

    timeSelect.onchange = function () {
      updateSelection();
      if (timeSelect.value) setStatus(panel, "Review the time below, then send your request.");
    };

    function loadSlotsForDay(message) {
      if (!dayInput.value) {
        renderTimes([]);
        submit.disabled = true;
        setStatus(panel, "Choose a day to see the start times that fit your job.");
        return Promise.resolve();
      }

      var requestId = ++slotRequestId;
      timeSelect.disabled = true;
      submit.disabled = true;
      submit.textContent = "Checking times…";
      panel.setAttribute("aria-busy", "true");
      setStatus(panel, message || "Checking that day against the live calendar…");
      return requestJson("/api/booking/slots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ booking: options.booking, dateISO: dayInput.value })
      }).then(function (response) {
        if (requestId !== slotRequestId) return;
        var slots = response.slots || [];
        renderTimes(slots);
        panel.setAttribute("aria-busy", "false");
        fields.hidden = false;
        submit.hidden = false;
        if (!slots.length) {
          setStatus(panel, "That day is full for a job this size. Try another day.", "notice");
          return;
        }
        setStatus(panel, reservationIsMultiDay
          ? slots.length + " start time" + (slots.length === 1 ? " can" : "s can") + " begin your reserved work day on this date."
          : slots.length + " start time" + (slots.length === 1 ? " fits" : "s fit") + " your complete job on this day.");
      }).catch(function (error) {
        if (requestId !== slotRequestId) return;
        renderTimes([]);
        panel.setAttribute("aria-busy", "false");
        setStatus(panel, friendlyError(error) + " You can still call or text (406) 607-2151.", "error");
      });
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

        if (response.bookingWindow) {
          dayInput.min = response.bookingWindow.minDate || "";
          dayInput.max = response.bookingWindow.maxDate || "";
        }
        dayInput.value = days[0].dateISO;
        renderTimes(days[0].slots || []);
        dayInput.onchange = function () { loadSlotsForDay(); };
        panel.setAttribute("aria-busy", "false");
        fields.hidden = false;
        submit.hidden = false;
        updateSelection();
        setStatus(panel, "Next available day selected. Pick a start time or choose another day.");
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
      if (!timeSelect.value) return;
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
          slotStartISO: timeSelect.value
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
          loadSlotsForDay("That time was just taken. Refreshing this date’s available times…");
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
