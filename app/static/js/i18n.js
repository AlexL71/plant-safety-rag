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
    "ex.5": "Plan tomorrow's job", "ex.6": "Make a site notice",
    "stage.route": "Understanding your question",
    "stage.condense": "Understanding your follow-up",
    "stage.query": "Choosing search words",
    "stage.plan": "Splitting the job into hazards",
    "stage.translate": "Translating the question (KO ↔ EN)",
    "stage.search": "Searching the documents",
    "stage.rerank": "Re-reading the best passages",
    "stage.answer": "Writing the answer with citations",
    "stage.visual": "Drawing the visual",
    "stage.notice": "Drafting the notice",
    "stage.check": "Checking sources and numbers",
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
    "mode.auto": "Auto", "mode.answer": "Answer", "mode.answerShort": "Q&A", "mode.visual": "Visual", "mode.compare": "KR vs US",
    "mode.task_plan": "Job plan", "mode.notice": "Notice", "mode.chitchat": "Chat",
    "ph.auto": "Ask a safety question, or describe a job…",
    "ph.answer": "Ask a safety question…",
    "ph.visual": "What should I explain as a visual?",
    "ph.compare": "What should I compare between Korea and the US?",
    "ph.task_plan": "Describe the job: what, where, when…",
    "ph.notice": "What should the notice be about?",
    "agent.routedTitle": "Tool chosen by the agent ({r})",
    "act.visual": "Show as a visual", "act.notice": "Make a notice", "act.tbm": "Make a TBM sheet",
    "act.print": "Print checklist", "act.working": "Working…",
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
    "plan.kind": "Job safety plan", "plan.hazards": "Hazards and controls", "plan.permits": "Permits and procedures",
    "plan.before_start": "Before you start", "plan.ppe": "Protective equipment", "plan.tbm": "TBM briefing (read out)",
    "plan.notCovered": "Not covered by the documents",
    "notice.drafted": "Notice drafted", "notice.draftedNote": "Edit it, add a second language, then send it for approval.",
    "notice.open": "Open in editor", "notice.warnTitle": "A number here is not in the cited source: {n}",
    "notice.back": "Back-translation: {t}",
    "tpl.poster": "Poster (A4)", "tpl.leaflet": "Leaflet (A5)", "tpl.card": "Card (messenger)", "tpl.tbm": "TBM sheet (A4)",
    "notices.none": "No notices yet.", "notices.approved": "Approved", "notices.draft": "Draft",
    "notices.discard": "Discard your unsaved edits?", "notices.noSecond": "No second language",
    "notices.translating": "Translating…", "notices.deleteConfirm": "Delete this notice?",
    "notices.cNumbers": "Sources and numbers", "notices.cWarn": "{n} line(s) need a look",
    "notices.cWarnNote": "A number is not in the cited source, or the source is missing. Fix the text or remove the line.",
    "notices.cOk": "All lines cite a source", "notices.cOkNote": "Every number appears in its cited clause.",
    "notices.cTr": "Second language", "notices.cTrBad": "{n} of {t} lines changed a number",
    "notices.cTrOk": "Numbers kept in all {t} lines",
    "notices.cTrNote": "Machine translation. The back-translation lets you check the meaning without reading the language.",
    "notices.cBack": "Show the back-translation", "notices.cSources": "Sources", "notices.cApproval": "Approval",
    "notices.approvedBy": "Approved by {u} (version {v})", "notices.needsApproval": "Waiting for approval",
    "notices.needsApprovalNote": "An admin checks the notice against its sources and approves it. Edits after approval need a new approval.",
    "notices.cShare": "Share", "notices.copy": "Copy link", "notices.copied": "Copied",
    "notices.shareAfter": "The share link and QR code work after approval.",
    "notices.unavailable": "This notice is not available. It may not be approved yet, or it was removed.",
  };

  /* Korean: the JavaScript strings above plus the static text of the landing, chat and notice pages. */
  const KO = {
    "chat.new": "새 채팅",
    "chat.none": "아직 채팅이 없습니다.",
    "chat.count": "채팅 {n} / {max}",
    "chat.deleteConfirm": "이 채팅을 삭제할까요?",
    "chat.deleteAria": "채팅 삭제",
    "ex.1": "밀폐공간 출입 전", "ex.2": "화기 작업", "ex.3": "고소 작업", "ex.4": "한국 vs 미국",
    "ex.5": "내일 작업 계획", "ex.6": "현장 게시물 만들기",
    "stage.route": "질문 이해하기",
    "stage.condense": "이전 대화 맥락 파악",
    "stage.query": "검색어 정리",
    "stage.plan": "작업을 위험요인별로 나누기",
    "stage.translate": "질문 번역 (한 ↔ 영)",
    "stage.search": "문서 검색",
    "stage.rerank": "관련 구절 정밀 검토",
    "stage.answer": "인용을 포함한 답변 작성",
    "stage.visual": "시각 자료 만들기",
    "stage.notice": "게시물 초안 작성",
    "stage.check": "근거와 수치 확인",
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
    "mode.label": "모드", "mode.auto": "자동", "mode.autoTitle": "어떤 도구를 쓸지 에이전트가 판단합니다", "mode.answer": "답변",
    "mode.answerShort": "질문", "mode.visual": "시각화", "mode.compare": "한·미 비교", "mode.task_plan": "작업 계획",
    "mode.notice": "게시물", "mode.chitchat": "대화",
    "ph.auto": "안전 질문을 하거나 작업 내용을 알려 주세요…",
    "ph.answer": "안전 관련 질문을 입력하세요…",
    "ph.visual": "어떤 내용을 시각 자료로 설명할까요?",
    "ph.compare": "한국과 미국의 어떤 기준을 비교할까요?",
    "ph.task_plan": "작업 내용을 알려 주세요: 무엇을, 어디서, 언제…",
    "ph.notice": "어떤 주제의 게시물을 만들까요?",
    "agent.routedTitle": "에이전트가 선택한 도구 ({r})",
    "act.visual": "시각 자료로 보기", "act.notice": "게시물 만들기", "act.tbm": "TBM 일지 만들기",
    "act.print": "체크리스트 인쇄", "act.working": "처리 중…",
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
    "plan.kind": "작업 안전 계획", "plan.hazards": "위험요인과 안전대책", "plan.permits": "필요한 허가·절차",
    "plan.before_start": "작업 전 확인", "plan.ppe": "보호구", "plan.tbm": "TBM 전달 내용 (읽어 주기)",
    "plan.notCovered": "문서에서 다루지 않는 부분",
    "notice.drafted": "게시물 초안 작성됨", "notice.draftedNote": "내용을 고치고 제2언어를 추가한 뒤 승인을 요청하세요.",
    "notice.open": "편집기에서 열기", "notice.warnTitle": "이 수치가 인용된 출처에 없습니다: {n}",
    "notice.back": "역번역: {t}",
    "tpl.poster": "포스터 (A4)", "tpl.leaflet": "리플릿 (A5)", "tpl.card": "카드 (메신저)", "tpl.tbm": "TBM 일지 (A4)",
    "notices.none": "아직 게시물이 없습니다.", "notices.approved": "승인됨", "notices.draft": "초안",
    "notices.discard": "저장하지 않은 수정 내용을 버릴까요?", "notices.noSecond": "제2언어 없음",
    "notices.translating": "번역 중…", "notices.deleteConfirm": "이 게시물을 삭제할까요?",
    "notices.cNumbers": "출처와 수치", "notices.cWarn": "확인이 필요한 줄 {n}개",
    "notices.cWarnNote": "수치가 인용된 출처에 없거나 출처가 없습니다. 내용을 고치거나 해당 줄을 지우세요.",
    "notices.cOk": "모든 줄에 출처가 있습니다", "notices.cOkNote": "모든 수치가 인용된 조항에 있습니다.",
    "notices.cTr": "제2언어", "notices.cTrBad": "{t}줄 중 {n}줄에서 수치가 바뀌었습니다",
    "notices.cTrOk": "{t}줄 모두 수치가 유지되었습니다",
    "notices.cTrNote": "기계 번역입니다. 역번역을 보면 그 언어를 몰라도 뜻을 확인할 수 있습니다.",
    "notices.cBack": "역번역 보기", "notices.cSources": "근거 조항", "notices.cApproval": "승인",
    "notices.approvedBy": "{u} 승인 (버전 {v})", "notices.needsApproval": "승인 대기 중",
    "notices.needsApprovalNote": "관리자가 출처와 대조해 확인한 뒤 승인합니다. 승인 후 수정하면 다시 승인을 받아야 합니다.",
    "notices.cShare": "공유", "notices.copy": "링크 복사", "notices.copied": "복사됨",
    "notices.shareAfter": "공유 링크와 QR 코드는 승인 후에 열립니다.",
    "notices.unavailable": "이 게시물을 볼 수 없습니다. 아직 승인되지 않았거나 삭제되었습니다.",

    /* chat page */
    "chat.pageTitle": "SafetyAgent · 질문하기",
    "chat.newBtn": "＋ 새 채팅",
    "chat.recent": "최근 채팅",
    "chat.removed": "50개를 넘으면 가장 오래된 채팅이 삭제됩니다.",
    "chat.homeTag": "산업 현장을 위한 AI 안전 도우미",
    "nav.notices": "안전 게시물",
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

    /* notices page */
    "notices.pageTitle": "SafetyAgent · 안전 게시물",
    "notices.newTitle": "새 게시물",
    "notices.topicPh": "주제, 예: 창고 지게차 안전",
    "notices.create": "초안 만들기",
    "notices.mine": "내 게시물",
    "notices.backChat": "← 채팅으로 돌아가기",
    "notices.save": "수정 저장",
    "notices.print": "인쇄 / PDF",
    "notices.png": "이미지",
    "notices.empty": "왼쪽에서 주제로 게시물을 만들거나, 채팅 답변에서 \"게시물 만들기\"를 누르세요. 내용을 고치고 제2언어를 추가하고, 관리자 승인 후 인쇄하거나 공유할 수 있습니다.",

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
    "mock.pt": "밀폐공간: 먼저 공기를 측정하세요", "mock.p1": "출입 전 산소·유해가스 측정", "mock.p2": "외부에 감시인 배치",
    "mock.pok": "✓ 승인됨",
    "f1.h": "묻고, 규정을 확인하기",
    "f1.p": "쉬운 질문에 쉬운 답. 번호를 누르면 원문 문서에서 해당 조항을 볼 수 있습니다.",
    "f2.h": "필요할 때는 그림으로",
    "f2.p": "절차, 체크리스트, 기준값, 기한을 그림으로 보여 주고, 한국과 미국 규정을 나란히 비교합니다.",
    "f3.h": "현장에 공유하기",
    "f3.p": "답변을 게시물이나 TBM 일지로 만들고, 관리감독자가 승인한 뒤 게시합니다.",
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
