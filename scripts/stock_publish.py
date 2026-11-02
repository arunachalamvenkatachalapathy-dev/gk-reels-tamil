"""Tamil GK Drive-stock publisher.

Publishes the next positively-cleared video straight from the owner's private
Drive stock (his approved plan, 2026-10-31): read-only keyless service account,
one video per due IST slot, YouTube only until a Meta identity is verified.
Never touches the question bank. Fails loudly; reserves state before upload.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IST = timezone(timedelta(hours=5, minutes=30))
ZIP_NAME = re.compile(r"^GK_TA_private_(p\d+-e\d+)\.zip$")
TAMIL_CHAR = re.compile(r"[஀-௿]")
DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]


def load(p):
    return json.loads(Path(p).read_text())


def save(p, x):
    Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n")


def persist(state_dir, state, config, note):
    save(state_dir / config["state_file"], state)
    subprocess.run(["git", "-C", str(state_dir), "add", config["state_file"]],
                   check=True, stdout=subprocess.DEVNULL)
    dirty = subprocess.run(["git", "-C", str(state_dir), "diff", "--cached", "--quiet"]).returncode != 0
    if not dirty:
        return
    for args in (
        ("commit", "-m", note),
        ("push", "origin", "HEAD:" + config["state_branch"]),
    ):
        subprocess.run(["git", "-C", str(state_dir), *args], check=True, stdout=subprocess.DEVNULL)


def parse_stock_name(name):
    """Question id from a stock ZIP name, or None for pilots/records/foreign files."""
    m = ZIP_NAME.match(name)
    return m.group(1) if m else None


def select_slot(now, config, state):
    local = now.astimezone(IST)
    today = local.date().isoformat()
    for name, clock in config["slots"].items():
        h, m = map(int, clock.split(":"))
        opening = local.replace(hour=h, minute=m, second=0, microsecond=0)
        lag = (local - opening).total_seconds()
        key = f"{today}:{name}"
        if name == "afternoon" and today <= config.get("studio_evening_until", ""):
            continue  # owner-scheduled Studio uploads hold the evening slot until that date
        if 0 <= lag < config["window_minutes"] * 60 and state.get("slots", {}).get(key, {}).get("status") != "published":
            return {"key": key, "slot": name, "opens_at": opening.isoformat(), "drift_seconds": round(lag)}
    return None


def select_run_slot(now, config, state, mode):
    if mode in ("facebook-retry", "instagram-retry"):
        return None
    if mode == "scheduled":
        return select_slot(now, config, state)
    local = now.astimezone(IST)
    return {"key": f"manual:{local.date()}", "slot": "manual", "opens_at": now.isoformat(), "drift_seconds": 0}


def dispatch_mode(event, mode=None):
    if event != "workflow_dispatch":
        return "scheduled"
    mode = mode or "manual"
    if mode not in ("manual", "scheduled", "facebook-retry", "instagram-retry"):
        raise ValueError("Invalid dispatch mode")
    return mode


def validate_title(title):
    if not title or len(title) > 100:
        raise ValueError("Invalid title length")
    if TAMIL_CHAR.search(title):
        raise ValueError("YouTube title must be English; Tamil script is not allowed")


def validate_manifest(manifest, channel_id):
    if manifest.get("destination_channel_id") != channel_id:
        raise ValueError("Stock manifest targets a different channel")
    videos = manifest.get("videos") or []
    if len(videos) != 1:
        raise ValueError("Stock ZIP must carry exactly one video manifest")
    v = videos[0]
    validate_title(v.get("title", ""))
    if len(v.get("description", "")) > 5000:
        raise ValueError("Description too long")
    if not (0 < float(v.get("duration", 0)) <= 35.0):
        raise ValueError("Stock video exceeds the 35 s format cap")
    if not v.get("file") or not v.get("sha256"):
        raise ValueError("Manifest missing file or sha256")
    return v


def drive_client():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    raw = os.environ.get("GDRIVE_SA_KEY_JSON", "").strip()
    if not raw:
        raise RuntimeError("Missing repository secret: GDRIVE_SA_KEY_JSON")
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=DRIVE_SCOPE)
    return build("drive", "v3", credentials=creds)


def list_stock(drive, folder_id):
    items, token = [], None
    while True:
        resp = (
            drive.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false and name contains 'GK_TA_private_'",
                fields="nextPageToken, files(id,name,md5Checksum,size)",
                pageSize=1000,
                pageToken=token,
                orderBy="name",
            )
            .execute()
        )
        items.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            return items


def download_zip(drive, file_id, dest):
    from googleapiclient.http import MediaIoBaseDownload

    request = drive.files().get_media(fileId=file_id)
    with open(dest, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def recent_titles(youtube, scan):
    """Titles of the channel's recent uploads, including private/scheduled ones (owner OAuth)."""
    channels = youtube.channels().list(part="contentDetails", mine=True).execute().get("items", [])
    if len(channels) != 1:
        raise RuntimeError("OAuth identity mismatch while reading uploads playlist")
    uploads = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    titles, token = set(), None
    while len(titles) < scan:
        resp = (
            youtube.playlistItems()
            .list(part="snippet", playlistId=uploads, maxResults=min(50, scan), pageToken=token)
            .execute()
        )
        for item in resp.get("items", []):
            titles.add(item["snippet"].get("title", ""))
        token = resp.get("nextPageToken")
        if not token or len(resp.get("items", [])) == 0:
            break
    return titles


