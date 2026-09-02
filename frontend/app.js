const inputText = document.getElementById("inputText");
const analyzeBtn = document.getElementById("analyzeBtn");
const loading = document.getElementById("loading");
const resultDiv = document.getElementById("result");
const sampleButtonsDiv = document.getElementById("sampleButtons");

const imageFile = document.getElementById("imageFile");
const imageDropZone = document.getElementById("imageDropZone");
const imageDropLabel = document.getElementById("imageDropLabel");
const imagePreview = document.getElementById("imagePreview");
const removeImageBtn = document.getElementById("removeImageBtn");

let selectedImageFile = null;

// 이미지 선택 (클릭)
imageFile.addEventListener("change", (e) => {
  if (e.target.files && e.target.files[0]) {
    handleImageSelect(e.target.files[0]);
  }
});

// 드래그 앤 드롭
imageDropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  imageDropZone.classList.add("dragover");
});
imageDropZone.addEventListener("dragleave", () => {
  imageDropZone.classList.remove("dragover");
});
imageDropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  imageDropZone.classList.remove("dragover");
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    handleImageSelect(e.dataTransfer.files[0]);
  }
});

function handleImageSelect(file) {
  if (!file.type.startsWith("image/")) {
    alert("이미지 파일만 업로드할 수 있습니다.");
    return;
  }
  selectedImageFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    imagePreview.src = e.target.result;
    imagePreview.classList.remove("hidden");
    imageDropLabel.classList.add("hidden");
  };
  reader.readAsDataURL(file);
  removeImageBtn.classList.remove("hidden");
}

function clearSelectedImage() {
  selectedImageFile = null;
  imageFile.value = "";
  imagePreview.removeAttribute("src");
  imagePreview.classList.add("hidden");
  imageDropLabel.classList.remove("hidden");
  removeImageBtn.classList.add("hidden");
}

removeImageBtn.addEventListener("click", (e) => {
  e.preventDefault();
  clearSelectedImage();
});

// 샘플 버튼 로드
async function loadSamples() {
  try {
    const res = await fetch("/api/samples");
    const samples = await res.json();
    Object.entries(samples).forEach(([key, sample]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sample-btn";
      btn.textContent = sample.label;
      btn.onclick = () => {
        inputText.value = sample.text;
        clearSelectedImage();
        resultDiv.classList.add("hidden");
        inputText.focus();
      };
      sampleButtonsDiv.appendChild(btn);
    });
  } catch (e) {
    console.error("샘플 로드 실패", e);
  }
}

function stageLabel(stage) {
  const labels = {
    0: "해당없음",
    1: "1단계 · 접촉",
    2: "2단계 · 신뢰구축",
    3: "3단계 · 고립유도",
    4: "4단계 · 정보/앱 요구",
    5: "5단계 · 이체/인출",
  };
  return labels[stage] ?? `${stage}단계`;
}

function riskLevel(score) {
  if (score >= 70) return { level: "danger", label: "위험" };
  if (score >= 30) return { level: "warn", label: "주의" };
  return { level: "safe", label: "안전" };
}

function riskColorClass(linkRisk) {
  if (linkRisk === "위험") return "link-danger";
  if (linkRisk === "의심") return "link-warn";
  return "link-safe";
}

