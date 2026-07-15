# The Feral Podcast Pipeline 🎙️

An open-source, automation-driven deployment engine for independent audio creators. 

The Feral Podcast Pipeline replaces expensive, centralized podcasting tollbooths (like Libsyn, Anchor, or Buzzsprout) with a simple, secure, and entirely sovereign infrastructure. By leveraging GitHub Actions, Python, and raw Markdown (`.md`) files, this pipeline acts as an automated radio tower. 

Drop your audio payload into any zero-egress storage bucket (like Cloudflare R2 or a local TrueNAS), write your show notes in a Markdown file, and push the code. The engine automatically compiles your metadata, generates a perfectly validated Apple/Spotify-compliant XML feed, and broadcasts it to the world via GitHub Pages.

## Core Features

* **Bare-Metal Custody:** You own the infrastructure, the raw XML, and the deployment keys.

* **Training-Free Execution:** Operates entirely on standard web protocols. No proprietary dashboards.

* **Markdown to Audio:** Write your show notes in your preferred local code editor. The engine handles the metadata translation.

* **Zero Egress Traps:** Designed to integrate seamlessly with sovereign storage solutions.

### Monetization & Licensing

This project is released under the permissive MIT License. You are free to use, modify, and distribute this pipeline. For creators who require hands-on deployment, Saiph House offers "White-Glove Setup Services" to configure your storage buckets, wire the GitHub Actions, and hand you the sovereign digital keys.