1) HTTP 요청정보
Request URL
https://www.saramin.co.kr/zf_user/jobs/list/job-category?page=2&cat_kewd=2248%2C82%2C83%2C106%2C107%2C108%2C105&search_optional_item=n&search_done=y&panel_count=y&preview=y&isAjaxRequest=0&page_count=50&sort=RL&type=job-category&is_param=1&isSearchResultEmpty=1&isSectionHome=0&searchParamCount=1
Request Method
GET
Status Code
200 OK
Remote Address
182.162.86.29:443
Referrer Policy
strict-origin-when-cross-origin
2) HTTP 헤더정보
host
www.saramin.co.kr
referer
https://www.saramin.co.kr/zf_user/jobs/list/job-category?cat_kewd=2248%2C82%2C83%2C106%2C107%2C108%2C105&panel_type=&search_optional_item=n&search_done=y&panel_count=y&preview=y
sec-ch-ua
"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-ch-ua-platform-version
"26.5.1"
sec-fetch-dest
document
sec-fetch-mode
navigate
sec-fetch-site
same-origin
sec-fetch-user
?1
upgrade-insecure-requests
1
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36
3) Payload 정보
page=2&cat_kewd=2248%2C82%2C83%2C106%2C107%2C108%2C105&search_optional_item=n&search_done=y&panel_count=y&preview=y&isAjaxRequest=0&page_count=50&sort=RL&type=job-category&is_param=1&isSearchResultEmpty=1&isSectionHome=0&searchParamCount=1
4) 응답의 일부를 Response 에서 일부를 복사해서 넣어주기 (전체는 토큰 수 제한으로 어렵습니다.)
<html lang="ko">
    <head>
        <title>데이터 사이언티스트 외 취업 | 직업별 채용정보 - 사람인</title>
        <meta http-equiv="X-UA-Compatible" content="IE=Edge">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <meta http-equiv="Content-Language" content="ko-KR">
        <meta name="naver-site-verification" content="86455485e27cab6986d130e4c3b90c5b516820d1">
        <meta name="robots" content="NOINDEX">
        <meta name="Description" content="데이터 사이언티스트 외 채용공고 | 직업(직종), 근무지역, 경력, 학력, 연봉 등으로 찾는 취업정보 - 사람인">
        <meta name="writer" content="사람인">
        <meta name="keywords" content="직업별, 직종별, 데이터 사이언티스트,데이터분석가,데이터엔지니어, 채용, 채용공고, 취업, 구인, 공채, 신입, 경력, 연봉, 취업정보, 채용정보, 기업정보, 취업사이트, 사람인">
        <meta name="naver" content="nosublinks">
        <meta property="og:title" content="데이터 사이언티스트 외 취업 | 직업별 채용정보 - 사람인">
        <meta property="og:description" content="데이터 사이언티스트 외 채용공고 | 직업(직종), 근무지역, 경력, 학력, 연봉 등으로 찾는 취업정보 - 사람인">
        <meta property="og:site_name" content="사람인">

5)한페이지가 성공적으로 수집되는지 확인하고 sqlitedb 파일로 저장하고 JSON 데이터는 별도의 컬럼으로 저장할 것
1페이지부터 마지막 페이지까지 수집이 다되면 수집이 잘 되었는지 확인하고 결과 리포트를 보여줄 것
채용 정보는 수집할 수 있는 정보는 모두 수집할 것, 기업명, 공고상태, 작성일, 마감일, 지원자 수, 찜한 수, 공고주소 등을 꼭 수집할 것
해당 정보를 수집하는 목적은 기업별 채용 정보 분석, 공고별 특성 분석, 시장 동향 파악에 필요한 기초 자료를 수집하는 것입니다.

6)데이터 수집 요청을 보낼때는 0.1~1초씩 쉬었다가 수집하게 할 것 네트워크 부담을 줄일 것
데이터베이스에 저장할 때는 중복데이터가 발생하지 않도록 기존 데이터가 있다면 업데이트 하는 방법으로 수집할 것