# Phase 2 hand test (setup D)

Model `gemini-3.8-flash`, temperature 0.0, thinking None, rerank candidates 10, min rerank score 0.01

## Q1. 안전밸브는 어떤 설비에 설치해야 하나요?

*Expected:* KO→KO: 안전보건규칙 제261조 / KOSHA C-C-11 4

과압에 따른 폭발을 방지하기 위하여 다음의 설비에 안전밸브 또는 파열판을 설치하여야 합니다 [1]:

1. 압력용기(안지름이 150밀리미터 이하인 압력용기는 제외하며, 관형 열교환기의 경우에는 관의 파열로 인하여 상승한 압력이 압력용기의 최고사용압력을 초과할 우려가 있는 경우만 해당) [1][2]
2. 정변위 압축기 [1][2]
3. 정변위 펌프(토출측에 차단밸브가 설치된 것만 해당) [1][2]
4. 배관(2개 이상의 밸브에 의하여 차단되어 대기온도에서 액체의 열팽창에 의하여 파열될 우려가 있는 것으로 한정) [1][2]
5. 그 밖의 화학설비 및 그 부속설비로서 해당 설비의 최고사용압력을 초과할 우려가 있는 것 [1]

또한, 다단형 압축기 또는 직렬로 접속된 공기압축기에는 각 단 또는 각 공기압축기별로 설치하여야 합니다 [1]. 아울러 급성 독성물질이 지속적으로 외부에 유출될 수 있는 화학설비 및 그 부속설비에는 파열판과 안전밸브를 직렬로 설치하여야 합니다 [4].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | 산업안전보건기준에 관한 규칙 (고용노동부령 제450호, 시행 2026-03-02), 제261조 ①–②, p. 46 | 0.997 | yes |
| 2 | 공정용 안전밸브에 관한 기술지원규정, 4, pp. 5–6 | 0.994 | yes |
| 3 | 공정용 안전밸브에 관한 기술지원규정, 2, p. 4 | 0.992 |  |
| 4 | 산업안전보건기준에 관한 규칙 (고용노동부령 제450호, 시행 2026-03-02), 제263조, p. 46 | 0.992 | yes |
| 5 | 공정용 안전밸브에 관한 기술지원규정, 1, p. 4 | 0.988 |  |

search 48.9s (rerank 46.4s) | LLM cached | thinking tokens 900 | refused: no

## Q2. 공정위험성평가는 몇 년마다 다시 해야 하나요?

*Expected:* KO→EN cross-lingual: 29 CFR 1910.119(e)(6), at least every 5 years

공정위험성평가는 초기 공정위험성평가 완료 후 적어도 매 5(5)년마다 갱신 및 재확인(updated and revalidated)되어야 합니다 [2][4]. 

이는 공정위험성평가가 현재 공정과 일치함을 보장하기 위한 것이며, 29 CFR 1910.119 (e)(4)의 요건을 충족하는 팀에 의해 수행되어야 합니다 [2].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | 연속공정의 위험과 운전분석(HAZOP) 기법에 관한 기술지원규정, 5.1, p. 7 | 0.022 |  |
| 2 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), (e)(3)–(6), p. 4 | 0.021 | yes |
| 3 | 연속공정의 위험과 운전분석(HAZOP) 기법에 관한 기술지원규정, 6.3 (2)–(4), p. 12 | 0.013 |  |
| 4 | Process Safety Management, OSHA 3132 (2000, reprinted), Process Hazard Analysis (part 1/2), pp. 13–14 | 0.004 | yes |
| 5 | 연속공정의 위험과 운전분석(HAZOP) 기법에 관한 기술지원규정, 7, pp. 15–16 | 0.004 |  |

search 19.4s (rerank 19.0s) | LLM cached | thinking tokens 313 | refused: no

## Q3. 변경요소관리 절차에는 어떤 내용이 포함되어야 하나요?

*Expected:* KO→KO: KOSHA C-C-53 (management of change)

변경요소관리 절차는 정상변경과 임시변경 관리절차로 구분되며 다음 내용이 포함되어야 합니다 [1][3].

