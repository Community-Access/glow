(function () {
  var root = document.getElementById('job-progress-root');
  if (!root) return;

  var state = root.getAttribute('data-state') || 'PENDING';
  var streamUrl = root.getAttribute('data-stream-url') || '';
  var pollUrl = root.getAttribute('data-poll-url') || '';
  var initialError = root.getAttribute('data-error') || '';

  var downloadWrap = document.getElementById('job-download-wrap');
  var msg = document.getElementById('job-message');
  var err = document.getElementById('job-error');
  var bar = document.getElementById('job-progress');
  var pctText = document.getElementById('job-progress-value');
  var attemptText = document.getElementById('job-attempt');
  var maxAttemptsText = document.getElementById('job-max-attempts');
  var retryForm = document.getElementById('job-retry-form');
  var cancelForm = document.getElementById('job-cancel-form');
  var continueWrap = document.getElementById('job-continue-wrap');
  var continueLink = document.getElementById('job-continue');

  var autoAdvanceCancelled = false;
  var cancelAutoAdvance = function () { autoAdvanceCancelled = true; };
  document.addEventListener('click', cancelAutoAdvance, { once: true });
  document.addEventListener('keydown', cancelAutoAdvance, { once: true });
  function autoAdvance(url) {
    if (!url) return;
    setTimeout(function () {
      if (autoAdvanceCancelled) return;
      window.location.assign(url);
    }, 1200);
  }

  function applyStatus(s) {
    var pct = Number(s.progress || 0);
    bar.value = pct;
    bar.setAttribute('aria-valuenow', String(pct));
    pctText.textContent = String(pct);
    attemptText.textContent = String(s.attempt || 0);
    maxAttemptsText.textContent = String(s.max_attempts || 1);
    msg.textContent = s.message || '';
    if (s.state === 'SUCCESS') {
      downloadWrap.hidden = !s.result_file;
      if (continueWrap && continueLink) {
        continueWrap.hidden = !s.continue_url;
        if (s.continue_url) {
          continueLink.setAttribute('href', s.continue_url);
        }
      }
      cancelForm.hidden = true;
      retryForm.hidden = true;
      msg.textContent = s.continue_url ? 'Done. Continuing\u2026' : 'Done.';
      autoAdvance(s.continue_url);
      return true;
    }
    if (s.state === 'CANCELLED') {
      cancelForm.hidden = true;
      retryForm.hidden = !s.retryable;
      err.textContent = s.error || 'Job cancelled.';
      return true;
    }
    if (s.state === 'FAILURE') {
      err.textContent = s.error || 'Job failed.';
      cancelForm.hidden = true;
      retryForm.hidden = !s.retryable;
      return true;
    }
    retryForm.hidden = true;
    cancelForm.hidden = false;
    return false;
  }

  if (state === 'SUCCESS') {
    downloadWrap.hidden = downloadWrap.getAttribute('data-has-result') !== '1';
    if (continueWrap && continueLink) {
      var continueUrl = continueWrap.getAttribute('data-continue-url') || '';
      continueWrap.hidden = !continueUrl;
      if (continueUrl) {
        continueLink.setAttribute('href', continueUrl);
        msg.textContent = 'Done. Continuing\u2026';
        autoAdvance(continueUrl);
      }
    }
    cancelForm.hidden = true;
    retryForm.hidden = true;
    return;
  }
  if (state === 'FAILURE') {
    err.textContent = initialError || 'Job failed.';
    cancelForm.hidden = true;
    retryForm.hidden = retryForm.getAttribute('data-retryable') !== '1';
    return;
  }
  if (state === 'CANCELLED') {
    err.textContent = initialError || 'Job cancelled.';
    cancelForm.hidden = true;
    retryForm.hidden = retryForm.getAttribute('data-retryable') !== '1';
    return;
  }

  if (!!window.EventSource && streamUrl) {
    var es = new EventSource(streamUrl);
    es.onmessage = function (e) {
      var payload = JSON.parse(e.data || '{}');
      if (applyStatus(payload)) es.close();
    };
    es.addEventListener('success', function (e) {
      var payload = JSON.parse(e.data || '{}');
      applyStatus(payload);
      es.close();
    });
    es.addEventListener('failure', function (e) {
      var payload = JSON.parse(e.data || '{}');
      applyStatus(payload);
      es.close();
    });
    es.addEventListener('cancelled', function (e) {
      var payload = JSON.parse(e.data || '{}');
      applyStatus(payload);
      es.close();
    });
  } else if (pollUrl) {
    var poll = function () {
      fetch(pollUrl)
        .then(function (r) { return r.json(); })
        .then(function (payload) {
          if (!applyStatus(payload)) setTimeout(poll, 1000);
        })
        .catch(function () { setTimeout(poll, 1500); });
    };
    poll();
  }
})();
