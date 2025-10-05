"""
이름 정규화 모듈
ERP 거래처명과 은행 거래처명을 정확히 매칭하기 위한 정규화 함수
"""
import regex as re
import unicodedata

# 회사명 관련 키워드 제거용
CORP_KEYWORDS = [
    "(주)", "주식회사", "㈜", "유한회사", 
    "co.,ltd", "co.", "co", "inc", "ltd", "llc", "company"
]

# 한글 자모 분해용 상수
KOREAN_FIRST = ord('ㄱ')  # 초성 시작
KOREAN_MIDDLE = ord('ㅏ')  # 중성 시작
KOREAN_LAST = ord('ㄱ')  # 종성 시작 (초성과 동일)
KOREAN_COMPLETE = ord('가')  # 완성형 한글 시작

def normalize_name(s: str) -> str:
    """
    거래처명을 기본적으로 정규화 (특수문자, 회사명 키워드만 제거)
    
    Args:
        s (str): 원본 거래처명
        
    Returns:
        str: 정규화된 거래처명
    """
    if not isinstance(s, str):
        return ""
    
    # Unicode 정규화 (NFKC)
    s = unicodedata.normalize("NFKC", s)
    
    # 공백 제거 및 소문자 변환
    s = s.strip().lower()
    
    # 회사명 키워드 제거
    for keyword in CORP_KEYWORDS:
        s = s.replace(keyword, "")
    
    # 괄호 및 그 안의 내용 제거 (예: "(H", "(주)" 등)
    s = re.sub(r'\([^)]*\)', '', s)
    
    # 하이픈, 슬래시, 언더스코어 제거
    s = re.sub(r'[-/_]', '', s)
    
    # 숫자 제거 (회사명에서 불필요한 숫자)
    s = re.sub(r'\d+', '', s)
    
    # 특수문자 및 공백 제거 (한글, 영문만 유지)
    s = re.sub(r'[^\p{L}]+', '', s)
    
    return s


def extract_bracket_contents(s: str) -> list:
    """
    괄호 안의 내용들을 추출
    
    Args:
        s (str): 원본 문자열
        
    Returns:
        list: 괄호 안의 내용 리스트
    """
    if not isinstance(s, str):
        return []
    
    import re
    # 괄호 안의 내용 추출 (중첩된 괄호는 고려하지 않음)
    matches = re.findall(r'\(([^)]+)\)', s)
    return [match.strip() for match in matches if match.strip()]


def decompose_korean(char):
    """
    한글 문자를 초성, 중성, 종성으로 분해
    
    Args:
        char (str): 한글 문자 하나
        
    Returns:
        tuple: (초성, 중성, 종성) 또는 None
    """
    if not char or len(char) != 1:
        return None
    
    code = ord(char)
    
    # 완성형 한글 범위 확인
    if KOREAN_COMPLETE <= code < KOREAN_COMPLETE + 11172:  # 가~힣
        # 유니코드 한글 분해 공식
        base = code - KOREAN_COMPLETE
        first = base // (21 * 28)
        middle = (base % (21 * 28)) // 28
        last = base % 28
        
        # 초성, 중성, 종성으로 변환
        first_char = chr(KOREAN_FIRST + first)
        middle_char = chr(KOREAN_MIDDLE + middle)
        last_char = chr(KOREAN_FIRST + last) if last > 0 else ''
        
        return (first_char, middle_char, last_char)
    
    # 자모만 있는 경우
    elif KOREAN_FIRST <= code < KOREAN_FIRST + 30:  # ㄱ~ㅎ
        return (char, '', '')
    elif KOREAN_MIDDLE <= code < KOREAN_MIDDLE + 21:  # ㅏ~ㅣ
        return ('', char, '')
    
    return None


def korean_similarity(s1: str, s2: str) -> float:
    """
    한글 문자열 간의 유사도를 계산
    
    Args:
        s1 (str): 첫 번째 문자열
        s2 (str): 두 번째 문자열
        
    Returns:
        float: 유사도 (0.0 ~ 1.0)
    """
    if not s1 and not s2:
        return 1.0
    
    if not s1 or not s2:
        return 0.0
    
    # 완전일치 확인
    if s1 == s2:
        return 1.0
    
    # 자모 분해
    def get_jamo_sequence(text):
        sequence = []
        for char in text:
            decomposed = decompose_korean(char)
            if decomposed:
                sequence.extend([c for c in decomposed if c])
            else:
                sequence.append(char)  # 한글이 아닌 문자는 그대로
        return sequence
    
    jamo1 = get_jamo_sequence(s1)
    jamo2 = get_jamo_sequence(s2)
    
    # 자모 시퀀스 간 Levenshtein Distance 계산
    distance = levenshtein_distance_jamo(jamo1, jamo2)
    max_length = max(len(jamo1), len(jamo2))
    
    if max_length == 0:
        return 1.0
    
    # 유사도 계산
    similarity = 1.0 - (distance / max_length)
    return max(0.0, similarity)


