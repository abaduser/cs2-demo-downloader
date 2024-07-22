# cs2-demo-downloader

cs2 demo downloader is a tool written in Python to help with downloading your cs2 demos, and organize them. valve only stores demos for about a week or two on their servers, this tool helps you by automatically scrapping all your most recent demos, periodically. Demos can then be sorted and filtered for packing and sending to friends.

This project is currently a WIP

- [x] demo scraping functionality
- [x] caching downloads
- [x] pyproject.toml / python whl
- [ ] demo parsing
- [ ] demo container format (what else can we extract)
- [ ] api / cleaner function documentation

## Configuration

configuration is done through a settings.toml file automatically generated at first run. most settings will be able to be overriden using the command line tool.

## Installation

Clone the repository and install the package using the `pip install -e .` command to install, or use a virtual envionment by running

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Usage

run `c2dd` in your terminal to run the tool, without any options will give you access to the help menu. the simplest way to download your demos is run the `c2dd dl` command which will automatically prompt users for the account username associated, and both authengenerate a `username.pickle` or load an existing pickle with that name. It then will attempt to download given rules specified by `settings.toml`.

### ⚠️ Caution - Pickle

when you authenticate with steam, you are creating a web session with steam, this session is stored in `<username>.pickle` for subsequent rerunning of the program. don't share this file, as it grants access to your steam account. it's even reccomended you delete this file when you are done downloading all the demos you need.
