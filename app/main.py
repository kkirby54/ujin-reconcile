"""
FastAPI 애플리케이션
미수미지급금 대조 API 서버
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.core.reader import read_erp, read_bank
from app.core.normalize import find_best_match
from app.core.generator import build_upload_form_workbook

app = FastAPI(
    title="미수미지급금 대조 시스템",
    description="ERP 미수미지급금과 은행 거래내역을 대조하여 전표를 생성하는 API",
    version="1.0.0"
)

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/reconcile")
async def reconcile(erp: UploadFile = File(...), bank: UploadFile = File(...)):
    """
    ERP 미수미지급금 파일과 은행 거래내역 파일을 대조하여 Upload_form.xlsx 형식의 전표 생성
    
    Args:
        erp (UploadFile): ERP 미수미지급금 파일 (Excel)
        bank (UploadFile): 은행 거래내역 파일 (Excel/CSV)
        
    Returns:
        StreamingResponse: Upload_form.xlsx 형식의 전표 엑셀 파일
        
    Raises:
        HTTPException: 파일 읽기 실패 시 400 에러
    """
    try:
        # ERP 파일 읽기
        erp_mapping = read_erp(erp.file)
        
        # 은행 파일 읽기
        bank_rows = read_bank(bank.file)
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "파일 읽기 실패",
                "details": str(e)
            }
        )
    
    # 매칭 처리
    matches = []
    unmatched = []
    
    for bank_row in bank_rows:
        # 유사도 기반 매칭 (80% 이상 임계값)
        partner_info, similarity = find_best_match(
            bank_row["counter_raw"], 
            erp_mapping, 
            threshold=0.80
        )
        
        # 매칭 조건 확인: 거래처 매칭, 입출금 구분, 유효한 날짜
        if (partner_info and 
            bank_row["type"] in ("입금", "출금") and 
            bank_row["date"]):
            
            # 매칭 성공: 전표 데이터에 추가 (유사도 정보 포함)
            match_data = {
                **bank_row,
                **partner_info,
                "similarity": similarity
            }
            matches.append(match_data)
        else:
            # 매칭 실패: Unmatched에 추가
            unmatched.append(bank_row)
    
    # Upload_form.xlsx 형식으로 엑셀 파일 생성
    try:
        template_path = "Upload_form.xlsx"
        excel_buffer = build_upload_form_workbook(matches, unmatched, template_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "엑셀 파일 생성 실패",
                "details": str(e)
            }
        )
    
    # 응답 헤더에 통계 정보 추가
    headers = {
        "Content-Disposition": "attachment; filename=upload_form.xlsx",
        "X-Match-Count": str(len(matches)),
        "X-Unmatch-Count": str(len(unmatched)),
        "X-Total-Count": str(len(bank_rows))
    }
    
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    """웹 인터페이스 홈페이지"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.get("/api")
async def api_info():
    """API 정보"""
    return {
        "message": "미수미지급금 대조 시스템 API",
        "version": "1.0.0",
        "endpoints": {
            "GET /": "웹 인터페이스",
            "POST /reconcile": "ERP와 은행 파일을 대조하여 Upload_form.xlsx 형식의 전표 생성",
            "GET /api": "API 정보",
            "GET /health": "헬스 체크"
        }
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