def levenshtein_distance_jamo(seq1: list, seq2: list) -> int:
    """
    자모 시퀀스 간의 Levenshtein Distance 계산
    
    Args:
        seq1 (list): 첫 번째 자모 시퀀스
        seq2 (list): 두 번째 자모 시퀀스
        
    Returns:
        int: 편집 거리
    """
    if len(seq1) < len(seq2):
        return levenshtein_distance_jamo(seq2, seq1)
    
    if len(seq2) == 0:
        return len(seq1)
    
    previous_row = list(range(len(seq2) + 1))
    for i, c1 in enumerate(seq1):
        current_row = [i + 1]
        for j, c2 in enumerate(seq2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    두 문자열 간의 Levenshtein Distance 계산
    
    Args:
        s1 (str): 첫 번째 문자열
        s2 (str): 두 번째 문자열
        
    Returns:
        int: 편집 거리
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def calculate_similarity(s1: str, s2: str) -> float:
    """
    두 문자열 간의 유사도를 계산 (한글 유사도 우선 적용)
    
    Args:
        s1 (str): 첫 번째 문자열
        s2 (str): 두 번째 문자열
        
    Returns:
        float: 유사도 (0.0 ~ 1.0)
    """
    if not s1 and not s2:
        return 1.0
    
    if not s1 or not s2:
        return 0.0
    
    # 정규화된 문자열로 유사도 계산
    norm1 = normalize_name(s1)
    norm2 = normalize_name(s2)
    
    if not norm1 and not norm2:
        return 1.0
    
    if not norm1 or not norm2:
        return 0.0
    
    # 완전일치 확인
    if norm1 == norm2:
        return 1.0
    
    # 한글 유사도 계산 (자모 분해 기반)
    korean_sim = korean_similarity(norm1, norm2)
    
    # 기존 Levenshtein Distance 계산 (백업용)
    distance = levenshtein_distance(norm1, norm2)
    max_length = max(len(norm1), len(norm2))
    basic_sim = 1.0 - (distance / max_length) if max_length > 0 else 0.0
    
    # 한글 유사도가 더 높으면 한글 유사도 사용, 아니면 기본 유사도 사용
    return max(korean_sim, basic_sim)


def smart_matching(target: str, candidates: dict, threshold: float = 0.80) -> tuple:
    """
    단계별 스마트 매칭 (다양한 케이스 커버)
    
    Args:
        target (str): 매칭할 대상 문자열
        candidates (dict): 후보 딕셔너리 {normalized_name: {"code": ..., "name": ...}}
        threshold (float): 유사도 임계값
        
    Returns:
        tuple: (매칭된 정보, 유사도) 또는 (None, 0.0)
    """
    if not target or not candidates:
        return None, 0.0
    
    # 1단계: 완전일치 확인 (정규화 후)
    normalized_target = normalize_name(target)
    if normalized_target in candidates:
        return candidates[normalized_target], 1.0
    
    # 2단계: 괄호 내용 추출 및 매칭
    bracket_contents = extract_bracket_contents(target)
    for content in bracket_contents:
        content_normalized = normalize_name(content)
        if content_normalized in candidates:
            return candidates[content_normalized], 0.95  # 높은 유사도
        
        # 괄호 내용과 유사도 매칭
        for normalized_name, candidate_info in candidates.items():
            similarity = calculate_similarity(content, candidate_info["name"])
            if similarity >= threshold:
                return candidate_info, similarity
    
    # 3단계: 괄호를 제거한 전체 문자열 매칭
    target_without_brackets = target.replace('(', '').replace(')', '')
    target_no_brackets_normalized = normalize_name(target_without_brackets)
    if target_no_brackets_normalized in candidates:
        return candidates[target_no_brackets_normalized], 0.9  # 높은 유사도
    
    # 4단계: 기본 유사도 매칭
    best_match = None
    best_similarity = 0.0
    
    for normalized_name, candidate_info in candidates.items():
        similarity = calculate_similarity(target, candidate_info["name"])
        
        if similarity >= threshold and similarity > best_similarity:
            best_match = candidate_info
            best_similarity = similarity
    
    return best_match, best_similarity


def find_best_match(target: str, candidates: dict, threshold: float = 0.80) -> tuple:
    """
    대상 문자열과 가장 유사한 후보를 찾아서 반환 (스마트 매칭 사용)
    
    Args:
        target (str): 매칭할 대상 문자열
        candidates (dict): 후보 딕셔너리 {normalized_name: {"code": ..., "name": ...}}
        threshold (float): 유사도 임계값 (기본값: 0.80)
        
    Returns:
        tuple: (매칭된 정보, 유사도) 또는 (None, 0.0)
    """
    return smart_matching(target, candidates, threshold)
