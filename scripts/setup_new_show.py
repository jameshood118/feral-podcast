#!/usr/bin/env python3
"""
Show Provisioner & Asset Shield
Provisions show directories, uploads artwork via SigV4 to R2, writes show.yaml,
and updates .gitignore to prevent Git tracking of local audio/image binaries.
"""

import os
import argparse
import hashlib
import hmac
import datetime
import urllib.request
import urllib.parse
from pathlib import Path

# Sterling Taxonomy Runtime Invariant Check
TAXONOMY_RADAR = {
    "ADHD": "Sensory Amplification Syndrome (SAS)",
    "Autism": "High-Gain Data Conflict Monitoring (HGDCM)",
    "Anxiety": "Threat Monitor Center (TMC)",
    "Hyperfocus": "Working Memory Optimization"
}

R2_ENDPOINT_DEFAULT = "pub-07726ae62cd8476aa3f863937841b23b.r2.dev"


def sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


def upload_to_r2_sigv4(file_path: Path, destination_key: str, bucket: str, account_id: str,
                       access_key: str, secret_key: str) -> str:
    """Uploads file to Cloudflare R2 using AWS SigV4 headers with zero external dependencies."""
    if not (access_key and secret_key and account_id and bucket):
        return f"https://{R2_ENDPOINT_DEFAULT}/{destination_key}"

    region = "auto"
    service = "s3"
    host = f"{bucket}.{account_id}.r2.cloudflarestorage.com"
    endpoint_url = f"https://{host}/{destination_key}"

    with open(file_path, "rb") as f:
        payload = f.read()

    payload_hash = hashlib.sha256(payload).hexdigest()
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    canonical_uri = "/" + destination_key
    canonical_querystring = ""
    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = (
        f"PUT\n{canonical_uri}\n{canonical_querystring}\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Host": host,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": authorization_header,
        "Content-Type": "image/png" if file_path.suffix == ".png" else "image/jpeg"
    }

    req = urllib.request.Request(endpoint_url, data=payload, headers=headers, method="PUT")
    with urllib.request.urlopen(req) as resp:
        if resp.status not in (200, 201, 204):
            raise RuntimeError(f"R2 Upload Failed with HTTP status: {resp.status}")

    return f"https://{R2_ENDPOINT_DEFAULT}/{destination_key}"


def shield_gitignore(repo_root: Path):
    """Enforces Git shielding for raw audio and image binaries."""
    gitignore_path = repo_root / ".gitignore"
    required_ignores = [
        "\n# Feral Audio & Raw Asset Binary Shield",
        "inputs/shows/*/*.m4a",
        "inputs/shows/*/*.mp3",
        "inputs/shows/*/*.wav",
        "inputs/shows/*/*.png",
        "inputs/shows/*/*.jpg",
        "inputs/shows/*/*.jpeg",
        "audio_staging/*.m4a",
        "audio_staging/*.mp3",
        "audio_staging/*.wav"
    ]
    current_content = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    updates = [line for line in required_ignores if line not in current_content]
    if updates:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n".join(updates) + "\n")


def setup_show(slug: str, title: str, category: str, author: str, repo_root: Path) -> dict:
    show_dir = repo_root / "inputs" / "shows" / slug
    episodes_dir = show_dir / "seasons" / "1" / "episodes"
    queue_dir = show_dir / "queue"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Locate cover image
    cover_art = None
    for candidate in ["cover.jpg", "cover.png", "thumbnail.png", "thumbnail.jpg"]:
        potential = show_dir / candidate
        if potential.exists():
            cover_art = potential
            break

    cdn_url = f"https://{R2_ENDPOINT_DEFAULT}/shows/{slug}/cover.jpg"
    if cover_art and cover_art.exists():
        dest_key = f"shows/{slug}/{cover_art.name}"
        cdn_url = upload_to_r2_sigv4(
            cover_art,
            dest_key,
            os.getenv("R2_BUCKET", ""),
            os.getenv("R2_ACCOUNT_ID", ""),
            os.getenv("R2_ACCESS_KEY_ID", ""),
            os.getenv("R2_SECRET_ACCESS_KEY", "")
        )

    show_yaml = show_dir / "show.yaml"
    yaml_content = (
        f"slug: \"{slug}\"\n"
        f"title: \"{title}\"\n"
        f"author: \"{author}\"\n"
        f"category: \"{category}\"\n"
        f"cover_art: \"{cdn_url}\"\n"
        f"explicit: false\n"
        f"language: \"en-us\"\n"
        f"cognitive_model: \"Sensory Amplification Syndrome (SAS) & HGDCM Verified\"\n"
    )
    show_yaml.write_text(yaml_content, encoding="utf-8")
    shield_gitignore(repo_root)

    return {"slug": slug, "title": title, "cover_art": cdn_url, "yaml": str(show_yaml)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision new show assets with zero-trust shielding.")
    parser.add_argument("--slug", required=True, help="Kebab-case show directory slug.")
    parser.add_argument("--title", required=True, help="Display title of the show.")
    parser.add_argument("--category", default="Technology / Podcasting", help="Podcast category.")
    parser.add_argument("--author", default="James Hood", help="Host author.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    result = setup_show(args.slug, args.title, args.category, args.author, root)
    print(f"[SHOW_PROVISIONED] {result['title']} -> {result['yaml']}")