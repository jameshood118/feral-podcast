"""
Feral Podcast RSS Generator (Multi-Show / Sovereign Braid)
Show.yaml + Auto-README Updating Edition
"""

# region IMPORTS & GLOBALS
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
# endregion

# region SHOW RSS GENERATION
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
        print(f"Skipping '{show_slug}': Missing episodes dir at {episodes_dir}")
        return
        
    # Prepare output dir
    show_output_dir = os.path.join(OUTPUT_ROOT, show_slug)
    os.makedirs(show_output_dir, exist_ok=True)

    fg = FeedGenerator()
    fg.load_extension('podcast')

    # Apply Metadata from show.yaml
    show_title = show_meta.get("title", show_slug.replace("-", " ").title())
    fg.title(show_title)
    fg.description(show_meta.get("description", f"High-friction truths from {show_title}."))
    fg.link(href=show_meta.get("link", f"{BASE_URL}/{show_slug}"), rel='alternate')
    fg.language('en')

    # Universal iTunes Ecosystem Tags
    # pylint: disable=no-member
    fg.podcast.itunes_author(show_meta.get("author", "James Hood"))
    fg.podcast.itunes_category(show_meta.get("category", "Technology"), show_meta.get("subcategory", "Podcasting"))
    fg.podcast.itunes_explicit(show_meta.get("explicit", "no"))
    fg.podcast.itunes_owner(email=show_meta.get("email", "jameshood118@gmail.com"), name=show_meta.get("author", "James Hood"))
    if "image" in show_meta:
        fg.podcast.itunes_image(show_meta["image"])
    fg.podcast.itunes_type('episodic')

    episode_files = [f for f in os.listdir(episodes_dir) if f.endswith('.md')]
    
    if not episode_files:
        print(f"Skipping '{show_slug}': 'episodes' directory is empty.")
        return

    for filename in episode_files:
        filepath = os.path.join(episodes_dir, filename)
        post = frontmatter.load(filepath)

        # region THE GUID INJECTION PROTOCOL
        # ---------------------------------------------------------
        # WHAT THIS DOES:
        # If an episode markdown file is pushed WITHOUT a 'guid' in the YAML,
        # this block intercepts it, generates a true UUIDv4, injects it into
        # the frontmatter, and physically overwrites the .md file before continuing.
        # 
        # WHY IT MATTERS:
        # This guarantees the GUID never changes, even if you rename the file,
        # fix a typo, or change hosts. Apple Podcasts demands GUID stability.
        # ---------------------------------------------------------
        if 'guid' not in post.metadata:
            new_guid = str(uuid.uuid4())
            post.metadata['guid'] = new_guid
            
            # Write the modified frontmatter back to the physical file
            with open(filepath, 'w') as f:
                f.write(frontmatter.dumps(post))
            print(f"[{show_title}] Injected new persistent GUID into {filename}")
        # endregion

        fe = fg.add_entry()

        # Safely map the persistent GUID
        fe.id(post.metadata['guid'])
        fe.title(post.metadata['title'])
        fe.description(post.content)

        # Parse date and ensure UTC timezone awareness
        pub_date = datetime.strptime(post.metadata['date'], "%Y-%m-%dT%H:%M:%SZ")
        pub_date = pub_date.replace(tzinfo=pytz.UTC)
        fe.pubDate(pub_date)

        # Add the audio payload enclosure
        fe.enclosure(post.metadata['audio_url'], str(post.metadata['file_size']), 'audio/x-m4a')
        fe.podcast.itunes_duration(post.metadata['duration'])

        # Optional Episode-Level Taxonomy
        if 'season' in post.metadata:
            fe.podcast.itunes_season(int(post.metadata['season']))
        if 'episode_number' in post.metadata:
            fe.podcast.itunes_episode(int(post.metadata['episode_number']))

    output_file = os.path.join(show_output_dir, 'rss.xml')
    fg.rss_file(output_file)
    print(f"[{show_title}] RSS Feed generated successfully at {output_file}.")
# endregion

# region README UPDATING
def update_readme_with_feeds():
    """
    Scans inputs/show/ for show directories and dynamically updates the README.
    """
    if not os.path.exists(INPUT_ROOT):
        return

    shows = [d for d in os.listdir(INPUT_ROOT) if os.path.isdir(os.path.join(INPUT_ROOT, d))]
    
    lines = []
    for slug in shows:
        show_yaml_path = os.path.join(INPUT_ROOT, slug, "show.yaml")
        title = slug.replace("-", " ").title()
        if os.path.exists(show_yaml_path):
            with open(show_yaml_path, "r") as f:
                meta = yaml.safe_load(f)
                if meta and "title" in meta:
                    title = meta["title"]

        feed_url = f"{BASE_URL}/{slug}/rss.xml"
        lines.append(f"- **{title}**\n  {feed_url}\n")

    if not os.path.exists(README_PATH):
        return

    with open(README_PATH, "r") as f:
        content = f.read()

    # The exact markers the script looks for
    start = ""
    end = ""

    # FERAL SAFEGUARD: Prevent 'empty separator' crashes
    if not start or not end:
        print("Marker variables are empty. Skipping README update.")
        return

    if start not in content or end not in content:
        print("README missing FEEDS markers. No update performed.")
        return

    before = content.split(start)[0]
    after = content.split(end)[1]

    new_section = start + "\n" + "\n".join(lines) + "\n" + end

    with open(README_PATH, "w") as f:
        f.write(before + new_section + after)

    print("README.md updated with latest feed list.")
# endregion

# region MAIN EXECUTION
def scan_and_generate():
    """
    Main entry point. Scans inputs/show/ and triggers builds.
    """
    if not os.path.exists(INPUT_ROOT):
        print(f"Input directory '{INPUT_ROOT}' does not exist.")
        return

    shows = [d for d in os.listdir(INPUT_ROOT) if os.path.isdir(os.path.join(INPUT_ROOT, d))]
    
    if not shows:
        print("No show directories found under 'inputs/show/'.")
        return

    for show_slug in shows:
        generate_rss_for_show(show_slug)
        
    # Update README after processing all feeds
    update_readme_with_feeds()

if __name__ == "__main__":
    scan_and_generate()
# endregion