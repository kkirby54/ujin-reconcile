// DOM 요소들
const uploadForm = document.getElementById('uploadForm');
const erpFileInput = document.getElementById('erpFile');
const bankFileInput = document.getElementById('bankFile');
const submitBtn = document.getElementById('submitBtn');
const progressSection = document.getElementById('progressSection');
const resultSection = document.getElementById('resultSection');
const errorSection = document.getElementById('errorSection');
const downloadBtn = document.getElementById('downloadBtn');

// 파일명 표시 요소들
const erpFileName = erpFileInput.parentElement.querySelector('.file-name');
const bankFileName = bankFileInput.parentElement.querySelector('.file-name');

// 전역 변수
let downloadUrl = null;

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    setupFileInputs();
    setupFormValidation();
    setupDragAndDrop();
});

// 파일 입력 설정
function setupFileInputs() {
    erpFileInput.addEventListener('change', function(e) {
        updateFileName(e.target, erpFileName);
        validateForm();
    });

    bankFileInput.addEventListener('change', function(e) {
        updateFileName(e.target, bankFileName);
        validateForm();
    });
}

// 파일명 업데이트
function updateFileName(input, nameElement) {
    if (input.files && input.files[0]) {
        nameElement.textContent = input.files[0].name;
        nameElement.classList.add('has-file');
    } else {
        nameElement.textContent = '파일을 선택하세요';
        nameElement.classList.remove('has-file');
    }
}

// 폼 유효성 검사
function setupFormValidation() {
    const inputs = [erpFileInput, bankFileInput];
    
    inputs.forEach(input => {
        input.addEventListener('change', validateForm);
    });
}

function validateForm() {
    const hasErpFile = erpFileInput.files && erpFileInput.files[0];
    const hasBankFile = bankFileInput.files && bankFileInput.files[0];
    
    const submitButton = uploadForm.querySelector('.submit-btn');
    
    if (hasErpFile && hasBankFile) {
        submitButton.disabled = false;
    } else {
        submitButton.disabled = true;
    }
}

// 드래그 앤 드롭 설정
function setupDragAndDrop() {
    const fileBoxes = document.querySelectorAll('.file-input-box');
    
    fileBoxes.forEach((box, index) => {
        const input = index === 0 ? erpFileInput : bankFileInput;
        const nameElement = index === 0 ? erpFileName : bankFileName;
        
        box.addEventListener('dragover', function(e) {
            e.preventDefault();
            box.classList.add('dragover');
        });
        
        box.addEventListener('dragleave', function(e) {
            e.preventDefault();
            box.classList.remove('dragover');
        });
        
        box.addEventListener('drop', function(e) {
            e.preventDefault();
            box.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                updateFileName(input, nameElement);
                validateForm();
            }
        });
    });
}

// 폼 제출 처리
uploadForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('erp', erpFileInput.files[0]);
    formData.append('bank', bankFileInput.files[0]);
    
    // UI 상태 변경
    showProgress();
    
    try {
        const response = await fetch('./reconcile', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // 성공 처리
            const blob = await response.blob();
            downloadUrl = URL.createObjectURL(blob);
            
            // 통계 정보 추출 (응답 헤더에서)
            const matchCount = response.headers.get('X-Match-Count') || '0';
            const unmatchCount = response.headers.get('X-Unmatch-Count') || '0';
            
            showResult(matchCount, unmatchCount);
        } else {
            // 오류 처리
            const errorData = await response.json();
            showError(errorData.error || '처리 중 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('네트워크 오류가 발생했습니다.');
    }
});

// 진행 상황 표시
function showProgress() {
    hideAllSections();
    progressSection.style.display = 'block';
}

// 결과 표시
function showResult(matchCount = '0', unmatchCount = '0') {
    hideAllSections();
    resultSection.style.display = 'block';
    
    // 통계 정보 업데이트
    document.getElementById('matchCount').textContent = matchCount;
    document.getElementById('unmatchCount').textContent = unmatchCount;
}

// 오류 표시
function showError(message) {
    hideAllSections();
    errorSection.style.display = 'block';
    document.getElementById('errorMessage').textContent = message;
}

// 모든 섹션 숨기기
function hideAllSections() {
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
}

// 다운로드 처리
downloadBtn.addEventListener('click', function() {
    if (downloadUrl) {
        const a = document.createElement('a');
        a.href = downloadUrl;
            a.download = 'upload_form.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
});

// 폼 리셋
function resetForm() {
    uploadForm.reset();
    erpFileName.textContent = '파일을 선택하세요';
    erpFileName.classList.remove('has-file');
    bankFileName.textContent = '파일을 선택하세요';
    bankFileName.classList.remove('has-file');
    
    hideAllSections();
    validateForm();
    
    if (downloadUrl) {
        URL.revokeObjectURL(downloadUrl);
        downloadUrl = null;
    }
}

// 파일 크기 제한 체크 (선택사항)
function validateFileSize(file, maxSizeMB = 10) {
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
        showError(`파일 크기가 너무 큽니다. ${maxSizeMB}MB 이하의 파일을 업로드해주세요.`);
        return false;
    }
    return true;
}

// 파일 확장자 체크
function validateFileExtension(file, allowedExtensions) {
    const fileName = file.name.toLowerCase();
    const hasValidExtension = allowedExtensions.some(ext => 
        fileName.endsWith(ext.toLowerCase())
    );
    
    if (!hasValidExtension) {
        showError(`지원하지 않는 파일 형식입니다. 허용된 형식: ${allowedExtensions.join(', ')}`);
        return false;
    }
    return true;
}

// 향상된 파일 검증
erpFileInput.addEventListener('change', function(e) {
    if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        if (!validateFileExtension(file, ['.xlsx', '.xls'])) {
            e.target.value = '';
            return;
        }
        if (!validateFileSize(file)) {
            e.target.value = '';
            return;
        }
    }
});

bankFileInput.addEventListener('change', function(e) {
    if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        if (!validateFileExtension(file, ['.xlsx', '.xls', '.csv'])) {
            e.target.value = '';
            return;
        }
        if (!validateFileSize(file)) {
            e.target.value = '';
            return;
        }
    }
});
