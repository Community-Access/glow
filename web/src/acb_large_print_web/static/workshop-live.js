/* Live room updates for the workshop gallery and facilitator dashboard.
 *
 * The hard rule here is that a live-updating page must not be hostile to a
 * screen reader user. So:
 *
 *   - The server sends counts, never content.
 *   - New work is announced politely, as a count, once per change.
 *   - Nothing on the page is re-rendered or reordered underneath anyone. The
 *     new work appears only when the reader activates the control, which
 *     reloads the page in the normal way.
 *   - Focus is never moved.
 *
 * Configured entirely through data-* attributes on #workshop-live, because the
 * site CSP forbids inline script.
 *
 *   data-stream-url   Server-Sent Events endpoint (counts only)
 *   data-poll-url     JSON endpoint, used when EventSource is unavailable
 *   data-initial      Submission count at page render
 *   data-mode         "gallery" (announce new work) or "pulse" (live totals)
 */
(function () {
  "use strict";

  var root = document.getElementById("workshop-live");
  if (!root) return;

  var streamUrl = root.getAttribute("data-stream-url") || "";
  var pollUrl = root.getAttribute("data-poll-url") || "";
  var mode = root.getAttribute("data-mode") || "gallery";
  var initial = parseInt(root.getAttribute("data-initial") || "0", 10) || 0;

  var status = document.getElementById("workshop-live-status");
  var reveal = document.getElementById("workshop-live-reveal");
  var lastAnnounced = initial;

  function plural(n, one, many) {
    return n === 1 ? one : many;
  }

  function announceGallery(payload) {
    var total = payload.total || 0;
    var added = total - initial;
    if (added <= 0 || total === lastAnnounced) return;
    lastAnnounced = total;

    if (status) {
      status.textContent =
        added +
        " new " +
        plural(added, "submission", "submissions") +
        " since you opened this page.";
    }
    if (reveal && reveal.hidden) {
      // A control the reader chooses to activate. Never an automatic reload:
      // that would throw away a half-written peer review.
      reveal.hidden = false;
    }
  }

  function updatePulse(payload) {
    var by = payload.by_activity || {};
    var keys = Object.keys(by);
    for (var i = 0; i < keys.length; i += 1) {
      var cell = document.querySelector('[data-activity-count="' + keys[i] + '"]');
      if (cell) cell.textContent = String(by[keys[i]]);
      var meter = document.querySelector('[data-activity-meter="' + keys[i] + '"]');
      if (meter) meter.value = by[keys[i]];
    }
    var totalCell = document.getElementById("workshop-live-total");
    if (totalCell) totalCell.textContent = String(payload.total || 0);
    var peopleCell = document.getElementById("workshop-live-participants");
    if (peopleCell) peopleCell.textContent = String(payload.participants || 0);
    if (status && payload.total !== lastAnnounced) {
      lastAnnounced = payload.total;
      status.textContent =
        payload.total +
        " " +
        plural(payload.total, "submission", "submissions") +
        " from " +
        payload.participants +
        " " +
        plural(payload.participants, "participant", "participants") +
        ".";
    }
  }

  function apply(payload) {
    if (!payload) return;
    if (mode === "pulse") updatePulse(payload);
    else announceGallery(payload);
  }

  if (window.EventSource && streamUrl) {
    var source = new EventSource(streamUrl);
    source.onmessage = function (event) {
      try {
        apply(JSON.parse(event.data));
      } catch (e) {
        /* a malformed frame is not worth breaking the page over */
      }
    };
    source.addEventListener("timeout", function () {
      source.close();
    });
    source.onerror = function () {
      /* EventSource reconnects on its own; nothing to do and nothing to say */
    };
    return;
  }

  if (pollUrl && window.fetch) {
    window.setInterval(function () {
      window
        .fetch(pollUrl, { credentials: "same-origin" })
        .then(function (response) {
          return response.ok ? response.json() : null;
        })
        .then(apply)
        .catch(function () {
          /* offline or blocked: the page is still correct, just not live */
        });
    }, 15000);
  }
})();
