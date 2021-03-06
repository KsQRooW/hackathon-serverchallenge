from copy import deepcopy
from .class_Browser import Browser
from .class_Text import Text, inn
from .class_Logs import logger
import re
from datetime import datetime
from .config import supplier_sorting_params, ideal_supplier_parameters


class Supplier(Browser):    # Класс для работы с поставщиками

    def __init__(self):
        super().__init__()
        self.__list_inn = []
        self.__inn = ''
        self.website = ''
        self.__supplier_data = {}

    @property
    def inn(self):
        return self.__inn

    @inn.setter
    def inn(self, inn):
        self.__inn = inn

    # Поиск ИНН по адресу сайта
    def find_inn_by_url(self, site):
        self.website = site
        self.__inn = ''
        logger.INFO('Start INN search by the site address', self.website)
        if self.__find_inn_spark():
            if len(self.__list_inn) == 1:
                self.__inn = self.__list_inn[0]
                logger.INFO('INN found: ' + self.inn)
            elif len(self.__list_inn) == 0:
                logger.FAIL('INN not found in database spark-interfax')
                return False
            else:
                logger.WARN('Few INN found: ' + ' '.join(self.__list_inn))
                self.__select_one_inn()
            return True
        return False

    # Проверка, содержится ли домен site в списке urls
    def __is_right_url(self, urls):
        for temp in urls:
            if self.get_text(temp) in (self.website, 'www.' + self.website):
                return True
        return False

    # Поиск ИНН по адресу сайта в базе данных spark-interfax.ru
    def __find_inn_spark(self):
        general_url = 'https://spark-interfax.ru/search?Query='
        self.__list_inn = []
        url = general_url + self.website
        self.get(url, time=1)
        list_items = self.html.find_all('li', class_='search-result-list__item')
        if len(list_items) == 0:
            logger.FAIL('INN not found in database spark-interfax')
            return False
        else:
            for item in list_items:
                urls = item.find_all('span', class_='highlight')
                if self.__is_right_url(urls):
                    data = self.get_text(item.find('div', class_='code')).split()
                    i = 0
                    while i < len(data):
                        if data[i] == 'ИНН':
                            self.__list_inn.append(data[i + 1])
                        i += 1
                else:
                    logger.WARN('Wrong site', self.get_text(item.find('span', class_='highlight')))    # debug
        return True

    # Из нескольких найденных ИНН выбрать один (более новый)
    def __select_one_inn(self):
        general_url = 'https://sbis.ru/contragents/'
        dates = {}
        logger.INFO('Search for the newest INN')
        for temp_inn in self.__list_inn:
            url = general_url + temp_inn
            # self.get(url, time=2)
            self.get(url, selen=True)
            # Проверка действующая ли компания или нет
            liquidated = self.get_text(self.html.find('div', class_='c-sbisru-CardStatus__closed'), log=False)
            if not liquidated:
                inf = self.get_text(self.html.find('div', class_='cCard__CompanyDescription'), log=False)
                try:
                    strdate = re.search(r'Действует с \d\d.\d\d.\d\d\d\d', inf).group()[12:]
                except Exception as er:
                    logger.FAIL('Date not found', err=repr(er))
                    continue
                # Сохранение даты регистрации каждого ИНН
                dates[datetime.strptime(strdate, '%d.%m.%Y')] = temp_inn
            else:
                logger.WARN('INN ' + temp_inn + ' liquidated')
        if dates:
            # Выбор ИНН с самой свежей датой регистрации
            self.__inn = dates[max(dates.keys())]
            logger.INFO('INN found: ' + self.inn)
            return True
        else:
            logger.FAIL('INN not found in database spark-interfax')
            return False

    # Ранжирование поставщиков (для 1 поставщика)
    def ranking(self, koefs=None):
        # keys = ('Госконтракты', 'Истец', 'Надежность', 'Ответчик', 'Прибыль', 'Уставный капитал', 'Тендер', 'Выручка', 'Стоимость')
        if koefs:
            coefs = koefs
        else:
            coefs = [10, 1, 2, 1, 0.5, 0.5, 10, 0.1, 0.1]
        sokr = {'млн ₽': 1000000, 'тыс ₽': 1000, 'млрд ₽': 1000000000}
        rating = 0
        if self.__supplier_data['Госконтракты'] != '':
            rating += int(self.__supplier_data['Госконтракты']) * coefs[0]
        if self.__supplier_data['Истец'] != '':
            win = self.__supplier_data['Истец']['Выиграл'][:-1]
            lose = self.__supplier_data['Истец']['Проиграл'][:-1]
            if win != '':
                if lose != '' and lose != '0':
                    rating += int(win) / int(lose) * coefs[1]
                else:
                    rating += int(win) * coefs[1]
            elif lose != '':
                rating -= int(lose) * coefs[1]
        if self.__supplier_data['Надежность']['Минусы'] != '':
            rating -= float(self.__supplier_data['Надежность']['Минусы'][2:]) * coefs[2]
        if self.__supplier_data['Надежность']['Плюсы'] != '':
            rating += float(self.__supplier_data['Надежность']['Плюсы'][2:]) * coefs[2]
        if self.__supplier_data['Ответчик'] != '':
            win = self.__supplier_data['Ответчик']['Выиграл'][:-1]
            lose = self.__supplier_data['Ответчик']['Проиграл'][:-1]
            if win != '':
                if lose != '' and lose != '0':
                    rating += int(win) / int(lose) * coefs[3]
                else:
                    rating += int(win) * coefs[3]
            elif lose != '':
                rating -= int(lose) * coefs[1]
        if self.__supplier_data['Прибыль'] != '':
            key = re.search(r'млн ₽|тыс ₽|млрд ₽', self.__supplier_data['Прибыль']).group()
            value = re.sub(r' млн ₽| тыс ₽| млрд ₽', r'', self.__supplier_data['Прибыль'])
            rating += sokr[key] * float(value) * coefs[4]
        if self.__supplier_data['Уставный капитал'] != '':
            key = re.search(r'млн ₽|тыс ₽|млрд ₽', self.__supplier_data['Прибыль']).group()
            value = re.sub(r' млн ₽| тыс ₽| млрд ₽', r'', self.__supplier_data['Прибыль'])
            rating += sokr[key] * float(value) * coefs[5]
        if self.__supplier_data['Тендер'] != '':
            win = self.__supplier_data['Тендер']['Выиграл']
            just = self.__supplier_data['Тендер']['Участник']
            if win != '':
                if just != '' and just != '0':
                    rating += int(win) / int(just) * coefs[6]
        if self.__supplier_data['Выручка'] != '':
            key = re.search(r'млн ₽|тыс ₽|млрд ₽', self.__supplier_data['Выручка']).group()
            value = re.sub(r' млн ₽| тыс ₽| млрд ₽', r'', self.__supplier_data['Выручка'])
            rating += sokr[key] * float(value) * coefs[7]
        if self.__supplier_data['Стоимость'] != '':
            key = re.search(r'млн ₽|тыс ₽|млрд ₽', self.__supplier_data['Стоимость']).group()
            value = re.sub(r' млн ₽| тыс ₽| млрд ₽', r'', self.__supplier_data['Стоимость'])
            rating += sokr[key] * float(value) * coefs[8]
        self.__supplier_data['Рейтинг'] = "{0:.2f}".format(rating)

    @staticmethod
    def clearing(markets, coefs):
        sokr = {'млн ₽': 1000000, 'тыс ₽': 1000, 'млрд ₽': 1000000000}
        for market in markets:
            for key in coefs:
                key_0 = key.split(', ')[0]
                val = market[key_0]
                if isinstance(val, dict):
                    for k in val:
                        nominal = re.search(r'млн ₽|тыс ₽|млрд ₽', val[k])
                        if val[k] and nominal:
                            market[key_0][k] = str(
                                float(re.sub(r' млн ₽| тыс ₽| млрд ₽', r'', val[k])) * sokr[nominal.group()])
                        else:
                            market[key_0][k] = re.sub(r'\+|\-|\%', r'', val[k])
                else:
                    nominal = re.search(r'млн ₽|тыс ₽|млрд ₽', val)
                    if val and nominal:
                        market[key_0] = str(float(re.sub(r' млн ₽| тыс ₽| млрд ₽', r'', val)) * sokr[nominal.group()])
                    else:
                        market[key_0] = re.sub(r'\+|\-|\%', r'', val)
        return markets

    @staticmethod
    def normalize(markets: list[dict], coefs):
        val_for_coefs = []
        for name_coef in coefs:
            words_name_coef = name_coef.split(', ')
            if len(words_name_coef) == 1:
                x = list(map(lambda m: m[name_coef], markets))
                if 'дата' in map(lambda w: w.lower(), words_name_coef[0].split()):
                    try:
                        days_x = list(map(lambda d: datetime.now() - datetime.strptime(d, '%d.%m.%Y'), x))
                        max_day = max(days_x)
                        norm_x = list(map(lambda d: d / max_day, days_x))
                    except Exception:
                        norm_x = [0] * len(markets)
                else:
                    try:
                        max_x = max(map(lambda z: float(z), x))
                        norm_x = list(map(lambda v: float(v) / max_x, x))
                    except Exception:
                        norm_x = [0] * len(markets)
            else:
                solv_expr = words_name_coef[1]
                for word in set(words_name_coef[1].split()):
                    val = markets[0][words_name_coef[0]].get(word, None)
                    if val == '':
                        val = '0'
                        solv_expr = solv_expr.replace(word, val)
                    elif val:
                        solv_expr = solv_expr.replace(word, f"float(m['{words_name_coef[0]}']['{word}'])")
                try:
                    x = list(map(lambda m: eval(solv_expr), markets))
                    max_x = max(x)
                    norm_x = list(map(lambda v: v / max_x, x))
                except Exception:
                    norm_x = [0] * len(markets)
            val_for_coefs.append(norm_x)
        return val_for_coefs

    # Нормализация данных
    def new_ranking(self, markets: list[dict], coefs=supplier_sorting_params):
        copy_markets = deepcopy(markets)
        copy_markets.append(ideal_supplier_parameters)

        clear_markets = self.clearing(copy_markets, coefs)
        val_for_coefs = self.normalize(clear_markets, coefs)

        raiting = [0] * len(markets)
        for val, k in zip(val_for_coefs, coefs.values()):
            i_ratings = list(map(lambda x: x * k, val))
            raiting = list(map(lambda a, b: a + b, raiting, i_ratings))
        for i, market in enumerate(markets):
            market['Рейтинг'] = "{0:.2f}".format(raiting[i])
        return markets

    @property
    def supplier_data(self):
        return self.__supplier_data

    # Парсинг юридической информации по поставщику из бд СБИС
    def parse_supplier_data(self):
        logger.INFO('Start parsing supplier info', self.website)
        self.__supplier_data = {}
        general_url = 'https://sbis.ru/contragents/'
        url = general_url + self.inn
        # self.get(url, time=2)
        self.get(url, selen=True)
        # Проверка действующая ли компания или нет
        liquidated = self.get_text(self.html.find('div', class_='c-sbisru-CardStatus__closed'), log=False)
        if liquidated:
            logger.FAIL('Supplier liquidated!')
            return False
        else:
            # self.__supplier_data['Статус'] = 'Действующее'      # Включаем только действующие
            self.__supplier_data['Рейтинг'] = ''
            self.__supplier_data['Сайт'] = self.website
            # Парсинг
            try:
                self.__supplier_data['Название'] = self.get_text(
                    self.html.find('div', class_='cCard__MainReq-Name'), log=False
                )
            except Exception:
                self.__supplier_data['Название'] = ''
            try:
                self.__supplier_data['Название полное'] = self.get_text(
                    self.html.find('div', class_='cCard__MainReq-FullName'), log=False
                )
            except Exception:
                self.__supplier_data['Название полное'] = ''
            try:
                self.__supplier_data['Адрес'] = self.get_text(
                    self.html.find('div', class_='cCard__Contacts-Address'), log=False
                ).strip()
            except Exception:
                self.__supplier_data['Адрес'] = ''
            # Контакты
            self.__supplier_data['Контакты'] = {}
            try:
                self.__supplier_data['Контакты']['Телефон'] = self.get_text(
                    self.html.find('div', itemprop='telephone'), log=False
                ).strip()
            except Exception:
                self.__supplier_data['Контакты']['Телефон'] = ''
            try:
                self.__supplier_data['Контакты']['email'] = self.get_text(
                    self.html.find('a', itemprop='email'), log=False
                ).strip()
            except Exception:
                self.__supplier_data['Контакты']['email'] = ''
            # Дата регистрации
            inf = self.get_text(self.html.find('div', class_='cCard__CompanyDescription'), log=False)
            try:
                self.__supplier_data['Дата регистрации'] = re.search(r'Действует с \d\d.\d\d.\d\d\d\d', inf).group()[12:]
            except Exception:
                self.__supplier_data['Дата регистрации'] = ''
            self.__supplier_data['ИНН'] = self.inn
            try:
                self.__supplier_data['КПП'] = re.search(r'КПП \d+', inf, flags=re.I).group()[4:]
            except Exception:
                self.__supplier_data['КПП'] = ''
            try:
                self.__supplier_data['ОГРН'] = re.search(r'ОГРН \d+', inf, flags=re.I).group()[5:]
            except Exception:
                self.__supplier_data['ОГРН'] = ''
            try:
                self.__supplier_data['ОКПО'] = re.search(r'ОКПО \d+', inf, flags=re.I).group()[5:]
            except Exception:
                self.__supplier_data['ОКПО'] = ''
            #
            try:
                self.__supplier_data['Руководитель'] = self.get_text(
                    self.html.find('div', class_='cCard__Director-Name').find('span'), log=False
                ).strip()
            except Exception:
                self.__supplier_data['Руководитель'] = ''
            try:
                self.__supplier_data['Выручка'] = self.get_text(
                    self.html.find(
                        'div', class_='cCard__Contacts'
                    ).find(
                        'div', class_='cCard__Contacts-Revenue-Desktop cCard__Main-Grid-Element'
                    ).find('span', class_='cCard__BlockMaskSum'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Выручка'] = ''
            try:
                self.__supplier_data['Прибыль'] = self.get_text(
                    self.html.find(
                        'div', class_='cCard__Owners-Profit-Desktop cCard__Main-Grid-Element'
                    ).find('span', class_='cCard__BlockMaskSum'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Прибыль'] = ''
            # Суды истец
            self.__supplier_data['Истец'] = {}
            try:
                self.__supplier_data['Истец']['Выиграл'] = self.get_text(
                    self.html.find('div', class_='cCard__Owners-CourtStat-Complain').find(
                        'div', class_='cCard__Owners-CourtStat-Stat-Win'
                    ).find('div', class_='cCard__Owners-CourtStat-Stat-Value'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Истец']['Выиграл'] = ''
            try:
                self.__supplier_data['Истец']['Проиграл'] = self.get_text(
                    self.html.find('div', class_='cCard__Owners-CourtStat-Complain').find(
                        'div', class_='cCard__Owners-CourtStat-Stat-Loose'
                    ).find('div', class_='cCard__Owners-CourtStat-Stat-Value'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Истец']['Проиграл'] = ''
            try:
                self.__supplier_data['Истец']['Прочие'] = self.get_text(
                    self.html.find('div', class_='cCard__Owners-CourtStat-Complain').find(
                        'div', class_='cCard__Owners-CourtStat-Stat-Other'
                    ).find('div', class_='cCard__Owners-CourtStat-Stat-Value'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Истец']['Прочие'] = ''
            # Суды ответчик
            self.__supplier_data['Ответчик'] = {}
            try:
                self.__supplier_data['Ответчик']['Выиграл'] = self.get_text(
                    self.html.find('div', class_='cCard__Owners-CourtStat-Defend').find(
                        'div', class_='cCard__Owners-CourtStat-Stat-Win'
                    ).find('div', class_='cCard__Owners-CourtStat-Stat-Value'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Ответчик']['Выиграл'] = ''
            try:
                self.__supplier_data['Ответчик']['Проиграл'] = self.get_text(
                    self.html.find('div', class_='cCard__Owners-CourtStat-Defend').find(
                        'div', class_='cCard__Owners-CourtStat-Stat-Loose'
                    ).find('div', class_='cCard__Owners-CourtStat-Stat-Value'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Ответчик']['Проиграл'] = ''
            try:
                self.__supplier_data['Ответчик']['Прочие'] = self.get_text(
                    self.html.find('div', class_='cCard__Owners-CourtStat-Defend').find(
                        'div', class_='cCard__Owners-CourtStat-Stat-Other'
                    ).find('div', class_='cCard__Owners-CourtStat-Stat-Value'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Ответчик']['Прочие'] = ''
            #
            try:
                self.__supplier_data['Уставный капитал'] = self.get_text(
                    self.html.find(
                        'div', class_='cCard__Owners-OwnerList-Authorized-Capital-Sum cCard__Owners-OwnerList-Bold'
                    ),
                    log=False
                )
            except Exception:
                self.__supplier_data['Уставный капитал'] = ''
            try:
                self.__supplier_data['Стоимость'] = self.get_text(
                    self.html.find(
                        'div', class_='cCard__Reliability-Cost-Desktop cCard__Main-Grid-Element'
                    ).find('span', class_='cCard__BlockMaskSum'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Стоимость'] = ''
            # Тендеры
            self.__supplier_data['Тендер'] = {}
            try:
                self.__supplier_data['Тендер']['Участник'] = self.get_text(
                    self.html.find(
                        'div', class_='cCard__Reliability-Tender-data'
                    ).find('div', class_='cCard__Reliability-Tender-Block-C2'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Тендер']['Участник'] = ''
            try:
                self.__supplier_data['Тендер']['Выиграл'] = self.get_text(
                    self.html.find(
                        'div', class_='cCard__Reliability-Tender-data'
                    ).find('div', class_='ws-flexbox ws-justify-content-between').next_sibling.find(
                        'div', class_='cCard__Reliability-Tender-Block-C2'
                    ),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Тендер']['Выиграл'] = ''
            # Госконтракты
            try:
                self.__supplier_data['Госконтракты'] = self.get_text(
                    self.html.find(
                        'div', class_='cCard__Reliability-Gov-Contract-data'
                    ).find('div', class_='cCard__Reliability-Tender-Block-C2'),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Госконтракты'] = ''
            self.__supplier_data['Надежность'] = {}
            try:
                self.__supplier_data['Надежность']['Плюсы'] = self.get_text(
                    self.html.find(
                        'div', class_='analytics-ReliabilitySbisRu__subHeaderGreen analytics-ReliabilitySbisRu__right'
                    ),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Надежность']['Плюсы'] = ''
            try:
                self.__supplier_data['Надежность']['Минусы'] = self.get_text(
                    self.html.find(
                        'div', class_='analytics-ReliabilitySbisRu__subHeaderRed analytics-ReliabilitySbisRu__right'
                    ),
                    log=False
                ).strip()
            except Exception:
                self.__supplier_data['Надежность']['Минусы'] = ''
            # TODO отзывы
        return True
