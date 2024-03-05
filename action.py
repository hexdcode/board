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

import smtplib
from email.mime.text import MIMEText
from email.header import Header

def send_email(sender_email, smtp_password, receiver_email, subject, body):
    # 设置SMTP服务器和端口号
    smtp_server = 'smtp.qq.com'
    smtp_port = 465
    
    # 创建一个MIMEText对象，定义邮件正文和字符编码
    message = MIMEText(body, 'plain', 'utf-8')
    
    # 设置邮件的头部信息
    message['From'] = Header(sender_email)
    message['To'] = Header(receiver_email)
    message['Subject'] = Header(subject, 'utf-8')
    
    try:
        # 连接到SMTP服务器
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        # 登录SMTP服务器
        server.login(sender_email, smtp_password)
        
        # 发送邮件
        server.sendmail(sender_email, [receiver_email], message.as_string())
        
        # 关闭连接
        server.quit()
        
        print("邮件发送成功")
    except smtplib.SMTPException as e:
        print("邮件发送失败", e)

email_address, email_password, email_target = sys.argv[1], sys.argv[2], sys.argv[3]
print(email_target)

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
  ]
}

# target timezone
tz_target = pytz.timezone('Etc/GMT-2')

# 判断是否符合configs中的条件
def is_match(symbol, caption, impact):
    """
    symbol: str, 交易品种, configs中的key
    caption: str, 经济数据标题
    impact: int, 经济数据重要性
    """
    # print(caption, impact)
    for config in configs[symbol]:
        if config[0] <= impact and all(kw in caption for kw in config[1:]):
            return True
    return False

alert_times = []

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

