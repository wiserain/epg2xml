#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import re
import sys
import imp
import time
import json
import codecs
import socket
import logging
import argparse
from functools import partial
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, date
from xml.sax.saxutils import escape, unescape

#
# default variables
#
__version__ = '1.2.7p2'
debug = True
today = date.today()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
timeout = 5
req_sleep = 1
htmlparser = 'lxml'
loglevel = logging.DEBUG if debug else logging.INFO

#
# logging
#
log = logging.getLogger(__name__)
log.setLevel(loglevel)

log_fmt = "%(asctime)-15s %(levelname)-8s %(lineno)03d %(message)s"
formatter = logging.Formatter(log_fmt, datefmt='%Y/%m/%d %H:%M:%S')

# logging to file
filehandler = RotatingFileHandler(
    __file__ + '.log',
    maxBytes=1024 * 1000, backupCount=10, encoding='utf-8'
)
filehandler.setLevel(loglevel)
filehandler.setFormatter(formatter)
log.addHandler(filehandler)

# logging to console, stderr by default
consolehandler = logging.StreamHandler()
consolehandler.setLevel(loglevel)
consolehandler.setFormatter(formatter)
log.addHandler(consolehandler)

#
# import third-parties
#
try:
    imp.find_module('bs4')
    from bs4 import BeautifulSoup, SoupStrainer
except ImportError:
    log.error("BeautifulSoup 모듈이 설치되지 않았습니다.")
    sys.exit(1)
try:
    imp.find_module('lxml')
    from lxml import html
except ImportError:
    log.error("lxml 모듈이 설치되지 않았습니다.")
    sys.exit(1)
try:
    imp.find_module('requests')
    import requests
except ImportError:
    log.error("requests 모듈이 설치되지 않았습니다.")
    sys.exit(1)

reload(sys)
sys.setdefaultencoding('utf-8')

if sys.version_info[:2] != (2, 7):
    log.error("python 2.7 버전이 필요합니다.")
    sys.exit(1)


# Get epg data
def getEpg():
    # XML 헤더 시작
    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
    print('<tv generator-info-name="epg2xml ' + __version__ + '">')

    # My Channel 정의
    MyChannelInfo = [ch.strip() for ch in MyChannels.split(',') if ch]

    ChannelInfos = []
    for Channeldata in Channeldatajson:     # Get Channel & Print Channel info
        if (Channeldata['Source'] in ['KT', 'LG', 'SK', 'SKB', 'NAVER']) and (str(Channeldata['Id']) in MyChannelInfo):
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
    GetEPGFromWAVVE([c for c in Channeldatajson if c['Source'] == 'POOQ' or c['Source'] == 'WAVVE'])

    print('</tv>')
    log.info('성공적으로 가져왔습니다.')


