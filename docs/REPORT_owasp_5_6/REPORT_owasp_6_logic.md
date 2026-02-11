# [취약점 분석 보고서] OWASP Top 10:2025 - A06: 비즈니스 로직 결함 (상태 전이 우회)

## 1. 개요 (Description)
- **항목**: OWASP Top 10:2025 - A06: Vulnerable Business Logic (취약한 비즈니스 로직)
- **취약점**: 상태 머신 우회 (State Machine Bypass) / 비정상적인 상태 전이
- **대상 엔드포인트**: `/complaints/<int:complaint_id>` (POST 요청)
- **내용**: 민원 처리 프로세스(`접수` -> `검토중` -> `완료/반려`)에서 현재 상태에 대한 검증 없이 관리자가 임의의 상태로 변경할 수 있는 취약점입니다.

## 2. 취약점 코드 분석 (Vulnerability Analysis)

### 2.1 취약한 라우트 로직
- **파일 위치**: `was/app/routes.py` ([L1262-L1276](file:///c:/workspace/PJT2/was/app/routes.py#L1262-L1276))
- **분석**:
    관리자가 민원 상세 페이지에서 상태 변경을 요청할 때, 서버는 단순히 새로운 상태 값이 유효한지(`validate_complaint_status`)만 확인하고, **현재 민원의 상태가 전이 가능한 상태인지**는 확인하지 않습니다.

```python
# [VULNERABLE CODE] was/app/routes.py:L1262
if request.method == "POST":
    if current_user.role != "admin":
        flash("상태 변경 권한이 없습니다.", "danger")
        return redirect(url_for("complaints_detail", complaint_id=complaint_id))
    
    status = request.form.get("status", complaint.status)
    errors = validate_complaint_status(status) # 단순히 값이 세트 내에 있는지만 확인
    if errors:
        flash_errors(errors)
        return redirect(url_for("complaints_detail", complaint_id=complaint_id))
    
    # [PROBLEM] 현재 complaint.status가 'received'인데도 바로 'resolved'로 변경 가능
    complaint.status = status 
    complaint.assigned_admin_id = current_user.id
    db.session.commit()
```

### 2.2 부족한 검증 함수
- **파일 위치**: `was/app/validators.py` ([L102-L105](file:///c:/workspace/PJT2/was/app/validators.py#L102-L105))
- **분석**:
    해당 함수는 리스트 내에 값이 포함되어 있는지만 체크할 뿐, 비즈니스 규칙(비가역적 상태 전이 등)을 적용하지 않습니다.

```python
def validate_complaint_status(status):
    if status not in COMPLAINT_STATUS_SET:
        return ["민원 상태 값이 올바르지 않습니다."]
    return []
```

## 3. 공격 시나리오 (Attack Scenario)
1. **정상 프로세스 우회**: 실제 검토 과정을 거치지 않고 `접수(received)` 상태의 민원을 즉시 `처리완료(resolved)`로 변경하여 행정 신뢰성을 저해할 수 있습니다.
2. **상태 되돌리기**: 이미 `처리완료(resolved)`된 민원을 다시 `접수(received)` 상태로 돌리는 등의 비정상적인 데이터 조작이 가능합니다.
3. **사회공학적 기법 결합**: 공격자가 관리자 계정을 탈취하거나 내부자일 경우, 특정 민원 처리를 의도적으로 건너뜀으로써 업무 프로세스를 교란할 수 있습니다.

## 4. 대응 방안 (Remediation)
- **상태 전이 맵 도입**: 특정 상태에서 전이 가능한 다음 상태를 사전에 정의하고 이를 검증하는 로직을 추가해야 합니다.
    - `received` -> `in_review`, `rejected` 가능
    - `in_review` -> `resolved`, `rejected` 가능
    - `resolved`, `rejected` -> 전이 불가 (최종 상태)
- **서버 측 현재 상태 체크**: POST 요청 처리 시 데이터베이스에서 현재 상태를 다시 조회하여 규칙에 맞는지 확인합니다.