**1. 정상변경 관리절차**
* **변경관리요구서 작성 및 제출**: 발의자의 이름, 요구일자, 설비명, 비상 여부, 변경의 개요 및 발의자의 의견, 변경계획에 대한 공정 및 설계의 기술 근거, 도면 또는 스케치 등 첨부 서류, 공정안전 확보 대책, 안전운전에 필요한 사항 및 신뢰성 향상 효과를 포함하여 문서로 제출합니다 [1].
* **위험성 평가**: 변경등급 3은 위험성 평가를 생략할 수 있고, 등급 1과 2는 위험성 평가를 실시하되 등급 2는 평가자 구성범위를 축소 또는 조정할 수 있습니다 [1].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | 변경요소관리에 관한 기술지원규정, 6.2, pp. 8–9 | 0.969 | yes |
| 2 | 변경요소관리에 관한 기술지원규정, 8, pp. 10–11 | 0.957 |  |
| 3 | 변경요소관리에 관한 기술지원규정, 6.4, pp. 9–10 | 0.949 | yes |
| 4 | 변경요소관리에 관한 기술지원규정, 4, p. 6 | 0.883 |  |
| 5 | 변경요소관리에 관한 기술지원규정, 별표 2, p. 15 | 0.797 |  |

search 14.9s (rerank 14.7s) | LLM cached | thinking tokens 1848 | refused: no

## Q4. 가동전 안전점검은 언제 실시해야 하나요?

*Expected:* KO→KO: KOSHA C-C-52 (pre-startup safety review)

가동전 점검은 설비의 신설, 변경 또는 정비․보수를 위한 기계, 전기, 배관 및 계장 공사가 완료된 후부터 시운전 전까지의 기간에 실시해야 합니다 [1].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | 가동전 안점점검에 관한 기술지원규정, 7, p. 6 | 0.917 | yes |
| 2 | 가동전 안점점검에 관한 기술지원규정, 2, p. 4 | 0.834 |  |
| 3 | 가동전 안점점검에 관한 기술지원규정, 개요 (part 2/2), pp. 2–4 | 0.443 |  |
| 4 | 가동전 안점점검에 관한 기술지원규정, 5, p. 5 | 0.388 |  |
| 5 | 가동전 안점점검에 관한 기술지원규정, 10, p. 7 | 0.329 |  |

search 17.7s (rerank 17.6s) | LLM cached | thinking tokens 512 | refused: no

## Q5. 수소충전소의 설계 기준은 무엇인가요?

*Expected:* Unanswerable (no hydrogen-station guide in the corpus): should refuse

제공된 문서에서 찾을 수 없습니다.

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 6.1, p. 7 | 0.056 |  |
| 2 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 6.5.3 (1) (part 2/2), p. 11 | 0.021 |  |
| 3 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 6.2, p. 7 | 0.015 |  |
| 4 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 6.5.1, p. 8 | 0.011 |  |
| 5 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 6.5.2–(2), pp. 8–9 | 0.010 |  |

search 17.8s (rerank 17.7s) | LLM cached | thinking tokens 136 | refused: model

## Q6. What must a pre-startup safety review confirm before highly hazardous chemicals are introduced?

*Expected:* EN→EN: 29 CFR 1910.119(i)(2)

Prior to the introduction of highly hazardous chemicals to a process, a pre-startup safety review must confirm the following:

* Construction and equipment are in accordance with design specifications [1][2][3].
* Safety, operating, maintenance, and emergency procedures are in place and are adequate [1][2][3].
* For new facilities, a process hazard analysis has been performed and recommendations have been resolved or implemented before startup; and modified facilities meet management of change requirements [1][2][3].
* Training of each employee involved in operating a process has been completed [1][2][3].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | Process Safety Management, OSHA 3132 (2000, reprinted), Contractors / Pre-Startup Safety Review, p. 22 | 1.000 | yes |
| 2 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), (i), p. 6 | 0.999 | yes |
| 3 | Process Safety Management, OSHA 3132 (2000, reprinted), Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 10/15), pp. 40–41 | 0.997 | yes |
| 4 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), Appendix C 8, p. 16 | 0.981 |  |
| 5 | Process Safety Management, OSHA 3132 (2000, reprinted), Pre-Startup Safety Review (part 1/2), pp. 22–23 | 0.630 |  |

search 18.8s (rerank 18.8s) | LLM cached | thinking tokens 455 | refused: no

## Q7. What must a hot work permit document?

