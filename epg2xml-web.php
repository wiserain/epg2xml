<?php
@mb_internal_encoding("UTF-8");
@date_default_timezone_set('Asia/Seoul');
error_reporting(E_ALL ^ E_NOTICE);
@set_time_limit(0);
define("VERSION", "1.2.6");
$debug = False;
$ua = "'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116'";
$timeout = 5;
$req_timeout = 10;
define("CHANNEL_ERROR", " 존재하지 않는 채널입니다.");
define("CONTENT_ERROR ", " EPG 정보가 없습니다.");
define("HTTP_ERROR", " EPG 정보를 가져오는데 문제가 있습니다.");
define("DISPLAY_ERROR", "EPG를 출력할 수 없습니다.");
define("FILE_ERROR", "XML 파일을 만들수 없습니다.");
define("SOCKET_ERROR", "소켓 파일을 찾을 수 없습니다.");
define("JSON_FILE_ERROR", "json 파일이 없습니다.");
define("JSON_SYNTAX_ERROR",  "json 파일 형식이 잘못되었습니다.");

if(version_compare(PHP_VERSION, '5.4.45','<')) :
    printError("PHP 버전은 5.4.45 이상이어야 합니다.");
    printError("현재 PHP 버전은 ".PHP_VERSION." 입니다.");
    exit;
endif;
if (!extension_loaded('json')) :
    printError("json 모듈이 설치되지 않았습니다.");
    exit;
endif;
if (!extension_loaded('dom')) :
    printError("dom 모듈이 설치되지 않았습니다.");
    exit;
endif;
if (!extension_loaded('mbstring')) :
    printError("mbstring 모듈이 설치되지 않았습니다.");
    exit;
endif;
if (!extension_loaded('openssl')) :
    printError("openssl 모듈이 설치되지 않았습니다.");
    exit;
endif;

if (!extension_loaded('curl')) :
    printError("curl 모듈이 설치되지 않았습니다.");
    exit;
endif;

