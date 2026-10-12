# Tamil question-bank conversion plan

Status: planning only. No full OCR run has started.

## Source and benchmark

Source: https://drive.google.com/file/d/1acRrumF720owcB17fO-nA7yRhP-QO_l7/view

File: 2026 to 2012 General Studies Questions_171 SET.pdf, 706,809,606 bytes, 9,954 A4 pages. It is predominantly scanned English/Tamil exam papers. Sampled text extraction found no question text; later pages contain only a website watermark.

Five-page Tamil+English OCR benchmark at 144 dpi: pages 3, 51, 301, 4978 and 9954 took 11.50, 8.43, 5.76, 13.26 and 14.52 seconds. Mean 10.694 sec/page. Serial OCR-only projection: 29.6 hours. Ideal four-worker projection: 7.4 hours; ideal eight-worker projection: 3.7 hours. These are arithmetic projections, not delivery promises: CPU contention, higher-resolution retries, rendering, extraction and answer review add time. Benchmark four workers on a bounded 100-page tranche before selecting concurrency.

Use resumable 100-page batches (roughly 17.8 minutes serial per batch), each with page IDs, hashes, OCR text and TSV coordinates. Do not keep thousands of page images in memory. Record every failed page and retry only that page. A full sweep is not needed to obtain the first reviewed 730 questions: first inventory set boundaries and select diverse static-GK tranches, then stop at a sufficiently reviewed buffer.

## Accuracy gates

Tamil prose is mostly recoverable; labels, roman numerals and digits are not reliable. Observed 3-to-8 substitutions, A/C/D corrupted by handwritten ticks, and fragmented numbering. Use OCR coordinates for question and option blocks, detect bilingual versions as one question, and verify the scan pixels whenever symbols, dates, match tables or negation matter. Older pages need a higher-resolution retry. OCR output is candidate material, never a reviewed answer.

Preserve source PDF page, set code, question number and original Tamil text. Rewrite only enough for a readable short quiz; preserve meaning and all four substantive options. Omit an extra "Answer not known" choice where present. Matching/assertion questions must not be flattened in a way that changes their logic.

## Question selection and duplicates

Keep static science, history, polity, geography, culture and historical Tamil Nadu facts. Exclude contemporary office-holders, changing ranks/statistics, recent events and other current-affairs items. Mark borderline scheme questions for review rather than auto-import.

Normalize Unicode, whitespace, option ordering and punctuation. First deduplicate exact Tamil stems, then English counterparts, then compare semantic near-duplicates across sets. One bilingual question counts once. Keep merged provenance for repeats. Manually review numerical and negative-question near-duplicates because "not", a year or a quantity may make them different.

The five sampled pages contain about nine distinct stems and no observed cross-page repeat. This sample is insufficient for a defensible archive duplicate rate, exact question count or unique yield. Do not claim 171 sets implies a particular number of unique questions. A stratified 100-page tranche plus set-boundary inventory is the next measurable step.

## Answers and disputed items

Use official TNPSC final answer keys matched to exam date, paper/set and question number. Tentative keys, handwritten ticks and coaching-book annotations are hints only. If an official key flags a question for an expert committee, drops it, awards multiple answers or changes its answer, quarantine it until final resolution; do not render it.

Where a final key cannot be located, verify against a primary source: NCERT/SCERT textbook edition and page for syllabus facts, legislation/official constitutional text for polity, government departments for historical schemes, or a primary scientific/public institution for scientific facts. Store explanation, exact source_url, source_label and verification note in reviewed_ta.json keyed by question id. Never invent a source URL.

Example already checked: PDF page 51 Q56, DANIDA-TNAHCP health-sector question. Primary source: https://tnhealth.tn.gov.in/tngovin/danida.php . The Health Department explicitly describes the rural health and family-welfare purpose. Its dated wording is used only as evidence about the historical project, not a claim it is current.

## Output and release gate

Use the Hindi format unchanged: questions_ta.json is a list with id, question, options, correct_index, used plus provenance; reviewed_ta.json is a dict keyed by id with checked explanation/source and display/speech overrides. Keep candidates separate from reviewed entries. Run schema, four-option, answer-index, dedup and explanation checks before commit. Render representative reviewed items and inspect pixels plus Tamil speech.

No full-bank run, publishing, schedules, manual dispatch, credentials or paid OCR service until Arun reviews this plan. Publishing slot times remain unconfirmed and disabled.
