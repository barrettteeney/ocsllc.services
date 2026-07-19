(function () {
  "use strict";

  var API_BASE = /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname)
    ? "http://localhost:3000"
    : "https://ocs-crm.vercel.app";
  var form = document.getElementById("booking-test-form");
  var findButton = document.getElementById("find-times");
  var quoteSection = document.getElementById("quote-section");
  var contactSection = document.getElementById("contact-section");
  var summary = document.getElementById("quote-summary");
  var durationNote = document.getElementById("duration-note");
  var daySelect = document.getElementById("day-select");
  var timeSelect = document.getElementById("time-select");
  var slotFields = document.getElementById("slot-fields");
  var status = document.getElementById("form-status");
  var sqft = document.getElementById("sqft");
  var currentBooking = null;
  var currentDays = [];

  function numberOrNull(value) {
    var parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function bookingPayload() {
    var data = new FormData(form);
    var screens = Math.max(0, Number(data.get("screens")) || 0);
    return {
      service: data.get("service") === "ext" ? "ext" : "both",
      sqft: numberOrNull(data.get("sqft")),
      paneCount: numberOrNull(data.get("panes")),
      stories2plus: data.get("stories") === "on",
      hardWater: data.get("hardWater") === "on",
      lastCleaned5yr: data.get("lastCleaned5yr") === "on",
      postConstruction: data.get("postConstruction") === "on",
      wantsScreens: screens > 0,
      screenCount: screens,
      plan: "onetime"
    };
  }

  function money(value) {
    return "$" + Math.round(value).toLocaleString();
  }

  function durationLabel(minutes) {
    if (minutes === 570) return "9.5-hour day";
    if (minutes < 60) return minutes + " min";
    var hours = Math.floor(minutes / 60);
    var mins = minutes % 60;
    return hours + " hr" + (hours === 1 ? "" : "s") + (mins ? " " + mins + " min" : "");
  }

  function setStatus(message, kind) {
    status.textContent = message || "";
    status.className = "status" + (kind ? " " + kind : "");
  }

  function renderTimes() {
    var day = currentDays.find(function (item) { return item.dateISO === daySelect.value; });
    timeSelect.innerHTML = "";
    (day ? day.slots : []).forEach(function (slot) {
      var option = document.createElement("option");
      option.value = slot.startISO;
      option.textContent = slot.label;
      timeSelect.appendChild(option);
    });
  }

  function renderQuote(quote) {
    summary.innerHTML = "<div><small>Quoted range</small><strong>" + money(quote.price.low) + "–" + money(quote.price.high) + "</strong></div>" +
      "<div><small>Estimated work time</small><strong>" + durationLabel(quote.durationMinutes) + "</strong></div>";
    durationNote.textContent = quote.durationNote;
    durationNote.className = "duration-note" + (quote.mayTakeMultipleDays ? " multiday" : "");
    quoteSection.hidden = false;
  }

  document.querySelectorAll("[data-sqft]").forEach(function (button) {
    button.addEventListener("click", function () {
      sqft.value = button.getAttribute("data-sqft");
      document.querySelectorAll("[data-sqft]").forEach(function (item) {
        item.classList.toggle("selected", item === button);
      });
      quoteSection.hidden = true;
      contactSection.hidden = true;
      setStatus("");
    });
  });

  sqft.addEventListener("input", function () {
    document.querySelectorAll("[data-sqft]").forEach(function (item) { item.classList.remove("selected"); });
  });
  daySelect.addEventListener("change", renderTimes);

  findButton.addEventListener("click", async function () {
    currentBooking = bookingPayload();
    if (!currentBooking.sqft && !currentBooking.paneCount) {
      setStatus("Enter square footage or a pane count first.", "error");
      return;
    }
    findButton.disabled = true;
    setStatus("Checking the live OCS calendar…", "loading");
    quoteSection.hidden = true;
    contactSection.hidden = true;
    try {
      var response = await fetch(API_BASE + "/api/booking-test/availability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentBooking)
      });
      var result = await response.json();
      if (result.quote) renderQuote(result.quote);
      if (!response.ok || !result.ok) throw new Error(result.error || "Could not load availability");
      if (result.quote.requiresInPerson) throw new Error("Homes over 8,000 sqft need a custom confirmed quote.");

      currentDays = result.days || [];
      renderQuote(result.quote);
      slotFields.hidden = false;
      daySelect.innerHTML = "";
      currentDays.forEach(function (day) {
        var option = document.createElement("option");
        option.value = day.dateISO;
        option.textContent = day.dayLabel;
        daySelect.appendChild(option);
      });
      renderTimes();
      contactSection.hidden = currentDays.length === 0;
      setStatus(currentDays.length ? "Choose a day and time below." : "No open times fit this job right now.", currentDays.length ? "" : "error");
      quoteSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      slotFields.hidden = true;
      setStatus(error instanceof Error ? error.message : "Could not load availability.", "error");
    } finally {
      findButton.disabled = false;
    }
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    var submit = form.querySelector('button[type="submit"]');
    var data = new FormData(form);
    if (!currentBooking || !timeSelect.value) {
      setStatus("Calculate the quote and choose an available time first.", "error");
      return;
    }
    submit.disabled = true;
    setStatus("Validating the test submission…", "loading");
    try {
      var response = await fetch(API_BASE + "/api/booking-test/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contact: { name: data.get("name"), phone: data.get("phone"), email: data.get("email") || "" },
          booking: currentBooking,
          slotStartISO: timeSelect.value
        })
      });
      var result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || "Test submission failed");
      setStatus("Test passed — the quote, duration, and selected slot are valid. Nothing was saved or reserved.", "success");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Test submission failed.", "error");
    } finally {
      submit.disabled = false;
    }
  });
})();
