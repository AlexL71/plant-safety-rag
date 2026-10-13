# Answer grading rubric

Used to grade the system's answers in `eval/results/` (Phase 3). The grader (a Claude Code session, then
a human spot-check of at least 20%) reads, for each answer: the question, the evidence passages the
system was given, the system's answer, and the reference (gold) answer.

Two scores per answer, graded independently. Refusals ("not found") are not graded here; they are
counted by the refusal metrics.

## 1. Faithfulness: is everything in the answer supported by the evidence it was given?

Judge against the **evidence passages shown to the model**, not against the gold answer or outside
knowledge.

| Score | Meaning | Typical cases |
|---|---|---|
| **2: Faithful** | Every factual claim is stated in, or directly follows from, the evidence. Numbers, units and conditions match exactly. | A correct summary of two passages; a correct translation of an English passage into Korean. |
| **1: Partly faithful** | The main claim is supported, but at least one secondary claim is not, or a condition/qualifier is dropped or slightly overstated. | Adds a plausible detail not in the passages; turns "should" into "must"; drops an exception ("…unless a protective device of equal effect is installed"). |
| **0: Unfaithful** | The main claim is not supported by, or contradicts, the evidence. | Wrong number or unit; answer taken from outside knowledge; mixes up two documents' requirements (Korean vs US). |

Notes:
- Translation is allowed: a Korean answer to an English passage is faithful if the meaning is the same.
- A claim with a wrong citation number but supported by another shown passage is still faithful;
  citation accuracy is measured separately (automatically, against the gold chunks).

## 2. Correctness: does the answer give the reference answer?

Judge against the **gold answer** (and the gold chunks if needed).

| Score | Meaning |
|---|---|
| **2: Correct** | Contains the key fact(s) of the gold answer, with the right numbers and conditions. Extra correct detail is fine. |
| **1: Partly correct** | Contains part of the gold answer (e.g. 2 of 4 required items), or the right fact with a missing/incorrect qualifier. |
| **0: Wrong or missing** | Does not contain the key fact, or states a different one. |

## Output format

One JSON object per graded answer, appended to `eval/results/<run>/grades.jsonl`:

```json
{"qid": "q017", "setup": "D", "faithfulness": 2, "correctness": 1,
 "reason": "Lists 3 of the 5 equipment types in 제261조; all stated items are supported by [1]."}
```

`reason`: one sentence, naming the unsupported or missing claim when a score is below 2.

## Human spot-check

The user re-grades a random 20% sample (fixed seed) without looking at the grader's scores first, then
compares. Report the agreement rate next to the faithfulness numbers ("grader–human agreement 11/12").
