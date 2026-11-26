/*
 * Daily Hadith card
 * Bundled with the Daily Hadith integration (zubir2k/homeassistant-dailyhadith).
 * The integration serves this file and adds it to the dashboard resources itself.
 *
 *   type: custom:daily-hadith-card
 *   entity: sensor.daily_hadith      # optional
 *   language: auto                   # auto | en | translation   (starting language)
 *   show_arabic: true
 *   show_translation: true
 *   show_toggle: true                # EN / translation switch on the card
 *   show_ai_note: true               # small "AI translation" note under the text
 *   show_header: true
 *   show_reference: true
 *   show_refresh: true
 *   show_copy: true
 *   collapse: true                   # fold long hadith behind "Show more"
 */

const CARD_VERSION = "1.3.3";
const CARD_TAG = "daily-hadith-card";
const EDITOR_TAG = "daily-hadith-card-editor";
const DEFAULT_ENTITY = "sensor.daily_hadith";
// Lines shown before "Show more" when a hadith is long.
const AR_LINES = 5;
const TR_LINES = 6;

/* Bundled Amiri (SIL OFL) for the Arabic text. @font-face does not register from
   inside a shadow root, so it goes into document.head once. The browser only downloads
   it when Arabic glyphs are drawn, and falls back to system Arabic fonts without it. */
const FONT_URL = "/daily_hadith_static/fonts/Amiri-Regular.woff2";
(function injectFont() {
  if (document.getElementById("daily-hadith-fonts")) return;
  const st = document.createElement("style");
  st.id = "daily-hadith-fonts";
  st.textContent =
    `@font-face{font-family:"Daily Hadith Amiri";src:url("${FONT_URL}") format("woff2");` +
    `font-weight:400;font-style:normal;font-display:swap;` +
    `unicode-range:U+0600-06FF,U+0750-077F,U+08A0-08FF,U+FB50-FDFF,U+FE70-FEFF;}`;
  document.head.appendChild(st);
})();

const COLLECTIONS = {
  riyadussalihin: "Riyad as-Salihin",
  bukhari: "Sahih al-Bukhari",
  muslim: "Sahih Muslim",
  abudawud: "Sunan Abi Dawud",
  tirmidhi: "Jami` at-Tirmidhi",
  nasai: "Sunan an-Nasa'i",
  ibnmajah: "Sunan Ibn Majah",
  malik: "Muwatta Malik",
  ahmad: "Musnad Ahmad",
  darimi: "Sunan ad-Darimi",
  nawawi40: "40 Hadith Nawawi",
  qudsi40: "40 Hadith Qudsi",
  adab: "Al-Adab Al-Mufrad",
  bulugh: "Bulugh al-Maram",
  shamail: "Ash-Shama'il",
  mishkat: "Mishkat al-Masabih",
  hisn: "Hisn al-Muslim",
};

const UI = {
  en: {
    heading: "Hadith of the Day",
    more: "Show more",
    less: "Show less",
    refresh: "New hadith",
    copy: "Copy",
    copied: "Copied",
    open: "Open on Sunnah.com",
    unavailable: "Hadith not available yet",
    missing: "Entity not found",
    no_tr: "Translation not available yet",
    ai: "AI translation",
    hadith: "Hadith",
  },
  ms: {
    heading: "Hadis Hari Ini",
    more: "Selanjutnya",
    less: "Ringkaskan",
    refresh: "Hadis baharu",
    copy: "Salin",
    copied: "Disalin",
    open: "Buka di Sunnah.com",
    unavailable: "Hadis belum tersedia",
    missing: "Entiti tidak dijumpai",
    no_tr: "Terjemahan belum tersedia",
    ai: "Terjemahan AI",
    hadith: "Hadis",
  },
};

