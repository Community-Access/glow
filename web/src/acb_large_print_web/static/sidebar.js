/* ==========================================================================
   GLOW 5.0.0 -- Sidebar Navigation (sidebar.js)
   Manages open/close on mobile, keyboard navigation, focus trapping,
   and aria-expanded state for the primary navigation sidebar.
   ========================================================================== */

(function () {
  'use strict';

  var SIDEBAR_ID    = 'primary-nav';
  var TOGGLE_ID     = 'sidebar-toggle';
  var OVERLAY_ID    = 'sidebar-overlay';
  var OPEN_CLASS    = 'sidebar--open';
  var LOCKED_CLASS  = 'sidebar-body-locked';

  /* Breakpoint that matches the CSS desktop threshold (64em = 1024px). */
  var DESKTOP_MQ = window.matchMedia('(min-width: 64em)');

  var sidebar = document.getElementById(SIDEBAR_ID);
  var toggle  = document.getElementById(TOGGLE_ID);
  var overlay = document.getElementById(OVERLAY_ID);

  if (!sidebar || !toggle) { return; }

  /* ------------------------------------------------------------------ */
  /* Helpers                                                              */
  /* ------------------------------------------------------------------ */

  function isDesktop() {
    return DESKTOP_MQ.matches;
  }

  function getFocusable() {
    return Array.prototype.slice.call(
      sidebar.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    );
  }

  /* ------------------------------------------------------------------ */
  /* Open / Close                                                         */
  /* ------------------------------------------------------------------ */

  function openSidebar() {
    sidebar.classList.add(OPEN_CLASS);
    toggle.setAttribute('aria-expanded', 'true');
    toggle.setAttribute('aria-label', 'Close navigation menu');
    toggle.setAttribute('title', 'Close navigation menu');
    if (overlay) {
      overlay.removeAttribute('hidden');
      overlay.setAttribute('aria-hidden', 'true');
    }
    document.body.classList.add(LOCKED_CLASS);

    /* Move focus to the first link inside the sidebar. */
    var focusable = getFocusable();
    if (focusable.length) { focusable[0].focus(); }
  }

  function closeSidebar(returnFocus) {
    sidebar.classList.remove(OPEN_CLASS);
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open navigation menu');
    toggle.setAttribute('title', 'Open navigation menu');
    if (overlay) { overlay.setAttribute('hidden', ''); }
    document.body.classList.remove(LOCKED_CLASS);

    if (returnFocus !== false) { toggle.focus(); }
  }

  /* ------------------------------------------------------------------ */
  /* Focus trap (mobile only) -- keeps Tab inside the open sidebar.      */
  /* ------------------------------------------------------------------ */

  function trapFocus(e) {
    if (isDesktop()) { return; }
    if (!sidebar.classList.contains(OPEN_CLASS)) { return; }

    var focusable = getFocusable();
    if (!focusable.length) { return; }

    var first = focusable[0];
    var last  = focusable[focusable.length - 1];

    if (e.key === 'Tab') {
      if (e.shiftKey) {
        /* Shift+Tab from first focusable → wrap to last */
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        /* Tab from last focusable → wrap to first */
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* Event wiring                                                         */
  /* ------------------------------------------------------------------ */

  toggle.addEventListener('click', function () {
    if (sidebar.classList.contains(OPEN_CLASS)) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  /* Close when the overlay (background) is clicked. */
  if (overlay) {
    overlay.addEventListener('click', function () { closeSidebar(); });
  }

  /* Close on Escape key (mobile only). */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar.classList.contains(OPEN_CLASS) && !isDesktop()) {
      closeSidebar();
    }
  });

  /* Focus trap on keydown. */
  sidebar.addEventListener('keydown', trapFocus);

  /* Close sidebar when a nav link is clicked on mobile. */
  sidebar.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', function () {
      if (!isDesktop()) { closeSidebar(false); }
    });
  });

  /* On resize to desktop, clear any open/locked mobile state. */
  function onBreakpointChange(mq) {
    if (mq.matches && sidebar.classList.contains(OPEN_CLASS)) {
      sidebar.classList.remove(OPEN_CLASS);
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open navigation menu');
      toggle.setAttribute('title', 'Open navigation menu');
      if (overlay) { overlay.setAttribute('hidden', ''); }
      document.body.classList.remove(LOCKED_CLASS);
    }
  }

  if (DESKTOP_MQ.addEventListener) {
    DESKTOP_MQ.addEventListener('change', onBreakpointChange);
  } else if (DESKTOP_MQ.addListener) {
    /* Safari <14 fallback */
    DESKTOP_MQ.addListener(onBreakpointChange);
  }

})();
