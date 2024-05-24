from playwright.sync_api import sync_playwright
import steam.webauth as steam_auth
from bs4 import BeautifulSoup
import pickle
import logging
import re
from pathlib import Path
from downloader import url_downloader
from time import sleep

logger = logging.getLogger("web_scraper")
logging.basicConfig(level=logging.INFO)
PICKLE_PATH = Path("wa.pickle")


def download_matches(community_id, tab):
    global wa
    recent_matches, folder = scrape_match(community_id, tab)
    recent_match_urls = list(filter(None, [match["url"] for match in recent_matches]))
    url_downloader(wa.session, recent_match_urls, folder)


def authenticate(ForceAuth=False):
    global wa
    if PICKLE_PATH.exists() and not ForceAuth:
        wa = pickle.loads(open(PICKLE_PATH, "rb").read())

        logging.info(f"Loaded existing pickle from {PICKLE_PATH}")
    else:
        logging.info("Authentication required from Steam.")
        logging.warning("Storing session on disk.")

        username = input("Steam Username: ")
        wa = steam_auth.WebAuth()
        wa.cli_login(username, input(f"Password for {username}: "))

        try:
            with open(PICKLE_PATH, "wb") as f:
                f.write(pickle.dumps(wa))
            logging.info(f"Pickled the session to {PICKLE_PATH}.")
        except pickle.PicklingError:
            logging.error("Failed to pickle the session!")
            logging.warn("Session was not pickled!")


def extract_cookies(request_cookies):
    playwright_cookies = []
    for cookie in request_cookies:
        playwright_cookie = {
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path,
            "httpOnly": bool(cookie._rest.get("HttpOnly", False)),
            "secure": bool(cookie._rest.get("Secure", False)),
            "sameSite": "Lax",  # SameSite is not directly available, default to 'Lax'
        }
        playwright_cookies.append(playwright_cookie)
    return playwright_cookies


def scrape_match(community_id, tab):
    global wa
    if wa.logged_on:
        logging.info(f"Fetching 'Matches' for {community_id}...")
        logging.info(f"Using access token: {wa.access_token}...")
        logging.info(f"Client ID: {wa.client_id}\tRequest ID: {wa.request_id}")
        logging.info(f"Refresh token: {wa.refresh_token}")
        logging.info(f"Session ID: {wa.session_id}")
    else:
        logging.warning("Not logged in")
        return False

    page_soup = None
    recent_matches = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=wa.session.headers["User-Agent"])
        logging.info("Setting cookies from SteamAuth...")
        context.add_cookies(extract_cookies(wa.session.cookies))

        page = context.new_page()
        gcpd_url = f"https://steamcommunity.com/id/{community_id}/gcpd/730/?tab=matchhistory{tab}"
        page.goto(gcpd_url)

        if "Personal Game Data" not in page.title():
            logging.warning("Issue with Auth, can't get to Personal Game Data page")
            authenticate(True)
            page.goto(gcpd_url)
            if "Personal Game Data" not in page.title():
                logging.warning("Couldn't auth. Aborting webscraper...")

        # logic for checking if theres a load more button as the only item
        # true => press button, loop
        # false => collect the 16 matches on the page. (TODO: maybe pass an arg of the last match collected, so we can continue until we reach it.)

        while match_table_empty(page):
            page.locator("#load_more_clickable").click()

        page_soup = BeautifulSoup(page.content(), "html.parser")

        context.close()
        browser.close()

    # use soup to pull all matches
    match_table = page_soup.find("table", class_="csgo_scoreboard_root")

    if match_table:
        logging.info("Found csgo_scoreboard_root...")
        matches = match_table.find_all("tr", style=re.compile("display: table-row;"))

        if matches:
            logging.info("Found matches...")
            for match in matches:
                # map_info : Map, Date, Ranked, Wait Time, Match duration, Match Score
                # Players (Player : Stats)
                players_info = {}
                # Player (Name) : Ping, Kills, Assists, Deaths, MVPs, HSP, Score
                downloadURL = ""

                # match_info process
                map_table = match.find(
                    "table", class_="csgo_scoreboard_inner_left"
                ).find("tbody")
                if map_table:

                    logging.info("Found map_table...")
                    downloadbutton = map_table.find(
                        "td", class_="csgo_scoreboard_cell_noborder"
                    )
                    if downloadbutton:
                        a = downloadbutton.find("a")
                        if a:
                            downloadURL = a.get("href")

                    extracted_match_info = [
                        info.get_text(strip=True) for info in map_table.find_all("td")
                    ]
                    extracted_match_info = extracted_match_info[:-1]
                    match_info = {
                        "map": extracted_match_info[0],
                        "date": extracted_match_info[1],
                        "ranked": extracted_match_info[2],
                        "wait_time": extracted_match_info[3],
                        "match_duration": extracted_match_info[4],
                        "match_score": "" 
                    }

                # player_info process
                player_table = match.find(
                    "table", class_="csgo_scoreboard_inner_right"
                ).find("tbody")
                if player_table:
                    logging.info("Found player_table...")
                    # do the score while we have the players_table
                    match_score = player_table.find(
                        "td", class_="csgo_scoreboard_score"
                    ).get_text(strip=True)
                    match_info["match_score"] = match_score

                    # grab all rows
                    player_rows = player_table.find_all("tr")
                    if player_rows:
                        logging.info("Found player_rows...")
                        # throwaway the header (first), and score row (7th)
                        valid_player_rows = player_rows[1:6] + player_rows[7:]
                        for player in valid_player_rows:
                            player_name = player.find("a", class_="linkTitle").get_text(
                                strip=True
                            )
                            # make strings out of every stat but the first one, which is the name
                            stats = [
                                s.get_text(strip=True)
                                for s in player.find_all("td")[1:]
                            ]
                            print(stats)
                            player_stats = {
                                "ping": stats[0],
                                "kills": stats[1],
                                "assists": stats[2],
                                "deaths": stats[3],
                                "mvp": stats[4],
                                "hsp": stats[5],
                                "score": stats[6],
                            }
                            players_info[player_name] = player_stats

                print(match_info)
                # finally, add match_entry to recent_matches
                match_entry = {
                    "url": downloadURL,
                    "match_info": match_info,
                    "players_info": players_info,
                }
                recent_matches.append(match_entry)

    logging.info(f"Page Scrape complete.")

    return recent_matches, tab


def match_table_empty(page):
    table_locator = page.locator("table.generic_kv_table.csgo_scoreboard_root tbody tr")

    row_count = table_locator.count()

    if row_count == 0 or (
        row_count == 1 and table_locator.first.locator("th").count() > 0
    ):
        logging.info("match_table empty")
        return True
    logging.info("match_table not empty!")
    return False


# authenticate()
if __name__ == "__main__":
    main()