const ICONS = {
  book:
    "M19 2L14 6.5V17.5L19 13V2M6.5 5C4.55 5 2.45 5.4 1 6.5V21.16C1 21.41 1.25 21.66 1.5 21.66C1.6 21.66 1.65 21.59 1.75 21.59C3.1 20.94 5.05 20.5 6.5 20.5C8.45 20.5 10.55 20.9 12 22C13.35 21.15 15.8 20.5 17.5 20.5C19.15 20.5 20.85 20.81 22.25 21.56C22.35 21.61 22.4 21.59 22.5 21.59C22.75 21.59 23 21.34 23 21.09V6.5C22.4 6.05 21.75 5.75 21 5.5V19C19.9 18.65 18.7 18.5 17.5 18.5C15.8 18.5 13.35 19.15 12 20V6.5C10.55 5.4 8.45 5 6.5 5Z",
  refresh:
    "M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35Z",
  copy:
    "M19 21H8V7h11m0-2H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2m-3-4H4a2 2 0 0 0-2 2v14h2V3h12V1Z",
  check: "M21 7L9 19l-5.5-5.5 1.41-1.41L9 16.17 19.59 5.59 21 7Z",
  open:
    "M14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3m-2 16H5V5h7V3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7h-2v7Z",
  chevron: "M7.41 8.58L12 13.17l4.59-4.59L18 10l-6 6-6-6 1.41-1.42Z",
};

const svg = (path, cls = "") =>
  `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>`;

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const uiLang = (hass) => (String(hass?.locale?.language || hass?.language || "en").startsWith("ms") ? "ms" : "en");

const baseLang = (code) => String(code || "").split(/[-_]/)[0].toLowerCase();
const RTL = new Set(["ar", "fa", "he", "ur", "ps", "sd", "ug", "yi", "dv", "ku"]);

/** The translation the sensor offers next to English (Malay on older versions). */
function translationOf(a) {
  const code = a.translation_language || "ms";
  const base = baseLang(code);
  const offered = base !== "en" && base !== "ar";
  const text = a.translation || (base === "ms" ? a.malay : "") || "";
  const title = a.title_translation || (base === "ms" ? a.title_ms : "") || "";
  return {
    code, base, offered, text, title,
    has: offered && !!String(text).trim(),
    label: base === "ms" ? "BM" : base.toUpperCase(),
    source: a.translation_source || "",
  };
}

/** Strip the Arabic chapter dash and normalise blank lines. */
const tidy = (s) => String(s ?? "").replace(/^\s*-\s*/, "").replace(/\n{3,}/g, "\n\n").trim();

/** Show the trailing narrator source, e.g. "[Al-Bukhari].", in a quieter style. */
function translationHtml(text) {
  const t = tidy(text);
  const m = t.match(/^([\s\S]*?)\s*(\[[^\]]+\]\.?)\s*$/);
  // ﷺ is not in most Latin UI fonts; draw it with the Arabic font.
  const fix = (s) => esc(s).replace(/\uFDFA/g, '<span class="saw">\uFDFA</span>');
  return m ? `${fix(m[1])} <span class="narr">${fix(m[2])}</span>` : fix(t);
}

class DailyHadithCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._expanded = false;
    this._lang = null;
    this._busy = false;
    this._sig = "";
  }

  static getConfigElement() {
    return document.createElement(EDITOR_TAG);
  }

  static getStubConfig(hass) {
    const found = Object.keys(hass?.states || {}).find(
      (id) => id.startsWith("sensor.") && "arabic" in (hass.states[id].attributes || {}) && "hadith_number" in (hass.states[id].attributes || {})
    );
    return { entity: found || DEFAULT_ENTITY };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = {
      entity: DEFAULT_ENTITY,
      language: "auto",
      show_arabic: true,
      show_translation: true,
      show_toggle: true,
      show_header: true,
      show_reference: true,
      show_refresh: true,
      show_copy: true,
      show_ai_note: true,
      collapse: true,
      ...config,
    };
    this._lang = null; // re-pick the starting language from the new config
    this._sig = "";
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config?.entity];
    const sig = st ? `${st.state}|${st.last_updated}|${uiLang(hass)}|${hass.themes?.darkMode}` : "none";
    if (sig !== this._sig) {
      this._sig = sig;
      this._render();
    }
  }

  getCardSize() {
    return this._expanded ? 9 : 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  /* --- language ------------------------------------------------------------ */
  _storageKey() {
    return `daily-hadith-card:lang:${this._config.entity}`;
  }

  _startLang(tr) {
    try {
      const saved = localStorage.getItem(this._storageKey());
      if (saved === "en") return "en";
      if (saved === "tr" || saved === "ms") return "tr"; // "ms" from 1.2.0
    } catch (_e) {
      /* private mode */
    }
    const c = this._config.language;
    if (c === "en") return "en";
    if (c === "translation" || c === "ms") return "tr";
    const ha = baseLang(this._hass?.locale?.language || this._hass?.language);
    return ha === tr.base ? "tr" : "en";
  }

  _setLang(lang) {
    this._lang = lang;
    try {
      localStorage.setItem(this._storageKey(), lang);
    } catch (_e) {
      /* ignore */
    }
    this._render();
  }

  /* --- actions --------------------------------------------------------------- */
  async _refresh() {
    if (this._busy) return;
    this._busy = true;
    this._render();
    try {
      await this._hass.callService("daily_hadith", "reload", {});
      this._expanded = false;
    } catch (err) {
      console.error("Daily Hadith: reload failed", err);
    } finally {
      this._busy = false;
      this._sig = "";
      this._render();
    }
  }

  async _copy(textToCopy) {
    let ok = false;
    try {
      await navigator.clipboard.writeText(textToCopy);
      ok = true;
    } catch (_e) {
      // Non-HTTPS dashboards have no clipboard API.
      const ta = document.createElement("textarea");
      ta.value = textToCopy;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        ok = document.execCommand("copy");
      } catch (_e2) {
        ok = false;
      }
      ta.remove();
    }
    if (ok) {
      const b = this.shadowRoot.querySelector(".copy");
      if (b) {
        b.innerHTML = svg(ICONS.check);
        b.title = UI[this._chrome || "en"].copied;
        setTimeout(() => {
          b.innerHTML = svg(ICONS.copy);
          b.title = UI[this._chrome || "en"].copy;
        }, 1500);
      }
    }
  }

  /* --- render --------------------------------------------------------------- */
  _render() {
    if (!this._config || !this._hass) return;
    const c = this._config;
    let t = UI[uiLang(this._hass)];
    const st = this._hass.states[c.entity];

    if (!st) {
      this._paint(`<div class="empty">${esc(t.missing)}: ${esc(c.entity)}</div>`);
      return;
    }
    const a = st.attributes || {};
    if (!a.text && !a.arabic) {
      this._paint(`<div class="empty">${esc(t.unavailable)}</div>`);
      return;
    }

    const tr = translationOf(a);
    if (!this._lang) this._lang = this._startLang(tr);
    const showTr = this._lang === "tr" && tr.has;
    const lang = showTr ? tr.code : "en";

    // The card's own words follow the language being shown (EN or BM);
    // for other languages they follow the Home Assistant language.
    this._chrome = showTr ? (UI[tr.base] ? tr.base : uiLang(this._hass)) : "en";
    t = UI[this._chrome];

    const translation = showTr ? tr.text : a.text;
    const title = (showTr && tr.title) || a.title || "";
    const slug = String(a.url || "").match(/sunnah\.com\/([^:/?#]+)/)?.[1] || "";
    const collection = COLLECTIONS[slug] || a.collection || "";
    const ref = [collection, a.hadith_number].filter(Boolean).join(" · ");

    let date = "";
    if (st.state && /^\d{4}-\d{2}-\d{2}$/.test(st.state)) {
      try {
        const ha = this._hass.locale?.language || "en";
        const locale = showTr ? tr.code : baseLang(ha) === "en" ? ha : "en";
        date = new Date(`${st.state}T12:00:00`).toLocaleDateString(locale, {
          weekday: "short", day: "numeric", month: "short", year: "numeric",
        });
      } catch (_e) {
        date = st.state;
      }
    }

    const toggle =
      c.show_toggle && c.show_translation && tr.offered
        ? `<div class="seg" role="group" aria-label="Translation">
             <button class="${showTr ? "" : "on"}" data-lang="en" aria-pressed="${!showTr}">EN</button>
             <button class="${showTr ? "on" : ""}" data-lang="tr" aria-pressed="${showTr}" ${tr.has ? "" : `disabled title="${esc(UI[uiLang(this._hass)].no_tr)}"`}>${esc(tr.label)}</button>
           </div>`
        : "";

    const header = c.show_header
      ? `<div class="head">
           <div class="badge">${svg(ICONS.book)}</div>
           <div class="ht">
             <div class="label">${esc(t.heading)}${date ? ` · ${esc(date)}` : ""}</div>
             <div class="title">${esc(title)}</div>
           </div>
           ${toggle}
         </div>`
      : toggle ? `<div class="head solo">${toggle}</div>` : "";

    const arabic = c.show_arabic && a.arabic ? `<div class="ar" dir="rtl" lang="ar">${esc(tidy(a.arabic))}</div>` : "";
    const trans =
      c.show_translation && translation
        ? `<div class="tr" lang="${esc(lang)}" dir="${showTr && RTL.has(tr.base) ? "rtl" : "auto"}">${translationHtml(translation)}</div>`
        : "";
    const aiNote =
      c.show_translation && showTr && c.show_ai_note !== false && tr.source
        ? `<div class="ai">${esc(t.ai)}</div>`
        : "";
    const divider = arabic && trans ? `<div class="div"></div>` : "";

    const chip =
      c.show_reference && ref
        ? a.url
          ? `<a class="chip" href="${esc(a.url)}" target="_blank" rel="noopener noreferrer" title="${esc(t.open)}">${svg(ICONS.book, "s")}<span>${esc(ref)}</span>${svg(ICONS.open, "s")}</a>`
          : `<span class="chip">${svg(ICONS.book, "s")}<span>${esc(ref)}</span></span>`
        : "";
    const refresh = c.show_refresh
      ? `<button class="icon refresh ${this._busy ? "spin" : ""}" title="${esc(t.refresh)}" aria-label="${esc(t.refresh)}">${svg(ICONS.refresh)}</button>`
      : "";
    const copy = c.show_copy
      ? `<button class="icon copy" title="${esc(t.copy)}" aria-label="${esc(t.copy)}">${svg(ICONS.copy)}</button>`
      : "";
    const footer =
      chip || refresh || copy ? `<div class="foot">${chip}<span class="sp"></span>${copy}${refresh}</div>` : "";

    this._paint(`
      ${header}
      <div class="body ${c.collapse && !this._expanded ? "clamped" : ""}">${arabic}${divider}${trans}</div>
      <button class="more" hidden>${svg(ICONS.chevron)}<span></span></button>
      ${aiNote}
      ${footer}
    `);

    const root = this.shadowRoot;
    root.querySelectorAll(".seg button").forEach((b) =>
      b.addEventListener("click", () => !b.disabled && this._setLang(b.dataset.lang))
    );
    root.querySelector(".refresh")?.addEventListener("click", () => this._refresh());
    root.querySelector(".copy")?.addEventListener("click", () => {
      const parts = [];
      if (c.show_arabic && a.arabic) parts.push(tidy(a.arabic));
      if (c.show_translation && translation) parts.push(tidy(translation));
      if (ref) parts.push(`${ref}${a.url ? `\n${a.url}` : ""}`);
      this._copy(parts.join("\n\n"));
    });

    // Show "Show more" only when the hadith is actually taller than the fold.
    const body = root.querySelector(".body");
    const more = root.querySelector(".more");
    requestAnimationFrame(() => {
      if (!c.collapse || !body) return;
      // Expanded: keep the button so it can fold again. Folded: show it only if a
      // block was actually cut off.
      const cut = [...body.querySelectorAll(".ar, .tr")].some((el) => el.scrollHeight > el.clientHeight + 2);
      if (!this._expanded && !cut) {
        body.classList.remove("clamped");
        return;
      }
      more.hidden = false;
      more.classList.toggle("up", this._expanded);
      more.querySelector("span").textContent = this._expanded ? t.less : t.more;
      more.onclick = () => {
        this._expanded = !this._expanded;
        this._render();
      };
    });
  }

  _paint(inner) {
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${inner}</ha-card>`;
  }
}

const STYLE = `
  :host { display:block; }
  ha-card { padding:16px 18px 12px; overflow:hidden;
    --dh-accent: var(--primary-color, #03a9f4);
    --dh-muted: var(--secondary-text-color, #727272);
    --dh-line: var(--divider-color, rgba(0,0,0,.12)); }
  .i { width:20px; height:20px; fill:currentColor; flex:none; }
  .i.s { width:15px; height:15px; }
  .head { display:flex; align-items:center; gap:12px; margin-bottom:12px; }
  .head.solo { justify-content:flex-end; }
  .badge { width:40px; height:40px; border-radius:50%; display:grid; place-items:center; flex:none;
    color:var(--dh-accent); background:color-mix(in srgb, var(--dh-accent) 14%, transparent); }
  .ht { flex:1; min-width:0; }
  .label { font-size:.78rem; color:var(--dh-muted); }
  .title { font-size:1rem; font-weight:600; line-height:1.3; margin-top:2px; color:var(--primary-text-color); }
  .seg { display:inline-flex; flex:none; border:1px solid var(--dh-line); border-radius:999px; padding:2px; gap:2px; }
  .seg button { all:unset; cursor:pointer; font-size:.75rem; font-weight:600; letter-spacing:.4px;
    padding:4px 10px; border-radius:999px; color:var(--dh-muted); }
  .seg button.on { background:var(--dh-accent); color:var(--text-primary-color, #fff); }
  .seg button:disabled { opacity:.4; cursor:not-allowed; }
  .seg button:focus-visible, .icon:focus-visible, .more:focus-visible, .chip:focus-visible { outline:2px solid var(--dh-accent); outline-offset:2px; }
  .body { position:relative; }
  .body.clamped .ar, .body.clamped .tr { display:-webkit-box; -webkit-box-orient:vertical; overflow:hidden; }
  .body.clamped .ar { -webkit-line-clamp:${AR_LINES}; line-clamp:${AR_LINES}; }
  .body.clamped .tr { -webkit-line-clamp:${TR_LINES}; line-clamp:${TR_LINES}; }
  .ar { font-family:"Daily Hadith Amiri","Amiri","Noto Naskh Arabic","Scheherazade New","Traditional Arabic",serif;
    font-size:1.55rem; line-height:2; text-align:right; color:var(--primary-text-color); white-space:pre-line; }
  .div { height:1px; background:var(--dh-line); margin:12px 0; }
  .tr { font-size:.95rem; line-height:1.65; color:var(--primary-text-color); white-space:pre-line; }
  .narr { color:var(--dh-muted); font-weight:600; }
  .ai { margin-top:8px; font-size:.72rem; color:var(--dh-muted); letter-spacing:.2px; }
  .saw { font-family:"Daily Hadith Amiri","Amiri","Noto Naskh Arabic",serif; font-size:1.15em; }
  .more { all:unset; cursor:pointer; display:inline-flex; align-items:center; gap:2px; margin-top:6px;
    font-size:.85rem; font-weight:500; color:var(--dh-accent); }
  .more[hidden] { display:none; }
  .more.up .i { transform:rotate(180deg); }
  .foot { display:flex; align-items:center; gap:4px; margin-top:12px; min-width:0; }
  .chip { display:inline-flex; align-items:center; gap:6px; min-width:0; max-width:100%; padding:5px 11px;
    border-radius:999px; font-size:.8rem; font-weight:600; text-decoration:none; white-space:nowrap;
    color:var(--dh-accent); background:color-mix(in srgb, var(--dh-accent) 12%, transparent); }
  .chip span { overflow:hidden; text-overflow:ellipsis; }
  .sp { flex:1; }
  .icon { all:unset; cursor:pointer; width:36px; height:36px; border-radius:50%; display:grid; place-items:center;
    color:var(--dh-muted); flex:none; }
  .icon:hover { background:color-mix(in srgb, var(--primary-text-color, #000) 8%, transparent); color:var(--primary-text-color); }
  .spin .i { animation:dh-spin 1s linear infinite; }
  @keyframes dh-spin { to { transform:rotate(360deg); } }
  .empty { color:var(--dh-muted); padding:8px 0; }
`;

/* --- visual editor ---------------------------------------------------------- */
const EDITOR_LABELS = {
  en: {
    entity: "Hadith sensor",
    language: "Starting language",
    auto: "Follow Home Assistant language",
    en: "English",
    translation: "Translation (set in the integration options)",
    show_arabic: "Show Arabic",
    show_translation: "Show translation",
    show_toggle: "Show language switch",
    show_ai_note: "Show \"AI translation\" note",
    show_header: "Show header",
    show_reference: "Show reference link",
    show_refresh: "Show refresh button",
    show_copy: "Show copy button",
    collapse: "Fold long hadith",
  },
  ms: {
    entity: "Sensor hadis",
    language: "Bahasa permulaan",
    auto: "Ikut bahasa Home Assistant",
    en: "English",
    translation: "Terjemahan (ditetapkan dalam pilihan integrasi)",
    show_arabic: "Papar teks Arab",
    show_translation: "Papar terjemahan",
    show_toggle: "Papar suis bahasa",
    show_ai_note: "Papar nota \"Terjemahan AI\"",
    show_header: "Papar tajuk",
    show_reference: "Papar pautan rujukan",
    show_refresh: "Papar butang muat semula",
    show_copy: "Papar butang salin",
    collapse: "Lipat hadis panjang",
  },
};

class DailyHadithCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else this._render();
  }

  _schema(L) {
    return [
      { name: "entity", selector: { entity: { domain: "sensor", integration: "daily_hadith" } } },
      {
        name: "language",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "auto", label: L.auto },
              { value: "en", label: L.en },
              { value: "translation", label: L.translation },
            ],
          },
        },
      },
      {
        type: "grid",
        name: "",
        schema: [
          "show_arabic", "show_translation", "show_toggle", "show_header",
          "show_reference", "show_refresh", "show_copy", "show_ai_note", "collapse",
        ].map((name) => ({ name, selector: { boolean: {} } })),
      },
    ];
  }

  _render() {
    if (!this._hass || !this._config) return;
    const L = EDITOR_LABELS[uiLang(this._hass)];
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => L[s.name] || s.name;
      this._form.addEventListener("value-changed", (ev) => {
        this._config = ev.detail.value;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = this._schema(L);
    this._form.data = {
      entity: DEFAULT_ENTITY, language: "auto", show_arabic: true, show_translation: true, show_toggle: true,
      show_header: true, show_reference: true, show_refresh: true, show_copy: true, show_ai_note: true,
      collapse: true,
      ...this._config,
      language: this._config.language === "ms" ? "translation" : this._config.language || "auto",
    };
  }
}

if (!customElements.get(CARD_TAG)) customElements.define(CARD_TAG, DailyHadithCard);
if (!customElements.get(EDITOR_TAG)) customElements.define(EDITOR_TAG, DailyHadithCardEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === CARD_TAG)) {
  window.customCards.push({
    type: CARD_TAG,
    name: "Daily Hadith",
    description: "Hadith of the day in Arabic with English and a translation in your language.",
    preview: true,
    documentationURL: "https://github.com/zubir2k/homeassistant-dailyhadith",
  });
}

console.info(`%c DAILY-HADITH-CARD %c ${CARD_VERSION} `, "color:#fff;background:#0f766e;font-weight:700", "color:#0f766e");
