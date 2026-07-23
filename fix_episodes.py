import os
import re
import frontmatter

episodes_dir = os.path.join("inputs", "show", "reports-from-the-node", "episodes")

if not os.path.exists(episodes_dir):
    print(f"[ERROR] Directory not found: {episodes_dir}")
else:
    files = [f for f in os.listdir(episodes_dir) if f.endswith('.md')]
    print(f"Found {len(files)} episode files. Commencing frontmatter sweep...\n")
    
    for filename in sorted(files):
        filepath = os.path.join(episodes_dir, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            
        # Extract the episode number from the title (e.g., "Episode 4: Refactoring Retail...")
        match = None
        if 'title' in post.metadata:
            match = re.search(r'Episode\s*(\d+)', post.metadata['title'], re.IGNORECASE)
            
        # Fallback to filename if title regex fails (e.g., "Episode_4.md")
        if not match:
            match = re.search(r'Episode_?(\d+)', filename, re.IGNORECASE)
            
        if match:
            ep_num = int(match.group(1))
            needs_save = False
            
            # Inject Season
            if 'season' not in post.metadata:
                post.metadata['season'] = 1
                needs_save = True
                
            # Inject Episode Number
            if 'episode_number' not in post.metadata:
                post.metadata['episode_number'] = ep_num
                needs_save = True
                
            # Save if modified
            if needs_save:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))
                print(f"✅ Updated {filename} -> season: 1, episode_number: {ep_num}")
            else:
                print(f"⏩ Skipped {filename} -> (Already fully tagged)")
        else:
            print(f"⚠️ [WARNING] Could not determine episode number for {filename}")

print("\nSweep complete. Run generate_feed.py to rebuild the XML.")