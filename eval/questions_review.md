# Evaluation questions

60 questions (dev 20 / test 40). Drafted by Opus 5.5 subagents that read the documents in full; every question verified by Claude Opus 5.5 against the full gold chunk texts and a corpus search for missing duplicates (2026-10-13). Not human-verified.

## q001 · dev · numeric · same-language (en→en)

**Q:** Under OSHA PSM, up to what design pressure can a storage tank still be treated as an atmospheric tank?

**Gold answer:** Under 29 CFR 1910.119 an atmospheric tank is a storage tank designed to operate at pressures from atmospheric through 0.5 p.s.i.g. (3.45 Kpa).

**Gold chunks:**
- `CFR-29-1910.119-2025::0002`: CFR-29-1910.119-2025 | (b) (part 1/2) | pp. 1-2
- `OSHA-3132-2000::0035`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 1/15) | pp. 32-33

**Evidence:**
> Atmospheric tank means a storage tank which has been designed to operate at pressures from
> atmospheric through 0.5 p.s.i.g. (pounds per square inch gauge, 3.45 Kpa)

## q002 · test · numeric · same-language (en→en)

**Q:** After a near miss that could have turned into a major toxic release, how soon do we have to start the incident investigation?

**Gold answer:** The investigation must be initiated as promptly as possible, but not later than 48 hours following the incident.

**Gold chunks:**
- `CFR-29-1910.119-2025::0020`: CFR-29-1910.119-2025 | (m) | pp. 7-7
- `OSHA-3132-2000::0027`: OSHA-3132-2000 | Management of Change (part 1/2) | pp. 26-27
- `OSHA-3132-2000::0047`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 13/15) | pp. 43-44

**Evidence:**
> (2) An incident investigation shall be initiated as promptly as possible, but not later than 48 hours following the incident.

## q003 · test · factual · same-language (en→en)

**Q:** When we run a HAZOP on a covered unit, does the study also have to look at facility siting and human factors, or only at equipment failures?

**Gold answer:** Yes. The process hazard analysis must address facility siting and human factors, in addition to the process hazards, previous incidents with catastrophic potential, engineering and administrative controls and the consequences of their failure, and a qualitative evaluation of possible safety and health effects on employees.

**Gold chunks:**
- `CFR-29-1910.119-2025::0008`: CFR-29-1910.119-2025 | (e)(3)–(6) | pp. 4-4
- `OSHA-3132-2000::0011`: OSHA-3132-2000 | Process Hazard Analysis (part 2/2) | pp. 14-15
- `OSHA-3132-2000::0040`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 6/15) | pp. 36-38

**Evidence:**
> (3) The process hazard analysis shall address:
> (v) Facility siting;
> (vi) Human factors; and

## q004 · dev · numeric · same-language (en→en)

**Q:** How many of our past compliance audit reports do we have to keep on file?

**Gold answer:** The employer must retain the two (2) most recent compliance audit reports.

**Gold chunks:**
- `CFR-29-1910.119-2025::0022`: CFR-29-1910.119-2025 | (o) | pp. 7-8
- `OSHA-3132-2000::0031`: OSHA-3132-2000 | Compliance Audits | pp. 29-29
- `OSHA-3132-2000::0048`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 14/15) | pp. 44-45

**Evidence:**
> (5) Employers shall retain the two (2) most recent compliance audit reports.

## q005 · test · factual · same-language (en→en)

**Q:** We use an outside cleaning company and a canteen caterer who work inside the unit fence. Do the process safety contractor requirements apply to them?

**Gold answer:** No. The contractor requirements apply to contractors doing maintenance or repair, turnaround, major renovation, or specialty work on or adjacent to a covered process, not to contractors providing incidental services that do not influence process safety, such as janitorial work, food and drink services, laundry, delivery or other supply services.

**Gold chunks:**
- `CFR-29-1910.119-2025::0013`: CFR-29-1910.119-2025 | (h)(1)–(2) | pp. 5-5
- `OSHA-3132-2000::0018`: OSHA-3132-2000 | Contractors / Application | pp. 20-20
- `OSHA-3132-2000::0043`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 9/15) | pp. 39-40

**Evidence:**
> This paragraph applies to contractors performing maintenance or repair, turnaround, major renovation, or specialty work on or adjacent to a covered process.
> It does not apply to contractors providing incidental services which do not influence process safety, such as janitorial work, food and drink services, laundry, delivery or other supply services.

## q006 · test · numeric · same-language (en→en)

**Q:** Under the US PSM rule, how much flammable liquid or gas held in one location on site brings a process into scope, even if the chemical is not on the Appendix A toxics list?

**Gold answer:** 10,000 pounds (4535.9 kg) or more on site in one location. The current CFR text applies this to Category 1 flammable gases and flammable liquids with a flashpoint below 100 °F (37.8 °C), with exceptions for hydrocarbon fuels used only as workplace fuel and for flammable liquids in atmospheric tanks kept below their normal boiling point without chilling or refrigeration.

**Gold chunks:**
- `CFR-29-1910.119-2025::0001`: CFR-29-1910.119-2025 | (a) | pp. 1-1
- `OSHA-3132-2000::0035`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 1/15) | pp. 32-33
- `OSHA-3132-2000::0006`: OSHA-3132-2000 | How the Standard Works (part 1/2) | pp. 9-9

**Evidence:**
> (ii) A process which involves a Category 1 flammable gas (as defined in 1910.1200(c)) or a flammable liquid with a flashpoint below 100 °F (37.8 °C) on site in one location
> in a quantity of 10,000 pounds (4535.9 kg) or more except for:

## q007 · dev · factual · same-language (en→en)

**Q:** For an outdoor unit handling toxic gas, how should people pick their escape route to the refuge area during a release, and where should the wind indicator go?

**Gold answer:** The employer should place a wind direction indicator, such as a wind sock or pennant, at the highest point that can be seen throughout the process area. Knowing the wind direction, employees move crosswind to upwind to reach the refuge area safely.

**Gold chunks:**
- `CFR-29-1910.119-2025::0061`: CFR-29-1910.119-2025 | Appendix C 13 (part 2/4) | pp. 19-19