//옵션 처리
$shortargs  = "";
$shortargs .= "i:";
$shortargs .= "v";
$shortargs .= "d";
$shortargs .= "o:s:";
$shortargs .= "l:";
$shortargs .= "h";
$longargs  = array(
    "version",
    "display",
    "outfile:",
    "socket:",
    "limit::",
    "icon:",
    "episode:",
    "rebroadcast:",
    "verbose:",
    "help"
);
$args = getopt($shortargs, $longargs);
$Settingfile = __DIR__."/epg2xml.json";
try {
    $f = @file_get_contents($Settingfile);
    if($f === False) :
        printError("epg2xml.".JSON_FILE_ERROR);
        exit;
    else :
        try {
            $Settings = json_decode($f, TRUE);
            if(json_last_error() != JSON_ERROR_NONE) throw new Exception("epg2xml.".JSON_SYNTAX_ERROR);
            $MyISP = $Settings['MyISP'] ?: "ALL";
            $MyChannels = isset($Settings['MyChannels']) ? $Settings['MyChannels'] : "";
            $default_output = $Settings['output'] ?: "d";
            $default_xml_file = $Settings['default_xml_file'] ?: "xmltv.xml";
            $default_xml_socket = $Settings['default_xml_socket'] ?: "xmltv.sock";
            $default_icon_url = $Settings['default_icon_url'] ?: "";
            $default_fetch_limit = $Settings['default_fetch_limit'] ?: "2";
            $default_rebroadcast = $Settings['default_rebroadcast'] ?: "y";
            $default_episode = $Settings['default_episode'] ?: "y";
            $default_verbose = $Settings['default_verbose'] ?: "n";
            $default_xmltvns = $Settings['default_xmltvns'] ?: "n";
            $userISP = !empty($_GET['i']) ? $_GET['i'] : (!empty($args['i']) ? $args['i'] : "");
            $user_output = "";
            $user_xml_file = "";
            $user_xml_socket = "";
            if(isset($_GET['d']) || isset($_GET['display']) || (isset($args['d']) && $args['d'] === False) || (isset($args['display']) && $args['display'] === False)):
                if(isset($_GET['o']) || isset($_GET['outfile']) || isset($_GET['s']) || isset($_GET['socket']) || isset($args['o']) || isset($args['outfile']) || isset($args['s']) || isset($args['socket'])) :
                    printf($usage);
                    printf("epg2xml.php: error:  argument -o/--outfile, -s/--socket: not allowed with argument -d/--display\n");
                    exit;
                endif;
                $user_output = "d";
            elseif(isset($_GET['o']) || isset($_GET['outfile']) || isset($args['o']) || isset($args['outfile'])):
                if(isset($_GET['d']) || isset($_GET['display']) || isset($_GET['s']) || isset($_GET['socket']) || isset($args['d']) || isset($args['display']) || isset($args['s']) || isset($args['socket'])) :
                    printf($usage);
                    printf("epg2xml.php: error:  argument -d/--display, -s/--socket: not allowed with argument -o/--outfile\n");
                    exit;
                endif;
                $user_output = "o";
                if(isset($_GET['o']) || isset($_GET['outfile'])) :
                    $user_xml_file = $_GET['o'] ?: $_GET['outfile'];
                elseif(isset($args['o']) || isset($args['outfile'])) :
                    $user_xml_file = $args['o'] ?: $args['outfile'];
                endif;
            elseif(isset($_GET['s']) || isset($_GET['socket']) || isset($args['s']) || isset($args['socket'])):
                if(isset($_GET['d']) || isset($_GET['display']) || isset($_GET['o']) || isset($_GET['outfile']) || isset($args['d']) || isset($args['display']) || isset($args['o']) || isset($args['outfile'])) :
                    printf($usage);
                    printf("epg2xml.php: error:  argument -d/--display, -o/--outfile: not allowed with argument -s/--socket\n");
                    exit;
                endif;
                $user_output = "s";
                if(isset($_GET['s']) || isset($_GET['socket'])) :
                    $user_xml_socket = $_GET['s'] ?: $_GET['socket'];
                elseif(isset($args['s']) || isset($args['socket'])) :
                    $user_xml_socket = $args['s'] ?: $args['socket'];
                endif;
            endif;
            $user_fetch_limit = "";
            $user_icon_url = empty($_GET['icon']) === False ? $_GET['icon'] : (empty($args['icon']) === False ? $args['icon'] : "");
            if(isset($_GET['l']) || isset($_GET['limit']) || isset($args['l']) || isset($args['limit'])):
                if(isset($_GET['l']) || isset($_GET['limit'])) :
                    $user_fetch_limit = $_GET['l'] ?: $_GET['limit'];
                elseif(isset($args['l']) || isset($args['limit'])) :
                    $user_fetch_limit = $args['l'] ?: $args['limit'];
                endif;
            endif;
            $user_rebroadcast = empty($_GET['rebroadcast']) === False ? $_GET['rebroadcast'] : (empty($args['rebroadcast']) === False ? $args['rebroadcast'] : "");
            $user_episode = empty($_GET['episode']) === False ? $_GET['episode'] : (empty($args['episode']) === False ? $args['episode'] : "");
            $user_verbose = empty($_GET['verbose']) === False ? $_GET['verbose'] : (empty($args['verbose']) === False ? $args['verbose'] : "");
            if(!empty($userISP)) $MyISP = $userISP;
            if(!empty($user_output)) $default_output = $user_output;
            if(!empty($user_xml_file)) $default_xml_file = $user_xml_file;
            if(!empty($user_xml_socket)) $default_xml_socket = $user_xml_socket;
            if(!empty($user_icon_url)) $default_icon_url = $user_icon_url;
            if(!empty($user_fetch_limit)) $default_fetch_limit = $user_fetch_limit;
            if(!empty($user_rebroadcast)) $default_rebroadcast = $user_rebroadcast;
            if(!empty($user_episode)) $default_episode = $user_episode;
            if(!empty($user_verbose)) $default_verbose = $user_verbose;

            if(empty($MyISP)) : //ISP 선택없을 시 사용법 출력
                printError("epg2xml.json 파일의 MyISP항목이 없습니다.");
                exit;
            else :
                if(!in_array($MyISP, array("ALL", "KT", "LG", "SK"))) : //ISP 선택
                    printError("MyISP는 ALL, KT, LG, SK만 가능합니다.");
                    exit;
                endif;
            endif;
            if(empty($default_output)) :
                printError("epg2xml.json 파일의 output항목이 없습니다.");
                exit;
            else :
                if(in_array($default_output, array("d", "o", "s"))) :
                    switch ($default_output) :
                        case "d" :
                            $output = "display";
                            break;
                        case "o" :
                            $output = "file";
                            break;
                        case "s" :
                            $output = "socket";
                            break;
                    endswitch;
                else :
                    printError("output는 d, o, s만 가능합니다.");
                    exit;
                endif;
            endif;
            if(empty($default_fetch_limit)) :
                printError("epg2xml.json 파일의 default_fetch_limit항목이 없습니다.");
                exit;
            else :
                if(in_array($default_fetch_limit, array(1, 2, 3, 4, 5, 6, 7))) :
                    $period = $default_fetch_limit;
                   else :
                    printError("default_fetch_limit는 1, 2, 3, 4, 5, 6, 7만 가능합니다.");
                    exit;
                endif;
            endif;
            if(is_null($default_icon_url) == True) :
                printError("epg2xml.json 파일의 default_icon_url항목이 없습니다.");
                exit;
            else :
                $IconUrl = $default_icon_url;
            endif;
            if(empty($default_rebroadcast)) :
                printError("epg2xml.json 파일의 default_rebroadcast항목이 없습니다.");
                exit;
            else :
                if(in_array($default_rebroadcast, array("y", "n"))) :
                    $addrebroadcast = $default_rebroadcast;
                else :
                    printError("default_rebroadcast는 y, n만 가능합니다.");
                    exit;
                endif;
            endif;
           if(empty($default_episode)) :
                printError("epg2xml.json 파일의 default_episode항목이 없습니다.");
                exit;
            else :
                if(in_array($default_episode, array("y", "n"))) :
                    $addepisode = $default_episode;
                else :
                    printError("default_episode는 y, n만 가능합니다.");
                    exit;
                endif;
            endif;
            if(empty($default_verbose)) :
                printError("epg2xml.json 파일의 default_verbose항목이 없습니다.");
                exit;
            else :
                if(in_array($default_verbose, array("y", "n"))) :
                    $addverbose = $default_verbose;
                else :
                    printError("default_verbose는 y, n만 가능합니다.");
                    exit;
                endif;
            endif;
            if(empty($default_xmltvns)) :
                printError("epg2xml.json 파일의 default_xmltvns항목이 없습니다.");
                exit;
            else :
                if(in_array($default_xmltvns, array("y", "n"))) :
                    $addxmltvns = $default_xmltvns;
                else :
                    printError("default_xmltvns는 y, n만 가능합니다.");
                    exit;
                endif;
            endif;
        }
        catch(Exception $e) {
            printError($e->getMessage());
            exit;
        }
    endif;
}
catch(Exception $e) {
    printError($e->getMessage());
    exit;
}

