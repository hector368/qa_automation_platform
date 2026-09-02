"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("aerForm");

  const fileInput = document.getElementById(
    "id_document"
  );

  const fileUiButton = document.getElementById(
    "fileUiBtn"
  );

  const uploadOrb = document.getElementById(
    "uploadOrb"
  );

  const uploader = document.getElementById(
    "uploader"
  );

  const fileHint = document.getElementById(
    "fileHint"
  );

  const filePill = document.getElementById(
    "filePill"
  );

  const fileName = document.getElementById(
    "fileName"
  );

  const fileSize = document.getElementById(
    "fileSize"
  );

  const clearFileButton = document.getElementById(
    "clearFileBtn"
  );

  const requirementPreview = document.getElementById(
    "reqPreview"
  );

  const requirementCount = document.getElementById(
    "reqCount"
  );

  const selectedCount = document.getElementById(
    "selCount"
  );

  const documentType = document.getElementById(
    "docType"
  );

  const requirementButton = document.getElementById(
    "reqPreviewBtn"
  );

  const submitButton = document.getElementById(
    "submitBtn"
  );

  const overlay = document.getElementById(
    "overlay"
  );

  const progressBar = document.getElementById(
    "progressBar"
  );

  const progressText = document.getElementById(
    "progressText"
  );

  const readyCard = document.getElementById(
    "readyCard"
  );

  const readyFilename = document.getElementById(
    "readyFilename"
  );

  const metricRequirements = document.getElementById(
    "mReq"
  );

  const metricTestCases = document.getElementById(
    "mTc"
  );

const metricTime = document.getElementById(
  "mTime"
);

  const metricTotal = document.getElementById(
    "mTotal"
  );

  const metricCost = document.getElementById(
    "mCost"
  );

  const downloadButton = document.getElementById(
    "downloadBtn"
  );

  const requirementReviewSection = document.getElementById(
  "requirementReviewSection"
);

const reviewAdequateCount = document.getElementById(
  "reviewAdequateCount"
);

const reviewHighCount = document.getElementById(
  "reviewHighCount"
);

const reviewSaturatedCount = document.getElementById(
  "reviewSaturatedCount"
);

const reviewPrevButton = document.getElementById(
  "reviewPrevBtn"
);

const reviewNextButton = document.getElementById(
  "reviewNextBtn"
);

const reviewRequirementId = document.getElementById(
  "reviewRequirementId"
);

const reviewRequirementTitle = document.getElementById(
  "reviewRequirementTitle"
);

const reviewLevel = document.getElementById(
  "reviewLevel"
);

const reviewReason = document.getElementById(
  "reviewReason"
);

const reviewAreasBlock = document.getElementById(
  "reviewAreasBlock"
);

const reviewAreas = document.getElementById(
  "reviewAreas"
);

const reviewFunctionalBlocks = document.getElementById(
  "reviewFunctionalBlocks"
);

const reviewFunctionalBlocksList = document.getElementById(
  "reviewFunctionalBlocksList"
);

const reviewPosition = document.getElementById(
  "reviewPosition"
);

  const documentInfoButton = document.getElementById(
  "docInfoBtn"
);
const requirementReviewInfoButton =
  document.getElementById(
    "requirementReviewInfoBtn"
  );
const projectIdElement = document.getElementById(
  "reqPid"
);
  const SweetAlert = window.Swal;

  const allowedExtensions = [
    ".pdf",
    ".docx",
  ];

