import json
import requests
from bs4 import BeautifulSoup
import re

def DumpChannelsFromLg():
  """
  LGU에서 제공하는 EPG의 채널 목록을 파싱합니다. \n
  @return [ 
    {
      'LG Name': '채널이름',
      'LGCh': 채널번호,
      'Source': 'LG',
      'ServiceId': '서비스ID'
    }
  ] \n
  @request_count: 9
  """

  print('LGU에서 정보를 가져오고 있습니다 . . .')

  URL = 'https://www.uplus.co.kr/css/chgi/chgi/RetrieveTvChannel.hpi'
  UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0'
  params = {'code': '12810'}

  category = [
    {'name': '지상파', 'category': '00'},
    {'name': '스포츠/취미', 'category': '01'},
    {'name': '영화', 'category': '02'},
    {'name': '뉴스/경제', 'category': '03'},
    {'name': '교양/다큐', 'category': '04'},
    {'name': '여성/오락', 'category': '05'},
    {'name': '어린이/교육', 'category': '06'},
    {'name': '홈쇼핑', 'category': '07'},
    {'name': '공공/종교', 'category': '08'}
  ]

  p_name = re.compile(r'.+(?=[(])')
  p_ch = re.compile(r'(?<=Ch[.])\d+')
  p_id = re.compile(r"(?<=[('])\d+(?=[',])")

  result = []
  for cat in category:
    try:
      params['category'] = cat['category']
      req = requests.get(URL, params=params, headers={'User-Agent': UA})
      print('Status Code: ', req.status_code)
    except Exception as e:
      print('요청 중 에러: %s' % str(e))
    
    html = BeautifulSoup(req.text, 'html.parser')

    channels = html.find_all(attrs={'name': 'chList'})
    for channel in channels:
      print('현재 처리중인 채널:', channel.string)
      result.append({
        'LG Name': p_name.search(channel.string).group(),
        'LGCh': int(p_ch.search(channel.string).group()),
        'Source': 'LG',
        'ServiceId': p_id.search(channel['onclick']).group()
      })
    
  return result