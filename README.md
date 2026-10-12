# GK Snippets Tamil

Private Tamil GK short-video pipeline. This repository is separate from the English and Hindi projects.

## Current bank

The bilingual bank is a source-checked, scan-checked editorial review copy. Final whole-file adviser review is still in progress. No official TNPSC answer key is claimed. Printed or handwritten scan marks are not answer verification.

- `data/bank_730_review_pending.json`: four-choice bilingual review checkpoint, with answer index and source ID. The renderer input `data/questions_ta.json` stays separate and empty until release.
- Full editorial rows and source repair records are preserved separately during review; the checkpoint is not a final release.
- `data/editorial_change_ledger.json`: original and edited fields, with reasons.
- Semantic duplicate decisions remain in the review ledger until the final checkpoint update.
- `data/bank_release_status.json`: current count and release state.

Do not describe a review copy as a final learner guide. Adviser claims are not official answer keys. A guide link is added only after the final review and release decision.

## Publishing holds

No upload is authorized by a bank commit. YouTube publishing remains held until the Tamil Charon sample is approved. The pipeline checks the exact Tamil channel, question ID, video hash, title and description against the approval record. A pending external upload must be reconciled before retrying.

The requested guide CTA is unchanged. Do not use it for a live release until the final book and its link exist. Review-only rendering does not publish.

YouTube channel ID: `UC5ZLfNHUI4z92IW69KVTGxg`.

## Voice and rendering

`run_pipeline.py` requires a Charon speech manifest for the chosen question. There is no fallback voice. The renderer uses bilingual reviewed text and refuses missing answer, explanation or source fields. Bank inclusion alone does not supply short-video explanations or voice approval.

## Secrets

Keep credentials only in repository Actions secrets. Never commit them or print them in logs. YouTube credentials must resolve to the Tamil channel before upload. Facebook and Instagram access must be checked separately.

## Checks

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate_bank.py
```

The bank validator checks structure, unique IDs, count, bilingual choices and answer alignment. It does not grant factual clearance or enable publishing.
