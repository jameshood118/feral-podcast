"""
Feral Podcast RSS Generator

This module reads Markdown files containing podcast episode metadata
and generates a validated, iTunes-compliant RSS XML feed using feedgen.
"""

import os
from datetime import datetime

import frontmatter
import pytz
from feedgen.feed import FeedGenerator

def generate_rss():
    """
    Reads Markdown files from the 'episodes' directory, parses YAML frontmatter,
    and compiles the data into 'rss.xml'.
    """
    fg = FeedGenerator()
    fg.load_extension('podcast')

    # Core Podcast Metadata (Update these for your specific show)
    fg.title('The Sovereign Pilot')
    fg.description('High-friction truths and systems architecture from the analog wasteland.')
    fg.link(href='https://jameshood118.github.io/feral-podcast', rel='alternate')
    fg.language('en')

    # pylint: disable=no-member
    fg.podcast.itunes_author('James Hood')
    fg.podcast.itunes_category('Technology', 'Podcasting')
    fg.podcast.itunes_explicit('no')

    # Read all markdown files in the episodes folder
    episodes_dir = 'episodes'
    if not os.path.exists(episodes_dir):
        os.makedirs(episodes_dir)

    episode_files = [f for f in os.listdir(episodes_dir) if f.endswith('.md')]

    for filename in episode_files:
        filepath = os.path.join(episodes_dir, filename)
        post = frontmatter.load(filepath)

        fe = fg.add_entry()
        fe.id(post['audio_url'])
        fe.title(post['title'])
        fe.description(post.content)

        # Parse date and ensure UTC timezone awareness
        pub_date = datetime.strptime(post['date'], "%Y-%m-%dT%H:%M:%SZ")
        pub_date = pub_date.replace(tzinfo=pytz.UTC)
        fe.pubDate(pub_date)

        # Add the audio payload
        fe.enclosure(post['audio_url'], str(post['file_size']), 'audio/mpeg')
        fe.podcast.itunes_duration(post['duration'])

    # Generate the XML file
    fg.rss_file('rss.xml')
    print("Feral RSS Feed generated successfully. Bare-Metal Custody maintained.")

if __name__ == "__main__":
    generate_rss()