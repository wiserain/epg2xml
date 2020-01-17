# 공지
~~epg2xml은 1.2.6 버전을 마지막으로 업데이트가 이루어 지지 않습니다.
3월 31일 이후로 리포지터리 삭제 예정입니다.~~

wonipapa/epg2xml을 이어받아 관리하고 있습니다.

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