**Evidence:**
> the employer should place a wind direction indicator such as a wind sock or pennant at the highest point that can be seen throughout the process area.
> Employees can move in the direction of cross wind to upwind to gain safe access to the refuge area by knowing the wind direction.

## q008 · test · factual · same-language (en→en)

**Q:** Our unit was built in 1988. Under PSM, do we have to include material and energy balances in its process safety information?

**Gold answer:** No, not as a strict requirement: material and energy balances are required only for processes built after May 26, 1992. The other equipment information (materials of construction, P&IDs, electrical classification, relief system design basis, etc.) is still required.

**Gold chunks:**
- `CFR-29-1910.119-2025::0006`: CFR-29-1910.119-2025 | (d)(2)–(3) | pp. 3-3
- `OSHA-3132-2000::0008`: OSHA-3132-2000 | Process Safety Information (part 1/2) | pp. 11-12
- `OSHA-3132-2000::0009`: OSHA-3132-2000 | Process Safety Information (part 2/2) | pp. 12-12
- `OSHA-3132-2000::0038`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 4/15) | pp. 34-36

**Evidence:**
> (G) Material and energy balances for processes built after May 26, 1992; and,

## q009 · test · numeric · cross-language (ko→en)

**Q:** 운전절차서가 현재 운전 방식과 맞고 정확하다는 것을 사업주가 얼마나 자주 확인해서 인증해야 하나요?

**Gold answer:** 운전절차서는 필요할 때마다 검토해야 하며, 사업주는 매년(annually) 운전절차서가 최신이고 정확하다는 것을 인증해야 합니다.

**Gold chunks:**
- `CFR-29-1910.119-2025::0010`: CFR-29-1910.119-2025 | (f)(1)–(3) | pp. 4-5
- `OSHA-3132-2000::0012`: OSHA-3132-2000 | Operating Procedures (part 1/2) | pp. 16-17
- `OSHA-3132-2000::0013`: OSHA-3132-2000 | Operating Procedures (part 2/2) | pp. 17-17
- `OSHA-3132-2000::0042`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 8/15) | pp. 38-39

**Evidence:**
> The employer shall certify annually that these operating procedures are current and accurate.

## q010 · test · procedural · cross-language (ko→en)

**Q:** 미국 PSM 기준에서 공정이나 설비를 바꾸기 전에 변경관리(MOC) 절차로 반드시 검토해야 하는 항목은 무엇인가요?

**Gold answer:** 변경 전에 (1) 변경의 기술적 근거, (2) 안전·보건에 미치는 영향, (3) 운전절차 수정, (4) 변경에 필요한 기간, (5) 변경 승인 요건을 검토해야 합니다. 단, 동일 사양 교체(replacement in kind)는 제외됩니다.

**Gold chunks:**
- `CFR-29-1910.119-2025::0019`: CFR-29-1910.119-2025 | (l) | pp. 7-7
- `OSHA-3132-2000::0027`: OSHA-3132-2000 | Management of Change (part 1/2) | pp. 26-27
- `OSHA-3132-2000::0046`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 12/15) | pp. 42-43

**Evidence:**
> (2) The procedures shall assure that the following considerations are addressed prior to any change:
> (i) The technical basis for the proposed change;
> (v) Authorization requirements for the proposed change.

## q011 · test · procedural · cross-language (ko→en)

**Q:** OSHA PSM의 기계적 건전성(MI) 요건은 어떤 설비들에 적용되나요?

**Gold answer:** 압력용기 및 저장탱크, 배관계통(밸브 등 배관 부품 포함), 방출 및 벤트 계통과 장치, 비상정지계통, 제어장치(감시장치·센서, 경보, 인터록 포함), 펌프에 적용됩니다.

**Gold chunks:**
- `CFR-29-1910.119-2025::0016`: CFR-29-1910.119-2025 | (j)(1)–(4) | pp. 6-6
- `OSHA-3132-2000::0022`: OSHA-3132-2000 | Pre-Startup Safety Review (part 1/2) | pp. 22-23
- `OSHA-3132-2000::0045`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 11/15) | pp. 41-42

**Evidence:**
> (i) Pressure vessels and storage tanks;
> (iii) Relief and vent systems and devices;
> (v) Controls (including monitoring devices and sensors, alarms, and interlocks) and,

## q012 · test · factual · cross-language (ko→en)

**Q:** 라이선스 공정이라 영업비밀 정보가 많은데, 공정위험성평가 팀이나 사고조사 담당자에게 비밀이라는 이유로 공정 정보를 제한해도 되나요?

**Gold answer:** 안 됩니다. 공정안전정보 작성, PHA 수행 지원, 운전절차 작성, 사고조사, 비상계획 및 대응, 준수감사 관계자에게는 영업비밀 여부와 관계없이 필요한 정보를 제공해야 합니다. 다만 사업주는 이들에게 비밀유지 계약을 요구할 수 있습니다.

**Gold chunks:**
- `CFR-29-1910.119-2025::0023`: CFR-29-1910.119-2025 | (p) | pp. 8-8
- `OSHA-3132-2000::0032`: OSHA-3132-2000 | Trade Secrets | pp. 30-30
- `OSHA-3132-2000::0048`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 14/15) | pp. 44-45

**Evidence:**
> without regard to possible trade secret status of such information.
> to enter into confidentiality agreements not to disclose the information as set forth in 29 CFR 1910.1200.

## q013 · dev · factual · cross-language (ko→en)

**Q:** 미국 PSM 기준에서 배관으로 연결된 여러 용기나, 떨어져 있어도 누출 시 같이 휘말릴 수 있는 용기들은 각각 별도의 공정으로 보나요?

**Gold answer:** 아닙니다. 서로 연결된 용기 그룹과, 고위험 화학물질의 잠재적 누출에 함께 관련될 수 있는 위치에 있는 별개의 용기들은 하나의 공정(single process)으로 간주합니다.

**Gold chunks:**
- `CFR-29-1910.119-2025::0003`: CFR-29-1910.119-2025 | (b) (part 2/2) | pp. 2-2
- `OSHA-3132-2000::0007`: OSHA-3132-2000 | How the Standard Works (part 2/2) | pp. 9-10
- `OSHA-3132-2000::0037`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 3/15) | pp. 33-34

