"""
파일 읽기 모듈
ERP 미수미지급금 파일과 은행 거래내역 파일을 읽고 파싱
"""
import pandas as pd
from .normalize import normalize_name


def read_erp(path_or_file):
    """
    ERP 미수미지급금 파일을 읽어서 거래처 매핑 딕셔너리 생성
    
    Args:
        path_or_file: 파일 경로 또는 파일 객체
        
    Returns:
        dict: 정규화된 거래처명 -> {"code": 코드, "name": 거래처명} 매핑
        
    Raises:
        ValueError: 헤더를 찾을 수 없거나 필수 컬럼이 없는 경우
    """
    # 먼저 헤더 행을 찾기 위해 데이터 타입을 문자열로 읽음
    df = pd.read_excel(path_or_file, header=None, dtype=str)
    
    # 첫 30행 내에서 "코드"와 "거래처"가 포함된 행 찾기
    header_idx = None
    for i in range(min(30, len(df))):
        row = df.iloc[i].astype(str).tolist()
        if any("코드" in str(x) for x in row) and any("거래처" in str(x) for x in row):
            header_idx = i
            break
    
    if header_idx is None:
        raise ValueError("ERP 헤더(코드/거래처명) 행을 찾지 못했습니다.")
    
    # 헤더 행을 기준으로 데이터 읽기
    df = pd.read_excel(path_or_file, header=header_idx, dtype=str)
    df.columns = df.columns.astype(str)  # 컬럼명을 문자열로 변환
    
    # 필수 컬럼 확인
    if not {"코드", "거래처명"}.issubset(df.columns):
        raise ValueError("ERP 파일에 '코드','거래처명' 컬럼이 없습니다.")
    
    # 필요한 컬럼만 선택하고 빈 행 제거
    df = df[["코드", "거래처명"]].dropna()
    
    # 정규화된 거래처명으로 매핑 딕셔너리 생성
    mapping = {}
    for _, row in df.iterrows():
        normalized_name = normalize_name(row["거래처명"])
        if normalized_name:
            mapping[normalized_name] = {
                "code": str(row["코드"]).strip(),
                "name": str(row["거래처명"]).strip()
            }
    
    return mapping


def read_bank(path_or_file):
    """
    은행 거래내역 파일을 읽어서 거래 데이터 리스트 생성
    
    Args:
        path_or_file: 파일 경로 또는 파일 객체
        
    Returns:
        list: 거래 데이터 딕셔너리 리스트
        
    Raises:
        ValueError: 필수 컬럼이 없는 경우
    """
    def _read_file():
        """파일 확장자에 따라 적절한 방법으로 파일 읽기 (7행부터 데이터 시작)"""
        filename = getattr(path_or_file, "filename", None) or str(path_or_file)
        
        if str(filename).lower().endswith(".csv"):
            # CSV 파일의 경우 헤더가 6행(0-based index 6)에 있다고 가정
            return pd.read_csv(path_or_file, header=6, dtype=str)
        else:
            # Excel 파일의 경우 헤더가 6행(0-based index 6)에 있다고 가정
            return pd.read_excel(path_or_file, header=6, dtype=str)
    
    df = _read_file()
    df.columns = df.columns.astype(str).str.strip()  # 컬럼명 정리
    
    # 필수 컬럼 확인 (실제 은행 파일 컬럼명 기준)
    required_columns = ["거래일시", "입금액(원)", "출금액(원)", "보낸분/받는분"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"은행 파일 필수 컬럼 누락: {missing_columns}")
    
    # 메모 컬럼이 없으면 빈 문자열로 추가
    if "적요" not in df.columns:
        df["적요"] = ""
    
    # 데이터 타입 변환 및 정리
    df["거래일시"] = pd.to_datetime(df["거래일시"], errors="coerce").dt.strftime("%Y-%m-%d")
    
    # 입금액과 출금액 정리
    df["입금액(원)"] = (df["입금액(원)"].astype(str)
                        .str.replace(",", "")
                        .str.replace(" ", ""))
    df["입금액(원)"] = pd.to_numeric(df["입금액(원)"], errors="coerce").fillna(0)
    
    df["출금액(원)"] = (df["출금액(원)"].astype(str)
                        .str.replace(",", "")
                        .str.replace(" ", ""))
    df["출금액(원)"] = pd.to_numeric(df["출금액(원)"], errors="coerce").fillna(0)
    
    # 거래 데이터 리스트 생성
    rows = []
    for _, row in df.iterrows():
        # 입금액과 출금액 중 0이 아닌 것으로 거래 구분
        deposit_amount = float(row["입금액(원)"]) if pd.notna(row["입금액(원)"]) else 0
        withdrawal_amount = float(row["출금액(원)"]) if pd.notna(row["출금액(원)"]) else 0
        
        # 거래 유형과 금액 결정
        if deposit_amount > 0:
            transaction_type = "입금"
            amount = deposit_amount
        elif withdrawal_amount > 0:
            transaction_type = "출금"
            amount = withdrawal_amount
        else:
            continue  # 입금액과 출금액이 모두 0인 경우 건너뛰기
        
        rows.append({
            "date": row["거래일시"],
            "amount": amount,
            "type": transaction_type,
            "counter_raw": str(row["보낸분/받는분"]),
            "memo": str(row["적요"]) if "적요" in row else ""
        })
    
    return rows
