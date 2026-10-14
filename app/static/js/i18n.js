/* SafetyAgent interface language (English / 한국어).
   - Static text: elements with data-i18n="key" keep their English HTML in the page; KO[key] replaces it in Korean.
     Attributes: data-i18n-attr="placeholder:key; aria-label:key".
   - Text built in JavaScript: DA.t("key", {vars}) reads EN / KO below.
   - Any button with data-ui-lang="en|ko" switches the language; the choice is remembered in this browser.
   - A page can fix its language with <body data-ui-lang-fixed="en"> (the admin console).
   On a switch, "da:lang" is dispatched on document so pages can re-render their dynamic parts. */
"use strict";
(() => {
  const STORE_KEY = "da_ui_lang";

  /* Strings used from JavaScript (English). */
  const EN = {
    "chat.new": "New chat",
    "chat.none": "No chats yet.",
    "chat.count": "{n} / {max} chats",
    "chat.deleteConfirm": "Delete this chat?",
    "chat.deleteAria": "Delete chat",
    "ex.1": "Before entering a confined space", "ex.2": "Hot work", "ex.3": "Work at height", "ex.4": "Korea vs US",
    "ex.5": "Before a job", "ex.6": "Forklifts (OSHA)",
    "stage.route": "Understanding your question",
    "stage.translate": "Translating the question (KO ↔ EN)",
    "stage.search": "Searching the documents",
    "stage.rerank": "Re-reading the best passages",
    "stage.answer": "Writing the answer with citations",
    "stage.visual": "Drawing the visual",
    "steps.scope": "· searching ~1,900 clauses in 29 documents",
    "steps.secs": "{s} s",
    "steps.done": "✓ Done in {s} s",
    "ans.source1": "{n} source", "ans.sourceN": "{n} sources",
    "ans.in": "Answered in {lang}",
    "ans.readAs": "· read as: “{q}”",
    "ans.readAsTitle": "Your follow-up was read as this question",
    "ans.searched": "Searched as: “{q}” · {w}",
    "ans.searchedTitle": "The agent searched the documents with these words (your question was searched too)",
    "country.kr": "Korean documents", "country.us": "US documents", "country.both": "Korean and US documents",
    "input.ph": "Ask a safety question…",
    "lang.ko": "Korean", "lang.en": "English",
    "ref.head": "Not found",
    "ref.note": "The documents searched don't answer this. Try rephrasing, or ask about a related rule.",
    "err.head": "Error",
    "status.ready": "● Ready · {n} documents",
    "status.error": "Engine error",
    "status.starting": "Starting up…",
    "admin.signedIn": "Admin console · {name}",
    "admin.signedInTitle": "You are signed in as admin",
    "cite.aria": "Source {n}",
    "pop.source": "Source [{n}]",
    "pop.open": "Open in document →",
    "viewer.aria": "Document viewer",
    "viewer.close": "Close",
    "viewer.opening": "Opening the document…",
    "viewer.pages": "{n} pages",
    "viewer.outlined": "Outlined: the passage cited in the answer",
    "viewer.whole": "Whole document",
    "viewer.pageAlt": "Page {n}",
    "vis.steps": "Steps", "vis.checklist": "Checklist", "vis.compare": "Korea vs US", "vis.limits": "Limits",
    "vis.intervals": "Time periods", "vis.checked": "Checked",
    "vis.checkedTitle": "Every element cites a source, and every number appears in that source",
    "vis.notCovered": "Not covered", "vis.allowed": "Allowed", "vis.notAllowed": "Not allowed",
    "vis.logScale": "Bar length on a log scale, so minutes and years fit on one chart.",
    "unit.minutes": "{n} min", "unit.hours": "{n} h", "unit.days": "{n} days", "unit.weeks": "{n} weeks",
    "unit.months": "{n} months", "unit.years": "{n} years",
    "unit.minutes.one": "{n} min", "unit.hours.one": "{n} h", "unit.days.one": "{n} day", "unit.weeks.one": "{n} week",
    "unit.months.one": "{n} month", "unit.years.one": "{n} year",
    "kind.every": "every {v}", "kind.within": "within {v}", "kind.at_least": "at least {v}", "kind.at_most": "at most {v}",
  };

  /* Korean: the JavaScript strings above plus the static text of the landing and chat pages. */
  const KO = {
    "chat.new": "새 채팅",
    "chat.none": "아직 채팅이 없습니다.",
    "chat.count": "채팅 {n} / {max}",
    "chat.deleteConfirm": "이 채팅을 삭제할까요?",
    "chat.deleteAria": "채팅 삭제",
    "ex.1": "밀폐공간 출입 전", "ex.2": "화기 작업", "ex.3": "고소 작업", "ex.4": "한국 vs 미국",
    "ex.5": "작업 전 준비", "ex.6": "지게차 (OSHA)",
    "stage.route": "질문 이해하기",
    "stage.translate": "질문 번역 (한 ↔ 영)",
    "stage.search": "문서 검색",
    "stage.rerank": "관련 구절 정밀 검토",
    "stage.answer": "인용을 포함한 답변 작성",
    "stage.visual": "시각 자료 만들기",
    "steps.scope": "· 문서 29개, 약 1,900개 조항 검색 중",
    "steps.secs": "{s}초",
    "steps.done": "✓ {s}초 만에 완료",
    "ans.source1": "출처 {n}개", "ans.sourceN": "출처 {n}개",
    "ans.in": "{lang}로 답변",
    "ans.readAs": "· 다음 질문으로 이해함: “{q}”",
    "ans.readAsTitle": "후속 질문을 이 질문으로 해석했습니다",
    "ans.searched": "검색어: “{q}” · {w}",
    "ans.searchedTitle": "에이전트가 이 단어로 문서를 검색했습니다 (질문 원문도 함께 검색)",
    "country.kr": "국내 문서", "country.us": "미국 문서", "country.both": "국내·미국 문서",
    "lang.ko": "한국어", "lang.en": "영어",
    "ref.head": "찾을 수 없음",
    "ref.note": "검색한 문서에서 이 질문의 답을 찾지 못했습니다. 표현을 바꾸거나 관련 규정에 대해 질문해 보세요.",
    "err.head": "오류",
    "status.ready": "● 준비됨 · 문서 {n}개",
    "status.error": "엔진 오류",
    "status.starting": "시작하는 중…",
    "admin.signedIn": "관리자 콘솔 · {name}",
    "admin.signedInTitle": "관리자로 로그인되어 있습니다",
    "cite.aria": "출처 {n}",
    "pop.source": "출처 [{n}]",
    "pop.open": "원문에서 보기 →",
    "viewer.aria": "문서 뷰어",
    "viewer.close": "닫기",
    "viewer.opening": "문서를 여는 중…",
    "viewer.pages": "{n}쪽",
    "viewer.outlined": "표시된 부분: 답변에 인용된 구절",
    "viewer.whole": "문서 전체",
    "viewer.pageAlt": "{n}쪽",
    "vis.steps": "단계", "vis.checklist": "체크리스트", "vis.compare": "한국 vs 미국", "vis.limits": "기준값",
    "vis.intervals": "기간·주기", "vis.checked": "검증됨",
    "vis.checkedTitle": "모든 항목에 출처가 있고, 모든 수치가 그 출처에 있습니다",
    "vis.notCovered": "해당 내용 없음", "vis.allowed": "허용", "vis.notAllowed": "허용 안 됨",
    "vis.logScale": "막대 길이는 로그 눈금입니다 (분과 년을 한 그래프에 표시).",
    "unit.minutes": "{n}분", "unit.hours": "{n}시간", "unit.days": "{n}일", "unit.weeks": "{n}주",
    "unit.months": "{n}개월", "unit.years": "{n}년",
    "unit.minutes.one": "{n}분", "unit.hours.one": "{n}시간", "unit.days.one": "{n}일", "unit.weeks.one": "{n}주",
    "unit.months.one": "{n}개월", "unit.years.one": "{n}년",
    "kind.every": "{v}마다", "kind.within": "{v} 이내", "kind.at_least": "최소 {v}", "kind.at_most": "최대 {v}",

    /* chat page */
    "chat.pageTitle": "SafetyAgent · 질문하기",
    "chat.newBtn": "＋ 새 채팅",
    "chat.recent": "최근 채팅",
    "chat.removed": "50개를 넘으면 가장 오래된 채팅이 삭제됩니다.",
    "chat.homeTag": "산업 현장을 위한 AI 안전 도우미",
    "empty.h": "작업 전에 안전 규정을 확인하세요",
    "empty.p": "한국어나 영어로, 평소 쓰는 말로 물어보세요. 모든 답변에 근거 조항이 표시되고, 도움이 될 때는 그래프나 체크리스트도 함께 보여 드립니다.",
    "input.ph": "안전 관련 질문을 입력하세요…",
    "input.aria": "질문",
    "send.aria": "보내기",
    "hint": "SafetyAgent는 참고용 도구이며 법률·안전 자문이 아닙니다. 항상 인용된 출처를 확인하세요.",
    "alang.label": "답변 언어",
    "alang.auto": "자동",
    "alang.autoTitle": "질문과 같은 언어로 답변",
    "ui.aria": "화면 언어",

    /* landing page */
    "home.pageTitle": "SafetyAgent · 현장 근로자를 위한 안전 규정",
    "nav.admin": "관리자", "nav.start": "질문하기",
    "hero.eyebrow": "<i></i>현장 근로자를 위한 안전 규정 · 한국어 &amp; 영어",
    "hero.title": "작업 전에 <em>안전 규정을 확인하세요</em>.",
    "hero.lead": "한국어나 영어로 편하게 물어보세요. SafetyAgent가 한국과 미국의 안전 규정에서 해당 규정을 찾아 정확한 조항과 함께 답하고, 도움이 될 때는 그림이나 체크리스트로 보여 줍니다.",
    "hero.ask": "안전 질문하기 →",
    "hero.trust": "<span>모든 답변에 정확한 조항</span><span>수치를 원문과 대조</span><span>한국어 ↔ 영어</span>",
    "mock.q": "밀폐공간 작업에 안전한 공기 기준은?",
    "mock.a": "산소 농도는 18% 이상 23.5% 미만이어야 하고, 이산화탄소 1.5% 미만, 일산화탄소 30ppm 미만, 황화수소 10ppm 미만이어야 합니다 <span class=\"cite\">1</span> <span class=\"cite\">2</span>.",
    "mock.vt": "밀폐공간 적정공기 기준", "mock.vk": "기준값", "mock.o2": "산소",
    "f1.h": "묻고, 규정을 확인하기",
    "f1.p": "쉬운 질문에 쉬운 답. 번호를 누르면 원문 문서에서 해당 조항을 볼 수 있습니다.",
    "f2.h": "필요할 때는 그림으로",
    "f2.p": "절차, 체크리스트, 기준값, 기한을 그림으로 보여 주고, 한국과 미국 규정을 나란히 비교합니다.",
    "f3.h": "한국어 또는 영어",
    "f3.p": "한국어로 물어도 OSHA 규정을, 영어로 물어도 한국 규정을 찾아 드립니다. 답은 질문한 언어로 나옵니다.",
    "s1": "올바른 조항을 찾은 질문",
    "s2": "한국어 ↔ 영어로 찾은 질문",
    "s3": "규정에 없는 내용에 \"찾을 수 없음\"으로 답변",
    "s4": "한국과 미국 안전 문서",
    "res.caveat": "처음 보는 테스트 질문으로 측정했습니다. 채점은 사람 안전 전문가가 아닌 AI가 했습니다.",
    "footer.note": "SafetyAgent는 참고용 도구입니다. 관리감독자, 안전 전문가, 현장의 안전 절차를 대체하지 않습니다.",
  };

  function initialLang() {
    const fixed = document.body && document.body.dataset.uiLangFixed;
    if (fixed) return fixed;
    try {
      const saved = localStorage.getItem(STORE_KEY);
      if (saved === "en" || saved === "ko") return saved;
    } catch (_) { /* storage blocked: fall back to the browser language */ }
    return (navigator.language || "").toLowerCase().startsWith("ko") ? "ko" : "en";
  }

  DA.lang = initialLang();

  DA.t = (key, vars = {}) => {
    const s = (DA.lang === "ko" && KO[key]) || EN[key] || key;
    return s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  };

  /* Apply the current language to static text and the language switches. */
  DA.applyLang = (root = document) => {
    document.documentElement.lang = DA.lang;
    root.querySelectorAll("[data-i18n]").forEach((el) => {
      if (el.dataset.en === undefined) el.dataset.en = el.innerHTML;  // the page's own English
      const ko = KO[el.dataset.i18n];
      el.innerHTML = DA.lang === "ko" && ko ? ko : el.dataset.en;
    });
    root.querySelectorAll("[data-i18n-attr]").forEach((el) => {
      for (const pair of el.dataset.i18nAttr.split(";")) {
        const [attr, key] = pair.split(":").map((x) => x.trim());
        if (!attr || !key) continue;
        const store = `en${attr.replace(/(^|-)(\w)/g, (m, d, c) => c.toUpperCase())}`;
        if (el.dataset[store] === undefined) el.dataset[store] = el.getAttribute(attr) || "";
        el.setAttribute(attr, DA.lang === "ko" && KO[key] ? KO[key] : el.dataset[store]);
      }
    });
    document.querySelectorAll("[data-ui-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.uiLang === DA.lang)));
  };

  DA.setLang = (lang) => {
    if (lang === DA.lang || (lang !== "en" && lang !== "ko")) return;
    DA.lang = lang;
    try { localStorage.setItem(STORE_KEY, lang); } catch (_) { /* not remembered; still switches */ }
    DA.applyLang();
    document.dispatchEvent(new CustomEvent("da:lang", { detail: { lang } }));
  };

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-ui-lang]");
    if (b) DA.setLang(b.dataset.uiLang);
  });
  DA.applyLang();
})();
