1) HTTP 요청정보
Request URL
https://api.linkareer.com/graphql?operationName=CoverLetterList&variables=%7B%22filterBy%22%3A%7B%22role%22%3A%22%EB%8D%B0%EC%9D%B4%ED%84%B0%22%2C%22types%22%3A%5B%22ALL%22%5D%2C%22status%22%3A%22PUBLISHED%22%7D%2C%22orderBy%22%3A%7B%22field%22%3A%22PASSED_AT%22%2C%22direction%22%3A%22DESC%22%7D%2C%22pagination%22%3A%7B%22page%22%3A3%2C%22pageSize%22%3A20%7D%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%2264cdd31e7f49c385660566f69f5340c90b2c4417999969089935b0078cf24415%22%7D%7D
Request Method
GET
Status Code
200 OK
Remote Address
18.64.8.45:443
Referrer Policy
same-origin

2) HTTP 헤더정보
origin
https://linkareer.com
priority
u=1, i
sec-ch-ua
"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-site
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36
3) Payload 정보
operationName=CoverLetterList&variables=%7B%22filterBy%22%3A%7B%22role%22%3A%22%EB%8D%B0%EC%9D%B4%ED%84%B0%22%2C%22types%22%3A%5B%22ALL%22%5D%2C%22status%22%3A%22PUBLISHED%22%7D%2C%22orderBy%22%3A%7B%22field%22%3A%22PASSED_AT%22%2C%22direction%22%3A%22DESC%22%7D%2C%22pagination%22%3A%7B%22page%22%3A3%2C%22pageSize%22%3A20%7D%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%2264cdd31e7f49c385660566f69f5340c90b2c4417999969089935b0078cf24415%22%7D%7D
4) 응답의 일부를 Response 에서 일부를 복사해서 넣어주기 (전체는 토큰 수 제한으로 어렵습니다.)
{
    "data": {
        "coverLetters": {
            "edges": [
                {
                    "node": {
                        "id": "28389",
                        "isScrapped": false,
                        "role": "공공데이터 인턴",
                        "contentSummaryMobile": "1. 지원동기 및 수료 후 향후 계획을 기술해 주십시오.\n\n경제학부를 전공하고 금융전문가를 준비하면서, 디지털 전환 시대에 필요한 역량이 무엇인지 고민하였습니다. 오픈뱅킹과 마이데이터 등 개방형 혁신 인프라가 가속화되면서 빅데이터 기반의 서비스 제공이 금융권의 새로운 ",
                        "organizationName": "한국지능정보사회진흥원",
                        "types": [
                            "PUBLIC_INSTITUTIONS",
                            "INTERN"
                        ],
5)한페이지가 성공적으로 수집되는지 확인하고 sqlitedb 파일로 저장하고 JSON 데이터는 별도의 컬럼으로 저장할 것
6)첫번째 페이지부터 마지막 페이지까지 수집이 다되면 수집이 잘 되었는지 확인하고 결과 리포트를 보여줄 것
7. 구직자 스펙 정보는 수집 가능한 정보를 최대한 모두 수집할 것. 특히 지원 직무, 희망 직무, 전공, 학력, 학점, 보유 자격증, 어학 성적, 인턴 경험, 프로젝트 경험, 공모전 경험, 수상 경험, 대외활동, 교육·부트캠프 수료 경험, 포트폴리오 보유 여부, GitHub 보유 여부, 기술 스택 등을 반드시 수집할 것.

8. 해당 정보를 수집하는 목적은 데이터 직무 채용공고에서 기업이 요구하는 스펙과 실제 구직자·취업준비생이 보유하거나 준비하는 스펙 간의 차이(Gap)를 분석하기 위한 것이다. 최종적으로 기업 요구 역량과 구직자 준비 현황의 미스매치를 파악하고, 직무별 취업 준비 방향 및 스펙 추천 서비스 기획에 활용할 수 있는 기초 자료를 구축할 것.

9. 구직자 목록 또는 합격자 사례 목록이 수집되었다면 개별 상세페이지 정보까지 추가로 수집할 것. 목록 데이터와 상세페이지 데이터는 별도의 테이블로 구성하며, 추후 지원자 ID, 게시글 ID, 사례 ID 또는 상세페이지 URL 등을 기준으로 조인할 수 있도록 설계할 것.

10. 상세페이지에서는 기본 스펙 정보와 더불어 자기소개서 내용, 지원 직무, 지원 기업, 합격 여부, 지원 시기, 직무 관련 경험, 프로젝트 경험, 사용 기술, 자격증 취득 내용, 교육 경험, 인턴 경험, 공모전·수상 경험, 포트폴리오 언급, GitHub 언급, 직무 준비 과정 등 수집 가능한 모든 정보를 최대한 수집할 것.

11. 기술 스택은 반드시 표준화할 것. 예를 들어 Python, SQL, R, Excel, Tableau, Power BI, AWS, Docker, Kafka, Spark, Hadoop, 머신러닝, 딥러닝, LLM, PyTorch, TensorFlow 등의 키워드는 동일 기술의 표기 차이를 통합하여 분석 가능한 형태로 저장할 것.

12. 자격증 역시 표준화할 것. 예를 들어 SQLD, ADsP, ADP, 정보처리기사, 빅데이터분석기사, 컴퓨터활용능력 등은 약어·한글명·영문명 차이를 통합하여 동일 자격증으로 처리할 것.

13. 직무명 역시 표준화할 것. 예를 들어 데이터 분석가, Data Analyst, BI Analyst는 필요에 따라 동일 또는 유사 직무군으로 분류하고, 데이터 사이언티스트, 데이터 엔지니어, AI/ML 엔지니어 등은 별도의 직무군으로 구분할 것.

14. 원본 데이터와 가공 데이터를 분리하여 저장할 것. 원문 텍스트는 그대로 보존하고, 분석용 컬럼에서는 기술 스택, 자격증, 전공, 직무, 경험 유형 등을 정규화·구조화할 것.

15. 데이터베이스는 최소한 다음과 같이 분리하여 설계할 것.

* job_seekers: 구직자 또는 합격자 기본 정보
* seeker_details: 개별 상세페이지 및 자기소개서·경험 정보
* seeker_skills: 보유·언급 기술 스택
* seeker_certificates: 보유 자격증
* seeker_experiences: 인턴·프로젝트·공모전·대외활동 경험
* source_pages: 수집 출처 URL, 수집일시, 원본 식별정보

16. 각 정보에는 반드시 출처 URL과 수집일시를 함께 저장하여 데이터의 추적 가능성을 확보할 것.

17. 동일 구직자, 동일 합격 사례, 동일 게시글이 중복 저장되지 않도록 고유 식별자를 설계할 것. 가능한 경우 게시글 ID, 사례 ID, 상세페이지 URL 등을 UNIQUE KEY로 사용하고, 기존 데이터가 존재하면 INSERT가 아닌 UPSERT 방식으로 업데이트할 것.

18. 수집 요청을 보낼 때는 각 요청 사이에 0.1~1초 범위의 랜덤 대기시간을 적용하여 네트워크 부담을 줄일 것. 오류 발생 시 즉시 반복 요청하지 말고 지수 백오프 방식으로 재시도할 것.

19. robots.txt, 서비스 이용약관, 접근 권한 및 개인정보 보호 원칙을 준수할 것. 로그인 우회, CAPTCHA 우회, 접근 제한 회피 등 비정상적인 방식은 사용하지 말 것. 개인을 직접 식별할 수 있는 이름, 연락처, 이메일, 전화번호 등은 분석 목적에 불필요한 경우 수집하지 않거나 비식별화할 것.

20. 최종 데이터는 기존에 수집한 기업 채용공고 데이터와 비교할 수 있도록 공통 분석 기준을 맞출 것. 특히 다음 항목은 기업 요구 데이터와 구직자 데이터 양쪽에서 동일한 기준으로 비교 가능해야 한다.

* Python
* SQL
* R
* Excel
* 머신러닝
* 딥러닝
* LLM
* PyTorch
* TensorFlow
* AWS
* Docker
* Kafka
* Spark
* GitHub
* 포트폴리오
* 프로젝트 경험
* 인턴 경험
* 자격증
* 학력
* 전공

21. 최종적으로 다음 분석이 가능하도록 데이터를 구성할 것.

* 기업 요구율 vs 구직자 보유율
* 기업 요구율 vs 구직자 준비·언급률
* 직무별 스펙 Gap 분석
* 자격증 요구율 vs 실제 보유율
* 기술 스택 요구율 vs 실제 보유율
* 기업이 많이 요구하지만 구직자가 적게 준비하는 역량
* 기업은 적게 요구하지만 구직자가 과도하게 준비하는 스펙
* 합격자와 일반 취업준비생 간 스펙 차이
* 신입과 경력직 간 요구 스펙 차이
* 데이터 분석가, 데이터 사이언티스트, 데이터 엔지니어, AI/ML 직무별 미스매치 분석

수집 요청을 보낼때는 0.1~1초씩 쉬었다가 수집하게 할 것 네트워크 부담을 줄일 것
데이터베이스에 저장할 때는 중복데이터가 발생하지 않도록 기존 데이터가 있다면 업데이트 하는 방법으로 수집할 것