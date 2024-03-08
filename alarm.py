import pytz
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
import pandas as pd

class Alarm:
    def __init__(self):
        self.configs = {
            'CADCHF': [
                [3, '加拿大'],
                [3, '瑞士'],
                [5, '美国'],
                [0, '加拿大', 'GDP'],
            ],
        }
        self.tz_target = pytz.timezone('Etc/GMT-2')
        self.time_spans = {symbol: [] for symbol in self.configs.keys()}
        # 时间格式
        self.datetime_format = '%Y.%m.%d %H:%M'
        def get_datetime(s):
            return self.tz_target.localize(datetime.strptime(s, self.datetime_format))
        with open('extra', 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip() != '']
            extra = [(get_datetime(lines[i]), get_datetime(lines[i + 1])) for i in range(0, len(lines), 2)]
        for symbol in self.configs.keys():
            with open(symbol, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip() != '']
            self.time_spans[symbol] = [
                (get_datetime(lines[i]), get_datetime(lines[i + 1])) for i in range(0, len(lines), 2)
            ]
            self.time_spans[symbol].extend(extra)

    def is_match(self, symbol, caption, impact):
        for config in self.configs[symbol]:
            if config[0] <= impact and all(kw in caption for kw in config[1:]):
                return True
        return False
    
    def get_time_span(self, t):
        nyse_calendar = mcal.get_calendar('NYSE')
        lse_calendar = mcal.get_calendar('LSE')  # 伦敦证券交易所

        # 将输入的时间转换为pandas的时间戳
        t1 = pd.Timestamp(t)
        
        # 获取给定时间之后的纽约和伦敦的下一个完整交易日
        nyse_schedule = nyse_calendar.schedule(start_date=t1 - pd.DateOffset(days=7), end_date=t1)
        lse_schedule = lse_calendar.schedule(start_date=t1 - pd.DateOffset(days=7), end_date=t1)
        
        # 获取自t1开始后第一个完整的NewYork交易时段的结束时间
        nyse_end = nyse_schedule.loc[nyse_schedule['market_close'] <= t1]['market_open'].iloc[-1]
        # 获取自t1开始后第一个完整的London交易时段的结束时间
        lse_end = lse_schedule.loc[lse_schedule['market_close'] <= t1]['market_open'].iloc[-1]
        
        return (min(nyse_end, lse_end).to_pydatetime(), t + timedelta(hours=3))

    def add_alarm(self, caption, impact, t):
        for symbol in self.configs.keys():
            if self.is_match(symbol, caption, impact):
                print(t, caption, impact, symbol)
                self.time_spans[symbol].append(self.get_time_span(t))

    def save(self):
        for symbol in self.configs.keys():
            time_spans = list(set(self.time_spans[symbol]))
            for ts in time_spans:
                print(ts)
            time_spans.sort()
            with open(symbol, 'w') as f:
                f.write('\n'.join([t.astimezone(self.tz_target).strftime(self.datetime_format) for ts in time_spans for t in ts]))
    

