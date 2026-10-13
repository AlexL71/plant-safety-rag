/* DocAgent interface language (English / 한국어).
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
    "ex.1": "Korean regulation", "ex.2": "Korean → US standard", "ex.3": "English → Korean guide", "ex.4": "US PSM",
    "stage.condense": "Understanding your follow-up",
    "stage.translate": "Translating the question (KO ↔ EN)",
    "stage.search": "Searching the documents",
    "stage.rerank": "Re-reading the best passages",
    "stage.answer": "Writing the answer with citations",
    "steps.scope": "· searching ~1,155 clauses in 10 documents",
    "steps.secs": "{s} s",
    "steps.done": "✓ Done in {s} s",
    "ans.source1": "{n} source", "ans.sourceN": "{n} sources",
    "ans.in": "Answered in {lang}",
    "ans.readAs": "· read as: “{q}”",
    "ans.readAsTitle": "Your follow-up was read as this question",
    "lang.ko": "Korean", "lang.en": "English",
    "ref.head": "Not found",
    "ref.note": "The documents searched don't answer this. Try rephrasing, or ask about a related clause.",
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
  };

  /* Korean: the JavaScript strings above plus the static text of the landing and chat pages. */
  const KO = {
    "chat.new": "새 채팅",
    "chat.none": "아직 채팅이 없습니다.",
    "chat.count": "채팅 {n} / {max}",
    "chat.deleteConfirm": "이 채팅을 삭제할까요?",
    "chat.deleteAria": "채팅 삭제",
    "ex.1": "국내 법규", "ex.2": "한국어 → 미국 표준", "ex.3": "영어 → 국내 가이드", "ex.4": "미국 PSM",
    "stage.condense": "이전 대화 맥락 파악",
    "stage.translate": "질문 번역 (한 ↔ 영)",
    "stage.search": "문서 검색",
    "stage.rerank": "관련 구절 정밀 검토",
    "stage.answer": "인용을 포함한 답변 작성",
    "steps.scope": "· 문서 10개, 약 1,155개 조항 검색 중",
    "steps.secs": "{s}초",
    "steps.done": "✓ {s}초 만에 완료",
    "ans.source1": "출처 {n}개", "ans.sourceN": "출처 {n}개",
    "ans.in": "{lang}로 답변",
    "ans.readAs": "· 다음 질문으로 이해함: “{q}”",
    "ans.readAsTitle": "후속 질문을 이 질문으로 해석했습니다",
    "lang.ko": "한국어", "lang.en": "영어",
    "ref.head": "찾을 수 없음",
    "ref.note": "검색한 문서에서 이 질문의 답을 찾지 못했습니다. 표현을 바꾸거나 관련 조항에 대해 질문해 보세요.",
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

    /* chat page */
    "chat.pageTitle": "DocAgent · 질문하기",
    "chat.newBtn": "＋ 새 채팅",
    "chat.recent": "최근 채팅",
    "chat.removed": "50개를 넘으면 가장 오래된 채팅이 삭제됩니다.",
    "chat.homeTag": "EPC 문서를 위한 AI 에이전트",
    "empty.h": "무엇을 찾고 계신가요?",
    "empty.p": "공정안전 표준에 대해 한국어나 영어로 질문하세요. 모든 답변에는 근거 조항이 인용됩니다. 번호에 마우스를 올리면 내용을, 클릭하면 원문에서 위치를 볼 수 있습니다.",
    "input.ph": "질문을 입력하세요… (예: 안전밸브 검사 주기는?)",
    "input.aria": "질문",
    "send.aria": "보내기",
    "hint": "DocAgent는 참고용 도구이며 법률·안전 자문이 아닙니다. 항상 인용된 출처를 확인하세요.",
    "alang.label": "답변 언어",
    "alang.auto": "자동",
    "alang.autoTitle": "질문과 같은 언어로 답변",
    "ui.aria": "화면 언어",

    /* landing page */
    "home.pageTitle": "DocAgent · EPC 문서를 위한 AI 에이전트",
    "nav.product": "제품", "nav.modules": "모듈", "nav.results": "성능",
    "nav.admin": "관리자", "nav.start": "시작하기",
    "hero.eyebrow": "<i></i>EPC 문서를 위한 AI 에이전트 · 한국어 &amp; 영어",
    "hero.title": "<em>EPC 프로젝트 문서</em>를 위한 AI 에이전트.",
    "hero.lead": "DocAgent는 프로젝트 문서를 한곳에 모아, 엔지니어가 평소 쓰는 말로 질문하고 문서를 확인하고 검토를 준비할 수 있게 합니다. 모든 답변은 근거가 된 조항으로 바로 연결됩니다.",
    "hero.ask": "문서에 질문하기 →",
    "hero.see": "측정 결과 보기",
    "hero.trust": "<span>조항 단위 인용</span><span>모르면 솔직하게 \"찾을 수 없음\"</span><span>한국어 ↔ 영어</span>",
    "mock.meta": "5.5 허가서의 보존 · p. 8 · 한국어",
    "mock.q": "완료된 작업허가서는 얼마나 보관해야 하나요?",
    "mock.a": "작업허가서는 <strong>1년</strong>, 밀폐공간 출입허가서는 <strong>3년</strong> 보관합니다 <span class=\"cite\">2</span>. 허가서는 작업 후 최소 30일간 현장에 비치한 뒤, 모니터링과 감사를 위해 보관합니다 <span class=\"cite\">1</span>.",
    "problem.kicker": "문제",
    "problem.h": "답은 수천 개의 문서 어딘가에 있습니다.",
    "problem.sub": "EPC 프로젝트에서 엔지니어링 질문의 답은 사양서, 표준, 법규, 데이터시트, 벤더 문서와 그 개정본에 흩어져 있고, 여러 언어로 작성된 경우도 많습니다. 엔지니어는 올바른 조항을 찾는 데 몇 시간을 쓰고, 놓친 요구사항은 비용과 안전 문제로 이어집니다.",
    "what.kicker": "DocAgent가 하는 일",
    "what.h": "단순한 챗봇이 아닌 에이전트.",
    "what.sub": "챗봇은 질문 하나에 답합니다. 에이전트는 여러 단계를 계획하고 도구를 사용합니다. 문서를 검색하고, 필요한 조항을 읽고, 비교한 뒤 결과를 준비합니다.",
    "f1.h": "근거가 있는 답변",
    "f1.p": "모든 문장에 문서, 조항, 페이지를 인용합니다. 번호에 마우스를 올리면 해당 구절을, 클릭하면 원문에서 표시된 위치를 볼 수 있습니다.",
    "f2.h": "추측 대신 \"찾을 수 없음\"",
    "f2.p": "문서에 없는 내용이면 그렇다고 답하고, 확인한 가장 가까운 구절을 보여줍니다.",
    "f3.h": "언어를 넘나드는 검색",
    "f3.p": "한국어로 질문하고 영어 표준에서 답을 받을 수 있습니다. 반대도 가능합니다.",
    "f4.h": "기존 시스템과 연동",
    "f4.p": "CDE나 문서관리시스템과 연결하도록 설계되었습니다. 기존 시스템을 바꿀 필요가 없습니다.",
    "f5.h": "최종 판단은 사람이",
    "f5.p": "에이전트는 코멘트, 점검 결과, 상태 제안을 준비하고 사람이 승인합니다. 승인은 공식 프로젝트 기록으로 남습니다.",
    "f6.h": "가정이 아닌 측정",
    "f6.p": "이중언어 테스트 세트로 검색 방법을 비교하고, 답변이 출처에 충실한지 평가했습니다.",
    "mod.kicker": "모듈",
    "mod.h": "하나의 플랫폼, 단계적으로 구축.",
    "mod.sub": "'구축됨' 모듈은 작동하며 평가를 마쳤습니다. '계획' 모듈은 로드맵에 있으며 아직 사용할 수 없습니다.",
    "chip.built": "구축됨", "chip.core": "구축됨 · 핵심", "chip.planned": "계획", "chip.works": "현재 사용 가능",
    "m1.p": "한국어나 영어로 질문하고, 조항 단위 인용이 포함된 답변 또는 \"찾을 수 없음\"을 받습니다.",
    "m2.p": "모든 출처와 언어에 걸쳐 문서나 조항을 찾습니다.",
    "m3.p": "모든 프로젝트 문서를 하나의 목록으로 관리하고 SharePoint, Aconex, ProjectWise, 공유 폴더와 연결합니다.",
    "m4.p": "데이터시트나 벤더 문서를 사양서·표준과 대조해 불일치 항목을 정리합니다.",
    "m5.p": "검토, 승인, 개정을 추적하고 승인용 코멘트 시트 초안을 작성합니다.",
    "t1.ask": "\"안전밸브는 어디에 설치해야 하나요?\"",
    "t1.does": "법규와 KOSHA 가이드를 검색하고 조항을 인용해 답합니다.",
    "t2.ask": "\"이 펌프 데이터시트가 우리 사양을 만족하나요?\"",
    "t2.does": "사양서를 찾고 데이터시트를 읽은 뒤 값을 비교해 불일치 항목을 정리합니다.",
    "t3.ask": "\"Rev B와 Rev C 사이에 무엇이 바뀌었나요?\"",
    "t3.does": "두 개정본을 가져와 비교하고 변경 사항을 요약합니다.",
    "t4.ask": "\"이 벤더 문서에 대한 검토 코멘트를 준비해 줘\"",
    "t4.does": "표준과 대조해 확인하고, 승인할 수 있도록 코멘트 시트 초안을 작성합니다.",
    "res.kicker": "신뢰할 수 있는 이유",
    "res.h": "조정에 쓰지 않은 질문으로 측정했습니다.",
    "res.sub": "시스템 조정에 한 번도 사용하지 않은, 공정안전 표준에 관한 이중언어 질문 40개로 테스트했습니다.",
    "s1": "답할 수 있는 질문에서 상위 5개 결과 안에 올바른 조항 포함",
    "s2": "언어를 넘나드는 질문(한국어 ↔ 영어)을 올바른 조항으로 답변",
    "s3": "문서 밖의 질문에 올바르게 \"찾을 수 없음\"으로 답변 (잘못된 거절 1건)",
    "s4": "출처에 충실한 답변: 지어낸 사실 없음",
    "res.caveat": "참고: 테스트 세트가 작고, 채점은 사람 전문가가 아닌 AI가 검토했습니다.",
    "final.h": "문서에 무엇이든 물어보세요.",
    "final.p": "조항 근거가 있는 답변, 또는 솔직한 \"찾을 수 없음\"을 받으세요.",
    "final.btn": "시작하기 →",
    "footer.note": "DocAgent는 참고용 도구입니다. 엔지니어링 판단, 법률 자문, 공식 안전 검토를 대체하지 않습니다.",
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
