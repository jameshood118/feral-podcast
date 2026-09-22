"""
Feral Podcast RSS Generator (Multi-Show / Sovereign Braid)
Show.yaml + Auto-README + Mutagen Telemetry + UTF-8 Hardened + Podcasting 2.0
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
    """
    Generate an RSS feed for a specific show slug by parsing local Markdown
    files and combining them with the root show.yaml configuration.
    """
    show_input_dir = os.path.join(INPUT_ROOT, show_slug)
    seasons_dir = os.path.join(show_input_dir, "seasons")
    show_yaml_path = os.path.join(show_input_dir, "show.yaml")

    if not os.path.exists(show_yaml_path):
        print(f"Skipping '{show_slug}': Missing show.yaml at {show_yaml_path}")
        return

    # UTF-8 Hardened Read
    with open(show_yaml_path, "r", encoding="utf-8") as f:
        show_meta = yaml.safe_load(f)

    if not os.path.exists(seasons_dir):
        print(f"Skipping '{show_slug}': Missing seasons directory at {seasons_dir}")
        return

    show_output_dir = os.path.join(OUTPUT_ROOT, show_slug)
    os.makedirs(show_output_dir, exist_ok=True)

    fg = FeedGenerator()
    fg.load_extension('podcast')

    show_title = show_meta.get("title", show_slug.replace("-", " ").title())
    fg.title(show_title)
    fg.description(show_meta.get("description", f"High-friction truths from {show_title}."))
    fg.link(href=f"{BASE_URL}/{show_slug}/rss.xml", rel="self", type="application/rss+xml")
    fg.language('en')

    # pylint: disable=no-member
    fg.podcast.itunes_author(show_meta.get("author", "James Hood"))

    # FIX 1: Feedgen requires a dictionary for Apple categories
    cat = show_meta.get("category", "Technology")
    subcat = show_meta.get("subcategory")
    if subcat:
        fg.podcast.itunes_category({'cat': cat, 'sub': subcat})
    else:
        fg.podcast.itunes_category({'cat': cat})

    # FIX 2: Bypassing feedgen's internal validation trap.
    explicit_raw = str(show_meta.get("explicit", "no")).lower()
    explicit_clean = "yes" if explicit_raw in ["true", "yes", "y", "1"] else "no"
    fg.podcast.itunes_explicit(explicit_clean)

    fg.podcast.itunes_owner(
        email=show_meta.get("email", "jameshood118@gmail.com"),
        name=show_meta.get("author", "James Hood")
    )

    if "image" in show_meta:
        fg.podcast.itunes_image(show_meta["image"])
    fg.podcast.itunes_type('episodic')

    # Collect episodes across all season directories
    episode_filepaths = []
    for root, _, files in os.walk(seasons_dir):
        for file in files:
            if file.endswith('.md'):
                episode_filepaths.append(os.path.join(root, file))

    if not episode_filepaths:
        print(f"Skipping '{show_slug}': No markdown files found in {seasons_dir}")
        return

    # THE CHRONOLOGICAL SORT PROTOCOL
    parsed_episodes = []

    for filepath in episode_filepaths:
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        needs_save = False

        # region 1. GUID INJECTION (YouTube-Compliant 3-Chunk GUID)
        current_guid = str(post.metadata.get('guid', '')).strip()
        invalid_guids = ["[INSERT_UUID_HERE]", "", "None"]
        
        if current_guid in invalid_guids:
            new_guid = "-".join(str(uuid.uuid4()).split("-")[:3])
            post.metadata['guid'] = new_guid
            needs_save = True
            print(f"[{show_title}] Injected new 3-chunk GUID ({new_guid}) into {filename}")
        # endregion

        # region 2. FERAL TELEMETRY (TINYTAG)
        current_size = str(post.metadata.get('file_size', '')).strip()
        current_duration = str(post.metadata.get('duration', '')).strip()
        
        invalid_sizes = ['[SIZE_IN_BYTES]', '', '0', 'None']
        invalid_durations = ['[HH:MM:SS]', '[DURATION]', '00:00:00', '', 'None']

        if current_size in invalid_sizes or current_duration in invalid_durations:

            audio_url = str(post.metadata.get('audio_url', '')).strip()
            
            # Guard against the template placeholder being left in the audio_url
            if not audio_url or "[ACTUAL_FILENAME" in audio_url:
                print(f"[WARNING] Skipping telemetry for {filename}: audio_url is empty or contains a placeholder.")
            else:
                audio_filename = urllib.parse.unquote(audio_url.split('/')[-1])
                local_audio_path = os.path.join(LOCAL_AUDIO_DIR, audio_filename)

                if os.path.exists(local_audio_path):
                    # pylint: disable=broad-exception-caught
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
                            print(f"[{show_title}] Injected Size ({size_bytes}) "
                                  f"& Duration ({formatted_duration}) into {filename}")
                        else:
                            print(f"[WARNING] TinyTag could not calculate duration for {audio_filename}")
                    except Exception as e:
                        print(f"[WARNING] TinyTag failed to parse {audio_filename}: {e}")
                else:
                    print(f"[WARNING] Local audio file not found for telemetry check: {local_audio_path}")
        # endregion

        if needs_save:
            with open(filepath, 'w', encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

        # Parse the date so we can sort mathematically
        try:
            pub_date = datetime.strptime(post.metadata['date'], "%Y-%m-%dT%H:%M:%SZ")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
        except (ValueError, KeyError) as e:
            print(f"[ERROR] Could not parse date for {filename}. Skipping. Error: {e}")
            continue

        # Industrial Solder: Cast Season and Episode as strict integers to defeat string-sorting
        try:
            season_num = int(post.metadata.get('season', 0))
        except (ValueError, TypeError):
            season_num = 0

        try:
            episode_num = int(post.metadata.get('episode_number', 0))
        except (ValueError, TypeError):
            episode_num = 0

        # Store in memory
        parsed_episodes.append({
            'post': post,
            'pub_date': pub_date,
            'season': season_num,
            'episode': episode_num
        })

    # FERAL ALIGNMENT: Sort descending by Season, then Episode, then Date. 
    # This prevents the Windows-style string sorting trap.
    parsed_episodes.sort(key=lambda x: (x['season'], x['episode'], x['pub_date']), reverse=True)

    # Build the final XML strictly in the sorted order
    for ep in parsed_episodes:
        post = ep['post']
        fe = fg.add_entry()
        
        fe.id(str(post.metadata.get('guid', '')))
        fe.title(str(post.metadata.get('title', 'Untitled')))

        # region 3. THE TRANSLATION LAYER
        # Convert raw Markdown content into clean HTML for the RSS feed
        html_description = markdown.markdown(post.content)

        # Feed the HTML into the standard description tag
        fe.description(html_description)

        # Feed HTML into the <content:encoded> tag (Crucial for Apple/Substack)
        fe.content(html_description)
        # endregion

        fe.pubDate(ep['pub_date'])
        
        audio_url = str(post.metadata.get('audio_url', ''))
        file_size = str(post.metadata.get('file_size', '0'))
        if "[SIZE_IN_BYTES]" in file_size or file_size == "None":
            file_size = "0"
            
        fe.enclosure(audio_url, file_size, 'audio/x-m4a')
        
        duration = str(post.metadata.get('duration', '00:00:00'))
        if "[HH:MM:SS]" in duration or "[DURATION]" in duration or duration == "None":
            duration = "00:00:00"
        fe.podcast.itunes_duration(duration)

        if 'season' in post.metadata:
            fe.podcast.itunes_season(int(post.metadata['season']))
        if 'episode_number' in post.metadata:
            fe.podcast.itunes_episode(int(post.metadata['episode_number']))
        if post.metadata.get('episode_type'):
            fe.podcast.itunes_episode_type(str(post.metadata['episode_type']).lower())

        if post.metadata.get('explicit') is not None:
            explicit_val = str(post.metadata['explicit']).lower()
            fe.podcast.itunes_explicit("yes" if explicit_val in ["true", "yes", "y", "1"] else "no")

        if post.metadata.get('image'):
            fe.podcast.itunes_image(post.metadata['image'])

        # SEO & Podcasting 2.0 Injections
        if post.metadata.get('subtitle'):
            fe.podcast.itunes_subtitle(post.metadata['subtitle'])
        if post.metadata.get('summary'):
            fe.podcast.itunes_summary(post.metadata['summary'])

        transcript_url = str(post.metadata.get('transcript_url', '')).strip()
        if transcript_url and "[ACTUAL_FILENAME" not in transcript_url and transcript_url != 'None':
            # Utilizing feedgen's native link tag mapping as the alternate transcript container
            fe.link(href=transcript_url, rel="alternate", type="text/vtt", title="Transcript")

    output_file = os.path.join(show_output_dir, 'rss.xml')
    fg.rss_file(output_file)
    print(f"[{show_title}] RSS Feed generated successfully at {output_file}.")
# endregion

# region README UPDATING
def update_readme_with_feeds():
    """
    Update the primary README.md with the generated RSS feed URLs by scanning
    between the predefined HTML comment blocks.
    """
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
        print("[SYSTEM ERROR] Python script misconfiguration: The 'start' or 'end' "
              "marker variables inside generate_feed.py are blank. Fix the script.")
        return

    # FERAL SAFEGUARD 2: Check the README.md File Contents
    if start not in content or end not in content:
        print(f"[SYSTEM WARNING] README.md is missing the specific HTML comments "
              f"({start} and/or {end}). Cannot auto-inject feeds.")
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
    """
    Scan the active show directory and execute the RSS generation pipeline 
    across all detected sub-directories.
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

    update_readme_with_feeds()

if __name__ == "__main__":
    scan_and_generate()
# endregion
