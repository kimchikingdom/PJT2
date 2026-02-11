import json
import random
import secrets
from datetime import date, timedelta
from types import SimpleNamespace

from app import db
from app.models import ProviderAccessToken, ProviderConsent, ProviderSubject, utc_now
from app.mydata_mock import generate_mock_medical_mydata


LAST_NAMES = [
    "김",
    "이",
    "박",
    "최",
    "정",
    "강",
    "조",
    "윤",
    "장",
    "임",
    "한",
    "오",
    "서",
    "신",
    "권",
    "황",
    "안",
    "송",
    "류",
    "홍",
]

GIVEN_SYLLABLE_1 = [
    "민",
    "서",
    "지",
    "도",
    "하",
    "유",
    "예",
    "준",
    "현",
    "수",
    "채",
    "은",
    "태",
    "성",
    "재",
    "우",
    "진",
    "나",
]

GIVEN_SYLLABLE_2 = [
    "수",
    "우",
    "민",
    "진",
    "아",
    "영",
    "호",
    "현",
    "준",
    "석",
    "은",
    "주",
    "훈",
    "빈",
    "연",
    "림",
    "지",
]


def _generate_korean_name(rng: random.Random) -> str:
    last = rng.choice(LAST_NAMES)
    given = rng.choice(GIVEN_SYLLABLE_1) + rng.choice(GIVEN_SYLLABLE_2)
    return last + given


def _generate_birth_date(rng: random.Random) -> date:
    year = rng.randint(1960, 2006)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return date(year, month, day)


def _generate_phone(rng: random.Random) -> str:
    mid = rng.randint(1000, 9999)
    last = rng.randint(1000, 9999)
    return f"010-{mid:04d}-{last:04d}"


def _generate_resident_number(rng: random.Random, birth: date, gender: str) -> str:
    # Korean RR-like mock format: YYMMDD-[1-4]XXXXXX (training/demo only)
    yy = birth.year % 100
    gender_code = 1
    if birth.year >= 2000:
        gender_code = 3 if gender == "M" else 4
    else:
        gender_code = 1 if gender == "M" else 2
    tail = rng.randint(0, 999999)
    return f"{yy:02d}{birth.month:02d}{birth.day:02d}-{gender_code}{tail:06d}"


def ensure_provider_subjects(count: int = 100) -> int:
    """
    Ensure provider has at least `count` subjects in DB.
    Returns number of subjects created.
    """

    existing = ProviderSubject.query.count()
    if existing >= count:
        return 0

    created = 0
    for idx in range(existing + 1, count + 1):
        rng = random.Random(f"provider-seed:{idx}")
        subject_ref = f"SUBJ-{idx:04d}"
        full_name = _generate_korean_name(rng)
        birth = _generate_birth_date(rng)
        gender = "M" if rng.randint(0, 1) == 0 else "F"
        phone = _generate_phone(rng)
        resident_number = _generate_resident_number(rng, birth, gender)

        pseudo_user = SimpleNamespace(
            id=idx,
            username=subject_ref.lower(),
            email=f"{subject_ref.lower()}@provider.local",
            full_name=full_name,
        )
        payload = generate_mock_medical_mydata(pseudo_user)
        payload["source"] = "PROVIDER_DB"
        payload["providerSubjectRef"] = subject_ref
        payload["profile"]["name"] = full_name
        payload["profile"]["birthDate"] = birth.isoformat()
        payload["profile"]["gender"] = gender

        db.session.add(
            ProviderSubject(
                subject_ref=subject_ref,
                full_name=full_name,
                birth_date=birth,
                gender=gender,
                resident_number=resident_number,
                phone=phone,
                payload_json=json.dumps(payload, ensure_ascii=False),
            )
        )
        created += 1

    db.session.commit()
    return created


def get_or_create_provider_consent(user) -> ProviderConsent:
    consent = ProviderConsent.query.filter_by(user_id=user.id).first()
    if consent:
        if consent.status != "active":
            consent.status = "active"
            consent.revoked_at = None
            db.session.commit()
        return consent

    # Prefer an unused subject (1:1 mapping between portal users and provider subjects).
    subject = (
        ProviderSubject.query.outerjoin(
            ProviderConsent, ProviderConsent.provider_subject_id == ProviderSubject.id
        )
        .filter(ProviderConsent.id.is_(None))
        .order_by(ProviderSubject.id.asc())
        .first()
    )
    if subject is None:
        subject = ProviderSubject.query.order_by(ProviderSubject.id.asc()).first()
    if subject is None:
        raise RuntimeError("Provider subjects are not seeded.")

    # Bind the selected provider subject to the portal user for realism in UI.
    if user.full_name and subject.full_name != user.full_name:
        try:
            payload = json.loads(subject.payload_json)
        except json.JSONDecodeError:
            payload = {}
        payload.setdefault("profile", {})
        payload["profile"]["name"] = user.full_name
        subject.full_name = user.full_name
        subject.payload_json = json.dumps(payload, ensure_ascii=False)

    consent = ProviderConsent(
        user_id=user.id,
        provider_subject_id=subject.id,
        status="active",
        consent_at=utc_now(),
    )
    db.session.add(consent)
    db.session.commit()
    return consent


def validate_provider_client(client_id: str, client_secret: str, expected_id: str, expected_secret: str) -> bool:
    return bool(client_id) and bool(client_secret) and client_id == expected_id and client_secret == expected_secret


def issue_provider_access_token(consent: ProviderConsent, client_id: str, ttl_seconds: int = 600) -> ProviderAccessToken:
    issued_at = utc_now()
    expires_at = issued_at + timedelta(seconds=max(int(ttl_seconds or 0), 30))
    token_str = secrets.token_urlsafe(32)
    token = ProviderAccessToken(
        token=token_str,
        client_id=client_id,
        consent_id=consent.id,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    db.session.add(token)
    db.session.commit()
    return token


def resolve_provider_access_token(token_str: str) -> ProviderAccessToken | None:
    if not token_str:
        return None
    token = ProviderAccessToken.query.filter_by(token=token_str).first()
    if token is None:
        return None
    if token.revoked_at is not None:
        return None
    if token.expires_at is not None and token.expires_at <= utc_now():
        return None
    return token


def fetch_provider_mydata_by_token(token_str: str) -> dict | None:
    token = resolve_provider_access_token(token_str)
    if token is None:
        return None
    consent = token.consent
    if consent is None or consent.status != "active":
        return None
    subject = consent.subject
    if subject is None:
        return None
    try:
        payload = json.loads(subject.payload_json)
    except json.JSONDecodeError:
        return None

    # When delivered through API, tag it accordingly.
    payload["source"] = "PROVIDER_API"
    payload["providerTokenId"] = token.id
    payload["providerConsentId"] = consent.id
    payload["providerSubjectRef"] = subject.subject_ref
    return payload


def portal_fetch_mydata_via_provider_api(user, client_id: str, ttl_seconds: int, seed_subjects: int = 100):
    """
    Portal-side orchestration that *looks like* calling an external provider:
    - Ensure provider dataset exists
    - Ensure user consent/link exists
    - Issue access token
    - Fetch data using that token
    """

    ensure_provider_subjects(seed_subjects)
    consent = get_or_create_provider_consent(user)
    token = issue_provider_access_token(consent, client_id=client_id, ttl_seconds=ttl_seconds)
    payload = fetch_provider_mydata_by_token(token.token)
    if payload is None:
        raise RuntimeError("Provider API returned no data.")
    return payload, consent, token

