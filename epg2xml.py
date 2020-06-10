#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import json
import socket
import logging
import argparse
from functools import partial
from urllib.parse import unquote
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, date
from xml.sax.saxutils import escape, unescape

#
# default variables
#
__version__ = '1.3.0'
today = date.today()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
req_timeout = 15
req_sleep = 1

# importtant files
__dirpath__ = os.path.dirname(os.path.realpath(sys.argv[0]))
logfile = os.path.join(__dirpath__, 'epg2xml.py.log')
configfile = os.path.join(__dirpath__, 'epg2xml.json')
channelfile = os.path.join(__dirpath__, 'Channel.json')

# parse command-line arguments
parser = argparse.ArgumentParser(description='EPG 정보를 XML로 만드는 프로그램')
parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
parser.add_argument('--config', dest='configfile', default=configfile, help='설정 파일 경로 (기본값: %s)' % configfile)
parser.add_argument('--logfile', default=logfile, help='로그 파일 경로 (기본값: %s)' % logfile)
parser.add_argument('--loglevel', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='로그 레벨 (기본값: INFO)')
parser.add_argument('--channelfile', default=channelfile, help='채널 파일 경로 (기본값: %s)' % channelfile)
parser.add_argument('-i', '--isp', dest='MyISP', choices=['ALL', 'KT', 'LG', 'SK'], help='사용하는 ISP 선택')
parser.add_argument('-c', '--channelid', dest='MyChannels', metavar='CHANNELID', help='채널 ID를 ,와 -, *를 적절히 조합하여 지정 (예: -3,5,7-9,11-)')
arg1 = parser.add_mutually_exclusive_group()
arg1.add_argument('-d', '--display', dest='output', action='store_const', const='d', help='생성된 EPG를 화면에 출력')
arg1.add_argument('-o', '--outfile', dest='default_xml_file', metavar='XMLTVFILE', nargs='?', const='xmltv.xml', help='생성된 EPG를 파일로 저장 (기본경로: %s)' % 'xmltv.xml')
arg1.add_argument('-s', '--socket', dest='default_xml_socket', metavar='XMLTVSOCK', nargs='?', const='xmltv.sock', help='생성된 EPG를 소켓으로 전송 (기본경로: %s)' % 'xmltv.sock')
args = vars(parser.parse_args())
if args['default_xml_file']:
    args['output'] = 'o'
elif args['default_xml_socket']:
    args['output'] = 's'

#
# logging
#
log = logging.getLogger(__name__)

log_fmt = "%(asctime)-15s %(levelname)-8s %(lineno)03d %(message)s"
formatter = logging.Formatter(log_fmt, datefmt='%Y/%m/%d %H:%M:%S')

# logging to file
filehandler = RotatingFileHandler(args['logfile'], maxBytes=1024 * 1000, backupCount=5, encoding='utf-8')
filehandler.setFormatter(formatter)
log.addHandler(filehandler)

# logging to console, stderr by default
consolehandler = logging.StreamHandler()
consolehandler.setFormatter(formatter)
log.addHandler(consolehandler)

log.setLevel(getattr(logging, args['loglevel']))

#
# import third-parties
#
try:
    from bs4 import BeautifulSoup, SoupStrainer
except ImportError:
    log.error("BeautifulSoup 모듈이 설치되지 않았습니다.")
    sys.exit(1)
try:
    import lxml
    htmlparser = 'lxml'
except ImportError:
    log.warning("lxml 모듈이 설치되지 않아 html.parser로 동작합니다. 속도가 느립니다.")
    htmlparser = 'html.parser'
try:
    import requests
except ImportError:
    log.error("requests 모듈이 설치되지 않았습니다.")
    sys.exit(1)

if list(sys.version_info[:2]) < [3, 5]:
    log.error("python 3.5+에서 실행하세요.")
    sys.exit(1)


# Get epg data
def getEpg():
    # XML 헤더 시작
    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
    print('<tv generator-info-name="epg2xml ' + __version__ + '">')

    ChannelInfos = []
    for Channeldata in Channeldatajson:     # Get Channel & Print Channel info
        if (Channeldata['Source'] in ['KT', 'LG', 'SK', 'SKB', 'NAVER']) and (str(Channeldata['Id']) in MyChannels):
            ChannelId = Channeldata['Id']
            ChannelName = escape(Channeldata['Name'])
            ChannelSource = Channeldata['Source']
            ChannelServiceId = Channeldata['ServiceId']
            ChannelIconUrl = escape(Channeldata['Icon_url'])
            ChannelInfos.append([ChannelId, ChannelName, ChannelSource, ChannelServiceId])
            print('  <channel id="%s">' % ChannelId)
            if MyISP != "ALL" and Channeldata[MyISP+'Ch'] is not None:
                ChannelNumber = str(Channeldata[MyISP+'Ch'])
                ChannelISPName = escape(Channeldata[MyISP+' Name'])
                print('    <display-name>%s</display-name>' % ChannelName)
                print('    <display-name>%s</display-name>' % ChannelISPName)
                print('    <display-name>%s</display-name>' % ChannelNumber)
                print('    <display-name>%s</display-name>' % (ChannelNumber+' '+ChannelISPName))
            elif MyISP == "ALL":
                print('    <display-name>%s</display-name>' % ChannelName)
            if IconUrl:
                print('    <icon src="%s/%s.png" />' % (IconUrl, ChannelId))
            else:
                print('    <icon src="%s" />' % ChannelIconUrl)
            print('  </channel>')

    # Print Program Information
    GetEPGFromKT([info for info in ChannelInfos if info[2] == 'KT'])
    GetEPGFromLG([info for info in ChannelInfos if info[2] == 'LG'])
    GetEPGFromSK([info for info in ChannelInfos if info[2] == 'SK'])
    GetEPGFromSKB([info for info in ChannelInfos if info[2] == 'SKB'])
    GetEPGFromNaver([info for info in ChannelInfos if info[2] == 'NAVER'])

    # 여기서부터는 기존의 채널 필터(My Channel)를 사용하지 않음
    GetEPGFromWAVVE([c for c in Channeldatajson if c['Source'] == 'WAVVE'])
    GetEPGFromTVING([c for c in Channeldatajson if c['Source'] == 'TVING'])

    print('</tv>')
    log.info('종료합니다.')


