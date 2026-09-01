(function () {
  'use strict';

  var tokenEl = document.getElementById('alt-text-token');
  var statusEl = document.getElementById('alt-text-status');
  var extraInstructionEl = document.getElementById('extra-instruction');
  var variantStyleEl = document.getElementById('variant-style');
  var variantCountEl = document.getElementById('variant-count');
  var systemPromptAddonEl = document.getElementById('system-prompt-addon');
  var generateButtons = document.querySelectorAll('.alt-text-generate-btn');
  var copyButtons = document.querySelectorAll('.alt-text-copy-btn');

  if (!tokenEl || !generateButtons.length) {
    return;
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') || '' : '';
  }

  function setStatus(message) {
    if (statusEl) {
      statusEl.textContent = message;
    }
  }

  function requestSuggestion(button) {
    var fd = new FormData();
    var itemIndex = button.getAttribute('data-item-index') || '0';
    var target = document.getElementById('suggestion-' + itemIndex);

    fd.append('token', tokenEl.value);
    fd.append('item_index', itemIndex);
    fd.append('extra_instruction', extraInstructionEl ? extraInstructionEl.value : '');
    fd.append('variant_style', variantStyleEl ? variantStyleEl.value : 'balanced');
    fd.append('variant_count', variantCountEl ? variantCountEl.value : '1');
    fd.append('system_prompt_addon', systemPromptAddonEl ? systemPromptAddonEl.value : '');

    button.disabled = true;
    button.textContent = 'Generating...';
    setStatus('Generating alt text suggestion...');

    fetch(window.location.pathname.replace(/\/$/, '') + '/suggest', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': getCsrfToken() }
    })
      .then(function (response) {
        return response.json().then(
          function (data) {
            return { ok: response.ok, data: data };
          },
          function () {
            // Body was not JSON (e.g. an HTML error page). Surface a clean
            // status instead of announcing a raw SyntaxError to the reader.
            throw new Error('Server error ' + response.status);
          }
        );
      })
      .then(function (payload) {
        if (!payload.ok || !payload.data || !payload.data.ok) {
          throw new Error((payload.data && payload.data.error) || 'Could not generate alt text.');
        }
        if (target) {
          target.value = payload.data.suggestion || '';
        }
        renderVariants(itemIndex, payload.data.variants || []);
        setStatus('Suggestion ready for ' + (payload.data.label || ('item ' + itemIndex)) + '.');
        document.dispatchEvent(new CustomEvent('ai:request-complete'));
      })
      .catch(function (error) {
        setStatus(error && error.message ? error.message : 'Could not generate alt text.');
      })
      .finally(function () {
        button.disabled = false;
        button.textContent = 'Generate suggestion';
      });
  }

  function renderVariants(itemIndex, variants) {
    var container = document.getElementById('variant-list-' + itemIndex);
    var target = document.getElementById('suggestion-' + itemIndex);
    if (!container) {
      return;
    }
    container.innerHTML = '';
    if (!variants || variants.length < 2) {
      return;
    }

    var heading = document.createElement('p');
    heading.innerHTML = '<strong>Alternative options</strong>';
    container.appendChild(heading);

    variants.forEach(function (variant, idx) {
      if (!variant) {
        return;
      }
      var item = document.createElement('div');
      item.setAttribute('role', 'listitem');

      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn-secondary';
      btn.textContent = 'Use option ' + (idx + 1);
      btn.addEventListener('click', function () {
        if (target) {
          target.value = variant;
          setStatus('Loaded option ' + (idx + 1) + ' into suggestion box.');
        }
      });

      var text = document.createElement('p');
      text.textContent = variant;

      item.appendChild(btn);
      item.appendChild(text);
      container.appendChild(item);
    });
  }

  Array.prototype.forEach.call(generateButtons, function (button) {
    button.addEventListener('click', function () {
      requestSuggestion(button);
    });
  });

  Array.prototype.forEach.call(copyButtons, function (button) {
    button.addEventListener('click', function () {
      var targetId = button.getAttribute('data-target') || '';
      var target = document.getElementById(targetId);
      if (!target || !target.value) {
        setStatus('Nothing to copy yet for this item.');
        return;
      }
      target.select();
      target.setSelectionRange(0, target.value.length);
      // navigator.clipboard is undefined on non-secure origins, so guard it
      // and fall back to execCommand (mirrors static/inline-handlers.js).
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(target.value)
          .then(function () {
            setStatus('Suggestion copied to clipboard.');
          })
          .catch(function () {
            setStatus('Could not copy automatically. The text is selected for manual copy.');
          });
      } else {
        try {
          document.execCommand('copy');
          setStatus('Suggestion copied to clipboard.');
        } catch (err) {
          setStatus('Could not copy automatically. The text is selected for manual copy.');
        }
      }
    });
  });
}());
