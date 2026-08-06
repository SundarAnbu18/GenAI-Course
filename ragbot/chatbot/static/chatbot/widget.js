(function () {
  var config = window.RAGBOT_CONFIG || {};
  var API_URL = config.apiUrl;
  var API_KEY = config.apiKey || null;

  if (!API_URL) {
    console.error('RAGBOT_CONFIG.apiUrl is required before loading widget.js');
    return;
  }

  // Ties a visitor's turns together so follow-ups make sense. Set
  // RAGBOT_CONFIG.remember = false to keep every question stateless.
  var CONVERSATION_KEY = 'ragbot-conversation';
  var REMEMBER = config.remember !== false;

  function uuid4() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    if (!window.crypto || !crypto.getRandomValues) return null;
    var bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    var hex = [];
    for (var i = 0; i < 16; i++) hex.push((bytes[i] + 0x100).toString(16).slice(1));
    return [
      hex.slice(0, 4).join(''), hex.slice(4, 6).join(''), hex.slice(6, 8).join(''),
      hex.slice(8, 10).join(''), hex.slice(10, 16).join('')
    ].join('-');
  }

  function conversationId() {
    if (!REMEMBER) return null;
    // Third-party storage is often blocked; stateless is the safe fallback.
    try {
      var id = localStorage.getItem(CONVERSATION_KEY);
      if (!id) {
        id = uuid4();
        if (!id) return null;
        localStorage.setItem(CONVERSATION_KEY, id);
      }
      return id;
    } catch (e) {
      return null;
    }
  }

  var style = document.createElement('style');
  style.textContent = [
    '#ragbot-launcher{position:fixed;bottom:24px;right:24px;width:60px;height:60px;border-radius:50%;',
    'background:linear-gradient(135deg,#fbbf24,#f59e0b);border:none;box-shadow:0 10px 30px rgba(245,158,11,.4),0 0 0 1px rgba(255,255,255,.06);',
    'cursor:pointer;z-index:999999;display:flex;align-items:center;justify-content:center;transition:transform .18s ease,box-shadow .18s ease;}',
    '#ragbot-launcher:hover{transform:scale(1.07);box-shadow:0 14px 34px rgba(245,158,11,.5),0 0 0 1px rgba(255,255,255,.08);}',
    '#ragbot-launcher svg{width:26px;height:26px;fill:#1a1206;}',

    '#ragbot-panel{position:fixed;bottom:96px;right:24px;width:352px;max-width:calc(100vw - 32px);height:480px;',
    'max-height:calc(100vh - 140px);background:#121218;border-radius:18px;box-shadow:0 30px 70px rgba(0,0,0,.55),0 0 0 1px rgba(255,255,255,.06);',
    'display:flex;flex-direction:column;overflow:hidden;z-index:999999;font-family:-apple-system,BlinkMacSystemFont,',
    '"Segoe UI",Roboto,Helvetica,Arial,sans-serif;',
    'opacity:0;visibility:hidden;transform:translateY(16px) scale(.97);transform-origin:bottom right;',
    'transition:opacity .18s ease,transform .18s ease,visibility .18s;}',
    '#ragbot-panel.open{opacity:1;visibility:visible;transform:translateY(0) scale(1);}',

    '#ragbot-header{padding:18px 20px;background:#17171f;border-bottom:1px solid rgba(255,255,255,.06);',
    'display:flex;align-items:center;justify-content:space-between;}',
    '#ragbot-header-title{display:flex;flex-direction:column;gap:2px;}',
    '#ragbot-header-title strong{color:#f5f5f7;font-size:14.5px;font-weight:700;letter-spacing:-.01em;}',
    '#ragbot-header-title span{color:#8a8a93;font-size:11.5px;display:flex;align-items:center;gap:5px;}',
    '#ragbot-header-title span::before{content:"";width:6px;height:6px;border-radius:50%;background:#34d399;',
    'box-shadow:0 0 0 3px rgba(52,211,153,.18);display:inline-block;}',
    '#ragbot-close{background:none;border:none;color:#8a8a93;font-size:16px;cursor:pointer;line-height:1;',
    'padding:6px;border-radius:8px;transition:background .15s,color .15s;}',
    '#ragbot-close:hover{background:rgba(255,255,255,.06);color:#f5f5f7;}',

    '#ragbot-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;background:#121218;}',
    '#ragbot-messages:empty::before{content:"Ask me anything about this page \\2014 I\'ll answer from what I know.";',
    'color:#5c5c66;font-size:13px;line-height:1.6;display:block;padding-top:8px;}',
    '.ragbot-bubble{max-width:85%;padding:10px 14px;border-radius:14px;font-size:13.5px;line-height:1.55;white-space:pre-wrap;}',
    '.ragbot-bubble.user{align-self:flex-end;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#1a1206;',
    'font-weight:500;border-bottom-right-radius:4px;}',
    '.ragbot-bubble.bot{align-self:flex-start;background:#1c1c25;border:1px solid rgba(255,255,255,.07);',
    'color:#e4e4e9;border-bottom-left-radius:4px;}',
    '.ragbot-bubble.pending{align-self:flex-start;color:#7a7a85;font-style:italic;background:transparent;border:none;padding-left:2px;}',

    '#ragbot-form{display:flex;gap:8px;padding:14px;border-top:1px solid rgba(255,255,255,.06);background:#17171f;}',
    '#ragbot-input{flex:1;resize:none;border:1.5px solid rgba(255,255,255,.09);border-radius:11px;padding:10px 12px;',
    'font-size:13.5px;font-family:inherit;outline:none;height:40px;background:#1c1c25;color:#f5f5f7;transition:border-color .15s;}',
    '#ragbot-input::placeholder{color:#5c5c66;}',
    '#ragbot-input:focus{border-color:#f59e0b;}',
    '#ragbot-send{border:none;border-radius:11px;padding:0 18px;background:linear-gradient(135deg,#fbbf24,#f59e0b);',
    'color:#1a1206;font-weight:700;font-size:13.5px;cursor:pointer;transition:transform .12s,opacity .12s;}',
    '#ragbot-send:hover:not(:disabled){transform:translateY(-1px);}',
    '#ragbot-send:disabled{opacity:.5;cursor:default;}',

    '#ragbot-messages::-webkit-scrollbar{width:6px;}',
    '#ragbot-messages::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:3px;}'
  ].join('');
  document.head.appendChild(style);

  var launcher = document.createElement('button');
  launcher.id = 'ragbot-launcher';
  launcher.setAttribute('aria-label', 'Open chat');
  launcher.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 3C6.48 3 2 6.94 2 11.8c0 2.63 1.35 4.98 3.48 6.58L5 21l3.6-1.34c1.05.3 2.18.46 3.4.46 5.52 0 10-3.94 10-8.8S17.52 3 12 3z"/></svg>';

  var panel = document.createElement('div');
  panel.id = 'ragbot-panel';
  panel.innerHTML =
    '<div id="ragbot-header">' +
      '<div id="ragbot-header-title"><strong>Chat with us</strong><span>Online now</span></div>' +
      '<button id="ragbot-close" aria-label="Close chat">✕</button>' +
    '</div>' +
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

    var payload = { question: question };
    var conversation = conversationId();
    if (conversation) payload.conversation_id = conversation;

    fetch(API_URL, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload)
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
