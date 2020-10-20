import json
import requests
from datetime import datetime, date, timedelta

def DumpChannelsFromTving():
  """
  Tving에서 제공하는 EPG의 채널 목록을 파싱합니다. 
  현재부터 3시간 지난 시점까지 EPG가 존재하는 채널만 해당됩니다. \n
  @return [
    {
      'last update': 'yyyy/mm/dd hh/mm/ss',
      'total': '채널갯수'
    },
    {
      'TVING Name': '채널이름', 
      'Icon_url': 'https://ddns/path/to/icon',
      'Source': 'TVING',
      'ServiceId': '서비스ID'
    }
  ] \n
  @request_count: #[number of channels]//20
  """

  URL = "https://api.tving.com/v2/media/schedules"
  UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0'
  params = {
    # 'pageNo': 1 2 3 ...
    'pageSize': '20',
    'order': 'chno',
    'scope': 'all',
    'adult': 'all', # 'all', 'adult', 'y'
    'free': 'all',
    'broadDate': date.today().strftime('%Y%m%d'),
    'broadcastDate': date.today().strftime('%Y%m%d'),
    'startBroadTime': datetime.now().strftime('%H') + "0000",
    'endBroadTime': (datetime.now() + timedelta(hours=3)).strftime('%H') + "0000",
    "screenCode": "CSSD0100", # ??
    "networkCode": "CSND0900", # ??
    "osCode": "CSOD0900", # ??
    "teleCode": "CSCD0900", # ??
    'apiKey': "1e7952d0917d6aab1f0293a063697610"
  }
  pageNumber = 1
  
  channels = []
  while True:
    params['pageNo'] = str(pageNumber)
    try:
      req = requests.get(URL, params=params, headers={'User-Agent': UA})
      print('pageNo: ', pageNumber, ', Status Code: ', req.status_code)
    except Exception as e:
      print('요청 중 에러: %s' % str(e))
    
    res = json.loads(req.text)
    if res['header']['status'] != 200:
      print('요청 값 에러')
      raise requests.exceptions.RequestException
    else:
      channels.extend(res['body']['result'])

    if res['body']['has_more'] == 'Y':
      pageNumber += 1
    else:
      break
  
  result = []
  for channel in channels:
    # EPG가 없는 채널은 넘김
    if channel['schedules'] is None:
      continue

    ch_img = ""
    while True:
      image = channel['image'].pop()
      if image['url'].split('/')[-1].split('.')[0] == channel['channel_code']:
        ch_img = "https://image.tving.com" + image['url']
        break

    result.append({
      'TVING Name': channel['channel_name']['ko'],
      'Icon_url': ch_img,
      'Source': 'TVING',
      'ServiceId': channel['channel_code']
    })
  
  headers = [{'last update': datetime.now().strftime('%Y/%m/%d %H:%M:%S'), 'total': len(result)}]

  return headers + result