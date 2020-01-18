#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import print_function
import imp
import os
import sys
import json
from datetime import datetime, timedelta, date
import codecs
import socket
import re
from xml.sax.saxutils import escape, unescape
import argparse
from functools import partial
import time

try:
    imp.find_module('bs4')
    from bs4 import BeautifulSoup, SoupStrainer
except ImportError:
    print("Error: ", "BeautifulSoup 모듈이 설치되지 않았습니다.", file=sys.stderr)
    sys.exit()
try:
    imp.find_module('lxml')
    from lxml import html
except ImportError:
    print("Error: ", "lxml 모듈이 설치되지 않았습니다.", file=sys.stderr)
    sys.exit()
try:
    imp.find_module('requests')
    import requests
except ImportError:
    print("Error: ", "requests 모듈이 설치되지 않았습니다.", file=sys.stderr)
    sys.exit()

reload(sys)
sys.setdefaultencoding('utf-8')

if not sys.version_info[:2] == (2, 7):
    print("Error: ", "python 2.7 버전이 필요합니다.", file=sys.stderr)
    sys.exit()

# Set variable
__version__ = '1.2.7p1'
debug = False
today = date.today()
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
timeout = 5
channel_sleep = 1
htmlparser = 'lxml'
CHANNEL_ERROR = ' 존재하지 않는 채널입니다.'
CONTENT_ERROR = ' EPG 정보가 없습니다.'
HTTP_ERROR = ' EPG 정보를 가져오는데 문제가 있습니다.'
SOCKET_ERROR = 'xmltv.sock 파일을 찾을 수 없습니다.'
JSON_FILE_ERROR = 'json 파일을 읽을 수 없습니다.'
JSON_SYNTAX_ERROR = 'json 파일 형식이 잘못되었습니다.'