**Evidence:**
> any group of vessels which are interconnected and separate vessels which are located such that a highly hazardous chemical could be involved in a potential release
> shall be considered a single process

## q014 · test · factual · same-language (ko→en)

**Q:** 임시 배관 연결 같은 임시변경도 변경관리(MOC)를 거쳐야 하나요? 그리고 임시변경 기간과 종료 후 조치는 어떻게 관리해야 하나요?

**Gold answer:** 네, 임시변경도 변경관리 대상입니다. 통제하지 않으면 영구화될 수 있으므로 임시변경의 기한을 정해 관리·감시해야 하고, 임시변경이 끝나면 설비와 절차를 원래(설계) 상태로 복구해야 합니다.

**Gold chunks:**
- `CFR-29-1910.119-2025::0057`: CFR-29-1910.119-2025 | Appendix C 11 (part 1/2) | pp. 18-18
- `CFR-29-1910.119-2025::0058`: CFR-29-1910.119-2025 | Appendix C 11 (part 2/2) | pp. 18-18
- `KOSHA-C-C-53-2026::0012`: KOSHA-C-C-53-2026 | 6.4 | pp. 9-10

**Evidence:**
> It is important that a time limit for temporary changes be established and monitored since, without control, these changes may tend to become permanent.
> Temporary changes are subject to the management of change provisions.

## q015 · dev · factual · cross-language (ko→en)

**Q:** 현장 작업자나 근로자 대표가 공정위험성평가 결과를 보여 달라고 하면 공개해야 하나요?

**Gold answer:** 네. 사업주는 근로자와 그 대표에게 공정위험성평가(PHA)와 이 기준에 따라 작성해야 하는 모든 정보에 접근할 수 있도록 해야 합니다. 또한 PHA 수행·개발에 대해 근로자와 협의하고, 근로자 참여에 관한 서면 실행계획을 작성해야 합니다.

**Gold chunks:**
- `CFR-29-1910.119-2025::0004`: CFR-29-1910.119-2025 | (c) | pp. 2-2
- `OSHA-3132-2000::0014`: OSHA-3132-2000 | Employee Participation | pp. 18-18
- `OSHA-3132-2000::0037`: OSHA-3132-2000 | Part 1910-Occupational Safety and Health Standards / 1910.119 Process Safety Management of Highly Hazardous Chemicals (part 3/15) | pp. 33-34

**Evidence:**
> (3) Employers shall provide to employees and their representatives access to process hazard analyses and to all other information required to be developed under this standard.
> (1) Employers shall develop a written plan of action regarding the implementation of the employee participation required by this paragraph.

## q016 · test · numeric · same-language (ko→ko)

**Q:** 설정압력이 3 barg인 안전밸브를 시험할 때, 실제 작동압력이 설정값에서 어느 정도까지 벗어나도 허용되나요?

**Gold answer:** 설정압력이 게이지 압력으로 5 bar 미만이므로 허용 오차는 ±0.14 bar 이하입니다. 참고로 설정압력이 5 bar 이상이면 설정압력의 ±3 % 이하입니다.

**Gold chunks:**
- `KOSHA-C-C-11-2026::0019`: KOSHA-C-C-11-2026 | 11–(2) | pp. 8-9

**Evidence:**
> 설정압력이 게이지 압력으로 5 bar 미만인 경우에는 ±0.14 bar 이하
> 설정압력이 게이지 압력으로 5 bar 이상인 경우에는 설정압력의 ±3 % 이하

## q017 · dev · numeric · cross-language (en→ko)

**Q:** Our vendor offered a cast-iron body relief valve for a reactor with a design pressure of 15 barg. Is that acceptable, and what pressure and temperature limits apply to cast iron?

**Gold answer:** No. Cast iron must not be used when the design pressure exceeds 13 bar gauge, or when the design temperature is above 220 ℃ or below 0 ℃; 15 barg is above the 13 bar limit.

**Gold chunks:**
- `KOSHA-C-C-11-2026::0018`: KOSHA-C-C-11-2026 | 10 | pp. 8-8

**Evidence:**
> (가) 설계압력이 게이지 압력으로 13 bar를 초과하는 경우
> (나) 설계온도가 220 ℃를 초과하거나 0 ℃ 미만인 경우

## q018 · test · numeric · same-language (ko→ko)

**Q:** 질소 블랭킷을 적용한 콘루프(고정지붕) 상압탱크는 설계압력을 양압과 진공 쪽으로 각각 얼마로 잡아야 하나요?

**Gold answer:** 불활성가스 봉입시설이 설치된 고정식 지붕탱크의 설계압력은 양압 2,000 Pa(0.0204 ㎏/㎠), 진공압력 600 Pa(0.0061 ㎏/㎠) 이내로 합니다.

**Gold chunks:**
- `KOSHA-C-C-93-2026::0010`: KOSHA-C-C-93-2026 | 6.1 | pp. 7-7

**Evidence:**
> (2) 불활성가스 봉입시설이 설치된 고정식 지붕탱크의 설계압력은 양압 2,000 Pa (0.0204 ㎏/㎠), 진공압력 600 Pa(0.0061 ㎏ /㎠)이내로 한다.

## q019 · dev · numeric · cross-language (en→ko)

**Q:** We have no corrosion-rate data for a new carbon-steel atmospheric tank that will store a corrosive liquid. What corrosion allowance should we design for?

**Gold answer:** Use a minimum corrosion allowance of 3 mm. If corrosion-rate data were available, the allowance would instead be the thickness lost over 20 years.

**Gold chunks:**
- `KOSHA-C-C-93-2026::0012`: KOSHA-C-C-93-2026 | 6.3 | pp. 7-8

**Evidence:**
> (가) 탄소강 재질의 탱크에 부식성이 있는 물질을 저장하는 경우 : 최소 3 mm
> 20년 동안 부식되는 두께를 부식 여유로 한다

## q020 · test · procedural · cross-language (en→ko)

**Q:** When is a floating-roof tank not a suitable choice for storing a flammable liquid?

**Gold answer:** A floating-roof tank must not be used when (1) rainwater ingress could contaminate or affect the stored product, (2) toxic vapours could leak, or (3) the product is viscous or has a high freezing point and forms a thick film on the inside of the tank at ambient temperature, unless the tank is insulated or heated to prevent the film.

