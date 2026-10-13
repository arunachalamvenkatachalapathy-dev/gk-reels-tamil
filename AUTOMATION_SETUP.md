# Tamil GK automatic ready-video publishing

Slot openings: 06:00 and 15:00 Asia/Kolkata, two videos per day when exact approved assets are ready.

The clock check runs at UTC minutes 2, 17, 32 and 47. GitHub schedules can be delayed or dropped; no exact-time promise is made. Checks inside the two-hour slot windows record actual start drift in seconds. Routine operation does not require manual triggers.

The separate tamil-publication-state branch stores reservations and receipts. It is pushed before any upload. Pending or ambiguous uploads cannot be retried automatically. Reconcile the YouTube receipt first. Failed state pushes block the external upload.

The owner approved full automation on 13 October 2026 at 12:04 IST after approving video 1. Two daily slots may publish source-reviewed Tamil videos in the approved format without per-video review. Charon remains the chosen voice. Exact asset hashes, destination and metadata are checked for every queue entry. Original approval IDs are retained in configuration/queue; quality review is separate from publishing authority. Ready-asset generation uses batches of Charon WAVs; a low buffer is a production blocker, not permission to switch voices.

Repository secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN. The uploader verifies the OAuth channel is exactly UC5ZLfNHUI4z92IW69KVTGxg. Never copy another channel's token. Facebook and Instagram need their own verified Tamil destinations and permissions; they are not silently represented by the YouTube receipt.

Charon speech is generated outside the publisher; ready MP4s are queued only after visual and speech review. The repository's role here is publishing the ready reviewed video, not a fallback TTS voice.

CTA keyword: gk snippets. The private 730 bank must not be distributed as the guide. The owner manages the shared government-paper Drive link and Meta reply fulfillment himself. No private bank audience is widened by video automation.
