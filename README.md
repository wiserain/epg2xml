# 공지
~~epg2xml은 1.2.6 버전을 마지막으로 업데이트가 이루어 지지 않습니다.
3월 31일 이후로 리포지터리 삭제 예정입니다.~~

wonipapa/epg2xml을 이어받아 관리하고 있습니다.

1.2.7 이후로 python과 php가 많이 다릅니다. 참고하세요.

### WAVVE EPG 사용법

1.2.7p2 이후로 추가된 WAVVE EPG의 사용법은 기존의 것과 약간 다릅니다. Channel.json에 다음과 같이 Source와 ServiceId를 주면 그 채널을 EPG로 만듭니다.

```json
{ "Source": "WAVVE", "ServiceId": "K01" },
```

그 외 Id, Name, Icon_url은 직접 Channel.json에서 지정하지 않으면 자동으로 정해집니다. Id는 pooq|ServiceId가 되고 Name과 Icon_url은 WAVVE api가 주는 값을 기본값으로 갖습니다.

어떤 채널이 서비스 되고 있는지 ServiceId를 알기 어려우므로 일단 한 채널만 올라가 있는 여기의 Channel.json로 epg2xml을 한번 실행하면 같은 폴더에 WAVVE 채널의 템플릿인 Channel_WAVVE.json이 생성됩니다. 내용은 대략 아래와 같습니다.

```json
[
    {
        "last update": "2020/02/16 05:53:31",
        "total": 98
    },
    {
        "WAVVE Name": "KBS 1TV",
        "Icon_url": "https://img.pooq.co.kr/BMS/Channelimage30/image/KBS-1TV-1.jpg",
        "Source": "WAVVE",
        "ServiceId": "K01"
    },
    {
        "WAVVE Name": "KBS 2TV",
        "Icon_url": "https://img.pooq.co.kr/BMS/Channelimage30/image/KBS-2TV-1.jpg",
        "Source": "WAVVE",
        "ServiceId": "K02"
    },
    {
        "WAVVE Name": "MBC",
        "Icon_url": "https://img.pooq.co.kr/BMS/Channelimage30/image/M01.jpg",
        "Source": "WAVVE",
        "ServiceId": "M01"
    }
]
```

첫번째로 생성일과 전체 채널의 갯수가 명시되고 그 아래로 서비스되는 채널의 정보가 나열됩니다. 참고로 WAVVE는 자주 새로운 채널이 추가되고 있던 채널이 삭제될 뿐만 아니라 가져오는 시간에 따라 api에서 제공여부가 달라져 전체 채널수가 자주 변하는 편입니다. 이 내용은 사용자가 원하는 채널을 Channel.json에 추가하기 쉽게 하기 위한 것이며 실제 적용은 현재 Channel.json에 있는 처럼 직접 입력해주어야 합니다. (화이트리스트 방식) 예를 들어 위 세개의 채널을 추가하고 싶다면 Channel.json에 아래와 같이 추가해주면 됩니다.

```json
[
{ "Source": "WAVVE", "ServiceId": "K01" },
{ "Source": "WAVVE", "ServiceId": "K02" },
{ "Source": "WAVVE", "ServiceId": "M01" }
]
```

앞에서 말했듯이 tvheadend에서 인식 가능하게 하는 Id나 Name 필드 그리고 Icon_url은 직접 입력하지 않으면 기본값이 들어갑니다. 

- 파이썬 버전만 WAVVE EPG가 가능합니다. PHP 버전 pull request 환영합니다.
- Plex 연동시 프로그램 포스터 입력이 됩니다. 그래서 조금 느립니다.
- 너무 자주 요청하지는 마세요. 하루에 1~2번이면 충분하지 않을까 싶습니다.
- 채널 템플릿은 SK도 동일하게 Channel_SK.json로 출력 됩니다.
- 정보가 많고 적은 요청에 한 번에 가져와서 서버에 부담이 적은 SK를 기본으로 쓰고 WAVVE를 부가적으로 추가해서 쓰는 것을 추천합니다.

조금 더 나은 사용을 고민해보겠습니다. 좋은 방안 있으면 issue로 알려주세요.

# EPG2XML
이 프로그램은 EPG(Electronic Program Guide)를 웹상의 여러 소스에서 가져와서 XML로 출력하는 프로그램으로 python2.7 및 php5.4.45 이상에서 사용 가능하도록 제작되었다.  
python3과 php 5.4.45 이하에서는 정상적인 작동을 보장하지 못한다.  또한 외부의 소스를 분석하여 EPG 정보를 가공하여 보여주는 것이므로 외부 소스 사이트가 변경되거나 삭제되면 문제가 발생할 수 있다.  

## 개발자 후원하기
https://www.facebook.com/chericface  
페이스북을 사용하신다면 개발자 후원하는 방법이라고 생각해주시고 위의 링크 들어가서 좋아요 눌러주시면 감사하겠습니다.
제가 관련된 곳에서 운영하는 페이스북인데 아직 초기라서 사람이 많이 없습니다. 화학공학 및 소재 관련 사이트입니다.
감사합니다.  

## 필요 모듈

