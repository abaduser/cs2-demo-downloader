import match_scraper as match_scraper
import toml
import os

SETTINGS_FILE = "settings.toml"
SETTINGS_TEMPLATE = {
    "Settings": {
        "community_id": "",
        "match_types_to_download": ["premier"],
        "download_behavior": "periodic",
        "download_interval": "daily",
        "download_location": "",
    },
}

def generate_new_settings():
    # TODO: come up with a better way of setting this up to expand with more settings in the future, not as hardcoded.
    setting_comments = [
        "# Make sure to set this is set to the type of matches you want to track (premier, competitivepermap, scrimmage, wingman)",
        "# Download behavior dictates when to download your demos 'periodic', 'startup' and 'manual'",
        "# Intervals available are daily / hourly",
    ]
    new_settings = SETTINGS_TEMPLATE
    toml_string = toml.dumps(new_settings)
    toml_dissected = toml_string.split("\n")
    toml_dissected.insert(2, setting_comments[0])
    return toml_dissected


def main():
    if not os.path.exists(SETTINGS_FILE):
        new_settings = generate_new_settings()
        print(
            "Setting match type to the default of 'premier'. Change settings.json to change match types to download."
        )
        with open(SETTINGS_FILE, "w") as f:
            f.writelines([line + "\n" for line in new_settings])

    with open(SETTINGS_FILE, "r") as f:
        settings = toml.load(f)["Settings"]

    print("[CS2 DEMO DOWNLOADER]")
    print("------------------------------------")
    webauth = match_scraper.authenticate()
    match_scraper.poll_scraper(settings["match_types_to_download"], webauth)


if __name__ == "__main__":
    main()
