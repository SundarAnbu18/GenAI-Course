(function () {
  var config = window.RAGBOT_CONFIG || {};
  var API_URL = config.apiUrl;
  var API_KEY = config.apiKey || null;

  if (!API_URL) {
    console.error('RAGBOT_CONFIG.apiUrl is required before loading widget.js');
    return;
  }

  var style = document.createElement('style');
  style.textContent = [
    '#ragbot-launcher{position:fixed;bottom:24px;right:24px;width:58px;height:58px;border-radius:50%;',
    'background:linear-gradient(120deg,#6366f1,#8b5cf6);border:none;box-shadow:0 12px 28px rgba(99,102,241,.45);',
    'cursor:pointer;z-index:999999;display:flex;align-items:center;justify-content:center;transition:transform .15s ease;}',
    '#ragbot-launcher:hover{transform:scale(1.06);}',
    '#ragbot-launcher svg{width:26px;height:26px;fill:#fff;}',
    '#ragbot-panel{position:fixed;bottom:96px;right:24px;width:340px;max-width:calc(100vw - 32px);height:460px;',
    'max-height:calc(100vh - 140px);background:#fff;border-radius:16px;box-shadow:0 25px 60px rgba(0,0,0,.35);',
    'display:none;flex-direction:column;overflow:hidden;z-index:999999;font-family:-apple-system,BlinkMacSystemFont,',
    '"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}',
    '#ragbot-panel.open{display:flex;}',
    '#ragbot-header{padding:16px 18px;background:linear-gradient(120deg,#6366f1,#8b5cf6);color:#fff;',
    'font-weight:700;font-size:15px;display:flex;align-items:center;justify-content:space-between;}',
    '#ragbot-close{background:none;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1;opacity:.85;}',
    '#ragbot-close:hover{opacity:1;}',
    '#ragbot-messages{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;background:#fafafa;}',
    '.ragbot-bubble{max-width:85%;padding:10px 13px;border-radius:12px;font-size:13.5px;line-height:1.5;white-space:pre-wrap;}',
    '.ragbot-bubble.user{align-self:flex-end;background:#eef2ff;color:#1e1b2e;border-bottom-right-radius:3px;}',
    '.ragbot-bubble.bot{align-self:flex-start;background:#fff;border:1px solid #eef0f4;color:#1e1b2e;border-bottom-left-radius:3px;}',
    '.ragbot-bubble.pending{align-self:flex-start;color:#9ca3af;font-style:italic;}',
    '#ragbot-form{display:flex;gap:8px;padding:12px;border-top:1px solid #eee;background:#fff;}',
    '#ragbot-input{flex:1;resize:none;border:1.5px solid #e5e7eb;border-radius:10px;padding:9px 11px;font-size:13.5px;',
    'font-family:inherit;outline:none;height:38px;}',
    '#ragbot-input:focus{border-color:#6366f1;}',
    '#ragbot-send{border:none;border-radius:10px;padding:0 16px;background:linear-gradient(120deg,#6366f1,#8b5cf6);',
    'color:#fff;font-weight:600;font-size:13.5px;cursor:pointer;}',
    '#ragbot-send:disabled{opacity:.6;cursor:default;}'
  ].join('');
  document.head.appendChild(style);

  var launcher = document.createElement('button');
  launcher.id = 'ragbot-launcher';
  launcher.setAttribute('aria-label', 'Open chat');
  launcher.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 3C6.48 3 2 6.94 2 11.8c0 2.63 1.35 4.98 3.48 6.58L5 21l3.6-1.34c1.05.3 2.18.46 3.4.46 5.52 0 10-3.94 10-8.8S17.52 3 12 3z"/></svg>';

  var panel = document.createElement('div');
  panel.id = 'ragbot-panel';
  panel.innerHTML =
    '<div id="ragbot-header"><span>Chat with us</span><button id="ragbot-close" aria-label="Close chat">✕</button></div>' +
    '<div id="ragbot-messages"></div>' +
    '<form id="ragbot-form">' +
    '<textarea id="ragbot-input" placeholder="Ask a question..." rows="1"></textarea>' +
    '<button id="ragbot-send" type="submit">Send</button>' +
    '</form>';

  document.body.appendChild(launcher);
  document.body.appendChild(panel);

  var messagesEl = panel.querySelector('#ragbot-messages');
  var formEl = panel.querySelector('#ragbot-form');
  var inputEl = panel.querySelector('#ragbot-input');
  var sendEl = panel.querySelector('#ragbot-send');
  var closeEl = panel.querySelector('#ragbot-close');

  function addBubble(text, cls) {
    var el = document.createElement('div');
    el.className = 'ragbot-bubble ' + cls;
    el.textContent = text;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  launcher.addEventListener('click', function () {
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) inputEl.focus();
  });
  closeEl.addEventListener('click', function () {
    panel.classList.remove('open');
  });

  formEl.addEventListener('submit', function (e) {
    e.preventDefault();
    var question = inputEl.value.trim();
    if (!question) return;

    addBubble(question, 'user');
    inputEl.value = '';
    sendEl.disabled = true;
    var pending = addBubble('Thinking...', 'bot pending');

    var headers = { 'Content-Type': 'application/json' };
    if (API_KEY) headers['X-Api-Key'] = API_KEY;

    fetch(API_URL, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ question: question })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        pending.remove();
        addBubble(data.answer || data.error || 'Something went wrong.', 'bot');
      })
      .catch(function () {
        pending.remove();
        addBubble('Network error — please try again.', 'bot');
      })
      .finally(function () {
        sendEl.disabled = false;
      });
  });
})();
