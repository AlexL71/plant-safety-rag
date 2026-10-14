# Agent evaluation v1: review of the outputs

Reviewer: Claude Opus 5.5 (main session), 2026-10-14. **Not a human safety expert.**
Method: every shown element (51 visual elements, 106 plan items, 66 notice lines) was read next to the clause it
cites; claims that looked doubtful were checked against the full passage text (e.g. v08 retention periods, v09
respirator rule). Not every line was compared word by word with its passage. The numbers guard had already removed every element with a number that is
not in its cited passage.

## Faithfulness

- **No element states something its cited passage does not support** (0 / 223 found).
- Spot checks confirmed against the full text: permit retention 1 year / confined-space permit 3 years and
  programme review every 2 years (KOSHA E-G-18 5.5, 5.2); respirator rule in 안전보건규칙 제619조의2; cold-store
  PPE at −18 °C (제32조); OSHA lifeline 10,000 lb for two workers in elevator shafts (1926.502(d)(10)).

## Problems found (quality, completeness, check bugs)

| Case | Problem | Cause | Status |
|---|---|---|---|
| v01 steps | 3 of 6 steps dropped | labels started with "4.", "5.", "6." and the guard checked those digits | **fixed** (list numbers and "[n]" marks are removed before checking) |
| p04 plan | 8 of 27 items dropped | the model wrote "[2]" into the text | **fixed** (same change) |
| v06 limits | the main requirement (42 ± 3 in) dropped; only 2 minor limits shown | the model wrote derived values (39–45) that are not literally in the cited paragraph | by design: the guard does not do arithmetic; known limitation |
| v08 intervals | covered the permit periods but not the forklift evaluation the question also asked for | two-part question, one part missed | open |
| v10 compare | Korea side "not covered" for the post-welding fire watch, although KOSHA A-G-14 says 30 min | that passage was not retrieved | retrieval miss, open |
| v11 compare | no answer ("not found") | best reranker score below the 0.15 threshold | same false-refusal pattern as test2 q066 |
| n01, n03 notices | the same rule repeated as a key rule and as a do / don't line | content quality | open (prompt) |
| n06 notice | "2미터" in an English notice | value copied from a Korean passage | open |
| n04, n05 translations | 3 lines flagged | dates ("January 2, 1990" → "1990년 1월 2일") and "half hour" → "30분" change the digits | false alarms: meaning kept; the flag sends them to a human, which is the intended safe side |
