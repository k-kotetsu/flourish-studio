(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const pageStep = document.body.dataset.step;

  const storage = {
    get(key, fallback = null) {
      try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, value); } catch { /* 表示は保存なしでも利用できる */ }
    },
  };

  let toastTimer;
  function toast(message) {
    const element = $("#toast");
    if (!element) return;
    element.textContent = message;
    element.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove("show"), 1800);
  }

  async function copyText(text, message) {
    try {
      await navigator.clipboard.writeText(text);
      toast(message);
    } catch {
      const input = document.createElement("textarea");
      input.value = text;
      input.style.position = "fixed";
      input.style.opacity = "0";
      document.body.append(input);
      input.select();
      document.execCommand("copy");
      input.remove();
      toast(message);
    }
  }

  function setupTheme() {
    const saved = storage.get("fs-deep-dive-theme", "auto");
    if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
    $(".theme-button")?.addEventListener("click", () => {
      const modes = ["auto", "light", "dark"];
      const current = document.documentElement.dataset.theme || "auto";
      const next = modes[(modes.indexOf(current) + 1) % modes.length];
      if (next === "auto") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.dataset.theme = next;
      storage.set("fs-deep-dive-theme", next);
      toast(`表示テーマ：${{ auto: "自動", light: "ライト", dark: "ダーク" }[next]}`);
    });
    $(".print-button")?.addEventListener("click", () => window.print());
  }

  function setupReadingProgress() {
    const fill = $(".reading-progress span");
    if (!fill) return;
    const update = () => {
      const max = document.documentElement.scrollHeight - innerHeight;
      fill.style.width = `${max > 0 ? Math.min(100, scrollY / max * 100) : 0}%`;
    };
    addEventListener("scroll", update, { passive: true });
    addEventListener("resize", update);
    update();
  }

  function setupPageSearch() {
    const input = $("#page-search");
    if (!input) return;
    const blocks = $$(".content-section p, .content-section li, .content-section td, .content-section h3");
    const original = new Map(blocks.map((block) => [block, block.innerHTML]));
    const clear = () => original.forEach((html, block) => { block.innerHTML = html; });
    input.addEventListener("input", () => {
      clear();
      const query = input.value.trim();
      if (!query) return;
      const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const pattern = new RegExp(`(${escaped})`, "gi");
      let first;
      for (const block of blocks) {
        if (!block.textContent.toLowerCase().includes(query.toLowerCase())) continue;
        // コードやリンクを壊さないため、単純なテキスト要素だけを強調する。
        if (!block.children.length) block.innerHTML = block.textContent.replace(pattern, "<mark>$1</mark>");
        first ||= block;
      }
      first?.scrollIntoView({ block: "center" });
    });
    document.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "f") {
        event.preventDefault(); input.focus(); input.select();
      }
      if (event.key === "Escape" && document.activeElement === input) { input.value = ""; input.dispatchEvent(new Event("input")); input.blur(); }
    });
  }

  function setupCodeCopy() {
    $$(".copy-code").forEach((button) => button.addEventListener("click", () => {
      const code = $("code", button.closest(".code-card"));
      copyText(code?.textContent || "", "コメント付きコードをコピーしました");
    }));
  }

  function setupStepSwitcher() {
    $("#step-switcher")?.addEventListener("change", (event) => {
      location.href = event.target.value;
    });
  }

  function setupChecklist() {
    if (!pageStep) return;
    const key = `fs-deep-dive-checks-${pageStep}`;
    const saved = new Set(JSON.parse(storage.get(key, "[]")));
    const checks = $$(".check-item input");
    checks.forEach((check, index) => {
      check.checked = saved.has(index);
      check.addEventListener("change", () => {
        const complete = checks.flatMap((item, itemIndex) => item.checked ? [itemIndex] : []);
        storage.set(key, JSON.stringify(complete));
        updateChecklistProgress(checks);
      });
    });
    updateChecklistProgress(checks);
  }

  function updateChecklistProgress(checks) {
    const done = checks.filter((check) => check.checked).length;
    const output = $("#check-progress");
    const progress = $("#check-progress-bar");
    if (output) output.textContent = `${done} / ${checks.length}`;
    if (progress) { progress.max = Math.max(checks.length, 1); progress.value = done; }
  }

  function setupCompletion() {
    if (!pageStep) return;
    const key = "fs-deep-dive-complete";
    const complete = new Set(JSON.parse(storage.get(key, "[]")));
    const button = $(".complete-button");
    if (!button) return;
    const render = () => {
      const done = complete.has(pageStep);
      button.setAttribute("aria-pressed", String(done));
      button.textContent = done ? "この深掘りは読了済み" : "この深掘りを読了にする";
    };
    button.addEventListener("click", () => {
      if (complete.has(pageStep)) complete.delete(pageStep); else complete.add(pageStep);
      storage.set(key, JSON.stringify([...complete]));
      render();
    });
    render();
  }

  function setupSectionNav() {
    const links = $$(".section-nav a");
    const targets = links.map((link) => document.getElementById(link.hash.slice(1))).filter(Boolean);
    if (!targets.length || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (!visible.length) return;
      links.forEach((link) => link.classList.toggle("is-active", link.hash === `#${visible[0].target.id}`));
    }, { rootMargin: "-18% 0px -72% 0px", threshold: 0 });
    targets.forEach((target) => observer.observe(target));
  }

  async function setupMermaid() {
    const nodes = $$(".mermaid");
    if (!nodes.length || !globalThis.mermaid) return;
    try {
      const dark = document.documentElement.dataset.theme === "dark" || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
      globalThis.mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: dark ? "dark" : "base",
        fontFamily: getComputedStyle(document.body).fontFamily,
        themeVariables: dark
          ? { primaryColor: "#243a32", primaryTextColor: "#f0f5f2", primaryBorderColor: "#8dbbab", lineColor: "#8dbbab", secondaryColor: "#1d2924", tertiaryColor: "#17211d" }
          : { primaryColor: "#deebe4", primaryTextColor: "#18241f", primaryBorderColor: "#3f6d61", lineColor: "#3f6d61", secondaryColor: "#f7f7f1", tertiaryColor: "#fffef9" },
        flowchart: { htmlLabels: true, curve: "basis" },
      });
      await globalThis.mermaid.run({ nodes });
    } catch (error) {
      console.warn("Mermaid diagram rendering failed; source remains available.", error);
    }
  }

  function setupIndexFilter() {
    const filter = $("#index-filter");
    if (!filter) return;
    const cards = $$(".step-card");
    const empty = $(".no-results");
    filter.addEventListener("input", () => {
      const query = filter.value.trim().toLowerCase();
      let count = 0;
      cards.forEach((card) => {
        const visible = !query || card.textContent.toLowerCase().includes(query);
        card.hidden = !visible;
        if (visible) count += 1;
      });
      if (empty) empty.hidden = count > 0;
    });
  }

  setupTheme();
  setupReadingProgress();
  setupPageSearch();
  setupCodeCopy();
  setupStepSwitcher();
  setupChecklist();
  setupCompletion();
  setupSectionNav();
  setupIndexFilter();
  setupMermaid();
})();
