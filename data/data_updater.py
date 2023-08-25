import json
from datetime import datetime
from pandas.tseries.offsets import BDay
from dateutil.relativedelta import relativedelta

f = open('master_schedule.json')
data = json.load(f)

g = open('schedule2.json' ,'w')

dict = {}

for key in data[0]:
    date = datetime.strptime(key, '%Y-%m-%d')
    
    date = date + relativedelta(years=1)
    date = date -  BDay(1)


    dict[date.strftime('%Y-%m-%d')] = data[0][key]

g.write(json.dumps(dict))