if(php_sapi_name() != "cli"):
    if(isset($_GET['h']) || isset($_GET['help']))://도움말 출력
        header("Content-Type: text/plain; charset=utf-8");
        print($help);
        exit;
    elseif(isset($_GET['v'])|| isset($_GET['version']))://버전 정보 출력
        header("Content-Type: text/plain; charset=utf-8");
        printf("epg2xml.php version : %s\n", VERSION);
        exit;
    endif;
else :
    if((isset($args['h']) && $args['h'] === False) || (isset($args['help']) && $args['help'] === False))://도움말 출력
        printf($help);
        exit;
    elseif((isset($args['v']) && $args['v'] === False) || (isset($args['version']) && $args['version'] === False))://버전 정보 출력
        printf("epg2xml.php version : %s\n", VERSION);
        exit;
    endif;
endif;
if($output == "display") :
    $fp = fopen('php://output', 'w+');
    if ($fp === False) :
        printError(DISPLAY_ERROR);
        exit;
    else :
        try {
            getEpg();
            fclose($fp);
        } catch(Exception $e) {
            if($GLOBALS['debug']) printError($e->getMessage());
        }
    endif;
elseif($output == "file") :
    if($default_xml_file) :
        $fp = fopen($default_xml_file, 'w+');
        if ($fp === False) :
            printError(FIEL_ERROR);
            exit;
        else :
            try {
                getEpg();
                fclose($fp);
            } catch(Exception $e) {
                if($GLOBALS['debug']) printError($e->getMessage());
            }
        endif;
    else :
        printError("epg2xml.json 파일의 default_xml_file항목이 없습니다.");
        exit;
    endif;
elseif($output == "socket") :
    if($default_xml_socket && php_sapi_name() == "cli") :
        $default_xml_socket = "unix://".$default_xml_socket;
        $fp = @fsockopen($default_xml_socket, -1, $errno, $errstr, 30);
        if ($fp === False) :
            printError(SOCKET_ERROR);
            exit;
        else :
            try {
                getEpg();
                fclose($fp);
            } catch(Exception $e) {
                if($GLOBALS['debug']) printError($e->getMessage());
            }
        endif;
    else :
        printError("epg2xml.json 파일의 default_xml_socket항목이 없습니다.");
        exit;
    endif;
endif;