def GetEPGFromKT(ChannelInfos):
    if ChannelInfos:
        log.info('소스가 KT인 채널을 가져오고 있습니다.')
    else:
        return

    url = 'https://tv.kt.com/tv/channel/pSchedule.asp'
    referer = 'https://tv.kt.com/'
    params = {
        'ch_type': '1',             # 1: live 2: skylife 3: uhd live 4: uhd skylife
        'view_type': '1',           # 1: daily 2: weekly
        'service_ch_no': 'SVCID',
        'seldate': 'EPGDATE',
    }

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    # check all available channels
    try:
        url_ch = 'https://tv.kt.com/tv/channel/pChList.asp'
        params_ch = {"ch_type": "1", "parent_menu_id": "0"}
        soup = BeautifulSoup(request_data(url_ch, params_ch, method='POST', output='html', session=sess), htmlparser)
        raw_channels = [unquote(x.find('span', {'class': 'ch'}).text.strip()) for x in soup.select('li > a')]
        all_channels = [{
            'KT Name': ' '.join(x.split()[1:]),
            'KTCh': int(x.split()[0]),
            'Source': 'KT',
            'ServiceId': x.split()[0]
        } for x in raw_channels]
        dump_channels('KT', all_channels)
        all_services = [x['ServiceId'] for x in all_channels]
    except Exception as e:
        log.error('체널 목록을 가져오지 못했습니다: %s', str(e))
        all_services = [x[3] for x in ChannelInfos]

    for ChannelInfo in ChannelInfos:
        if ChannelInfo[3] not in all_services:
            log.warning('없는 서비스 아이디입니다: %s', ChannelInfo)
            continue
        epginfo = []
        for k in range(period):
            day = today + timedelta(days=k)
            params.update({'service_ch_no': ChannelInfo[3], 'seldate': day.strftime('%Y%m%d')})
            try:
                data = request_data(url, params, method='POST', output='html', session=sess)
                soup = BeautifulSoup(data, htmlparser, parse_only=SoupStrainer('tbody'))
                for row in soup.find_all('tr'):
                    cell = row.find_all('td')
                    for minute, program, category in zip(cell[1].find_all('p'), cell[2].find_all('p'), cell[3].find_all('p')):
                        startTime = str(day) + ' ' + cell[0].text.strip() + ':' + minute.text.strip()
                        startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M%S')
                        programName = program.text.replace('방송중 ', '').strip()
                        category = category.text.strip()
                        rating = 0
                        for image in program.find_all('img', alt=True):
                            grade = re.match('([\d,]+)', image['alt'])
                            if grade:
                                rating = int(grade.group(1))
                        epginfo.append([ChannelInfo[0], startTime, programName, '', '', '', '', category, '', False, rating])
            except Exception as e:
                log.error('파싱 에러: %s: %s' % (ChannelInfo, str(e)))
        epgzip(epginfo)


def GetEPGFromLG(ChannelInfos):
    if ChannelInfos:
        log.info('소스가 LG인 채널을 가져오고 있습니다.')
    else:
        return

    url = 'http://www.uplus.co.kr/css/chgi/chgi/RetrieveTvSchedule.hpi'
    referer = 'http://www.uplus.co.kr/css/chgi/chgi/RetrieveTvContentsMFamily.hpi'
    params = {'chnlCd': 'SVCID', 'evntCmpYmd': 'EPGDATE'}

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    for ChannelInfo in ChannelInfos:
        epginfo = []
        for k in range(period):
            day = today + timedelta(days=k)
            params.update({'chnlCd': ChannelInfo[3], 'evntCmpYmd': day.strftime('%Y%m%d')})
            data = request_data(url, params, method='POST', output='html', session=sess)
            try:
                data = data.replace('<재>', '&lt;재&gt;').replace(' [..', '').replace(' (..', '')
                soup = BeautifulSoup(data, htmlparser, parse_only=SoupStrainer('table'))
                if not str(soup):
                    log.warning('EPG 정보가 없거나 없는 채널입니다: %s' % ChannelInfo)
                    # 오늘 없으면 내일도 없는 채널로 간주
                    break
                for row in soup.find('table').tbody.find_all('tr'):
                    cell = row.find_all('td')
                    startTime = str(day) + ' ' + cell[0].text
                    startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M%S')
                    rating_str = cell[1].find('span', {'class': 'tag cte_all'}).text.strip()
                    rating = 0 if rating_str == 'All' else int(rating_str)
                    cell[1].find('span', {'class': 'tagGroup'}).decompose()
                    pattern = r'\s?(?:\[.*?\])?(.*?)(?:\[(.*)\])?\s?(?:\(([\d,]+)회\))?\s?(<재>)?$'
                    matches = re.match(pattern, cell[1].text.strip())
                    if matches:
                        programName = matches.group(1).strip() if matches.group(1) else ''
                        subprogramName = matches.group(2).strip() if matches.group(2) else ''
                        episode = matches.group(3) if matches.group(3) else ''
                        rebroadcast = True if matches.group(4) else False
                    else:
                        programName, subprogramName, episode, rebroadcast = '', '', '', False
                    category = cell[2].text.strip()
                    epginfo.append([ChannelInfo[0], startTime, programName, subprogramName, '', '', '', category, episode, rebroadcast, rating])
            except Exception as e:
                log.error('파싱 에러: %s: %s' % (ChannelInfo, str(e)))
        epgzip(epginfo)