let selectedFile = null;
let requirements = [];
let selectedRequirementIds = new Set();
let requirementReviews = new Map();
let hasExceptionsSection = false;
let includeExceptions = false;
let currentReviewIndex = 0;
let projectId = "";
let lastDownloadUrl = "";
let analyzeController = null;
  if (!form) {
    return;
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;

    const parts = value.split(
      `; ${name}=`
    );

    if (parts.length !== 2) {
      return "";
    }

    return (
      parts.pop().split(";").shift()
      || ""
    );
  }

  function bytesToMegabytes(bytes) {
    return (
      Number(bytes || 0)
      / (1024 * 1024)
    ).toFixed(2);
  }

  function isAllowedFile(file) {
    const filename = String(
      file?.name || ""
    ).toLowerCase();

    return allowedExtensions.some(
      extension => filename.endsWith(
        extension
      )
    );
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
  
  function getProjectId(requirementList) {
  if (
    !Array.isArray(requirementList)
    || requirementList.length === 0
  ) {
    return "Not detected";
  }

  const requirementId = String(
    requirementList[0]?.requirement_id
    || ""
  ).trim();

  const parts = requirementId.split(".");

  if (parts.length !== 3) {
    return "Not detected";
  }

  return parts
    .slice(0, 2)
    .join(".");
}

async function showError(message) {
  setOverlay(false);

  if (SweetAlert) {
    await SweetAlert.fire({
      icon: "error",
      title: "Error",
      text: message,
      confirmButtonText: "Close",
    });

    return;
  }

  window.alert(message);
}

  function showSuccess(message) {
    if (SweetAlert) {
      SweetAlert.fire({
        toast: true,
        position: "top-end",
        icon: "success",
        title: message,
        showConfirmButton: false,
        timer: 3000,
      });

      return;
    }

    console.info(message);
  }

  function setFileUi(file) {
    if (fileHint) {
      fileHint.textContent = file
        ? file.name
        : "No file selected";
    }

    if (!file) {
      filePill.style.display = "none";
      return;
    }

    fileName.textContent = (
      `✅ File uploaded: ${file.name}`
    );

    fileSize.textContent = (
      `Size: ${bytesToMegabytes(file.size)} MB`
    );

    filePill.style.display = "flex";
  }

  function resetAnalysis() {
    requirements = [];
    selectedRequirementIds = new Set();
    hasExceptionsSection = false;
    includeExceptions = false;
    projectId = "";

    if (projectIdElement) {
      projectIdElement.textContent = "—";
    }
    requirementPreview.hidden = true;

    requirementCount.textContent = "0";
    selectedCount.textContent = "0";
    documentType.textContent = "—";

    requirementButton.disabled = true;
    submitButton.disabled = true;

    resetResult();
  }

function resetResult() {
  readyCard.style.display = "none";

  lastDownloadUrl = "";
  requirementReviews = new Map();
  currentReviewIndex = 0;

  if (requirementReviewSection) {
    requirementReviewSection.hidden = true;
  }

  downloadButton.disabled = true;

metricRequirements.textContent = "0";
metricTestCases.textContent = "0";
metricTime.textContent = "00:00";
metricTotal.textContent = "0";
metricCost.textContent = "$0.00";
}

  function clearFileSelection() {
    if (analyzeController) {
      analyzeController.abort();
      analyzeController = null;
    }

    selectedFile = null;
    fileInput.value = "";

    setFileUi(null);
    resetAnalysis();
  }

  async function selectFile(file) {
    if (!file) {
      clearFileSelection();
      return;
    }

    if (!isAllowedFile(file)) {
      await showError(
        "Unsupported file type. Allowed: PDF and DOCX."
      );

      clearFileSelection();
      return;
    }

    selectedFile = file;

    setFileUi(file);
    resetAnalysis();

    await analyzeDocument(file);
  }

  async function analyzeDocument(file) {
    const analyzeUrl = (
      form.dataset.analyzeUrl
      || ""
    );

    if (!analyzeUrl) {
      return;
    }

    if (analyzeController) {
      analyzeController.abort();
    }

    analyzeController = new AbortController();

    const formData = new FormData();

    formData.set(
      "document",
      file,
      file.name
    );

    try {
      const response = await fetch(
        analyzeUrl,
        {
          method: "POST",
          body: formData,
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": getCookie(
              "csrftoken"
            ),
          },
          signal: analyzeController.signal,
        }
      );

      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.message
          || "The document could not be analyzed."
        );
      }

      requirements = Array.isArray(
        payload.requirements
      )
        ? payload.requirements
        : [];

      hasExceptionsSection = (
        payload.has_exceptions === true
      );

      includeExceptions = false;

      projectId = getProjectId(
        requirements
      );

      projectId = getProjectId(
        requirements
      );

      if (projectIdElement) {
        projectIdElement.textContent =
          projectId;
      }

      selectedRequirementIds = new Set(
        requirements.map(
          requirement => requirement.requirement_id
        )
      );

      requirementCount.textContent = String(
        requirements.length
      );

      selectedCount.textContent = String(
        selectedRequirementIds.size
      );

      documentType.textContent = (
        file.name.toLowerCase().endsWith(".pdf")
          ? "PDF"
          : "DOCX"
      );

      requirementPreview.hidden = false;

      requirementButton.disabled = (
        requirements.length === 0
      );

      submitButton.disabled = (
        requirements.length === 0
      );

    } catch (error) {
      if (error?.name === "AbortError") {
        return;
      }

      resetAnalysis();

      await showError(
        error?.message
        || "The document could not be analyzed."
      );
    }
  }

