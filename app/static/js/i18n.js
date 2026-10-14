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
    "ex.1": "Korean rule", "ex.2": "Visual", "ex.3": "Korea vs US", "ex.4": "Job plan", "ex.5": "Notice", "ex.6": "English → Korean guide",
    "stage.route": "Understanding your request",
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
    "ex.1": "국내 규칙", "ex.2": "시각 자료", "ex.3": "한국 vs 미국", "ex.4": "작업 계획", "ex.5": "게시물", "ex.6": "영어 → 국내 가이드",
    "stage.route": "요청 내용 파악",
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
    "empty.h": "무엇을 도와드릴까요?",
    "empty.p": "한국과 미국의 안전 규정에 대해 한국어나 영어로 질문하세요. 모든 답변에 근거 조항이 표시됩니다. 규정을 시각 자료로 보여 주고, 한국과 미국 기준을 비교하고, 작업 전 점검 계획을 세우고, 인쇄용 게시물 초안도 만들 수 있습니다.",
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
    "home.pageTitle": "SafetyAgent · 산업 현장을 위한 AI 안전 도우미",
    "nav.features": "기능", "nav.how": "작동 방식", "nav.results": "성능",
    "nav.admin": "관리자", "nav.start": "시작하기",
    "hero.eyebrow": "<i></i>AI 안전 도우미 · 한국 &amp; 미국 규정",
    "hero.title": "안전 규정, <em>정확한 조항</em>으로 답합니다.",
    "hero.lead": "SafetyAgent는 한국과 미국의 안전 규정으로 질문에 답하고, 시각 자료로 설명하고, 작업 전 점검 계획을 세우고, 인쇄할 수 있는 게시물을 만듭니다. 모든 줄은 근거 조항으로 연결되고, 수치는 보여 드리기 전에 원문과 대조해 확인합니다.",
    "hero.ask": "안전 질문하기 →",
    "hero.see": "측정 결과 보기",
    "hero.trust": "<span>조항 단위 인용</span><span>수치를 원문과 대조</span><span>한국어 ↔ 영어</span>",
    "mock.q": "밀폐공간 작업에 안전한 공기 기준은?",
    "mock.a": "산소 농도는 18% 이상 23.5% 미만이어야 하고, 이산화탄소 1.5% 미만, 일산화탄소 30ppm 미만, 황화수소 10ppm 미만이어야 합니다 <span class=\"cite\">1</span> <span class=\"cite\">2</span>.",
    "mock.vt": "밀폐공간 적정공기 기준", "mock.vk": "기준값", "mock.o2": "산소",
    "mock.pt": "밀폐공간: 먼저 공기를 측정하세요", "mock.p1": "출입 전 산소·유해가스 측정", "mock.p2": "외부에 감시인 배치",
    "mock.pok": "✓ 승인됨",
    "problem.kicker": "문제",
    "problem.h": "규정은 있습니다. 찾고, 설명하고, 게시하는 데 몇 시간이 걸릴 뿐.",
    "problem.sub": "현장 안전은 산업안전보건법, 안전보건규칙, KOSHA 가이드, 그리고 해외 프로젝트에서는 OSHA 기준에 따라 움직입니다. 관리감독자는 작업 전에 정확한 요구사항이 필요하고, 근로자는 쉬운 말로, 때로는 다른 언어로 알아야 합니다. 요구사항 하나를 놓치면 생명이 위험해지고, 회사는 법적 책임을 질 수 있습니다.",
    "feat.kicker": "SafetyAgent가 하는 일",
    "feat.h": "하나의 도우미로: 묻고, 보고, 계획하고, 게시하기.",
    "feat.sub": "단순한 챗봇이 아닌 에이전트입니다. 요청에 맞는 도구를 고르고, 규정을 검색하고, 결과를 만든 뒤, 보여 드리기 전에 검증합니다.",
    "f1.h": "근거가 있는 답변",
    "f1.p": "모든 문장에 문서, 조항, 페이지를 인용합니다. 번호에 마우스를 올리면 조항을, 클릭하면 원문 PDF에서 표시된 위치를 볼 수 있습니다.",
    "f2.h": "시각 자료로 설명",
    "f2.p": "절차는 단계 흐름으로, 요구사항은 체크리스트로, 기준값은 눈금 위에, 기한은 타임라인으로 보여 줍니다.",
    "f3.h": "한국과 미국 기준 비교",
    "f3.p": "한국어로 질문하고 OSHA 규정을 받거나, 두 나라의 요구사항을 한 표로 비교할 수 있습니다.",
    "f4.h": "작업 계획",
    "f4.p": "내일 할 작업을 알려 주면, 위험요인을 찾아 각각 검색하고 허가, 안전대책, 점검 항목, 보호구, TBM 전달 내용을 정리합니다.",
    "f5.h": "인쇄용 게시물",
    "f5.p": "포스터, 리플릿, 메신저 카드, TBM 일지를 만듭니다. 조항으로 연결되는 QR 코드와 외국인 근로자를 위한 제2언어를 넣고, 게시 전에 사람이 승인합니다.",
    "f6.h": "검증되지 않으면 보여 주지 않습니다",
    "f6.p": "모든 줄에는 출처가 있어야 하고, 모든 수치는 그 출처에 있어야 합니다. 문서에 없는 내용이면 \"찾을 수 없음\"으로 답합니다.",
    "how.kicker": "작동 방식",
    "how.h": "네 단계, 진행 상황이 모두 보입니다.",
    "s1.h": "이해", "s1.p": "짧은 모델 호출로 필요한 것을 판단합니다: 답변, 시각 자료, 비교, 작업 계획, 게시물.",
    "s2.h": "검색", "s2.p": "두 언어로 된 29개 문서에서 키워드 검색과 의미 검색을 하고, 재순위 모델이 가장 관련 있는 구절을 다시 읽습니다.",
    "s3.h": "작성", "s3.p": "모델은 그 구절만으로 작성하고 각각을 인용합니다. 작업 계획은 위험요인마다 따로 검색합니다.",
    "s4.h": "검증", "s4.p": "출처가 없거나 출처에 없는 수치가 들어간 줄은 지웁니다. 게시물은 사람의 승인을 기다립니다.",
    "corp.1": "산업안전보건법", "corp.2": "산업안전보건기준에 관한 규칙 (674조)", "corp.3": "사업장 위험성평가에 관한 지침",
    "corp.4": "KOSHA 가이드 16종", "corp.5": "OSHA 기준 9개 (미국)", "corp.6": "OSHA PSM 해설서 (미국)",
    "mod.kicker": "모듈",
    "mod.h": "먼저 만들고 측정했습니다. 다음은 카메라.",
    "mod.sub": "'구축됨' 모듈은 작동하며 평가를 마쳤습니다. '계획' 모듈은 로드맵에 있으며 아직 사용할 수 없습니다.",
    "chip.built": "구축됨", "chip.planned": "계획",
    "m1.p": "한국어나 영어로, 두 나라 규정에 걸쳐 인용이 있는 답변 또는 솔직한 \"찾을 수 없음\".",
    "m2.p": "단계 흐름, 체크리스트, 기준값 눈금, 타임라인, 한·미 비교표. 모든 항목에 출처가 있고 검증됩니다.",
    "m3.p": "TBM 전달 내용이 포함된 작업 계획, QR 코드·제2언어·승인 절차가 있는 인쇄용 게시물.",
    "m4.p": "현장 카메라로 보호구 미착용과 위험구역 출입을 감지하고, 모든 경보를 위반한 규정과 연결합니다.",
    "m5.p": "작업 장소 사진을 올리면 보이는 위험요인과 해당 규정을 알려 줍니다.",
    "m6.p": "사고가 나기 전에 경고하는 영상 모델. 몇 초 먼저 경고하는지로 측정합니다.",
    "res.kicker": "신뢰할 수 있는 이유",
    "res.h": "본 적 없는 질문으로 측정했습니다.",
    "res.sub": "문서와 대조해 작성·검증한 이중언어 질문으로, 시스템 조정에는 한 번도 사용하지 않았습니다.",
    "s1": "답할 수 있는 질문에서 상위 5개 결과 안에 올바른 조항 포함",
    "s2": "언어를 넘나드는 질문(한국어 ↔ 영어)에서 올바른 조항 찾음",
    "s3": "문서 밖의 질문에 올바르게 \"찾을 수 없음\"으로 답변",
    "s4": "에이전트가 요청을 올바른 도구로 보낸 비율",
    "res.caveat": "참고: 테스트 세트가 작고, 질문과 채점은 사람 안전 전문가가 아닌 AI가 검토했습니다.",
    "final.h": "규정을 손에 들고, 안전하게 일하세요.",
    "final.p": "조항 근거가 있는 답변, 시각 자료, 작업 계획, 게시물. 또는 솔직한 \"찾을 수 없음\".",
    "final.btn": "시작하기 →",
    "footer.note": "SafetyAgent는 참고용 도구입니다. 안전 전문가, 법률 자문, 현장의 공식 안전 절차를 대체하지 않습니다.",
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
