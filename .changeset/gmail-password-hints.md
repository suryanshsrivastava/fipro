---
"fipro": minor
---

Add `fipro gmail` (read-only Gmail) to save each bank's statement-password hint, and let `fipro dashboard` unlock and process password-protected statements by entering the password next to that hint. Locked statements are now left in `data/input/` instead of being moved to `data/failed/`, and a run that processes nothing no longer overwrites the previous exports.
