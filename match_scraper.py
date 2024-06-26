import logging
import pickle
import re
from pathlib import Path

import steam.webauth as steam_auth
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from downloader import url_downloader

logger = logging.getLogger("web_scraper")
logging.basicConfig(level=logging.INFO)


def download_matches(tabs, webauth):
    for tab in tabs:
        recent_matches, folder = scrape_matches(tab, webauth)
        recent_match_urls = list(filter(None, [match["url"] for match in recent_matches]))
        url_downloader(webauth.session, recent_match_urls, folder)


def load_webauth_pickle(path):
    logging.info(f"Loading an existing pickle from {path}")
    return pickle.loads(open(path, "rb").read())


def create_webauth_pickle(path):
    logging.info("Authentication required from Steam.")
    logging.warning("Storing session on disk!")
    username = input("Steam Username: ")
    webauth = steam_auth.WebAuth()
    webauth.cli_login(username, input(f"Password for {username}: "))
    try:
        with open(path, "wb") as f:
            f.write(pickle.dumps(webauth))
        logging.info(f"Pickled the session to {path}.")
    except pickle.PicklingError:
        logging.error("Failed to pickle the session!")
        logging.warn("Session was not pickled!")
    return webauth


def authenticate(ForceAuth=False):
    webauth_pickle_path = Path("webauth.pickle")

    if webauth_pickle_path.exists() and not ForceAuth:
        webauth = load_webauth_pickle(webauth_pickle_path)
    else:
        webauth = create_webauth_pickle(webauth_pickle_path)
    return webauth


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


def goto_personal_data(page, url):
    page.goto(url)

    if "Personal Game Data" not in page.title():
        logging.error("Can't get to Personal Game Data page")
        authenticate(True)
        page.goto(url)
        if "Personal Game Data" not in page.title():
            # CATASTROPHIC FAILURE HAS OCCURRED!
            # We should handle this in some nice, Windows service-y way.
            return False
    return True


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


def fetch_match_table(page):
    # logic for checking if theres a load more button as the only item
    # while we find no match elements on the page, click load more.
    retries = 0
    while match_table_empty(page):
        page.locator("#load_more_clickable").click()
        retries = retries + 1
        if retries == 10:
            return None
    page_soup = BeautifulSoup(page.content(), "html.parser")
    match_table = page_soup.find("table", class_="csgo_scoreboard_root")
    return match_table


def parse_map_info(map_table):
    downloadbutton = map_table.find("td", class_="csgo_scoreboard_cell_noborder")
    if downloadbutton:
        a = downloadbutton.find("a")
        if a:
            downloadURL = a.get("href")

    map_info = [info.get_text(strip=True) for info in map_table.find_all("td")]
    if len(map_info) > 5:
        extracted_match_info = extracted_match_info[:-1]
    return map_info, downloadURL


def parse_player_info(player_table):
    # do the score while we have the players_table
    score = player_table.find("td", class_="csgo_scoreboard_score").get_text(strip=True)

    # grab all rows
    player_rows = player_table.find_all("tr")
    if not player_rows:
        logging.error("Found no player rows!")
        return None, None

    logging.info("Found player_rows...")
    # throwaway the header (first), and score row (7th)
    valid_player_rows = player_rows[1:6] + player_rows[7:]
    players_info = {}
    for player in valid_player_rows:
        player_name = player.find("a", class_="linkTitle").get_text(strip=True)
        # make strings out of every stat but the first one, which is the name
        stats = [s.get_text(strip=True) for s in player.find_all("td")[1:]]
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
    return score, players_info


def scrape_matches(tab, webauth):
    recent_matches = []

    # Look to move this into fetch_match_table
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=webauth.session.headers["User-Agent"])
        logging.info("Setting cookies from SteamAuth...")
        cookies = extract_cookies(webauth.session.cookies)
        context.add_cookies(cookies)

        page = context.new_page()
        # "/my" is an alias for "/id/<community_id"
        gcpd_url = f"https://steamcommunity.com/my/gcpd/730/?tab=matchhistory{tab}"
        if not goto_personal_data(page, gcpd_url):
            logging.error("Unable to go to the personal data page!")
            return None
        match_table = fetch_match_table(page)
        context.close()
        browser.close()

    if not match_table:
        logging.error("Unable to find a match table!")
        return None

    logging.info("Found csgo_scoreboard_root...")
    matches = match_table.find_all("tr", style=re.compile("display: table-row;"))

    if not matches:
        logging.error("Unable to find any matches!")
        return None

    logging.info("Found matches...")
    for match in matches:
        # map_info : Map, Date, Ranked, Wait Time, Match duration, Match Score
        # Players (Player : Stats)
        players_info = {}
        match_info = {}
        # Player (Name) : Ping, Kills, Assists, Deaths, MVPs, HSP, Score
        downloadURL = ""

        # match_info process
        map_table = match.find("table", class_="csgo_scoreboard_inner_left").find(
            "tbody"
        )
        if map_table:
            logging.info("Found map table...")
            map_info, downloadURL = parse_map_info(map_table)
            match_info = {
                "map": map_info[0],
                "date": map_info[1],
                "ranked": map_info[2],
                "wait_time": map_info[3],
                "match_duration": map_info[4],
                "match_score": "",
            }

        # player_info process
        player_table = match.find("table", class_="csgo_scoreboard_inner_right").find(
            "tbody"
        )
        if player_table:
            logging.info("Found player_table...")
            match_info["match_score"], players_info = parse_player_info(player_table)
            # finally, add match_entry to recent_matches
            match_entry = {
                "url": downloadURL,
                "match_info": match_info,
                "players_info": players_info,
            }
            logging.info(f"Match recorded: {match_entry}")
            recent_matches.append(match_entry)

    logging.info(f"Page Scrape complete.")

    return recent_matches, tab
