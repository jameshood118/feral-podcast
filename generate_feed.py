"""
Feral Podcast RSS Generator (Multi-Show / Sovereign Braid)
Show.yaml + Auto-README Updating Edition
"""

import os
import uuid
from datetime import datetime
import yaml
import frontmatter
import pytz
from feedgen.feed import FeedGenerator

INPUT_ROOT = os.path.join("inputs", "show")
OUTPUT_ROOT = os.path.join("outputs", "show")
README_PATH = "README.md"
BASE_URL = "https://jameshood118.github.io/feral-podcast/outputs/show"


def generate_rss_for_show(show_slug):
    """
    Reads:
        inputs/show/{show_slug}/show.yaml
        inputs/show/{show_slug}/episodes/*.md
    Outputs:
        outputs/show/{show_slug}/rss.xml
    """

    show_input_dir = os.path.join(INPUT_ROOT, show_slug)
    episodes_dir = os.path.join(show_input_dir, "episodes")
    show_yaml_path = os.path.join(show_input_dir, "show.yaml")

    # Validate show.yaml exists
    if not os.path.exists(show_yaml_path):
        print(f"Skipping '{show_slug}': Missing show.yaml at {show_yaml_path}")
        return

    # Load show metadata
    with open(show_yaml_path, "r") as f:
        show_meta = yaml.safe_load(f)

    # Validate episodes directory
    if not os.path.exists(episodes_dir):
        print(f"Skipping '{show_slug}': No episodes directory at {episodes_dir}")
        return

    episode_files = [f for f in os.listdir(episodes_dir) if f.endswith(".md")]
    if not episode_files:
        print(f"Skipping '{show_slug}': No episode files found.")
        return

    # Initialize feed
    fg = FeedGenerator()
    fg.load_extension("podcast")

    # Show-level metadata from show.yaml
    fg.title(show_meta["title"])
    fg.description(show_meta["description"])
    fg.link(href=show_meta["link"], rel="alternate")
    fg.language("en")

    # iTunes metadata
    # pylint: disable=no-member
    fg.podcast.itunes_author(show_meta["author"])
    fg.podcast.itunes_owner(email=show_meta["email"], name=show_meta["author"])
    fg.podcast.itunes_image(show_meta["image"])
    fg.podcast.itunes_category(show_meta["category"], show_meta.get("subcategory", None))
    fg.podcast.itunes_explicit(show_meta.get("explicit", "no"))
    fg.podcast.itunes_type("episodic")

    # Process episodes
    for filename in episode_files:
        filepath = os.path.join(episodes_dir, filename)
        post = frontmatter.load(filepath)

        fe = fg.add_entry()

        # GUID (persistent)
        guid = post.get("guid")
        if not guid:
            guid = str(uuid.uuid5(uuid.NAMESPACE_URL, post.get("audio_url", filename)))
        fe.id(guid)

        # Episode metadata
        fe.title(post["title"])
        fe.description(post.content)

        pub_date = datetime.strptime(post["date"], "%Y-%m-%dT%H:%M:%SZ")
        pub_date = pub_date.replace(tzinfo=pytz.UTC)
        fe.pubDate(pub_date)

        fe.enclosure(post["audio_url"], str(post["file_size"]), "audio/mpeg")
        fe.podcast.itunes_duration(post["duration"])

        # Optional taxonomy
        if "season" in post:
            fe.podcast.itunes_season(int(post["season"]))
        if "episode_number" in post:
            fe.podcast.itunes_episode(int(post["episode_number"]))

    # Output directory per show
    show_output_dir = os.path.join(OUTPUT_ROOT, show_slug)
    os.makedirs(show_output_dir, exist_ok=True)

    output_file = os.path.join(show_output_dir, "rss.xml")
    fg.rss_file(output_file)

    print(f"[{show_meta['title']}] RSS generated → {output_file}")


def update_readme():
    """
    Auto-updates README.md between markers:
    <!-- FEEDS-START -->
    <!-- FEEDS-END -->
    """

    if not os.path.exists(OUTPUT_ROOT):
        print("No outputs/show directory found. README not updated.")
        return

    shows = [
        d for d in os.listdir(OUTPUT_ROOT)
        if os.path.isdir(os.path.join(OUTPUT_ROOT, d))
    ]

    lines = ["## Podcast Feeds\n"]

    for slug in shows:
        # Load show.yaml to get real show title
        show_yaml_path = os.path.join(INPUT_ROOT, slug, "show.yaml")
        if os.path.exists(show_yaml_path):
            with open(show_yaml_path, "r") as f:
                meta = yaml.safe_load(f)
            title = meta["title"]
        else:
            title = slug.replace("-", " ").title()

        feed_url = f"{BASE_URL}/{slug}/rss.xml"
        lines.append(f"- **{title}**\n  {feed_url}\n")

    with open(README_PATH, "r") as f:
        content = f.read()

    start = "<!-- FEEDS-START -->"
    end = "<!-- FEEDS-END -->"

    if start not in content or end not in content:
        print("README missing FEEDS markers. No update performed.")
        return

    before = content.split(start)[0]
    after = content.split(end)[1]

    new_section = start + "\n" + "\n".join(lines) + "\n" + end

    with open(README_PATH, "w") as f:
        f.write(before + new_section + after)

    print("README.md updated with latest feed list.")


def scan_and_generate():
    """
    Scans inputs/show/ for show directories.
    """

    if not os.path.exists(INPUT_ROOT):
        print(f"Input directory '{INPUT_ROOT}' does not exist.")
        return

    shows = [
        d for d in os.listdir(INPUT_ROOT)
        if os.path.isdir(os.path.join(INPUT_ROOT, d))
    ]

    if not shows:
        print("No shows found in inputs/show/")
        return

    for show_slug in shows:
        generate_rss_for_show(show_slug)


if __name__ == "__main__":
    scan_and_generate()
    update_readme()