def GetEPGFromSK(ChannelInfos):
    if ChannelInfos:
        log.info('소스가 SK인 채널을 가져오고 있습니다.')
    else:
        return

    url = 'http://mapp.btvplus.co.kr/sideMenu/live/IFGetData.do'
    referer = 'http://mapp.btvplus.co.kr/channelFavor.do'
    icon_url = 'http://mapp.btvplus.co.kr/data/btvplus/admobd/channelLogo/nsepg_{}.png'

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    def request_json(form_data):
        ret = []
        try:
            data = request_data(url, form_data, method='POST', output='json', session=sess)
            if data['result'].lower() == 'ok':
                ret = data['ServiceInfoArray']
            else:
                raise ValueError('유효한 응답이 아닙니다: %s' % data['reason'])
        except Exception as e:
            log.error(str(e))
        return ret

    # dump all available channels to json
    try:
        all_channels = [{
            'SK Name': x['NM_CH'],
            'SKCh': int(x['NO_CH']),
            'Icon_url': icon_url.format(x['ID_SVC']),
            'Source': 'SK',
            'ServiceId': x['ID_SVC']
        } for x in request_json({'variable': 'IF_LIVECHART_ALL'})]
        dump_channels('SK', all_channels)
        all_services = [x['ServiceId'] for x in all_channels]
    except Exception as e:
        log.error('체널 목록을 가져오지 못했습니다: %s', str(e))
        all_services = [x[3] for x in ChannelInfos]

    # remove unavailable channels in advance
    newChannelInfos = []
    for ChannelInfo in ChannelInfos:
        ServiceId = ChannelInfo[3]
        if ServiceId in all_services:
            newChannelInfos.append(ChannelInfo)
        else:
            log.warning('없는 서비스 아이디입니다: %s', ChannelInfo)

    params = {
        'variable': 'IF_LIVECHART_DETAIL',
        'o_date': 'EPGDATE',
        'svc_ids': '|'.join([info[3].strip() for info in newChannelInfos]),
    }

    for k in range(period):
        day = today + timedelta(days=k)
        params.update({'o_date': day.strftime('%Y%m%d')})
        channels = {x['ID_SVC']: x['EventInfoArray'] for x in request_json(params)}

        for ChannelInfo in newChannelInfos:
            ServiceId = ChannelInfo[3]
            if ServiceId in channels:
                programs = channels[ServiceId]
                writeSKPrograms(ChannelInfo, programs)
            else:
                log.warning('해당 날짜에 EPG 정보가 없거나 없는 채널입니다: %s %s' % (day.strftime('%Y%m%d'), ChannelInfo))

    log.info('SK EPG 완료: {}/{}개 채널'.format(len(newChannelInfos), len(ChannelInfos)))


def GetEPGFromSKB(ChannelInfos):
    if ChannelInfos:
        log.info('소스가 SKB인 채널을 가져오고 있습니다.')
    else:
        return

    def replacement(match, tag):
        if match:
            tag = tag.strip()
            programName = unescape(match.group(1)).replace('<', '&lt;').replace('>', '&gt;').strip()
            programName = '<' + tag + ' class="cont">' + programName
            return programName
        else:
            return ''

    url = 'http://m.skbroadband.com/content/realtime/Channel_List.do'
    referer = 'http://m.skbroadband.com/content/realtime/Channel_List.do'
    params = {'key_depth2': 'SVCID', 'key_depth3': 'EPGDATE'}

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    # dump all available channels to json
    try:
        url_ch = 'https://m.skbroadband.com/content/realtime/Realtime_List_Ajax.do'
        params_ch = {"package_name": "PM50305785", "pack": "18"}
        all_channels = [{
            'SKB Name': x['m_name'],
            'SKBCh': int(x['ch_no']),
            'Source': 'SKB',
            'ServiceId': x['c_menu'],
        } for x in request_data(url_ch, params_ch, method='POST', output='json', session=sess) if x['depth'] == '2']
        dump_channels('SKB', all_channels)
        all_services = [x['ServiceId'] for x in all_channels]
    except Exception as e:
        log.error('체널 목록을 가져오지 못했습니다: %s', str(e))
        all_services = [x[3] for x in ChannelInfos]

    for ChannelInfo in ChannelInfos:
        if ChannelInfo[3] not in all_services:
            log.warning('없는 서비스 아이디입니다: %s', ChannelInfo)
            continue
        epginfo = []
        for k in range(period):
            day = today + timedelta(days=k)
            params.update({'key_depth2': ChannelInfo[3], 'key_depth3': day.strftime('%Y%m%d')})
            data = request_data(url, params, method='GET', output='html', session=sess)
            try:
                data = re.sub('EUC-KR', 'utf-8', data)
                data = re.sub('<!--(.*?)-->', '', data, 0, re.I | re.S)
                data = re.sub('<span class="round_flag flag02">(.*?)</span>', '', data)
                data = re.sub('<span class="round_flag flag03">(.*?)</span>', '', data)
                data = re.sub('<span class="round_flag flag04">(.*?)</span>', '', data)
                data = re.sub('<span class="round_flag flag09">(.*?)</span>', '', data)
                data = re.sub('<span class="round_flag flag10">(.*?)</span>', '', data)
                data = re.sub('<span class="round_flag flag11">(.*?)</span>', '', data)
                data = re.sub('<span class="round_flag flag12">(.*?)</span>', '', data)
                data = re.sub('<strong class="hide">프로그램 안내</strong>', '', data)
                data = re.sub('<p class="cont">(.*)', partial(replacement, tag='p'), data)
                data = re.sub('<p class="tit">(.*)', partial(replacement, tag='p'), data)
                strainer = SoupStrainer('div', {'id': 'uiScheduleTabContent'})
                soup = BeautifulSoup(data, htmlparser, parse_only=strainer)
                html = soup.find_all('li', {'class': 'list'}) if soup.find_all('li') else ''
                if html:
                    for row in html:
                        startTime = endTime = programName = subprogramName = episode = ''
                        rebroadcast = False
                        rating = 0
                        startTime = str(day) + ' ' + row.find('p', {'class': 'time'}).text
                        startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M')
                        startTime = startTime.strftime('%Y%m%d%H%M%S')
                        cell = row.find('p', {'class': 'cont'})
                        grade = row.find('i', {'class': 'hide'})
                        if grade is not None:
                            rating = int(grade.text.replace('세 이상', '').strip())

                        if cell:
                            if cell.find('span'):
                                cell.span.decompose()
                            cell = cell.text.strip()
                            pattern = "^(.*?)(\(([\d,]+)회\))?(<(.*)>)?(\((재)\))?$"
                            matches = re.match(pattern, cell)

                            if matches:
                                programName = matches.group(1) if matches.group(1) else ''
                                subprogramName = matches.group(5) if matches.group(5) else ''
                                rebroadcast = True if matches.group(7) else False
                                episode = matches.group(3) if matches.group(3) else ''

                        epginfo.append([ChannelInfo[0], startTime, programName, subprogramName, '', '', '', '', episode, rebroadcast, rating])
                else:
                    log.warning('EPG 정보가 없거나 없는 채널입니다: %s' % ChannelInfo)
                    # 오늘 없으면 내일도 없는 채널로 간주
                    break
            except Exception as e:
                log.error('파싱 에러: %s: %s' % (ChannelInfo, str(e)))
            epgzip(epginfo)


