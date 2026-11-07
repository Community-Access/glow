/*
 * accessibility-agents-ask.js - "Ask a question with your own AI" on
 * /accessibility-agents.
 *
 * The visitor's key lives only in this tab's sessionStorage, which the
 * browser clears when the tab or the browser closes. It is sent with each
 * question to GLOW, which passes it to the chosen provider and stores
 * nothing (see aa_ask.py).
 *
 * OpenRouter sign-in uses OAuth PKCE: the verifier is made and kept here,
 * OpenRouter returns to this page with ?code=, and GLOW trades the code and
 * verifier for a key, which comes straight back into sessionStorage.
 */
(function () {
  "use strict";

  var form = document.getElementById("aa-ask-form");
  if (!form) return;

  var PAGE = "/accessibility-agents/";
  var status = document.getElementById("aa-ask-status");
  var provider = document.getElementById("aa-provider");
  var keyField = document.getElementById("aa-key");
  var model = document.getElementById("aa-model");
  var modelDefault = document.getElementById("aa-model-default");
  var pick = document.getElementById("aa-model-pick");
  var modelsButton = document.getElementById("aa-models-button");
  var keyLink = document.getElementById("aa-key-link");
  var signin = document.getElementById("aa-openrouter-signin");
  var signinButton = document.getElementById("aa-openrouter-button");
  var forget = document.getElementById("aa-forget");
  var answer = document.getElementById("aa-answer");
  var answerHeading = document.getElementById("aa-answer-heading");
  var answerBody = document.getElementById("aa-answer-body");
  var answerMeta = document.getElementById("aa-answer-meta");

  var store = {
    get: function (k) { try { return window.sessionStorage.getItem(k) || ""; } catch (e) { return ""; } },
    set: function (k, v) { try { window.sessionStorage.setItem(k, v); } catch (e) { /* private mode */ } },
    del: function (k) { try { window.sessionStorage.removeItem(k); } catch (e) { /* private mode */ } }
  };
  var keyName = function () { return "aa.key." + provider.value; };

  function csrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.error || ("The request failed (" + r.status + ")."));
        return data;
      });
    });
  }

  // The model list for the chosen service. Model names are not secret, but
  // they live in sessionStorage too, so they go when the tab does.
  function fillPick(models, chosen) {
    var def = provider.options[provider.selectedIndex].getAttribute("data-default-model");
    pick.textContent = "";
    var first = document.createElement("option");
    first.value = "";
    first.textContent = "The default, " + def;
    pick.appendChild(first);
    models.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m.id;
      o.textContent = m.name === m.id ? m.id : m.name + " (" + m.id + ")";
      pick.appendChild(o);
    });
    pick.value = chosen && pick.querySelector('option[value="' + CSS.escape(chosen) + '"]') ? chosen : "";
  }

  function savedModels() {
    try { return JSON.parse(store.get("aa.models." + provider.value) || "[]"); } catch (e) { return []; }
  }

  function syncProvider() {
    var opt = provider.options[provider.selectedIndex];
    modelDefault.textContent = opt.getAttribute("data-default-model");
    fillPick(savedModels(), store.get("aa.pick." + provider.value));
    keyLink.href = opt.getAttribute("data-key-url");
    signin.hidden = provider.value !== "openrouter";
    keyField.value = store.get(keyName());
    store.set("aa.provider", provider.value);
  }

  // Restore this tab's choices.
  var saved = store.get("aa.provider");
  if (saved && provider.querySelector('option[value="' + saved + '"]')) provider.value = saved;
  model.value = store.get("aa.model");
  syncProvider();

  provider.addEventListener("change", syncProvider);
  keyField.addEventListener("input", function () {
    if (keyField.value.trim()) store.set(keyName(), keyField.value.trim());
    else store.del(keyName());
  });
  model.addEventListener("input", function () { store.set("aa.model", model.value.trim()); });
  pick.addEventListener("change", function () { store.set("aa.pick." + provider.value, pick.value); });

  modelsButton.addEventListener("click", function () {
    var key = keyField.value.trim();
    if (!key && provider.value !== "openrouter") {
      status.textContent = "Enter your API key first, so the list shows the models it can use.";
      keyField.focus();
      return;
    }
    modelsButton.disabled = true;
    status.textContent = "Getting your models.";
    post(PAGE + "models", { provider: provider.value, key: key }).then(function (data) {
      var models = data.models || [];
      store.set("aa.models." + provider.value, JSON.stringify(models));
      fillPick(models, store.get("aa.pick." + provider.value));
      if (models.length) {
        status.textContent = models.length + (models.length === 1 ? " model" : " models") +
          " found. Choose one from the Model list.";
        pick.focus();
      } else {
        status.textContent = "No chat models were found for this key. The default will be used.";
      }
    }).catch(function (err) {
      status.textContent = err.message;
    }).then(function () {
      modelsButton.disabled = false;
    });
  });

  forget.addEventListener("click", function () {
    Array.prototype.forEach.call(provider.options, function (o) { store.del("aa.key." + o.value); });
    store.del("aa.or.verifier");
    keyField.value = "";
    status.textContent = "Your keys are forgotten in this tab.";
    keyField.focus();
  });

  // ---- OpenRouter sign-in (PKCE) ----
  function base64url(bytes) {
    var s = "";
    for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  signinButton.addEventListener("click", function () {
    if (!window.crypto || !window.crypto.subtle) {
      status.textContent = "This browser cannot sign in to OpenRouter. Paste an OpenRouter key instead.";
      return;
    }
    var verifier = base64url(window.crypto.getRandomValues(new Uint8Array(32)));
    store.set("aa.or.verifier", verifier);
    window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)).then(function (hash) {
      var callback = window.location.origin + PAGE;
      window.location.href = "https://openrouter.ai/auth?callback_url=" + encodeURIComponent(callback) +
        "&code_challenge=" + base64url(new Uint8Array(hash)) + "&code_challenge_method=S256";
    });
  });

  var params = new URLSearchParams(window.location.search);
  if (params.get("code")) {
    var code = params.get("code");
    var verifier = store.get("aa.or.verifier");
    window.history.replaceState(null, "", PAGE + "#aa-ask");
    store.del("aa.or.verifier");
    provider.value = "openrouter";
    syncProvider();
    status.textContent = "Finishing the OpenRouter sign-in.";
    post(PAGE + "openrouter/exchange", { code: code, code_verifier: verifier }).then(function (data) {
      store.set("aa.key.openrouter", data.key);
      keyField.value = data.key;
      status.textContent = "Signed in to OpenRouter. The key is kept in this tab only.";
      document.getElementById("aa-question").focus();
    }).catch(function (err) {
      status.textContent = err.message;
    });
  }

  // ---- A file to review ----
  // GLOW turns the file into text (and deletes it); the text goes into the
  // material box, where the visitor can read or trim it before asking.
  var fileInput = document.getElementById("aa-file");
  var materialBox = document.getElementById("aa-material");
  var fileSource = "";
  var fileScan = "";
  var fileSpecialist = "";
  var fileImage = "";
  var IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];
  var scanBox = document.getElementById("aa-scan");
  var scanText = document.getElementById("aa-scan-text");
  fileInput.addEventListener("change", function () {
    var file = fileInput.files && fileInput.files[0];
    fileSource = "";
    fileScan = "";
    fileSpecialist = "";
    fileImage = "";
    scanBox.hidden = true;
    if (!file) return;
    if (IMAGE_TYPES.indexOf(file.type) !== -1) {
      if (file.size > 5 * 1024 * 1024) {
        status.textContent = "Choose an image under 5 MB.";
        fileInput.value = "";
        return;
      }
      var reader = new FileReader();
      reader.onload = function () {
        fileImage = String(reader.result || "");
        fileSource = file.name;
        var q = document.getElementById("aa-question");
        if (!q.value.trim()) q.value = "Write alt text for this image, and a long description if it needs one.";
        status.textContent = "Image ready: " + file.name + ". The question is filled in; change it if you like, then Ask.";
      };
      reader.onerror = function () {
        fileInput.value = "";
        status.textContent = "That image could not be read. Try another.";
      };
      reader.readAsDataURL(file);
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      status.textContent = "Choose a file under 20 MB.";
      fileInput.value = "";
      return;
    }
    var data = new FormData();
    data.append("file", file);
    fileInput.disabled = true;
    status.textContent = "Reading and scanning " + file.name + ".";
    fetch(PAGE + "extract", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf() },
      body: data
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error(d.error || ("The file could not be read (" + r.status + ")."));
        return d;
      });
    }).then(function (d) {
      materialBox.value = d.text;
      fileSource = d.filename + " (" + d.kind + ")";
      fileScan = d.scan || "";
      fileSpecialist = d.specialist || "";
      scanText.textContent = fileScan;
      scanBox.hidden = !fileScan;
      var scanned = fileScan
        ? " The scanner found " + (d.issues === null || d.issues === undefined ? "its results" :
            d.issues + (d.issues === 1 ? " issue" : " issues")) + ", shown under Scanner report." +
          (fileSpecialist ? " The " + fileSpecialist + " specialist will review it." : "")
        : "";
      status.textContent = "Read " + d.filename + ": " + d.characters.toLocaleString() + " characters" +
        (d.truncated ? ", cut to the first 50,000" : "") + "." + scanned +
        " Type your question, then Ask.";
    }).catch(function (err) {
      fileInput.value = "";
      status.textContent = err.message;
    }).then(function () {
      fileInput.disabled = false;
    });
  });

  // ---- Showing an answer ----
  // Models answer in Markdown. Read as plain text, a screen reader speaks
  // every asterisk and hash, so the common parts (headings, lists, bold,
  // code) become real elements. Built with createElement and textContent
  // only: nothing from the model is ever parsed as HTML.
  function inline(parent, text) {
    var re = /(\*\*([^*]+)\*\*|__([^_]+)__|`([^`]+)`|\*([^*\s][^*]*)\*)/g;
    var last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      var el;
      if (m[2] || m[3]) { el = document.createElement("strong"); el.textContent = m[2] || m[3]; }
      else if (m[4]) { el = document.createElement("code"); el.textContent = m[4]; }
      else { el = document.createElement("em"); el.textContent = m[5]; }
      parent.appendChild(el);
      last = re.lastIndex;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderAnswer(target, markdown) {
    target.textContent = "";
    var list = null, listType = "", para = null, fence = null;
    function close() { list = null; listType = ""; para = null; }
    var lines = String(markdown || "").split(/\r?\n/);
    // Whatever heading levels the model used, the biggest becomes h4 and the
    // next h5, so the outline never skips a level under the answer's h3.
    var levels = [];
    lines.forEach(function (l) {
      var m = /^\s{0,3}(#{1,6})\s+/.exec(l);
      if (m && levels.indexOf(m[1].length) === -1) levels.push(m[1].length);
    });
    levels.sort();
    lines.forEach(function (line) {
      if (/^\s*```/.test(line)) {
        if (fence) { fence = null; } else { close(); fence = document.createElement("pre"); target.appendChild(fence); }
        return;
      }
      if (fence) { fence.textContent += (fence.textContent ? "\n" : "") + line; return; }
      var h = /^\s{0,3}(#{1,6})\s+(.*)$/.exec(line);
      var ul = /^\s*[-*+]\s+(.*)$/.exec(line);
      var ol = /^\s*\d+[.)]\s+(.*)$/.exec(line);
      if (!line.trim()) { close(); return; }
      if (h) {
        close();
        var level = Math.min(6, 4 + levels.indexOf(h[1].length));
        var el = document.createElement("h" + level);
        inline(el, h[2].replace(/\s*#+\s*$/, ""));
        target.appendChild(el);
        return;
      }
      if (ul || ol) {
        var type = ul ? "ul" : "ol";
        // An indented bullet under a numbered item stays with that item.
        if (ul && listType === "ol" && /^\s{2,}/.test(line) && list.lastChild) {
          var sub = list.lastChild.querySelector("ul");
          if (!sub) { sub = document.createElement("ul"); list.lastChild.appendChild(sub); }
          var subItem = document.createElement("li");
          inline(subItem, ul[1]);
          sub.appendChild(subItem);
          return;
        }
        if (listType !== type) { para = null; list = document.createElement(type); listType = type; target.appendChild(list); }
        var li = document.createElement("li");
        inline(li, (ul || ol)[1]);
        list.appendChild(li);
        return;
      }
      if (list && /^\s{2,}/.test(line) && list.lastChild) {
        list.lastChild.appendChild(document.createTextNode(" "));
        inline(list.lastChild, line.trim());
        return;
      }
      list = null; listType = "";
      if (!para) { para = document.createElement("p"); target.appendChild(para); }
      else { para.appendChild(document.createTextNode(" ")); }
      inline(para, line.trim());
    });
  }

  // ---- Asking ----
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var question = document.getElementById("aa-question");
    var material = document.getElementById("aa-material");
    if (!keyField.value.trim()) {
      status.textContent = "Enter your API key first" + (provider.value === "openrouter" ? ", or sign in with OpenRouter." : ".");
      keyField.focus();
      return;
    }
    if (!question.value.trim()) {
      status.textContent = "Type a question first.";
      question.focus();
      return;
    }
    var button = form.querySelector("button[type=submit]");
    button.disabled = true;
    status.textContent = "Asking. This can take up to a minute.";
    post(PAGE + "ask", {
      provider: provider.value,
      key: keyField.value.trim(),
      model: model.value.trim() || pick.value,
      question: question.value,
      material: material.value,
      source: fileImage || material.value.trim() ? fileSource : "",
      image: fileImage,
      scan: material.value.trim() ? fileScan : "",
      specialist: material.value.trim() ? fileSpecialist : ""
    }).then(function (data) {
      renderAnswer(answerBody, data.answer);
      answerMeta.textContent = "Answered by " + data.provider + ", " + data.model + "." +
        (data.specialist ? " Specialist: " + data.specialist + "." : "") +
        (data.tools_used && data.tools_used.length
          ? " Checks it ran: " + data.tools_used.join(", ") + "."
          : " It ran no checks.");
      answer.hidden = false;
      status.textContent = "Answer ready.";
      answerHeading.focus();
    }).catch(function (err) {
      status.textContent = err.message;
    }).then(function () {
      button.disabled = false;
    });
  });
})();
