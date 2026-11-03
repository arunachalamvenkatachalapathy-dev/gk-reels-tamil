"""Read-only audit of every stock ZIP in the Drive folder.

For each GK_TA_private_*.zip it downloads the archive, reads manifest.json and
runs the same validate_manifest the publisher uses, printing one line per ZIP:
qid, zip name, title length, and OK or the exact validation error. Never
mutates Drive or repo state; run it when a publish run fails on a bad ZIP.
"""
import io
import json
import zipfile

from stock_publish import ROOT, drive_client, list_stock, load, parse_stock_name, validate_manifest


def main():
    config = load(ROOT / "data/stock_config.json")
    drive = drive_client()
    stock = list_stock(drive, config["drive_folder_id"])
    quarantined = set(config.get("quarantined_ids", []))
    print(f"folder has {len(stock)} stock ZIPs; quarantined: {sorted(quarantined)}")
    bad = 0
    for item in sorted(stock, key=lambda f: f["name"]):
        qid = parse_stock_name(item["name"]) or "?"
        try:
            data = drive.files().get_media(fileId=item["id"]).execute()
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            v = validate_manifest(manifest, config["channel_id"])
            title = v.get("title", "")
            flag = " QUARANTINED" if qid in quarantined else ""
            print(f"OK   {qid} {item['name']} title_len={len(title)}{flag} :: {title[:70]}")
        except Exception as exc:
            bad += 1
            print(f"BAD  {qid} {item['name']} :: {type(exc).__name__}: {exc}")
    print(f"scan complete: {bad} bad of {len(stock)}")


if __name__ == "__main__":
    main()
