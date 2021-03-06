from urllib import parse
from selenium.webdriver.common.timeouts import Timeouts
from .config import headers, proxies, Blacklist, path_webdriver
from .class_Logs import logger
import requests
from bs4 import BeautifulSoup
from time import sleep
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from selenium.webdriver import Chrome, ChromeOptions

timeouts = Timeouts()
timeouts.implicit_wait = 15
timeouts.page_load = 15
timeouts.script = 15


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Browser:
    def __init__(self):
        self.__headers = headers.copy()
        self.__headers.pop('Cookie')
        self.__proxies = proxies.copy()
        self.__html = BeautifulSoup()

        # Веб-драйвер и настройки для Selenium
        self.__options = ChromeOptions()
        self.__options.add_argument('headless')
        self.__options.add_argument("–disable-infobars")
        self.__options.add_argument("–enable-automation")
        self.__options.add_argument("--disable-notifications")
        self.__options.add_argument("--log-level=3")
        self.__driver = Chrome(executable_path=path_webdriver, options=self.__options)
        self.__driver.timeouts = timeouts

        self.__domain_has = False  # Проверка: был ли получен домен для текущего url
        self.__domain = None
        self.__url = None
        self.__cookie = None

    # Завершение работы веб-драйвера
    def close_driver(self):
        self.driver.close()

    @property
    def driver(self):
        return self.__driver

    @property
    def cookie(self):
        return self.__cookie

    @cookie.setter
    def cookie(self, value):
        self.__cookie = value

    @property
    def domain_has(self):
        return self.__domain_has

    @domain_has.setter
    def domain_has(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"Передан класс {type(value)}. Ожидался класс Bool.")
        self.__domain_has = value

    # Возвращает весь текст с HTML страницы
    @staticmethod
    def get_text(item, log=True):
        try:
            all_text = item.text
        except Exception as err:
            if log:
                logger.FAIL('Text not found', item.url, repr(err))
            all_text = ''
        return all_text

    @property
    def url(self):
        return self.__url

    @url.setter
    def url(self, url):
        self.__url = url
        self.domain_has = False

    # При вызове свойства domain из url'а вычленяется его домен
    @property
    def domain(self):
        if not self.url:
            raise Exception("URL is None type. Use .get or .url")
        if not self.domain_has:
            self.__domain = self.domain_parser(self.url)
        return self.__domain

    # Функция вычленения домена из ссылки (без www)
    @staticmethod
    def domain_parser(url):
        domain = parse.urlsplit(url).netloc
        if domain[0:3] == 'www':
            return domain[4:]
        return domain

    # Получение кода HTML страницы по текущему url
    @property
    def html(self):
        return self.__html

    @html.setter
    def html(self, soup):
        if not isinstance(soup, BeautifulSoup):
            raise TypeError(f"Передан класс {type(soup)}. Ожидался класс BeautifulSoup.")
        self.__html = soup

    # Отправка GET запроса странице при помощи Selenium
    def __selen_connect(self, url, info):
        logger.INFO(info, url)
        self.driver.get(url)
        self.html = BeautifulSoup(self.driver.page_source, 'lxml')

    # Отправка GET запроса странице при помощи requests
    def __connect(self, url, time, google, selen, verify=True, info='Connecting to'):
        if selen:
            self.__selen_connect(url, info)
            return
        sleep(time)
        logger.INFO(info, url)
        response = requests.get(url=url, headers=self.__headers, timeout=(5, 5), verify=verify)
        self.html = BeautifulSoup(response.text, 'lxml')

    # Функция отправки серии GET запросов странице (либо requests, либо Selenium)
    def get(self, url, time=0, google=False, selen=False):
        self.url = url
        if self.domain in Blacklist:
            logger.WARN('Website in Blacklist', self.url)
            return None
        try:
            self.__connect(url, time, google, selen)
        except Exception as err:
            logger.WARN('Failed connect to', url, repr(err))
            try:
                self.__connect(url, time, google, selen, verify=False, info='Reconnecting to')
            except Exception as err:
                logger.FAIL('Not connected to', url, repr(err))
                return None
        return self.html