*Expected:* EN→EN: 29 CFR 1910.119(k)(2)

A hot work permit must document that the fire prevention and protection requirements in 29 CFR 1910.252(a) (OSHA regulations) have been implemented prior to beginning hot work operations [1][2][3]. In addition, the permit must indicate the date(s) authorized for hot work and identify the object on which the hot work is to be performed [1][2][3].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | Process Safety Management, OSHA 3132 (2000, reprinted), Hot Work Permit, p. 25 | 0.999 | yes |
| 2 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), (k), p. 7 | 0.989 | yes |
| 3 | Process Safety Management, OSHA 3132 (2000, reprinted), Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 12/15), pp. 42–43 | 0.942 | yes |
| 4 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), Appendix C 10, p. 18 | 0.374 |  |
| 5 | Process Safety Management, OSHA 3132 (2000, reprinted), How the Standard Works (part 2/2), pp. 9–10 | 0.130 |  |

search 16.7s (rerank 16.7s) | LLM cached | thinking tokens 159 | refused: no

## Q8. What is the design pressure of a vented fixed-roof atmospheric storage tank?

*Expected:* EN→KO cross-lingual: KOSHA C-C-93 (750 Pa positive)

The design pressure of a fixed-roof tank equipped with a vent must be within a positive pressure of 750 Pa (0.0076 ㎏/cm2) and a vacuum pressure of 250 Pa (0.0025 ㎏/㎠) [1].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 6.1, p. 7 | 0.920 | yes |
| 2 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), (b) (part 1/2), pp. 1–2 | 0.775 |  |
| 3 | Process Safety Management, OSHA 3132 (2000, reprinted), Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 1/15), pp. 32–33 | 0.705 |  |
| 4 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 4, pp. 5–6 | 0.630 |  |
| 5 | 상압저장탱크의 형식선정 및 설계에 관한 기술지원규정, 3 (1) (part 1/2), pp. 4–5 | 0.505 |  |

search 19.6s (rerank 19.6s) | LLM cached | thinking tokens 305 | refused: no

## Q9. How long must completed work permits be kept?

*Expected:* EN→KO cross-lingual: KOSHA C-C-49 8 (30 days on site, 1 year)

Under OSHA standards, a hot work permit must be kept on file until completion of the hot work operations [1][2][3]. 

Under technical support regulations for safe work permits, completed permits must generally be kept for 1 year, but confined space entry work permits must be kept for 3 years [4]. Additionally, work permit-related documents such as permits must be kept on-site by the issuing department for at least 30 days after work completion, and then kept for 1 year for monitoring and auditing [5].

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | Process Safety Management, OSHA 3132 (2000, reprinted), Hot Work Permit, p. 25 | 0.685 | yes |
| 2 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), (k), p. 7 | 0.584 | yes |
| 3 | Process Safety Management, OSHA 3132 (2000, reprinted), Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 12/15), pp. 42–43 | 0.553 | yes |
| 4 | 안전작업허가에 관한 기술지원규정, 5.5, p. 8 | 0.387 | yes |
| 5 | 안전작업허가에 관한 기술지원규정, 8–(6), pp. 23–24 | 0.296 | yes |

search 17.4s (rerank 17.4s) | LLM cached | thinking tokens 532 | refused: no

## Q10. What are the cybersecurity requirements for a plant's distributed control system?

*Expected:* Unanswerable: should refuse

Not found in the provided documents.

| # | Source | Rerank | Cited |
|---|---|---|---|
| 1 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), Appendix C 14 (part 2/4), pp. 20–21 | 0.002 |  |
| 2 | 29 CFR 1910.119 Process safety management of highly hazardous chemicals (CFR annual edition, July 1, 2025), Appendix C 13 (part 3/4), pp. 19–20 | 0.002 |  |
| 3 | Process Safety Management, OSHA 3132 (2000, reprinted), How the Standard Works (part 2/2), pp. 9–10 | 0.001 |  |
| 4 | Process Safety Management, OSHA 3132 (2000, reprinted), Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 6/15), pp. 36–38 | 0.001 |  |
| 5 | Process Safety Management, OSHA 3132 (2000, reprinted), Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 5/15), pp. 35–36 | 0.001 |  |

search 27.4s (rerank 27.4s) | LLM 0.0s | thinking tokens 0 | refused: low_score