# Get epg data
def getEpg():
    Channelfile = os.path.dirname(os.path.abspath(__file__)) + '/Channel.json'
    ChannelInfos = []
    try:
        with open(Channelfile) as f:    # Read Channel Information file
            Channeldatajson = json.load(f)
    except EnvironmentError:
        printError("Channel." + JSON_FILE_ERROR)
        sys.exit()
    except ValueError:
        printError("Channel." + JSON_SYNTAX_ERROR)
        sys.exit()
    print('<?xml version="1.0" encoding="UTF-8"?>')
    print('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
    print('<tv generator-info-name="epg2xml ' + __version__ + '">')

    # My Channel 정의
    MyChannelInfo = [int(ch.strip()) for ch in MyChannels.split(',') if ch]
    # MyChannelInfo = [ch for ch in range(500)]       # debug

    for Channeldata in Channeldatajson:     # Get Channel & Print Channel info
        if Channeldata['Id'] in MyChannelInfo:
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
                print('    <display-name>%s</display-name>' % ChannelNumber + ' ' + ChannelISPName)
            elif MyISP == "ALL":
                print('    <display-name>%s</display-name>' % ChannelName)
            if IconUrl:
                print('    <icon src="%s/%s.png" />' % (IconUrl, ChannelId))
            else:
                print('    <icon src="%s" />' % ChannelIconUrl)
            print('  </channel>')

    # Print Program Information
    for ChannelInfo in ChannelInfos:
        ChannelId = ChannelInfo[0]
        ChannelName = ChannelInfo[1]
        ChannelSource = ChannelInfo[2]
        ChannelServiceId = ChannelInfo[3]
        if debug:
            printLog(ChannelName + ' 채널 EPG 데이터를 가져오고 있습니다.')
        if ChannelSource == 'KT':
            GetEPGFromKT(ChannelInfo)
        elif ChannelSource == 'LG':
            GetEPGFromLG(ChannelInfo)
        # elif ChannelSource == 'SK':
        #     time.sleep(channel_sleep)
        #     GetEPGFromSK(ChannelInfo)
        elif ChannelSource == 'SKB':
            time.sleep(channel_sleep)
            GetEPGFromSKB(ChannelInfo)
        if ChannelSource == 'NAVER':
            GetEPGFromNaver(ChannelInfo)
    SKChannelInfos = [info for info in ChannelInfos if info[2] == 'SK']
    GetEPGFromSK_Multi(SKChannelInfos)

    print('</tv>')


def GetEPGFromKT(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId = ChannelInfo[3]
    url = 'https://tv.kt.com/tv/channel/pSchedule.asp'
    referer = 'https://tv.kt.com/'

    epginfo = []
    for k in range(period):
        day = today + timedelta(days=k)
        params = {
            'ch_type': '1',
            'view_type': '1',
            'service_ch_no': ServiceId,
            'seldate': day.strftime('%Y%m%d')
        }
        try:
            response = requests.post(url, data=params, headers={'User-Agent': ua, 'Referer': referer}, timeout=timeout)
            response.raise_for_status()
            html_data = response.content
            data = unicode(html_data, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
            strainer = SoupStrainer('tbody')
            soup = BeautifulSoup(data, htmlparser, parse_only=strainer, from_encoding='utf-8')
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
                            epginfo.append([ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                            time.sleep(0.001)
            else:
                if debug:
                    printError(ChannelName + CONTENT_ERROR)
                # 오늘 없으면 내일도 없는 채널로 간주
                time.sleep(0.001)
                break
        except requests.exceptions.RequestException as e:
            if debug:
                printError(ChannelName + str(e))
    if epginfo:
        epgzip(epginfo)


def GetEPGFromLG(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId = ChannelInfo[3]
    url = 'http://www.uplus.co.kr/css/chgi/chgi/RetrieveTvSchedule.hpi'
    referer = 'http://www.uplus.co.kr/css/chgi/chgi/RetrieveTvContentsMFamily.hpi'

    epginfo = []
    for k in range(period):
        day = today + timedelta(days=k)
        params = {'chnlCd': ServiceId, 'evntCmpYmd': day.strftime('%Y%m%d')}
        try:
            response = requests.post(url, data=params, headers={'User-Agent': ua, 'Referer': referer}, timeout=timeout)
            response.raise_for_status()
            html_data = response.content
            data = unicode(html_data, 'euc-kr', 'ignore').encode('utf-8', 'ignore')
            data = data.replace('<재>', '&lt;재&gt;').replace(' [..', '').replace(' (..', '')
            strainer = SoupStrainer('table')
            soup = BeautifulSoup(data, htmlparser, parse_only=strainer, from_encoding='utf-8')
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
                        epginfo.append([ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                        time.sleep(0.001)
            else:
                if debug:
                    printError(ChannelName + CONTENT_ERROR)
                # 오늘 없으면 내일도 없는 채널로 간주
                time.sleep(0.001)
                break
        except requests.exceptions.RequestException as e:
            if debug:
                printError(ChannelName + str(e))
    if epginfo:
        epgzip(epginfo)


def GetEPGFromSK(ChannelInfo):
    ChannelName = ChannelInfo[1]
    ServiceId = ChannelInfo[3]
    url = 'http://mapp.btvplus.co.kr/sideMenu/live/IFGetData.do'
    referer = 'http://mapp.btvplus.co.kr/channelFavor.do'

    for k in range(period):
        params = {
            'variable': 'IF_LIVECHART_DETAIL',
            'o_date': (today+timedelta(days=k)).strftime('%Y%m%d'),
            'svc_ids': str(ServiceId),
        }
        try:
            response = requests.post(url, data=params, headers={'User-Agent': ua, 'Referer': referer}, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if data['result'] != 'OK':
                if debug:
                    printError(ChannelName + ' ' + data['reason'])
                time.sleep(0.001)
                break

            if len(data['ServiceInfoArray']) == 0:
                if debug:
                    printError(ChannelName + CHANNEL_ERROR)
            else:
                programs = data['ServiceInfoArray'][0]['EventInfoArray']
                writeSKPrograms(ChannelInfo, programs)
        except ValueError:
            if debug:
                printError(ChannelName + CONTENT_ERROR)
        except requests.exceptions.RequestException as e:
            if debug:
                printError(ChannelName + str(e))


def GetEPGFromSK_Multi(ChannelInfos):
    url = 'http://mapp.btvplus.co.kr/sideMenu/live/IFGetData.do'
    referer = 'http://mapp.btvplus.co.kr/channelFavor.do'

    for k in range(period):
        params = {
            'variable': 'IF_LIVECHART_DETAIL',
            'o_date': (today+timedelta(days=k)).strftime('%Y%m%d'),
            'svc_ids': '|'.join([info[3] for info in ChannelInfos]),
        }
        try:
            response = requests.post(url, data=params, headers={'User-Agent': ua, 'Referer': referer}, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if data['result'] != 'OK':
                if debug:
                    printError(data['reason'])
                time.sleep(0.001)
                break

            channels = {x['ID_SVC']: x['EventInfoArray'] for x in data['ServiceInfoArray']}
            for ChannelInfo in ChannelInfos:
                ChannelName = ChannelInfo[1]
                ServiceId = ChannelInfo[3]
                if ServiceId in channels:
                    programs = channels[ServiceId]
                    writeSKPrograms(ChannelInfo, programs)
                else:
                    if debug:
                        printError(ChannelName + CHANNEL_ERROR)
                    time.sleep(0.001)
                    continue
        except ValueError:
            if debug:
                printError(CONTENT_ERROR)
        except requests.exceptions.RequestException as e:
            if debug:
                printError(HTTP_ERROR + str(e))


def GetEPGFromSKB(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId = ChannelInfo[3]
    url = 'http://m.skbroadband.com/content/realtime/Channel_List.do'
    epginfo = []
    for k in range(period):
        day = today + timedelta(days=k)
        params = {'key_depth2': ServiceId, 'key_depth3': day.strftime('%Y%m%d')}
        try:
            response = requests.get(url, params=params, headers={'User-Agent': ua, 'Referer': url}, timeout=timeout)
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
                    epginfo.append([ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                    time.sleep(0.001)
            else:
                if debug:
                    printError(ChannelName + CONTENT_ERROR)
                # 오늘 없으면 내일도 없는 채널로 간주
                time.sleep(0.001)
                break
        except requests.exceptions.RequestException as e:
            if debug:
                printError(ChannelName + str(e))
    if epginfo:
        epgzip(epginfo)


def GetEPGFromNaver(ChannelInfo):
    ChannelId = ChannelInfo[0]
    ChannelName = ChannelInfo[1]
    ServiceId = ChannelInfo[3]
    epginfo = []
    url = 'https://m.search.naver.com/p/csearch/content/nqapirender.nhn'
    for k in range(period):
        day = today + timedelta(days=k)
        params = {
            'callback': 'epg',
            'key': 'SingleChannelDailySchedule',
            'where': 'm',
            'pkid': '66',
            'u1': ServiceId,
            'u2': day.strftime('%Y%m%d')
        }
        try:
            response = requests.get(url, params=params, headers={'User-Agent': ua}, timeout=timeout)
            response.raise_for_status()
            json_data = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "", response.text.split("epg(")[1].strip(");").strip())
            try:
                data = json.loads(json_data, encoding='utf-8')
                if data['statusCode'] != 'SUCCESS':
                    if debug:
                        printError(ChannelName + CONTENT_ERROR)
                    time.sleep(0.001)
                    break

                for ul in data['dataHtml']:
                    strainer = SoupStrainer('ul', {'class': 'ind_list'})
                    soup = BeautifulSoup(ul, htmlparser, parse_only=strainer)
                    html = soup.find_all('li', {'class': 'list'}) if soup.find('ul', {'class': 'ind_list'}) else ''
                    if html:
                        for row in html:
                            for cell in [row.find_all('div')]:
                                startTime = endTime = programName = subprogramName = desc = actors = producers = category = episode = ''
                                rebroadcast = False
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
                                epginfo.append([ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating])
                                time.sleep(0.001)
                    else:
                        if debug:
                            printError(ChannelName + CONTENT_ERROR)

            except ValueError:
                if debug:
                    printError(ChannelName + CONTENT_ERROR)
        except requests.RequestException as e:
            if debug:
                printError(ChannelName + str(e))
    if epginfo:
        epgzip(epginfo)


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
    print('  </programme>')


def writeSKPrograms(ChannelInfo, programs):
    ChannelId = ChannelInfo[0]
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
        time.sleep(0.001)   # 빼도 되지 않을까?


def printLog(*args):
    print(*args, file=sys.stderr)


def printError(*args):
    print("Error:", *args, file=sys.stderr)


def replacement(match, tag):
    if match:
        tag = tag.strip()
        programName = unescape(match.group(1)).replace('<', '&lt;').replace('>', '&gt;').strip()
        programName = '<' + tag + ' class="cont">' + programName
        return programName
    else:
        return ''


Settingfile = os.path.dirname(os.path.abspath(__file__)) + '/epg2xml.json'
try:
    with open(Settingfile) as f:    # Read Channel Information file
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
    printError("epg2xml." + JSON_FILE_ERROR)
    sys.exit()
except ValueError:
    printError("epg2xml." + JSON_SYNTAX_ERROR)
    sys.exit()

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
        printError("MyISP는 ALL, KT, LG, SK만 가능합니다.")
        sys.exit()
else:
    printError("epg2xml.json 파일의 MyISP항목이 없습니다.")
    sys.exit()

if default_output:
    if any(default_output in s for s in ['d', 'o', 's']):
        if default_output == "d":
            output = "display"
        elif default_output == "o":
            output = "file"
        elif default_output == 's':
            output = "socket"
    else:
        printError("default_output는 d, o, s만 가능합니다.")
        sys.exit()
else:
    printError("epg2xml.json 파일의 output항목이 없습니다.")
    sys.exit()

IconUrl = default_icon_url

if default_rebroadcast:
    if not any(default_rebroadcast in s for s in ['y', 'n']):
        printError("default_rebroadcast는 y, n만 가능합니다.")
        sys.exit()
    else:
        addrebroadcast = default_rebroadcast
else:
    printError("epg2xml.json 파일의 default_rebroadcast항목이 없습니다.")
    sys.exit()

if default_episode:
    if not any(default_episode in s for s in ['y', 'n']):
        printError("default_episode는 y, n만 가능합니다.")
        sys.exit()
    else:
        addepisode = default_episode
else:
    printError("epg2xml.json 파일의 default_episode항목이 없습니다.")
    sys.exit()

if default_verbose:
    if not any(default_verbose in s for s in ['y', 'n']):
        printError("default_verbose는 y, n만 가능합니다.")
        sys.exit()
    else:
        addverbose = default_verbose
else:
    printError("epg2xml.json 파일의 default_verbose항목이 없습니다.")
    sys.exit()

if default_xmltvns:
    if not any(default_xmltvns in s for s in ['y', 'n']):
        printError("default_xmltvns는 y, n만 가능합니다.")
        sys.exit()
    else:
        addxmltvns = default_xmltvns
else:
    printError("epg2xml.json 파일의 default_verbose항목이 없습니다.")
    sys.exit()

if default_fetch_limit:
    if not any(str(default_fetch_limit) in s for s in ['1', '2', '3', '4', '5', '6', '7']):
        printError("default_fetch_limit 는 1, 2, 3, 4, 5, 6, 7만 가능합니다.")
        sys.exit()
    else:
        period = int(default_fetch_limit)
else:
    printError("epg2xml.json 파일의 default_fetch_limit항목이 없습니다.")
    sys.exit()

if output == "file":
    if default_xml_file:
        sys.stdout = codecs.open(default_xml_file, 'w+', encoding='utf-8')
    else:
        printError("epg2xml.json 파일의 default_xml_file항목이 없습니다.")
        sys.exit()
elif output == "socket":
    if default_xml_socket:
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(default_xml_socket)
            sockfile = sock.makefile('w+')
            sys.stdout = sockfile
        except socket.error:
            printError(SOCKET_ERROR)
            sys.exit()
    else:
        printError("epg2xml.json 파일의 default_xml_socket항목이 없습니다.")
        sys.exit()
getEpg()
