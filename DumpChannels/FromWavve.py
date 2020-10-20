import json
import requests
from datetime import datetime, timedelta, date

def DumpChannelsFromWavve():
  """
  Wavve에서 제공하는 EPG의 채널 목록을 파싱합니다. 
  오늘 날짜로 제공되는 EPG만 해당됩니다. \n
  @return [
    {
      'last update': 'yyyy/mm/dd hh/mm/ss',
      'total': '채널갯수'
    },
    {
      'WAVVE Name': '채널이름',
      'Icon_url': 'https://ddns/path/to/icon',
      'Source': 'WAVVE',
      'ServiceId': '서비스ID'
    }
  ] \n
  @request_count: 1
  """

  URL = 'https://apis.wavve.com/live/epgs'
  UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0'
  params = {
    'limit': 200,
    'apikey': 'E5F3E0D30947AA5440556471321BB6D9',
    'genre': 'all',
    'startdatetime': date.today().strftime('%Y-%m-%d') + ' 00:00',
    'enddatetime': date.today().strftime('%Y-%m-%d') + ' 24:00'
  }

  try:
    req = requests.get(URL, params=params, headers={'User-Agent': UA})
    print('Status Code: ', req.status_code)
  except Exception as e:
    print('요청 중 에러: %s' % str(e))

  channels = json.loads(req.text)
  result = []

  for channel in channels['list']:
    ch_name = channel['channelname']
    ch_id = channel['channelid']
    ch_icon = 'https://' + channel['channelimage']
    result.append({
      'WAVVE Name': ch_name,
      'Icon_url': ch_icon,
      'Source': 'WAVVE',
      'ServiceId': ch_id
    })
  
  headers = [{'last update': datetime.now().strftime('%Y/%m/%d %H:%M:%S'), 'total': len(result)}]

  return headers + result