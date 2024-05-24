import os
import tqdm
from datetime import datetime, timedelta
import logging
import json

logging.basicConfig(level=logging.INFO)

CACHE_FILE = "cache.json"
CACHE_EXPIRY_DAYS = 60


def url_downloader(session, urls, destination_folder):
    metadata = load_metadata()
    remove_old_urls(metadata)

    for url in urls:
        filename, downloaded = download_file(session, url, metadata, destination_folder)
        if downloaded:
            logging.info(f"Downloaded: {filename}")
        else:
            logging.info(f"Already exists: {filename}")


def load_metadata():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {"files": []}
    # return json from loaded file, or new empty json list


def save_metadata(metadata):
    with open(CACHE_FILE, "w") as f:
        json.dump(metadata, f, indent=4)


def get_filename_from_url(url):
    return url.split("/")[-1]


def is_cached(url, metadata):
    for entry in metadata["files"]:
        if entry["url"] == url:
            return entry
    return None


def ensure_dir(folderpath):
    if not os.path.exists(folderpath):
        os.makedirs(folderpath)
        logging.info(f"{folderpath} created.")


def remove_old_urls(metadata):
    current_time = datetime.now()
    metadata["files"] = [
        entry
        for entry in metadata["files"]
        if current_time - datetime.fromisoformat(entry["download_date"])
        <= timedelta(days=CACHE_EXPIRY_DAYS)
    ]
    save_metadata(metadata)


def download_file(session, url, metadata, destination_folder):
    entry = is_cached(url, metadata)
    if entry:
        logging.info(f"Skipping {entry}: {url}")
        return entry["filename"], False

    response = session.get(url, stream=True)
    response.raise_for_status()

    filename = get_filename_from_url(url)
    folderpath = os.path.join(os.getcwd(), "demos/" + destination_folder)
    ensure_dir(folderpath)
    filepath = os.path.join(folderpath, filename)

    with open(filepath, "wb") as f, tqdm.tqdm(
        desc=filename,
        total=int(response.headers.get("content-length", 0)),
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))

    entry = {
        "url": url,
        "filename": filename,
        "download_date": datetime.now().isoformat(),
    }

    metadata["files"].append(entry)
    save_metadata(metadata)
    return filename, True
