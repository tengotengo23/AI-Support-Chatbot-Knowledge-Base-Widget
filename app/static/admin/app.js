/* Admin dashboard — plain JavaScript, no build step. All user data is inserted as text nodes. */
(function () {
  "use strict";

  // ------------------------------------------------------------------ i18n
  var I18N = {
    en: {
      nav_dashboard: "Dashboard", nav_knowledge: "Knowledge base", nav_inbox: "Inbox", nav_leads: "Leads",
      nav_settings: "Settings", nav_install: "Install", nav_billing: "Plan & billing", nav_platform: "Platform",
      logout: "Log out", new_workspace: "+ New chatbot", new_workspace_prompt: "Name of the business / website:",
      login_title: "Log in", signup_title: "Create your account", email: "Email", password: "Password",
      password_hint: "At least 8 characters", business_name: "Business name", login_btn: "Log in",
      signup_btn: "Create account", no_account: "No account yet?", have_account: "Already have an account?",
      signup_closed: "Sign-up is closed on this server.",
      last_30: "Last 30 days", t_conversations: "Conversations", t_questions: "Questions",
      t_answer_rate: "Answered by AI", t_unanswered: "Unanswered", t_leads: "Leads", t_human: "Human chats",
      chart_title: "Conversations per day", show_table: "Show as table", date: "Date",
      top_questions: "Most asked questions", unanswered_title: "Questions the AI could not answer",
      unanswered_hint: "Add an answer and the bot will know it next time.", add_answer: "Add answer",
      answer: "Answer", save: "Save", saved: "Saved", cancel: "Cancel", nothing_yet: "Nothing here yet.",
      getting_started: "Getting started", step_knowledge: "Add your FAQ, website or PDF",
      step_telegram: "Connect Telegram for human handoff", step_install: "Put the widget on your website",
      llm_off_notice:
        "No AI provider is configured (LLM_PROVIDER=none), so the bot replies with the best matching FAQ or text snippet. Set ANTHROPIC_API_KEY or OPENAI_API_KEY on the server for natural answers.",
      kb_sub: "The bot answers only from what you add here.", tab_faq: "FAQ", tab_url: "Website", tab_pdf: "PDF",
      tab_text: "Text", question: "Question", add: "Add", url: "Page URL",
      crawl: "Also import other pages of this website", max_pages: "Max pages", import: "Import",
      working: "Working…", pdf_file: "PDF file", upload: "Upload", title: "Title", content: "Content",
      text_hint: "Prices, working hours, delivery, return policy, contacts…", documents: "Sources", kind: "Type",
      size: "Size", refresh: "Refresh", delete: "Delete", confirm_delete: "Delete this item?",
      test_title: "Test your bot", test_placeholder: "Ask something a customer would ask…", ask: "Ask",
      answered: "answered", not_answered: "no answer",
      filter_all: "All", filter_handoff: "Needs a human", select_conv: "Select a conversation",
      reply_placeholder: "Write a reply to the visitor…", send: "Send", hand_back: "Hand back to AI",
      status_bot: "AI", status_handoff: "Human", role_user: "Visitor", role_assistant: "AI", role_operator: "You",
      lead_info: "Contact left", export_csv: "Export CSV", name: "Name", phone: "Phone", note: "Note",
      status: "Status", value: "Order value", chat: "Chat", st_new: "New", st_contacted: "Contacted",
      st_won: "Won (order)", st_lost: "Lost",
      s_bot: "Chatbot", ws_name: "Business / website name", bot_name: "Bot name", welcome: "Welcome message",
      welcome_hint: "Leave empty to use the default greeting in the visitor's language.",
      company_info: "About the business (always given to the AI)",
      company_info_hint: "Short description, address, phone, working hours, tone of voice…",
      brand_color: "Brand color", default_lang: "Default language",
      lead_capture: "Show the “Leave your contact” form", handoff: "Allow “Talk to a human”",
      origins: "Allowed websites (optional)",
      origins_hint: "One per line, e.g. https://myshop.ge — leave empty to allow any website.",
      tg_title: "Telegram handoff",
      tg_unavailable:
        "Telegram is not configured on this server. Create a bot with @BotFather and set TELEGRAM_BOT_TOKEN.",
      tg_connected: "Connected. Chats that need a human arrive in your Telegram — reply to the message to answer.",
      tg_connect: "Connect Telegram", tg_steps: "Open the link, press Start in Telegram, then come back and refresh.",
      tg_manual: "Or send this message to the bot:", tg_test: "Send test message", tg_disconnect: "Disconnect",
      tg_check: "I've connected — refresh", danger: "Danger zone", rotate_key: "Regenerate widget key",
      rotate_confirm: "The old embed code will stop working. Continue?", delete_ws: "Delete this chatbot",
      delete_ws_confirm: "Type the chatbot name to confirm deletion:",
      install_step1: "1. Copy this code", install_step2: "2. Paste it before </body> on every page of your website",
      copy: "Copy", copied: "Copied", preview: "Open preview", platforms: "Where to paste it",
      p_wp: "WordPress: install the “WPCode” plugin → Code Snippets → Header & Footer → Footer.",
      p_shopify: "Shopify: Online Store → Themes → Edit code → theme.liquid, right before </body>.",
      p_wix: "Wix: Settings → Custom code → Add code → Body – end.",
      p_tilda: "Tilda: Site settings → More → HTML code for the HEAD section (or a T123 block).",
      p_html: "Any HTML site: paste right before </body>.", js_api: "Open the chat from your own button:",
      selfhosted_notice: "This is a self-hosted install: everything is free and unlimited.",
      current_plan: "Current plan", ai_answers: "AI answers this month", sources_used: "Knowledge sources",
      unlimited: "unlimited", per_month: "/month", upgrade: "Choose", current: "Current plan",
      manage_payment: "Update payment method", cancel_sub: "Cancel subscription", paid_until: "Paid until",
      pay_invoice: "Want to pay by bank transfer / invoice? Contact the platform owner.",
      payment_done: "Payment received! Your plan will update in a few seconds.",
      fee_title: "Platform fee (transparent)",
      fee_text: "{p}% of confirmed orders (leads marked “Won”) is billed monthly. Last 30 days: orders {v} → fee {f}.",
      mrr: "MRR (USD)", customers: "Chatbots", paying: "Paying", owner: "Owner", plan: "Plan", expires: "Expires",
      set_plan: "Set", create_first: "Create your first chatbot", create: "Create", open_site: "Open",
    },
    ka: {
      nav_dashboard: "მთავარი", nav_knowledge: "ცოდნის ბაზა", nav_inbox: "ჩატები", nav_leads: "კონტაქტები",
      nav_settings: "პარამეტრები", nav_install: "საიტზე დაყენება", nav_billing: "პაკეტი და გადახდა",
      nav_platform: "პლატფორმა", logout: "გასვლა", new_workspace: "+ ახალი ჩატბოტი",
      new_workspace_prompt: "ბიზნესის ან საიტის სახელი:", login_title: "შესვლა",
      signup_title: "ანგარიშის შექმნა", email: "ელ-ფოსტა", password: "პაროლი", password_hint: "მინიმუმ 8 სიმბოლო",
      business_name: "ბიზნესის სახელი", login_btn: "შესვლა", signup_btn: "რეგისტრაცია",
      no_account: "ჯერ არ გაქვთ ანგარიში?", have_account: "უკვე გაქვთ ანგარიში?",
      signup_closed: "რეგისტრაცია ამ სერვერზე დახურულია.",
      last_30: "ბოლო 30 დღე", t_conversations: "საუბრები", t_questions: "კითხვები", t_answer_rate: "AI-მ უპასუხა",
      t_unanswered: "უპასუხო", t_leads: "კონტაქტები", t_human: "ოპერატორთან", chart_title: "საუბრები დღეების მიხედვით",
      show_table: "ცხრილად ნახვა", date: "თარიღი", top_questions: "ყველაზე ხშირი კითხვები",
      unanswered_title: "კითხვები, რომლებზეც AI-მ ვერ უპასუხა",
      unanswered_hint: "დაამატეთ პასუხი და ბოტმა შემდეგ ჯერზე ეცოდინება.", add_answer: "პასუხის დამატება",
      answer: "პასუხი", save: "შენახვა", saved: "შენახულია", cancel: "გაუქმება", nothing_yet: "ჯერ ცარიელია.",
      getting_started: "დაწყება", step_knowledge: "დაამატეთ FAQ, საიტი ან PDF",
      step_telegram: "დააკავშირეთ Telegram ოპერატორისთვის", step_install: "ჩასვით ვიჯეტი თქვენს საიტზე",
      llm_off_notice:
        "AI პროვაიდერი არ არის დაყენებული (LLM_PROVIDER=none), ამიტომ ბოტი პასუხობს ყველაზე შესაბამისი FAQ-ით ან ტექსტის ნაწყვეტით. ბუნებრივი პასუხებისთვის სერვერზე მიუთითეთ ANTHROPIC_API_KEY ან OPENAI_API_KEY.",
      kb_sub: "ბოტი პასუხობს მხოლოდ იმის მიხედვით, რასაც აქ დაამატებთ.", tab_faq: "კითხვა-პასუხი",
      tab_url: "ვებსაიტი", tab_pdf: "PDF", tab_text: "ტექსტი", question: "კითხვა", add: "დამატება",
      url: "გვერდის მისამართი", crawl: "საიტის სხვა გვერდებიც დაიმპორტდეს", max_pages: "მაქს. გვერდები",
      import: "იმპორტი", working: "მიმდინარეობს…", pdf_file: "PDF ფაილი", upload: "ატვირთვა", title: "სათაური",
      content: "შინაარსი", text_hint: "ფასები, სამუშაო საათები, მიწოდება, დაბრუნების პირობები, კონტაქტები…",
      documents: "წყაროები", kind: "ტიპი", size: "ზომა", refresh: "განახლება", delete: "წაშლა",
      confirm_delete: "წავშალოთ?", test_title: "გამოცადეთ ბოტი",
      test_placeholder: "დაწერეთ კითხვა ისე, როგორც მომხმარებელი დაწერდა…", ask: "კითხვა",
      answered: "უპასუხა", not_answered: "ვერ უპასუხა", filter_all: "ყველა", filter_handoff: "ელოდება ოპერატორს",
      select_conv: "აირჩიეთ საუბარი", reply_placeholder: "დაწერეთ პასუხი მომხმარებელს…", send: "გაგზავნა",
      hand_back: "AI-ს დაბრუნება", status_bot: "AI", status_handoff: "ოპერატორი", role_user: "მომხმარებელი",
      role_assistant: "AI", role_operator: "თქვენ", lead_info: "დატოვებული კონტაქტი", export_csv: "CSV ექსპორტი",
      name: "სახელი", phone: "ტელეფონი", note: "შენიშვნა", status: "სტატუსი", value: "შეკვეთის თანხა",
      chat: "ჩატი", st_new: "ახალი", st_contacted: "დაკავშირებული", st_won: "შეკვეთა ✓", st_lost: "დაკარგული",
      s_bot: "ჩატბოტი", ws_name: "ბიზნესის / საიტის სახელი", bot_name: "ბოტის სახელი", welcome: "მისალმების ტექსტი",
      welcome_hint: "თუ ცარიელია, გამოჩნდება სტანდარტული მისალმება ვიზიტორის ენაზე.",
      company_info: "ბიზნესის შესახებ (AI-ს ყოველთვის აქვს)",
      company_info_hint: "მოკლე აღწერა, მისამართი, ტელეფონი, სამუშაო საათები, საუბრის სტილი…",
      brand_color: "ფერი", default_lang: "ძირითადი ენა", lead_capture: "„კონტაქტის დატოვების“ ფორმა",
      handoff: "„ოპერატორთან დაკავშირების“ ღილაკი", origins: "დაშვებული საიტები (არასავალდებულო)",
      origins_hint: "თითო ხაზზე ერთი, მაგ. https://myshop.ge — ცარიელი ნიშნავს ნებისმიერ საიტს.",
      tg_title: "Telegram ოპერატორი",
      tg_unavailable:
        "Telegram ამ სერვერზე არ არის ჩართული. შექმენით ბოტი @BotFather-ით და მიუთითეთ TELEGRAM_BOT_TOKEN.",
      tg_connected:
        "დაკავშირებულია. ჩატები, რომლებსაც ოპერატორი სჭირდება, მოვა Telegram-ში — საპასუხოდ შეტყობინებას Reply გაუკეთეთ.",
      tg_connect: "Telegram-ის დაკავშირება",
      tg_steps: "გახსენით ბმული, Telegram-ში დააჭირეთ Start-ს, შემდეგ დაბრუნდით და განაახლეთ.",
      tg_manual: "ან გაუგზავნეთ ბოტს ეს ტექსტი:", tg_test: "სატესტო შეტყობინება", tg_disconnect: "გათიშვა",
      tg_check: "დავაკავშირე — განახლება", danger: "საშიში ზონა", rotate_key: "ვიჯეტის გასაღების შეცვლა",
      rotate_confirm: "ძველი კოდი აღარ იმუშავებს. გავაგრძელოთ?", delete_ws: "ჩატბოტის წაშლა",
      delete_ws_confirm: "წასაშლელად ჩაწერეთ ჩატბოტის სახელი:", install_step1: "1. დააკოპირეთ ეს კოდი",
      install_step2: "2. ჩასვით </body>-მდე საიტის ყველა გვერდზე", copy: "კოპირება", copied: "დაკოპირდა",
      preview: "გადახედვა", platforms: "სად ჩავსვა",
      p_wp: "WordPress: დააყენეთ „WPCode“ plugin → Code Snippets → Header & Footer → Footer.",
      p_shopify: "Shopify: Online Store → Themes → Edit code → theme.liquid, </body>-მდე.",
      p_wix: "Wix: Settings → Custom code → Add code → Body – end.",
      p_tilda: "Tilda: Site settings → More → HTML code for the HEAD section (ან T123 ბლოკი).",
      p_html: "ნებისმიერი HTML საიტი: ჩასვით </body>-მდე.", js_api: "ჩატის გახსნა თქვენივე ღილაკიდან:",
      selfhosted_notice: "ეს არის self-hosted ინსტალაცია: ყველაფერი უფასო და შეუზღუდავია.",
      current_plan: "მიმდინარე პაკეტი", ai_answers: "AI პასუხები ამ თვეში", sources_used: "ცოდნის წყაროები",
      unlimited: "შეუზღუდავი", per_month: "/თვე", upgrade: "არჩევა", current: "მიმდინარე პაკეტი",
      manage_payment: "ბარათის შეცვლა", cancel_sub: "გამოწერის გაუქმება", paid_until: "გადახდილია",
      pay_invoice: "გსურთ ბანკით / ინვოისით გადახდა? დაუკავშირდით პლატფორმის მფლობელს.",
      payment_done: "გადახდა მიღებულია! პაკეტი რამდენიმე წამში განახლდება.",
      fee_title: "პლატფორმის საკომისიო (გამჭვირვალე)",
      fee_text:
        "დადასტურებული შეკვეთების (სტატუსი „შეკვეთა ✓“) {p}% ერიცხება ყოველთვიურად. ბოლო 30 დღე: შეკვეთები {v} → საკომისიო {f}.",
      mrr: "თვიური შემოსავალი (USD)", customers: "ჩატბოტები", paying: "ფასიანი", owner: "მფლობელი",
      plan: "პაკეტი", expires: "ვადა", set_plan: "დაყენება", create_first: "შექმენით პირველი ჩატბოტი",
      create: "შექმნა", open_site: "გახსნა",
    },
  };

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (e) { /* ignore */ }
    return null;
  }

  var lang = store("d2c_admin_lang") || ((navigator.language || "").slice(0, 2) === "ka" ? "ka" : "en");
  function tr(key, vars) {
    var s = (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  }

  // ------------------------------------------------------------------ DOM helpers
  function h(tag, props) {
    var node = document.createElement(tag);
    props = props || {};
    Object.keys(props).forEach(function (k) {
      var v = props[k];
      if (v === undefined || v === null || v === false) return;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k === "style") Object.assign(node.style, v);
      else if (k.slice(0, 2) === "on") node.addEventListener(k.slice(2).toLowerCase(), v);
      else if (k === "value") node.value = v;
      else if (k === "checked") node.checked = !!v;
      else node.setAttribute(k, v === true ? "" : v);
    });
    for (var i = 2; i < arguments.length; i++) append(node, arguments[i]);
    return node;
  }
  function append(node, child) {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) return child.forEach(function (c) { append(node, c); });
    node.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return "";
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }
  function fmtNum(n) { return Number(n || 0).toLocaleString(); }

  var toastTimer;
  function toast(msg, isErr) {
    var old = document.querySelector(".toast");
    if (old) old.remove();
    var t = h("div", { class: "toast" + (isErr ? " err" : ""), role: "status", text: msg });
    document.body.appendChild(t);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.remove(); }, isErr ? 6000 : 2500);
  }

  // ------------------------------------------------------------------ API
  function errorText(data, res) {
    if (data && typeof data.detail === "string") return data.detail;
    if (data && Array.isArray(data.detail)) {
      return data.detail.map(function (d) { return (d.loc ? d.loc[d.loc.length - 1] + ": " : "") + d.msg; }).join("; ");
    }
    return res.status + " " + res.statusText;
  }
  function api(method, path, body, opts) {
    opts = opts || {};
    var init = { method: method, credentials: "same-origin", headers: { "X-Requested-With": "fetch" } };
    if (body instanceof FormData) init.body = body;
    else if (body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    return fetch(path, init).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (res.status === 401 && !opts.allow401) {
          state.me = null;
          go("#/login");
        }
        if (!res.ok) {
          var err = new Error(errorText(data, res));
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }
  function run(button, promise) {
    if (button) button.disabled = true;
    return promise
      .catch(function (err) { if (err.status !== 401) toast(err.message, true); throw err; })
      .finally(function () { if (button) button.disabled = false; });
  }

  // ------------------------------------------------------------------ state & routing
  var state = { me: null, ws: null, timers: [] };
  var app = document.getElementById("app");

  function go(hash) {
    if (location.hash === hash) route();
    else location.hash = hash;
  }
  function wsPath(suffix) { return "/api/workspaces/" + state.ws.id + (suffix || ""); }
  function every(ms, fn) { state.timers.push(setInterval(fn, ms)); }

  function route() {
    state.timers.forEach(clearInterval);
    state.timers = [];
    var parts = (location.hash || "#/dashboard").slice(2).split("/");
    var page = parts[0] || "dashboard";
    var arg = parts[1];
    document.documentElement.lang = lang;
    if (page === "login" || page === "signup") return renderAuth(page);

    var ready = state.me
      ? Promise.resolve(state.me)
      : api("GET", "/api/auth/me", undefined, { allow401: true }).then(function (me) { state.me = me; return me; });
    ready
      .then(function (me) {
        document.title = me.brand_name + " · Admin";
        if (!me.workspaces.length) return renderCreateFirst();
        var wanted = parseInt(store("d2c_ws") || "0", 10);
        var ws = me.workspaces.filter(function (w) { return w.id === wanted; })[0] || me.workspaces[0];
        return api("GET", "/api/workspaces/" + ws.id).then(function (full) {
          state.ws = full;
          store("d2c_ws", String(full.id));
          var main = renderLayout(page);
          var pages = {
            dashboard: pageDashboard, knowledge: pageKnowledge, inbox: pageInbox, leads: pageLeads,
            settings: pageSettings, install: pageInstall, billing: pageBilling, platform: pagePlatform,
          };
          return (pages[page] || pageDashboard)(main, arg);
        });
      })
      .catch(function (err) {
        if (err && err.status === 401) return go("#/login");
        clear(app).appendChild(h("div", { class: "boot" }, "⚠️ " + (err && err.message)));
      });
  }
  window.addEventListener("hashchange", route);

  function reloadMe() {
    return api("GET", "/api/auth/me").then(function (me) { state.me = me; });
  }

  // ------------------------------------------------------------------ auth pages
  function renderAuth(mode) {
    clear(app);
    api("GET", "/api/auth/status", undefined, { allow401: true }).then(function (st) {
      document.title = st.brand_name + " · " + tr(mode === "login" ? "login_title" : "signup_title");
      if (mode === "login" && !st.has_users) return go("#/signup");
      var email = h("input", { type: "email", required: true, autocomplete: "email" });
      var password = h("input", { type: "password", required: true, minlength: mode === "signup" ? "8" : null,
        autocomplete: mode === "signup" ? "new-password" : "current-password" });
      var bizName = h("input", { type: "text", required: true, maxlength: "200" });
      var submit = h("button", { class: "btn", type: "submit", style: { width: "100%" },
        text: tr(mode === "login" ? "login_btn" : "signup_btn") });
      var form = h("form", {
        onsubmit: function (e) {
          e.preventDefault();
          var body = { email: email.value, password: password.value };
          if (mode === "signup") body.workspace_name = bizName.value;
          run(submit, api("POST", "/api/auth/" + mode, body)).then(function () {
            state.me = null;
            go(mode === "signup" ? "#/knowledge" : "#/dashboard");
          });
        },
      },
        h("label", { class: "f" }, tr("email"), email),
        h("label", { class: "f" }, tr("password"), password,
          mode === "signup" ? h("span", { class: "hint", text: tr("password_hint") }) : null),
        mode === "signup" ? h("label", { class: "f" }, tr("business_name"), bizName) : null,
        submit
      );
      var closed = mode === "signup" && !st.signup_enabled;
      clear(app).appendChild(
        h("div", { class: "auth" },
          h("div", { class: "brand", style: { textAlign: "center", marginBottom: "12px" }, text: st.brand_name }),
          h("div", { class: "card" },
            h("h1", { text: tr(mode === "login" ? "login_title" : "signup_title") }),
            closed ? h("p", { class: "notice warn", text: tr("signup_closed") }) : form,
            h("p", { class: "small muted", style: { marginTop: "14px" } },
              mode === "login" ? tr("no_account") + " " : tr("have_account") + " ",
              h("a", { href: mode === "login" ? "#/signup" : "#/login",
                text: tr(mode === "login" ? "signup_btn" : "login_btn") }))
          ),
          langSwitch()
        )
      );
      email.focus();
    });
  }

  function langSwitch() {
    return h("div", { class: "row small", style: { justifyContent: "center", marginTop: "10px" } },
      ["en", "ka"].map(function (l) {
        return h("button", { class: "btn link sm", style: { fontWeight: l === lang ? "800" : "400" },
          text: l === "en" ? "English" : "ქართული",
          onclick: function () { lang = l; store("d2c_admin_lang", l); route(); } });
      }));
  }

  function renderCreateFirst() {
    var name = h("input", { type: "text", required: true, maxlength: "200" });
    var btn = h("button", { class: "btn", type: "submit", text: tr("create") });
    clear(app).appendChild(h("div", { class: "auth" }, h("div", { class: "card" },
      h("h1", { text: tr("create_first") }),
      h("form", { onsubmit: function (e) {
        e.preventDefault();
        run(btn, api("POST", "/api/workspaces", { name: name.value })).then(function (ws) {
          store("d2c_ws", String(ws.id));
          state.me = null;
          go("#/knowledge");
        });
      } }, h("label", { class: "f" }, tr("business_name"), name), btn))));
  }

  // ------------------------------------------------------------------ layout
  function renderLayout(page) {
    var me = state.me;
    var ws = state.ws;
    var nav = [
      ["dashboard", "📊"], ["knowledge", "📚"], ["inbox", "💬"], ["leads", "📇"], ["settings", "⚙️"],
      ["install", "🧩"], ["billing", "💳"],
    ];
    if (me.is_superadmin && me.billing_enabled) nav.push(["platform", "🏢"]);

    var select = h("select", { "aria-label": "Chatbot", onchange: function () {
      if (select.value === "__new") {
        var name = window.prompt(tr("new_workspace_prompt"));
        if (!name) { select.value = String(ws.id); return; }
        api("POST", "/api/workspaces", { name: name }).then(function (created) {
          store("d2c_ws", String(created.id));
          state.me = null;
          go("#/knowledge");
        }).catch(function (err) { toast(err.message, true); });
        return;
      }
      store("d2c_ws", select.value);
      route();
    } },
      me.workspaces.map(function (w) { return h("option", { value: String(w.id), text: w.name }); }),
      h("option", { value: "__new", text: tr("new_workspace") }));
    select.value = String(ws.id);

    var side = h("aside", { class: "side" },
      h("div", { class: "brand", text: me.brand_name }),
      select,
      h("nav", { class: "nav" }, nav.map(function (n) {
        return h("a", { href: "#/" + n[0], class: page === n[0] ? "on" : "" },
          h("span", { "aria-hidden": "true", text: n[1] }), tr("nav_" + n[0]),
          n[0] === "inbox" && ws.open_handoffs ? h("span", { class: "count", text: String(ws.open_handoffs) }) : null);
      })),
      h("div", { class: "side-foot" },
        h("div", { class: "muted", text: me.email }),
        h("div", { class: "row" },
          h("button", { class: "btn link sm", text: lang === "en" ? "ქართული" : "English", onclick: function () {
            lang = lang === "en" ? "ka" : "en";
            store("d2c_admin_lang", lang);
            route();
          } }),
          h("button", { class: "btn link sm", text: tr("logout"), onclick: function () {
            api("POST", "/api/auth/logout").then(function () { state.me = null; go("#/login"); });
          } })))
    );
    var main = h("main", { class: "main" });
    var top = h("div", { class: "mobile-top" },
      h("button", { class: "btn secondary sm", text: "☰", "aria-label": "Menu",
        onclick: function () { side.classList.toggle("open"); } }),
      h("strong", { text: ws.name }));
    main.addEventListener("click", function () { side.classList.remove("open"); });
    clear(app).appendChild(h("div", { class: "layout" }, side, h("div", {}, top, main)));
    return main;
  }

  function pageHead(main, title, sub, actions) {
    main.appendChild(h("div", { class: "page-head" },
      h("div", {}, h("h1", { text: title }), sub ? h("div", { class: "muted", text: sub }) : null),
      actions ? h("div", { class: "row" }, actions) : null));
  }

  // ------------------------------------------------------------------ dashboard
  function barChart(daily) {
    var W = 900, H = 200, left = 34, bottom = 22, top = 8;
    var plotW = W - left - 4, plotH = H - bottom - top;
    var max = Math.max.apply(null, daily.map(function (d) { return d.conversations; }).concat([1]));
    var niceMax = max <= 5 ? 5 : Math.ceil(max / 5) * 5;
    var slot = plotW / daily.length;
    var bw = Math.min(24, Math.max(2, slot - 2));
    var NS = "http://www.w3.org/2000/svg";
    function s(tag, attrs, text) {
      var n = document.createElementNS(NS, tag);
      Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
      if (text !== undefined) n.textContent = text;
      return n;
    }
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": tr("chart_title") });
    [0, niceMax / 2, niceMax].forEach(function (v) {
      var y = top + plotH - (v / niceMax) * plotH;
      svg.appendChild(s("line", { x1: left, x2: W - 4, y1: y, y2: y, class: "axis" }));
      svg.appendChild(s("text", { x: left - 6, y: y + 4, "text-anchor": "end" }, fmtNum(v)));
    });
    var wrap = h("div", { class: "chart" });
    var tip = h("div", { class: "tip", hidden: true });
    daily.forEach(function (d, i) {
      var x = left + i * slot + (slot - bw) / 2;
      var bh = (d.conversations / niceMax) * plotH;
      var y0 = top + plotH;
      var hit = s("rect", { x: left + i * slot, y: top, width: slot, height: plotH, class: "bar-hit" });
      var bar;
      if (bh > 0) {
        var r = Math.min(4, bh, bw / 2);
        var y = y0 - bh;
        bar = s("path", { class: "bar", d: "M" + x + "," + y0 + "V" + (y + r) + "Q" + x + "," + y + " " + (x + r) + "," + y +
          "H" + (x + bw - r) + "Q" + (x + bw) + "," + y + " " + (x + bw) + "," + (y + r) + "V" + y0 + "Z" });
      } else {
        bar = s("g", {});
      }
      hit.addEventListener("mouseenter", function () {
        tip.hidden = false;
        tip.textContent = d.date + ": " + d.conversations;
        var rect = wrap.getBoundingClientRect();
        var scale = rect.width / W;
        tip.style.left = (x + bw / 2) * scale + "px";
        tip.style.top = (y0 - bh) * scale + "px";
        if (bar.classList) bar.classList.add("hl");
      });
      hit.addEventListener("mouseleave", function () { tip.hidden = true; if (bar.classList) bar.classList.remove("hl"); });
      svg.appendChild(hit);
      svg.appendChild(bar);
      if (i === 0 || i === daily.length - 1 || i === Math.floor(daily.length / 2)) {
        svg.appendChild(s("text", { x: left + i * slot + slot / 2, y: H - 4, "text-anchor": "middle" }, d.date.slice(5)));
      }
    });
    wrap.appendChild(svg);
    wrap.appendChild(tip);
    var table = h("details", { class: "small", style: { marginTop: "8px" } },
      h("summary", { class: "muted", text: tr("show_table") }),
      h("div", { class: "table-wrap" }, h("table", { class: "t" },
        h("thead", {}, h("tr", {}, h("th", { text: tr("date") }), h("th", { class: "num", text: tr("t_conversations") }))),
        h("tbody", {}, daily.slice().reverse().map(function (d) {
          return h("tr", {}, h("td", { text: d.date }), h("td", { class: "num", text: fmtNum(d.conversations) }));
        })))));
    return h("div", {}, wrap, table);
  }

  function pageDashboard(main) {
    var ws = state.ws;
    return api("GET", wsPath("/analytics?days=30")).then(function (d) {
      pageHead(main, tr("nav_dashboard"), ws.name + " · " + tr("last_30"));
      if (!state.me.llm_enabled) main.appendChild(h("div", { class: "notice warn small", text: tr("llm_off_notice") }));

      var steps = [
        [ws.document_count > 0, tr("step_knowledge"), "#/knowledge"],
        [ws.telegram.connected, tr("step_telegram"), "#/settings"],
        [d.totals.conversations > 0, tr("step_install"), "#/install"],
      ];
      if (steps.some(function (s) { return !s[0]; })) {
        main.appendChild(h("div", { class: "card" }, h("h2", { text: tr("getting_started") }),
          steps.map(function (s) {
            return h("div", { class: "row", style: { marginBottom: "6px" } },
              h("span", { text: s[0] ? "✅" : "⬜️" }),
              s[0] ? h("span", { class: "muted", text: s[1] }) : h("a", { href: s[2], text: s[1] }));
          })));
      }

      var t = d.totals;
      var tiles = [
        [fmtNum(t.conversations), tr("t_conversations")],
        [fmtNum(t.questions), tr("t_questions")],
        [t.answer_rate === null ? "—" : t.answer_rate + "%", tr("t_answer_rate")],
        [fmtNum(t.unanswered), tr("t_unanswered")],
        [fmtNum(t.leads), tr("t_leads")],
        [fmtNum(t.human_chats), tr("t_human")],
      ];
      main.appendChild(h("div", { class: "tiles" }, tiles.map(function (x) {
        return h("div", { class: "tile" }, h("div", { class: "v", text: x[0] }), h("div", { class: "l", text: x[1] }));
      })));
      main.appendChild(h("div", { class: "card" }, h("h2", { text: tr("chart_title") }), barChart(d.daily)));

      var unanswered = h("div", {});
      if (!d.unanswered_questions.length) unanswered.appendChild(h("div", { class: "empty", text: tr("nothing_yet") }));
      d.unanswered_questions.forEach(function (q) {
        var item = h("div", { style: { borderBottom: "1px solid var(--border)", padding: "8px 0" } });
        var answer = h("textarea", { placeholder: tr("answer"), rows: "3" });
        var saveBtn = h("button", { class: "btn sm", text: tr("save") });
        var form = h("div", { hidden: true, style: { marginTop: "6px" } }, answer,
          h("div", { class: "row", style: { marginTop: "6px" } }, saveBtn,
            h("button", { class: "btn secondary sm", text: tr("cancel"), onclick: function () { form.hidden = true; } })));
        saveBtn.addEventListener("click", function () {
          if (!answer.value.trim()) return answer.focus();
          run(saveBtn, api("POST", wsPath("/documents/faq"), { question: q.question, answer: answer.value })).then(function () {
            toast(tr("saved"));
            item.remove();
          });
        });
        append(item, [
          h("div", { class: "row" }, h("div", { class: "grow", text: q.question }),
            h("span", { class: "pill", text: q.count + "×" }),
            h("button", { class: "btn secondary sm", text: tr("add_answer"),
              onclick: function () { form.hidden = false; answer.focus(); } })),
          form,
        ]);
        unanswered.appendChild(item);
      });

      main.appendChild(h("div", { class: "grid two" },
        h("div", { class: "card" }, h("h2", { text: tr("top_questions") }),
          d.top_questions.length ? h("table", { class: "t" }, h("tbody", {}, d.top_questions.map(function (q) {
            return h("tr", {}, h("td", { text: q.question }), h("td", { class: "num", text: q.count + "×" }));
          }))) : h("div", { class: "empty", text: tr("nothing_yet") })),
        h("div", { class: "card" }, h("h2", { text: tr("unanswered_title") }),
          h("p", { class: "small muted", text: tr("unanswered_hint") }), unanswered)));
    });
  }

  // ------------------------------------------------------------------ knowledge base
  function pageKnowledge(main) {
    pageHead(main, tr("nav_knowledge"), tr("kb_sub"));
    if (!state.me.llm_enabled) main.appendChild(h("div", { class: "notice warn small", text: tr("llm_off_notice") }));
    var list = h("div", {});
    var formBox = h("div", {});
    var tabs = h("div", { class: "tabs", role: "tablist" });
    var current = store("d2c_kb_tab") || "faq";

    function renderForm(kind) {
      current = kind;
      store("d2c_kb_tab", kind);
      Array.prototype.forEach.call(tabs.children, function (b) { b.className = b.dataset.k === kind ? "on" : ""; });
      clear(formBox);
      var btn = h("button", { class: "btn", type: "submit" });
      var form;
      if (kind === "faq") {
        var q = h("input", { type: "text", required: true, maxlength: "1000" });
        var a = h("textarea", { required: true, rows: "4" });
        btn.textContent = tr("add");
        form = h("form", { onsubmit: function (e) {
          e.preventDefault();
          run(btn, api("POST", wsPath("/documents/faq"), { question: q.value, answer: a.value })).then(function () {
            form.reset(); q.focus(); toast(tr("saved")); loadDocs();
          });
        } }, h("label", { class: "f" }, tr("question"), q), h("label", { class: "f" }, tr("answer"), a), btn);
      } else if (kind === "url") {
        var url = h("input", { type: "url", required: true, placeholder: "https://example.ge/delivery" });
        var crawl = h("input", { type: "checkbox" });
        var pages = h("input", { type: "number", min: "1", max: "500", value: "20", style: { width: "90px" } });
        btn.textContent = tr("import");
        form = h("form", { onsubmit: function (e) {
          e.preventDefault();
          btn.textContent = tr("working");
          run(btn, api("POST", wsPath("/documents/url"), { url: url.value, crawl: crawl.checked, max_pages: parseInt(pages.value, 10) || 1 }))
            .then(function (docs) { form.reset(); toast(tr("saved") + ": " + docs.length); loadDocs(); })
            .finally(function () { btn.textContent = tr("import"); });
        } }, h("label", { class: "f" }, tr("url"), url),
          h("div", { class: "row", style: { marginBottom: "12px" } },
            h("label", { class: "check", style: { margin: 0 } }, crawl, tr("crawl")),
            h("label", { class: "check", style: { margin: 0 } }, tr("max_pages"), pages)), btn);
      } else if (kind === "pdf") {
        var file = h("input", { type: "file", accept: "application/pdf,.pdf", required: true });
        btn.textContent = tr("upload");
        form = h("form", { onsubmit: function (e) {
          e.preventDefault();
          var fd = new FormData();
          fd.append("file", file.files[0]);
          btn.textContent = tr("working");
          run(btn, api("POST", wsPath("/documents/pdf"), fd))
            .then(function () { form.reset(); toast(tr("saved")); loadDocs(); })
            .finally(function () { btn.textContent = tr("upload"); });
        } }, h("label", { class: "f" }, tr("pdf_file"), file), btn);
      } else {
        var title = h("input", { type: "text", required: true, maxlength: "500" });
        var content = h("textarea", { required: true, rows: "8", placeholder: tr("text_hint") });
        btn.textContent = tr("add");
        form = h("form", { onsubmit: function (e) {
          e.preventDefault();
          run(btn, api("POST", wsPath("/documents/text"), { title: title.value, content: content.value })).then(function () {
            form.reset(); toast(tr("saved")); loadDocs();
          });
        } }, h("label", { class: "f" }, tr("title"), title), h("label", { class: "f" }, tr("content"), content), btn);
      }
      formBox.appendChild(form);
    }
    ["faq", "url", "pdf", "text"].forEach(function (k) {
      tabs.appendChild(h("button", { type: "button", "data-k": k, role: "tab", text: tr("tab_" + k), onclick: function () { renderForm(k); } }));
    });

    function loadDocs() {
      return api("GET", wsPath("/documents")).then(function (docs) {
        clear(list);
        if (!docs.length) return list.appendChild(h("div", { class: "empty", text: tr("nothing_yet") }));
        list.appendChild(h("div", { class: "table-wrap" }, h("table", { class: "t" },
          h("thead", {}, h("tr", {}, h("th", { text: tr("kind") }), h("th", { text: tr("title") }),
            h("th", { class: "num", text: tr("size") }), h("th", { text: "" }))),
          h("tbody", {}, docs.map(function (d) {
            var del = h("button", { class: "btn danger sm", text: tr("delete") });
            del.addEventListener("click", function () {
              if (!window.confirm(tr("confirm_delete"))) return;
              run(del, api("DELETE", wsPath("/documents/" + d.id))).then(loadDocs);
            });
            var refresh = d.kind === "url" ? h("button", { class: "btn secondary sm", text: tr("refresh") }) : null;
            if (refresh) refresh.addEventListener("click", function () {
              run(refresh, api("POST", wsPath("/documents/" + d.id + "/refresh"))).then(function () { toast(tr("saved")); loadDocs(); });
            });
            return h("tr", {},
              h("td", {}, h("span", { class: "pill", text: d.kind.toUpperCase() })),
              h("td", {}, d.kind === "url" ? h("a", { href: d.source, target: "_blank", rel: "noopener", text: d.title }) : d.title,
                h("div", { class: "small muted", text: d.preview.slice(0, 140) })),
              h("td", { class: "num small", text: fmtNum(d.char_count) }),
              h("td", {}, h("div", { class: "row", style: { justifyContent: "flex-end", flexWrap: "nowrap" } }, refresh, del)));
          })))));
      });
    }

    // playground
    var qInput = h("input", { type: "text", placeholder: tr("test_placeholder"), class: "grow" });
    var askBtn = h("button", { class: "btn", type: "submit", text: tr("ask") });
    var out = h("div", { style: { marginTop: "10px" } });
    var test = h("form", { onsubmit: function (e) {
      e.preventDefault();
      if (!qInput.value.trim()) return;
      run(askBtn, api("POST", wsPath("/test-chat"), { text: qInput.value })).then(function (r) {
        clear(out).appendChild(h("div", { class: "notice", style: { whiteSpace: "pre-wrap" } },
          h("span", { class: "pill " + (r.answered ? "good" : "bad"), text: r.answered ? tr("answered") : tr("not_answered") }),
          " ", h("span", { class: "small muted", text: r.kind }), h("div", { style: { marginTop: "6px" }, text: r.text }),
          r.sources.length ? h("div", { class: "small muted", text: "↳ " + r.sources.map(function (s) { return s.title; }).join(", ") }) : null));
      });
    } }, h("div", { class: "row" }, qInput, askBtn));

    main.appendChild(h("div", { class: "grid two" },
      h("div", { class: "card" }, tabs, formBox),
      h("div", { class: "card" }, h("h2", { text: tr("test_title") }), test, out)));
    main.appendChild(h("div", { class: "card" }, h("h2", { text: tr("documents") }), list));
    renderForm(current);
    return loadDocs();
  }

  // ------------------------------------------------------------------ inbox
  function pageInbox(main, convId) {
    var filter = store("d2c_inbox_filter") || "";
    var listBox = h("div", { class: "conv-list" });
    var detail = h("div", { class: "card" });
    var tabs = h("div", { class: "tabs" });
    var lastRendered = "";
    pageHead(main, tr("nav_inbox"));

    function loadList() {
      return api("GET", wsPath("/conversations" + (filter ? "?status=" + filter : ""))).then(function (convs) {
        clear(listBox);
        if (!convs.length) listBox.appendChild(h("div", { class: "empty", text: tr("nothing_yet") }));
        convs.forEach(function (c) {
          listBox.appendChild(h("a", { class: "conv-item" + (String(c.id) === convId ? " on" : ""), href: "#/inbox/" + c.id },
            h("div", { class: "row", style: { justifyContent: "space-between" } },
              h("strong", { text: "#" + c.id }),
              h("span", { class: "pill " + (c.status === "handoff" ? "warn" : ""), text: tr("status_" + c.status) + " · " + c.language.toUpperCase() })),
            h("div", { class: "p", text: c.last_message ? c.last_message.content : "" }),
            h("div", { class: "small muted", text: fmtDate(c.updated_at) })));
        });
      });
    }
    function renderTabs() {
      clear(tabs);
      [["", "filter_all"], ["handoff", "filter_handoff"]].forEach(function (f) {
        tabs.appendChild(h("button", { class: filter === f[0] ? "on" : "", text: tr(f[1]), onclick: function () {
          filter = f[0]; store("d2c_inbox_filter", filter); renderTabs(); loadList();
        } }));
      });
    }

    var thread = h("div", { class: "thread" });
    var headBox = h("div", {});
    var leadBox = h("div", {});
    var reply = h("textarea", { rows: "3", placeholder: tr("reply_placeholder") });
    var sendBtn = h("button", { class: "btn", type: "submit", text: tr("send") });
    var backBtn = h("button", { class: "btn secondary", type: "button", text: tr("hand_back") });

    function loadDetail() {
      if (!convId) return Promise.resolve();
      return api("GET", wsPath("/conversations/" + convId)).then(function (c) {
        var sig = c.status + ":" + c.messages.length + ":" + (c.lead ? c.lead.id : "");
        if (sig === lastRendered) return;
        lastRendered = sig;
        clear(headBox).appendChild(h("div", { class: "row", style: { justifyContent: "space-between", marginBottom: "8px" } },
          h("h2", { style: { margin: 0 }, text: "#" + c.id }),
          h("span", { class: "pill " + (c.status === "handoff" ? "warn" : ""), text: tr("status_" + c.status) })));
        if (c.page_url) headBox.appendChild(h("div", { class: "small muted", style: { marginBottom: "8px", overflowWrap: "anywhere" } }, "🔗 ", c.page_url));
        clear(thread);
        c.messages.forEach(function (m) {
          thread.appendChild(h("div", { class: "bubble " + m.role },
            m.content,
            m.role !== "system" ? h("div", { class: "meta", text: tr("role_" + m.role) + " · " + fmtDate(m.created_at) +
              (m.role === "user" && m.answered === false ? " · ⚠️ " + tr("not_answered") : "") }) : null));
        });
        thread.scrollTop = thread.scrollHeight;
        clear(leadBox);
        if (c.lead) {
          leadBox.appendChild(h("div", { class: "notice small" }, h("strong", { text: tr("lead_info") + ": " }),
            [c.lead.name, c.lead.phone, c.lead.email, c.lead.note].filter(Boolean).join(" · ")));
        }
        backBtn.hidden = c.status !== "handoff";
      });
    }

    backBtn.addEventListener("click", function () {
      run(backBtn, api("POST", wsPath("/conversations/" + convId + "/close"))).then(function () { loadDetail(); loadList(); });
    });
    var replyForm = h("form", { onsubmit: function (e) {
      e.preventDefault();
      if (!reply.value.trim()) return;
      run(sendBtn, api("POST", wsPath("/conversations/" + convId + "/reply"), { text: reply.value })).then(function () {
        reply.value = ""; loadDetail(); loadList();
      });
    } }, reply, h("div", { class: "row", style: { marginTop: "8px" } }, sendBtn, backBtn));
    reply.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) replyForm.requestSubmit();
    });

    if (convId) append(detail, [headBox, leadBox, thread, replyForm]);
    else detail.appendChild(h("div", { class: "empty", text: tr("select_conv") }));

    renderTabs();
    main.appendChild(h("div", { class: "inbox" }, h("div", { class: "card", style: { padding: "8px" } }, tabs, listBox), detail));
    every(5000, function () { loadList(); loadDetail(); });
    return Promise.all([loadList(), loadDetail()]);
  }

  // ------------------------------------------------------------------ leads
  function pageLeads(main) {
    pageHead(main, tr("nav_leads"), null,
      h("a", { class: "btn secondary", href: wsPath("/leads.csv"), text: "⬇ " + tr("export_csv") }));
    var box = h("div", { class: "card" });
    main.appendChild(box);
    return api("GET", wsPath("/leads")).then(function (leads) {
      if (!leads.length) return box.appendChild(h("div", { class: "empty", text: tr("nothing_yet") }));
      box.appendChild(h("div", { class: "table-wrap" }, h("table", { class: "t" },
        h("thead", {}, h("tr", {}, ["date", "name", "phone", "email", "note", "status", "value", "chat"].map(function (k) {
          return h("th", { text: tr(k) });
        }))),
        h("tbody", {}, leads.map(function (l) {
          var status = h("select", { onchange: function () { save({ status: status.value }); } },
            ["new", "contacted", "won", "lost"].map(function (s) { return h("option", { value: s, text: tr("st_" + s) }); }));
          status.value = l.status;
          var value = h("input", { type: "number", min: "0", step: "0.01", value: l.value === null ? "" : String(l.value),
            style: { width: "110px" }, onchange: function () {
              save({ value: value.value === "" ? null : parseFloat(value.value) });
            } });
          function save(body) {
            api("PATCH", wsPath("/leads/" + l.id), body).then(function () { toast(tr("saved")); })
              .catch(function (err) { toast(err.message, true); });
          }
          return h("tr", {},
            h("td", { class: "small", text: fmtDate(l.created_at) }),
            h("td", { text: l.name }),
            h("td", {}, l.phone ? h("a", { href: "tel:" + l.phone.replace(/[^+\d]/g, ""), text: l.phone }) : ""),
            h("td", {}, l.email ? h("a", { href: "mailto:" + l.email, text: l.email }) : ""),
            h("td", { class: "small", text: l.note }),
            h("td", {}, status), h("td", {}, value),
            h("td", {}, l.conversation_id ? h("a", { href: "#/inbox/" + l.conversation_id, text: "#" + l.conversation_id }) : ""));
        })))));
    });
  }

  // ------------------------------------------------------------------ settings
  function pageSettings(main) {
    var ws = state.ws;
    pageHead(main, tr("nav_settings"), ws.name);
    var f = {
      name: h("input", { type: "text", value: ws.name, maxlength: "200", required: true }),
      bot_name: h("input", { type: "text", value: ws.bot_name, maxlength: "100", required: true }),
      welcome_message: h("textarea", { rows: "2", maxlength: "1000", value: ws.welcome_message }),
      company_info: h("textarea", { rows: "6", maxlength: "8000", value: ws.company_info, placeholder: tr("company_info_hint") }),
      brand_color: h("input", { type: "color", value: ws.brand_color }),
      default_language: h("select", {}, [["ka", "ქართული"], ["en", "English"], ["ru", "Русский"]].map(function (o) {
        return h("option", { value: o[0], text: o[1] });
      })),
      lead_capture_enabled: h("input", { type: "checkbox", checked: ws.lead_capture_enabled }),
      handoff_enabled: h("input", { type: "checkbox", checked: ws.handoff_enabled }),
      allowed_origins: h("textarea", { rows: "2", value: ws.allowed_origins.split(",").filter(Boolean).join("\n"),
        placeholder: "https://myshop.ge" }),
    };
    f.default_language.value = ws.default_language;
    var saveBtn = h("button", { class: "btn", type: "submit", text: tr("save") });
    var form = h("form", { onsubmit: function (e) {
      e.preventDefault();
      var body = {};
      Object.keys(f).forEach(function (k) { body[k] = f[k].type === "checkbox" ? f[k].checked : f[k].value; });
      run(saveBtn, api("PATCH", wsPath(), body)).then(function (updated) {
        state.ws = updated;
        state.me = null;
        toast(tr("saved"));
      });
    } },
      h("label", { class: "f" }, tr("ws_name"), f.name),
      h("div", { class: "row" },
        h("label", { class: "f grow" }, tr("bot_name"), f.bot_name),
        h("label", { class: "f" }, tr("default_lang"), f.default_language),
        h("label", { class: "f" }, tr("brand_color"), f.brand_color)),
      h("label", { class: "f" }, tr("welcome"), f.welcome_message, h("span", { class: "hint", text: tr("welcome_hint") })),
      h("label", { class: "f" }, tr("company_info"), f.company_info),
      h("label", { class: "check" }, f.lead_capture_enabled, tr("lead_capture")),
      h("label", { class: "check" }, f.handoff_enabled, tr("handoff")),
      h("label", { class: "f" }, tr("origins"), f.allowed_origins, h("span", { class: "hint", text: tr("origins_hint") })),
      saveBtn);

    // telegram
    var tg = ws.telegram;
    var tgBox = h("div", { class: "card" }, h("h2", { text: tr("tg_title") }));
    if (!tg.available) {
      tgBox.appendChild(h("p", { class: "small muted", text: tr("tg_unavailable") }));
    } else if (tg.connected) {
      var testBtn = h("button", { class: "btn secondary sm", text: tr("tg_test") });
      testBtn.addEventListener("click", function () {
        run(testBtn, api("POST", wsPath("/telegram/test"))).then(function () { toast("✅"); });
      });
      var disBtn = h("button", { class: "btn danger sm", text: tr("tg_disconnect") });
      disBtn.addEventListener("click", function () {
        run(disBtn, api("POST", wsPath("/telegram/disconnect"))).then(function () { route(); });
      });
      append(tgBox, [h("p", {}, "✅ " + tr("tg_connected")), h("div", { class: "row" }, testBtn, disBtn)]);
    } else {
      append(tgBox, [
        h("p", { class: "small", text: tr("tg_steps") }),
        h("div", { class: "row" },
          tg.connect_link ? h("a", { class: "btn", href: tg.connect_link, target: "_blank", rel: "noopener", text: "✈️ " + tr("tg_connect") }) : null,
          h("button", { class: "btn secondary", text: tr("tg_check"), onclick: function () { route(); } })),
        h("p", { class: "small muted", style: { marginTop: "10px" } }, tr("tg_manual") + " ",
          h("code", { text: "/start " + tg.connect_code }), tg.bot_username ? " → @" + tg.bot_username : ""),
      ]);
    }

    var rotate = h("button", { class: "btn danger sm", text: tr("rotate_key") });
    rotate.addEventListener("click", function () {
      if (!window.confirm(tr("rotate_confirm"))) return;
      run(rotate, api("POST", wsPath("/rotate-key"))).then(function () { toast(tr("saved")); route(); });
    });
    var del = h("button", { class: "btn danger sm", text: tr("delete_ws") });
    del.addEventListener("click", function () {
      var typed = window.prompt(tr("delete_ws_confirm"));
      if (typed !== ws.name) return;
      run(del, api("DELETE", wsPath())).then(function () { store("d2c_ws", ""); state.me = null; go("#/dashboard"); });
    });

    main.appendChild(h("div", { class: "grid two" },
      h("div", { class: "card" }, h("h2", { text: tr("s_bot") }), form),
      h("div", {}, tgBox, h("div", { class: "card" }, h("h2", { text: tr("danger") }), h("div", { class: "row" }, rotate, del)))));
  }

  // ------------------------------------------------------------------ install
  function pageInstall(main) {
    var ws = state.ws;
    pageHead(main, tr("nav_install"), ws.name, h("a", { class: "btn secondary", href: "/demo?key=" + encodeURIComponent(ws.public_key), target: "_blank", rel: "noopener", text: "👁 " + tr("preview") }));
    var copyBtn = h("button", { class: "btn", text: tr("copy") });
    copyBtn.addEventListener("click", function () {
      navigator.clipboard.writeText(ws.embed_code).then(function () { toast(tr("copied")); }, function () { toast("Clipboard blocked", true); });
    });
    main.appendChild(h("div", { class: "card" },
      h("h2", { text: tr("install_step1") }), h("pre", { class: "code", text: ws.embed_code }), copyBtn,
      h("h2", { style: { marginTop: "18px" }, text: tr("install_step2") }),
      h("h3", { text: tr("platforms") }),
      h("ul", {}, ["p_wp", "p_shopify", "p_wix", "p_tilda", "p_html"].map(function (k) { return h("li", { text: tr(k) }); })),
      h("h3", { style: { marginTop: "14px" }, text: tr("js_api") }),
      h("pre", { class: "code", text: '<button onclick="Docs2Chat.open()">Chat</button>' })));
  }

  // ------------------------------------------------------------------ billing
  var paddleLoading = null;
  function loadPaddle(cfg, onEvent) {
    if (window.Paddle && window.Paddle.__d2c) return Promise.resolve(window.Paddle);
    if (!paddleLoading) {
      paddleLoading = new Promise(function (resolve, reject) {
        var s = document.createElement("script");
        s.src = "https://cdn.paddle.com/paddle/v2/paddle.js";
        s.onload = function () {
          if (cfg.environment === "sandbox") window.Paddle.Environment.set("sandbox");
          window.Paddle.Initialize({ token: cfg.client_token, eventCallback: onEvent });
          window.Paddle.__d2c = true;
          resolve(window.Paddle);
        };
        s.onerror = function () { paddleLoading = null; reject(new Error("Could not load Paddle")); };
        document.head.appendChild(s);
      });
    }
    return paddleLoading;
  }

  function meter(used, limit) {
    var pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
    return h("div", {},
      h("div", { class: "small", text: fmtNum(used) + " / " + (limit > 0 ? fmtNum(limit) : tr("unlimited")) }),
      limit > 0 ? h("div", { class: "meter", role: "meter", "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100" },
        h("i", { style: { width: pct + "%" } })) : null);
  }

  function pageBilling(main) {
    pageHead(main, tr("nav_billing"), state.ws.name);
    return api("GET", wsPath("/billing")).then(function (b) {
      if (!b.billing_enabled) {
        main.appendChild(h("div", { class: "notice", text: "✅ " + tr("selfhosted_notice") }));
        return;
      }
      var p = b.plan;
      var manage = h("div", { class: "row", style: { marginTop: "10px" } },
        b.paddle.update_payment_url && b.plan_source === "paddle" ? h("a", { class: "btn secondary sm", href: b.paddle.update_payment_url, target: "_blank", rel: "noopener", text: tr("manage_payment") }) : null,
        b.paddle.cancel_url && b.plan_source === "paddle" ? h("a", { class: "btn danger sm", href: b.paddle.cancel_url, target: "_blank", rel: "noopener", text: tr("cancel_sub") }) : null);
      main.appendChild(h("div", { class: "grid two" },
        h("div", { class: "card" }, h("h2", { text: tr("current_plan") }),
          h("div", { style: { fontSize: "24px", fontWeight: "800" }, text: p.name }),
          b.plan_expires_at ? h("div", { class: "small muted", text: tr("paid_until") + ": " + fmtDate(b.plan_expires_at) }) : null,
          b.paddle.status ? h("div", { class: "small muted", text: "Paddle: " + b.paddle.status }) : null, manage),
        h("div", { class: "card" },
          h("h3", { text: tr("ai_answers") }), meter(b.usage.ai_messages, p.ai_messages),
          h("h3", { style: { marginTop: "12px" }, text: tr("sources_used") }), meter(b.usage.documents, p.documents))));

      function onPaddleEvent(ev) {
        if (ev && ev.name === "checkout.completed") {
          toast(tr("payment_done"));
          var tries = 0;
          var poll = setInterval(function () {
            tries += 1;
            api("GET", wsPath("/billing")).then(function (nb) {
              if (nb.plan.id !== b.plan.id || tries > 15) { clearInterval(poll); state.me = null; route(); }
            });
          }, 2000);
        }
      }

      var cards = b.plans.map(function (plan) {
        var isCurrent = plan.id === p.id;
        var priceId = b.paddle.prices[plan.id];
        var btn = null;
        if (isCurrent) btn = h("button", { class: "btn secondary", disabled: true, text: tr("current") });
        else if (plan.price_usd > 0 && b.paddle.enabled && priceId) {
          btn = h("button", { class: "btn", text: tr("upgrade") });
          btn.addEventListener("click", function () {
            run(btn, loadPaddle(b.paddle, onPaddleEvent)).then(function (Paddle) {
              Paddle.Checkout.open({
                items: [{ priceId: priceId, quantity: 1 }],
                customer: { email: b.paddle.customer_email },
                customData: { workspace_id: String(state.ws.id) },
              });
            });
          });
        }
        return h("div", { class: "plan" + (isCurrent ? " current" : "") },
          h("div", { style: { fontWeight: "700" }, text: plan.name }),
          h("div", {}, h("span", { class: "price", text: "$" + plan.price_usd }), h("span", { class: "muted", text: tr("per_month") })),
          h("ul", {}, plan.features.map(function (f) { return h("li", { text: f }); })), btn);
      });
      main.appendChild(h("div", { class: "card" }, h("div", { class: "plans" }, cards),
        h("p", { class: "small muted", style: { marginTop: "12px" } }, tr("pay_invoice") + " ",
          b.contact_email ? h("a", { href: "mailto:" + b.contact_email, text: b.contact_email }) : null)));

      if (b.platform_fee.percent > 0) {
        main.appendChild(h("div", { class: "card" }, h("h2", { text: tr("fee_title") }),
          h("p", { text: tr("fee_text", { p: b.platform_fee.percent, v: fmtNum(b.platform_fee.won_value_30d), f: fmtNum(b.platform_fee.fee_30d) }) })));
      }
    });
  }

  // ------------------------------------------------------------------ platform (superadmin)
  function pagePlatform(main) {
    pageHead(main, tr("nav_platform"));
    return api("GET", "/api/platform/workspaces").then(function (d) {
      var paying = d.workspaces.filter(function (w) { return w.plan !== "free"; }).length;
      main.appendChild(h("div", { class: "tiles" },
        [["$" + fmtNum(d.mrr_usd), tr("mrr")], [fmtNum(d.workspaces.length), tr("customers")], [fmtNum(paying), tr("paying")]].map(function (x) {
          return h("div", { class: "tile" }, h("div", { class: "v", text: x[0] }), h("div", { class: "l", text: x[1] }));
        })));
      main.appendChild(h("div", { class: "card" }, h("div", { class: "table-wrap" }, h("table", { class: "t" },
        h("thead", {}, h("tr", {}, ["#", tr("business_name"), tr("owner"), tr("plan"), tr("ai_answers"), tr("sources_used"), "Telegram", tr("expires"), ""].map(function (x) {
          return h("th", { text: x });
        }))),
        h("tbody", {}, d.workspaces.map(function (w) {
          var sel = h("select", {}, ["free", "starter", "pro", "business"].map(function (p) { return h("option", { value: p, text: p }); }));
          sel.value = w.plan;
          var exp = h("input", { type: "date", value: w.plan_expires_at ? w.plan_expires_at.slice(0, 10) : "" });
          var btn = h("button", { class: "btn sm", text: tr("set_plan") });
          btn.addEventListener("click", function () {
            run(btn, api("POST", "/api/platform/workspaces/" + w.id + "/plan", {
              plan: sel.value, expires_at: exp.value ? exp.value + "T23:59:59Z" : null,
            })).then(function () { toast(tr("saved")); });
          });
          return h("tr", {},
            h("td", { text: String(w.id) }), h("td", { text: w.name }), h("td", { class: "small", text: w.owner_email }),
            h("td", {}, h("span", { class: "pill", text: w.plan + (w.plan_source !== "none" ? " · " + w.plan_source : "") })),
            h("td", { class: "num", text: fmtNum(w.ai_messages) }), h("td", { class: "num", text: fmtNum(w.documents) }),
            h("td", { text: w.telegram ? "✅" : "—" }),
            h("td", {}, h("div", { class: "row", style: { flexWrap: "nowrap" } }, sel, exp)), h("td", {}, btn));
        }))))));
    });
  }

  route();
})();