function updateSelectedCount() {
  selectedCount.textContent = String(
    selectedRequirementIds.size
  );

  submitButton.disabled = (
    selectedRequirementIds.size === 0
    && !includeExceptions
  );
}

function openDocumentInfoModal() {
  if (!SweetAlert) {
    return;
  }

  SweetAlert.fire({
    icon: "info",

    title:
      "PDD/FDD document requirements",

    html: `
      <div class="tc-doc-modal">

        <p class="tc-doc-modal__subtitle">
          AER Test Case Generator
        </p>

        <p>
          The generator analyzes a Heineken PDD/FDD
          document and detects its functional
          requirements from their structured IDs.
        </p>

        <h3>
          Supported requirement structure
        </h3>

        <div class="tc-doc-example">
          <span>
            Example
          </span>

          <pre>MCC.015.001 Download the MAE catalog
Requirement content...

MCC.015.002 Consult the MAE catalog
Requirement content...</pre>
        </div>

        <h3>
          Important
        </h3>

        <ul>
          <li>
            Each requirement must begin with a
            structured requirement ID.
          </li>

          <li>
            PDF and DOCX documents are supported.
          </li>

          <li>
            Requirements are automatically detected
            after selecting the document.
          </li>

          <li>
            You can select which requirements will
            be used to generate AER test cases.
          </li>
        </ul>

      </div>
    `,

    confirmButtonText:
      "Close",

    width:
      "min(760px, 92vw)",

    allowOutsideClick: true,

    allowEscapeKey: true,
  });
}

  async function openRequirementsModal() {
  if (
    !SweetAlert
    || requirements.length === 0
  ) {
    return;
  }

  const total = requirements.length;

  const requirementsHtml = requirements
    .map(
      (requirement, index) => {
        const requirementId = String(
          requirement.requirement_id
          || ""
        );

        const title = String(
          requirement.title
          || ""
        );

        const checked = (
          selectedRequirementIds.has(
            requirementId
          )
            ? "checked"
            : ""
        );

        const searchText = (
          `${requirementId} ${title}`
        );

        return `
          <li
            class="req-item"
            data-search="${escapeHtml(searchText)}"
          >
            <label class="req-check">

              <input
                type="checkbox"
                class="req-checkbox"
                value="${escapeHtml(requirementId)}"
                ${checked}
              >

              <span class="req-num">
                ${index + 1}.
              </span>

              <span class="req-title">
                ${escapeHtml(title)}
              </span>

            </label>
          </li>
        `;
      }
    )
    .join("");

  const result = await SweetAlert.fire({
    title: "",

    width: "min(980px, 92vw)",

    showCancelButton: true,

    confirmButtonText:
      "Apply selection",

    cancelButtonText:
      "Cancel",

    allowOutsideClick: true,

    allowEscapeKey: true,

    html: `
      <div class="req-modal">

        <div class="req-modal__header">

          <div class="req-modal__title">
            Select Requirements
          </div>

          <div class="req-modal__badges">

            <span class="badge-mini">
              🧩 ID:
              ${escapeHtml(projectId)}
            </span>

            <span class="badge-mini">
              📌 Requirements:
              ${total}
            </span>

            <span class="badge-mini">
              ✅ Selected:
              <span id="modalSelCount">
                0
              </span>

              
            </span>
                <span class="badge-mini">
      ${
        hasExceptionsSection
          ? "✅ Exceptions section detected"
          : "🚫 Exceptions section not detected"
      }
    </span>
          </div>

          <div class="req-modal__toolbar">

            <div class="req-toolbar__actions">

              <button
                type="button"
                class="req-chip"
                id="selectAllRequirements"
              >
                <span class="req-chip__icon">
                  ✅
                </span>

                Select all
              </button>

              <button
                type="button"
                class="req-chip req-chip--ghost"
                id="clearAllRequirements"
              >
                <span class="req-chip__icon">
                  🧹
                </span>

                Clear
              </button>

            </div>

            <input
              type="text"
              class="input"
              id="requirementsSearch"
              placeholder="Search..."
            >

          </div>

        </div>

<div class="req-modal__list">

  <ul
    class="req-list"
    id="requirementsSelectList"
  >
    ${requirementsHtml}
  </ul>

</div>

<div class="req-modal__list">

  <ul class="req-list">

    <li class="req-item">

      <label class="req-check">

        <input
          type="checkbox"
          id="includeExceptionsCheckbox"
          ${
            (
              hasExceptionsSection
              && includeExceptions
            )
              ? "checked"
              : ""
          }
          ${
            hasExceptionsSection
              ? ""
              : "disabled"
          }
        >

        <span class="req-num">
          ⚠️
        </span>

        <span class="req-title">
          Include FDD Exceptions
        </span>

      </label>

    </li>

  </ul>

</div>

</div>
    `,

    didOpen: () => {
      const root = (
        SweetAlert.getHtmlContainer()
      );

      if (!root) {
        return;
      }

      const checkboxes = Array.from(
        root.querySelectorAll(
          ".req-checkbox"
        )
      );

      const modalSelectedCount =
        root.querySelector(
          "#modalSelCount"
        );

      const updateModalSelectedCount = () => {
        const count = checkboxes.filter(
          checkbox => checkbox.checked
        ).length;

        if (modalSelectedCount) {
          modalSelectedCount.textContent =
            String(count);
        }
      };

      updateModalSelectedCount();

      for (const checkbox of checkboxes) {
        checkbox.addEventListener(
          "change",
          updateModalSelectedCount
        );
      }

      const selectAllButton =
        root.querySelector(
          "#selectAllRequirements"
        );

      const clearAllButton =
        root.querySelector(
          "#clearAllRequirements"
        );

      const searchInput =
        root.querySelector(
          "#requirementsSearch"
        );

      const requirementsList =
        root.querySelector(
          "#requirementsSelectList"
        );

      selectAllButton?.addEventListener(
        "click",
        () => {
          for (const checkbox of checkboxes) {
            checkbox.checked = true;
          }

          updateModalSelectedCount();
        }
      );

      clearAllButton?.addEventListener(
        "click",
        () => {
          for (const checkbox of checkboxes) {
            checkbox.checked = false;
          }

          updateModalSelectedCount();
        }
      );

      searchInput?.addEventListener(
        "input",
        () => {
          const query = (
            searchInput.value
            .trim()
            .toLowerCase()
          );

          const items = Array.from(
            requirementsList
              ?.querySelectorAll(
                ".req-item"
              )
            || []
          );

          for (const item of items) {
            const searchText = String(
              item.dataset.search
              || item.textContent
              || ""
            ).toLowerCase();

            item.style.display = (
              searchText.includes(query)
                ? ""
                : "none"
            );
          }
        }
      );
    },

preConfirm: () => {
  const root = (
    SweetAlert.getHtmlContainer()
  );

  const selected = Array.from(
    root?.querySelectorAll(
      ".req-checkbox:checked"
    )
    || []
  ).map(
    checkbox => checkbox.value
  );

  const exceptionsCheckbox = (
    root?.querySelector(
      "#includeExceptionsCheckbox"
    )
  );

  const exceptionsSelected = (
    hasExceptionsSection
    && Boolean(
      exceptionsCheckbox?.checked
    )
  );

  if (
    selected.length === 0
    && !exceptionsSelected
  ) {
    SweetAlert.showValidationMessage(
      "Select at least one requirement "
      + "or include FDD Exceptions."
    );

    return false;
  }

  return {
    selectedRequirements: selected,
    includeExceptions: exceptionsSelected,
  };
},
  });

if (!result.isConfirmed) {
  return;
}

selectedRequirementIds = new Set(
  result.value?.selectedRequirements
  || []
);

includeExceptions = Boolean(
  result.value?.includeExceptions
);

updateSelectedCount();
}