def choose_candidates(stock, config, state):
    published = set(state.get("published_ids", []))
    published.update(
        x.get("question_id") for x in state.get("slots", {}).values() if x.get("status") in ("pending", "ambiguous", "published")
    )
    blocked = set(config.get("quarantined_ids", []))
    out = []
    for item in sorted(stock, key=lambda f: f["name"]):
        qid = parse_stock_name(item["name"])
        if qid and qid not in published and qid not in blocked:
            out.append((qid, item))
    return out




def ig_caption_for(manifest):
    title = manifest.get("title", "").strip()
    tags = manifest.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    hashtags = ["#" + re.sub(r"[^0-9A-Za-z]+", "", str(t)) for t in tags]
    hashtags = [h for h in hashtags if len(h) > 1][:15]
    return (title + "\n\n" + " ".join(hashtags)).strip()[:2100]

def retry_facebook_failures(sd, state, config, drive, work):
    """Re-attempt Facebook for slots whose YouTube receipt is confirmed but whose
    Facebook destination failed. Never picks a new video; re-fetches the exact
    reserved asset from Drive and re-verifies its hash before upload."""
    if not (config.get("facebook_enabled") or config.get("instagram_enabled")):
        return
    today = datetime.now(IST).date().isoformat()
    pending = []
    for k, s in sorted(state.get("slots", {}).items()):
        if s.get("status") != "published":
            continue
        errs = s.get("destination_errors", {})
        if "facebook" in errs or "instagram" in errs:
            pending.append((k, s))
        elif config.get("instagram_enabled") and today in k and "instagram" not in s.get("destinations", {}):
            errs["instagram"] = "backfill: instagram enabled after publish"
            pending.append((k, s))
    if not pending:
        return
    sys.path.insert(0, str(ROOT / "scripts"))
    import meta_publish
    meta_publish.preflight_facebook()
    stock = list_stock(drive, config["drive_folder_id"])
    by_qid = {}
    for item in stock:
        q = parse_stock_name(item["name"])
        if q:
            by_qid[q] = item
    for key, slot in pending[:2]:
        qid = slot.get("question_id")
        item = by_qid.get(qid)
        if not item:
            raise RuntimeError(f"Facebook retry for {key}: stock asset {qid} not found in Drive")
        zip_path = work / item["name"]
        download_zip(drive, item["id"], zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            manifest = validate_manifest(json.loads(zf.read("manifest.json").decode("utf-8")), config["channel_id"])
            video_bytes = zf.read(manifest["file"])
        if hashlib.sha256(video_bytes).hexdigest() != manifest["sha256"]:
            raise ValueError(f"Stock video hash mismatch for {qid}")
        errors = slot.get("destination_errors", {})
        destinations = slot.setdefault("destinations", {})
        video_path = None
        if config.get("facebook_enabled") and "facebook" in errors:
            existing = meta_publish.find_recent_reel(manifest["title"], slot.get("published_at"))
            if existing:
                receipt = existing
                print(f"Facebook retry adopted existing reel for {qid}: {receipt['id']}")
            else:
                video_path = work / manifest["file"]
                video_path.write_bytes(video_bytes)
                receipt = meta_publish.publish_facebook_reel(str(video_path), manifest["title"], manifest["description"], lambda cp: None)
            destinations["facebook"] = receipt
            errors.pop("facebook", None)
            persist(sd, state, config, f"Record retried Tamil stock Facebook receipt for {qid}")
            print(f"Facebook retry published {qid}: {receipt if isinstance(receipt, str) else receipt.get('id')}")
        if config.get("instagram_enabled") and "instagram" in errors:
            existing = meta_publish.find_recent_ig_reel(manifest["title"], slot.get("published_at"))
            if existing:
                destinations["instagram"] = existing
                print(f"Instagram retry adopted existing reel for {qid}: {existing['id']}")
            else:
                if video_path is None:
                    video_path = work / manifest["file"]
                    video_path.write_bytes(video_bytes)
                public_url = meta_publish.host_on_github_release(
                    str(video_path), "ig-host-" + key.replace(":", "-") + "-" + qid, manifest["file"])
                meta_publish.public_video(public_url, manifest["sha256"])
                receipt = meta_publish.publish_reel(public_url, ig_caption_for(manifest), lambda cp: None)
                destinations["instagram"] = receipt
            errors.pop("instagram", None)
            persist(sd, state, config, f"Record retried Tamil stock Instagram receipt for {qid}")
            print(f"Instagram retry published {qid}: {destinations['instagram'].get('id')}")

def main():
    config = load(ROOT / "data/stock_config.json")
    sd = Path(os.environ["PUBLICATION_STATE_DIR"])
    state_path = sd / config["state_file"]
    state = load(state_path) if state_path.is_file() else {"slots": {}, "published_ids": [], "checks": [], "skipped_external": []}
    now = datetime.now(timezone.utc)
    mode = dispatch_mode(os.getenv("GITHUB_EVENT_NAME"), os.getenv("DISPATCH_MODE"))
    slot = select_run_slot(now, config, state, mode)
    state.setdefault("checks", []).append(
        {"at": now.isoformat(), "run_id": os.getenv("GITHUB_RUN_ID"), "event": os.getenv("GITHUB_EVENT_NAME"), "slot": slot, "mode": mode}
    )
    state["checks"] = state["checks"][-500:]
    if config.get("facebook_enabled") or config.get("instagram_enabled"):
        retry_drive = drive_client()
        retry_work = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "tamil-stock-retry"
        retry_work.mkdir(parents=True, exist_ok=True)
        retry_facebook_failures(sd, state, config, retry_drive, retry_work)
    if not slot:
        persist(sd, state, config, "Record Tamil stock slot check")
        print("No active IST slot")
        return
    previous = state.setdefault("slots", {}).get(slot["key"], {})
    if previous.get("status") in ("pending", "ambiguous"):
        persist(sd, state, config, "Record blocked pending Tamil stock publication")
        raise RuntimeError("Reconcile pending receipt before retry")
    fb_enabled = config.get("facebook_enabled", False)
    ig_enabled = config.get("instagram_enabled", False)
    if not ig_enabled:
        print("Instagram disabled: Tamil IG publishing needs a Page token with instagram_basic and instagram_content_publish (pending owner).")

    drive = drive_client()
    stock = list_stock(drive, config["drive_folder_id"])
    candidates = choose_candidates(stock, config, state)
    if not candidates:
        persist(sd, state, config, "Record Tamil stock slot with no eligible candidate")
        print("No eligible stock candidate")
        return

    sys.path.insert(0, str(ROOT / "scripts"))
    from upload_youtube import get_youtube_client, upload_short

    for name in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        if not os.getenv(name):
            raise RuntimeError("Missing repository secret: " + name)
    os.environ["YT_CHANNEL_ID"] = config["channel_id"]
    youtube = get_youtube_client()
    known_titles = recent_titles(youtube, int(config.get("recent_upload_scan", 50)))

    work = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "tamil-stock"
    work.mkdir(parents=True, exist_ok=True)
    chosen = None
    for qid, item in candidates:
        zip_path = work / item["name"]
        download_zip(drive, item["id"], zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            manifest = validate_manifest(json.loads(zf.read("manifest.json").decode("utf-8")), config["channel_id"])
            video_bytes = zf.read(manifest["file"])
        if hashlib.sha256(video_bytes).hexdigest() != manifest["sha256"]:
            raise ValueError(f"Stock video hash mismatch for {qid}")
        if manifest["title"] in known_titles:
            state.setdefault("skipped_external", []).append({"question_id": qid, "reason": "title already on channel", "at": now.isoformat()})
            print(f"Skip {qid}: its title is already uploaded on the channel (owner-scheduled copy).")
            continue
        chosen = (qid, manifest, video_bytes)
        break
    if not chosen:
        persist(sd, state, config, "Record Tamil stock slot with all candidates skipped")
        print("All candidates skipped")
        return

    qid, manifest, video_bytes = chosen
    video_path = work / manifest["file"]
    video_path.write_bytes(video_bytes)
    state["slots"][slot["key"]] = dict(slot, status="pending", question_id=qid, sha256=manifest["sha256"], run_id=os.getenv("GITHUB_RUN_ID"))
    persist(sd, state, config, "Reserve exact Tamil stock asset before external upload")
    try:
        receipt = upload_short(str(video_path), manifest["title"], manifest["description"], manifest.get("tags"))
    except Exception:
        state["slots"][slot["key"]]["status"] = "ambiguous"
        persist(sd, state, config, "Hold uncertain Tamil stock upload for reconciliation")
        raise
    destinations = {"youtube": receipt}
    state["slots"][slot["key"]].update(status="published", youtube_id=receipt, destinations=destinations, published_at=datetime.now(timezone.utc).isoformat())
    state.setdefault("published_ids", []).append(qid)
    persist(sd, state, config, "Record confirmed Tamil stock YouTube receipt")
    if fb_enabled:
        try:
            import meta_publish
            meta_publish.preflight_facebook()
            fb_receipt = meta_publish.publish_facebook_reel(str(video_path), manifest["title"], manifest["description"], lambda cp: None)
            destinations["facebook"] = fb_receipt
            state["slots"][slot["key"]]["destinations"] = destinations
            persist(sd, state, config, "Record confirmed Tamil stock Facebook receipt")
        except Exception as exc:
            state["slots"][slot["key"]].setdefault("destination_errors", {})["facebook"] = str(exc)[:200]
            persist(sd, state, config, "Record Tamil stock Facebook destination failure")
            raise
    if ig_enabled:
        try:
            import meta_publish as mp
            mp.preflight()
            public_url = mp.host_on_github_release(str(video_path), "ig-host-" + slot["key"].replace(":", "-") + "-" + qid, manifest["file"])
            mp.public_video(public_url, manifest["sha256"])
            ig_receipt = mp.publish_reel(public_url, ig_caption_for(manifest), lambda cp: None)
            destinations["instagram"] = ig_receipt
            state["slots"][slot["key"]]["destinations"] = destinations
            persist(sd, state, config, "Record confirmed Tamil stock Instagram receipt")
        except Exception as exc:
            state["slots"][slot["key"]].setdefault("destination_errors", {})["instagram"] = str(exc)[:200]
            persist(sd, state, config, "Record Tamil stock Instagram destination failure")
            raise
    print(json.dumps({"question_id": qid, "youtube_id": receipt, "destinations": {k: (v if isinstance(v, str) else v.get("id")) for k, v in destinations.items()}, "slot": slot["key"], "drift_seconds": slot["drift_seconds"]}))


if __name__ == "__main__":
    main()
