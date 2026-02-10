HEALTH_NEWS = [
    {
        "title": "2026 국가예방접종 지원 일정",
        "summary": "영유아, 임신부, 고위험군 대상 무료 예방접종 지원 기간을 안내합니다.",
        "target": "영유아/임신부/고위험군",
        "channel": "보건소 및 지정 의료기관",
    },
    {
        "title": "지역 응급의료기관 연계 강화",
        "summary": "야간/휴일 응급실 과밀 완화를 위한 권역 연계 체계를 운영합니다.",
        "target": "응급환자 및 보호자",
        "channel": "응급의료포털, 119",
    },
    {
        "title": "디지털 의료민원 원스톱 서비스",
        "summary": "진료기록 열람, 비용 문의, 민원 접수를 온라인에서 통합 처리합니다.",
        "target": "전 국민",
        "channel": "공공 의료 민원 포털",
    },
]

EMERGENCY_BANNER = {
    "active": True,
    "level": "warning",
    "title": "감염병/재난 의료 긴급 안내",
    "message": "고열, 호흡곤란 등 중증 증상이 있으면 즉시 119 또는 응급의료기관으로 연락하세요.",
    "contact": "응급의료상담 1339 · 재난안전 110",
}

HEALTH_PROGRAMS = [
    {
        "id": "vaccination",
        "name": "국가예방접종 지원",
        "category": "예방",
        "eligibility": "영유아, 임신부, 만 65세 이상",
        "how_to_apply": "신분증 지참 후 지정 의료기관 방문",
        "contact": "질병관리청 콜센터 1339",
        "documents": ["신분증", "임신확인서(해당 시)", "예방접종 수첩"],
    },
    {
        "id": "mental-care",
        "name": "정신건강 상담 연계",
        "category": "정신건강",
        "eligibility": "우울, 불안, 스트레스 상담이 필요한 주민",
        "how_to_apply": "지역 정신건강복지센터 예약 또는 전화 상담",
        "contact": "정신건강위기상담 1577-0199",
        "documents": ["신분증", "의뢰서(선택)"],
    },
    {
        "id": "medical-aid",
        "name": "의료비 지원(취약계층)",
        "category": "복지",
        "eligibility": "기초생활수급자, 차상위계층, 중증질환자",
        "how_to_apply": "주민센터 또는 보건소 신청",
        "contact": "보건복지상담센터 129",
        "documents": ["신분증", "소득 증빙서류", "진단서(해당 시)"],
    },
]

COMPLAINT_TYPE_GUIDE = [
    {
        "category": "진료 서비스",
        "code": "medical",
        "description": "진료 지연, 진료 과정 문의, 의료진 응대 관련",
        "sla_days": "3~5 영업일",
        "required_docs": "진료일시, 기관명, 영수증/접수증",
    },
    {
        "category": "보험/진료비",
        "code": "billing",
        "description": "진료비 산정, 본인부담금, 청구 오류 문의",
        "sla_days": "5~7 영업일",
        "required_docs": "진료비 계산서, 영수증",
    },
    {
        "category": "개인정보/의무기록",
        "code": "privacy",
        "description": "의무기록 열람/정정, 개인정보 처리 문의",
        "sla_days": "7~10 영업일",
        "required_docs": "본인확인 서류, 위임장(대리인 시)",
    },
    {
        "category": "시설/접근성",
        "code": "facility_access",
        "description": "편의시설, 이동약자 접근성, 환경개선 요청",
        "sla_days": "5~10 영업일",
        "required_docs": "발생 위치, 시간, 사진(선택)",
    },
    {
        "category": "예방접종",
        "code": "vaccination",
        "description": "접종 대상/일정/증명서 발급 문의",
        "sla_days": "2~4 영업일",
        "required_docs": "접종일자, 기관명, 대상자 정보",
    },
    {
        "category": "디지털 서비스",
        "code": "digital_service",
        "description": "로그인, 인증, 페이지 오류, 모바일 사용 문제",
        "sla_days": "1~3 영업일",
        "required_docs": "오류 화면 캡처, 발생 시각, 사용 기기",
    },
]

VACCINATION_CHECKUP_CALENDAR = [
    {
        "month": "2026-02",
        "title": "고위험군 인플루엔자 추가접종",
        "target": "만 65세 이상, 만성질환자",
        "support": "무료 접종",
        "channel": "지정 의료기관",
    },
    {
        "month": "2026-03",
        "title": "국가건강검진 집중안내",
        "target": "홀수년도 출생 성인",
        "support": "기본검진 본인부담 없음",
        "channel": "검진기관 예약",
    },
    {
        "month": "2026-04",
        "title": "영유아 예방접종 주간",
        "target": "12세 이하 아동",
        "support": "국가필수예방접종 지원",
        "channel": "보건소/위탁의료기관",
    },
    {
        "month": "2026-05",
        "title": "모자보건 검진 캠페인",
        "target": "임신부, 영유아 보호자",
        "support": "상담/검사비 일부 지원",
        "channel": "보건소",
    },
]