function getEPG() {
    $fp = $GLOBALS['fp'];
    $MyISP = $GLOBALS['MyISP'];
    $MyChannels = $GLOBALS['MyChannels'];
    $Channelfile = __DIR__."/Channel.json";
    $IconUrl = "";
    $ChannelInfos = array();
    try {
        $f = @file_get_contents($Channelfile);
        if($f === False) :
            printError("Channel.json.".JSON_FILE_ERROR);
            exit;
        else :
            try {
                $Channeldatajson = json_decode($f, TRUE);
                if(json_last_error() != JSON_ERROR_NONE) throw new Exception("Channel.".JSON_SYNTAX_ERROR);
            }
            catch(Exception $e) {
                printError($e->getMessage());
                exit;
            }
        endif;
    }
    catch(Exception $e) {
        printError($e->getMessage());
        exit;
    }
//My Channel 정의
    $MyChannelInfo = array();
    if($MyChannels) :
        $MyChannelInfo = array_map('trim',explode(',', $MyChannels));
    endif;
    if(php_sapi_name() != "cli" && $GLOBALS['default_output'] == "d") header("Content-Type: application/xml; charset=utf-8");
    fprintf($fp, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    fprintf($fp, "<!DOCTYPE tv SYSTEM \"xmltv.dtd\">\n\n");
    fprintf($fp, "<tv generator-info-name=\"epg2xml %s\">\n", VERSION);

    foreach ($Channeldatajson as $Channeldata) : //Get Channel & Print Channel info
        if(in_array($Channeldata['Id'], $MyChannelInfo)) :
            $ChannelId = $Channeldata['Id'];
            $ChannelName = htmlspecialchars($Channeldata['Name'], ENT_XML1);
            $ChannelSource = $Channeldata['Source'];
            $ChannelServiceId = $Channeldata['ServiceId'];
            $ChannelIconUrl = htmlspecialchars($Channeldata['Icon_url'], ENT_XML1);
            if($MyISP != "ALL" && $Channeldata[$MyISP.'Ch'] != Null):
                $ChannelInfos[] = array($ChannelId,  $ChannelName, $ChannelSource, $ChannelServiceId);
                $Channelnumber = $Channeldata[$MyISP.'Ch'];
                $ChannelISPName = htmlspecialchars($Channeldata[$MyISP." Name"], ENT_XML1);
                fprintf($fp, "  <channel id=\"%s\">\n", $ChannelId);
                fprintf($fp, "    <display-name>%s</display-name>\n", $ChannelName);
                fprintf($fp, "    <display-name>%s</display-name>\n", $ChannelISPName);
                fprintf($fp, "    <display-name>%s</display-name>\n", $Channelnumber);
                fprintf($fp, "    <display-name>%s</display-name>\n", $Channelnumber." ".$ChannelISPName);
                if($IconUrl) :
                    fprintf($fp, "    <icon src=\"%s/%s.png\" />\n", $IconUrl, $ChannelId);
                else :
                    fprintf($fp, "    <icon src=\"%s\" />\n", $ChannelIconUrl);
                endif;
                fprintf($fp, "  </channel>\n");
            elseif($MyISP == "ALL"):
                $ChannelInfos[] = array($ChannelId,  $ChannelName, $ChannelSource, $ChannelServiceId);
                fprintf($fp, "  <channel id=\"%s\">\n", $ChannelId);
                fprintf($fp, "    <display-name>%s</display-name>\n", $ChannelName);
                if($IconUrl) :
                    fprintf($fp, "    <icon src=\"%s/%s.png\" />\n", $IconUrl, $ChannelId);
                else :
                    fprintf($fp, "    <icon src=\"%s\" />\n", $ChannelIconUrl);
                endif;
                fprintf($fp, "  </channel>\n");
            endif;
        endif;
    endforeach;
    // Print Program Information
    foreach ($ChannelInfos as $ChannelInfo) :
        $ChannelId = $ChannelInfo[0];
        $ChannelName =  $ChannelInfo[1];
        $ChannelSource =  $ChannelInfo[2];
        $ChannelServiceId =  $ChannelInfo[3];
        if($GLOBALS['debug']) printLog($ChannelName.' 채널 EPG 데이터를 가져오고 있습니다');
        if($ChannelSource == 'KT') :
            GetEPGFromKT($ChannelInfo);
        elseif($ChannelSource == 'LG') :
            GetEPGFromLG($ChannelInfo);
        elseif($ChannelSource == 'SK') :
            sleep(5);
            GetEPGFromSK($ChannelInfo);
        elseif($ChannelSource == 'SKB') :
            sleep(5);
            GetEPGFromSKB($ChannelInfo);
        elseif($ChannelSource == 'NAVER') :
            GetEPGFromNaver($ChannelInfo);
        endif;
    endforeach;
    fprintf($fp, "</tv>\n");
}

// Get EPG data from KT
function GetEPGFromKT($ChannelInfo) {
    $ChannelId = $ChannelInfo[0];
    $ChannelName = $ChannelInfo[1];
    $ServiceId =  $ChannelInfo[3];
    $epginfo = array();
    foreach(range(1, $GLOBALS['period']) as $k) :
        $url = "http://tv.kt.com/tv/channel/pSchedule.asp";
        $day = date("Ymd", strtotime("+".($k - 1)." days"));
        $params = array(
            'ch_type' => '1',
            'view_type' => '1',
            'service_ch_no' => $ServiceId,
            'seldate' => $day
        );
        $params = http_build_query($params);
        $method = "POST";
        try {
            $response = getWeb($url, $params, $method);
            if ($response === False && $GLOBALS['debug']) :
                printError($ChannelName.HTTP_ERROR);
            else :
                $response = mb_convert_encoding($response, "HTML-ENTITIES", "EUC-KR");
                $dom = new DomDocument;
                libxml_use_internal_errors(True);
                if($dom->loadHTML('<?xml encoding="utf-8" ?>'.$response)):
                    $xpath = new DomXPath($dom);
                    $query = "//tbody/tr";
                    $rows = $xpath->query($query);
                    foreach($rows as $row) :
                        $startTime = $endTime = $programName = $subprogramName = $desc = $actors = $producers = $category = $episode = "";
                        $rebroadcast = False;
                        $rating = 0;
                        $cells = $row->getElementsByTagName('td');
                        $programs = array_map(null, iterator_to_array($xpath->query('p', $cells->item(1))), iterator_to_array($xpath->query('p', $cells->item(2))), iterator_to_array($xpath->query('p', $cells->item(3))));
                        foreach($programs as $program):
                            $hour = trim($cells->item(0)->nodeValue);
                            $minute = trim($program[0]->nodeValue);
                            $startTime = date("YmdHis", strtotime($day.$hour.$minute."00"));
                            $programName = trim($program[1]->nodeValue);
                            $images = $program[1]->getElementsByTagName('img')->item(0);
                            preg_match('/([\d,]+)/', $images->getAttribute('alt'), $grade);
                            if($grade != NULL):
                                $rating = $grade[1];
                            else:
                                $rating = 0;
                            endif;
                            $programName = str_replace("방송중 ", "", $programName);
                            $category = trim($program[2]->nodeValue);
                            //ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
                            $epginfo[] = array($ChannelId, $startTime, $programName, $subprogramName, $desc, $actors, $producers, $category, $episode, $rebroadcast, $rating);
                            usleep(1000);
                        endforeach;
                    endforeach;
                else :
                    if($GLOBALS['debug']) printError($ChannelName.CONTENT_ERROR);
                endif;
            endif;
        } catch (Exception $e) {
            if($GLOBALS['debug']) printError($e->getMessage());
        }
    endforeach;
    if($epginfo) epgzip($epginfo);
}

// Get EPG data from LG
function GetEPGFromLG($ChannelInfo) {
    $ChannelId = $ChannelInfo[0];
    $ChannelName = $ChannelInfo[1];
    $ServiceId =  $ChannelInfo[3];
    $epginfo = array();
    foreach(range(1, $GLOBALS['period']) as $k) :
        $url = "http://www.uplus.co.kr/css/chgi/chgi/RetrieveTvSchedule.hpi";
        $day = date("Ymd", strtotime("+".($k - 1)." days"));
        $params = array(
            'chnlCd' => $ServiceId,
            'evntCmpYmd' =>  $day
        );
        $params = http_build_query($params);
        $method = "POST";
        try {
            $response = getWeb($url, $params, $method);
            if ($response === False && $GLOBALS['debug']) :
                printError($ChannelName.HTTP_ERROR);
            else :
                $response = mb_convert_encoding($response, "UTF-8", "EUC-KR");
                $response = str_replace(array('<재>', ' [..', ' (..'), array('&lt;재&gt;', '', ''), $response);
                $dom = new DomDocument;
                libxml_use_internal_errors(True);
                if($dom->loadHTML('<?xml encoding="utf-8" ?>'.$response)):
                    $xpath = new DomXPath($dom);
                    $query = "//div[@class='tblType list']/table/tbody/tr";
                    $rows = $xpath->query($query);
                    foreach($rows as $row) :
                        $startTime = $endTime = $programName = $subprogramName = $desc = $actors = $producers = $category = $episode = "";
                        $rebroadcast = False;
                        $rating = 0;
                        $cells = $row->getElementsByTagName('td');
                        $startTime = date("YmdHis", strtotime($day." ".trim($cells->item(0)->nodeValue)));
                        $programName = trim($cells->item(1)->childNodes->item(0)->nodeValue);
                        $pattern = '/(<재>)?\s?(?:\[.*?\])?(.*?)(?:\[(.*)\])?\s?(?:\(([\d,]+)회\))?$/';
                        preg_match($pattern, $programName, $matches);
                        if ($matches != NULL) :
                            if(isset($matches[2])) $programName = trim($matches[2]) ?: "";
                            if(isset($matches[3])) $subprogramName = trim($matches[3]) ?: "";
                            if(isset($matches[4])) $episode = trim($matches[4]) ?: "";
                            if(isset($matches[1])) $rebroadcast = trim($matches[1]) ? True: False;
                        endif;
                        $category = trim($cells->item(2)->nodeValue);
                        $spans = $cells->item(1)->getElementsByTagName('span');
                        $rating = trim($spans->item(1)->nodeValue)=="All" ? 0 : trim($spans->item(1)->nodeValue);
                        //ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
                        $epginfo[] = array($ChannelId, $startTime, $programName, $subprogramName, $desc, $actors, $producers, $category, $episode, $rebroadcast, $rating);
                        usleep(1000);
                    endforeach;
                else :
                    if($GLOBALS['debug']) printError($ChannelName.CONTENT_ERROR);
                endif;
            endif;
        } catch (Exception $e) {
            if($GLOBALS['debug']) printError($e->getMessage());
        }
    endforeach;
    if($epginfo) epgzip($epginfo);
}

// Get EPG data from SK
function GetEPGFromSK($ChannelInfo) {
    $ChannelId = $ChannelInfo[0];
    $ChannelName = $ChannelInfo[1];
    $ServiceId =  $ChannelInfo[3];
    $today = date("Ymd");
    $lastday = date("Ymd", strtotime("+".($GLOBALS['period'] - 1)." days"));
    $url = "http://m.btvplus.co.kr/common/inc/IFGetData.do";
    $params = array(
        'variable' => 'IF_LIVECHART_DETAIL',
        'pcode' => '|^|start_time='.$today.'00|^|end_time='.$lastday.'24|^|svc_id='.$ServiceId
    );
    $params = http_build_query($params);
    $method = "POST";
    try {
        $response = getWeb($url, $params, $method);
        if ($response === False && $GLOBALS['debug']) :
            printError($ChannelName.HTTP_ERROR);
        else :
            try {
                $data = json_decode($response, TRUE);
                if(json_last_error() != JSON_ERROR_NONE) throw new Exception(JSON_SYNTAX_ERROR);
                if($data['channel'] == NULL) :
                    if($GLOBALS['debug']) :
                        printError($ChannelName.CHANNEL_ERROR);
                    endif;
                else :
                    $programs = $data['channel']['programs'];
                    foreach ($programs as $program) :
                        $startTime = $endTime = $programName = $subprogramName = $desc = $actors = $producers = $category = $episode = "";
                        $rebroadcast = False;
                        $rating = 0;
                        $pattern = '/^(.*?)(?:\s*[\(<]([\d,회]+)[\)>])?(?:\s*<([^<]*?)>)?(\((재)\))?$/';
                        preg_match($pattern, str_replace('...', '>', $program['programName']), $matches);
                        if ($matches != NULL) :
                            if(isset($matches[1])) $programName = trim($matches[1]) ?: "";
                            if(isset($matches[3])) $subprogramName = trim($matches[3]) ?: "";
                            if(isset($matches[2])) $episode = str_replace("회", "", $matches[2]) ?: "";
                            if(isset($matches[5])) $rebroadcast = $matches[5] ? True : False;
                        endif;
                        $startTime = date("YmdHis",$program['startTime']/1000);
                        $endTime = date("YmdHis",$program['endTime']/1000);
                        $desc = $program['synopsis'] ?: "";
                        $actors =trim(str_replace('...','',$program['actorName']), ', ') ?: "";
                        $producers = trim(str_replace('...','',$program['directorName']), ', ') ?: "";
                        if ($program['mainGenreName'] != NULL) :
                            $category = $program['mainGenreName'];
                        else:
                            $category = "";
                        endif;
                        $rating = $program['ratingCd'] ?: 0;
                        $programdata = array(
                            'channelId'=> $ChannelId,
                            'startTime' => $startTime,
                            'endTime' => $endTime,
                            'programName' => $programName,
                            'subprogramName'=> $subprogramName,
                            'desc' => $desc,
                            'actors' => $actors,
                            'producers' => $producers,
                            'category' => $category,
                            'episode' => $episode,
                            'rebroadcast' => $rebroadcast,
                            'rating' => $rating
                        );
                        writeProgram($programdata);
                        usleep(1000);
                    endforeach;
                endif;
            } catch(Exception $e) {
                if($GLOBALS['debug']) printError($e->getMessage());
            }
        endif;
    } catch (Exception $e) {
        if($GLOBALS['debug']) printError($e->getMessage());
    }
}

// Get EPG data from SKB
function GetEPGFromSKB($ChannelInfo) {
    $ChannelId = $ChannelInfo[0];
    $ChannelName = $ChannelInfo[1];
    $ServiceId =  $ChannelInfo[3];
    $epginfo = array();
    foreach(range(1, $GLOBALS['period']) as $k) :
        $url = "http://m.skbroadband.com/content/realtime/Channel_List.do";
        $day = date("Ymd", strtotime("+".($k - 1)." days"));
        $params = array(
            'key_depth2' => $ServiceId,
            'key_depth3' => $day
        );
        $params = http_build_query($params);
        $method = "POST";
        try {
            $response = getWeb($url, $params, $method);
            if ($response === False && $GLOBALS['debug']) :
                printError($ChannelName.HTTP_ERROR);
            else :
                $response = str_replace('charset="EUC-KR"', 'charset="UTF-8"', $response);
                $response = mb_convert_encoding($response, "UTF-8", "EUC-KR");
                $response = preg_replace('/<!--(.*?)-->/is', '', $response);
                $response = preg_replace('/<span class="round_flag flag02">(.*?)<\/span>/', '', $response);
                $response = preg_replace('/<span class="round_flag flag03">(.*?)<\/span>/', '', $response);
                $response = preg_replace('/<span class="round_flag flag04">(.*?)<\/span>/', '', $response);
                $response = preg_replace('/<span class="round_flag flag09">(.*?)<\/span>/', '', $response);
                $response = preg_replace('/<span class="round_flag flag10">(.*?)<\/span>/', '', $response);
                $response = preg_replace('/<span class="round_flag flag11">(.*?)<\/span>/', '', $response);
                $response = preg_replace('/<span class="round_flag flag12">(.*?)<\/span>/', '', $response);
                $response = preg_replace('/<strong class="hide">프로그램 안내<\/strong>/', '', $response);
                $response = preg_replace_callback('/<p class="cont">(.*)/', 'converthtmlspecialchars', $response);
                $response = preg_replace_callback('/<p class="tit">(.*)/', 'converthtmlspecialchars', $response);
                $dom = new DomDocument;
                libxml_use_internal_errors(True);
                if($dom->loadHTML('<?xml encoding="utf-8" ?>'.$response)):
                    $xpath = new DomXPath($dom);
                    $query = "//span[@class='caption' or @class='explan' or @class='fullHD' or @class='UHD' or @class='nowon']";
                    $spans = $xpath->query($query);
                    foreach($spans as $span) :
                        $span->parentNode->removeChild( $span);
                    endforeach;
                    $query = "//div[@id='uiScheduleTabContent']/div/ol/li";
                    $rows = $xpath->query($query);
                    foreach($rows as $row) :
                        $startTime = $endTime = $programName = $subprogramName = $desc = $actors = $producers = $category = $episode = "";
                        $rebroadcast = False;
                        $rating = 0;
                        $cells = $row->getElementsByTagName('p');
                        $startTime = $cells->item(0)->nodeValue ?: "";
                        $startTime = date("YmdHis", strtotime($day." ".$startTime));
                        $programName = trim($cells->item(1)->childNodes->item(0)->nodeValue) ?: "";
                        $pattern = '/^(.*?)(\(([\d,]+)회\))?(<(.*)>)?(\((재)\))?$/';
                        preg_match($pattern, $programName, $matches);
                        if ($matches != NULL) :
                            if(isset($matches[1])) $programName = trim($matches[1]) ?: "";
                            if(isset($matches[5])) $subprogramName = trim($matches[5]) ?: "";
                            if(isset($matches[3])) $episode = $matches[3] ?: "";
                            if(isset($matches[7])) $rebroadcast = $matches[7] ? True : False;
                        endif;
                        if(trim($cells->item(1)->childNodes->item(1)->nodeValue)) $rating = str_replace('세 이상', '', trim($cells->item(1)->childNodes->item(1)->nodeValue))  ?: 0;
                        //ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
                        $epginfo[] = array($ChannelId, $startTime, $programName, $subprogramName, $desc, $actors, $producers, $category, $episode, $rebroadcast, $rating);
                        usleep(1000);
                    endforeach;
                else :
                    if($GLOBALS['debug']) printError($ChannelName.CONTENT_ERROR);
                endif;
            endif;
        } catch (Exception $e) {
            if($GLOBALS['debug']) printError($e->getMessage());
        }
    endforeach;
    if($epginfo) epgzip($epginfo);
}

// Get EPG data from Naver
function GetEPGFromNaver($ChannelInfo) {
    $ChannelId = $ChannelInfo[0];
    $ChannelName = $ChannelInfo[1];
    $ServiceId =  $ChannelInfo[3];
    $epginfo = array();
    $totaldate = array();
    $url = "https://search.naver.com/p/csearch/content/batchrender_ssl.nhn";
    foreach(range(1, $GLOBALS['period']) as $k) :
        $day = date("Ymd", strtotime("+".($k - 1)." days"));
        $totaldate[] = $day;
    endforeach;
    $params = array(
        '_callback' => 'epg',
        'fileKey' => 'single_schedule_channel_day',
        'pkid' => '66',
        'u1' => 'single_schedule_channel_day',
        'u2' => join(",", $totaldate),
        'u3' => $day,
        'u4' => $GLOBALS['period'],
        'u5' => $ServiceId,
        'u6' => 1,
        'u7' => $ChannelName."편성표",
        'u8' => $ChannelName."편성표",
        'where' => 'nexearch'
    );
    $params = http_build_query($params);
    $method = "GET";
    try {
        $response = getWeb($url, $params, $method);
        if ($response === False && $GLOBALS['debug']) :
            printError($ChannelName.HTTP_ERROR);
        else :
            try {
                $response = str_replace('epg( ', '', $response );
                $response = substr($response, 0, strlen($response)-2);
                $response = preg_replace("/\/\*.*?\*\//","",$response);
                $data = json_decode($response, TRUE);
                if(json_last_error() != JSON_ERROR_NONE) throw new Exception(JSON_SYNTAX_ERROR);
                 if($data['displayDates'][0]['count'] == 0) :
                    if($GLOBALS['debug']) :
                        printError($ChannelName.CHANNEL_ERROR);
                    endif;
                else :
                    for($i = 0; $i < count($data['displayDates']); $i++) :
                        for($j = 0; $j < 24; $j++) :
                            foreach($data['schedules'][$j][$i] as $program) :
                                $startTime = $endTime = $programName = $subprogramName = $desc = $actors = $producers = $category = $episode = "";
                                $rebroadcast = False;
                                $rating = 0;
                                $startTime = date("YmdHis", strtotime($data['displayDates'][$i]['date']." ".$program['startTime']));
                                $programName = htmlspecialchars_decode(trim($program['title']), ENT_XML1);
                                $episode = str_replace("회","", $program['episode']);
                                $rebroadcast = $program['isRerun'] ? True : False;
                                $rating = $program['grade'];
                                //ChannelId, startTime, programName, subprogramName, desc, actors, producers, category, episode, rebroadcast, rating
                                $epginfo[] = array($ChannelId, $startTime, $programName, $subprogramName, $desc, $actors, $producers, $category, $episode, $rebroadcast, $rating);
                                usleep(1000);
                            endforeach;
                        endfor;
                    endfor;
                endif;
             } catch(Exception $e) {
                if($GLOBALS['debug']) printError($e->getMessage());
            }
        endif;
    } catch (Exception $e) {
        if($GLOBALS['debug']) printError($e->getMessage());
    }
    if($epginfo) epgzip($epginfo);
}

# Zip epginfo
function epgzip($epginfo) {
    $epg1 = current($epginfo);
    array_shift($epginfo);
    foreach($epginfo as $epg2):
        $ChannelId = $epg1[0] ?: "";
        $startTime = $epg1[1] ?: "";
        $endTime = $epg2[1] ?: "";
        $programName = $epg1[2] ?: "";
        $subprogramName = $epg1[3] ?: "";
        $desc = $epg1[4] ?: "";
        $actors = $epg1[5] ?: "";
        $producers = $epg1[6] ?: "";
        $category = $epg1[7] ?: "";
        $episode = $epg1[8] ?: "";
        $rebroadcast = $rebroadcast = $epg1[9] ? True: False;
        $rating = $epg1[10] ?: 0;
        $programdata = array(
            'channelId'=> $ChannelId,
            'startTime' => $startTime,
            'endTime' => $endTime,
            'programName' => $programName,
            'subprogramName'=> $subprogramName,
            'desc' => $desc,
            'actors' => $actors,
            'producers' => $producers,
            'category' => $category,
            'episode' => $episode,
            'rebroadcast' => $rebroadcast,
            'rating' => $rating
        );
        writeProgram($programdata);
        $epg1 = $epg2;
    endforeach;
}

function writeProgram($programdata) {
    $fp = $GLOBALS['fp'];
    $ChannelId = $programdata['channelId'];
    $startTime = $programdata['startTime'];
    $endTime = $programdata['endTime'];
    $programName = trim(htmlspecialchars($programdata['programName'], ENT_XML1));
    $subprogramName = trim(htmlspecialchars($programdata['subprogramName'], ENT_XML1));
    preg_match('/(.*) \(?(\d+부)\)?/', $programName, $matches);
    if ($matches != NULL) :
        if(isset($matches[1])) $programName = trim($matches[1]) ?: "";
        if(isset($matches[2])) $subprogramName = trim($matches[2]." ".$subprogramName) ?: "";
    endif;//
    if($programName == NULL):
        $programName = $subprogramName;
    endif;
    $actors = htmlspecialchars($programdata['actors'], ENT_XML1);
    $producers = htmlspecialchars($programdata['producers'], ENT_XML1);
    $category = htmlspecialchars($programdata['category'], ENT_XML1);
    $episode = $programdata['episode'];
    if($episode) :
        $episode_ns = (int)$episode - 1;
        $episode_ns = '0' . '.' . $episode_ns . '.' . '0' . '/' . '0';
        $episode_on = $episode;
    endif;
    $rebroadcast = $programdata['rebroadcast'];
    if($episode && $GLOBALS['addepisode'] == 'y') $programName = $programName." (".$episode."회)";
    if($rebroadcast == True && $GLOBALS['addrebroadcast'] == 'y') $programName = $programName." (재)";
    if($programdata['rating'] == 0) :
        $rating = "전체 관람가";
    else :
        $rating = sprintf("%s세 이상 관람가", $programdata['rating']);
    endif;
    if($GLOBALS['addverbose'] == 'y') :
        $desc = $programName;
        if($subprogramName)  $desc = $desc."\n부제 : ".$subprogramName;
        if($rebroadcast == True && $GLOBALS['addrebroadcast']  == 'y') $desc = $desc."\n방송 : 재방송";
        if($episode) $desc = $desc."\n회차 : ".$episode."회";
        if($category) $desc = $desc."\n장르 : ".$category;
        if($actors) $desc = $desc."\n출연 : ".trim($actors);
        if($producers) $desc = $desc."\n제작 : ".trim($producers);
        $desc = $desc."\n등급 : ".$rating;
    else:
        $desc = "";
    endif;
    if($programdata['desc']) $desc = $desc."\n".htmlspecialchars($programdata['desc'], ENT_XML1);
    $desc = preg_replace('/ +/', ' ', $desc);
    $contentTypeDict = array(
        '교양' => 'Arts / Culture (without music)',
        '만화' => 'Cartoons / Puppets',
        '교육' => 'Education / Science / Factual topics',
        '취미' => 'Leisure hobbies',
        '드라마' => 'Movie / Drama',
        '영화' => 'Movie / Drama',
        '음악' => 'Music / Ballet / Dance',
        '뉴스' => 'News / Current affairs',
        '다큐' => 'Documentary',
        '라이프' => 'Documentary',
        '시사/다큐' => 'Documentary',
        '연예' => 'Show / Game show',
        '스포츠' => 'Sports',
        '홈쇼핑' => 'Advertisement / Shopping'
       );
    $contentType = "";
    foreach($contentTypeDict as $key => $value) :
        if(!(strpos($category, $key) === False)) :
            $contentType = $value;
        endif;
    endforeach;
    fprintf($fp, "  <programme start=\"%s +0900\" stop=\"%s +0900\" channel=\"%s\">\n", $startTime, $endTime, $ChannelId);
    fprintf($fp, "    <title lang=\"kr\">%s</title>\n", $programName);
    if($subprogramName) :
        fprintf($fp, "    <sub-title lang=\"kr\">%s</sub-title>\n", $subprogramName);
    endif;
    if($GLOBALS['addverbose']=='y') :
        fprintf($fp, "    <desc lang=\"kr\">%s</desc>\n", $desc);
        if($actors || $producers):
            fprintf($fp, "    <credits>\n");
            if($actors) :
                foreach(explode(',', $actors) as $actor):
                    if(trim($actor)) fprintf($fp, "      <actor>%s</actor>\n", trim($actor));
                endforeach;
            endif;
            if($producers) :
                foreach(explode(',', $producers) as $producer):
                    if(trim($producer)) fprintf($fp, "      <producer>%s</producer>\n", trim($producer));
                endforeach;
            endif;
            fprintf($fp, "    </credits>\n");
        endif;
    endif;
    if($category) fprintf($fp, "    <category lang=\"kr\">%s</category>\n", $category);
    if($contentType) fprintf($fp, "    <category lang=\"en\">%s</category>\n", $contentType);
    if($episode && $GLOBALS['addxmltvns']=='y') fprintf($fp, "    <episode-num system=\"xmltv_ns\">%s</episode-num>\n", $episode_ns);
    if($episode && $GLOBALS['addxmltvns']!='y') fprintf($fp, "    <episode-num system=\"onscreen\">%s</episode-num>\n", $episode_on);
    if($rebroadcast) fprintf($fp, "    <previously-shown />\n");
    if($rating) :
        fprintf($fp, "    <rating system=\"KMRB\">\n");
        fprintf($fp, "      <value>%s</value>\n", $rating);
        fprintf($fp, "    </rating>\n");
    endif;
    fprintf($fp, "  </programme>\n");
}

function getWeb($url, $params, $method) {
    $ch = curl_init();
    if($method == "GET"):
        $url = $url."?".$params;
    elseif($method == "POST"):
        curl_setopt ($ch, CURLOPT_POST, True);
        curl_setopt ($ch, CURLOPT_POSTFIELDS, $params);
    endif;
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, True);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, $GLOBALS['timeout']);
    curl_setopt($ch, CURLOPT_TIMEOUT, $GLOBALS['req_timeout']);
    curl_setopt($ch, CURLOPT_HEADER, False);
    curl_setopt($ch, CURLOPT_FAILONERROR, True);
    curl_setopt($ch, CURLOPT_USERAGENT, $GLOBALS['ua']);
    $response = curl_exec($ch);
    if(curl_error($ch) && $GLOBALS['debug']) printError($url." ".curl_error($ch));
    curl_close($ch);
    return $response;
}

