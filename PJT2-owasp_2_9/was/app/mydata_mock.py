from datetime import date, timedelta
import random


HOSPITALS = [
    "서울중앙의원",
    "동부보건의료원",
    "시민건강센터",
    "공공의료지원병원",
    "서부종합병원",
]

DEPARTMENTS = [
    "내과",
    "가정의학과",
    "정형외과",
    "소아청소년과",
    "이비인후과",
]

DIAGNOSES = [
    ("J00", "급성 비인두염(감기)"),
    ("K30", "기능성 소화불량"),
    ("M54.5", "요통"),
    ("E11.9", "2형 당뇨병(합병증 없음)"),
    ("I10", "본태성 고혈압"),
]

MEDICATIONS = [
    "아세트아미노펜 500mg",
    "메트포르민 500mg",
    "로사르탄 50mg",
    "에소메프라졸 20mg",
    "레보플록사신 250mg",
]

VACCINES = [
    "인플루엔자",
    "코로나19",
    "A형간염",
    "B형간염",
    "폐렴구균",
]

ALLERGIES = [
    "없음",
    "페니실린",
    "갑각류",
    "견과류",
    "꽃가루",
]


def _iso(dt):
    return dt.isoformat()


def generate_mock_medical_mydata(user):
    rng = random.Random(f"mydata:{user.id}:{user.username}:{user.email}")
    today = date.today()

    age = rng.randint(24, 68)
    birth_year = today.year - age
    birth_month = rng.randint(1, 12)
    birth_day = rng.randint(1, 28)
    birth_date = date(birth_year, birth_month, birth_day)
    gender = "M" if rng.randint(0, 1) == 0 else "F"
    blood_type = rng.choice(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])

    visit_count = rng.randint(3, 8)
    visits = []
    for _ in range(visit_count):
        code, name = rng.choice(DIAGNOSES)
        visit_date = today - timedelta(days=rng.randint(10, 360))
        visits.append(
            {
                "date": _iso(visit_date),
                "provider": rng.choice(HOSPITALS),
                "department": rng.choice(DEPARTMENTS),
                "diagnosisCode": code,
                "diagnosisName": name,
            }
        )
    visits.sort(key=lambda item: item["date"], reverse=True)

    medication_count = rng.randint(2, 5)
    medications = []
    for _ in range(medication_count):
        medications.append(
            {
                "name": rng.choice(MEDICATIONS),
                "dose": f"{rng.randint(1, 2)}정",
                "frequencyPerDay": rng.randint(1, 3),
                "days": rng.choice([3, 5, 7, 14, 30]),
            }
        )

    vaccinations = []
    for _ in range(rng.randint(1, 3)):
        shot_date = today - timedelta(days=rng.randint(30, 400))
        vaccinations.append(
            {
                "name": rng.choice(VACCINES),
                "date": _iso(shot_date),
                "doseNo": rng.randint(1, 3),
            }
        )
    vaccinations.sort(key=lambda item: item["date"], reverse=True)

    fasting_glucose = rng.randint(86, 130)
    hba1c = round(rng.uniform(5.1, 7.2), 1)
    systolic = rng.randint(108, 145)
    diastolic = rng.randint(68, 94)
    bmi = round(rng.uniform(19.1, 29.8), 1)
    total_cholesterol = rng.randint(155, 240)

    monthly_costs = []
    for month_offset in range(5, -1, -1):
        ref = today - timedelta(days=month_offset * 30)
        monthly_costs.append(
            {
                "month": f"{ref.year}-{ref.month:02d}",
                "outOfPocket": rng.randint(12000, 165000),
            }
        )
    out_of_pocket_total = sum(item["outOfPocket"] for item in monthly_costs)

    alerts = []
    if fasting_glucose >= 110:
        alerts.append("공복혈당이 경계 이상입니다.")
    if hba1c >= 6.5:
        alerts.append("당화혈색소가 높습니다.")
    if systolic >= 140 or diastolic >= 90:
        alerts.append("혈압이 높게 측정되었습니다.")
    if not alerts:
        alerts.append("현재 주요 이상 징후는 없습니다.")

    return {
        "source": "MOCK",
        "profile": {
            "name": user.full_name,
            "birthDate": _iso(birth_date),
            "gender": gender,
            "bloodType": blood_type,
            "allergy": rng.choice(ALLERGIES),
        },
        "insurance": {
            "type": "국민건강보험",
            "eligibility": "정상",
            "copayRate": rng.choice([0.2, 0.3, 0.4]),
        },
        "visits": visits,
        "medications": medications,
        "checkups": {
            "bloodPressure": f"{systolic}/{diastolic}",
            "fastingGlucose": fasting_glucose,
            "hba1c": hba1c,
            "totalCholesterol": total_cholesterol,
            "bmi": bmi,
        },
        "vaccinations": vaccinations,
        "costSummary": {
            "year": today.year,
            "outOfPocketTotal": out_of_pocket_total,
            "monthly": monthly_costs,
        },
        "alerts": alerts,
    }
