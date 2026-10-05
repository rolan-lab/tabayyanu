# Privacy

**لا نخزّن النصوص التي تدخلها.** We do not store the texts you enter.

## What happens to your text

- The text you paste is sent to our server, checked in memory, and the result is sent back. It is not written to disk or a database.
- Server logs hold **counts and timings only**: number of quotations, their statuses, text length in characters, and milliseconds. Never the text itself.
- **When the AI model is enabled**, the text (or the quotation and the computed result) is sent to the configured model provider to extract quotations and write the short explanation. That provider's own privacy terms apply to that request. Without a model (`LLM_BACKEND=none`) nothing leaves our server.

## Learning-path guide

- Questions typed into the guide are not stored. When the model is enabled, the question is sent to the model provider only to pick search keywords and lessons.

## Links to other sites

- When a text is not found, the result offers a link to search it in Dorar al-Sunniyya's encyclopedia. Your text is sent to dorar.net only if you click that link.

## Error reports

- The "report an error" form saves a case **only if you tick the consent box**. The server refuses a report without consent.
- A saved report contains: the time, your quotation, the result status and reference, and your optional comment. No name, email or IP address is stored in it.
- Reports are kept in a file on the server (`data/reports/reports.jsonl`), are never committed to the code repository, and are used only to fix mistakes.

## Learning progress

- Lesson progress is stored **only in your own browser** (localStorage). It never reaches our server, and clearing your browser data removes it.

## Other

- No accounts, no cookies of our own, no analytics or advertising trackers.
- The page loads the IBM Plex Sans Arabic font from Google Fonts, so your browser contacts Google's font servers.
- Hosting providers may keep standard access logs (IP address, time, URL) under their own policies.
