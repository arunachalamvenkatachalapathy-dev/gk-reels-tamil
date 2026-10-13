# Tamil GK automatic ready-video publishing

Slot openings: 06:00 and 15:00 Asia/Kolkata, two videos per day when exact approved assets are ready.

The clock check runs at UTC minutes 2, 17, 32 and 47. GitHub schedules can be delayed or dropped; no exact-time promise is made. Checks inside the two-hour slot windows record actual start drift in seconds. Routine operation does not require manual triggers.

The separate tamil-publication-state branch stores reservations and receipts. It is pushed before any upload. Pending or ambiguous uploads cannot be retried automatically. Reconcile the YouTube receipt first. Failed state pushes block the external upload.

All public videos require the owner's review of the exact video, destination, title and description. An approval record carries the original user message ID and date plus the exact file hash and metadata. No current blanket automatic-publish permission exists. Empty queue and publish_enabled=false are intentional until approval.

Repository secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN. The uploader verifies the OAuth channel is exactly UC5ZLfNHUI4z92IW69KVTGxg. Never copy another channel's token. Facebook and Instagram need their own verified Tamil destinations and permissions; they are not silently represented by the YouTube receipt.

Charon speech is generated outside the publisher; ready MP4s are queued only after visual and speech review. The repository's role here is publishing the ready reviewed video, not a fallback TTS voice.

Guide CTA is review-only until the guide and delivery route are available. The first owner's sample includes the requested wording for review, not a live fulfillment promise.
