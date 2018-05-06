from namlat.modules import AbstractNamlatJob
from namlat.context import context
import time
import logging
import json
from xaled_scrapers.selenium import get_firefox_proxy_caps, init_driver, get_display
from xaled_scrapers.proxy import Proxy

logger = logging.getLogger(__name__)
with context.localdb:
    if 'modules' not in context.localdb:
        context.localdb['modules'] = dict()
    if __name__ not in context.localdb['modules']:
        context.localdb['modules'][__name__] = {'operation-ids': [], 'operations': {}, 'evolution': {}, 'factures': {}}
module_db = context.localdb['modules'][__name__]


class Ch3ibaJob(AbstractNamlatJob):
    def init_job(self):
        self.operation_report = self.get_report("chaabi_operations", "chaabi_operations", self.kwargs['operation_handlers'],
                                           report_title="New Ch3iba operations", report_append=True)
        self.factures_report = self.get_report("chaabi_factures", "chaabi_factures", self.kwargs['factures_handlers'],
                                           report_title="New Ch3iba factures")

    def execute(self):
        try:
            self.display = get_display()
            self.proxy = Proxy()
            self.proxy.set_intercept_params('bpnet.gbp.ma',
                                            ['/DashBoard/GetUserAccountBalanceEvolution',
                                             '/DashBoard/GetAccountStatement'])
            self.driver = init_driver(caps=get_firefox_proxy_caps(proxy=self.proxy.proxy_address))
            self.login()
            self.parse_operations()
            self.check_factures()
            # factures = self.check_factures()
            # for f in factures:
            #     print("- %s: %d new factures." % (f['label'], f['#']))
        except:
            logger.error("Error while executing Ch3ibaJob instance", exc_info=True)
        finally:
            try: self.driver.quit()
            except: pass
            try: self.proxy.stop()
            except: pass
            try: self.display.stop()
            except: pass

    def login(self):
        # driver.get("https://bpnet.gbp.ma/")
        self.driver.get("https://bpnet.gbp.ma/Account/Login")
        self.driver.find_element_by_id("UserName").send_keys(self.kwargs['user'])
        self.driver.find_element_by_id("Password").send_keys(self.kwargs['password'])
        self.driver.find_element_by_id("btnLogin").click()

    def parse_operations(self):
        intercpeted_data = self.proxy.get_intercept_data()
        wait = 0
        while len(intercpeted_data) < 2 and wait < 10:
            logger.info("Sleeping for 2s...")
            time.sleep(2)
            wait += 2
            intercpeted_data.update(self.proxy.get_intercept_data())

        # wait, sometimes you need to wait
        try:
            operations = json.loads(intercpeted_data['/DashBoard/GetAccountStatement'])
            for operation in operations:
                operation = dict(operation)
                opid = operation['RefOpe'] + '-' + operation['Dateope']
                operation['opid'] = opid
                with context.localdb:
                    if opid not in module_db['operation-ids']:
                        module_db['operation-ids'].append(opid)
                        module_db['operations'][opid] = operation
                        self.operation_report.append_report_entry(operation['Dateope'] + "-" + operation['LibOpe'].strip(),
                                                                  "%s DH" % operation['Montant'], opid)
            self.operation_report.send_report()
        except:
            logger.error("Error parsing AccountStatement.", exc_info=True)

        try:
            evolution = json.loads(intercpeted_data['/DashBoard/GetUserAccountBalanceEvolution'])[0]['BalanceEvolution']
        except:
            logger.error("Error parsing UserAccountBalanceEvolution.", exc_info=True)
            evolution = []
        with context.localdb:
            for item in evolution:
                module_db['evolution'][item['Dateope']] = float(item['Solde'].replace(',', '.'))

    def check_factures(self):
        i = -1
        while True:
            i += 1
            try:
                self.driver.get('https://bpnet.gbp.ma/Payment/Favorite')
                self.driver.execute_script("window.scrollTo(0, 2000)")
                factures = self.driver.find_elements_by_xpath("//button[@class='unstylled_btn']")
                labels = [e.text for e in
                          self.driver.find_elements_by_xpath("//td[contains(@class,'operationLibelle')]/span")]
                if i >= len(factures):
                    break
                logger.info("getting facture #%d", (i + 1))
                factures[i].click()
                self.driver.execute_script("window.scrollTo(0, 2000)")
                if self.driver.current_url != 'https://bpnet.gbp.ma/PaymentCategory/1':  # ignore category = recharges mobiles
                    nbr_factures = len(self.driver.find_elements_by_xpath("//tr[@class='negatif_transaction']"))
                    if nbr_factures > 0:
                        # f = {'label': labels[i], '#': nbr_factures }
                        msg = "%d new %s factures." % (nbr_factures, labels[i])
                        self.factures_report.append_report_entry(msg, msg)
            except:
                logger.error("error parsing facture #%d", (i + 1), exc_info=True)
        self.factures_report.send_report()
