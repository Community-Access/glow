/* Delegated event handlers for what used to be inline DOM event attributes
 * (onclick, oninput, onsubmit, ...). Inline handlers are blocked by the
 * strict CSP (no 'unsafe-inline', no 'unsafe-hashes'), so each pattern is
 * expressed via data-* attributes on the element and wired up here.
 *
 * Supported attributes:
 *   data-confirm="message"           on <button>/<a>: show confirm() before
 *                                    submitting/following; cancel if declined.
 *   data-action="history-back"       on any clickable: history.back().
 *   data-toggle-rule-group="<state>" on <button>: call glowToggleRuleGroup
 *                                    (defined in static/rules-toggle.js or
 *                                    inline elsewhere) with the button and
 *                                    a boolean (state="select" => true,
 *                                    "deselect" => false).
 *   data-char-count-target="<id>"    on <input>/<textarea>: update target's
 *                                    textContent on input. With optional
 *                                    data-char-count-max="N" the text is
 *                                    "(N - length) characters remaining";
 *                                    otherwise it is the length as a number.
 *   data-copy-target="<id>"          on <button>: copy the value (or text) of
 *                                    the element with that id to the
 *                                    clipboard and report the outcome in the
 *                                    element named by data-copy-status. The
 *                                    copied field stays on the page and stays
 *                                    selectable, so the button is an
 *                                    accelerator rather than the only way to
 *                                    get the text.
 */
(function () {
  "use strict";

  document.addEventListener(
    "click",
    function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;

      // data-action="history-back"
      var backEl = t.closest('[data-action="history-back"]');
      if (backEl) {
        ev.preventDefault();
        try {
          window.history.back();
        } catch (e) {
          /* ignore */
        }
        return;
      }

      // data-toggle-rule-group (must run before data-confirm short-circuit)
      var toggleEl = t.closest("[data-toggle-rule-group]");
      if (toggleEl) {
        ev.preventDefault();
        var state = toggleEl.getAttribute("data-toggle-rule-group") === "deselect" ? false : true;
        if (typeof window.glowToggleRuleGroup === "function") {
          try {
            window.glowToggleRuleGroup(toggleEl, state);
          } catch (e) {
            /* ignore */
          }
        }
        return;
      }

      // data-copy-target="<id>" -- copy a field to the clipboard.
      var copyEl = t.closest("[data-copy-target]");
      if (copyEl) {
        ev.preventDefault();
        var src = document.getElementById(copyEl.getAttribute("data-copy-target"));
        var statusId = copyEl.getAttribute("data-copy-status");
        var status = statusId ? document.getElementById(statusId) : null;
        var text = src ? (src.value != null ? src.value : src.textContent) : "";

        var report = function (message) {
          // Announced by the status region, never by moving focus: the
          // person pressing this button is mid-task and should stay there.
          if (status) status.textContent = message;
        };

        if (!src) {
          report("Nothing to copy.");
          return;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(
            function () {
              report("Copied to the clipboard.");
            },
            function () {
              report("Could not copy automatically. Select the text and copy it.");
            }
          );
          return;
        }
        try {
          if (src.select) {
            src.select();
            document.execCommand("copy");
            report("Copied to the clipboard.");
          } else {
            report("Select the text and copy it.");
          }
        } catch (e) {
          report("Could not copy automatically. Select the text and copy it.");
        }
        return;
      }

      // data-confirm="..." -- cancel the click (and any default submit)
      // if the user declines the prompt.
      var confirmEl = t.closest("[data-confirm]");
      if (confirmEl) {
        var msg = confirmEl.getAttribute("data-confirm") || "Are you sure?";
        if (!window.confirm(msg)) {
          ev.preventDefault();
          ev.stopPropagation();
        }
      }
    },
    false
  );

  // data-char-count-target: input value length -> target textContent
  document.addEventListener(
    "input",
    function (ev) {
      var t = ev.target;
      if (!t || !t.getAttribute) return;
      var targetId = t.getAttribute("data-char-count-target");
      if (!targetId) return;
      var dest = document.getElementById(targetId);
      if (!dest) return;
      var val = t.value == null ? "" : String(t.value);
      var maxStr = t.getAttribute("data-char-count-max");
      if (maxStr) {
        var max = parseInt(maxStr, 10) || 0;
        dest.textContent = (max - val.length) + " characters remaining";
      } else {
        dest.textContent = String(val.length);
      }
    },
    false
  );
})();