**Gold chunks:**
- `KOSHA-C-C-93-2026::0009`: KOSHA-C-C-93-2026 | 5.2 | pp. 6-7

**Evidence:**
> (가) 빗물의 침투로 인하여 저장물질이 오염되거나 또는 영향을 받는 경우
> (나) 독성물질의 증기가 누출될 우려가 있는 경우
> (다) 저장물질의 점도가 높거나 또는 어는 점이 높아 상온에서 탱크내부 면에 두꺼운 막을 형성하는 경우

## q021 · test · numeric · same-language (ko→ko)

**Q:** 상압 저장탱크의 설계온도는 어떻게 정하나요? 스팀으로 탱크 내부를 청소해야 하는 경우에는 달라지나요?

**Gold answer:** 상압저장탱크의 설계온도는 저장물질의 온도에 30 ℃를 더한 값으로 합니다. 다만 스팀으로 탱크를 청소할 필요가 있는 경우에는 설계온도를 120 ℃로 합니다.

**Gold chunks:**
- `KOSHA-C-C-93-2026::0011`: KOSHA-C-C-93-2026 | 6.2 | pp. 7-7

**Evidence:**
> 상압저장탱크의 설계온도는 저장물질의 온도에 30 ℃를 더한 수치를 설계 온도로 한다
> 스팀을 사용하여 상압저장탱크를 청소할 필요가 있는 경우에는 설계온도를 120 ℃로 한다

## q022 · test · numeric · cross-language (en→ko)

**Q:** For a Korean project, when is nitrogen blanketing required on a cone-roof tank that stores a low-conductivity (static-accumulating) flammable liquid?

**Gold answer:** An inerting system is required on fixed-roof tanks of 100 m3 or more that store flammable liquids with an electrical conductivity of 10 pS/m or less. Tanks smaller than 100 m3 also need it where static can build up, i.e. when the liquid is sprayed in through an internal inlet nozzle or the inlet velocity is 1.0 m/s or more.

**Gold chunks:**
- `KOSHA-C-C-93-2026::0032`: KOSHA-C-C-93-2026 | 12 | pp. 17-18

**Evidence:**
> 전기 전도도가 10 pS/m 이하인 인화성물질을 저장하는 용량 100 m3 이상의 고정식 지붕탱크에는 불활성가스 봉입시설을 설치한다
> (나) 인화성물질의 인입 유속이 1.0 m/s 이상인 경우

## q023 · test · numeric · same-language (ko→ko)

**Q:** 펌프나 계기처럼 압력용기가 아닌 일반 설비의 점검결과 보고서는 얼마 동안 보관해야 하나요? 압력용기는 다른가요?

**Gold answer:** 압력용기·보일러가 아닌 기기의 점검결과 보고서는 다음 점검주기 또는 2년 중 긴 기간 동안 보관하며, 결함이 있던 기기는 보완조치를 완료한 후부터 그 기간을 보관합니다. 압력용기·보일러의 점검결과 보고서는 용기의 내구년한까지 보관합니다.

**Gold chunks:**
- `KOSHA-C-C-48-2026::0015`: KOSHA-C-C-48-2026 | 6.5 | pp. 10-11

**Evidence:**
> (1) 압력용기, 보일러에 대한 점검결과 보고서는 용기의 내구년한까지 보관한다.
> 다음 점검주기 또는 2년에서 긴 기간을 보관한다

## q024 · test · numeric · cross-language (en→ko)

**Q:** Under the Korean KOSHA guide on inspection and maintenance of hazardous equipment, how often should equipment inspectors be retrained, and how long must the training records be kept?

**Gold answer:** As a rule, inspection training is given at least once every 3 years, adjustable for equipment criticality, operating experience and manufacturer requirements. Training records, with the training plan and attendees' signatures, are kept for 3 years.

**Gold chunks:**
- `KOSHA-C-C-48-2026::0016`: KOSHA-C-C-48-2026 | 6.6 | pp. 11-11

**Evidence:**
> (2) 교육의 주기 점검에 대한 교육은 3년마다 1회 이상 실시함을 원칙으로 하되
> 교육실시에 대한 기록은 교육계획안 및 참석자의 서명과 함께 3년간 보관한다.

## q025 · test · factual · cross-language (en→ko)

**Q:** We're ranking equipment criticality for our inspection program. A pump whose failure would cause a partial unit shutdown but has no safety impact: which class does it belong to, and when should it be ranked higher?

**Gold answer:** It is Class C (failure causes a partial shutdown but no safety problem). It is recommended to raise it one grade if failure could breach safety or environmental regulations, affect the local community, or damage the company's image.

**Gold chunks:**
- `KOSHA-C-C-48-2026::0009`: KOSHA-C-C-48-2026 | 5.4 | pp. 7-7

**Evidence:**
> (다) C급은 기기의 고장이 운전의 부분정지를 가져오지만 안전상 문제가 없는 경우
> 한 단계 높게 설정하는 것을 권장한다

## q026 · test · procedural · same-language (ko→ko)

**Q:** 정비 작업을 마친 뒤 쓰는 정비 결과보고서에는 어떤 내용을 넣어야 하나요? 안전밸브를 정비했다면 따로 챙길 항목이 있나요?

**Gold answer:** 기기 이름과 식별번호, 작업자 성명과 자격, 정비항목과 정비내용, 정비 후 점검결과(허용범위 대비 적합 판정), 관리자의 검토·확인을 기록합니다. 안전밸브 작동시험을 한 경우에는 재닫힘(Reset) 압력을 확인하고 기록해야 합니다.

**Gold chunks:**
- `KOSHA-C-C-48-2026::0023`: KOSHA-C-C-48-2026 | 8.4 | pp. 15-16

**Evidence:**
> (바) 안전밸브 작동시험은 재닫힘(Reset) 압력을 확인하고, 기록
> (라) 정비후 점검결과 (허용범위 대비 적합 판정)

## q027 · test · numeric · same-language (ko→ko)

**Q:** 설비 제작·설치 외주업체를 유자격 업체로 한 번 등록하면, 그 뒤에는 자격을 어떻게 유지·관리해야 하나요?

