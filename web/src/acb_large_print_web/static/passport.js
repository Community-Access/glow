/* The browser half of the GLOW passport.
 *
 * GLOW's preferences already live in localStorage, applied by
 * preferences.js. The passport does not replace that: it carries a copy to
 * the server so it can come back on another device, and writes the server's
 * copy into localStorage when someone arrives through a link.
 *
 * Two jobs, both driven by data-* attributes because the site CSP forbids
 * inline script:
 *
 *   1. On the settings page, fill the hidden settings_json field before the
 *      "Keep these settings" form posts.
 *   2. On any page, if this browser carries a passport whose stored settings
 *      differ from local storage, offer to apply them -- never silently, and
 *      never by reloading underneath somebody.
 */
(function () {
  "use strict";

  function prefs() {
    return window.glowPreferences || null;
  }

  // --- 1. Carry local settings up with the form ---------------------------
  var form = document.getElementById("passport-save-form");
  if (form) {
    form.addEventListener("submit", function () {
      var field = document.getElementById("passport-settings-json");
      var api = prefs();
      if (!field || !api || typeof api.loadSettings !== "function") return;
      try {
        field.value = JSON.stringify(api.loadSettings());
      } catch (e) {
        field.value = "{}";
      }
    });
  }

  // --- 2. Offer the stored settings on arrival ----------------------------
  var offer = document.getElementById("passport-restore-offer");
  if (!offer || !window.fetch) return;

  var url = offer.getAttribute("data-settings-url");
  if (!url) return;

  window
    .fetch(url, { credentials: "same-origin" })
    .then(function (response) {
      return response.ok ? response.json() : null;
    })
    .then(function (payload) {
      if (!payload || !payload.passport) return;
      var api = prefs();
      if (!api || typeof api.loadSettings !== "function") return;

      var local = JSON.stringify(api.loadSettings());
      var stored = JSON.stringify(payload.settings || {});
      if (stored === "{}" || stored === local) return;

      // A control the reader activates. Applying settings changes type size
      // and contrast; doing that underneath someone mid-task would be
      // exactly the kind of thing this tool exists to prevent.
      offer.hidden = false;
      var button = document.getElementById("passport-apply-settings");
      var status = document.getElementById("passport-apply-status");
      if (!button) return;

      button.addEventListener("click", function () {
        try {
          api.saveSettings(payload.settings);
          if (status) {
            status.textContent =
              "Your saved settings have been applied to this browser.";
          }
          offer.hidden = true;
        } catch (e) {
          if (status) {
            status.textContent =
              "Those settings could not be applied in this browser.";
          }
        }
      });
    })
    .catch(function () {
      /* offline, blocked, or no passport: the page is correct either way */
    });
})();
