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

  function syncProvider() {
    var opt = provider.options[provider.selectedIndex];
    modelDefault.textContent = opt.getAttribute("data-default-model");
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
      model: model.value.trim(),
      question: question.value,
      material: material.value
    }).then(function (data) {
      answerBody.textContent = data.answer;
      answerMeta.textContent = "Answered by " + data.provider + ", " + data.model + "." +
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