### epg2xml.py
BeautifulSoup(bs4), lxml, requests 모듈이 추가로 필요하다.  
설치 OS별로 모듈을 설치하기 위한 사전 설치 방법이 다를 수도 있으므로 검색해서 설치하도록 한다.  
pip install beautifulsoup4, pip install lxml, pip install requests 로 추가할 수 있다.  
* easy_install로 설치시 모듈이 인식되지 않는 경우가 있으므로 pip로 설치하기를 권한다.  

### epg2xml.php
json, dom, mbstring, openssl, curl 모듈이 필요하다. 일반적으로 PHP가 설치되어 있다면 대부분 설치되어 있는 모듈이나 설치되어 있지 않을 경우 추가로 설치해야 한다.

### epg2xml-web.php
epg2xml.php와 동일하다.

## 설정방법
### epg2xml.json
epg2xml.json 안의 항목이 설정 가능한 항목이다. 
```bash
MyISP : 사용하는 ISP를 넣는다 .(ALL, KT, LG, SK가 사용가능하다)
MyChannels : EPG 정보를 가져오고자 하는 채널 ID를 넣는다. ("1, 2, 3, 4" 또는 "1,2,3,4")
output : EPG 정보 출력방향 (d: 화면 출력, o: 파일 출력, s:소켓출력)
default_icon_url : 채널별 아이콘이 있는 url을 설정할 수 있다. 아이콘의 이름은 json 파일에 있는 Id.png로 기본설정되어 있다.
default_rebroadcast : 제목에 재방송 정보 출력
default_episode : 제목에 회차정보 출력
default_verbose : EPG 정보 상세 출력
default_xmltvns : 에피소드 정보 표시 방법
default_fetch_limit : EPG 데이터 가져오는 기간.
default_xml_filename : EPG 저장시 기본 저장 이름으로 tvheadend 서버가 쓰기가 가능한 경로로 설정해야 한다.
default_xml_socket   : External XMLTV 사용시 xmltv.sock가 있는 경로로 설정해준다.
```

### Channel.json
Channel.json 파일의 최신버전은 https://github.com/wonipapa/Channel.json 에서 다운받을 수 있다.  
Channel.json 파일을 텍스트 편집기로 열어보면 각채널별 정보가 들어 있다.  

## 옵션 소개
### epg2xml.py, epg2xml.php 옵션
실행시 사용가능한 인수는 --help 명령어로 확인이 가능하다.  
epg2xml.json의 설정을 옵션의 인수를 이용하여 변경할 수 있다.  
```bash
-h --help : 도움말 출력
--version : 버전을 보여준다.
-i : IPTV 선택 (ALL, KT, SK, LG 선택가능) ex) -i KT
-d --display : EPG 정보를 화면으로 보여준다.
-o --outfile : EPG 정보를 파일로 저장한다. ex) -o xmltv.xml
-s --socket  : EPG 정보를 xmltv.sock로 전송한다. ex) -s /var/run/xmltv.sock
-l --limit : EPG 정보 가져올 기간으로 기본값은 2일이며 최대 7일까지 설정 가능하다. ex) -l 2
--icon : 채널 icon 위치 URL ex) --icon http://www.example.com
--rebroadcast : 제목에 재방송정보 표기 ex) --rebroadcast y
--episode : 제목에 회차정보 표기 ex) --episode y
--verbose : EPG 정보 상세하게 표기 ex) --verbose y
```

### epg2xml-web.php 옵션
실행시 사용가능한 인수는 epg2xml.php?help 명령어로 확인이 가능하다.  
epg2xml.json의 설정을 옵션의 인수를 이용하여 변경할 수 있다.  
ex : http://domain/epg2xml.php?i=ALL&l=2

## 사용방법

### tv_grab_file 사용시 (https://github.com/nurtext/tv_grab_file_synology)
tv_grab_file 안의 cat xmltv.xml 또는 wget 이 있는 부분을 아래와 같이 변경해준다.  
python 경로와 php의 경로는 /usr/bin에 있고, epg2xml 파일은 /home/hts에 있는 것으로 가정했다.  
이 경우 epg2xml.json의 output을 d로 해야 한다.

#### PYTHON의 경우
```bash
/usr/bin/python /home/hts/epg2xml.py  # 또는
/home/hts/epg2xml.py
```

#### PHP CLI의 경우
```bash
/usr/bin/php /home/hts/epg2xml.php  # 또는
/home/hts/epg2xml.php
```

#### PHP WEB의 경우
```bash
wget -O - http://www.examle.com/epg2xml-web.php   # 또는
wget -O - http://www.example.com/epg2xml-web.php?i=ALL&l=2
```

### XMLTV SOCKET 사용시
**xmltv.sock 사용시 socat 등을 사용하지 않고 바로 socket에 쓰기가 가능하다**

#### PYTHON의 경우
```bash
/usr/bin/python /home/hts/epg2xml.py  # 또는
/home/hts/epg2xml.py
```

#### PHP CLI의 경우
```bash
/usr/bin/php /home/hts/epg2xml.php  # 또는
/home/hts/epg2xml.php
```

#### PHP WEB의 경우
php web 버전은 xmltv.sock을 지원하지 않는다.

## 라이센스
BSD 3-clause "New" or "Revised" License

## [변경사항](https://github.com/wiserain/epg2xml/blob/master/CHANGELOG.md)
