/**
 * GLOW Accessibility Enhancements
 *
 * Adds keyboard and locale niceties that are independent of any single page:
 *   1. Pressing Escape inside an open <details> accordion collapses it and
 *      restores focus to its <summary>. This matches the WAI-ARIA Authoring
 *      Practices "disclosure" pattern keyboard expectations.
 *   2. Any <time data-utc-local> element has its text content rewritten in
 *      the user's local timezone, with a short " (your time)" suffix to make
 *      it obvious the value was converted from UTC.
 */
(function () {
    'use strict';

    // --- 1. Escape collapses <details> accordions -----------------------------
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape' && e.keyCode !== 27) return;
        var active = document.activeElement;
        if (!active) return;
        // Don't hijack Escape inside form controls that have their own behavior
        // (e.g. clearing a field, closing a native <select> popup) or while the
        // user is typing in editable content -- collapsing the disclosure would
        // yank them out mid-edit.
        var tag = active.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || active.isContentEditable) {
            return;
        }
        var details = active.closest ? active.closest('details[open]') : null;
        if (!details) return;
        e.preventDefault();
        details.open = false;
        var summary = details.querySelector(':scope > summary');
        if (summary && typeof summary.focus === 'function') {
            summary.focus();
        }
    });

    // --- 2. UTC -> local time rewriting --------------------------------------
    function formatLocal(d) {
        try {
            var opts = {
                weekday: undefined,
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                timeZoneName: 'short',
            };
            return d.toLocaleString(undefined, opts);
        } catch (err) {
            return d.toString();
        }
    }

    function rewriteTimes(root) {
        var nodes = (root || document).querySelectorAll('time[data-utc-local]');
        Array.prototype.forEach.call(nodes, function (node) {
            if (node.dataset.localized === '1') return;
            var iso = node.getAttribute('datetime') || node.getAttribute('data-utc-local');
            if (!iso) return;
            var d = new Date(iso);
            if (isNaN(d.getTime())) return;
            node.textContent = formatLocal(d);
            node.title = 'Local time (converted from UTC: ' + iso + ')';
            node.dataset.localized = '1';
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { rewriteTimes(); });
    } else {
        rewriteTimes();
    }

    // --- 2b. Footer deploy status -------------------------------------------
    function updateFooterHealthStatus() {
        var deployEl = document.getElementById('footer-deploy-phase');
        if (!deployEl) return;

        function label(value) {
            var v = String(value || '').toLowerCase();
            if (!v || v === 'unknown') return 'checking';
            if (v === 'not-run') return 'not run for this revision';
            if (v === 'not-reported') return 'awaiting report';
            if (v === 'not-configured') return 'not configured (manual tracking only)';
            if (v === 'in_progress') return 'in progress';
            return String(value);
        }

        fetch('/health', { method: 'GET', credentials: 'same-origin' })
            .then(function (resp) {
                if (!resp.ok) throw new Error('health http ' + resp.status);
                return resp.json();
            })
            .then(function (payload) {
                var deployment = payload && payload.deployment ? payload.deployment : {};
                var rawPhase = String(deployment.phase || '').toLowerCase();
                var rawState = String(deployment.state || '').toLowerCase();
                var phase = label(deployment.phase || 'unknown');
                var state = label(deployment.state || 'unknown');

                if (deployEl) {
                    var updated = deployment.updated_at_utc ? ' Last update: ' + deployment.updated_at_utc + '.' : '';
                    if ((rawPhase === 'none' || rawPhase === '') && (rawState === 'idle' || rawState === '')) {
                        deployEl.textContent = 'Deployment: standing by. No active rollout right now.' + updated;
                    } else if (rawState === 'in_progress') {
                        deployEl.textContent = 'Deployment: in progress at phase ' + phase + '.' + updated;
                    } else if (rawState === 'completed') {
                        deployEl.textContent = 'Deployment: completed at phase ' + phase + '.' + updated;
                    } else if (rawState === 'failed') {
                        var detail = deployment.detail ? ' Details: ' + deployment.detail + '.' : '';
                        deployEl.textContent = 'Deployment: failed at phase ' + phase + '.' + detail + updated;
                    } else {
                        var fallbackDetail = deployment.detail ? ' Details: ' + deployment.detail + '.' : '';
                        deployEl.textContent = 'Deployment: phase ' + phase + ' (' + state + ').' + fallbackDetail + updated;
                    }
                }
            })
            .catch(function () {
                if (deployEl) deployEl.textContent = 'Deployment: unavailable';
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateFooterHealthStatus);
    } else {
        updateFooterHealthStatus();
    }
    // Poll only while the tab is visible. A forever-running interval on every
    // background tab is wasteful and keeps hitting /health for no benefit.
    var _footerHealthTimer = null;
    function startFooterHealthPolling() {
        if (_footerHealthTimer || document.getElementById('footer-deploy-phase') === null) return;
        _footerHealthTimer = window.setInterval(updateFooterHealthStatus, 30 * 1000);
    }
    function stopFooterHealthPolling() {
        if (_footerHealthTimer) {
            window.clearInterval(_footerHealthTimer);
            _footerHealthTimer = null;
        }
    }
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            stopFooterHealthPolling();
        } else {
            updateFooterHealthStatus();
            startFooterHealthPolling();
        }
    });
    if (!document.hidden) {
        startFooterHealthPolling();
    }

    // --- 5. Cognitive profile helpers -------------------------------------
    function cognitiveModeEnabled() {
        try {
            return document.documentElement.getAttribute('data-cognitive') === 'on';
        } catch (_err) {
            return false;
        }
    }

    function applyCognitiveMode() {
        if (!cognitiveModeEnabled()) return;
        var details = document.querySelectorAll('details:not([data-keep-collapsed])');
        Array.prototype.forEach.call(details, function (d) {
            d.open = true;
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyCognitiveMode);
    } else {
        applyCognitiveMode();
    }

    window.GLOW = window.GLOW || {};
    window.GLOW.rewriteLocalTimes = rewriteTimes;
    window.GLOW.applyCognitiveMode = applyCognitiveMode;

    // --- 3. Alt+U -- focus first visible file input --------------------------
    // Deliberately NOT Ctrl/Cmd+U: those are reserved (View Source in the
    // browser, and the readline "kill line" chord in terminals/inputs), and
    // preventing their default breaks that behavior. Alt+U is unclaimed.
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'u' && e.key !== 'U') return;
        if (!e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
        var input = document.querySelector('input[type="file"]:not([disabled]):not([hidden])');
        if (!input) return;
        e.preventDefault();
        input.focus();
        if (window.GLOW && window.GLOW.toast) {
            window.GLOW.toast('File picker focused. Press Space or Enter to open.', 'info');
        }
    });

    // --- 4. Session keep-alive -- ping /health every 15 minutes when a form is present ------
    (function () {
        if (!document.querySelector('form')) return;
        var _keepAliveInterval = setInterval(function () {
            try {
                fetch('/health', { method: 'GET', credentials: 'same-origin' }).catch(function () { });
            } catch (_) { }
        }, 15 * 60 * 1000);
        // Cancel if the user navigates away cleanly
        window.addEventListener('beforeunload', function () { clearInterval(_keepAliveInterval); });
    }());

    // --- 6. Single-file helper upload buttons ------------------------------
    // Provide an explicit, keyboard-friendly action next to file inputs so
    // users do not depend on browser-native file dialog button behavior.
    function initUploadHelperButtons() {
        var inputs = document.querySelectorAll('input[type="file"]:not([multiple])');
        Array.prototype.forEach.call(inputs, function (input) {
            if (input.dataset.uploadHelperBound === '1') return;
            var form = input.form;
            if (!form) return;

            var container = document.createElement('div');
            container.className = 'upload-helper';

            var helperBtn = document.createElement('button');
            helperBtn.type = 'button';
            helperBtn.className = 'btn-secondary';
            helperBtn.textContent = 'Upload selected file';
            helperBtn.disabled = !(input.files && input.files.length > 0);

            helperBtn.addEventListener('click', function () {
                if (!input.files || input.files.length < 1) {
                    input.focus();
                    if (window.GLOW && window.GLOW.toast) {
                        window.GLOW.toast('Choose a file first, then select Upload selected file.', 'warning');
                    }
                    return;
                }
                if (typeof form.requestSubmit === 'function') {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            });

            container.appendChild(helperBtn);
            input.insertAdjacentElement('afterend', container);

            input.addEventListener('change', function () {
                helperBtn.disabled = !(input.files && input.files.length > 0);
            });

            input.dataset.uploadHelperBound = '1';
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUploadHelperButtons);
    } else {
        initUploadHelperButtons();
    }

    // --- 7. (removed) Enter-on-file-input auto-submit -----------------------
    // A keydown handler here used to call form.requestSubmit() when Enter was
    // pressed on a focused file input. That hijacked the file input's native
    // Enter/Space behavior (open the file-picker dialog) and could submit the
    // wrong form. The explicit "Upload selected file" helper button in section
    // 6 provides the keyboard-friendly submit path instead.
}());
