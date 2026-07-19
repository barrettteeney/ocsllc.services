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
    var daySelect = panel.querySelector("[data-self-booking-day]");
    var timeSelect = panel.querySelector("[data-self-booking-time]");
    var submit = panel.querySelector("[data-self-booking-submit]");
    var duration = panel.querySelector("[data-self-booking-duration]");
    var days = [];
    var bookingKey = createKey("booking");

    panel.hidden = false;
    fields.hidden = true;
    submit.hidden = true;
    setStatus(panel, "Checking the calendar for times that fit your quoted job…");

    function renderTimes() {
      var selected = days.filter(function (day) { return day.dateISO === daySelect.value; })[0];
      timeSelect.innerHTML = "";
      (selected ? selected.slots : []).forEach(function (slot) {
        var option = document.createElement("option");
        option.value = slot.startISO;
        option.textContent = slot.label;
        timeSelect.appendChild(option);
      });
      submit.disabled = !timeSelect.value;
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

        days = response.days || [];
        if (!days.length) {
          setStatus(panel, "No online times currently fit this job. Call or text (406) 607-2151 and we’ll find a time with you.", "error");
          return;
        }

        daySelect.innerHTML = "";
        days.forEach(function (day) {
          var option = document.createElement("option");
          option.value = day.dateISO;
          option.textContent = day.dayLabel;
          daySelect.appendChild(option);
        });
        renderTimes();
        daySelect.onchange = renderTimes;
        fields.hidden = false;
        submit.hidden = false;
        submit.disabled = !timeSelect.value;
        submit.textContent = "Request this time";
        setStatus(panel, "Select a day and start time. We’ll reserve it with this quote.");
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
          loadAvailability("That time was just taken. Refreshing the available times…");
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
