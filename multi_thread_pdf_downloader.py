import os
import time
import random
import requests
import threading

from queue import Queue
from lxml import etree


class Proxy:
    def __init__(self, proxy_source, headers, proxy_path,
                 test_url='http://www.baidu.com'):
        self.proxy_source = proxy_source
        self.headers = headers
        self.proxy_path = proxy_path
        self.test_url = test_url
        if os.path.exists(self.proxy_path):
            self.proxies = [line.strip().split(',') for line in
                            open(self.proxy_path, 'r').readlines()]
        else:
            self.proxies = []

    def update_proxies(self, page_num):
        with open(self.proxy_path, 'w+') as fw:
            for i in range(page_num):
                url = self.proxy_source + str(i + 1)
                self.headers['Referer'] = url + str(i) if i > 0 else url
                response = requests.get(url, headers=self.headers)
                html = etree.HTML(response.text)
                lines = html.xpath('//body//tr')
                for index, line in enumerate(lines):
                    if index == 0:
                        continue
                    protocol = line.xpath('./td[6]/text()')[0]
                    host = line.xpath('./td[2]/text()')[0]
                    port = line.xpath('./td[3]/text()')[0]
                    if self.get_html_page_with_proxy((protocol,
                                                      host, port)) is not None:
                        fw.write(','.join((protocol, host, port)) + '\n')
                time.sleep(random.uniform(1, 3))
        self.proxies = [line.strip().split(',') for line in
                        open(self.proxy_path, 'r').readlines()]

    def get_html_page_with_proxy(self, proxy, url=''):
        if not url:
            url = self.test_url
        protocol, host, port = proxy
        try:
            response = requests.get(url, proxies={protocol: host + ':' + port},
                                    timeout=2)
            html = etree.HTML(response.text)
            return html
        except Exception:
            return None

    def get_proxy(self, test_url=''):
        if not test_url:
            test_url = self.test_url
        while True:
            proxy = random.choice(self.proxies)
            if self.get_html_page_with_proxy(proxy) is not None:
                return {proxy[0]: proxy[1] + ':' + proxy[2]}


def get_http_response(url, proxy=None):
    if isinstance(proxy, Proxy):
        auto_proxy = proxy.get_proxy(url)
        time.sleep(random.uniform(1, 3))
        response = requests.get(url, proxies=auto_proxy, timeout=2)
    else:
        response = requests.get(url)
    return response


class DownloadThread(threading.Thread):
    def __init__(self, dist, page_queue, pdf_queue, proxy=None):
        threading.Thread.__init__(self)
        self.dist = dist
        self.page_queue = page_queue
        self.pdf_queue = pdf_queue
        self.proxy = proxy

    def get_url_fields(self, url):
        fields = url.split('?')[-1].split('&')
        mapper = {}
        for field in fields:
            key, value = field.split('=')
            mapper[key] = value
        return mapper

    def download_pdf(self, url):
        fields = self.get_url_fields(url)
        year, quarter, file_no = \
            fields['year_id'], fields['quarter_id'], fields['file_no']
        par_path = os.path.join(self.dist, year, quarter)
        path = os.path.join(par_path, file_no + '.pdf')
        if not os.path.exists(par_path):
            try:
                os.makedirs(par_path)
            except Exception:
                pass
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print('File already exists, skipped.', path)
            return
        try_count = 0
        while True:
            try:
                response = get_http_response(url, self.proxy)
                with open(path, 'wb') as fw:
                    fw.write(response.content)
                print('Download Complete.', path)
                return
            except Exception as e:
                try_count += 1
                if try_count >= 3:
                    print(url, e)
                    self.pdf_queue.put(url)
                    return

    def run(self):
        while True:
            if self.pdf_queue.empty() and self.page_queue.empty():
                print('Download Finished')
                return
            next_url = self.pdf_queue.get()
            self.download_pdf(next_url)
            time.sleep(random.uniform(1, 3))


class SpiderThread(threading.Thread):
    def __init__(self, prefix, page_queue, pdf_queue, proxy=None):
        threading.Thread.__init__(self)
        self.prefix = prefix
        self.page_queue = page_queue
        self.pdf_queue = pdf_queue
        self.proxy = proxy

    def run(self):
        while True:
            if self.page_queue.empty():
                return
            url = self.page_queue.get()
            self.parse_page(url)

    def parse_page(self, url):
        response = get_http_response(url, self.proxy)
        html = etree.HTML(response.text)
        pdf_list = html.xpath('.//a[contains(@href, "create_pdf")]/@href')
        for pdf in pdf_list:
            self.pdf_queue.put(self.prefix + pdf)


class PDFDownloader():
    def __init__(self, prefix, url, dist, spider_thread=4, download_thread=8,
                 proxy=None):
        self.prefix = prefix
        self.url = url
        self.dist = dist
        self.spider_thread = spider_thread
        self.download_thread = download_thread
        self.pdf_queue = Queue(0)
        self.page_queue = Queue(0)
        self.proxy = proxy

    def update_page_queue(self):
        response = get_http_response(self.url, self.proxy)
        html = etree.HTML(response.text)
        year_list = html.xpath('//body//tr//tr//tr//tr//tr')
        for year in year_list:
            quarter_list = year.xpath('./td[2]//li/a/@href')
            for quarter in quarter_list:
                self.page_queue.put(self.prefix + quarter)

    def download_pdf(self):
        self.update_page_queue()
        print('Update page queue done. Total: {}'.format(
            self.page_queue.qsize()))

        for i in range(self.spider_thread):
            thread = SpiderThread(self.prefix, self.page_queue,
                                  self.pdf_queue, self.proxy)
            thread.start()

        for i in range(self.download_thread):
            thread = DownloadThread(self.dist, self.page_queue,
                                    self.pdf_queue, self.proxy)
            thread.start()


if __name__ == '__main__':
    proxy_source = 'http://www.xicidaili.com/nn/'
    headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,\
                       image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
                           AppleWebKit/537.36 (KHTML, like Gecko) \
                           Chrome/68.0.3440.75 Safari/537.36'
            }
    proxy = Proxy(proxy_source, headers, 'ip_pool.csv',
                  'http://www.jos.org.cn/jos/ch/reader/issue_browser.aspx')
    # proxy.update_proxies(10)
    prefix = 'http://www.jos.org.cn/jos/ch/reader/'
    url = 'http://www.jos.org.cn/jos/ch/reader/issue_browser.aspx'
    dist = 'data\\journal_of_software'
    pdf_downloader = PDFDownloader(prefix, url, dist, proxy=proxy)
    pdf_downloader.download_pdf()
