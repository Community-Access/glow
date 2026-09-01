/**
 * ai-meter.js -- live AI usage sidebar meter.
 *
 * Polls /ai/usage/ every 30 seconds and after each page AI action (signalled
 * via a CustomEvent "ai:request-complete" dispatched by feature scripts).
 * Updates the sidebar meter in place without a page reload.
 */
(function () {
  "use strict";

  var POLL_INTERVAL_MS = 30000;
  var USAGE_URL = "/ai/usage/";
  var _timer = null;
  var _sessionExpiryMs = 0;
  var _countdownTimer = null;

  function el(id) { return document.getElementById(id); }

  // Announce only meaningful session transitions through the dedicated live
  // region, so the per-second countdown does not re-announce the whole meter.
  function announce(message) {
    var live = el('ai-meter-announce');
    if (live && live.textContent !== message) {
      live.textContent = message;
    }
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') || '' : '';
  }

  function formatDuration(totalSeconds) {
    var seconds = Math.max(0, Number(totalSeconds || 0));
    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return hours + 'h ' + minutes + 'm remaining';
    }
    if (minutes > 0) {
      return minutes + 'm remaining';
    }
    return Math.max(0, seconds) + 's remaining';
  }

  function updateMeter(data) {
    var meterEl = el("ai-meter");
    var quotaEl = el("ai-meter-quota");
    if (!meterEl) return;

    if (data.provider && data.chat_remaining_today == null) {
      var reqEl = el("ai-meter-requests");
      var modelEl = el("ai-meter-model");
      if (reqEl) reqEl.textContent = data.session_requests_today;
      if (modelEl) modelEl.textContent = data.provider_model || data.ollama_model || "unknown";

    } else if (data.provider === "openrouter") {
      var reqEl2 = el("ai-meter-requests");
      var limitEl = el("ai-meter-limit");
      var barEl = el("ai-meter-bar");
      var fillEl = el("ai-meter-bar-fill");

      if (reqEl2) reqEl2.textContent = data.session_requests_today;
      if (limitEl) {
        var limit = data.chat_remaining_today != null
          ? (data.session_requests_today + data.chat_remaining_today)
          : 50;
        limitEl.textContent = limit;
      }
      if (barEl && data.budget_pct_remaining != null) {
        barEl.setAttribute("aria-valuenow", data.budget_pct_remaining);
        if (fillEl) fillEl.style.width = data.budget_pct_remaining + "%";
      }
    }

    if (quotaEl) {
      var bits = [];
      if (data.budget_remaining_usd != null) {
        bits.push('Budget left: $' + Number(data.budget_remaining_usd).toFixed(2));
      }
      if (data.session_quota_enabled) {
        bits.push('Session requests left: ' + Number(data.session_requests_remaining || 0));
        if (data.session_reset_seconds) {
          bits.push('Resets in ' + formatDuration(data.session_reset_seconds));
        }
      }
      quotaEl.textContent = bits.join(' | ');
      quotaEl.hidden = !bits.length;
    }
  }

  function renderSessionCountdown() {
    var sessionEl = el('ai-meter-session-time');
    var extendBtn = el('ai-meter-extend-btn');
    var secondsRemaining;
    if (!sessionEl) return;

    secondsRemaining = Math.max(0, Math.floor((_sessionExpiryMs - Date.now()) / 1000));
    if (!_sessionExpiryMs || secondsRemaining <= 0) {
      var expired = 'Key session expired';
      if (sessionEl.textContent !== expired) {
        sessionEl.textContent = expired;
        announce(expired);
      }
      if (extendBtn) {
        extendBtn.disabled = true;
      }
      // Countdown has reached zero -- stop the per-second timer so it does
      // not keep firing (and re-writing) forever.
      if (_countdownTimer) {
        clearInterval(_countdownTimer);
        _countdownTimer = null;
      }
      return;
    }

    var next = 'Key session: ' + formatDuration(secondsRemaining);
    if (sessionEl.textContent === next) return;
    sessionEl.textContent = next;
    if (extendBtn) {
      extendBtn.disabled = false;
    }
  }

  function startCountdownTimer() {
    if (_countdownTimer) {
      clearInterval(_countdownTimer);
    }
    renderSessionCountdown();
    _countdownTimer = setInterval(renderSessionCountdown, 1000);
  }

  function updateSessionStatus(data) {
    var sessionWrap = el('ai-meter-session');
    if (!sessionWrap) {
      return;
    }
    if (!data || !data.ok || !data.active || !data.expires_utc) {
      _sessionExpiryMs = 0;
      sessionWrap.hidden = false;
      // Session is inactive -- stop any running countdown timer.
      if (_countdownTimer) {
        clearInterval(_countdownTimer);
        _countdownTimer = null;
      }
      renderSessionCountdown();
      return;
    }
    var wasInactive = !_sessionExpiryMs;
    _sessionExpiryMs = Date.parse(data.expires_utc);
    sessionWrap.hidden = false;
    if (wasInactive) {
      announce('AI key session active');
    }
    startCountdownTimer();
  }

  function fetchSessionStatus() {
    var meterEl = el('ai-meter');
    var sessionUrl = meterEl ? meterEl.getAttribute('data-session-url') : '';
    if (!sessionUrl) {
      return;
    }
    fetch(sessionUrl, { credentials: 'same-origin' })
      .then(function (response) { return response.ok ? response.json() : null; })
      .then(function (data) { if (data) updateSessionStatus(data); })
      .catch(function () { });
  }

  function fetchUsage() {
    fetch(USAGE_URL, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) { if (data) updateMeter(data); })
      .catch(function () { /* silent -- meter stays at last value */ });
    fetchSessionStatus();
  }

  function resetTimer() {
    if (_timer) clearTimeout(_timer);
    _timer = setTimeout(function () {
      fetchUsage();
      resetTimer();
    }, POLL_INTERVAL_MS);
  }

  // Initial fetch shortly after page load (gives Flask time to settle)
  if (el("ai-meter")) {
    setTimeout(fetchUsage, 1500);
    resetTimer();

    // Also refresh immediately after any AI feature fires its completion event
    document.addEventListener("ai:request-complete", function () {
      fetchUsage();
      resetTimer();
    });

    var extendBtn = el('ai-meter-extend-btn');
    if (extendBtn) {
      extendBtn.addEventListener('click', function () {
        var meterEl = el('ai-meter');
        var extendUrl = meterEl ? meterEl.getAttribute('data-extend-url') : '';
        if (!extendUrl) {
          return;
        }
        extendBtn.disabled = true;
        fetch(extendUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': getCsrfToken() }
        })
          .then(function (response) { return response.ok ? response.json() : null; })
          .then(function (data) {
            if (data) {
              updateSessionStatus(data);
            }
          })
          .catch(function () { })
          .finally(function () {
            renderSessionCountdown();
          });
      });
    }
  }
}());