**Gold answer:** 등록된 업체는 매년 작업품질에 대한 실사와 평가를 받아 유자격 업체로서의 자격유지 적부판정을 받아야 하며, 그 결과를 유지관리해야 합니다.

**Gold chunks:**
- `KOSHA-C-C-48-2026::0032`: KOSHA-C-C-48-2026 | 10.2 | pp. 20-20

**Evidence:**
> 등록된 업체는 자격이 유지되기 위해 매년 작업품질에 대한 실사와 평가를 통하여 유 자격 업체로서의 자격유지 적부판정을 받고 그 결과가 유지관리되어야 한다.

## q028 · test · factual · same-language (ko→ko)

**Q:** HAZOP 회의에서 개선 권고안을 두고 팀원끼리 의견이 갈리면, 리더가 정하거나 표결로 결론을 내도 되나요?

**Gold answer:** 아니요. 의견이 다를 경우 리더가 직접 결정하지 말고 팀원들에게 다시 묻거나 분야별 전문가 의견을 들어 조정해야 하며, 개선권고사항은 팀 전원의 동의가 필요하고 다수결로 처리하지 않습니다.

**Gold chunks:**
- `KOSHA-C-C-37-2026::0012`: KOSHA-C-C-37-2026 | 5.4 | pp. 9-9

**Evidence:**
> 서로 다른 의견이 있을 경우에는 리더가 직접 결정하지 말고 팀원들에게 다시 물어보든가 분야별 전문가의 의견을 들어 상반된 의견을 조정한다.
> 개선권고사항은 팀 전원의 동의가 필요하며 다수결에 의해 처리하지 않도록 한다.

## q029 · test · factual · cross-language (en→ko)

**Q:** When we rank the risk of a HAZOP deviation, do we take credit for the existing safeguards when judging both the likelihood and the severity?

**Gold answer:** No. The likelihood (frequency) is set taking the existing safeguards into account, but the severity is set without considering the existing safeguards.

**Gold chunks:**
- `KOSHA-C-C-37-2026::0019`: KOSHA-C-C-37-2026 | 6.5 | pp. 13-14

**Evidence:**
> 위험도를 결정하는 경우 발생빈도는 현재 안전조치를 고려하여 결정하나, 강도는 현재 안전조치를 고려하지 않는다.

## q030 · test · factual · same-language (ko→ko)

**Q:** HAZOP 노드를 나눌 때 첫 번째 노드는 어디서부터 잡고, 같은 배관이 다음 P&ID 장으로 넘어가면 노드를 새로 끊어야 하나요?

**Gold answer:** 가능한 한 공정흐름 순서를 따르며, 원료가 투입되는 배관 주변을 첫 번째 검토구간으로 정합니다. 다음 도면으로 바뀌어도 배관으로 계속 연결되는 경우에는 동일한 검토구간으로 간주합니다.

**Gold chunks:**
- `KOSHA-C-C-37-2026::0015`: KOSHA-C-C-37-2026 | 6.2 | pp. 11-11

**Evidence:**
> 원료가 투입되는 배관 주변을 첫 번째 검토구간으로 정한다.
> 다음 도면으로 바뀌어도 배관으로 계속 연결되는 경우에는 동일한 검토구간으로 간주한다.

## q031 · test · numeric · same-language (ko→ko)

**Q:** 변경관리(MOC) 위원회는 최소 몇 명으로 구성해야 하고, 반드시 들어가야 하는 사람은 누구인가요?

**Gold answer:** 공정기술자, 정비기술자, 운전기술자 등 3인을 필수위원으로 구성하며, 변경 규모나 대상에 따라 기계·전기·계장기술자 등을 추가할 수 있습니다.

**Gold chunks:**
- `KOSHA-C-C-53-2026::0015`: KOSHA-C-C-53-2026 | 9.1 | pp. 11-11

**Evidence:**
> 변경관리위원회는 공정기술자, 정비기술자 및 운전기술자 등 3인을 필수위원으로 구성하되

## q032 · test · numeric · cross-language (en→ko)

**Q:** How many people have to review the MOC class assigned to a proposed change, and who signs off that classification?

**Gold answer:** The class must be reviewed by at least 2 reviewers and then approved by the head of the department that initiated the change or by the MOC committee.

**Gold chunks:**
- `KOSHA-C-C-53-2026::0008`: KOSHA-C-C-53-2026 | 5.3 | pp. 7-7

**Evidence:**
> 등급의 분류는 최소한 2명의 검토자가 검토한 후 변경 발의부서의 장 또는 변경관리 위원회에 의해 승인되도록 한다.

## q033 · test · procedural · cross-language (en→ko)

**Q:** If we must modify the plant urgently on a weekend to prevent an accident and cannot wait for the MOC committee, who has to approve it and what do we have to do afterwards?

**Gold answer:** It is handled as an emergency change: the initiator gets approval from the head of the operations department and the employer (by phone if needed, with formal approval later). Immediately after the change, the initiator submits an MOC request under the normal procedure marked "비상" (emergency), and the MOC committee reviews it and decides whether the change may stay in place.

**Gold chunks:**
- `KOSHA-C-C-53-2026::0011`: KOSHA-C-C-53-2026 | 6.3 | pp. 9-9
- `KOSHA-C-C-53-2026::0021`: KOSHA-C-C-53-2026 | 10.4 | pp. 12-12

**Evidence:**
> 비상변경 발의자는 운전부서의 장 및 사업주의 승인을 받는다. 다만 필요시 유선으로 보고하고 추후 승인을 받는다.
> 비상변경 발의자는 변경시행 후 즉시 6.2의 정상변경관리절차에 따라 변경관리요구서를 작성하여 변경관리위원회에 제출한다.
> 변경관리위원회는 변경관리요구서를 검토하여 변경 시행된 사항을 계속 유지하여 운전할 것인가를 결정한다.

## q034 · test · numeric · cross-language (en→ko)

**Q:** After a new unit starts operating, how long do we have to keep the pre-startup safety review report and the punch list paperwork?

**Gold answer:** The pre-startup safety review report, the punch list request sheet and the punch list action plan must be kept for at least 3 years after the plant starts operation.

