# Review Packs

Review packs hold targeted human-feedback requests for scarce review time.

Keep each pack as a YAML manifest in this folder. The `review-pack` command will
extract the requested manuscript lines and build a readable Markdown packet
under `build/<story>/reviews/`.

Use [`_template.yml`](_template.yml) as the starting point for new packs.