MEDICAL_SUPPORT_PROGRAMS = [
    {
        "name": "저소득층 의료비 지원",
        "target": "기초생활수급자/차상위계층",
        "benefit": "입원/외래 본인부담금 일부 지원",
        "how_to_apply": "주민센터 또는 보건소 신청",
        "contact": "보건복지상담센터 129",
    },
    {
        "name": "중증질환 의료비 지원",
        "target": "암, 희귀난치성 질환자",
        "benefit": "고액 의료비 경감",
        "how_to_apply": "진단서 지참 후 관할 기관 접수",
        "contact": "국민건강보험공단 1577-1000",
    },
    {
        "name": "산모/영유아 건강지원",
        "target": "임신부 및 만 2세 이하 영유아",
        "benefit": "검진/예방접종/건강관리 지원",
        "how_to_apply": "보건소 모자보건실 신청",
        "contact": "보건소 대표번호",
    },
]

RECORDS_PRIVACY_PROCEDURE = [
    {
        "step": 1,
        "title": "신청서 작성",
        "detail": "의무기록 열람/정정 요청서와 본인확인 정보를 입력합니다.",
    },
    {
        "step": 2,
        "title": "본인확인",
        "detail": "신분증 또는 공동인증서를 통해 신청자 본인을 확인합니다.",
    },
    {
        "step": 3,
        "title": "기관 검토",
        "detail": "의료기관 및 담당부서가 요청 내용을 검토합니다.",
    },
    {
        "step": 4,
        "title": "결과 통지",
        "detail": "승인/보완/반려 결과를 포털 알림과 문자로 안내합니다.",
    },
]

COMPLAINT_STATUS_FAQ = [
    {
        "status": "received",
        "title": "접수",
        "description": "민원이 정상 등록되었으며 담당자 배정 전 상태입니다.",
    },
    {
        "status": "in_review",
        "title": "검토중",
        "description": "담당자가 사실 확인과 처리 방안을 검토하고 있습니다.",
    },
    {
        "status": "resolved",
        "title": "처리완료",
        "description": "검토 및 조치가 완료되어 결과를 확인할 수 있습니다.",
    },
    {
        "status": "rejected",
        "title": "반려",
        "description": "필수 정보 부족 또는 관할 외 사유로 반려된 상태입니다.",
    },
]

HEALTH_FAQ = [
    {
        "question": "민원 처리 기간은 얼마나 걸리나요?",
        "answer": "일반 민원은 접수 후 3~7영업일, 개인정보 관련 민원은 최대 10영업일 이내 처리됩니다.",
    },
    {
        "question": "민원 카테고리를 잘못 선택했어요.",
        "answer": "민원 상세 페이지에서 추가 설명을 남기거나 재접수해 주세요. 관리자가 분류를 재조정할 수 있습니다.",
    },
    {
        "question": "응급 상황에서 포털 민원 접수를 해야 하나요?",
        "answer": "응급 상황은 즉시 119 또는 응급의료기관으로 연락하세요. 포털은 비응급 행정/문의 처리용입니다.",
    },
]

REGIONAL_CENTERS = [
    {
        "region": "서울",
        "name": "서울권역 공공의료지원센터",
        "service": "응급 연계, 고위험군 상담, 예방접종 안내",
        "phone": "02-120",
        "address": "서울특별시 종로구 세종대로 110",
        "night_weekend": "야간진료 연계: 가능 / 주말상담: 가능",
        "map_url": "https://map.naver.com/",
    },
    {
        "region": "부산",
        "name": "부산권역 공공의료상담센터",
        "service": "의료비 지원 안내, 민원 상담",
        "phone": "051-120",
        "address": "부산광역시 연제구 중앙대로 1001",
        "night_weekend": "야간진료 연계: 가능 / 주말상담: 가능",
        "map_url": "https://map.naver.com/",
    },
    {
        "region": "대전",
        "name": "충청권 공공보건 연계센터",
        "service": "정신건강 연계, 지역 보건소 연계",
        "phone": "042-120",
        "address": "대전광역시 서구 둔산로 100",
        "night_weekend": "야간진료 연계: 일부 / 주말상담: 가능",
        "map_url": "https://map.naver.com/",
    },
]