def GetEPGFromNaver(ChannelInfos):
    if ChannelInfos:
        log.info('소스가 NAVER인 채널을 가져오고 있습니다.')
    else:
        return

    url = 'https://m.search.naver.com/p/csearch/content/nqapirender.nhn'
    referer = 'https://m.search.naver.com/search.naver?where=m&query=%ED%8E%B8%EC%84%B1%ED%91%9C'
    params = {
        'key': 'SingleChannelDailySchedule',
        'where': 'm',
        'pkid': '66',
        'u1': 'SVCID',
        'u2': 'EPGDATE'
    }

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    for ChannelInfo in ChannelInfos:
        epginfo = []
        for k in range(period):
            day = today + timedelta(days=k)
            params.update({'u1': ChannelInfo[3], 'u2': day.strftime('%Y%m%d')})
            data = request_data(url, params, method='GET', output='json', session=sess)
            try:
                if data['statusCode'].lower() != 'success':
                    log.error('유효한 응답이 아닙니다: %s %s' % (ChannelInfo, data['statusCode']))
                    continue

                soup = BeautifulSoup(''.join(data['dataHtml']), htmlparser)
                for row in soup.find_all('li', {'class': 'list'}):
                    cell = row.find_all('div')
                    rating = 0
                    programName = unescape(cell[4].text.strip())
                    startTime = str(day) + ' ' + cell[1].text.strip()
                    startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M%S')
                    rebroadcast = True if cell[3].find('span', {'class': 're'}) else False
                    try:
                        subprogramName = cell[5].text.strip()
                    except:
                        subprogramName = ''
                    epginfo.append([ChannelInfo[0], startTime, programName, subprogramName, '', '', '', '', '', rebroadcast, rating])
            except Exception as e:
                log.error('파싱 에러: %s: %s' % (ChannelInfo, str(e)))
        epgzip(epginfo)


