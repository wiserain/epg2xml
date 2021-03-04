# EPG2XML

웹상의 여러 소스를 취합하여 XML 규격의 EPG(Electronic Program Guide)를 만드는 프로그램

- 2018년 3월 31일 이후로 삭제된 wonipapa/epg2xml을 fork하여 관리하고 있습니다. 기본적인 내용은 기존의 [README](https://github.com/wiserain/epg2xml/blob/master/OLDME.md)를 참고하세요.

- 1.2.7 이후로 python과 php가 동일한 결과물을 보장하지 않습니다. (php 마지막 버전은 1.2.7p1)

- 1.2.8 이후로 python2.7에 대한 지원은 종료 되었습니다. [python2.7 마지막 버전](https://github.com/wiserain/epg2xml/tree/1.2.8py2)

- 1.5.2 이후로 v1에 대한 지원은 종료 되었습니다. [새로운 저장소](https://github.com/epg2xml/epg2xml)에서 v2로 개발을 이어가겠습니다.

## 지원 소스 및 각각의 특징

| 소스  | 채널 템플릿  | 프로그램 포스터 | 요청수  | 소요시간 | 정보량 | 추천 |
|---|---|---|---|---|---|---|
| KT  | :heavy_check_mark: | :x: | ```#channels * #days```  | :rage::rage::rage: | :smiley::smiley: | 
| LG  | :x:  | :x:| ```#channels * #days```  | :rage::rage::rage: | :smiley::smiley: |
| ~~SK~~<sup id="a1">[1](#f1)</sup>  | :heavy_check_mark:  | :x: | ~~```#days```~~  | ~~:rage:~~ | ~~:smiley::smiley::smiley:~~ | ~~:+1::+1::+1:~~ |
| SKB  | :heavy_check_mark: | :x:  | ```#channels * #days```  | :rage::rage::rage::rage: | :smiley::smiley: |
| NAVER  | :x: | :x: | ```#channels * #days``` | :rage::rage::rage: | :smiley: | 
| WAVVE  | :heavy_check_mark: | :x:<sup id="a2">[2](#f2)</sup> | ```1```  |  | :smiley::smiley: |:+1: |
| TVING  | :heavy_check_mark: | :heavy_check_mark: | ```#channels/20 * #days * 24/3```  | :rage::rage: | :smiley::smiley::smiley::smiley: | :+1::+1: |

<sup><b id="f1">1</b> SK btv 사이트 개편으로 현재 지원되지 않습니다. 다른 소스로 변경하여 사용하세요. [↩](#a1)</sup>

<sup><b id="f2">2</b> 프로그램 포스터와 함께 추가 정보를 가져오려면 ```epg2xml.json```의 ```WAVVE_more_details``` 항목을 참조. [↩](#a2)</sup>

~~정보가 많고 적은 요청으로 한 번에 가져와서 서버에 부담이 적은 SK를 기본으로 쓰고~~ 부족한 채널은 다른 소스에서 추가해 쓰는 것을 권합니다.

## 사용법

### WAVVE EPG 사용법

1.2.7p2 이후로 추가된 WAVVE EPG의 사용법은 기존의 것과 약간 다릅니다. Channel.json에 다음과 같이 Source와 ServiceId를 주면 그 채널을 EPG로 만듭니다.

```json
{ "Source": "WAVVE", "ServiceId": "K01" },
```

그 외 Id, Name, Icon_url은 직접 Channel.json에서 지정하지 않으면 자동으로 정해집니다. Id는 wavve|ServiceId가 되고 Name과 Icon_url은 WAVVE api가 주는 값을 기본값으로 갖습니다.

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

첫번째로 생성일과 전체 채널의 갯수가 명시되고 그 아래로 서비스되는 채널의 정보가 나열됩니다. 참고로 WAVVE는 자주 새로운 채널이 추가되고 있던 채널이 삭제될 뿐만 아니라 가져오는 시간에 따라 api에서 제공여부가 달라져 전체 채널수가 자주 변하는 편입니다. 이 내용은 사용자가 원하는 채널을 Channel.json에 추가하기 쉽게 하기 위한 것이며 실제 적용은 현재 Channel.json와 같이 직접 입력해주어야 합니다. (화이트리스트 방식) 예를 들어 위 세개의 채널을 추가하고 싶다면 Channel.json에 아래와 같이 추가해주면 됩니다.

```json
[
{ "Source": "WAVVE", "ServiceId": "K01" },
{ "Source": "WAVVE", "ServiceId": "K02" },
{ "Source": "WAVVE", "ServiceId": "M01" }
]
```

앞에서 말했듯이 tvheadend에서 인식 가능하게 하는 Id나 Name 필드 그리고 Icon_url은 직접 입력하지 않으면 기본값이 들어갑니다. 

- 파이썬 버전만 WAVVE EPG가 가능합니다. PHP 버전 pull request 환영합니다.
- ~~Plex 연동시 프로그램 포스터 입력이 됩니다. 그래서 조금 느립니다.~~ 포스터 입력은 ```epg2xml.json```의 ```WAVVE_more_details``` 항목을 참조
- 너무 자주 요청하지는 마세요. 하루에 1~2번이면 충분하지 않을까 싶습니다.

조금 더 나은 사용을 고민해보겠습니다. 좋은 방안 있으면 issue로 알려주세요.

### TVING 사용법

WAVVE와 동일합니다.

## 라이센스
BSD 3-clause "New" or "Revised" License

## [변경사항](https://github.com/wiserain/epg2xml/blob/master/CHANGELOG.md)
