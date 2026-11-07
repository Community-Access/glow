/*
 * accessibility-agents-check.js - the check tool on /accessibility-agents.
 *
 * Each form calls one tool on the hosted Accessibility Agents MCP server,
 * which Caddy serves on this origin at /a11y/mcp (stateless Streamable HTTP,
 * JSON-RPC 2.0). The server may answer with JSON or with a one-event SSE
 * stream; both are handled. Results go into one region whose heading takes
 * focus, and progress and errors are announced through a status region.
 */
(function () {
  "use strict";

  var ENDPOINT = "/a11y/mcp";
  var status = document.getElementById("aa-status");
  var result = document.getElementById("aa-result");
  var resultHeading = document.getElementById("aa-result-heading");
  var resultBody = document.getElementById("aa-result-body");
  if (!status || !result) return;

  var nextId = 1;

  function parseReply(text) {
    // An SSE reply carries the JSON-RPC message on its data: lines.
    var trimmed = text.trim();
    if (trimmed.charAt(0) === "{") return JSON.parse(trimmed);
    var data = trimmed
      .split(/\r?\n/)
      .filter(function (line) { return line.indexOf("data:") === 0; })
      .map(function (line) { return line.slice(5).trim(); })
      .join("");
    return JSON.parse(data);
  }

  function callTool(name, args) {
    return fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: nextId++,
        method: "tools/call",
        params: { name: name, arguments: args }
      })
    }).then(function (response) {
      if (!response.ok) throw new Error("The server answered " + response.status + ".");
      return response.text();
    }).then(function (text) {
      var message = parseReply(text);
      if (message.error) throw new Error(message.error.message || "The check failed.");
      var res = message.result || {};
      var out = (res.content || [])
        .map(function (part) { return part.text || ""; })
        .join("\n\n");
      return { text: out, isError: Boolean(res.isError) };
    });
  }

  function show(title, sections) {
    resultBody.textContent = "";
    sections.forEach(function (section) {
      if (section.heading) {
        var h = document.createElement("h4");
        h.textContent = section.heading;
        resultBody.appendChild(h);
      }
      var pre = document.createElement("pre");
      pre.className = "aa-result-text";
      pre.textContent = section.text;
      resultBody.appendChild(pre);
    });
    resultHeading.textContent = title;
    result.hidden = false;
    resultHeading.focus();
  }

  function fieldError(form, message) {
    var first = form.querySelector("input[required], textarea[required]");
    var id = form.getAttribute("data-aa-tool") + "-error";
    var existing = document.getElementById(id);
    if (existing) existing.remove();
    if (!message) return;
    var p = document.createElement("p");
    p.id = id;
    p.className = "form-error";
    p.textContent = message;
    first.insertAdjacentElement("afterend", p);
    first.setAttribute("aria-invalid", "true");
    var described = (first.getAttribute("aria-describedby") || "").split(" ").filter(Boolean);
    if (described.indexOf(id) === -1) described.push(id);
    first.setAttribute("aria-describedby", described.join(" "));
    first.focus();
  }

  function clearError(form) {
    var id = form.getAttribute("data-aa-tool") + "-error";
    var existing = document.getElementById(id);
    if (existing) existing.remove();
    form.querySelectorAll("[aria-invalid]").forEach(function (el) {
      el.removeAttribute("aria-invalid");
      var described = (el.getAttribute("aria-describedby") || "").split(" ").filter(function (x) {
        return x && x !== id;
      });
      if (described.length) el.setAttribute("aria-describedby", described.join(" "));
      else el.removeAttribute("aria-describedby");
    });
  }

  var HEX = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i;

  var tools = {
    contrast: function (form) {
      var fg = form.foreground.value.trim();
      var bg = form.background.value.trim();
      if (!HEX.test(fg) || !HEX.test(bg)) {
        return { error: "Enter both colors as hex, such as #1a1a1a or #fff." };
      }
      if (fg.charAt(0) !== "#") fg = "#" + fg;
      if (bg.charAt(0) !== "#") bg = "#" + bg;
      var calls = [{ heading: "WCAG 2.2", name: "check_contrast", args: { foreground: fg, background: bg } }];
      if (form.apca.checked) {
        calls.push({ heading: "APCA (WCAG 3 draft)", name: "check_apca_contrast", args: { foreground: fg, background: bg } });
      }
      return { title: "Contrast: " + fg + " on " + bg, calls: calls };
    },
    reading: function (form) {
      var text = form.text.value.trim();
      if (!text) return { error: "Enter some text to check." };
      return { title: "Reading level", calls: [{ name: "check_reading_level", args: { text: text } }] };
    },
    html: function (form) {
      var html = form.html.value.trim();
      if (!html) return { error: "Paste some HTML to check." };
      var select = form.check;
      var label = select.options[select.selectedIndex].text;
      return { title: label, calls: [{ name: select.value, args: { html: html } }] };
    },
    guidelines: function (form) {
      var select = form.component;
      var label = select.options[select.selectedIndex].text;
      return {
        title: "Guidelines: " + label,
        calls: [{ name: "get_accessibility_guidelines", args: { component: select.value } }]
      };
    }
  };

  document.querySelectorAll("form.aa-check").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      clearError(form);
      var plan = tools[form.getAttribute("data-aa-tool")](form);
      if (plan.error) {
        fieldError(form, plan.error);
        return;
      }
      var button = form.querySelector("button[type=submit]");
      button.disabled = true;
      status.textContent = "Checking.";
      Promise.all(plan.calls.map(function (call) {
        return callTool(call.name, call.args).then(function (r) {
          return { heading: call.heading, text: r.text };
        });
      })).then(function (sections) {
        status.textContent = "Done.";
        show(plan.title, sections);
      }).catch(function (err) {
        status.textContent = "The check did not run: " + err.message + " Try again in a moment.";
      }).then(function () {
        button.disabled = false;
      });
    });
  });
})();
