/**
 * PropBot Chat Widget — Vanilla JS, zero dependencies, mobile-first.
 *
 * Embed on any website with:
 * <script src="https://propbot.onrender.com/static/chat-widget.js"
 *         data-client-id="YOUR_CLIENT_ID"
 *         data-api-url="https://propbot.onrender.com"></script>
 */
(function () {
  "use strict";

  // Config from script tag attributes
  var script = document.currentScript;
  var CLIENT_ID = script.getAttribute("data-client-id") || "";
  var API_BASE = (script.getAttribute("data-api-url") || "").replace(/\/$/, "");

  if (!CLIENT_ID) {
    console.error("PropBot: data-client-id is required");
    return;
  }
  if (!API_BASE) {
    console.error("PropBot: data-api-url is required");
    return;
  }

  // State
  var isOpen = false;
  var isLoading = false;
  var showCallbackForm = false;
  var history = [];
  var visitorId = sessionStorage.getItem("propbot_vid") || generateId();
  sessionStorage.setItem("propbot_vid", visitorId);

  function generateId() {
    return "v_" + Math.random().toString(36).substring(2, 15);
  }

  // Inject CSS
  var style = document.createElement("style");
  style.textContent = getCss();
  document.head.appendChild(style);

  // Build UI
  var container = document.createElement("div");
  container.id = "propbot-widget";
  container.innerHTML = getHtml();
  document.body.appendChild(container);

  // DOM refs
  var fab = container.querySelector("#propbot-fab");
  var panel = container.querySelector("#propbot-panel");
  var closeBtn = container.querySelector("#propbot-close");
  var msgList = container.querySelector("#propbot-messages");
  var input = container.querySelector("#propbot-input");
  var sendBtn = container.querySelector("#propbot-send");
  var callbackBtn = container.querySelector("#propbot-callback-btn");
  var callbackForm = container.querySelector("#propbot-callback-form");
  var callbackSubmit = container.querySelector("#propbot-callback-submit");
  var callbackCancel = container.querySelector("#propbot-callback-cancel");

  // Events
  fab.addEventListener("click", togglePanel);
  closeBtn.addEventListener("click", togglePanel);
  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  callbackBtn.addEventListener("click", function () {
    showCallbackForm = !showCallbackForm;
    callbackForm.style.display = showCallbackForm ? "block" : "none";
  });
  callbackCancel.addEventListener("click", function () {
    showCallbackForm = false;
    callbackForm.style.display = "none";
  });
  callbackSubmit.addEventListener("click", submitCallback);

  // Add welcome message
  addMessage("assistant", "Namaste! Main aapki kya madad kar sakti hoon? Property ke baare mein kuch bhi poochiye.");

  function togglePanel() {
    isOpen = !isOpen;
    panel.style.display = isOpen ? "flex" : "none";
    fab.style.display = isOpen ? "none" : "flex";
    if (isOpen) input.focus();
  }

  function addMessage(role, text) {
    var div = document.createElement("div");
    div.className = "propbot-msg propbot-msg-" + role;
    div.textContent = text;
    msgList.appendChild(div);
    msgList.scrollTop = msgList.scrollHeight;
    history.push({ role: role, content: text });
  }

  function addTypingIndicator() {
    var div = document.createElement("div");
    div.className = "propbot-msg propbot-msg-assistant propbot-typing";
    div.textContent = "...";
    div.id = "propbot-typing";
    msgList.appendChild(div);
    msgList.scrollTop = msgList.scrollHeight;
  }

  function removeTypingIndicator() {
    var el = document.getElementById("propbot-typing");
    if (el) el.remove();
  }

  function sendMessage() {
    var text = input.value.trim();
    if (!text || isLoading) return;

    addMessage("user", text);
    input.value = "";
    isLoading = true;
    sendBtn.disabled = true;
    addTypingIndicator();

    // Build history for API (exclude last user message, it's sent separately)
    var apiHistory = history.slice(0, -1).map(function (m) {
      return { role: m.role, content: m.content };
    });

    fetch(API_BASE + "/api/chat/" + CLIENT_ID, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: apiHistory,
        visitor_id: visitorId,
      }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Server error");
        return res.json();
      })
      .then(function (data) {
        removeTypingIndicator();
        addMessage("assistant", data.reply);
        if (data.visitor_id) visitorId = data.visitor_id;
      })
      .catch(function () {
        removeTypingIndicator();
        addMessage(
          "assistant",
          "Sorry, kuch gadbad ho gayi. Kripya dubara try karein ya callback request karein."
        );
      })
      .finally(function () {
        isLoading = false;
        sendBtn.disabled = false;
      });
  }

  function submitCallback() {
    var name = container.querySelector("#propbot-cb-name").value.trim();
    var phone = container.querySelector("#propbot-cb-phone").value.trim();
    var time = container.querySelector("#propbot-cb-time").value.trim();

    if (!phone) {
      alert("Phone number is required");
      return;
    }

    // Get last few messages as context
    var context = history
      .slice(-4)
      .map(function (m) {
        return m.role + ": " + m.content;
      })
      .join("\n");

    fetch(API_BASE + "/api/chat/" + CLIENT_ID + "/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        phone: phone,
        preferred_time: time,
        context: context,
      }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Server error");
        return res.json();
      })
      .then(function () {
        callbackForm.style.display = "none";
        showCallbackForm = false;
        addMessage(
          "assistant",
          "Aapki callback request mil gayi hai. Agent aapko jald call karenge!"
        );
        container.querySelector("#propbot-cb-name").value = "";
        container.querySelector("#propbot-cb-phone").value = "";
        container.querySelector("#propbot-cb-time").value = "";
      })
      .catch(function () {
        alert("Error submitting callback. Please try again.");
      });
  }

  function getHtml() {
    return (
      '<button id="propbot-fab" aria-label="Chat with us">' +
      '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>' +
      "</button>" +
      '<div id="propbot-panel" style="display:none">' +
      '<div id="propbot-header">' +
      '<div id="propbot-header-info">' +
      '<div id="propbot-avatar">P</div>' +
      "<div><strong>Priya</strong><br><small>AI Assistant</small></div>" +
      "</div>" +
      '<div id="propbot-header-actions">' +
      '<button id="propbot-callback-btn" title="Request Callback">&#128222;</button>' +
      '<button id="propbot-close" title="Close">&times;</button>' +
      "</div>" +
      "</div>" +
      '<div id="propbot-callback-form" style="display:none">' +
      "<p><strong>Request a Callback</strong></p>" +
      '<input id="propbot-cb-name" placeholder="Your name" />' +
      '<input id="propbot-cb-phone" placeholder="Phone number *" type="tel" />' +
      '<input id="propbot-cb-time" placeholder="Preferred time (optional)" />' +
      '<div class="propbot-cb-actions">' +
      '<button id="propbot-callback-submit">Submit</button>' +
      '<button id="propbot-callback-cancel">Cancel</button>' +
      "</div>" +
      "</div>" +
      '<div id="propbot-messages"></div>' +
      '<div id="propbot-input-area">' +
      '<input id="propbot-input" placeholder="Type your message..." />' +
      '<button id="propbot-send" aria-label="Send">' +
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>' +
      "</button>" +
      "</div>" +
      "</div>"
    );
  }

  function getCss() {
    return (
      "#propbot-widget{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:14px;}" +
      "#propbot-fab{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#2563eb;color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(0,0,0,0.2);z-index:9999;transition:transform .2s;}" +
      "#propbot-fab:hover{transform:scale(1.1);}" +
      "#propbot-panel{position:fixed;bottom:20px;right:20px;width:380px;max-width:calc(100vw - 24px);height:560px;max-height:calc(100vh - 40px);border-radius:16px;background:#fff;box-shadow:0 8px 30px rgba(0,0,0,0.15);z-index:9999;flex-direction:column;overflow:hidden;}" +
      "@media(max-width:767px){#propbot-panel{width:100%;height:100%;max-width:100%;max-height:100%;bottom:0;right:0;border-radius:0;}}" +
      "#propbot-header{background:#2563eb;color:#fff;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;}" +
      "#propbot-header-info{display:flex;align-items:center;gap:10px;}" +
      "#propbot-avatar{width:36px;height:36px;border-radius:50%;background:#1d4ed8;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:16px;}" +
      "#propbot-header small{opacity:0.8;font-size:12px;}" +
      "#propbot-header-actions{display:flex;gap:4px;}" +
      "#propbot-header-actions button{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:4px 8px;border-radius:4px;}" +
      "#propbot-header-actions button:hover{background:rgba(255,255,255,0.2);}" +
      "#propbot-callback-form{padding:12px 16px;background:#f0f4ff;border-bottom:1px solid #dbeafe;}" +
      "#propbot-callback-form p{margin:0 0 8px;font-size:13px;}" +
      "#propbot-callback-form input{width:100%;padding:8px 10px;margin-bottom:6px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;box-sizing:border-box;}" +
      ".propbot-cb-actions{display:flex;gap:8px;margin-top:4px;}" +
      ".propbot-cb-actions button{flex:1;padding:8px;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500;}" +
      "#propbot-callback-submit{background:#2563eb;color:#fff;}" +
      "#propbot-callback-cancel{background:#e5e7eb;color:#374151;}" +
      "#propbot-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px;}" +
      ".propbot-msg{max-width:80%;padding:10px 14px;border-radius:12px;line-height:1.4;word-wrap:break-word;white-space:pre-wrap;}" +
      ".propbot-msg-user{align-self:flex-end;background:#2563eb;color:#fff;border-bottom-right-radius:4px;}" +
      ".propbot-msg-assistant{align-self:flex-start;background:#f3f4f6;color:#1f2937;border-bottom-left-radius:4px;}" +
      ".propbot-typing{opacity:0.6;}" +
      "#propbot-input-area{display:flex;padding:12px;gap:8px;border-top:1px solid #e5e7eb;}" +
      "#propbot-input{flex:1;padding:10px 14px;border:1px solid #d1d5db;border-radius:20px;outline:none;font-size:14px;}" +
      "#propbot-input:focus{border-color:#2563eb;}" +
      "#propbot-send{width:40px;height:40px;border-radius:50%;background:#2563eb;color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}" +
      "#propbot-send:disabled{opacity:0.5;cursor:not-allowed;}"
    );
  }
})();