function renderResult(data) {
  const { level, label } = riskLevel(data.risk_score);

  const evidenceQuotes = data.evidence_quotes || [];
  const evidenceVisibleCount = 2;
  const evidenceHasMore = evidenceQuotes.length > 3;
  const evidenceVisible = evidenceHasMore
    ? evidenceQuotes.slice(0, evidenceVisibleCount)
    : evidenceQuotes;
  const evidenceExtra = evidenceHasMore ? evidenceQuotes.slice(evidenceVisibleCount) : [];

  const evidenceHtml = evidenceQuotes.length
    ? `${evidenceVisible.map((q) => `<div class="evidence-quote">"${escapeHtml(q)}"</div>`).join("")}${
        evidenceHasMore
          ? `<div class="evidence-extra hidden" id="evidenceExtra">${evidenceExtra
              .map((q) => `<div class="evidence-quote">"${escapeHtml(q)}"</div>`)
              .join("")}</div>
             <button type="button" class="evidence-toggle-btn" id="evidenceToggleBtn">근거 더보기 (+${evidenceExtra.length})</button>`
          : ""
      }`
    : "<p>해당 없음</p>";

  const nextMovesHtml = (data.predicted_next_moves || []).length
    ? `<ul>${data.predicted_next_moves.map((m) => `<li>${escapeHtml(m)}</li>`).join("")}</ul>`
    : "<p>예측된 다음 요구 없음</p>";

  const linkFindings = data.link_findings || [];
  const linkHtml = linkFindings.length
    ? `
      <div class="result-section">
        <h3>발견된 링크 분석 (${linkFindings.length}개)</h3>
        ${linkFindings
          .map(
            (l) => `
          <div class="link-item ${riskColorClass(l.risk)}">
            <div class="link-url">${escapeHtml(l.url)}</div>
            <div class="link-risk-badge">${escapeHtml(l.risk)}</div>
            <ul class="link-reasons">${l.reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
          </div>`
          )
          .join("")}
      </div>`
    : "";

  const extractedTextHtml = data.extracted_text
    ? `
      <div class="result-section">
        <h3>이미지에서 인식된 대화 내용</h3>
        <div class="extracted-text-box">${escapeHtml(data.extracted_text)}</div>
      </div>`
    : "";

  const shareBlock = data.share_message
    ? `
      <div class="result-section">
        <h3>가족·은행 전달용 공유 문구</h3>
        <div class="share-box" id="shareBox">${escapeHtml(data.share_message)}</div>
        <button type="button" class="copy-btn" id="copyBtn">문구 복사하기</button>
      </div>`
    : "";

  resultDiv.className = `result ${level}`;
  resultDiv.innerHTML = `
    <div class="result-header">
      <div class="result-header-text">
        <span class="result-badge">${label}</span>
        <span class="scam-type">${escapeHtml(data.scam_type)}</span>
      </div>
      <div class="risk-ring" style="--pct:${data.risk_score}">
        <span class="risk-ring-value">${data.risk_score}%</span>
      </div>
    </div>

    <div class="result-body">
      <div class="result-section">
        <h3>진행 단계</h3>
        <p>${stageLabel(data.stage)}</p>
      </div>

      ${extractedTextHtml}

      <div class="result-section">
        <h3>판단 근거 (원문 인용)</h3>
        ${evidenceHtml}
      </div>

      ${linkHtml}

      <div class="result-section">
        <h3>다음에 요구할 가능성이 높은 행동</h3>
        ${nextMovesHtml}
      </div>

      <div class="result-section">
        <h3>지금 해야 할 행동</h3>
        <p>${escapeHtml(data.response_guide)}</p>
      </div>

      ${shareBlock}

      <div class="reset-row">
        <button type="button" class="reset-btn" id="resetBtn">다시 분석하기</button>
      </div>
    </div>
  `;
  resultDiv.classList.remove("hidden");

  const evidenceToggleBtn = document.getElementById("evidenceToggleBtn");
  if (evidenceToggleBtn) {
    const evidenceExtraEl = document.getElementById("evidenceExtra");
    evidenceToggleBtn.onclick = () => {
      const isHidden = evidenceExtraEl.classList.contains("hidden");
      evidenceExtraEl.classList.toggle("hidden");
      evidenceToggleBtn.textContent = isHidden ? "접기" : `근거 더보기 (+${evidenceExtra.length})`;
    };
  }

  const copyBtn = document.getElementById("copyBtn");
  if (copyBtn) {
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(data.share_message);
      copyBtn.textContent = "복사됨";
      setTimeout(() => (copyBtn.textContent = "문구 복사하기"), 1500);
    };
  }

  const resetBtn = document.getElementById("resetBtn");
  if (resetBtn) {
    resetBtn.onclick = () => {
      inputText.value = "";
      clearSelectedImage();
      resultDiv.classList.add("hidden");
      resultDiv.innerHTML = "";
      window.scrollTo({ top: 0, behavior: "smooth" });
      inputText.focus();
    };
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function handleAnalyze() {
  const text = inputText.value.trim();
  if (!text && !selectedImageFile) {
    alert("분석할 텍스트를 입력하거나 스크린샷을 첨부해주세요.");
    return;
  }

  analyzeBtn.disabled = true;
  loading.classList.remove("hidden");
  resultDiv.classList.add("hidden");

  try {
    let res;
    if (selectedImageFile) {
      const formData = new FormData();
      formData.append("file", selectedImageFile);
      if (text) formData.append("text", text);
      res = await fetch("/api/analyze-image", {
        method: "POST",
        body: formData,
      });
    } else {
      res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
    }

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "분석 요청이 실패했습니다.");
    }

    const data = await res.json();
    renderResult(data);
  } catch (e) {
    resultDiv.className = "result";
    resultDiv.innerHTML = `<div class="error-box">오류: ${escapeHtml(e.message)}</div>`;
    resultDiv.classList.remove("hidden");
  } finally {
    analyzeBtn.disabled = false;
    loading.classList.add("hidden");
  }
}

analyzeBtn.addEventListener("click", handleAnalyze);
loadSamples();
