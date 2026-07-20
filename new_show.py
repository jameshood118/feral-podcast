import os
import shutil
import yaml

INPUT_ROOT = os.path.join("inputs", "show")
SHOW_TEMPLATE = "show.yaml"
EP_TEMPLATE = "ep_00_template.md"


def slugify(name):
    """Convert show name into kebab-case slug."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace("--", "-")
    )


def create_show(name):
    slug = slugify(name)
    show_dir = os.path.join(INPUT_ROOT, slug)
    episodes_dir = os.path.join(show_dir, "episodes")

    # Ensure base directories exist
    os.makedirs(episodes_dir, exist_ok=True)

    # Copy show.yaml template
    if os.path.exists(SHOW_TEMPLATE):
        shutil.copy(SHOW_TEMPLATE, os.path.join(show_dir, "show.yaml"))
    else:
        print(f"Missing template: {SHOW_TEMPLATE}")
        return

    # Copy episode template
    if os.path.exists(EP_TEMPLATE):
        shutil.copy(EP_TEMPLATE, os.path.join(episodes_dir, "ep_00.md"))
    else:
        print(f"Missing template: {EP_TEMPLATE}")
        return

    print(f"New show created: {slug}")
    print(f" → {show_dir}")
    print(f" → {episodes_dir}/ep_00.md")
    print("Populate show.yaml and ep_00.md to begin broadcasting.")


if __name__ == "__main__":
    show_name = input("Enter the new show name: ")
    create_show(show_name)
