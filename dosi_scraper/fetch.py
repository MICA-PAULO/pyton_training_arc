"""Nette HTTP-laag: controleert robots.txt, wacht tussen verzoeken en probeert
opnieuw bij tijdelijke fouten. Zie het juridisch kader in het onderzoeksplan
(ECLI:NL:RBAMS:2024:6563 over robots.txt en artikel 15o Auteurswet).
"""

import time
import urllib.robotparser
from urllib.parse import urlsplit

import requests

from . import config


class RobotsVerbod(Exception):
    """De website staat deze URL niet toe volgens robots.txt."""


class Fetcher:
    def __init__(self, delay=config.DELAY, user_agent=config.USER_AGENT):
        self.delay = delay
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._robots = {}
        self._laatste = 0.0

    def _robots_voor(self, url):
        parts = urlsplit(url)
        basis = f"{parts.scheme}://{parts.netloc}"
        if basis not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.session.get(basis + "/robots.txt", timeout=30)
                if r.status_code in (401, 403):
                    rp.disallow_all = True
                elif r.ok:
                    rp.parse(r.text.splitlines())
                else:
                    rp.allow_all = True
            except requests.RequestException:
                # Geen robots.txt bereikbaar: voor de zekerheid niets scrapen.
                rp.disallow_all = True
            self._robots[basis] = rp
        return self._robots[basis]

    def mag(self, url):
        return self._robots_voor(url).can_fetch(self.user_agent, url)

    def get(self, url, params=None, pogingen=4):
        if not self.mag(url):
            raise RobotsVerbod(url)
        for poging in range(pogingen):
            wacht = self.delay - (time.monotonic() - self._laatste)
            if wacht > 0:
                time.sleep(wacht)
            self._laatste = time.monotonic()
            try:
                r = self.session.get(url, params=params, timeout=60)
            except requests.RequestException:
                if poging == pogingen - 1:
                    raise
            else:
                if r.status_code not in (429, 500, 502, 503, 504):
                    r.raise_for_status()
                    return r
            time.sleep(2 ** (poging + 1))
        r.raise_for_status()
        return r
