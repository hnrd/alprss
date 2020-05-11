import dbm
import json

import requests
from bs4 import BeautifulSoup
from flask import Flask


class Store:
    def __init__(self, dbo):
        self.db = dbo

    def add_version(self, pkg, version, bdate, branch='v3.11', arch='x86_64'):
        pkg_key = json.dumps((pkg, branch, arch))
        versions = json.loads(self.db.get(pkg_key, "{}"))
        if bdate not in versions:
            versions[bdate] = version
        self.db[pkg_key] = json.dumps(versions)

    def get_feed(self, pkgs=None, branch='v3.11', arch='x86_64'):
        items = []
        if not pkgs:
            pkgs = ['bash']
        for pkg in pkgs:
            pkg_key = json.dumps((pkg, branch, arch))
            items = items + [(pkg, x[0], x[1]) for x in json.loads(self.db.get(pkg_key, "{}")).items()]
        return gen_feed(items)


app = Flask(__name__)
db = dbm.open('/data/cache', 'c')
pkg_store = Store(db)


def get_release(pkg, branch="v3.11", arch="x86_64"):
    req = requests.get(
        "https://pkgs.alpinelinux.org/packages?name={}&branch={}&arch={}".format(
            pkg,
            branch,
            arch,
        )
    )
    soup = BeautifulSoup(req.text, 'html.parser')
    if not soup.find_all("td", class_="version"):
        return None
    if branch == "edge":  # literal edge case -_-
        ver_link = soup.find_all("td", class_="version")[0].contents[1]
        version = ver_link.find_all("a")[0].contents[0]
    else:
        version = soup.find_all("td", class_="version")[0].contents[0]
    bdate = soup.find_all("td", class_="bdate")[0].contents[0]
    return (version, bdate)


def gen_feed(items):
    from feedgen.feed import FeedGenerator
    from slugify import slugify
    feedgen = FeedGenerator()
    feedgen.id('https://alprss.zknt.org/feed/1')
    feedgen.title('alpine packagefeed')
    feedgen.link(href='https://alprss.zknt.org/', rel="alternate")
    feedgen.description('packages')
    for item in items:
        feedentry = feedgen.add_entry()
        feedentry.id('https://alprss.zknt.org/{}/{}-{}'.format(slugify(item[0]), slugify(item[2]), slugify(item[1])))
        feedentry.title("{} version: {}".format(item[0], item[2]))
        feedentry.published(item[1] + ' UTC')
    return feedgen


@app.route('/rss')
def handle():
    """ Dump all known packags to feed. """
    for pkg in ["bash"]:
        try:
            version, bdate = get_release(pkg)
            pkg_store.add_version(pkg, version, bdate)
        except TypeError:
            pass
    return pkg_store.get_feed().rss_str()


@app.route('/rss/<pkglist>')
def handle_list(pkglist):
    for pkg in pkglist.split(','):
        try:
            version, bdate = get_release(pkg)
            pkg_store.add_version(pkg, version, bdate)
        except TypeError:
            pass
    return pkg_store.get_feed(pkglist.split(',')).rss_str()


@app.route('/rss/<branch>/<arch>/<pkglist>')
def handle_params(branch, arch, pkglist):
    for pkg in pkglist.split(','):
        try:
            version, bdate = get_release(pkg, branch=branch, arch=arch)
            pkg_store.add_version(pkg, version, bdate, branch, arch)
        except TypeError:
            pass
    return pkg_store.get_feed(pkglist.split(','), branch, arch).rss_str()


@app.route('/')
def index():
    import markdown
    return markdown.markdown("""
# alprss
   
Provide alpine package search results as RSS feed.

## Usage:

    GET /rss/your,package,list

This will combine results for the packages `your`, `package` and `list`.
Requesting information on non-existant packages will result in empty output.
Search is restricted to alpines latest stable branch, and arch x86_64 by default.

    GET /rss/branch/arch/your,package,list

Same as above, but queries supplied alpine branch and arch.

### Example:

    curl https://alprss.zknt.org/rss/vim,emacs
""")