function setOverlay(visible) {
  if (!overlay) {
    return;
  }

  if (visible) {
    overlay.classList.add(
      "show"
    );

    overlay.setAttribute(
      "aria-hidden",
      "false"
    );

    return;
  }

  overlay.classList.remove(
    "show"
  );

  overlay.setAttribute(
    "aria-hidden",
    "true"
  );
}
  function setProgress(percent, message) {
    const safePercent = Math.max(
      0,
      Math.min(
        100,
        Number(percent) || 0
      )
    );

    progressBar.style.width = (
      `${safePercent}%`
    );

    progressText.textContent = (
      message || ""
    );
  }

function getRequirementReviewList() {
  return Array.from(
    requirementReviews.values()
  );
}

function formatReviewLevel(level) {
  if (level === "high_concentration") {
    return "High concentration";
  }

  if (level === "saturated") {
    return "Saturated";
  }

  return "Adequate";
}

function renderRequirementReviewSummary(
  reviews
) {
  const adequate = reviews.filter(
    review => review.level === "adequate"
  ).length;

  const high = reviews.filter(
    review => (
      review.level === "high_concentration"
    )
  ).length;

  const saturated = reviews.filter(
    review => review.level === "saturated"
  ).length;

  reviewAdequateCount.textContent = String(
    adequate
  );

  reviewHighCount.textContent = String(
    high
  );

  reviewSaturatedCount.textContent = String(
    saturated
  );
}

