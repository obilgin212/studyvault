---
name: add-course
description: Set up a new course in the vault from a textbook PDF, syllabus, or online curriculum. Extracts text with page numbers, builds the Course Map, Learner Model and concept graph. Use for "/add-course", "add my <class>", "here's my syllabus/textbook/curriculum for X".
---

# /add-course

Input: a course name plus any of: textbook PDF path, syllabus/curriculum PDF or URL, test dates. Model it on `_examples/AP Calc BC/` (read its Course Map and Learner Model as templates).

1. `mkdir -p "Courses/<Course>/"{_sources/text,Sessions,Visuals,Flashcards}`; copy (don't move) source PDFs into `_sources/` (`textbook.pdf`, `syllabus.pdf`).
2. **Textbook PDF:**
   - `~/miniconda3/envs/study/bin/python tools/pdf.py pagemap <pdf>` to map printed pages.
   - Find chapter and section starts: use the PDF outline (`pymupdf` `get_toc()`) if there is one; otherwise search for section-heading patterns and the "Contents" pages.
   - `tools/pdf.py split` each section into `_sources/text/<§> <title>.md`. Do the chapters on the syllabus first; add others later when needed.
   - Scanned PDF (pages with no text): tell {{NAME}}, then OCR only the pages needed (`brew install ocrmypdf` requires their approval).
3. **No textbook (online curriculum):** save the curriculum pages as Markdown in `_sources/` (WebFetch; keep the URL at the top of each file). For AP classes, the College Board **Course and Exam Description** (CED) is the most authoritative source: use its units and topic numbers and learning objectives as the Course Map backbone. Use reputable free texts where they help (OpenStax for physics/stats; for French, the class's own materials).
4. Write **Course Map.md**: frontmatter (course, textbook, pdf, pagemap), an Upcoming table (tests and dates), and per unit/chapter a Mermaid prerequisite graph plus section headings with page ranges and key ideas.
5. Write **Learner Model.md**: a concept table (all ⬜) at the granularity of individual testable skills.
6. Add the course to `Dashboard.md`. Show {{NAME}} the Course Map and ask about upcoming tests.

## Skill tree
Create `Courses/<course>/_skilltree.yaml` from the Course Map (branches = units in order; nodes = skills with `lm` = the exact start of the Learner Model concept, `find`, `needs`; skills the class already covered and {{NAME}} clearly has can use `given: 3` + `given_note`), modeled on `_examples/AP Calc BC/_skilltree.yaml`. Then run `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`.