**Gold chunks:**
- `KOSHA-C-C-52-2026::0012`: KOSHA-C-C-52-2026 | 10 | pp. 7-7

**Evidence:**
> 가동전 안전점검보고서, 개선항목 요구표 및 개선항목 실행계획서는 공장운전개시 후 최소한 3년간 보관한다.

## q035 · dev · procedural · cross-language (en→ko)

**Q:** For a plant project in Korea, which disciplines should make up the pre-startup safety review team?

**Gold answer:** The team (or engineers specially trained for PSSR) should include: a team leader, the process/equipment design engineer, the process/equipment operations engineer, an inspection and maintenance engineer, the emergency planning and safety manager, and, if needed, a manufacturer's specialist for special equipment and major rotating machinery.

**Gold chunks:**
- `KOSHA-C-C-52-2026::0008`: KOSHA-C-C-52-2026 | 6 | pp. 6-6

**Evidence:**
> 가동전 점검을 위한 팀은 점검범위에 따라 별도의 가동전 점검을 위해 사전 교육․ 훈련된 기술자 또는 다음과 같은 기술자들로 구성한다.
> (5) 비상계획 및 안전관리자
> (6) 특수설비 및 주요 회전기기의 경우 제작 전문기술자(필요 시)

## q036 · test · numeric · cross-language (en→ko)

**Q:** On a Korean site, what oxygen reading must the gas test show before workers are allowed inside a vessel or other confined space?

**Gold answer:** Entry is allowed only when the oxygen concentration is 18 % or more and less than 23.5 %. The Korean OSH Standards Rule defines the same range (18-23.5 %) as part of 'adequate air' (적정공기).

**Gold chunks:**
- `KOSHA-C-C-49-2026::0025`: KOSHA-C-C-49-2026 | 7.3 (1) (part 2/4) | pp. 16-17
- `KOSHA-C-C-49-2026::0026`: KOSHA-C-C-49-2026 | 7.3 (1) (part 3/4) | pp. 17-18
- `KR-RULE-OSH-STANDARDS-450::0658`: KR-RULE-OSH-STANDARDS-450 | 제618조 | pp. 111-111

**Evidence:**
> 산소농도가 18 % 이상 23.5 %미만일 때에만 용기내의 출입을

## q037 · dev · numeric · same-language (ko→ko)

**Q:** 지하에 배관이나 전선 케이블을 묻으려고 땅을 팔 때, 깊이가 어느 정도부터 굴착작업 허가를 받아야 하나요?

**Gold answer:** 깊이 30cm 이상 지반을 파고 배관, 전기케이블 등의 지하매설 작업을 할 때는 굴착작업 허가서를 발급받아야 합니다.

**Gold chunks:**
- `KOSHA-C-C-49-2026::0029`: KOSHA-C-C-49-2026 | 7.3 (3) | pp. 20-20

**Evidence:**
> 깊이 30cm 이상 지반을 파고 배관, 전기케이블 등의 지하매설 작업을 하고자 할 때는 굴착작업 허가서를 발급받아야 한다.

## q038 · dev · factual · cross-language (en→ko)

**Q:** Can a work permit issued this morning stay valid overnight if the job carries on into the next day?

**Gold answer:** No. A permit is valid only for the period written on it and cannot exceed the normal daily working hours (it may be extended within the same day if the workers and issuer do not change). If the work continues to the next day, or the scope, safety requirements or other conditions change, the permit must be reissued.

**Gold chunks:**
- `KOSHA-C-C-49-2026::0014`: KOSHA-C-C-49-2026 | 5.6 | pp. 8-9

**Evidence:**
> 허가서의 효력은 허가서상의 허가기간에서만 유지되며, 일일 정상근무시간을 초과할 수 없다.
> 작업이 허가 익일까지 지속되거나 작업내용의 변경, 안전요구 사항의 변경 및 기타 조건의 변동이 있을 때에는 재발급하여야 한다.

## q039 · dev · numeric · same-language (ko→ko)

**Q:** 안전보건규칙상 공정 유체가 디스크·시트에 직접 닿는 안전밸브는 몇 년마다 설정압력 작동 검사를 받아야 하나요? 입구 쪽에 파열판을 단 경우에는 주기가 어떻게 달라지나요?

**Gold answer:** 공정 유체가 안전밸브의 디스크 또는 시트에 직접 접촉하도록 설치된 경우 2년마다 1회 이상, 안전밸브 전단에 파열판이 설치된 경우 3년마다 1회 이상 검사해야 합니다. (공정안전보고서 이행상태 평가 결과가 우수한 사업장은 4년마다 1회 이상)

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0285`: KR-RULE-OSH-STANDARDS-450 | 제261조 ③–⑤ | pp. 46-46
- `KOSHA-C-C-11-2026::0008`: KOSHA-C-C-11-2026 | 5 (part 1/2) | pp. 6-6

**Evidence:**
> 화학공정 유체와 안전밸브의 디스크 또는 시트가 직접 접촉될 수 있도록 설치된 경우: 2년마다 1회 이상
> 안전밸브 전단에 파열판이 설치된 경우: 3년마다 1회 이상

## q040 · test · numeric · same-language (ko→ko)

**Q:** 반응기나 증류탑을 운전 온도·압력만으로 특수화학설비로 보게 되는 기준이 있나요? 몇 도, 몇 kPa 이상이면 온도계·압력계 같은 계측장치를 갖춰야 하나요?

**Gold answer:** 별표 9의 위험물을 기준량 이상 제조·취급하는 설비 중 온도가 섭씨 350도 이상이거나 게이지 압력이 980킬로파스칼 이상인 상태에서 운전되는 설비는 특수화학설비에 해당하며, 온도계·유량계·압력계 등의 계측장치를 설치해야 합니다.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0297`: KR-RULE-OSH-STANDARDS-450 | 제273조 | pp. 48-48

**Evidence:**
> 온도가 섭씨 350도 이상이거나 게이지 압력이 980킬로파스칼 이상인 상태에서 운전되는 설비
> 온도계ㆍ유량계ㆍ압력계 등의 계측장치를 설치하여야 한다

## q041 · dev · numeric · same-language (ko→ko)