def add_alert(input_date, input_time, data):
    # 尝试解析输入的日期和时间，检查其合法性
    try:
        dt = datetime.strptime(f"{input_date} {input_time}", "%Y%m%d %H:%M")
    except ValueError:
        # 如果输入的日期或时间不合法，设置为00:00
        dt = datetime.strptime(input_date, "%Y%m%d")

    # 减去12小时，得到t1
    t1 = dt - timedelta(hours=12)
    # 加上12小时，得到t2
    t2 = dt + timedelta(hours=12)

    # 创建北京时区和目标时区(GMT+2)的对象
    tz_beijing = pytz.timezone('Asia/Shanghai')
    tz_target = pytz.timezone('Etc/GMT-2')

    # 将t1和t2转换为带有时区的时间
    t1_aware = tz_beijing.localize(t1)
    t2_aware = tz_beijing.localize(t2)

    # 将t1和t2转换为GMT+02:00的时间
    t1_target = t1_aware.astimezone(tz_target)
    t2_target = t2_aware.astimezone(tz_target)

    # 获取t1和t2覆盖的日期
    # alert_dates.add(t1_target.strftime("%Y%m%d"))
    # alert_dates.add(t2_target.strftime("%Y%m%d"))
    # dates_covered = set()
    # dates_covered.add(t1_target.strftime("%Y%m%d"))
    # dates_covered.add(t2_target.strftime("%Y%m%d"))

    # 如果t1和t2跨越了多天，添加中间的所有日期
    current_date = t1_target.date()
    end_date = t2_target.date()
    while current_date < end_date:
        alert_dates.add(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
        # dates_covered.add(current_date.strftime("%Y%m%d"))
    print(input_date, input_time, data)
    
# 将给定时间（北京）转换为UTC时间，使用pd.Timestamp对象
def beijing_to_utc(date, time):
    if isinstance(date, datetime):
        date = date.strftime('%Y%m%d')
    # 创建北京时区对象
    tz_beijing = pytz.timezone('Asia/Shanghai')
    # 创建UTC时区对象
    tz_utc = pytz.timezone('UTC')
    # 将输入时间字符串转换为datetime对象
    dt = datetime.strptime(f"{date} {time}", "%Y%m%d %H:%M")
    # 将datetime对象转换为带有时区的datetime对象
    dt_aware = tz_beijing.localize(dt)
    # 将带有时区的datetime对象转换为UTC时间
    dt_utc = dt_aware.astimezone(tz_utc)
    # 返回UTC时间的时间字符串
    return dt_utc

def next_begin_sessions(t1):
    # 定义纽约和伦敦的交易市场
    nyse_calendar = mcal.get_calendar('NYSE')
    lse_calendar = mcal.get_calendar('LSE')  # 伦敦证券交易所

    # 将输入的时间转换为pandas的时间戳
    t1 = pd.Timestamp(t1)
    
    # 获取给定时间之后的纽约和伦敦的下一个完整交易日
    nyse_schedule = nyse_calendar.schedule(start_date=t1 - pd.DateOffset(days=7), end_date=t1)
    lse_schedule = lse_calendar.schedule(start_date=t1 - pd.DateOffset(days=7), end_date=t1)
    
    # 获取自t1开始后第一个完整的NewYork交易时段的结束时间
    nyse_end = nyse_schedule.loc[nyse_schedule['market_close'] <= t1]['market_open'].iloc[-1]
    # 获取自t1开始后第一个完整的London交易时段的结束时间
    lse_end = lse_schedule.loc[lse_schedule['market_close'] <= t1]['market_open'].iloc[-1]
    
    return min(nyse_end, lse_end).to_pydatetime()

# UTC转换为GMT+2
def utc_to_target(t):
    # 创建目标时区对象
    tz_target = pytz.timezone('Etc/GMT-2')
    t_target = t.astimezone(tz_target)
    return t_target

# now
now = datetime.now()
# now = datetime.strptime('20240316', '%Y%m%d')

# 未来3天的日历URL
dates = [now + timedelta(days=i) for i in range(7)]
urls = [f"https://rili.jin10.com/day/{(now + timedelta(days=i)).strftime('%Y-%m-%d')}" for i in range(7)]

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver = webdriver.Chrome(options=options)

for date in dates:
    url = f"https://rili.jin10.com/day/{date.strftime('%Y-%m-%d')}"
    driver.get(url)
    html_string = driver.page_source
    doc = html.fromstring(html_string)

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
        if time is not None:
            economic_data[-1].append(time.strip())
        else:
            if len(economic_data) > 1:
                economic_data[-1].append(economic_data[-2][0])

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
        if time is not None:
            economic_events[-1].append(time.strip())
        else:
            if len(economic_events) > 1:
                economic_events[-1].append(economic_events[-2][0])

        # 国家
        country = get_text(td_elements[1])
        economic_events[-1].append(country.strip())

        # 重要性
        importance = td_elements[2].xpath('.//i[not(starts-with(@style, "color: rgb(221, 221, 221)"))]')
        economic_events[-1].append(len(importance))

        # 事件
        event = get_text(td_elements[3])
        economic_events[-1].append(event.strip())
    
    for data in economic_data:
        for symbol in configs:
            if is_match(symbol, data[1], data[2]):
                print(date, data[0], data[1])
                # 将该数据的时间的前1小时和后3小时添加到alert_times
                alert_times.append(
                    (
                        # beijing_to_utc(date, data[0]) - timedelta(hours=1), 
                        next_begin_sessions(beijing_to_utc(date, data[0])),
                        beijing_to_utc(date, data[0]) + timedelta(hours=3)
                    )
                )
                break


output_fmt = '%Y.%m.%d %H:%M'
with open('CADCHF', 'r')  as f:
    output = f.readlines()
output = [line.strip() for line in output if line.strip() != '']
with open('extra.txt', 'r') as f:
    output = output + [line.strip() for line in f.readlines() if line.strip() != '']
print(output)
output = [(output[i], output[i + 1]) for i in range(0, len(output), 2) if output[i + 1] > datetime.now(tz_target).strftime(output_fmt)]
for t1, t2 in alert_times:
    output.append((utc_to_target(t1).strftime('%Y.%m.%d %H:%M'), utc_to_target(t2).strftime('%Y.%m.%d %H:%M')))
output = list(set(output))
output.sort()
output = [t for ts in output for t in ts]

with open('CADCHF', 'w') as f:
    f.write('\n'.join(output))


print(alert_times)
