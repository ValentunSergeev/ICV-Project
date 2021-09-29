from typing import List, Tuple
from requests_html import HTMLSession

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os.path
from pathlib import Path
import re

HEADERS = {
    "Host": "readmanga.live",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "sec-ch-ua": '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Referer": "https://readmanga.live/neveroiatnye_prikliucheniia_djodjo_chast_7__steel_ball_run__cvetnaia_versiia___A5327",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-GB,en;q=0.9,ru-GB;q=0.8,ru;q=0.7,nl-GB;q=0.6,nl;q=0.5,en-US;q=0.4",
    "Cookie": "_ym_uid=1631965563163149659; _ym_d=1631965563; _ym_isad=1; resize_type=real; resize_type_web=width; JSESSIONID=49A02ACE018AE03635B2B34B13A9AFB2; reader-mode=web; sso_timeout=Sat%20Sep%2018%202021%2018:20:35%20GMT+0300%20(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5%20%D0%B2%D1%80%D0%B5%D0%BC%D1%8F)"
}

session = HTMLSession()
session.cookies.set("reader-mode", "web", domain="readmanga.live")
session.cookies.set("resize_type_web", "real", domain="readmanga.live")
session.headers.update(HEADERS)

RESTRICTED_GENRES = {"гарем", "гендерная интрига", "арт", "додзинси", "кодомо", "сёдзё-ай", "сёнэн-ай", "этти", "юри",
                     "сянься", "уся"}

HOST = "https://readmanga.live/"


def join_with_host(host, relative):
    return urljoin(host, relative)


def text_and_link(anchor):
    return anchor.contents[0], anchor["href"]


def normalize(text: str):
    return text.replace("\n", "").replace(" ", "")


def crawl_manga(genre, name, relative_url):
    print(f"\t{name}")

    full_url = join_with_host(HOST, relative_url)

    normalized_name = "".join(x for x in name if x.isalnum())

    page = requests.get(full_url, headers=HEADERS).content
    dom = BeautifulSoup(page, 'html.parser')

    chapter_table = dom.find("table")

    # no manga contents
    if chapter_table is None:
        return

    last_chapter_anchor = chapter_table.find("a", attrs={"class": "chapter-link"})
    chapter_title, chapter_link = text_and_link(last_chapter_anchor)
    chapter_title = normalize(chapter_title)

    chapter_page = session.get(join_with_host(HOST, chapter_link), headers=HEADERS)
    chapter_page.html.render(timeout=20, scrolldown=10000, send_cookies_session=True)

    images = chapter_page.html.find("#mangaPicture")

    for index, image in enumerate(images):
        image_url = image.attrs["src"]

        if image_url == "#":
            break

        print(f"\t\tDownloading {index}/{len(images)} {image_url}", flush=True)

        response = requests.get(image_url)

        image_data = response.content

        Path(f"data/{genre}/{normalized_name}").mkdir(parents=True, exist_ok=True)

        with open(f"data/{genre}/{normalized_name}/{index}.jpg", "wb") as fout:
            fout.write(image_data)


PAGE_SIZE = 70


def crawl_genre_page(full_url, page_number: int) -> List[Tuple[str, str]]:
    offset = PAGE_SIZE * page_number

    page = requests.get(full_url, headers=HEADERS, params={"offset": offset}).content
    dom = BeautifulSoup(page, 'html.parser')

    manga_elements = dom.find_all("div", attrs={"class": "desc"})
    manga_anchors = [e.find_next("h3").find_next("a") for e in manga_elements]

    return [text_and_link(a) for a in manga_anchors]


REQUIRED_MANGAS = 10


def crawl_genre(name, relative_url, visited_mangas: set):
    print(f"{name}:")

    full_url = join_with_host(HOST, relative_url)

    new_mangas = []
    page_number = 0

    while len(new_mangas) < REQUIRED_MANGAS:
        page_mangas = crawl_genre_page(full_url, page_number)

        for title, link in page_mangas:
            if title in visited_mangas:
                continue

            visited_mangas.add(title)
            new_mangas.append((title, link))

            if len(new_mangas) == REQUIRED_MANGAS:
                break

        page_number += 1

    # print(f"{name} ({page_number} pages)":{new_titles}")

    for title, link in new_mangas:
        crawl_manga(name, title, link)


def crawl(relative_path: str):
    url = join_with_host(HOST, relative_path)

    page = requests.get(url, headers=HEADERS).content

    dom = BeautifulSoup(page, 'html.parser')

    genre_elements = dom.find_all("a", attrs={"class": "element-link"})
    visited_magnas = set()

    for e in genre_elements:
        name, link = text_and_link(e)

        if name not in RESTRICTED_GENRES:
            crawl_genre(name, link, visited_magnas)


crawl(relative_path="list/genres/sort_name")
