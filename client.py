import toml
import click
import match_scraper as match_scraper
import logging

logger = logging.getLogger("c2dd")
# TODO: make sure logging is less verbose with a debug flag or something. maybe a --verbose flag. 
# Maybe also figure out how logging is nested or handled across modules.
logging.basicConfig(level=logging.INFO)

SETTINGS_FILE = "settings.toml"
SETTINGS_TEMPLATE = {
    "Settings": {
        "steam_username": "",
        "match_types_to_download": ["premier"],
        "download_behavior": "periodic",
        "download_interval": "daily",
        "download_location": "",
    },
}

SETTINGS_COMMENTS = {
    "match_types_to_download": "# Make sure to set this is set to the type of matches you want to track (premier, competitivepermap, scrimmage, wingman)",
    "download_behavior": "# Download behavior dictates when to download your demos 'periodic', 'startup' and 'manual'",
    "download_interval": "# Intervals available are daily / hourly",
}


def load_settings(settings_file):
    # try to load the settings file, if it doesn't exist generate one.
    try:
        with open(settings_file, "r") as f:
            return toml.load(f)["Settings"]
    except FileNotFoundError:
        logging.error("Settings file not found. Generating new settings file.")
        new_settings = SETTINGS_TEMPLATE
        write_settings_comments(settings_file, new_settings)
        # return the settings dictionary from the new settings file.
        return toml.load(new_settings)["Settings"]

def write_settings_comments(settings_file, settings):
    logging.info(f"Writing settings to {settings_file}")
    toml_string = toml.dumps(settings)
    toml_dissected = toml_string.split("\n")
    for line in toml_dissected:
        if line in SETTINGS_COMMENTS:
            toml_dissected.insert(toml_dissected.index(line), SETTINGS_COMMENTS[line])
    
    with open(settings_file, "w") as f:
        f.writelines([line + "\n" for line in toml_dissected])


# Need to add commands for
# browsing matches / manual download
@click.group()
@click.option("--settings", "settings_file", type=click.Path(exists=True), default=SETTINGS_FILE, help="Path to settings file.")
# @click.option("--debug/--no-debug", default=False)
@click.pass_context
def c2dd(ctx, settings_file):
    # load settings dictionary, into context key 'settings'
    ctx.ensure_object(dict)
    ctx.obj['settings'] = load_settings(settings_file)

    # authenticate before every command (TODO: change)
    ctx.obj['wa'] = match_scraper.authenticate()


@c2dd.command()
@click.option("--username", default=None, help="Steam username of the account to download demos from.")
@click.option("--password", default=None, prompt="Enter Steam Password: ", hide_input=True, confirmation_prompt=True, help="Steam password.")
@click.pass_context
def authenticate(ctx, username, password):
    click.echo("Authenticating with Steam...")
    steam_user = ctx.obj['settings']["steam_username"]
    if username:
        steam_user = username

    match_scraper.authenticate(steam_user, password, True)


@c2dd.command()
@click.pass_context
def dl(ctx):
    click.echo("Downloading demos...")
    match_scraper.download_matches(ctx.obj['settings']["match_types_to_download"], ctx.obj['wa'])

    

if __name__ == "__main__":
    c2dd()
