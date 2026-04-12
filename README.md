# GitHub metadata mirror

A Python-based generator for a static HTML GitHub issues and pull-request
mirror using backup data from [github-metadata-backup](https://github.com/0xB10C/github-metadata-backup).

## Usage

This tool generates a static HTML site from a github-metadata-backup in a
single step. It reads the backup JSON files, builds an in-memory index, then
renders HTML pages one at a time.

**Dependencies**: Python 3.11+ and [mistune] for Markdown rendering.

```
pip install mistune
```

Run `build.py` with the path to the backup directory and an output directory:

```
python build.py \
    --input /path/to/backup \
    --output /path/to/output \
    --title "My GitHub Mirror" \
    --owner <owner> \
    --repository <repository>
```

The generated static files can be served by nginx, caddy, or any other
web server.

### Options

- `--input`: Path to the github-metadata-backup directory (contains `issues/` and `pulls/` subdirectories).
- `--output`: Output directory for the generated HTML site.
- `--title`: Site title shown in the navigation bar.
- `--owner`: GitHub repository owner (used for link rewriting and linking back to GitHub).
- `--repository`: GitHub repository name.
- `--footer`: Optional footer HTML shown on every page.
- `--base-url`: Base URL path if hosting in a subdirectory (e.g. `/mirror/`). Defaults to `/`.
- `-s` / `--subset`: Only process the first 100 issues and 100 pull requests. Useful for testing.

## Example

To generate a mirror from the Bitcoin Core [bitcoin/bitcoin] metadata backup
(assuming it's located in `/var/backup/github-metadata-backup-bitcoin-bitcoin`):

```
python build.py \
    --input /var/backup/github-metadata-backup-bitcoin-bitcoin \
    --output ./public \
    --title "Bitcoin Core GitHub Mirror" \
    --owner bitcoin \
    --repository bitcoin \
    --footer "<b>This mirror is hosted by 0xB10C</b>" \
    --base-url "/bitcoin-bitcoin/"
```

When testing with large repositories, pass `-s` to process only a subset of
100 issues and pull requests. This significantly speeds up the build.

The static files are written to the `--output` directory. From there, use
nginx, caddy, or any other web server to host them.

[bitcoin/bitcoin]: https://github.com/bitcoin/bitcoin
[mistune]: https://github.com/lepture/mistune

## Development

### Tests

Tests use Python's built-in `unittest` and require `pytest`:

```
pip install pytest
python -m pytest tests/ -v
```

### Linting

```
pip install ruff
ruff check .
```