def GetEPGFromKT(ChannelInfos):
    if ChannelInfos:
        log.info('KT EPG 데이터를 가져오고 있습니다.')
    else:
        return

    url = 'https://tv.kt.com/tv/channel/pSchedule.asp'
    referer = 'https://tv.kt.com/'
    params = {
        'ch_type': '1',
        'view_type': '1',
        'service_ch_no': 'SVCID',
        'seldate': 'EPGDATE',
    }

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    for ChannelInfo in ChannelInfos:
        epginfo = []
        for k in range(period):
            day = today + timedelta(days=k)
            params.update({'service_ch_no': ChannelInfo[3], 'seldate': day.strftime('%Y%m%d')})
            try:
                response = sess.post(url, data=params, timeout=timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, htmlparser, parse_only=SoupStrainer('tbody'))
                html = soup.find_all('tr') if soup.find('tbody') else ''
                if html:
                    for row in html:
                        for cell in [row.find_all('td')]:
                            startTime = endTime = programName = subprogramName = desc = actors = producers = category = episode = ''
                            rebroadcast = False
                            for minute, program, category in zip(cell[1].find_all('p'), cell[2].find_all('p'), cell[3].find_all('p')):
                                startTime = str(day) + ' ' + cell[0].text.strip() + ':' + minute.text.strip()
                                startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M')
                                startTime = startTime.strftime('%Y%m%d%H%M%S')
                                programName = program.text.replace('방송중 ', '').strip()
                                category = category.text.strip()
                                for image in [program.find_all('img', alt=True)]:
                                    grade = re.match('([\d,]+)', image[0]['alt'])
                                    rating = int(grade.group(1)) if grade else 0
                                # ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
                                epginfo.append([ChannelInfo[0], startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                else:
                    log.info('EPG 정보가 없거나 없는 채널입니다: %s' % ChannelInfo)
                    # 오늘 없으면 내일도 없는 채널로 간주
                    break
            except requests.exceptions.RequestException as e:
                log.error('요청 중 에러: %s: %s' % (ChannelInfo, str(e)))

            # req_sleep
            time.sleep(req_sleep)

        if epginfo:
            epgzip(epginfo)


def GetEPGFromLG(ChannelInfos):
    if ChannelInfos:
        log.info('LG EPG 데이터를 가져오고 있습니다.')
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
            try:
                response = sess.post(url, data=params, timeout=timeout)
                response.raise_for_status()
                data = unicode(response.content, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
                data = data.replace('<재>', '&lt;재&gt;').replace(' [..', '').replace(' (..', '')
                soup = BeautifulSoup(data, htmlparser, parse_only=SoupStrainer('table'), from_encoding='utf-8')
                html = soup.find('table').tbody.find_all('tr') if soup.find('table') else ''
                if html:
                    for row in html:
                        for cell in [row.find_all('td')]:
                            startTime = endTime = programName = subprogramName = desc = actors = producers = category = episode = ''
                            rebroadcast = False
                            startTime = str(day) + ' ' + cell[0].text
                            startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M')
                            startTime = startTime.strftime('%Y%m%d%H%M%S')
                            rating_str = cell[1].find('span', {'class': 'tag cte_all'}).text.strip()
                            rating = 0 if rating_str == 'All' else int(rating_str)
                            cell[1].find('span', {'class': 'tagGroup'}).decompose()
                            pattern = '(<재>)?\s?(?:\[.*?\])?(.*?)(?:\[(.*)\])?\s?(?:\(([\d,]+)회\))?$'
                            matches = re.match(pattern, cell[1].text.strip().decode('string_escape'))
                            if matches:
                                programName = matches.group(2).strip() if matches.group(2) else ''
                                subprogramName = matches.group(3).strip() if matches.group(3) else ''
                                episode = matches.group(4) if matches.group(4) else ''
                                rebroadcast = True if matches.group(1) else False
                            category = cell[2].text.strip()
                            # ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
                            epginfo.append([ChannelInfo[0], startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                else:
                    log.info('EPG 정보가 없거나 없는 채널입니다: %s' % ChannelInfo)
                    # 오늘 없으면 내일도 없는 채널로 간주
                    break
            except requests.exceptions.RequestException as e:
                log.error('요청 중 에러: %s: %s' % (ChannelInfo, str(e)))

            # req_sleep
            time.sleep(req_sleep)

        if epginfo:
            epgzip(epginfo)


def GetEPGFromSK(ChannelInfos):
    if ChannelInfos:
        log.info('SK EPG 데이터를 가져오고 있습니다.')
    else:
        return

    url = 'http://mapp.btvplus.co.kr/sideMenu/live/IFGetData.do'
    referer = 'http://mapp.btvplus.co.kr/channelFavor.do'
    params = {
        'variable': 'IF_LIVECHART_DETAIL',
        'o_date': 'EPGDATE',
        'svc_ids': 'SVCID1|SVCID2',
    }

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    for k in range(period):
        day = today + timedelta(days=k)
        params.update({
            'o_date': day.strftime('%Y%m%d'),
            'svc_ids': '|'.join([info[3] for info in ChannelInfos]),
        })
        try:
            response = sess.post(url, data=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if data['result'].lower() == 'ok':
                channels = {x['ID_SVC']: x['EventInfoArray'] for x in data['ServiceInfoArray']}
                for ChannelInfo in ChannelInfos:
                    ServiceId = ChannelInfo[3]
                    if ServiceId in channels:
                        programs = channels[ServiceId]
                        writeSKPrograms(ChannelInfo, programs)
                    else:
                        log.info('EPG 정보가 없거나 없는 채널입니다: %s %s' % (day.strftime('%Y%m%d'), ChannelInfo))
            else:
                log.error('유효한 응답이 아닙니다: %s' % data['reason'])
        except ValueError as e:
            log.error(str(e))
        except requests.exceptions.RequestException as e:
            log.error('요청 중 에러: %s' % str(e))

        # req_sleep
        time.sleep(req_sleep)


def GetEPGFromSKB(ChannelInfos):
    if ChannelInfos:
        log.info('SKB EPG 데이터를 가져오고 있습니다.')
    else:
        return

    url = 'http://m.skbroadband.com/content/realtime/Channel_List.do'
    referer = 'http://m.skbroadband.com/content/realtime/Channel_List.do'
    params = {'key_depth2': 'SVCID', 'key_depth3': 'EPGDATE'}

    sess = requests.session()
    sess.headers.update({'User-Agent': ua, 'Referer': referer})

    for ChannelInfo in ChannelInfos:
        epginfo = []
        for k in range(period):
            day = today + timedelta(days=k)
            params.update({'key_depth2': ChannelInfo[3], 'key_depth3': day.strftime('%Y%m%d')})
            try:
                response = sess.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                html_data = response.content
                data = unicode(html_data, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
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
                soup = BeautifulSoup(data, htmlparser, parse_only=strainer, from_encoding='utf-8')
                html = soup.find_all('li', {'class': 'list'}) if soup.find_all('li') else ''
                if html:
                    for row in html:
                        startTime = endTime = programName = subprogramName = desc = actors = producers = category = episode = ''
                        rebroadcast = False
                        rating = 0
                        startTime = str(day) + ' ' + row.find('p', {'class': 'time'}).text
                        startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M')
                        startTime = startTime.strftime('%Y%m%d%H%M%S')
                        cell = row.find('p', {'class': 'cont'})
                        grade = row.find('i', {'class': 'hide'})
                        if grade is not None:
                            rating = int(grade.text.decode('string_escape').replace('세 이상', '').strip())

                        if cell:
                            if cell.find('span'):
                                cell.span.decompose()
                            cell = cell.text.decode('string_escape').strip()
                            pattern = "^(.*?)(\(([\d,]+)회\))?(<(.*)>)?(\((재)\))?$"
                            matches = re.match(pattern, cell)

                            if matches:
                                programName = matches.group(1) if matches.group(1) else ''
                                subprogramName = matches.group(5) if matches.group(5) else ''
                                rebroadcast = True if matches.group(7) else False
                                episode = matches.group(3) if matches.group(3) else ''

                        # ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
                        epginfo.append([ChannelInfo[0], startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                else:
                    log.info('EPG 정보가 없거나 없는 채널입니다: %s' % ChannelInfo)
                    # 오늘 없으면 내일도 없는 채널로 간주
                    break
            except requests.exceptions.RequestException as e:
                log.error('요청 중 에러: %s: %s' % (ChannelInfo, str(e)))

            # req_sleep
            time.sleep(req_sleep)

        if epginfo:
            epgzip(epginfo)


def GetEPGFromNaver(ChannelInfos):
    if ChannelInfos:
        log.info('NAVER EPG 데이터를 가져오고 있습니다.')
    else:
        return

    url = 'https://m.search.naver.com/p/csearch/content/nqapirender.nhn'
    referer = 'https://m.search.naver.com/search.naver?where=m&query=%ED%8E%B8%EC%84%B1%ED%91%9C'
    params = {
        'callback': 'epg',
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
            try:
                response = sess.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                json_data = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "", response.text.split("epg(")[1].strip(");").strip())
                try:
                    data = json.loads(json_data, encoding='utf-8')
                    if data['statusCode'].lower() != 'success':
                        log.error('유효한 응답이 아닙니다: %s %s' % (ChannelInfo, data['statusCode']))
                        break

                    for ul in data['dataHtml']:
                        strainer = SoupStrainer('ul', {'class': 'ind_list'})
                        soup = BeautifulSoup(ul, htmlparser, parse_only=strainer)
                        html = soup.find_all('li', {'class': 'list'}) if soup.find('ul', {'class': 'ind_list'}) else ''
                        if html:
                            for row in html:
                                for cell in [row.find_all('div')]:
                                    startTime = endTime = programName = subprogramName = desc = actors = producers = category = episode = ''
                                    rating = 0
                                    programName = unescape(cell[4].text.strip())
                                    startTime = str(day) + ' ' + cell[1].text.strip()
                                    startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M')
                                    startTime = startTime.strftime('%Y%m%d%H%M%S')
                                    rebroadcast = True if cell[3].find('span', {'class': 're'}) else False
                                    try:
                                        subprogramName = cell[5].text.strip()
                                    except:
                                        subprogramName = ''
                                    epginfo.append([ChannelInfo[0], startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                        else:
                            log.info('EPG 정보가 없거나 없는 채널입니다: %s %s' % (day.strftime('%Y%m%d'), ChannelInfo))

                except ValueError as e:
                    log.error(str(e))
            except requests.RequestException as e:
                log.error('요청 중 에러: %s: %s' % (ChannelInfo, str(e)))

            # req_sleep
            time.sleep(req_sleep)

        if epginfo:
            epgzip(epginfo)


def GetEPGFromWAVVE(reqChannels):
    if reqChannels:
        log.info('WAVVE EPG 데이터를 가져오고 있습니다.')
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

    # for caching program details
    programdict = {}

    try:
        response = sess.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        channellist = response.json()['list']
        channeldict = {x['channelid']: x for x in channellist}

        for reqChannel in reqChannels:
            if 'ServiceId' in reqChannel and reqChannel['ServiceId'] in channeldict:
                # 채널이름은 그대로 들어오고 프로그램 제목은 escape되어 들어옴
                srcChannel = channeldict[reqChannel['ServiceId']]
                channelid = reqChannel['Id'] if 'Id' in reqChannel else 'pooq|%s' % srcChannel['channelid']
                channelname = reqChannel['Name'] if 'Name' in reqChannel else srcChannel['channelname'].strip()
                channelicon = reqChannel['Icon_url'] if 'Icon_url' in reqChannel else 'https://' + srcChannel['channelimage']
                # channelliveimg = "https://wchimg.pooq.co.kr/pooqlive/thumbnail/%s.jpg" % reqChannel['ServiceId']
                print('  <channel id="%s">' % channelid)
                print('    <icon src="%s" />' % escape(channelicon))
                print('    <display-name>%s</display-name>' % escape(channelname))
                print('  </channel>')

                for program in srcChannel['list']:
                    startTime = endTime = programName = subprogramName = desc = ''
                    actors = producers = category = episode = iconurl = ''
                    rebroadcast = False
                    startTime = datetime.strptime(program['starttime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M%S')
                    endTime = datetime.strptime(program['endtime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M%S')

                    # TODO: 제목 너무 지저분/부실하네
                    programName = unescape(program['title'].strip())
                    pattern = '^(.*?)(?:\s*[\(<]([\d,회]+)[\)>])?(?:\s*<([^<]*?)>)?(\((재)\))?$'
                    matches = re.match(pattern, programName)
                    if matches:
                        programName = matches.group(1).strip() if matches.group(1) else ''
                        subprogramName = matches.group(3).strip() if matches.group(3) else ''
                        episode = matches.group(2).replace('회', '') if matches.group(2) else ''
                        episode = '' if episode == '0' else episode
                        rebroadcast = True if matches.group(5) else False

                    rating = 0 if program['targetage'] == 'n' else int(program['targetage'])

                    # 추가 정보 가져오기
                    programid = program['programid'].strip()
                    if programid:
                        programdict = getWAVVEProgramDetails(programdict, programid, sess)
                        programdetail = programdict[programid]

                        # TODO: 추가 제목 정보 활용
                        # programtitle = programdetail['programtitle']
                        # log.info('%s / %s' % (programName, programtitle))
                        desc = programdetail['programsynopsis'].strip()
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
            else:
                log.info('EPG 정보가 없거나 없는 채널입니다: %s' % reqChannel)
    except ValueError as e:
        log.error(str(e))
    except requests.exceptions.RequestException as e:
        log.error('요청 중 에러: %s' % str(e))

    # req_sleep
    time.sleep(req_sleep)


def getWAVVEProgramDetails(programdict, programid, sess):
    if programid not in programdict:
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

        try:
            res = sess.get(url, params=param, timeout=timeout)
            res.raise_for_status()
            contentid = res.json()['contentid'].strip()

            url2 = 'https://apis.pooq.co.kr/cf/vod/contents/' + contentid
            # url2 = 'https://apis.pooq.co.kr/vod/contents/' + contentid    # 같은 주소
            res2 = sess.get(url2, params=param, timeout=timeout)
            res2.raise_for_status()
            programdict[programid] = res2.json()
        except ValueError as e:
            log.error(str(e))
        except requests.exceptions.RequestException as e:
            log.error('요청 중 에러: %s' % str(e))

        # req_sleep
        time.sleep(req_sleep)

    return programdict


def epgzip(epginfo):
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
        programdata = {
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
        }
        writeProgram(programdata)
        epg1 = epg2


def writeProgram(programdata):
    ChannelId = programdata['channelId']
    startTime = programdata['startTime']
    endTime = programdata['endTime']
    programName = escape(programdata['programName']).strip()
    subprogramName = escape(programdata['subprogramName']).strip()
    matches = re.match('(.*) \(?(\d+부)\)?', unescape(programName.encode('utf-8', 'ignore')))
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
    for key, value in contentTypeDict.iteritems():
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
    for program in programs:
        startTime = endTime = programName = subprogramName = desc = actors = producers = category = episode = ''
        rebroadcast = False
        programName = program['NM_TITLE'].replace('...', '>').encode('utf-8')
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
        category = program['CD_CATEGORY'] if 'CD_CATEGORY' in program else ''
        rating = int(program['CD_RATING']) if program['CD_RATING'] else 0
        programdata = {
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
        }
        writeProgram(programdata)


def replacement(match, tag):
    if match:
        tag = tag.strip()
        programName = unescape(match.group(1)).replace('<', '&lt;').replace('>', '&gt;').strip()
        programName = '<' + tag + ' class="cont">' + programName
        return programName
    else:
        return ''


Channelfile = os.path.dirname(os.path.abspath(__file__)) + '/Channel.json'
try:
    with open(Channelfile) as f:    # Read Channel Information file
        Channeldatajson = json.load(f)
except EnvironmentError:
    log.error("Channel.json 파일을 읽을 수 없습니다.")
    sys.exit(1)
except ValueError:
    log.error("Channel.json 파일 형식이 잘못되었습니다.")
    sys.exit(1)


Settingfile = os.path.dirname(os.path.abspath(__file__)) + '/epg2xml.json'
try:
    with open(Settingfile) as f:    # Read epg2xml.json file
        Settings = json.load(f)
        MyISP = Settings['MyISP'] if 'MyISP' in Settings else 'ALL'
        MyChannels = Settings['MyChannels'] if 'MyChannels' in Settings else ''
        default_output = Settings['output'] if 'output' in Settings else 'd'
        default_xml_file = Settings['default_xml_file'] if 'default_xml_file' in Settings else 'xmltv.xml'
        default_xml_socket = Settings['default_xml_socket'] if 'default_xml_socket' in Settings else 'xmltv.sock'
        default_icon_url = Settings['default_icon_url'] if 'default_icon_url' in Settings else None
        default_fetch_limit = Settings['default_fetch_limit'] if 'default_fetch_limit' in Settings else '2'
        default_rebroadcast = Settings['default_rebroadcast'] if 'default_rebroadcast' in Settings else 'y'
        default_episode = Settings['default_episode'] if 'default_episode' in Settings else 'y'
        default_verbose = Settings['default_verbose'] if 'default_verbose' in Settings else 'n'
        default_xmltvns = Settings['default_xmltvns'] if 'default_xmltvns' in Settings else 'n'
except EnvironmentError:
    log.error("epg2xml.json 파일을 읽을 수 없습니다.")
    sys.exit(1)
except ValueError:
    log.error("epg2xml.json 파일 형식이 잘못되었습니다.")
    sys.exit(1)

parser = argparse.ArgumentParser(description='EPG 정보를 출력하는 방법을 선택한다')
argu1 = parser.add_argument_group(description='IPTV 선택')
argu1.add_argument('-i', dest='MyISP', choices=['ALL', 'KT', 'LG', 'SK'], help='사용하는 IPTV : ALL, KT, LG, SK', default=MyISP)
argu2 = parser.add_mutually_exclusive_group()
argu2.add_argument('-v', '--version', action='version', version='%(prog)s version : ' + __version__)
argu2.add_argument('-d', '--display', action='store_true', help='EPG 정보 화면출력')
argu2.add_argument('-o', '--outfile', metavar=default_xml_file, nargs='?', const=default_xml_file, help='EPG 정보 저장')
argu2.add_argument('-s', '--socket', metavar=default_xml_socket, nargs='?', const=default_xml_socket, help='xmltv.sock(External: XMLTV)로 EPG정보 전송')
argu3 = parser.add_argument_group('추가옵션')
argu3.add_argument('--icon', dest='icon', metavar="http://www.example.com/icon", help='채널 아이콘 URL, 기본값: ' + default_icon_url, default=default_icon_url)
argu3.add_argument('-l', '--limit', dest='limit', type=int, metavar="1-7", choices=range(1, 8), help='EPG 정보를 가져올 기간, 기본값: ' + str(default_fetch_limit), default=default_fetch_limit)
argu3.add_argument('--rebroadcast', dest='rebroadcast', metavar='y, n', choices='yn', help='제목에 재방송 정보 출력', default=default_rebroadcast)
argu3.add_argument('--episode', dest='episode', metavar='y, n', choices='yn', help='제목에 회차 정보 출력', default=default_episode)
argu3.add_argument('--verbose', dest='verbose', metavar='y, n', choices='yn', help='EPG 정보 추가 출력', default=default_verbose)

args = parser.parse_args()
if args.MyISP:
    MyISP = args.MyISP
if args.display:
    default_output = "d"
elif args.outfile:
    default_output = "o"
    default_xml_file = args.outfile
elif args.socket:
    default_output = "s"
    default_xml_socket = args.socket
if args.icon:
    default_icon_url = args.icon
if args.limit:
    default_fetch_limit = args.limit
if args.rebroadcast:
    default_rebroadcast = args.rebroadcast
if args.episode:
    default_episode = args.episode
if args.verbose:
    default_verbose = args.verbose

if MyISP:
    if not any(MyISP in s for s in ['ALL', 'KT', 'LG', 'SK']):
        log.error("MyISP는 ALL, KT, LG, SK만 가능합니다.")
        sys.exit(1)
else:
    log.error("epg2xml.json 파일의 MyISP항목이 없습니다.")
    sys.exit(1)

if default_output:
    if any(default_output in s for s in ['d', 'o', 's']):
        if default_output == "d":
            output = "display"
        elif default_output == "o":
            output = "file"
        elif default_output == 's':
            output = "socket"
    else:
        log.error("default_output는 d, o, s만 가능합니다.")
        sys.exit(1)
else:
    log.error("epg2xml.json 파일의 output항목이 없습니다.")
    sys.exit(1)

IconUrl = default_icon_url

if default_rebroadcast:
    if not any(default_rebroadcast in s for s in ['y', 'n']):
        log.error("default_rebroadcast는 y, n만 가능합니다.")
        sys.exit(1)
    else:
        addrebroadcast = default_rebroadcast
else:
    log.error("epg2xml.json 파일의 default_rebroadcast항목이 없습니다.")
    sys.exit(1)

if default_episode:
    if not any(default_episode in s for s in ['y', 'n']):
        log.error("default_episode는 y, n만 가능합니다.")
        sys.exit(1)
    else:
        addepisode = default_episode
else:
    log.error("epg2xml.json 파일의 default_episode항목이 없습니다.")
    sys.exit(1)

if default_verbose:
    if not any(default_verbose in s for s in ['y', 'n']):
        log.error("default_verbose는 y, n만 가능합니다.")
        sys.exit(1)
    else:
        addverbose = default_verbose
else:
    log.error("epg2xml.json 파일의 default_verbose항목이 없습니다.")
    sys.exit(1)

if default_xmltvns:
    if not any(default_xmltvns in s for s in ['y', 'n']):
        log.error("default_xmltvns는 y, n만 가능합니다.")
        sys.exit(1)
    else:
        addxmltvns = default_xmltvns
else:
    log.error("epg2xml.json 파일의 default_verbose항목이 없습니다.")
    sys.exit(1)

if default_fetch_limit:
    if not any(str(default_fetch_limit) in s for s in ['1', '2', '3', '4', '5', '6', '7']):
        log.error("default_fetch_limit 는 1, 2, 3, 4, 5, 6, 7만 가능합니다.")
        sys.exit(1)
    else:
        period = int(default_fetch_limit)
else:
    log.error("epg2xml.json 파일의 default_fetch_limit항목이 없습니다.")
    sys.exit(1)

if output == "file":
    if default_xml_file:
        sys.stdout = codecs.open(default_xml_file, 'w+', encoding='utf-8')
    else:
        log.error("epg2xml.json 파일의 default_xml_file항목이 없습니다.")
        sys.exit(1)
elif output == "socket":
    if default_xml_socket:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(default_xml_socket)
            sockfile = sock.makefile('w+')
            sys.stdout = sockfile
        except socket.error:
            sys.exit('xmltv.sock 파일을 찾을 수 없습니다.')
    else:
        log.error("epg2xml.json 파일의 default_xml_socket항목이 없습니다.")
        sys.exit(1)
getEpg()
