# Tamil setup status

Existing private scaffold was preserved. New code/documents are committed; bank, asset and entry-point installation remains incomplete. The Hindi repository was read only.

Prepared a Hindi studio-arena renderer adapted to Tamil labels/font, a local dry-run entry point, one source-checked sample question from the designated PDF, and pure IST slot-gate planning/tests. Only the new files were committed; the sample banks, assets and updated existing entry point are still pending exact-path installation. The sample is page 51 question 56, independently verified against the Tamil Nadu Health Department. It is not a complete question bank.

`data/slots.json` deliberately has null morning/afternoon values pending owner confirmation. `slot_gate.py` selects the earliest opened unpublished slot for the current IST date, one per call. Slots have explicit date+slot keys. Pending/ambiguous external results block repeat publication until reconciliation. Questions are consumed only after destination receipts. Future integration must persist state atomically before external calls, use a global single-run concurrency lock and reconcile upload receipts before retrying. Prior-day misses require owner approval; no automatic catch-up.

Publishing remains unwired and Actions disabled. No dispatch or scheduled run was invoked. For future activation only: derive retry UTC crons from confirmed IST openings, offset retry minutes such as :07/:23/:41 from round hours, permit retries within opened windows, and keep one video/run. Do not activate before timing, destination authority and credentials are resolved.

Voice: Edge Tamil TTS returned HTTP 403 locally. A 13-second music-only visual proof was made and labeled; it is not the spoken sample. Hindi production code uses Fish Audio `s2.1-pro-free` with a repo secret. Fish supports Tamil, but a Tamil voice selection and actual audio review remain outstanding. Never silently fall back to a paid model. No secrets were copied or read.

Full OCR is on hold. See CONVERSION_PLAN.md for benchmark and review gates. Exact total and unique question counts remain unknown.
