"""
Feral Podcast RSS Generator (Multi-Show / Sovereign Braid)
Show.yaml + Auto-README + Mutagen Telemetry + UTF-8 Hardened
"""

# region IMPORTS & GLOBALS
import os
import uuid
import urllib.parse
from datetime import datetime, timedelta
import yaml
import frontmatter
import pytz
from feedgen.feed import FeedGenerator
from tinytag import TinyTag
import markdown
# endregion

# region CONSTANTS

INPUT_ROOT = os.path.join("inputs", "show")
OUTPUT_ROOT = os.path.join("outputs", "show")
README_PATH = "README.md"
BASE_URL = "https://jameshood118.github.io/feral-podcast/outputs/show"
LOCAL_AUDIO_DIR = os.path.join(".", "audio_staging")
# endregion

# region SHOW RSS GENERATION
def generate_rss_for_show(show_slug):
    show_input_dir = os.path.join(INPUT_ROOT, show_slug)
    episodes_dir = os.path.join(show_input_dir, "episodes")
    show_yaml_path = os.path.join(show_input_dir, "show.yaml")

    if not os.path.exists(show_yaml_path):
        print(f"Skipping '{show_slug}': Missing show.yaml at {show_yaml_path}")
        return

    # UTF-8 Hardened Read
    with open(show_yaml_path, "r", encoding="utf-8") as f:
        show_meta = yaml.safe_load(f)

    if not os.path.exists(episodes_dir):
        print(f"Skipping '{show_slug}': Missing episodes dir at {episodes_dir}")
        return
        
    show_output_dir = os.path.join(OUTPUT_ROOT, show_slug)
    os.makedirs(show_output_dir, exist_ok=True)

    fg = FeedGenerator()
    fg.load_extension('podcast')

    show_title = show_meta.get("title", show_slug.replace("-", " ").title())
    fg.title(show_title)
    fg.description(show_meta.get("description", f"High-friction truths from {show_title}."))
    fg.link(href=show_meta.get("link", f"{BASE_URL}/{show_slug}"), rel='alternate')
    fg.language('en')

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

    # THE CHRONOLOGICAL SORT PROTOCOL
    parsed_episodes = []

    for filename in episode_files:
        filepath = os.path.join(episodes_dir, filename)
        
        with open(filepath, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            
        needs_save = False

        # region 1. GUID INJECTION
        if 'guid' not in post.metadata:
            new_guid = str(uuid.uuid4())
            post.metadata['guid'] = new_guid
            needs_save = True
            print(f"[{show_title}] Injected new persistent GUID into {filename}")
        # endregion

        # region 2. FERAL TELEMETRY (TINYTAG)
        current_size = str(post.metadata.get('file_size', ''))
        current_duration = str(post.metadata.get('duration', ''))

        if current_size == '[SIZE_IN_BYTES]' or current_duration in ['[HH:MM:SS]', '[DURATION]', '00:00:00'] or not current_size or not current_duration:
            audio_url = post.metadata.get('audio_url', '')
            audio_filename = urllib.parse.unquote(audio_url.split('/')[-1])
            local_audio_path = os.path.join(LOCAL_AUDIO_DIR, audio_filename)

            if os.path.exists(local_audio_path):
                try:
                    # Inject Byte Size
                    size_bytes = os.path.getsize(local_audio_path)
                    post.metadata['file_size'] = str(size_bytes)

                    # Honey Badger Duration Extraction
                    tag = TinyTag.get(local_audio_path)
                    if tag.duration is not None and tag.duration > 0:
                        duration_seconds = int(tag.duration)
                        formatted_duration = str(timedelta(seconds=duration_seconds))
                        
                        if len(formatted_duration.split(':')) == 2:
                            formatted_duration = f"00:{formatted_duration}"
                        elif len(formatted_duration) == 7: 
                            formatted_duration = f"0{formatted_duration}"
                        
                        post.metadata['duration'] = formatted_duration
                        needs_save = True
                        print(f"[{show_title}] Injected Size ({size_bytes}) & Duration ({formatted_duration}) into {filename}")
                    else:
                        print(f"[WARNING] TinyTag could not calculate duration for {audio_filename}")
                except Exception as e:
                    print(f"[WARNING] TinyTag failed to parse {audio_filename}: {e}")
            else:
                pass 
        # endregion
        if needs_save:
            with open(filepath, 'w', encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

        # Parse the date so we can sort mathematically
        pub_date = datetime.strptime(post.metadata['date'], "%Y-%m-%dT%H:%M:%SZ")
        pub_date = pub_date.replace(tzinfo=pytz.UTC)
        
        # Store in memory
        parsed_episodes.append({
            'post': post,
            'pub_date': pub_date
        })

    # FERAL ALIGNMENT: Sort descending by date (Newest episodes at the top)
    parsed_episodes.sort(key=lambda x: x['pub_date'], reverse=True)

    # Build the final XML strictly in the sorted order
    for ep in parsed_episodes:
        post = ep['post']
        fe = fg.add_entry()
        fe.id(post.metadata['guid'])
        fe.title(post.metadata['title'])
        # region 3. THE TRANSLATION LAYER
        # Convert raw Markdown content into clean HTML for the RSS feed
        html_description = markdown.markdown(post.content)
        
        # Feed the HTML into the standard description tag
        fe.description(html_description)
        
        # Feed the HTML into the <content:encoded> tag (Crucial for Apple Podcasts & Substack)
        fe.content(html_description)
        # endregion
        fe.pubDate(ep['pub_date'])
        fe.enclosure(post.metadata['audio_url'], str(post.metadata.get('file_size', '0')), 'audio/x-m4a')
        fe.podcast.itunes_duration(post.metadata.get('duration', '00:00:00'))

        if 'season' in post.metadata:
            fe.podcast.itunes_season(int(post.metadata['season']))
        if 'episode_number' in post.metadata:
            fe.podcast.itunes_episode(int(post.metadata['episode_number']))

    output_file = os.path.join(show_output_dir, 'rss.xml')
    # Use explicit encoding for writing the XML file via feedgen if needed, but feedgen handles it.
    fg.rss_file(output_file)
    print(f"[{show_title}] RSS Feed generated successfully at {output_file}.")
# endregion

# region README UPDATING
def update_readme_with_feeds():
    if not os.path.exists(INPUT_ROOT):
        return

    shows = [d for d in os.listdir(INPUT_ROOT) if os.path.isdir(os.path.join(INPUT_ROOT, d))]
    
    lines = []
    for slug in shows:
        show_yaml_path = os.path.join(INPUT_ROOT, slug, "show.yaml")
        title = slug.replace("-", " ").title()
        if os.path.exists(show_yaml_path):
            with open(show_yaml_path, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f)
                if meta and "title" in meta:
                    title = meta["title"]

        feed_url = f"{BASE_URL}/{slug}/rss.xml"
        lines.append(f"- **{title}**\n  {feed_url}\n")

    if not os.path.exists(README_PATH):
        return

    # UTF-8 Hardened README Read
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # The exact markers the script looks for
    start = "<!-- FEEDS-START -->"
    end = "<!-- FEEDS-END -->"

    # FERAL SAFEGUARD 1: Check the Python Script Variables
    if not start or not end:
        print("[SYSTEM ERROR] Python script misconfiguration: The 'start' or 'end' marker variables inside generate_feed.py are blank. Fix the script.")
        return

    # FERAL SAFEGUARD 2: Check the README.md File Contents
    if start not in content or end not in content:
        print(f"[SYSTEM WARNING] README.md is missing the specific HTML comments ({start} and/or {end}). Cannot auto-inject feeds.")
        return

    before = content.split(start)[0]
    after = content.split(end)[1]
    new_section = start + "\n" + "\n".join(lines) + "\n" + end

    # UTF-8 Hardened README Write
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(before + new_section + after)

    print("[SYSTEM NOTIFICATION] README.md successfully updated with latest feed list.")
# endregion

# region MAIN EXECUTION
def scan_and_generate():
    if not os.path.exists(INPUT_ROOT):
        print(f"Input directory '{INPUT_ROOT}' does not exist.")
        return

    shows = [d for d in os.listdir(INPUT_ROOT) if os.path.isdir(os.path.join(INPUT_ROOT, d))]
    
    if not shows:
        print("No show directories found under 'inputs/show/'.")
        return

    for show_slug in shows:
        generate_rss_for_show(show_slug)
        
    update_readme_with_feeds()

if __name__ == "__main__":
    scan_and_generate()
# endregion