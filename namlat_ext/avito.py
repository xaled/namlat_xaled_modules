from namlat.modules import AbstractNamlatJob
from namlat.context import context
from lxml import html
import time
import requests
import logging

logger = logging.getLogger(__name__)
with context.localdb:
    if 'modules' not in context.localdb:
        context.localdb['modules'] = dict()
    if __name__ not in context.localdb['modules']:
        context.localdb['modules'][__name__] = {'result_archive': {}}
module_db = context.localdb['modules'][__name__]
result_archive = module_db['result_archive']
BASE_URL = "https://www.avito.ma"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"


class AvitoSearchJob(AbstractNamlatJob):
    def init_job(self):
        # self.report = None
        pass

    def execute(self):
        searches = self.kwargs['searches']
        for search in searches:
            self.run_search(search)

    def run_search(self, search):
        search_id = search["search_id"]
        with context.localdb:
            if not search_id in result_archive:
                result_archive[search_id] = dict()
        report = self.get_report("avito_search_finds", "avito_search_finds_" + search_id,  search["notify_handlers"],
                                 report_title="New results for Avito search: " + search["search_name"],
                                 report_append=True)
        new_items = list()
        for srch in search["search_url"]:
            # time.sleep(random.randint(1, RANDSLEEP_RANGE))

            url = BASE_URL + srch
            page = requests.get(url, headers={'User-agent': USER_AGENT})
            fetch_time = time.time()
            # tree = html.fromstring(page.content)
            tree = html.fromstring(page.text)
            items = tree.xpath('//div[@class="item-age"]')
            parsed_items = list()
            for item in items:
                date = _xpath_warn(item, '*/small/strong/text()', 'date', url)
                # TODO: date aujourd'hui, hier
                title = _xpath_warn(item, '../div//h2/a/text()', 'title', url)
                link = _xpath_warn(item, '../div//h2/a/@href', 'link', url)
                # link = url_fix(link)  # TODO test
                price = _xpath_warn(item, '../div/span/span/text()', 'price', url, ignore=True)
                parsed_items.append(
                    {"date": date, "title": title, "link": link, "price": price, "fetch_time": fetch_time})
            logger.debug("len(parsed_items)=%d", len(parsed_items))
            for item in parsed_items:
                with context.localdb:
                    if not item['link'] in result_archive[search_id]:
                        result_archive[search_id][item['link']] = item
                        logger.debug("adding to new items %s" % item)
                        new_items.append(item)
                        report.append_report_entry("(%s DH) - %s - %s" % (item['price'], item['date'], item['title']),
                                                   item['link'], item['link'])
        logger.debug("len(new_items)=%d" % len(new_items))
        report.send_report()
        # for notify_method in search["notify"]:
        #     if notify_method == 'mail':
        #         notify_mail(search, new_items)
        #     elif notify_method == "daily-mail":
        #         notify_daily_mail(search, new_items)
        #     elif notify_method == "weekly-mail":
        #         notify_weekly_mail(search, new_items)
        #     elif notify_method == "monthly-mail":
        #         notify_monthly_mail(search, new_items)
        #     else:
        #         pass
        #


def _xpath_warn(item, path, field, url, ignore=False):
    try:
        res = item.xpath(path)
        if not ignore:
            if len(res) == 0:
                logger.error("unable to fetch field: %s in url: %s", field, url)
            elif len(res) > 1:
                logger.warning("got multiple results fetching field: %s in url: %s", field, url)
        if len(res)==0:
            return ''
        else:
            return res[0]
    except:
        logger.error("unable to fetch field: %s in url: %s.", field, url, exc_info=True)


# def url_fix(s, charset='utf-8'):
#     """
#     https://stackoverflow.com/questions/120951/how-can-i-normalize-a-url-in-python
#     Sometimes you get an URL by a user that just isn't a real
#     URL because it contains unsafe characters like ' ' and so on.  This
#     function can fix some of the problems in a similar way browsers
#     handle data entered by the user:
#     :param charset: The target charset for the URL if the url was
#                     given as unicode string.
#     """
#     if isinstance(s, unicode):
#         s = s.encode(charset, 'ignore')
#     scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
#     path = urllib.quote(path, '/%')
#     qs = urllib.quote_plus(qs, ':&=')
#     return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))
