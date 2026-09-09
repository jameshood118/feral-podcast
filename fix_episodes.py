import os
import re
import frontmatter

# Define root show directory and the new seasons container
show_dir = os.path.join("inputs", "show", "reports-from-the-node")
seasons_dir = os.path.join(show_dir, "seasons")

if not os.path.exists(seasons_dir):
    print(f"[ERROR] Directory not found: {seasons_dir}")
else:
    # Recursively collect all markdown files in the seasons directory tree
    episode_filepaths = []
    for root, dirs, files in os.walk(seasons_dir):
        for file in files:
            if file.endswith('.md'):
                episode_filepaths.append(os.path.join(root, file))

    print(f"Found {len(episode_filepaths)} episode files. Commencing frontmatter sweep...\n")
    
    for filepath in sorted(episode_filepaths):
        filename = os.path.basename(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            
        # Extract the episode number from the title
        match = None
        if 'title' in post.metadata:
            match = re.search(r'Episode\s*(\d+)', post.metadata['title'], re.IGNORECASE)
            
        # Fallback to filename if title regex fails
        if not match:
            match = re.search(r'Episode_?(\d+)', filename, re.IGNORECASE)
            
        if match:
            ep_num = int(match.group(1))
            needs_save = False
            
            # Dynamically extract season number from the directory structure
            # Expected path format: .../seasons/{season_num}/episodes/{filename}
            path_parts = filepath.split(os.sep)
            season_num = 1 # Default fallback
            if 'seasons' in path_parts:
                seasons_idx = path_parts.index('seasons')
                if len(path_parts) > seasons_idx + 1:
                    try:
                        season_num = int(path_parts[seasons_idx + 1])
                    except ValueError:
                        pass
            
            # Inject or overwrite Season based on the physical folder architecture
            if 'season' not in post.metadata or post.metadata['season'] != season_num:
                post.metadata['season'] = season_num
                needs_save = True
                
            if 'episode_number' not in post.metadata:
                post.metadata['episode_number'] = ep_num
                needs_save = True

            if 'episode_type' not in post.metadata:
                post.metadata['episode_type'] = 'full'
                needs_save = True

            if 'explicit' not in post.metadata:
                post.metadata['explicit'] = 'no'
                needs_save = True

            if 'image' not in post.metadata:
                post.metadata['image'] = ''
                needs_save = True
                
            # Save if modified
            if needs_save:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))
                print(f"✅ Updated {filename} -> Injecting structural frontmatter (Season {season_num}, Ep {ep_num}).")
            else:
                print(f"⏩ Skipped {filename} -> (Already fully tagged)")
        else:
            print(f"⚠️ [WARNING] Could not determine episode number for {filename}")

print("\nSweep complete. Run generate_feed.py to rebuild the XML.")