function renderRequirementReviewSlide() {
  const reviews = getRequirementReviewList();

  if (reviews.length === 0) {
    requirementReviewSection.hidden = true;
    return;
  }

  if (currentReviewIndex >= reviews.length) {
    currentReviewIndex = reviews.length - 1;
  }

  if (currentReviewIndex < 0) {
    currentReviewIndex = 0;
  }

  const review = reviews[
    currentReviewIndex
  ];

  requirementReviewSection.hidden = false;

  reviewRequirementId.textContent = (
    review.requirement_id || "—"
  );

  reviewRequirementTitle.textContent = (
    review.requirement_title || "—"
  );

  reviewLevel.textContent = (
    formatReviewLevel(
      review.level
    )
  );

reviewLevel.className = (
  "tc-review-badge "
  + `tc-review-badge--${review.level}`
);

const reviewSlide = document.getElementById(
  "reviewSlide"
);

reviewSlide.className = (
  "tc-review-card "
  + `tc-review-card--${review.level}`
);

  reviewReason.textContent = (
    review.reason || "—"
  );

  const areas = Array.isArray(
    review.areas
  )
    ? review.areas
    : [];

  if (areas.length > 0) {
    reviewAreas.innerHTML = areas
  .map(
    area => `
      <li>
        ${escapeHtml(area)}
      </li>
    `
  )
  .join("");

    reviewAreasBlock.hidden = false;

  } else {
    reviewAreas.innerHTML = "";
    reviewAreasBlock.hidden = true;
  }

  const functionalBlocks = Array.isArray(
    review.functional_blocks
  )
    ? review.functional_blocks
    : [];

  if (functionalBlocks.length > 0) {
    reviewFunctionalBlocksList.innerHTML = (
      functionalBlocks
        .map(
          block => `
            <li>
              ${escapeHtml(block)}
            </li>
          `
        )
        .join("")
    );

    reviewFunctionalBlocks.hidden = false;

  } else {
    reviewFunctionalBlocksList.innerHTML = "";
    reviewFunctionalBlocks.hidden = true;
  }

  reviewPosition.textContent = (
    `${currentReviewIndex + 1} / `
    + `${reviews.length}`
  );

  reviewPrevButton.disabled = (
    reviews.length <= 1
  );

  reviewNextButton.disabled = (
    reviews.length <= 1
  );

  renderRequirementReviewSummary(
    reviews
  );
}

