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
    var bookingKey = createKey("booking");
    var slotRequestId = 0;

    panel.hidden = false;
    fields.hidden = true;
    submit.hidden = true;
    setStatus(panel, "Checking the calendar for times that fit your quoted job…");

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
      submit.disabled = !timeSelect.value;
    }

    timeSelect.onchange = function () {
      submit.disabled = !timeSelect.value;
    };

    function loadSlotsForDay(message) {
      if (!dayInput.value) {
        renderTimes([]);
        submit.disabled = true;
        setStatus(panel, "Choose a date to see every available start time.");
        return Promise.resolve();
      }

      var requestId = ++slotRequestId;
      timeSelect.disabled = true;
      submit.disabled = true;
      submit.textContent = "Request this time";
      setStatus(panel, message || "Checking every available time for that date…");
      return requestJson("/api/booking/slots", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ booking: options.booking, dateISO: dayInput.value })
      }).then(function (response) {
        if (requestId !== slotRequestId) return;
        var slots = response.slots || [];
        renderTimes(slots);
        fields.hidden = false;
        submit.hidden = false;
        if (!slots.length) {
          setStatus(panel, "No times fit this job on that date. Choose another day from the calendar.", "error");
          return;
        }
        setStatus(panel, "Choose any available start time shown for this date.");
      }).catch(function (error) {
        if (requestId !== slotRequestId) return;
        renderTimes([]);
        setStatus(panel, error.message + " You can still call or text (406) 607-2151.", "error");
      });
    }

    function loadAvailability(message) {
      fields.hidden = true;
      submit.hidden = true;
      setStatus(panel, message || "Checking the calendar for times that fit your quoted job…");
      return requestJson("/api/booking/availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(options.booking)
      }).then(function (response) {
        duration.textContent = response.quote && response.quote.durationNote
          ? response.quote.durationNote
          : "Available times are sized to the estimated work in your quote.";

        if (response.quote && response.quote.requiresInPerson) {
          setStatus(panel, "This project needs a custom confirmed quote before scheduling. We’ll contact you directly.");
          return;
        }

        var days = response.days || [];
        if (!days.length) {
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
        fields.hidden = false;
        submit.hidden = false;
        submit.disabled = !timeSelect.value;
        submit.textContent = "Request this time";
        setStatus(panel, "Choose any date in the calendar, then select an available start time.");
      }).catch(function (error) {
        if (error.body && error.body.quote && error.body.quote.durationNote) {
          duration.textContent = error.body.quote.durationNote;
        }
        setStatus(panel, error.message + " You can still call or text (406) 607-2151.", "error");
      });
    }

    loadAvailability();

    submit.onclick = function () {
      if (!timeSelect.value) return;
      submit.disabled = true;
      submit.textContent = "Reserving…";
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
        fields.hidden = true;
        submit.hidden = true;
        setStatus(panel, response.message || "Your requested time has been saved.", "success");
      }).catch(function (error) {
        setStatus(panel, error.message, "error");
        submit.disabled = false;
        submit.textContent = "Request this time";
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