def GetEPGFromWAVVE(reqChannels):
    if reqChannels:
        log.info('소스가 WAVVE인 채널을 가져오고 있습니다.')
    else:
        return

    '''
    개별채널: https://apis.pooq.co.kr/live/epgs/channels/{ServideId}
    전체채널: https://apis.pooq.co.kr/live/epgs
    정보량은 거의 비슷
    '''

    url = 'https://apis.pooq.co.kr/live/epgs'
    referer = 'https://www.wavve.com/schedule/index.html'
    params = {
        'enddatetime': '2020-01-20 24:00',
        'genre': 'all',
        'limit': 100,
        'offset': 0,
        'startdatetime': '2020-01-20 21:00',
        'apikey': 'E5F3E0D30947AA5440556471321BB6D9',
        'credential': 'none',
        'device': 'pc',
        'drm': 'wm',
        'partner': 'pooq',
        'pooqzone': 'none',
        'region': 'kor',
        'targetage': 'auto',
    }

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    # update parameters for requests
    params.update({
        'startdatetime': today.strftime('%Y-%m-%d') + ' 00:00',
        'enddatetime': (today + timedelta(days=period-1)).strftime('%Y-%m-%d') + ' 24:00',
    })

    channellist = request_data(url, params, method='GET', output='json', session=sess)['list']
    channeldict = {x['channelid']: x for x in channellist}

    # dump all available channels to json
    all_channels = [{
        'WAVVE Name': x['channelname'],
        'Icon_url': 'https://' + x['channelimage'],
        'Source': 'WAVVE',
        'ServiceId': x['channelid']
    } for x in channellist]
    dump_channels('WAVVE', all_channels)

    # remove unavailable channels in advance
    all_services = [x['channelid'] for x in channellist]
    tmpChannels = []
    for reqChannel in reqChannels:
        if reqChannel['ServiceId'] in all_services:
            tmpChannels.append(reqChannel)
        else:
            log.warning('없는 서비스 아이디입니다: %s', reqChannel)

    # reqChannels = all_channels  # request all channels
    reqChannels = tmpChannels

    # for caching program details
    programcache = {}

    try:
        for reqChannel in reqChannels:
            if not ('ServiceId' in reqChannel and reqChannel['ServiceId'] in channeldict):
                log.warning('EPG 정보가 없거나 없는 채널입니다: %s' % reqChannel)
                continue

            # 채널이름은 그대로 들어오고 프로그램 제목은 escape되어 들어옴
            srcChannel = channeldict[reqChannel['ServiceId']]
            channelid = reqChannel['Id'] if 'Id' in reqChannel else 'wavve|%s' % srcChannel['channelid']
            channelname = reqChannel['Name'] if 'Name' in reqChannel else srcChannel['channelname'].strip()
            channelicon = reqChannel['Icon_url'] if 'Icon_url' in reqChannel else 'https://' + srcChannel['channelimage']
            # channelliveimg = "https://wchimg.pooq.co.kr/pooqlive/thumbnail/%s.jpg" % reqChannel['ServiceId']
            print('  <channel id="%s">' % channelid)
            print('    <icon src="%s" />' % escape(channelicon))
            print('    <display-name>%s</display-name>' % escape(channelname))
            print('  </channel>')

            for program in srcChannel['list']:
                startTime = datetime.strptime(program['starttime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M%S')
                endTime = datetime.strptime(program['endtime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M%S')

                # TODO: 제목 너무 지저분/부실하네
                # TODO: python3에서 re.match에 더 많이 잡힘. 왜?
                programName = unescape(program['title'])
                pattern = '^(.*?)(?:\s*[\(<]([\d,회]+)[\)>])?(?:\s*<([^<]*?)>)?(\((재)\))?$'
                matches = re.match(pattern, programName)
                if matches:
                    programName = matches.group(1).strip() if matches.group(1) else ''
                    subprogramName = matches.group(3).strip() if matches.group(3) else ''
                    episode = matches.group(2).replace('회', '') if matches.group(2) else ''
                    episode = '' if episode == '0' else episode
                    rebroadcast = True if matches.group(5) else False
                else:
                    subprogramName, episode, rebroadcast = '', '', False

                rating = 0 if program['targetage'] == 'n' else int(program['targetage'])

                # 추가 정보 가져오기
                desc, category, iconurl, actors, producers = '', '', '', '', ''
                programid = program['programid'].strip()
                if programid and (programid not in programcache):
                    # 개별 programid가 없는 경우도 있으니 체크해야함
                    programdetail = getWAVVEProgramDetails(programid, sess)
                    if programdetail is not None:
                        programdetail[u'hit'] = 0  # to know cache hit rate
                    programcache[programid] = programdetail

                if (programid in programcache) and bool(programcache[programid]):
                    programcache[programid][u'hit'] += 1
                    programdetail = programcache[programid]
                    # TODO: 추가 제목 정보 활용
                    # programtitle = programdetail['programtitle']
                    # log.info('%s / %s' % (programName, programtitle))
                    desc = '\n'.join([x.replace('<br>', '\n').strip() for x in programdetail['programsynopsis'].splitlines()])     # carriage return(\r) 제거, <br> 제거
                    category = programdetail['genretext'].strip()
                    iconurl = 'https://' + programdetail['programposterimage'].strip()
                    # tags = programdetail['tags']['list'][0]['text']
                    if programdetail['actors']['list']:
                        actors = ','.join([x['text'] for x in programdetail['actors']['list']])

                writeProgram({
                    'channelId': channelid,
                    'startTime': startTime,
                    'endTime': endTime,
                    'programName': programName,
                    'subprogramName': subprogramName,
                    'desc': desc,
                    'actors': actors,
                    'producers': producers,
                    'category': category,
                    'episode': episode,
                    'rebroadcast': rebroadcast,
                    'rating': rating,
                    'iconurl': iconurl
                })
        log.info('WAVVE EPG 완료: {}개 채널'.format(len(reqChannels)))
    except Exception as e:
        log.error(str(e))


def getWAVVEProgramDetails(programid, sess):
    url = 'https://apis.pooq.co.kr/vod/programs-contentid/' + programid
    referer = 'https://www.wavve.com/player/vod?programid=' + programid
    param = {
        "apikey": "E5F3E0D30947AA5440556471321BB6D9",
        "credential": "none",
        "device": "pc",
        "drm": "wm",
        "partner": "pooq",
        "pooqzone": "none",
        "region": "kor",
        "targetage": "auto"
    }
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    ret = None
    try:
        contentid = request_data(url, param, method='GET', output='json', session=sess)['contentid'].strip()

        # url2 = 'https://apis.pooq.co.kr/cf/vod/contents/' + contentid
        url2 = 'https://apis.pooq.co.kr/vod/contents/' + contentid    # 같은 주소지만 이게 더 안정적인듯
        ret = request_data(url2, param, method='GET', output='json', session=sess)
    except Exception as e:
        log.error(str(e))
    return ret


def GetEPGFromTVING(reqChannels):
    if reqChannels:
        log.info('소스가 TVING인 채널을 가져오고 있습니다.')
    else:
        return

    url = 'https://api.tving.com/v2/media/schedules'
    referer = 'https://www.tving.com/schedule/main.do'
    params = {
        "pageNo": "1",
        "pageSize": "20",   # maximum 20
        "order": "chno",
        "scope": "all",
        "adult": "all",
        "free": "all",
        "broadDate": "20200608",
        "broadcastDate": "20200608",
        "startBroadTime": "030000",  # 최대 3시간 간격
        "endBroadTime": "060000",
        # "channelCode": "C06941,C07381,...",
        "screenCode": "CSSD0100",
        "networkCode": "CSND0900",
        "osCode": "CSOD0900",
        "teleCode": "CSCD0900",
        "apiKey": "1e7952d0917d6aab1f0293a063697610",
    }

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    def get_json(_params):
        _page = 1
        _results = []
        while True:
            _params.update({'pageNo': str(_page)})
            _data = request_data(url, _params, method='GET', output='json', session=sess)
            if _data['header']['status'] != 200:
                raise requests.exceptions.RequestException
            else:
                _results.extend(_data['body']['result'])
            if _data['body']['has_more'] == 'Y':
                _page += 1
            else:
                return _results

    def get_imgurl(_item):
        priority_img_code = ['CAIC1600', 'CAIC0100', 'CAIC0400']
        for img_code in priority_img_code:
            img_list = [x for x in _item['image'] if x['code'] == img_code]
            if img_list:
                return 'https://image.tving.com' + (img_list[0]['url'] if 'url' in img_list[0] else img_list[0]['url2'])

    gcode = {
        'CPTG0100': 0,
        'CPTG0200': 7,
        'CPTG0300': 12,
        'CPTG0400': 15,
        'CPTG0500': 19,
        'CMMG0100': 0,
        'CMMG0200': 12,
        'CMMG0300': 15,
        'CMMG0400': 19,
    }

    # update parameters for requests
    params.update({
        'broadDate': today.strftime('%Y%m%d'),
        'broadcastDate': today.strftime('%Y%m%d'),
        "startBroadTime": datetime.now().strftime('%H') + "0000",
        "endBroadTime": (datetime.now() + timedelta(hours=3)).strftime('%H') + "0000",
    })

    channellist = get_json(params)
    all_channels = [{
        'TVING Name': x['channel_name']['ko'],
        'Icon_url': get_imgurl(x),
        'Source': 'TVING',
        'ServiceId': x['channel_code']
    } for x in channellist if x['schedules'] is not None]
    dump_channels('TVING', all_channels)

    # remove unavailable channels in advance
    all_services = [x['channel_code'] for x in channellist]
    tmpChannels = []
    for reqChannel in reqChannels:
        if reqChannel['ServiceId'] in all_services:
            tmpChannels.append(reqChannel)
        else:
            log.warning('없는 서비스 아이디입니다: %s', reqChannel)

    # reqChannels = all_channels  # request all channels
    reqChannels = tmpChannels

    params.update({"channelCode": ','.join([x['ServiceId'].strip() for x in reqChannels])})

    channeldict = {}
    for k in range(period):
        day = today + timedelta(days=k)
        params.update({'broadDate': day.strftime('%Y%m%d'), 'broadcastDate': day.strftime('%Y%m%d')})
        for t in range(8):
            params.update({
                "startBroadTime": '{:02d}'.format(t*3) + "0000",
                "endBroadTime": '{:02d}'.format(t*3+3) + "0000",
            })
            for ch in get_json(params):
                if ch['channel_code'] in channeldict:
                    if ch['schedules']:
                        channeldict[ch['channel_code']]['schedules'] += ch['schedules']
                else:
                    channeldict[ch['channel_code']] = ch

    for reqChannel in reqChannels:
        if not ('ServiceId' in reqChannel and reqChannel['ServiceId'] in channeldict):
            log.warning('EPG 정보가 없거나 없는 채널입니다: %s' % reqChannel)
            continue
        srcChannel = channeldict[reqChannel['ServiceId']]
        channelid = reqChannel['Id'] if 'Id' in reqChannel else 'tving|%s' % srcChannel['channel_code']
        channelname = reqChannel['Name'] if 'Name' in reqChannel else srcChannel['channel_name']['ko'].strip()
        channelicon = reqChannel['Icon_url'] if 'Icon_url' in reqChannel else get_imgurl(srcChannel)
        print('  <channel id="%s">' % channelid)
        print('    <icon src="%s" />' % escape(channelicon))
        print('    <display-name>%s</display-name>' % escape(channelname))
        print('  </channel>')

        for sch in srcChannel['schedules']:
            # 공통
            startTime = str(sch['broadcast_start_time'])
            endTime = str(sch['broadcast_end_time'])
            rebroadcast = True if sch['rerun_yn'] == 'Y' else False

            get_from = 'movie' if sch['movie'] else 'program'
            img_code = 'CAIM2100' if sch['movie'] else 'CAIP0900'

            rating = gcode[sch[get_from]['grade_code']]

            programName = sch[get_from]['name']['ko']
            subprogramName = sch[get_from]['name']['en'] if sch[get_from]['name']['en'] else ''

            category = sch[get_from]['category1_name']['ko']
            actors = ','.join(sch[get_from]['actor'])
            producers = ','.join(sch[get_from]['director'])

            iconurl = ''
            poster = [x['url'] for x in sch[get_from]['image'] if x['code'] == img_code]
            if poster:
                iconurl = 'https://image.tving.com' + poster[0]
                # iconurl += '/dims/resize/236'

            episode = ''
            desc = sch[get_from]['story' if sch['movie'] else 'synopsis']['ko']
            if sch['episode']:
                episode = sch['episode']['frequency']
                episode = '' if episode == 0 else str(episode)
                desc = sch['episode']['synopsis']['ko']

            writeProgram({
                'channelId': channelid,
                'startTime': startTime,
                'endTime': endTime,
                'programName': programName,
                'subprogramName': subprogramName,
                'desc': desc,
                'actors': actors,
                'producers': producers,
                'category': category,
                'episode': episode,
                'rebroadcast': rebroadcast,
                'rating': rating,
                'iconurl': iconurl
            })
    log.info('TVING EPG 완료: {}개 채널'.format(len(reqChannels)))


def epgzip(epginfo):
    # ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
    if epginfo:
        epginfo = iter(epginfo)
        epg1 = next(epginfo)
        for epg2 in epginfo:
            ChannelId = epg1[0]
            startTime = epg1[1] if epg1[1] else ''
            endTime = epg2[1] if epg2[1] else ''
            programName = epg1[2] if epg1[2] else ''
            subprogramName = epg1[3] if epg1[3] else ''
            desc = epg1[4] if epg1[4] else ''
            actors = epg1[5] if epg1[5] else ''
            producers = epg1[6] if epg1[6] else ''
            category = epg1[7] if epg1[7] else ''
            episode = epg1[8] if epg1[8] else ''
            rebroadcast = True if epg1[9] else False
            rating = int(epg1[10]) if epg1[10] else 0
            writeProgram({
                'channelId': ChannelId,
                'startTime': startTime,
                'endTime': endTime,
                'programName': programName,
                'subprogramName': subprogramName,
                'desc': desc,
                'actors': actors,
                'producers': producers,
                'category': category,
                'episode': episode,
                'rebroadcast': rebroadcast,
                'rating': rating
            })
            epg1 = epg2


def writeProgram(programdata):
    ChannelId = programdata['channelId']
    startTime = programdata['startTime']
    endTime = programdata['endTime']
    programName = escape(programdata['programName']).strip()
    subprogramName = escape(programdata['subprogramName']).strip()
    matches = re.match('(.*) \(?(\d+부)\)?', unescape(programName))
    if matches:
        programName = escape(matches.group(1)).strip()
        subprogramName = escape(matches.group(2)) + ' ' + subprogramName
        subprogramName = subprogramName.strip()
    if programName is None:
        programName = subprogramName
    actors = escape(programdata['actors'])
    producers = escape(programdata['producers'])
    category = escape(programdata['category'])
    episode = programdata['episode']
    if episode:
        try:
            episode_ns = int(episode) - 1
        except ValueError:
            episode_ns = int(episode.split(',', 1)[0]) - 1
        episode_ns = '0' + '.' + str(episode_ns) + '.' + '0' + '/' + '0'
        episode_on = episode
    rebroadcast = programdata['rebroadcast']
    if episode and addepisode == 'y':
        programName = programName + ' (' + str(episode) + '회)'
    if rebroadcast and (addrebroadcast == 'y'):
        programName = programName + ' (재)'
    if programdata['rating'] == 0:
        rating = '전체 관람가'
    else:
        rating = '%s세 이상 관람가' % (programdata['rating'])
    if addverbose == 'y':
        desc = programName
        if subprogramName:
            desc += '\n부제 : ' + subprogramName
        if rebroadcast and (addrebroadcast == 'y'):
            desc += '\n방송 : 재방송'
        if episode:
            desc += '\n회차 : ' + str(episode) + '회'
        if category:
            desc += '\n장르 : ' + category
        if actors:
            desc += '\n출연 : ' + actors.strip()
        if producers:
            desc += '\n제작 : ' + producers.strip()
        desc += '\n등급 : ' + rating
    else:
        desc = ''
    if programdata['desc']:
        desc += '\n' + escape(programdata['desc'])
    desc = re.sub(' +', ' ', desc)
    contentTypeDict = {
        '교양': 'Arts / Culture (without music)',
        '만화': 'Cartoons / Puppets',
        '교육': 'Education / Science / Factual topics',
        '취미': 'Leisure hobbies',
        '드라마': 'Movie / Drama',
        '영화': 'Movie / Drama',
        '음악': 'Music / Ballet / Dance',
        '뉴스': 'News / Current affairs',
        '다큐': 'Documentary',
        '라이프': 'Documentary',
        '시사/다큐': 'Documentary',
        '연예': 'Show / Game show',
        '스포츠': 'Sports',
        '홈쇼핑': 'Advertisement / Shopping'
    }
    contentType = ''
    for key, value in contentTypeDict.items():
        if key in category:
            contentType = value
    print('  <programme start="%s +0900" stop="%s +0900" channel="%s">' % (startTime, endTime, ChannelId))
    print('    <title lang="kr">%s</title>' % programName)
    if subprogramName:
        print('    <sub-title lang="kr">%s</sub-title>' % subprogramName)
    if addverbose == 'y':
        print('    <desc lang="kr">%s</desc>' % desc)
        if actors or producers:
            print('    <credits>')
            if actors:
                for actor in actors.split(','):
                    if actor.strip():
                        print('      <actor>%s</actor>' % actor.strip())
            if producers:
                for producer in producers.split(','):
                    if producer.strip():
                        print('      <producer>%s</producer>' % producer.strip())
            print('    </credits>')
    if category:
        print('    <category lang="kr">%s</category>' % category)
    if contentType:
        print('    <category lang="en">%s</category>' % contentType)
    if episode and addxmltvns == 'y':
        print('    <episode-num system="xmltv_ns">%s</episode-num>' % episode_ns)
    if episode and addxmltvns != 'y':
        print('    <episode-num system="onscreen">%s</episode-num>' % episode_on)
    if rebroadcast:
        print('    <previously-shown />')
    if rating:
        print('    <rating system="KMRB">')
        print('      <value>%s</value>' % rating)
        print('    </rating>')
    if ('iconurl' in programdata) and programdata['iconurl']:
        print('    <icon src="%s" />' % escape(programdata['iconurl']))
    print('  </programme>')


def writeSKPrograms(ChannelInfo, programs):
    genre_code = {
        '1': '드라마',
        '2': '영화',
        '4': '만화',
        '8': '스포츠',
        '9': '교육',
        '11': '홈쇼핑',
        '13': '예능',
        '14': '시사/다큐',
        '15': '음악',
        '16': '라이프',
        '17': '교양',
        '18': '뉴스',
    }
    for program in programs:
        rebroadcast = False
        programName = program['NM_TITLE'].replace('...', '>')
        pattern = '^(.*?)(?:\s*[\(<]([\d,회]+)[\)>])?(?:\s*<([^<]*?)>)?(\((재)\))?$'
        matches = re.match(pattern, programName)
        if matches:
            programName = matches.group(1).strip() if matches.group(1) else ''
            subprogramName = matches.group(3).strip() if matches.group(3) else ''
            episode = matches.group(2).replace('회', '') if matches.group(2) else ''
            episode = '' if episode == '0' else episode
            rebroadcast = True if matches.group(5) else False
        startTime = program['DT_EVNT_START']
        endTime = program['DT_EVNT_END']
        desc = program['NM_SYNOP'] if program['NM_SYNOP'] else ''
        if 'AdditionalInfoArray' in program:
            info_array = program['AdditionalInfoArray'][0]
            actors = info_array['NM_ACT'].replace('...', '').strip(', ') if info_array['NM_ACT'] else ''
            producers = info_array['NM_DIRECTOR'].replace('...', '').strip(', ') if info_array['NM_DIRECTOR'] else ''
        else:
            actors, producers = '', ''
        if program['CD_GENRE'] and (program['CD_GENRE'] in genre_code):
            category = genre_code[program['CD_GENRE']]
        else:
            category = ''
        rating = int(program['CD_RATING']) if program['CD_RATING'] else 0
        writeProgram({
            'channelId': ChannelInfo[0],
            'startTime': startTime,
            'endTime': endTime,
            'programName': programName,
            'subprogramName': subprogramName,
            'desc': desc,
            'actors': actors,
            'producers': producers,
            'category': category,
            'episode': episode,
            'rebroadcast': rebroadcast,
            'rating': rating
        })


def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.error("파일 읽는 중 에러: %s", file_path)
        log.error(str(e))
        sys.exit(1)


def dump_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        log.warning("파일 저장 중 에러: %s", file_path)
        log.warning(str(e))


def dump_channels(name_suffix, channels):
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Channel_%s.json' % name_suffix)
    headers = [{'last update': datetime.now().strftime('%Y/%m/%d %H:%M:%S'), 'total': len(channels)}]
    dump_json(filename, headers + channels)


def request_data(url, params, method='GET', output='html', session=None, ret=''):
    sess = requests.Session() if session is None else session
    try:
        if method == 'GET':
            r = sess.get(url, params=params, timeout=req_timeout)
        elif method == 'POST':
            r = sess.post(url, data=params, timeout=req_timeout)
        else:
            raise ValueError('Unexpected method: %s', method)
        r.raise_for_status()
        if output.lower() == 'html':
            ret = r.text
        elif output.lower() == 'json':
            ret = r.json()
        else:
            raise ValueError('Unexpected output type: %s', output)
    except Exception as e:
        log.error('요청 중 에러: %s' % str(e))
    time.sleep(req_sleep)
    return ret


Channeldatajson = load_json(args['channelfile'])
json_conf = load_json(args['configfile'])

log.debug('설정을 읽어오는 중 ...')

# default config
conf = {
    'MyISP': 'ALL',
    'MyChannels': '',
    'output': 'd',
    'default_xml_file': 'xmltv.xml',
    'default_xml_socket': 'xmltv.sock',
    'default_icon_url': '',
    'default_fetch_limit': '2',
    'default_rebroadcast': 'y',
    'default_episode': 'y',
    'default_verbose': 'n',
    'default_xmltvns': 'n',
}
for k in conf:
    if k in args and args[k]:
        conf[k] = args[k]
        log.debug('%s=%s by %s', k, args[k], 'cmd')
    elif k in json_conf and json_conf[k]:
        conf[k] = json_conf[k]
        log.debug('%s=%s by %s', k, json_conf[k], 'configfile')
    else:
        log.debug('%s=%s by %s', k, conf[k], 'default')

#
# validate settings
#
MyISP = conf['MyISP']
if not any(MyISP in s for s in ['ALL', 'KT', 'LG', 'SK']):
    log.error("MyISP는 ALL, KT, LG, SK만 가능합니다.")
    sys.exit(1)

cids = [x['Id'] for x in Channeldatajson if 'Id' in x]
min_cid, max_cid = min(cids), max(cids)
cid_bin = [0] * (max_cid+1)
for r in conf['MyChannels'].strip('"').strip("'").split(','):
    first, last = min_cid-1, max_cid
    if r.strip() != '*':
        ends = r.split('-')
        if len(ends) == 1:
            first = last = int(r)
        elif len(ends) == 2:
            a, b = ends
            first = int(a) if a.strip() != '' else first
            last = int(b) if b.strip() != '' else last
        else:
            log.error('MyChannels 범위에 문제가 있습니다: %s', conf['MyChannels'])
            sys.exit(1)
    if first < min_cid:
        first = min_cid
    if last >= max_cid:
        last = max_cid
    for i in range(first, last+1):
        cid_bin[i] = 1
MyChannels = [str(x) for x, y in enumerate(cid_bin) if y == 1]

if not any(conf['output'] in s for s in ['d', 'o', 's']):
    log.error("output은 d, o, s만 가능합니다.")
    sys.exit(1)
if conf['output'] == 'o':
    sys.stdout = open(conf['default_xml_file'], 'w', encoding='utf-8')
elif conf['output'] == 's':
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(conf['default_xml_socket'])
        sockfile = sock.makefile('w')
        sys.stdout = sockfile
    except socket.error:
        log.error('xmltv.sock 파일을 찾을 수 없습니다.')
        sys.exit(1)

IconUrl = conf['default_icon_url']

if not any(conf['default_rebroadcast'] in s for s in 'yn'):
    log.error("default_rebroadcast는 y, n만 가능합니다.")
    sys.exit(1)
else:
    addrebroadcast = conf['default_rebroadcast']

if not any(conf['default_episode'] in s for s in 'yn'):
    log.error("default_episode는 y, n만 가능합니다.")
    sys.exit(1)
else:
    addepisode = conf['default_episode']

if not any(conf['default_verbose'] in s for s in 'yn'):
    log.error("default_verbose는 y, n만 가능합니다.")
    sys.exit(1)
else:
    addverbose = conf['default_verbose']

if not any(conf['default_xmltvns'] in s for s in 'yn'):
    log.error("default_xmltvns는 y, n만 가능합니다.")
    sys.exit(1)
else:
    addxmltvns = conf['default_xmltvns']

if not any(conf['default_fetch_limit'] in s for s in '1234567'):
    log.error("default_fetch_limit은 1-7만 가능합니다.")
    sys.exit(1)
else:
    period = int(conf['default_fetch_limit'])

getEpg()