**Q:** 배관 용접이나 절단 작업 때, 작업 지점에서 몇 미터 안에 가연물이 있으면 화재감시자를 따로 배치해야 하나요?

**Gold answer:** 용접·용단 작업반경 11미터 이내에 건물구조 자체나 내부에 가연성물질이 있는 장소 등에서는 화재감시자를 지정하여 작업 장소에 배치해야 합니다. 다만 같은 장소에서 상시·반복적으로 작업하면서 경보용 설비·기구, 소화설비 또는 소화기가 갖추어진 경우에는 배치하지 않을 수 있습니다.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0264`: KR-RULE-OSH-STANDARDS-450 | 제241조의2 | pp. 43-44

**Evidence:**
> 작업반경 11미터 이내에 건물구조 자체나 내부(개구부 등으로 개방된 부분을 포함한다)에 가연성물질이 있는 장소
> 화재감시자를 지정하여 용접ㆍ용단 작업 장소에 배치해야 한다

## q042 · test · numeric · same-language (ko→ko)

**Q:** 정비 후 한동안 세워 두었던 화학설비를 다시 돌릴 때, 얼마 이상 쉬었으면 법적으로 사용 전 점검을 하고 가동해야 하나요?

**Gold answer:** 계속하여 1개월 이상 사용하지 않은 후 다시 사용하는 경우에는 화학설비 및 그 부속설비의 안전검사내용을 점검한 후 사용해야 합니다. 처음 사용하는 경우와 분해·개조·수리를 한 경우도 마찬가지입니다.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0301`: KR-RULE-OSH-STANDARDS-450 | 제277조 | pp. 48-49

**Evidence:**
> 계속하여 1개월 이상 사용하지 아니한 후 다시 사용하는 경우
> 화학설비 및 그 부속설비의 안전검사내용을 점검한 후 해당 설비를 사용하여야 한다

## q043 · dev · procedural · same-language (ko→ko)

**Q:** 압력용기나 배관에 안전밸브 말고 꼭 파열판(럽쳐디스크)을 써야 하는 경우는 어떤 경우인가요?

**Gold answer:** ① 반응 폭주 등 급격한 압력 상승 우려가 있는 경우, ② 급성 독성물질의 누출로 주위 작업환경을 오염시킬 우려가 있는 경우, ③ 운전 중 안전밸브에 이상 물질이 누적되어 안전밸브가 작동되지 않을 우려가 있는 경우에는 파열판을 설치해야 합니다.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0286`: KR-RULE-OSH-STANDARDS-450 | 제262조 | pp. 46-46

**Evidence:**
> 반응 폭주 등 급격한 압력 상승 우려가 있는 경우
> 급성 독성물질의 누출로 인하여 주위의 작업환경을 오염시킬 우려가 있는 경우
> 운전 중 안전밸브에 이상 물질이 누적되어 안전밸브가 작동되지 아니할 우려가 있는 경우

## q044 · test · factual · same-language (ko→ko)

**Q:** 안전보건규칙상 안전밸브 앞뒤에는 블록밸브를 못 단다고 들었는데, 배관 열팽창 보호용 써멀 릴리프밸브에도 똑같이 적용되나요?

**Gold answer:** 원칙적으로 안전밸브등의 전단·후단에는 차단밸브를 설치할 수 없지만, 열팽창에 의하여 상승된 압력을 낮추기 위한 목적으로 설치된 안전밸브의 경우에는 자물쇠형 또는 이에 준하는 형식의 차단밸브를 설치할 수 있습니다.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0290`: KR-RULE-OSH-STANDARDS-450 | 제266조 | pp. 47-47

**Evidence:**
> 사업주는 안전밸브등의 전단ㆍ후단에 차단밸브를 설치해서는 아니 된다.
> 열팽창에 의하여 상승된 압력을 낮추기 위한 목적으로 안전밸브가 설치된 경우
> 자물쇠형 또는 이에 준하는 형식의 차단밸브를 설치할 수 있다

## q045 · dev · numeric · same-language (ko→ko)

**Q:** 도시가스 배관 근처에서 굴착할 때 가스 농도는 언제 재야 하나요? 작업이 길어지면 몇 시간마다 재고, 농도가 LEL의 몇 %가 되면 작업자를 대피시켜야 하나요?

**Gold answer:** 가스농도 측정자를 지명해 매일 작업 시작 전, 누출이 의심될 때, 가스가 발생·정체할 위험이 있을 때 측정하고, 장시간 작업 시에는 4시간마다 측정해야 합니다. 가스 농도가 인화하한계 값의 25퍼센트 이상이면 즉시 근로자를 안전한 장소로 대피시키고 점화원 사용을 중지하며 환기해야 합니다.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0320`: KR-RULE-OSH-STANDARDS-450 | 제296조 | pp. 52-52

**Evidence:**
> 장시간 작업을 계속하는 경우(이 경우 4시간마다 가스 농도를 측정하도록 하여야 한다)
> 가스의 농도가 인화하한계 값의 25퍼센트 이상으로 밝혀진 경우에는 즉시 근로자를 안전한 장소에 대피시키고

## q046 · dev · procedural · same-language (ko→ko)

**Q:** 열교환기나 탑조를 열고 내부 청소·수리 작업을 할 때, 위험물 설비라서 법으로 꼭 지켜야 하는 사항이 뭔가요?

**Gold answer:** ① 작업책임자를 정하여 작업을 지휘하게 하고, ② 작업장소에 위험물 등이 누출되거나 고온의 수증기가 새어 나오지 않도록 하며, ③ 작업장 및 주변의 인화성 액체 증기나 인화성 가스 농도를 수시로 측정해야 합니다.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0302`: KR-RULE-OSH-STANDARDS-450 | 제278조 | pp. 49-49

**Evidence:**
> 작업책임자를 정하여 해당 작업을 지휘하도록 할 것
> 작업장소에 위험물 등이 누출되거나 고온의 수증기가 새어나오지 않도록 할 것
> 작업장 및 그 주변의 인화성 액체의 증기나 인화성 가스의 농도를 수시로 측정할 것

## q047 · test · numeric · cross-language (en→ko)

**Q:** If we fit two relief valves on the same process vessel, does the second one also have to be set at or below the MAWP, or can it go higher — and how much higher if it is sized for the external fire case?

