# Contributing

Bug reports, ideas, code and pixel art are welcome. Open an issue for larger changes before starting.

1. Fork the repo and create a branch for your change.
2. For new ships or language logos, share a pixel-art or animation preview and get maintainer approval before integration.
3. Keep changes focused. Preserve sharp pixels, transparent backgrounds, seamless loops and accurate commit counts.
4. Open a pull request explaining the change and how you checked it. Include previews for visual changes.

With Python 3.11+ in a virtual environment:

```sh
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
pytest -q
```

Looking for something to work on? See the [project goals](README.md#project-goals).
