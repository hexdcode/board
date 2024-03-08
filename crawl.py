# vim test.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
from lxml import html
import pytz
import pandas as pd
import pandas_market_calendars as mcal
import sys
import os


def get_deepest_element(element):
    """
    获取给定元素的最底层子元素。
    假设每个元素最多只有一个子元素。
    
    :param element: lxml element
    :return: 最底层的子元素
    """
    # 持续遍历直到当前元素没有子元素
    while len(element):
        element = element[0]  # 获取当前元素的第一个（也是唯一的）子元素
    return element

def get_text(element):
    """
    获取给定元素的文本内容。
    如果给定元素没有文本内容，返回空字符串。
    
    :param element: lxml element
    :return: 文本内容
    """
    text = element.xpath('.//text()')
    text = [t.strip() for t in text if t.strip() != '']
    return text[0] if text else ''

os.environ['TZ'] = 'Asia/Shanghai' # 设置时区，网站内容和时区有关
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--timezone=Asia/Shanghai')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver = webdriver.Chrome(options=options)

def crawl(date):
    url = f"https://rili.jin10.com/day/{date.strftime('%Y-%m-%d')}"
    driver.get(url)
    html_string = driver.page_source
    doc = html.fromstring(html_string)

    def get_datetime(t):
        if isinstance(t, datetime):
            return t
        t = t.strip()
        tz = pytz.timezone('Asia/Shanghai')
        d = date.strftime('%Y-%m-%d')
        dt = f"{d} {t}"
        try:
            ret = tz.localize(datetime.strptime(dt, '%Y-%m-%d %H:%M'))
        except ValueError:
            dt = f"{d} 12:00"
            ret = tz.localize(datetime.strptime(dt, '%Y-%m-%d %H:%M'))
        return ret

    # 获取经济数据
    tr_elements = doc.xpath('//*[@class="jin-table calendar-data-table"]/div[2]/table/tbody/tr')
    economic_data = []
    for tr in tr_elements:
        td_elements = tr.xpath('./td')
        if len(td_elements) == 1:
            continue

        economic_data.append([])

        # 时间
        time = td_elements[0].xpath('.//span')[0].text
        if time is None or time == '':
            assert len(economic_data) > 1
            time = economic_data[-2][0]
        economic_data[-1].append(get_datetime(time))

        # 数据
        data = td_elements[1].xpath('.//span')[1].text
        if data is not None:
            economic_data[-1].append(data.strip())
        else:
            economic_data[-1].append('')

        # 重要性
        importance = td_elements[2].xpath('.//i[not(starts-with(@style, "color: rgb(221, 221, 221)"))]')
        economic_data[-1].append(len(importance))

        # 前值
        previous = get_text(td_elements[3])
        economic_data[-1].append(previous.strip())

        # 预测值
        forecast = get_text(td_elements[4])
        economic_data[-1].append(forecast.strip())

        # 公布值
        actual = td_elements[5].xpath('.//span')[0].text
        economic_data[-1].append(actual.strip())

        # 影响
        impact = td_elements[6].xpath('./div/div')[0].text
        economic_data[-1].append(impact.strip())

    # 获取经济事件
    economic_events = []
    tr_elements = doc.xpath('//*[@class="jin-table calendar-event-table"]/div[2]/table/tbody/tr')
    for tr in tr_elements:
        td_elements = tr.xpath('./td')
        if len(td_elements) < 4:
            continue

        economic_events.append([])

        # 时间
        time = td_elements[0].xpath('.//span')[0].text
        if time is None or time.strip() == '':
            assert len(economic_events) > 1
            time = economic_events[-2][0]
        economic_events[-1].append(get_datetime(time))
        
        # 国家
        country = get_text(td_elements[1])
        economic_events[-1].append(country.strip())

        # 重要性
        importance = td_elements[2].xpath('.//i[not(starts-with(@style, "color: rgb(221, 221, 221)"))]')
        economic_events[-1].append(len(importance))

        # 事件
        event = get_text(td_elements[3])
        economic_events[-1].append(event.strip())

    return economic_data, economic_events