**Gold answer:** Relief devices must normally open at or below the maximum allowable working pressure of the protected equipment. When two or more are installed, one of them may be set at up to 1.05 times that pressure, or up to 1.1 times when it is provided for the external fire case.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0288`: KR-RULE-OSH-STANDARDS-450 | 제264조 | pp. 47-47

**Evidence:**
> 보호하려는 설비의 최고사용압력 이하에서 작동되도록 하여야 한다
> 1개는 최고 사용압력의 1.05배(외부화재를 대비한 경우에는 1.1배) 이하에서 작동되도록 설치할 수 있다

## q048 · test · factual · cross-language (en→ko)

**Q:** Under Korean safety rules, is a pressure relief device mandatory on every positive displacement pump, or only in certain configurations?

**Gold answer:** Not on every one: a positive displacement pump needs a relief valve or rupture disc only when a shut-off (block) valve is installed on its discharge side. Positive displacement compressors, by contrast, are listed without that condition.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0284`: KR-RULE-OSH-STANDARDS-450 | 제261조 ①–② | pp. 46-46
- `KOSHA-C-C-11-2026::0007`: KOSHA-C-C-11-2026 | 4 | pp. 5-6

**Evidence:**
> 정변위 펌프(토출측에 차단밸브가 설치된 것만 해당한다)
> 안전밸브 또는 파열판(이하 “안전밸브등”이라 한다)을 설치하여야 한다

## q049 · dev · factual · cross-language (en→ko)

**Q:** Under the Korean OSH standards, can a storage tank vent use a simple flame screen instead of a certified flame arrester? Which liquids does that apply to?

**Gold answer:** Yes, in two cases: a flame arrester is not required if the vent line has a breather valve with flame-arresting function, or if the tank stores/handles flammable liquids with a flash point of 38 °C to 60 °C and a flame screen (인화방지망) with flame-arresting function is installed. Otherwise a flame arrester meeting the Korean Industrial Standard must be fitted at the top of the equipment.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0293`: KR-RULE-OSH-STANDARDS-450 | 제269조 | pp. 47-47

**Evidence:**
> 인화점이 섭씨 38도 이상 60도 이하인 인화성 액체를 저장ㆍ취급할 때에 화염방지 기능을 가지는 인화방지망을 설치한 경우에는 그렇지 않다
> 화염방지기를 그 설비 상단에 설치해야 한다

## q050 · test · factual · cross-language (en→ko)

**Q:** In a Zone 1 area where all electrical equipment is already explosion-proof, do we still have to install fixed gas detectors with alarms?

**Gold answer:** No. Gas detection and alarm devices are generally required where flammable vapours or gases could cause a fire or explosion, but they are not required in a Zone 0 or Zone 1 hazardous area (per the Korean Industrial Standard) where explosion-proof electrical equipment has been installed under Article 311.

**Gold chunks:**
- `KR-RULE-OSH-STANDARDS-450::0254`: KR-RULE-OSH-STANDARDS-450 | 제232조 | pp. 41-42

**Evidence:**
> 가스 검지 및 경보 성능을 갖춘 가스 검지 및 경보 장치를 설치해야 한다
> 한국산업표준에 따른 0종 또는 1종 폭발위험장소에 해당하는 경우로서 제311조에 따라 방폭구조 전기기계ㆍ기구를 설치한 경우에는 그렇지 않다

## q051 · dev · unanswerable · unanswerable (ko→–)

**Q:** LOPA(방호계층분석)를 할 때 고압 트립 같은 계장 안전기능을 독립방호계층(IPL)으로 인정받으려면 요구 시 고장확률(PFD)이 얼마 이하여야 하나요?

**Gold answer:** 제공된 문서에서 찾을 수 없습니다.


## q052 · test · unanswerable · unanswerable (ko→–)

**Q:** 인화성 액체용 상압저장탱크를 내진설계할 때, 지진 시 액면이 출렁이는 슬로싱을 고려해 지붕 아래 여유 높이(freeboard)를 얼마나 확보해야 하나요?

**Gold answer:** 제공된 문서에서 찾을 수 없습니다.


## q053 · dev · unanswerable · unanswerable (ko→–)

**Q:** 공정안전 성과지표(PSPI)에서 Tier 1 공정안전사고로 분류되는 물질 누출량 기준은 어떻게 정해져 있나요?

**Gold answer:** 제공된 문서에서 찾을 수 없습니다.


## q054 · test · unanswerable · unanswerable (ko→–)

**Q:** 고압 수소가스 배관 재질을 선정할 때 수소취성을 막기 위해 탄소강의 경도나 인장강도 상한을 얼마로 제한해야 하나요?

**Gold answer:** 제공된 문서에서 찾을 수 없습니다.


## q055 · test · unanswerable · unanswerable (ko→–)

**Q:** 가열로(fired heater) 버너를 점화하기 전에 노 내부를 퍼지할 때, 노 체적의 몇 배 이상을 공기로 치환해야 점화해도 되나요?

**Gold answer:** 제공된 문서에서 찾을 수 없습니다.


## q056 · dev · unanswerable · unanswerable (en→–)

**Q:** How do we determine the required Safety Integrity Level (SIL) for a high-pressure shutdown trip on a gas compressor discharge?

**Gold answer:** Not found in the provided documents.


## q057 · test · unanswerable · unanswerable (en→–)

**Q:** What design blast overpressure should an occupied control building in a refinery process area be built to withstand?

**Gold answer:** Not found in the provided documents.


## q058 · dev · unanswerable · unanswerable (en→–)

**Q:** What average alarm rate per console operator per hour is considered acceptable under alarm management guidance such as ISA-18.2 or EEMUA 191?

**Gold answer:** Not found in the provided documents.


## q059 · test · unanswerable · unanswerable (en→–)

**Q:** What Kst value separates an St 1 dust from an St 2 dust when sizing explosion vents for a dust collector?

**Gold answer:** Not found in the provided documents.


## q060 · test · unanswerable · unanswerable (en→–)

**Q:** Under the EPA Risk Management Program rule, what toxic endpoint concentration is used for chlorine when calculating the worst-case release distance?

**Gold answer:** Not found in the provided documents.

