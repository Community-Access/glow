/**
 * SPA Tab Navigation -- GLOW Accessibility Toolkit
 *
 * Progressively enhances the navigation tabs into a true ARIA tab
 * control with keyboard navigation and dynamic content loading.
 * Without JavaScript, tabs function as normal navigation links.
 */
(function () {
  "use strict";

  var tablist = document.querySelector('[role="tablist"]');
  if (!tablist) return;

  var tabs = Array.prototype.slice.call(
    tablist.querySelectorAll('[role="tab"]')
  );
  var main = document.getElementById("main");
  if (!tabs.length || !main) return;

  /* This SPA enhancement only applies to link-based tabs (navigation tabs
     with an href). Some pages (e.g. admin feature flags) use a <button>
     tablist for in-page panels; enhancing those would wipe their state and
     re-inject their inline <script> without a CSP nonce. Bail out unless
     every tab is a real link. */
  if (!tabs.every(function (t) { return t.tagName === "A" && t.href; })) return;

  /* ---- Roving tabindex setup ---- */
  var activeTab = null;
  tabs.forEach(function (tab) {
    if (tab.getAttribute("aria-selected") === "true") {
      tab.setAttribute("tabindex", "0");
      activeTab = tab;
    } else {
      tab.setAttribute("tabindex", "-1");
    }
  });

  /* Ensure at least one tab is reachable by keyboard */
  if (!activeTab && tabs.length) {
    tabs[0].setAttribute("tabindex", "0");
  }

  /* ---- Content cache: URL -> { html, title } ---- */
  var cache = {};
  if (activeTab) {
    cache[activeTab.href] = {
      html: main.innerHTML,
      title: document.title,
    };
  }

  /* ---- Helpers ---- */

  function extractContent(responseText) {
    var parser = new DOMParser();
    var doc = parser.parseFromString(responseText, "text/html");
    var newMain = doc.getElementById("main");
    return {
      html: newMain ? newMain.innerHTML : "",
      title: doc.title || "Home | GLOW (Guided Layout & Output Workflow)",
    };
  }

  function executeScripts() {
    var scripts = main.querySelectorAll("script");
    Array.prototype.forEach.call(scripts, function (old) {
      var fresh = document.createElement("script");
      /* A cloned script does not inherit the per-request CSP nonce, so copy
         it explicitly or the strict script-src would block execution. */
      if (old.nonce) {
        fresh.setAttribute("nonce", old.nonce);
      }
      if (old.src) {
        fresh.src = old.src;
      } else {
        fresh.textContent = old.textContent;
      }
      old.parentNode.replaceChild(fresh, old);
    });
  }

  function swapContent(content) {
    main.innerHTML = content.html;
    document.title = content.title;
    executeScripts();

    document.dispatchEvent(new CustomEvent("glow:content-swapped"));

    /* Move focus to the page heading so screen readers announce context */
    var heading = main.querySelector("h1");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus();
    }
  }

  function activateTab(tab, updateHistory) {
    /* Update ARIA states and roving tabindex */
    tabs.forEach(function (t) {
      t.setAttribute("aria-selected", "false");
      t.setAttribute("tabindex", "-1");
    });
    tab.setAttribute("aria-selected", "true");
    tab.setAttribute("tabindex", "0");

    var url = tab.href;

    /* Serve from cache when available */
    if (cache[url]) {
      swapContent(cache[url]);
      if (updateHistory) {
        history.pushState({ tabUrl: url }, cache[url].title, url);
      }
      return;
    }

    /* Fetch fresh content from server */
    main.setAttribute("aria-busy", "true");
    fetch(url, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error(res.status);
        return res.text();
      })
      .then(function (text) {
        var content = extractContent(text);
        cache[url] = content;
        swapContent(content);
        if (updateHistory) {
          history.pushState({ tabUrl: url }, content.title, url);
        }
      })
      .catch(function () {
        /* Network or server error -- fall back to normal navigation */
        window.location.href = url;
      })
      .finally(function () {
        main.removeAttribute("aria-busy");
      });
  }

  /* ---- Click handler ---- */
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function (e) {
      e.preventDefault();
      activateTab(tab, true);
    });
  });

  /* ---- Keyboard navigation ---- */
  tablist.addEventListener("keydown", function (e) {
    var index = tabs.indexOf(document.activeElement);
    if (index < 0) return;

    var newIndex;
    switch (e.key) {
      case "ArrowRight":
        newIndex = (index + 1) % tabs.length;
        break;
      case "ArrowLeft":
        newIndex = (index - 1 + tabs.length) % tabs.length;
        break;
      case "Home":
        newIndex = 0;
        break;
      case "End":
        newIndex = tabs.length - 1;
        break;
      default:
        return;
    }

    e.preventDefault();
    tabs[newIndex].focus();
    activateTab(tabs[newIndex], true);
  });

  /* ---- Browser history (back / forward) ---- */
  window.addEventListener("popstate", function (e) {
    if (!e.state || !e.state.tabUrl) return;

    var url = e.state.tabUrl;
    var tab = null;
    for (var i = 0; i < tabs.length; i++) {
      if (tabs[i].href === url) {
        tab = tabs[i];
        break;
      }
    }

    if (tab) {
      activateTab(tab, false);
    } else {
      /* URL doesn't match any tab -- do a real navigation */
      window.location.href = url;
    }
  });

  /* Record initial history entry so popstate can return here */
  if (activeTab) {
    history.replaceState(
      { tabUrl: activeTab.href },
      document.title,
      window.location.href
    );
  }
})();
