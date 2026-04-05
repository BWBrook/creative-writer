# Review Packs

This story uses review packs for scarce first-human feedback.

Each YAML manifest in this folder selects a small number of manuscript excerpts,
labels them as `confidence` or `uncertainty`, and asks a concrete review
question. Build a readable packet with:

```bash
make review-pack STORY=mars-2044-cave PACK=first-human-pass
```

Use [`_template.yml`](_template.yml) as the starting point for future packs.
