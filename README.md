# cs2 demo downloader 

cs2 demo downloader is a tool written in Python to help with downloading your cs2 demos, and sending them to friends. valve only stores demos for about a week or two on their servers, this tool helps by automatically scrapping all your most recent demos, periodically. Demos can be set to be automatically sent to a server running the application in server mode.

This project is currently a WIP

- [x] demo scraping functionality 
- [ ] more configuration options / caching data
- [ ] demo sending functionality
- [ ] server / demo reception
- [ ] service solution / setup.py
- [ ] demo browsing / unpacking

## Configuration

configuration is done through a settings.toml file automatically generated at first run. most settings will be able to be overriden using the command line tool.

## Installation

Clone the repository and satisfy the Pipfile requirements (pipenv is the venv solution provided). Run the command using `python client.py <arguments>`

## Usage

run `python client.py dl` to download all your latest demos from the tabs specified in `match_types_to_download` in your `settings.toml`

### Caution - Pickle

when you authenticate with steam, you are creating a web session with steam, this session is stored in `<username>.pickle` for subsequent rerunning of the program. don't share this file, as it grants access to your steam account.
