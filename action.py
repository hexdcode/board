# vim test.py
from datetime import datetime, timedelta
from lxml import html
import pytz
import pandas as pd
import pandas_market_calendars as mcal
import sys
from crawl import crawl
from alarm import Alarm

email_address, email_password, email_target = sys.argv[1], sys.argv[2], sys.argv[3]

# 暂时只做CADCHF
# 每个value都是[item1, item2, ...]
# 每个item的形式为[impact_threshold, keyword1, keyword2, ...]
# 重要性大于等于impact_threshold且包含所有keyword的事件会记录
configs = {
  'CADCHF': [
    [3, '加拿大'], # 重要性大于等于3的加拿大经济数据
    [3, '瑞士'],  # 
    [5, '美国'], # 重要性大于等于5的美国失业率数据
    [0, '加拿大', 'GDP'], # 任何包含"加拿大"和"GDP"的经济数据
  ],
}

# 待爬取的日期
now = datetime.now()
dates = [now + timedelta(days=i) for i in range(7)]
alarm = Alarm()
for date in dates:
    economic_data, economic_events = crawl(date)
    for data in economic_data:
        alarm.add_alarm(data[1], data[2], data[0])
alarm.save()