function formatElapsedTime(seconds) {
  const totalSeconds = Math.max(
    0,
    Math.round(
      Number(seconds) || 0
    )
  );

  const minutes = Math.floor(
    totalSeconds / 60
  );

  const remainingSeconds = (
    totalSeconds % 60
  );

  return (
    String(minutes).padStart(2, "0")
    + ":"
    + String(remainingSeconds).padStart(
      2,
      "0"
    )
  );
}

  function applyCompletedEvent(event) {
    const usage = event.usage || {};
    const cost = event.cost || {};

    lastDownloadUrl = String(
      event.download_url || ""
    );

    readyFilename.textContent = (
      event.filename
      || "AER_Test_Cases.xlsx"
    );

    metricRequirements.textContent = String(
  event.selected_requirements?.length
  || selectedRequirementIds.size
);

metricTestCases.textContent = String(
  event.total_test_cases || 0
);

metricTime.textContent = (
  formatElapsedTime(
    event.elapsed
  )
);

metricTotal.textContent = String(
  usage.total_tokens || 0
);

metricCost.textContent = (
  cost.total_usd_formatted
  || "$0.00"
);

    readyCard.style.display = "block";

    downloadButton.disabled = (
      !lastDownloadUrl
    );
  }

  async function generateViaStream(formData) {
    const generateUrl = (
      form.dataset.generateStreamUrl
      || ""
    );

    const response = await fetch(
      generateUrl,
      {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCookie(
            "csrftoken"
          ),
        },
      }
    );

    if (!response.ok) {
      const payload = await response
        .json()
        .catch(() => ({}));

      throw new Error(
        payload.message
        || "Generation could not be started."
      );
    }

    if (!response.body) {
      throw new Error(
        "Streaming is not supported by this browser."
      );
    }

    const reader = response.body.getReader();

    const decoder = new TextDecoder(
      "utf-8"
    );

    let buffer = "";
    let completed = false;

    while (true) {
      const result = await reader.read();

      if (result.done) {
        break;
      }

      buffer += decoder.decode(
        result.value,
        {
          stream: true,
        }
      );

      const lines = buffer.split("\n");

      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) {
          continue;
        }

        const event = JSON.parse(line);

        if (event.type === "started") {
          setProgress(
            0,
            `Preparing ${event.total_requirements} requirements...`
          );
        }

        if (event.type === "requirement_started") {
          setProgress(
            event.progress,
            (
              `${event.requirement_id} - `
              + `${event.requirement_title} `
              + `(${event.current}/${event.total})`
            )
          );
        }

        if (event.type === "requirement_completed") {
  const review = event.requirement_review;

  if (
    review
    && typeof review === "object"
  ) {
    requirementReviews.set(
      String(event.requirement_id || ""),
      {
        requirement_id: String(
          event.requirement_id || ""
        ),
        requirement_title: String(
          event.requirement_title || ""
        ),
        level: String(
          review.level || ""
        ),
        reason: String(
          review.reason || ""
        ),
        areas: Array.isArray(
          review.areas
        )
          ? review.areas
          : [],
        functional_blocks: Array.isArray(
          review.functional_blocks
        )
          ? review.functional_blocks
          : [],
      }
    );
  }

  setProgress(
    event.progress,
    (
      `${event.requirement_id} completed `
      + `(${event.current}/${event.total})`
    )
  );
}
if (event.type === "exceptions_started") {
  setProgress(
    event.progress,
    "Generating FDD Exceptions..."
  );
}

if (event.type === "exceptions_completed") {
  setProgress(
    event.progress,
    (
      "FDD Exceptions completed. "
      + `${event.total_exceptions} exceptions, `
      + `${event.generated_test_cases} test cases.`
    )
  );
}
if (event.type === "completed") {
  completed = true;

  setProgress(
    100,
    "Completed. Ready to download."
  );

  console.log(
    "Requirement Reviews:",
    Array.from(
      requirementReviews.values()
    )
  );

  currentReviewIndex = 0;

  renderRequirementReviewSlide();

  applyCompletedEvent(event);
}

if (event.type === "error") {
  setProgress(
    event.progress || 0,
    "Generation stopped due to an error."
  );

  setOverlay(false);

  throw new Error(
    event.message
    || "Generation failed."
  );
}
      }
    }

    if (!completed) {
      throw new Error(
        "The generation stream ended unexpectedly."
      );
    }
  }

