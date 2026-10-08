---
name: profile
description: Learning-preferences quiz. Asks {{NAME}} how they like to learn (explanations, visuals, practice, feedback, pace, tone) and updates Learning Profile.md. Use for "/profile", "update my learning style", "quiz me on how I like to learn", or when the tutor notices the profile is out of date.
---

# /profile: learning-preferences quiz

1. Read `Learning Profile.md`. Never overwrite §1 ({{NAME}}'s own words); only suggest additions to it.
2. Run 2–3 rounds of **AskUserQuestion** (up to 4 questions each; use `multiSelect` when options aren't exclusive). Skip anything the profile already answers clearly unless {{NAME}} asked for a full redo. Cover:
   - First contact with a concept: visual / derive with hints / plain intuition / worked example
   - Visuals: static graph, step-by-step annotated sequence, interactive (Desmos link), hand-sketch prompts
   - Practice: rebuild-from-understanding, multiple-choice checks, FRQ, timed sets, error-spotting ("find the bug in this solution")
   - When wrong: hint and retry / explain your reasoning / immediate explanation
   - Pace and length: one step per message vs chunks; how often to check
   - Tone: formal, casual, blunt, encouraging; how much small talk
   - Memorization: flashcards, mnemonics, or only understanding-based recall
   - Real-world hooks: tie to their own projects and hobbies or keep it abstract
   - Voice: whether they'll mostly dictate, and whether the tutor should prompt "talk me through it"
3. Also give one open question: "Describe a time learning went really well: what made it work?" ({{NAME}} can dictate the answer.)
4. Rewrite §2 with the answers (date-stamp it). Where §3 (observed patterns) contradicts a stated preference, point it out gently and ask which one to trust.
5. End with a 3-line summary of how sessions will now change.