function printLog($string) {
    if(php_sapi_name() == "cli"):
        fwrite(STDERR, $string."\n");
    else:
        header("Content-Type: text/plain; charset=utf-8");
        print($string."\n");
    endif;
}

function printError($string) {
    if(php_sapi_name() == "cli"):
        fwrite(STDERR, "Error : ".$string."\n");
    else:
        header("Content-Type: text/plain; charset=utf-8");
        print("Error : ".$string."\n");
    endif;
}

function _microtime() {
    list($usec, $sec) = explode(" ", microtime());
    return ($sec.(int)($usec*1000));
}

function startsWith($haystack, $needle) {
    return !strncmp($haystack, $needle, strlen($needle));
}

function converthtmlspecialchars($match) {
    return '<p class="cont">'.htmlspecialchars($match[1]);
}

//사용방법
$usage = <<<USAGE
usage: epg2xml.py [-h] [-i {ALL,KT,LG,SK}] [-v | -d | -o [xmltv.xml] | -s
                  [xmltv.sock]] [--icon http://www.example.com/icon] [-l 1-2]
                  [--rebroadcast y, n] [--episode y, n] [--verbose y, n]

USAGE;

//도움말
$help = <<<HELP
usage: epg2xml.php [-h] [-i {ALL,KT,LG,SK}]
                  [-v | -d | -o [xmltv.xml]
                  | -s [xmltv.sock]] [--icon http://www.example.com/icon]
                  [-l 1-2] [--rebroadcast y, n] [--episode y, n]
                  [--verbose y, n]

EPG 정보를 출력하는 방법을 선택한다

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -d, --display         EPG 정보 화면출력
  -o [xmltv.xml], --outfile [xmltv.xml]
                        EPG 정보 저장
  -s [xmltv.sock], --socket [xmltv.sock]
                        xmltv.sock(External: XMLTV)로 EPG정보 전송

  IPTV 선택

  -i {ALL,KT,LG,SK}     사용하는 IPTV : ALL, KT, LG, SK

추가옵션:
  --icon http://www.example.com/icon
                        채널 아이콘 URL, 기본값:
  -l 1-2, --limit 1-2   EPG 정보를 가져올 기간, 기본값: 2
  --rebroadcast y, n    제목에 재방송 정보 출력
  --episode y, n        제목에 회차 정보 출력
  --verbose y, n        EPG 정보 추가 출력


HELP;
?>
