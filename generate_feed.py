"""
Feral Podcast RSS Generator (Multi-Show / Sovereign Braid)

This module reads Markdown files from isolated show directories structured as:
show/{show-name}/episodes/
It parses YAML frontmatter, handles persistent GUID generation, and compiles 
the data into independent, iTunes-compliant RSS XML feeds per show.
"""

import os
import uuid
from datetime import datetime
import frontmatter
import pytz
from feedgen.feed import FeedGenerator

def generate_rss_for_show(show_slug):
    """
    Reads Markdown files from 'inputs/show/{show_slug}/episodes/',
    parses YAML frontmatter, ensures persistent GUIDs, and compiles 
    the data into 'outputs/show/{show_slug}/rss.xml'.
    """
    # Construct the path using the new inputs/show/{show-name}/episodes/ standard
    shows_base_dir = os.path.join('inputs', 'show')
    episodes_dir = os.path.join(shows_base_dir, 'episodes')
    
    if not os.path.exists(episodes_dir):
        print(f"Skipping '{show_slug}': No episodes directory found at '{episodes_dir}'.")
        return

    fg = FeedGenerator()
    fg.load_extension('podcast')

    # Convert kebab-case slug to Title Case for the podcast feed title
    # e.g., 'reports-from-the-node' -> 'Reports From The Node'
    show_title = show_slug.replace("-", " ").title()
    
    fg.title(show_title)
    fg.description(f'High-friction truths and systems architecture from {show_title}.')
    fg.link(href=f'https://jameshood118.github.io/feral-podcast/show/{show_slug}', rel='alternate')
    fg.language('en')

    # Universal iTunes Ecosystem Tags (One-Stop Shop Compliance)
    # pylint: disable=no-member
    fg.podcast.itunes_author('James Hood')
    fg.podcast.itunes_category('Technology', 'Podcasting')
    fg.podcast.itunes_explicit('no')
    fg.podcast.itunes_owner(email='jameshood118@gmail.com', name='James Hood')
    fg.podcast.itunes_image('https://pub-07726ae62cd8476aa3f863937841b23b.r2.dev/reports_from_the_node.png')
    fg.podcast.itunes_type('episodic')

    episode_files = [f for f in os.listdir(episodes_dir) if f.endswith('.md')]
    
    if not episode_files:
         print(f"Skipping '{show_slug}': Episodes directory is empty.")
         return

    for filename in episode_files:
        filepath = os.path.join(episodes_dir, filename)
        post = frontmatter.load(filepath)

        fe = fg.add_entry()

        # GUID Decoupling: Check for persistent GUID or generate stable UUID v5
        if 'guid' in post:
            fe.id(post['guid'])
        else:
            stable_guid = str(uuid.uuid5(uuid.NAMESPACE_URL, post.get('audio_url', filename)))
            fe.id(stable_guid)

        fe.title(post['title'])
        fe.description(post.content)

        # Parse date and ensure UTC timezone awareness
        pub_date = datetime.strptime(post['date'], "%Y-%m-%dT%H:%M:%SZ")
        pub_date = pub_date.replace(tzinfo=pytz.UTC)
        fe.pubDate(pub_date)

        # Add the audio payload enclosure
        fe.enclosure(post['audio_url'], str(post['file_size']), 'audio/mpeg')
        fe.podcast.itunes_duration(post['duration'])

        # Optional Episode-Level Taxonomy
        if 'season' in post:
            fe.podcast.itunes_season(int(post['season']))
        if 'episode_number' in post:
            fe.podcast.itunes_episode(int(post['episode_number']))

    # Output the RSS file directly inside the show's root directory: show/{show-slug}/rss.xml
    shows_output_dir = os.path.join('outputs', 'show')
    output_file = os.path.join(shows_output_dir, 'rss.xml')
    fg.rss_file(output_file)
    print(f"[{show_title}] Feral RSS Feed generated successfully at {output_file}. Bare-Metal Custody maintained.")

def scan_and_generate():
    """
    Scans the 'show/' root directory for strict kebab-case show folders.
    """
    shows_base_dir = 'show'
    
    if not os.path.exists(shows_base_dir):
        print(f"Base directory '{shows_base_dir}' does not exist.")
        return

    # Automatically discover all subdirectories inside the 'show/' folder
    shows = [d for d in os.listdir(shows_base_dir) if os.path.isdir(os.path.join(shows_base_dir, d))]
    
    if not shows:
        print("No show directories found under 'show/'.")
        return

    for show_slug in shows:
        generate_rss_for_show(show_slug)

if __name__ == "__main__":
    scan_and_generate()