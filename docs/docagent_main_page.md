# DocAgent: main page text

Text for the platform's main (landing) page. Copy the sections you need.
"Built" means it works and was evaluated in this repository. "Planned" means it is not built yet, so don't
present planned modules as working features.

---

## Hero

**Name:** DocAgent

**Tagline:** The AI agent for EPC project documents.

**Subtitle (one sentence):**
DocAgent brings all your project documents into one place and lets engineers ask questions, check documents
and prepare reviews in plain language, with every answer linked to the exact clause it came from.

**Short version (for a card or a header):**
Ask your project documents anything. Get answers with clause references, or an honest "not found".

---

## The problem

On an EPC project, the answer to an engineering question is spread across thousands of documents:
specifications, standards, regulations, datasheets, vendor documents and their revisions, often in more than
one language. Engineers lose hours finding the right clause, and a missed requirement costs money and safety.

## What DocAgent does

DocAgent is an **AI agent**, not just a chatbot. A chatbot answers one question. An agent plans several steps
and uses tools: it searches the documents, reads the right clauses, compares them and prepares a result.

- **Answers with proof**: every statement cites the document, clause and page.
- **Says "not found" instead of guessing** when the documents don't cover the question.
- **Works across languages**: ask in Korean and get the answer from an English standard, or the other way round.
- **Works with your existing system**: connects to your CDE (Common Data Environment) or document management
  system. You don't have to replace it.
- **A person stays in control**: the agent prepares comments, checks and status suggestions, and a person
  approves them. This matters because approvals and transmittals are formal project records.

## Modules

| Module | One line | Status |
|---|---|---|
| **DocAgent Ask** | Ask in Korean or English, get an answer with clause-level citations | Built |
| **DocAgent Search** | Find any document or clause across all sources and languages | Built (core) |
| **DocAgent Library** | One register of all project documents, connected to SharePoint, Aconex, ProjectWise or shared folders | Planned |
| **DocAgent Check** | Check a datasheet or vendor document against specs and standards, and list mismatches | Planned |
| **DocAgent Flow** | Track reviews, approvals and revisions; draft comment sheets for approval | Planned |

## Example tasks

| You ask | What the agent does |
|---|---|
| "Where must a relief valve be installed?" | Searches the regulations and KOSHA guides, then answers with clause citations *(works today)* |
| "Is this pump datasheet compliant with our specs?" | Finds the specs, reads the datasheet, compares the values and lists mismatches *(planned)* |
| "What changed between Rev B and Rev C?" | Gets both revisions, compares them and summarizes the changes *(planned)* |
| "Prepare review comments for this vendor document" | Checks it against the standards and drafts a comment sheet for you to approve *(planned)* |

## Why trust it (measured results)

Tested on 40 held-out bilingual questions about process-safety standards:

- Found the right clause in the top 5 results for **34 of 34** answerable questions, including
  **16 of 16** cross-language ones.
- Correctly refused **6 of 6** questions that the documents don't answer, with only **1** false refusal.
- **Every answer was faithful to its sources**: no invented facts.

*Caveat: this is a small test set, and the grading was checked by AI, not by a human expert.*

## Footer / disclaimer

DocAgent is a reference tool. It does not replace engineering judgment, legal advice or formal safety review.
