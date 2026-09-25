/*! Docs2Chat website widget | AGPL-3.0 | https://github.com/tengotengo23/AI-Support-Chatbot-Knowledge-Base-Widget
 * Usage: <script src="https://YOUR-SERVER/widget.js" data-key="pk_..." async></script>
 * Optional attributes: data-lang="ka|en|ru", data-position="right|left", data-open="true"
 * JS API: window.Docs2Chat.open() / .close() / .toggle()
 */
(function () {
  "use strict";
  if (window.__docs2chatLoaded) return;
  window.__docs2chatLoaded = true;

  var script =
    document.currentScript ||
    (function () {
      var all = document.querySelectorAll("script[data-key]");
      return all[all.length - 1];
    })();
  if (!script) return;
  var KEY = script.getAttribute("data-key");
  if (!KEY) return;
  var BASE = (script.getAttribute("data-api") || new URL(script.src, location.href).origin).replace(/\/$/, "");
  var API = BASE + "/api/widget/" + encodeURIComponent(KEY);
  var SIDE = script.getAttribute("data-position") === "left" ? "left" : "right";
  var LANGS = ["ka", "en", "ru"];

  function store(key, value) {
    try {
      if (value === undefined) return window.localStorage.getItem(key);
      if (value === null) window.localStorage.removeItem(key);
      else window.localStorage.setItem(key, value);
    } catch (e) {
      /* storage blocked: the widget still works, just without memory */
    }
    return null;
  }

  function randomId() {
    var bytes = new Uint8Array(16);
    (window.crypto || window.msCrypto).getRandomValues(bytes);
    var hex = "";
    for (var i = 0; i < bytes.length; i++) hex += ("0" + bytes[i].toString(16)).slice(-2);
    return "v_" + hex;
  }

  var visitorId = store("d2c_vid");
  if (!visitorId || !/^[A-Za-z0-9_-]{16,64}$/.test(visitorId)) {
    visitorId = randomId();
    store("d2c_vid", visitorId);
  }
  var CONV_KEY = "d2c_conv_" + KEY;
  var LANG_KEY = "d2c_lang";

  var state = {
    cfg: null,
    lang: "ka",
    open: false,
    convId: parseInt(store(CONV_KEY) || "0", 10) || null,
    status: "bot",
    lastId: 0,
    seen: {},
    loadedHistory: false,
    busy: false,
    unread: 0,
    timer: null,
  };

  function api(method, path, body) {
    var opts = { method: method, headers: {} };
    if (body) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (res) {
      return res
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          if (!res.ok) {
            var err = new Error((data && data.detail) || "HTTP " + res.status);
            err.status = res.status;
            throw err;
          }
          return data;
        });
    });
  }

  function T(key) {
    var s = state.cfg.strings;
    return (s[state.lang] && s[state.lang][key]) || s.en[key] || key;
  }

  function pickLanguage(cfg) {
    var candidates = [
      store(LANG_KEY),
      script.getAttribute("data-lang"),
      document.documentElement.lang,
      navigator.language,
      cfg.default_language,
    ];
    for (var i = 0; i < candidates.length; i++) {
      var c = (candidates[i] || "").slice(0, 2).toLowerCase();
      if (LANGS.indexOf(c) >= 0) return c;
    }
    return "ka";
  }

  function textColorFor(hex) {
    var m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex || "");
    if (!m) return "#fff";
    var lum = (0.299 * parseInt(m[1], 16) + 0.587 * parseInt(m[2], 16) + 0.114 * parseInt(m[3], 16)) / 255;
    return lum > 0.62 ? "#111827" : "#ffffff";
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      for (var k in attrs) {
        if (!Object.prototype.hasOwnProperty.call(attrs, k)) continue;
        if (k === "class") node.className = attrs[k];
        else if (k === "text") node.textContent = attrs[k];
        else if (k.slice(0, 2) === "on") node.addEventListener(k.slice(2), attrs[k]);
        else node.setAttribute(k, attrs[k]);
      }
    }
    (children || []).forEach(function (c) {
      if (c) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  }

  /* Safe rich text: plain text nodes + clickable links, **bold** markers removed. No innerHTML. */
  function renderText(text) {
    var frag = document.createDocumentFragment();
    var clean = String(text || "").replace(/\*\*(.+?)\*\*/g, "$1");
    var re = /(https?:\/\/[^\s<>"')\]]+)/g;
    var last = 0;
    var m;
    while ((m = re.exec(clean))) {
      if (m.index > last) frag.appendChild(document.createTextNode(clean.slice(last, m.index)));
      frag.appendChild(el("a", { href: m[1], target: "_blank", rel: "noopener noreferrer nofollow", text: m[1] }));
      last = m.index + m[1].length;
    }
    if (last < clean.length) frag.appendChild(document.createTextNode(clean.slice(last)));
    return frag;
  }

  var ICON_CHAT =
    '<svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path fill="currentColor" d="M12 3C6.5 3 2 6.9 2 11.7c0 2.4 1.1 4.6 3 6.2L4.3 21.4c-.1.5.4.9.9.6l4-2.1c.9.2 1.8.3 2.8.3 5.5 0 10-3.9 10-8.6S17.5 3 12 3z"/></svg>';
  var ICON_CLOSE =
    '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M18.3 5.7a1 1 0 0 0-1.4 0L12 10.6 7.1 5.7a1 1 0 1 0-1.4 1.4l4.9 4.9-4.9 4.9a1 1 0 1 0 1.4 1.4l4.9-4.9 4.9 4.9a1 1 0 0 0 1.4-1.4L13.4 12l4.9-4.9a1 1 0 0 0 0-1.4z"/></svg>';
  var ICON_SEND =
    '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M3.4 20.4 21 12 3.4 3.6 3.4 10l12.6 2-12.6 2z"/></svg>';

  function css(color, fg) {
    return (
      ":host{all:initial}[hidden]{display:none!important}" +
      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans Georgian','Noto Sans',Arial,sans-serif}" +
      ".launcher{position:fixed;bottom:20px;" + SIDE + ":20px;width:60px;height:60px;border-radius:50%;border:0;cursor:pointer;" +
      "background:" + color + ";color:" + fg + ";box-shadow:0 8px 24px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;z-index:2147483000;transition:transform .15s}" +
      ".launcher:hover{transform:scale(1.06)}.launcher:focus-visible{outline:3px solid #93c5fd;outline-offset:2px}" +
      ".unread{position:absolute;top:-2px;right:-2px;min-width:20px;height:20px;border-radius:10px;background:#ef4444;color:#fff;font-size:12px;line-height:20px;text-align:center;padding:0 5px;font-weight:600}" +
      ".panel{position:fixed;bottom:92px;" + SIDE + ":20px;width:370px;max-width:calc(100vw - 24px);height:560px;max-height:calc(100vh - 110px);" +
      "background:#fff;color:#111827;border-radius:16px;box-shadow:0 16px 48px rgba(0,0,0,.22);display:flex;flex-direction:column;overflow:hidden;z-index:2147483001;font-size:14px}" +
      ".panel[hidden]{display:none}" +
      ".head{background:" + color + ";color:" + fg + ";padding:14px 14px 12px 16px;display:flex;align-items:center;gap:10px}" +
      ".head .t{flex:1;min-width:0}.head .n{font-weight:700;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.head .s{font-size:12px;opacity:.85;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" +
      ".langs{display:flex;gap:2px}.langs button{background:transparent;border:1px solid transparent;color:inherit;opacity:.7;font-size:11px;font-weight:700;padding:3px 5px;border-radius:6px;cursor:pointer}" +
      ".langs button.on{opacity:1;border-color:currentColor}" +
      ".x{background:transparent;border:0;color:inherit;cursor:pointer;padding:4px;border-radius:8px;display:flex}.x:hover{background:rgba(255,255,255,.15)}" +
      ".msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:#f9fafb}" +
      ".m{max-width:85%;padding:9px 12px;border-radius:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word;overflow-wrap:anywhere}" +
      ".m a{color:inherit;text-decoration:underline}" +
      ".m.user{align-self:flex-end;background:" + color + ";color:" + fg + ";border-bottom-right-radius:4px}" +
      ".m.assistant,.m.operator{align-self:flex-start;background:#fff;border:1px solid #e5e7eb;border-bottom-left-radius:4px}" +
      ".m.operator{border-color:" + color + "}" +
      ".m.pending{opacity:.6}" +
      ".label{font-size:11px;font-weight:700;color:" + color + ";margin-bottom:2px}" +
      ".src{margin-top:6px;font-size:12px;color:#6b7280}.src a{color:#374151}" +
      ".sys{align-self:center;text-align:center;font-size:12px;color:#4b5563;background:#eef2ff;border-radius:10px;padding:7px 10px;max-width:92%}" +
      ".typing{align-self:flex-start;background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:10px 12px;display:flex;gap:4px}" +
      ".typing i{width:6px;height:6px;border-radius:50%;background:#9ca3af;animation:b 1s infinite}.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}" +
      "@keyframes b{0%,60%,100%{transform:translateY(0);opacity:.5}30%{transform:translateY(-4px);opacity:1}}" +
      ".actions{display:flex;gap:6px;padding:8px 12px 0;flex-wrap:wrap;background:#fff}" +
      ".actions button{border:1px solid #d1d5db;background:#fff;color:#374151;border-radius:999px;padding:5px 10px;font-size:12px;cursor:pointer}" +
      ".actions button:hover{border-color:" + color + ";color:" + color + "}" +
      ".actions.hl button{border-color:" + color + ";color:" + color + ";font-weight:600}" +
      ".lead{padding:10px 12px;border-top:1px solid #e5e7eb;background:#fff;display:flex;flex-direction:column;gap:6px}.lead[hidden]{display:none}" +
      ".lead input,.lead textarea{width:100%;border:1px solid #d1d5db;border-radius:8px;padding:8px 10px;font-size:14px;color:#111827;background:#fff}" +
      ".lead textarea{resize:none;height:54px}" +
      ".lead .row{display:flex;gap:6px}.lead .row>*{flex:1}" +
      ".btn{background:" + color + ";color:" + fg + ";border:0;border-radius:8px;padding:9px 12px;font-weight:600;cursor:pointer;font-size:14px}.btn[disabled]{opacity:.6;cursor:default}" +
      ".btn.ghost{background:#f3f4f6;color:#374151}" +
      ".composer{display:flex;gap:8px;padding:10px 12px;border-top:1px solid #e5e7eb;background:#fff;align-items:flex-end}" +
      ".composer textarea{flex:1;border:1px solid #d1d5db;border-radius:10px;padding:9px 11px;font-size:14px;resize:none;max-height:110px;min-height:40px;line-height:1.4;color:#111827;background:#fff}" +
      ".composer textarea:focus,.lead input:focus,.lead textarea:focus{outline:2px solid " + color + ";outline-offset:-1px;border-color:transparent}" +
      ".send{width:40px;height:40px;border-radius:10px;border:0;background:" + color + ";color:" + fg + ";cursor:pointer;display:flex;align-items:center;justify-content:center;flex:none}.send[disabled]{opacity:.5;cursor:default}" +
      ".badge{text-align:center;font-size:11px;color:#9ca3af;padding:0 0 8px;background:#fff}.badge a{color:#6b7280;text-decoration:none;font-weight:600}" +
      "@media (max-width:480px){.panel{bottom:0;" + SIDE + ":0;width:100vw;max-width:100vw;height:100%;max-height:100%;border-radius:0}.launcher.hidden-mobile{display:none}}"
    );
  }

  var ui = {};

  function build(cfg) {
    var color = /^#[0-9a-f]{6}$/i.test(cfg.brand_color) ? cfg.brand_color : "#2563eb";
    var fg = textColorFor(color);
    var host = el("div", { id: "docs2chat-widget" });
    document.body.appendChild(host);
    var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
    root.appendChild(el("style", { text: css(color, fg) }));

    ui.launcher = el("button", { class: "launcher", type: "button", onclick: toggle });
    ui.launcher.innerHTML = ICON_CHAT;
    ui.unread = el("span", { class: "unread", hidden: "" });
    ui.launcher.appendChild(ui.unread);

    ui.title = el("div", { class: "n" });
    ui.subtitle = el("div", { class: "s" });
    ui.langs = el("div", { class: "langs" });
    LANGS.forEach(function (l) {
      ui.langs.appendChild(
        el("button", {
          type: "button",
          "data-l": l,
          text: l.toUpperCase(),
          onclick: function () {
            setLang(l);
          },
        })
      );
    });
    ui.close = el("button", { class: "x", type: "button", onclick: close });
    ui.close.innerHTML = ICON_CLOSE;

    ui.msgs = el("div", { class: "msgs", role: "log", "aria-live": "polite" });

    ui.btnHuman = el("button", { type: "button", onclick: requestHuman });
    ui.btnLead = el("button", { type: "button", onclick: showLead });
    ui.actions = el("div", { class: "actions" }, [ui.btnHuman, ui.btnLead]);

    ui.leadName = el("input", { type: "text", maxlength: "200", autocomplete: "name" });
    ui.leadPhone = el("input", { type: "tel", maxlength: "64", autocomplete: "tel" });
    ui.leadEmail = el("input", { type: "email", maxlength: "320", autocomplete: "email" });
    ui.leadNote = el("textarea", { maxlength: "2000" });
    ui.leadSubmit = el("button", { class: "btn", type: "submit" });
    ui.leadCancel = el("button", {
      class: "btn ghost",
      type: "button",
      onclick: function () {
        ui.lead.hidden = true;
      },
    });
    ui.lead = el("form", { class: "lead", hidden: "", onsubmit: submitLead }, [
      ui.leadName,
      el("div", { class: "row" }, [ui.leadPhone, ui.leadEmail]),
      ui.leadNote,
      el("div", { class: "row" }, [ui.leadCancel, ui.leadSubmit]),
    ]);

    ui.input = el("textarea", { rows: "1", maxlength: "2000" });
    ui.input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        sendMessage();
      }
    });
    ui.input.addEventListener("input", function () {
      ui.input.style.height = "auto";
      ui.input.style.height = Math.min(ui.input.scrollHeight, 110) + "px";
    });
    ui.send = el("button", { class: "send", type: "submit" });
    ui.send.innerHTML = ICON_SEND;
    var composer = el("form", {
      class: "composer",
      onsubmit: function (e) {
        e.preventDefault();
        sendMessage();
      },
    }, [ui.input, ui.send]);

    ui.badge = null;
    if (cfg.show_badge) {
      ui.badge = el("div", { class: "badge" });
    }

    ui.panel = el("div", { class: "panel", hidden: "", role: "dialog" }, [
      el("div", { class: "head" }, [el("div", { class: "t" }, [ui.title, ui.subtitle]), ui.langs, ui.close]),
      ui.msgs,
      ui.actions,
      ui.lead,
      composer,
      ui.badge,
    ]);
    ui.panel.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });

    root.appendChild(ui.panel);
    root.appendChild(ui.launcher);
    applyTexts();
  }

  function applyTexts() {
    var cfg = state.cfg;
    ui.title.textContent = cfg.bot_name;
    ui.subtitle.textContent = cfg.name;
    ui.launcher.setAttribute("aria-label", T("open_chat"));
    ui.close.setAttribute("aria-label", T("close"));
    ui.panel.setAttribute("aria-label", cfg.bot_name);
    ui.input.placeholder = T("placeholder");
    ui.send.setAttribute("aria-label", T("send"));
    ui.btnHuman.textContent = "🙋 " + T("talk_to_human");
    ui.btnLead.textContent = "📇 " + T("leave_contact");
    ui.leadName.placeholder = T("name");
    ui.leadPhone.placeholder = T("phone");
    ui.leadEmail.placeholder = T("email");
    ui.leadNote.placeholder = T("note");
    ui.leadSubmit.textContent = T("submit");
    ui.leadCancel.textContent = T("close");
    Array.prototype.forEach.call(ui.langs.children, function (b) {
      b.className = b.getAttribute("data-l") === state.lang ? "on" : "";
    });
    if (ui.badge) {
      ui.badge.textContent = "";
      ui.badge.appendChild(document.createTextNode(T("powered_by") + " "));
      ui.badge.appendChild(el("a", { href: cfg.badge_url, target: "_blank", rel: "noopener", text: cfg.badge_text }));
    }
    if (ui.welcome) ui.welcome.textContent = T("welcome");
    updateActions();
  }

  function updateActions() {
    var cfg = state.cfg;
    ui.btnHuman.hidden = !cfg.handoff_enabled || !state.convId || state.status === "handoff";
    ui.btnLead.hidden = !cfg.lead_capture_enabled;
    ui.actions.hidden = ui.btnHuman.hidden && ui.btnLead.hidden;
  }

  function setLang(lang) {
    state.lang = lang;
    store(LANG_KEY, lang);
    applyTexts();
  }

  function scrollDown() {
    ui.msgs.scrollTop = ui.msgs.scrollHeight;
  }

  function addMessage(m) {
    if (m.id && state.seen[m.id]) return;
    if (m.id) {
      state.seen[m.id] = true;
      state.lastId = Math.max(state.lastId, m.id);
    }
    var node;
    if (m.role === "system") {
      node = el("div", { class: "sys" }, [renderText(m.content)]);
    } else {
      node = el("div", { class: "m " + m.role });
      if (m.role === "operator") node.appendChild(el("div", { class: "label", text: T("operator") }));
      node.appendChild(renderText(m.content));
      if (m.sources && m.sources.length) {
        var src = el("div", { class: "src" }, [T("sources") + ": "]);
        m.sources.forEach(function (s, i) {
          if (i) src.appendChild(document.createTextNode(", "));
          if (s.url && /^https?:\/\//.test(s.url)) {
            src.appendChild(el("a", { href: s.url, target: "_blank", rel: "noopener noreferrer nofollow", text: s.title || s.url }));
          } else {
            src.appendChild(document.createTextNode(s.title || ""));
          }
        });
        node.appendChild(src);
      }
    }
    ui.msgs.appendChild(node);
    if (!state.open && (m.role === "operator" || m.role === "assistant")) {
      state.unread += 1;
      ui.unread.textContent = String(state.unread);
      ui.unread.hidden = false;
    }
    scrollDown();
    return node;
  }

  function showTyping(on) {
    if (on && !ui.typing) {
      ui.typing = el("div", { class: "typing" }, [el("i"), el("i"), el("i")]);
      ui.msgs.appendChild(ui.typing);
      scrollDown();
    } else if (!on && ui.typing) {
      ui.typing.remove();
      ui.typing = null;
    }
  }

  function showSystem(text) {
    addMessage({ role: "system", content: text });
  }

  function setConversation(id) {
    state.convId = id;
    store(CONV_KEY, id ? String(id) : null);
    updateActions();
  }

  function setStatus(status) {
    if (status && status !== state.status) {
      state.status = status;
      updateActions();
    }
    schedulePoll();
  }

  function loadHistory() {
    if (state.loadedHistory || !state.convId) return Promise.resolve();
    state.loadedHistory = true;
    return api("GET", "/conversations/" + state.convId + "?visitor_id=" + visitorId + "&after=0")
      .then(function (data) {
        data.messages.forEach(function (m) {
          addMessage(m);
        });
        state.unread = 0;
        ui.unread.hidden = true;
        setStatus(data.status);
      })
      .catch(function (err) {
        if (err.status === 404) setConversation(null);
      });
  }

  function poll() {
    if (!state.convId) return;
    api("GET", "/conversations/" + state.convId + "?visitor_id=" + visitorId + "&after=" + state.lastId)
      .then(function (data) {
        data.messages.forEach(function (m) {
          addMessage(m);
        });
        setStatus(data.status);
      })
      .catch(function (err) {
        if (err.status === 404) setConversation(null);
        else schedulePoll();
      });
  }

  function schedulePoll() {
    clearTimeout(state.timer);
    if (!state.convId) return;
    var delay = state.status === "handoff" ? (state.open ? 3000 : 10000) : state.open ? 15000 : 0;
    if (delay && !document.hidden) state.timer = setTimeout(poll, delay);
  }

  function sendMessage() {
    var text = ui.input.value.trim();
    if (!text || state.busy) return;
    state.busy = true;
    ui.send.disabled = true;
    ui.input.value = "";
    ui.input.style.height = "auto";
    var pending = addMessage({ role: "user", content: text });
    pending.classList.add("pending");
    if (state.status !== "handoff") showTyping(true);
    api("POST", "/messages", {
      visitor_id: visitorId,
      conversation_id: state.convId,
      text: text,
      lang: state.lang,
      page_url: location.href.slice(0, 1000),
    })
      .then(function (data) {
        pending.remove();
        showTyping(false);
        if (data.conversation_id !== state.convId) setConversation(data.conversation_id);
        data.messages.forEach(function (m) {
          addMessage(m);
        });
        if (data.suggest_handoff || data.quota_exceeded) {
          ui.actions.className = "actions hl";
        } else {
          ui.actions.className = "actions";
        }
        if (data.quota_exceeded && state.cfg.lead_capture_enabled) showLead();
        setStatus(data.status);
      })
      .catch(function (err) {
        pending.classList.remove("pending");
        showTyping(false);
        showSystem(err.status === 429 ? err.message : T("error"));
      })
      .then(function () {
        state.busy = false;
        ui.send.disabled = false;
        ui.input.focus();
      });
  }

  function requestHuman() {
    if (!state.convId) return;
    ui.btnHuman.disabled = true;
    api("POST", "/handoff", { visitor_id: visitorId, conversation_id: state.convId, lang: state.lang })
      .then(function (data) {
        data.messages.forEach(function (m) {
          addMessage(m);
        });
        if (!data.available && state.cfg.lead_capture_enabled) showLead();
        setStatus(data.status);
      })
      .catch(function () {
        showSystem(T("error"));
      })
      .then(function () {
        ui.btnHuman.disabled = false;
      });
  }

  function showLead() {
    ui.lead.hidden = false;
    ui.leadName.focus();
  }

  function submitLead(e) {
    e.preventDefault();
    var phone = ui.leadPhone.value.trim();
    var email = ui.leadEmail.value.trim();
    if (!phone && !email) {
      ui.leadPhone.focus();
      showSystem(T("lead_invalid"));
      return;
    }
    ui.leadSubmit.disabled = true;
    api("POST", "/leads", {
      visitor_id: visitorId,
      conversation_id: state.convId,
      lang: state.lang,
      name: ui.leadName.value.trim(),
      phone: phone,
      email: email,
      note: ui.leadNote.value.trim(),
    })
      .then(function (data) {
        ui.lead.hidden = true;
        ui.lead.reset();
        if (data.messages && data.messages.length) {
          data.messages.forEach(function (m) {
            addMessage(m);
          });
        } else {
          showSystem(T("lead_thanks"));
        }
      })
      .catch(function (err) {
        showSystem(err.status === 400 ? err.message : T("error"));
      })
      .then(function () {
        ui.leadSubmit.disabled = false;
      });
  }

  function open() {
    if (!state.cfg) return;
    state.open = true;
    ui.panel.hidden = false;
    ui.launcher.classList.add("hidden-mobile");
    state.unread = 0;
    ui.unread.hidden = true;
    loadHistory().then(function () {
      if (!ui.welcome) {
        ui.welcome = el("div", { class: "m assistant", text: T("welcome") });
        ui.msgs.insertBefore(ui.welcome, ui.msgs.firstChild);
      }
      scrollDown();
      schedulePoll();
    });
    setTimeout(function () {
      ui.input.focus();
    }, 50);
  }

  function close() {
    state.open = false;
    ui.panel.hidden = true;
    ui.launcher.classList.remove("hidden-mobile");
    schedulePoll();
  }

  function toggle() {
    if (state.open) close();
    else open();
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) schedulePoll();
  });

  window.Docs2Chat = { open: open, close: close, toggle: toggle };

  function init() {
    api("GET", "/config")
      .then(function (cfg) {
        state.cfg = cfg;
        state.lang = pickLanguage(cfg);
        build(cfg);
        if (state.convId) {
          // Resume an existing chat (e.g. waiting for an operator reply) in the background.
          loadHistory().then(schedulePoll);
        }
        if (script.getAttribute("data-open") === "true") open();
      })
      .catch(function (err) {
        if (window.console) console.warn("[Docs2Chat] widget disabled:", err.message);
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