function openRequirementReviewInfoModal() {
  if (!SweetAlert) {
    return;
  }

  SweetAlert.fire({
    icon: "info",
    title: "Requirement Review",

    html: `
      <div class="tc-review-modal-lite">

        <p class="tc-review-modal-lite__subtitle">
          Functional concentration analysis
        </p>

        <p class="tc-review-modal-lite__lead">
          The classification is based on functional structure,
          not simply on the length of the requirement, number
          of steps, test cases, systems, files, or business rules.
        </p>

        <div class="tc-review-modal-lite__grid">

          <section
            class="
              tc-review-modal-card
              tc-review-modal-card--adequate
            "
          >
            <div class="tc-review-modal-card__top">

              <span
                class="
                  tc-review-modal-card__badge
                  tc-review-modal-card__badge--adequate
                "
              >
                Adequate
              </span>

              <span
                class="
                  tc-review-modal-card__icon
                  tc-review-modal-card__icon--adequate
                "
                aria-hidden="true"
              >
                ✓
              </span>

            </div>

            <p class="tc-review-modal-card__text">
              The requirement represents a cohesive functional
              unit with one main objective and a consistent
              functional result.
            </p>

            <ul class="tc-review-modal-card__list">
              <li>
                Its activities belong to the same functional flow.
              </li>

              <li>
                It may contain several rules, exceptions,
                systems or inputs.
              </li>

              <li>
                These elements continue contributing to the
                same functional objective.
              </li>

              <li>
                There are no clearly independent functional
                blocks.
              </li>
            </ul>

          </section>


          <section
            class="
              tc-review-modal-card
              tc-review-modal-card--high
            "
          >
            <div class="tc-review-modal-card__top">

              <span
                class="
                  tc-review-modal-card__badge
                  tc-review-modal-card__badge--high
                "
              >
                High concentration
              </span>

              <span
                class="
                  tc-review-modal-card__icon
                  tc-review-modal-card__icon--high
                "
                aria-hidden="true"
              >
                !
              </span>

            </div>

            <p class="tc-review-modal-card__text">
              The requirement still represents one main
              functional objective, but contains significant
              internal complexity.
            </p>

            <ul class="tc-review-modal-card__list">
              <li>
                It may contain multiple business rules,
                decisions, exceptions or variants.
              </li>

              <li>
                It may contain different execution paths.
              </li>

              <li>
                These variations still belong to the same
                main functional unit.
              </li>

              <li>
                There is not enough independence to consider
                them separate functional blocks.
              </li>
            </ul>

          </section>


          <section
            class="
              tc-review-modal-card
              tc-review-modal-card--saturated
            "
          >
            <div class="tc-review-modal-card__top">

              <span
                class="
                  tc-review-modal-card__badge
                  tc-review-modal-card__badge--saturated
                "
              >
                Saturated
              </span>

              <span
                class="
                  tc-review-modal-card__icon
                  tc-review-modal-card__icon--saturated
                "
                aria-hidden="true"
              >
                !
              </span>

            </div>

            <p class="tc-review-modal-card__text">
              The requirement contains multiple clearly
              distinguishable functional blocks within the
              same requirement.
            </p>

            <ul class="tc-review-modal-card__list">
              <li>
                The blocks may have their own functional purpose.
              </li>

              <li>
                They may consume different inputs or artifacts.
              </li>

              <li>
                They may apply their own rules or processing.
              </li>

              <li>
                They produce identifiable and verifiable results.
              </li>

              <li>
                They can reasonably be tested as separate
                functional units.
              </li>
            </ul>

          </section>

        </div>


        <div class="tc-review-modal-lite__important">

          <div class="tc-review-modal-lite__important-title">
            Important
          </div>

          <div class="tc-review-modal-lite__important-grid">

            <span>
              A long requirement is not automatically saturated.
            </span>

            <span>
              More test cases do not automatically increase
              the classification.
            </span>

            <span>
              Multiple systems, files or inputs do not determine
              the classification by themselves.
            </span>

            <span>
              The analysis focuses on functional cohesion,
              complexity and independence between blocks.
            </span>

          </div>

        </div>

      </div>
    `,

    confirmButtonText: "Close",

    width: "min(980px, 94vw)",

    allowOutsideClick: true,

    allowEscapeKey: true,
  });
}

  async function downloadXlsx() {
    if (!lastDownloadUrl) {
      return;
    }

    const response = await fetch(
      lastDownloadUrl,
      {
        credentials: "same-origin",
      }
    );

    if (!response.ok) {
      throw new Error(
        "Download failed."
      );
    }

    const blob = await response.blob();

    const contentDisposition = String(
      response.headers.get(
        "Content-Disposition"
      )
      || ""
    );

    const filenameMatch = (
      contentDisposition.match(
        /filename="([^"]+)"/i
      )
    );

    const filename = (
      filenameMatch?.[1]
      || "AER_Test_Cases.xlsx"
    );

    const objectUrl = window.URL.createObjectURL(
      blob
    );

    const anchor = document.createElement(
      "a"
    );

    anchor.href = objectUrl;
    anchor.download = filename;

    document.body.appendChild(
      anchor
    );

    anchor.click();
    anchor.remove();

    window.URL.revokeObjectURL(
      objectUrl
    );
  }

  fileUiButton.addEventListener(
    "click",
    () => fileInput.click()
  );

  uploadOrb.addEventListener(
    "click",
    () => fileInput.click()
  );

  fileInput.addEventListener(
    "change",
    () => {
      const file = (
        fileInput.files?.[0]
        || null
      );

      void selectFile(file);
    }
  );

  clearFileButton.addEventListener(
    "click",
    event => {
      event.preventDefault();

      clearFileSelection();
    }
  );

  requirementButton.addEventListener(
    "click",
    () => {
      void openRequirementsModal();
    }
  );

  documentInfoButton?.addEventListener(
  "click",
  openDocumentInfoModal
);
requirementReviewInfoButton?.addEventListener(
  "click",
  openRequirementReviewInfoModal
);
  uploader.addEventListener(
    "dragover",
    event => {
      event.preventDefault();

      uploader.classList.add(
        "is-dragover"
      );
    }
  );

  uploader.addEventListener(
    "dragleave",
    () => {
      uploader.classList.remove(
        "is-dragover"
      );
    }
  );

  uploader.addEventListener(
    "drop",
    event => {
      event.preventDefault();

      uploader.classList.remove(
        "is-dragover"
      );

      const file = (
        event.dataTransfer?.files?.[0]
        || null
      );

      void selectFile(file);
    }
  );

  form.addEventListener(
    "submit",
    async event => {
      event.preventDefault();

      if (!selectedFile) {
        await showError(
          "Please select a document."
        );

        return;
      }

if (
  selectedRequirementIds.size === 0
  && !includeExceptions
) {
  await showError(
    "Select at least one requirement "
    + "or include FDD Exceptions."
  );

  return;
}

      resetResult();

      const formData = new FormData();

      formData.set(
        "document",
        selectedFile,
        selectedFile.name
      );

formData.set(
  "selected_requirements",
  Array.from(
    selectedRequirementIds
  ).join(",")
);

formData.set(
  "include_exceptions",
  includeExceptions
    ? "true"
    : "false"
);

      submitButton.disabled = true;

      setProgress(
        0,
        "Starting generation..."
      );

      setOverlay(true);

try {
  await generateViaStream(
    formData
  );

  setOverlay(false);

  showSuccess(
    "AER test cases generated successfully."
  );

} catch (error) {
  setOverlay(false);

  await showError(
    error?.message
    || "An unexpected error occurred."
  );

} finally {
  setOverlay(false);

submitButton.disabled = (
  selectedRequirementIds.size === 0
  && !includeExceptions
);
}
    }
  );

  downloadButton.addEventListener(
    "click",
    async () => {
      downloadButton.disabled = true;

      try {
        await downloadXlsx();

      } catch (error) {
        await showError(
          error?.message
          || "Download failed."
        );

      } finally {
        downloadButton.disabled = (
          !lastDownloadUrl
        );
      }
    }
  );
reviewPrevButton?.addEventListener(
  "click",
  () => {
    const reviews = getRequirementReviewList();

    if (reviews.length <= 1) {
      return;
    }

    currentReviewIndex = (
      currentReviewIndex - 1
      + reviews.length
    ) % reviews.length;

    renderRequirementReviewSlide();
  }
);

reviewNextButton?.addEventListener(
  "click",
  () => {
    const reviews = getRequirementReviewList();

    if (reviews.length <= 1) {
      return;
    }

    currentReviewIndex = (
      currentReviewIndex + 1
    ) % reviews.length;

    renderRequirementReviewSlide();
  }
);
  clearFileSelection();
});