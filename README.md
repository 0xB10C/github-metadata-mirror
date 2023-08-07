# GitHub metadata mirror

A [Hugo]-based GitHub issues and pull-request mirror using backup data from
[github-metadata-backup].

[hugo]: https://gohugo.io/
[github-metadata-backup]: https://github.com/0xB10C/github-metadata-backup

## Usage

This tool generates static HTML pages from a github-metadata-backup. There are
two steps to this process.

1. **Generate mirror content**: First, the Python script `generate-data.py` is
    used to generate MarkDown files into the `content` directory and JSON files
    into the `data` directory. Pass the folder with the backup as first argument
    and the output directory as second argument.

```
python generate-data.py /path/to/backup /path/to/project/directory
```

2. **Build static site**: The second step is to use [Hugo] to build the static
    HTML site. Make sure to address the `FIXME`'s in the `config.toml` file or
    to set the environment variables `HUGO_TITLE`, `HUGO_PARAMS_OWNER`,
    `HUGO_PARAMS_REPOSITORY`, and `HUGO_PARAMS_FOOTER` before building the
    site. With larger projects (a few thousand issues and pull requests), Hugo's
    RAM usage will be noticable. Consider enabling swapping if your system has
    limited RAM. It might also make sense to pass the `--debug` flag to observe
    the build process. Set a base URL with `--baseURL` if you want to host the
    site in a sub path. By default, the command below will generate the static
    HTML site into the `public` directory.

```
hugo --source /path/to/project/directory --debug --baseURL /mirror
```

- `HUGO_TITLE`: Sets the title of the page. This is shown in the top left corner.
- `HUGO_PARAMS_OWNER`: Sets GitHub repository owner. This is needed for rewriting
    link and for linking to the repository on GitHub.
- `HUGO_PARAMS_REPOSITORY`: Sets GitHub repository name. This is needed for rewriting
    link and for linking to the repository on GitHub.
- `HUGO_PARAMS_FOOTER`: Sets a footer that is shown on each page. This can be HTML
    syntax.

## Example

To generate a mirror from the Bitcoin Core [bitcoin/bitcoin] metadata backup
(assuming it's located in `/var/backup/bitcoin-bitcoin/`), run `generate-data.py`
from the github-metadata-mirror project directory.

```
python generate-data.py /var/backup/bitcoin-bitcoin/ .
```

When testing with large repositoires, you can pass `-s` to pick a subset of
100 issues and pull-requests. This speeds up the processing and the generation.

Then, address the `FIXME`'s in the `config.toml` file or set the above
enviroment variables. In this case, we set the environment variables.
As we plan to host our site in the subdirectory `bitcoin-bitcoin`, we set the
base URL. We set the owner and repository to "bitcoin".

```
export HUGO_TITLE="Bitcoin Core GitHub mirror"
export HUGO_PARAMS_OWNER="bitcoin"
export HUGO_PARAMS_REPOSITORY="bitcoin"
export HUGO_PARAMS_FOOTER="<b>This mirror is hosted by 0xB10C</b>"
hugo --source . --debug --baseURL "/bitcoin-bitcoin/
```

Hugo will generate the static files to the `public/` directory. This might take
a few minutes. From there on you can use nginx, caddy, or any other webserver to
host them.

[bitcoin/bitcoin]: https://github.com/bitcoin/bitcoin


## Nix Package and module

A Nix package and module for the github-metadata-mirror tool are avaliable in
my personal [nix-package-collection]. Note that the package does not include a
binary that can be run. Rather, it includes the `generate-data.py` Python script
and the Hugo files (layout, tests, ...).

[nix-package-collection]: https://github.com/0xB10C/nix
