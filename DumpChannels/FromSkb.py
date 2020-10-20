import json
import requests
from datetime import datetime

def DumpChannelsFromSkb():
  """
  SKB에서 제공하는 EPG의 채널 목록을 파싱합니다. \n
  @return [
    {
      'last update': 'yyyy/mm/dd hh/mm/ss',
      'total': '채널갯수'
    },
    {
      'SKB Name': '채널이름', 
      'SKBCh': 채널번호,
      'Source': 'SKB',
      'ServiceId': '서비스ID'
    }
  ] \n
  @request_count: 1
  """

  print('Skb에서 정보를 가져오고 있습니다 . . .')

  URL = "https://m.skbroadband.com/content/realtime/Realtime_List_Ajax.do"
  UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0'
  try:
    req = requests.get(URL, headers={'User-Agent': UA})
    print('Status Code: ', req.status_code)
  except Exception as e:
    print('요청 중 에러: %s' % str(e))

  channels = json.loads(req.text)
  result = []

  for channel in channels:
    if channel['depth'] == '1':
      continue
    ch_name = channel['m_name']
    ch_no = channel['ch_no']
    ch_id = channel['c_menu']
    result.append({
      'SKB Name': ch_name,
      'SKBCh': int(ch_no),
      'Source': 'SKB',
      'ServiceId': ch_id
    })
  
  headers = [{'last update': datetime.now().strftime('%Y/%m/%d %H:%M:%S'), 'total': len(result)}]

  return headers + result