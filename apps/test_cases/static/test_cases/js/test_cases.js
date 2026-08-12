"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("genForm");
  const fileInput = document.getElementById("id_document");
  const fileUiBtn = document.getElementById("fileUiBtn");
  const uploadOrb = document.getElementById("uploadOrb");
  const fileHint = document.getElementById("fileHint");
  const docInfoBtn = document.getElementById("docInfoBtn");
  const requirementReviewInfoBtn = document.getElementById(
  "requirementReviewInfoBtn"
);

  const filePill = document.getElementById("filePill");
  const fileNameElement = document.getElementById("fileName");
  const fileSizeElement = document.getElementById("fileSize");
  const clearFileButton = document.getElementById("clearFileBtn");

  const submitButton = document.getElementById("submitBtn");
  const downloadButton = document.getElementById("downloadBtn");

  const overlay = document.getElementById("overlay");
  const progressBar = document.getElementById("progressBar");
  const progressText = document.getElementById("progressText");

  const readyCard = document.getElementById("readyCard");
  const readyFilename = document.getElementById("readyFilename");

  const metricInput = document.getElementById("mInput");
  const metricOutput = document.getElementById("mOutput");
  const metricTime = document.getElementById("mTime");
  const metricRequirements = document.getElementById("mReq");
  const metricTestCases = document.getElementById("mTc");
  const metricNotTestable = document.getElementById("mNot");
  const metricCost = document.getElementById("mCost");
  const metricArea = document.getElementById("mArea");

  const requirementReviewSection = document.getElementById(
  "requirementReviewSection"
);

const requirementReviewSummary = document.getElementById(
  "requirementReviewSummary"
);

const requirementReviewList = document.getElementById(
  "requirementReviewList"
);

  const uploader = document.querySelector(".uploader");
  const assignedInput = document.getElementById(
    "id_assigned_to"
  );

  const requirementsPreview = document.getElementById(
    "reqPreview"
  );
  const projectIdElement = document.getElementById("reqPid");
  const requirementsCountElement = document.getElementById(
    "reqCount"
  );
  const selectedCountElement = document.getElementById(
    "selCount"
  );
  const documentTypeElement = document.getElementById(
    "docType"
  );
  const requirementsPreviewButton = document.getElementById(
    "reqPreviewBtn"
  );
  const selectedRequirementsInput = document.getElementById(
    "selectedRequirements"
  );

  if (!form) {
    return;
  }

  const SweetAlert = window.Swal;

  let selectedFile = null;
  let lastPreview = null;
  let selectedRequirementNumbers = null;
  let analyzeController = null;
  let lastDownloadUrl = "";

  const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

  const REVIEW_LEVELS = {
  adequate: {
    label: "Adequate",
  },
  high_concentration: {
    label: "High functional concentration",
  },
  saturated: {
    label: "Saturated requirement",
  },
};

  const MESSAGES = {
    ERR_NO_FILE:
      "Please upload a file to continue.",
    ERR_BAD_EXT:
      "Unsupported file type. Allowed: .pdf, .docx.",
    ERR_TOO_LARGE:
      "The file exceeds the maximum allowed size.",
    ERR_NO_PROJECT_ID:
      "Project ID was not found in the document or file name.",
    ERR_NO_REQUIREMENTS:
      "No supported requirements were detected.",
    ERR_GENERATION_INPUT:
      "Review Assigned To and the requirement selection.",
    ERR_INVALID_JSON:
      "The AI response could not be processed correctly.",
    ERR_EMPTY_GENERATION:
      "No test cases were generated.",
    ERR_CLAUDE_CONFIG:
      "The AI service is not configured.",
    ERR_CLAUDE_REQUEST:
      "The AI service could not complete the request.",
    ERR_CLAUDE_RESPONSE:
      "The AI service returned an invalid response.",
    ERR_STREAM_GENERATION:
      "An internal error occurred during generation.",

    UI_SELECT_FILE:
      "Please select a file before generating test cases.",
    UI_SELECT_ASSIGNED:
      "Please fill Assigned To with the exact Azure DevOps "
      + "display name.",
    UI_ANALYSIS_PENDING:
      "Please wait for the document analysis to finish.",
    UI_SELECT_REQUIREMENT:
      "Select at least one requirement.",
    UI_STREAM_UNSUPPORTED:
      "Your browser does not support streaming responses.",
    UI_STREAM_ENDED:
      "The generation stream ended unexpectedly.",
    UI_DOWNLOAD_FAILED:
      "Download failed. Please generate the test cases again.",
    UI_REQUEST_FAILED:
      "The request could not be completed.",
    UI_GENERATE_URL_MISSING:
      "The generation URL is not configured.",
    UI_DOWNLOAD_URL_MISSING:
      "The download URL is not available.",

    UI_STARTING:
      "Starting generation…",
    UI_PREPARING:
      "Preparing requirements…",
    UI_PROCESSING:
      "Processing requirement",
    UI_COMPLETED:
      "Completed. Ready to download.",

    UI_NO_FILE:
      "No file selected",
    UI_FILE_UPLOADED:
      "File uploaded",
    UI_SIZE:
      "Size",
    UI_ERROR_TITLE:
      "Error",
    UI_CLOSE:
      "Close",
  };

  const Toast = SweetAlert
    ? SweetAlert.mixin({
        toast: true,
        position: "top-end",
        showConfirmButton: false,
        timer: 3200,
        timerProgressBar: true,
        showCloseButton: true,
        didOpen: (toast) => {
          toast.addEventListener(
            "mouseenter",
            SweetAlert.stopTimer
          );
          toast.addEventListener(
            "mouseleave",
            SweetAlert.resumeTimer
          );
        },
      })
    : null;

  function translate(code, fallback = "") {
    return MESSAGES[code] || fallback || code || "";
  }

  function getCookie(name) {
    const cookieValue = `; ${document.cookie}`;
    const parts = cookieValue.split(`; ${name}=`);

    if (parts.length !== 2) {
      return "";
    }

    return parts.pop().split(";").shift() || "";
  }

  function bytesToMegabytes(bytes) {
    return (
      Number(bytes || 0)
      / (1024 * 1024)
    ).toFixed(2);
  }

  function isAllowedFile(file) {
    const filename = String(file?.name || "").toLowerCase();

    return ALLOWED_EXTENSIONS.some(
      (extension) => filename.endsWith(extension)
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

  function showElement(element, display = "block") {
    if (element) {
      element.style.display = display;
    }
  }

  function hideElement(element) {
    if (element) {
      element.style.display = "none";
    }
  }

  function showSuccess(message) {
    if (Toast) {
      Toast.fire({
        icon: "success",
        title: message,
      });

      return;
    }

    console.info(message);
  }

  async function showError(message) {
    if (SweetAlert) {
      await SweetAlert.fire({
        icon: "error",
        title: translate(
          "UI_ERROR_TITLE",
          "Error"
        ),
        text: message,
        confirmButtonText: translate(
          "UI_CLOSE",
          "Close"
        ),
        allowOutsideClick: true,
        allowEscapeKey: true,
      });

      return;
    }

    window.alert(message);
  }

  function getTotalRequirements(preview) {
    if (!preview) {
      return 0;
    }

    const requirements = Array.isArray(
      preview.requirements
    )
      ? preview.requirements
      : [];

    const total = Number(
      preview.total_blocks ?? requirements.length
    );

    return Number.isFinite(total)
      ? total
      : requirements.length;
  }

  function updateSelectedCount() {
    if (!selectedCountElement) {
      return;
    }

    const total = getTotalRequirements(lastPreview);

    const selectedCount = (
      selectedRequirementNumbers === null
    )
      ? total
      : Array.isArray(selectedRequirementNumbers)
        ? selectedRequirementNumbers.length
        : 0;

    selectedCountElement.textContent = String(
      selectedCount
    );
  }

  function getDocumentTypeLabel(method) {
    const normalizedMethod = String(
      method || ""
    ).trim().toLowerCase();

    if (
      normalizedMethod === "tobe"
      || normalizedMethod === "tobe_numbered"
    ) {
      return "PDD Beecker";
    }

    if (
      normalizedMethod.includes("process_steps")
      || normalizedMethod.includes("process-steps")
    ) {
      return "PDD Nestlé";
    }

    if (
      normalizedMethod === "req_id"
      || normalizedMethod.includes("fdd")
    ) {
      return "FDD";
    }

    if (
      normalizedMethod
      && normalizedMethod !== "none"
    ) {
      return "PDD / FDD";
    }

    return "Undetermined";
  }

  function cleanRequirementTitle(title, number) {
    let cleanTitle = String(title ?? "").trim();
    const cleanNumber = String(number ?? "").trim();

    if (!cleanNumber) {
      return cleanTitle;
    }

    const escapedNumber = cleanNumber.replace(
      /[.*+?^${}()|[\]\\]/g,
      "\\$&"
    );

    const patterns = [
      new RegExp(
        `^\\s*#\\s*${escapedNumber}\\s+`,
        "i"
      ),
      new RegExp(
        `^\\s*${escapedNumber}\\s*[.)-]\\s+`,
        "i"
      ),
      new RegExp(
        `^\\s*${escapedNumber}\\s*\\.\\s*`
        + `${escapedNumber}\\s*\\.\\s+`,
        "i"
      ),
      new RegExp(
        "^\\s*Nombre\\s+de\\s+la\\s+"
        + "acci[oó]n\\s*:\\s*",
        "i"
      ),
    ];

    for (const pattern of patterns) {
      cleanTitle = cleanTitle.replace(
        pattern,
        ""
      );
    }

    return cleanTitle.trim();
  }

  function clearRequirementsPreview() {
    lastPreview = null;
    selectedRequirementNumbers = null;

    if (requirementsPreview) {
      requirementsPreview.hidden = true;
    }

    if (projectIdElement) {
      projectIdElement.textContent = "—";
    }

    if (requirementsCountElement) {
      requirementsCountElement.textContent = "0";
    }

    if (selectedCountElement) {
      selectedCountElement.textContent = "0";
    }

    if (documentTypeElement) {
      documentTypeElement.textContent = "—";
    }

    if (requirementsPreviewButton) {
      requirementsPreviewButton.disabled = true;
    }

    if (selectedRequirementsInput) {
      selectedRequirementsInput.value = "";
    }
  }

  function renderRequirementsPreview(preview) {
    if (!requirementsPreview) {
      return;
    }

    const requirements = Array.isArray(
      preview?.requirements
    )
      ? preview.requirements
      : [];

    const total = getTotalRequirements(preview);

    if (projectIdElement) {
      projectIdElement.textContent = (
        preview?.project_id
        || "Not detected"
      );
    }

    if (requirementsCountElement) {
      requirementsCountElement.textContent = String(total);
    }

    if (documentTypeElement) {
      documentTypeElement.textContent = (
        getDocumentTypeLabel(preview?.method)
      );
    }

    requirementsPreview.hidden = false;

    if (requirementsPreviewButton) {
      requirementsPreviewButton.disabled = (
        requirements.length === 0
      );
    }

    updateSelectedCount();
  }

  function setSelectedRequirements(numbers) {
    const requirements = Array.isArray(
      lastPreview?.requirements
    )
      ? lastPreview.requirements
      : [];

    const normalizedNumbers = Array.from(
      new Set(
        (numbers || [])
          .map(Number)
          .filter(Number.isFinite)
      )
    ).sort((first, second) => first - second);

    if (
      normalizedNumbers.length
      === requirements.length
    ) {
      selectedRequirementNumbers = null;

      if (selectedRequirementsInput) {
        selectedRequirementsInput.value = "";
      }
    } else {
      selectedRequirementNumbers = normalizedNumbers;

      if (selectedRequirementsInput) {
        selectedRequirementsInput.value = (
          normalizedNumbers.join(",")
        );
      }
    }

    updateSelectedCount();
  }

  function openRequirementsModal() {
    if (!SweetAlert || !lastPreview) {
      return;
    }

    const requirements = Array.isArray(
      lastPreview.requirements
    )
      ? lastPreview.requirements
      : [];

    const projectId = (
      lastPreview.project_id
      || "Not detected"
    );

    const total = getTotalRequirements(lastPreview);

    const requirementsHtml = requirements
      .map((requirement) => {
        const number = requirement.number;
        const title = cleanRequirementTitle(
          requirement.title,
          number
        );

        return `
          <li class="req-item">
            <label class="req-check">
              <input
                type="checkbox"
                class="req-checkbox"
                data-num="${escapeHtml(number)}"
              >
              <span class="req-num">
                ${escapeHtml(number)}.
              </span>
              <span class="req-title">
                ${escapeHtml(
                  title || requirement.title || ""
                )}
              </span>
            </label>
          </li>
        `;
      })
      .join("");

    SweetAlert.fire({
      title: "",
      width: "min(980px, 92vw)",
      showCancelButton: true,
      confirmButtonText: "Apply selection",
      cancelButtonText: "Cancel",
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
                🧩 ID: ${escapeHtml(projectId)}
              </span>

              <span class="badge-mini">
                📌 Requirements:
                ${escapeHtml(total)}
              </span>

              <span class="badge-mini">
                ✅ Selected:
                <span id="modalSelCount">0</span>
              </span>
            </div>

            <div class="req-modal__toolbar">
              <div class="req-toolbar__actions">
                <button
                  type="button"
                  class="req-chip"
                  id="selectAllRequirements"
                >
                  <span class="req-chip__icon">✅</span>
                  Select all
                </button>

                <button
                  type="button"
                  class="req-chip req-chip--ghost"
                  id="clearAllRequirements"
                >
                  <span class="req-chip__icon">🧹</span>
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
        </div>
      `,
      didOpen: () => {
        const root = SweetAlert.getHtmlContainer();

        if (!root) {
          return;
        }

        const checkboxes = Array.from(
          root.querySelectorAll(".req-checkbox")
        );

        const selectedSet = (
          selectedRequirementNumbers === null
        )
          ? null
          : new Set(
              selectedRequirementNumbers.map(Number)
            );

        for (const checkbox of checkboxes) {
          const number = Number(
            checkbox.dataset.num
          );

          checkbox.checked = (
            selectedSet === null
            || selectedSet.has(number)
          );
        }

        const modalSelectedCount = root.querySelector(
          "#modalSelCount"
        );

        const updateModalSelectedCount = () => {
          const count = checkboxes.filter(
            (checkbox) => checkbox.checked
          ).length;

          if (modalSelectedCount) {
            modalSelectedCount.textContent = String(count);
          }
        };

        updateModalSelectedCount();

        for (const checkbox of checkboxes) {
          checkbox.addEventListener(
            "change",
            updateModalSelectedCount
          );
        }

        const selectAllButton = root.querySelector(
          "#selectAllRequirements"
        );

        const clearAllButton = root.querySelector(
          "#clearAllRequirements"
        );

        const searchInput = root.querySelector(
          "#requirementsSearch"
        );

        const requirementsList = root.querySelector(
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
            const query = searchInput.value
              .trim()
              .toLowerCase();

            const items = Array.from(
              requirementsList?.querySelectorAll(
                ".req-item"
              ) || []
            );

            for (const item of items) {
              const itemText = item.textContent
                .toLowerCase();

              item.style.display = (
                itemText.includes(query)
              )
                ? ""
                : "none";
            }
          }
        );
      },
      preConfirm: () => {
        const root = SweetAlert.getHtmlContainer();

        const selected = Array.from(
          root?.querySelectorAll(
            ".req-checkbox:checked"
          ) || []
        )
          .map(
            (checkbox) => Number(
              checkbox.dataset.num
            )
          )
          .filter(Number.isFinite);

        if (selected.length === 0) {
          SweetAlert.showValidationMessage(
            translate(
              "UI_SELECT_REQUIREMENT",
              "Select at least one requirement."
            )
          );

          return false;
        }

        return selected;
      },
    }).then((result) => {
      if (!result.isConfirmed) {
        return;
      }

      setSelectedRequirements(
        result.value || []
      );
    });
  }

  async function analyzeDocument(file) {
    const analyzeUrl = form.dataset.analyzeUrl;

    if (!analyzeUrl) {
      return;
    }

    if (analyzeController) {
      analyzeController.abort();
    }

    analyzeController = new AbortController();

    try {
      const formData = new FormData();

      formData.set(
        "document",
        file,
        file.name
      );

      const response = await fetch(
        analyzeUrl,
        {
          method: "POST",
          body: formData,
          headers: {
            "X-CSRFToken": getCookie(
              "csrftoken"
            ),
          },
          credentials: "same-origin",
          signal: analyzeController.signal,
        }
      );

      const contentType = String(
        response.headers.get("content-type")
        || ""
      ).toLowerCase();

      const data = contentType.includes(
        "application/json"
      )
        ? await response.json()
        : null;

      if (!response.ok) {
        const message = (
          data?.code
            ? translate(
                data.code,
                data.message
              )
            : data?.message
        );

        throw new Error(
          message
          || translate(
            "UI_REQUEST_FAILED",
            "The document could not be analyzed."
          )
        );
      }

      lastPreview = data;
      selectedRequirementNumbers = null;

      if (selectedRequirementsInput) {
        selectedRequirementsInput.value = "";
      }

      renderRequirementsPreview(
        lastPreview
      );

      if (data?.truncated && Toast) {
        Toast.fire({
          icon: "info",
          title: (
            "Only the first 400 requirements "
            + "are available for selection."
          ),
        });
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        return;
      }

      clearRequirementsPreview();

      await showError(
        error?.message
        || "The document could not be analyzed."
      );
    }
  }

  function resetMetrics() {
    if (metricInput) {
      metricInput.textContent = "0";
    }

    if (metricOutput) {
      metricOutput.textContent = "0";
    }

    if (metricTime) {
      metricTime.textContent = "0";
    }

    if (metricRequirements) {
      metricRequirements.textContent = "0";
    }

    if (metricTestCases) {
      metricTestCases.textContent = "0";
    }

    if (metricNotTestable) {
      metricNotTestable.textContent = "0";
    }

    if (metricArea) {
      metricArea.textContent = "-";
    }

    if (metricCost) {
      metricCost.textContent = "$0.000000";
    }
  }

function resetGenerationResult() {
  hideElement(readyCard);
  lastDownloadUrl = "";

  if (downloadButton) {
    downloadButton.disabled = true;
  }

  resetMetrics();
  resetRequirementReviews();
}

  function setFileSelectedUi(file) {
    if (fileHint) {
      fileHint.textContent = file
        ? file.name
        : translate(
            "UI_NO_FILE",
            "No file selected"
          );
    }

    if (!file) {
      hideElement(filePill);
      return;
    }

    if (fileNameElement) {
      fileNameElement.textContent = (
        `✅ ${translate(
          "UI_FILE_UPLOADED",
          "File uploaded"
        )}: ${file.name}`
      );
    }

    if (fileSizeElement) {
      fileSizeElement.textContent = (
        `${translate("UI_SIZE", "Size")}: `
        + `${bytesToMegabytes(file.size)} MB`
      );
    }

    showElement(filePill);
  }

  function clearFileSelection() {
    if (analyzeController) {
      analyzeController.abort();
      analyzeController = null;
    }

    selectedFile = null;

    if (fileInput) {
      fileInput.value = "";
    }

    setFileSelectedUi(null);
    clearRequirementsPreview();
    resetGenerationResult();
  }

  async function selectFile(file) {
    if (file && !isAllowedFile(file)) {
      await showError(
        translate(
          "ERR_BAD_EXT",
          "Unsupported file type. "
          + "Allowed: .pdf, .docx."
        )
      );

      clearFileSelection();
      return;
    }

    selectedFile = file || null;
    setFileSelectedUi(selectedFile);
    clearRequirementsPreview();
    resetGenerationResult();

    if (selectedFile) {
      await analyzeDocument(selectedFile);
    }
  }

  function setOverlay(visible) {
    if (!overlay) {
      return;
    }

    overlay.classList.toggle(
      "show",
      visible
    );

    overlay.setAttribute(
      "aria-hidden",
      visible ? "false" : "true"
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

    if (progressBar) {
      progressBar.style.width = (
        `${safePercent}%`
      );
    }

    if (progressText && message) {
      progressText.textContent = message;
    }
  }

  function formatCost(cost) {
    const formatted = cost?.total_usd_formatted;

    if (
      typeof formatted === "string"
      && formatted.trim()
    ) {
      return formatted;
    }

    const total = Number(
      cost?.total_usd ?? 0
    );

    if (!Number.isFinite(total)) {
      return "$0.000000";
    }

    return `$${total.toFixed(6)}`;
  }

function resetRequirementReviews() {
  if (requirementReviewSummary) {
    requirementReviewSummary.replaceChildren();
  }

  if (requirementReviewList) {
    requirementReviewList.replaceChildren();
  }

  if (requirementReviewSection) {
    requirementReviewSection.hidden = true;
  }
}


function createReviewSummaryBadge(
  label,
  count,
  level
) {
  const badge = document.createElement("span");

  badge.className = (
    `tc-review-summary-badge `
    + `tc-review-summary-badge--${level}`
  );

  badge.textContent = `${label}: ${count}`;

  return badge;
}


function appendReviewDetailList(
  container,
  title,
  values
) {
  if (
    !container
    || !Array.isArray(values)
    || values.length === 0
  ) {
    return;
  }

  const group = document.createElement("div");
  group.className = "tc-review-group";

  const heading = document.createElement("div");
  heading.className = "tc-review-group__title";
  heading.textContent = title;

  const list = document.createElement("ul");
  list.className = "tc-review-group__list";

  for (const value of values) {
    const cleanValue = String(
      value ?? ""
    ).trim();

    if (!cleanValue) {
      continue;
    }

    const item = document.createElement("li");
    item.textContent = cleanValue;

    list.appendChild(item);
  }

  if (!list.children.length) {
    return;
  }

  group.appendChild(heading);
  group.appendChild(list);

  container.appendChild(group);
}


function createRequirementReviewCard(detail) {
  const review = detail?.requirement_review;

  if (!review) {
    return null;
  }

  const level = String(
    review.level || ""
  ).trim();

  const levelConfig = REVIEW_LEVELS[level];

  if (!levelConfig) {
    return null;
  }

  const card = document.createElement("article");

  card.className = (
    `tc-review-card `
    + `tc-review-card--${level}`
  );

  const header = document.createElement("div");
  header.className = "tc-review-card__header";

  const identity = document.createElement("div");
  identity.className = "tc-review-card__identity";

  const requirement = document.createElement("strong");
  requirement.className = "tc-review-card__requirement";

  requirement.textContent = (
    `REQ ${detail.requirement ?? "?"}`
  );

  identity.appendChild(requirement);

  const scenarioName = String(
    detail.scenario_name || ""
  ).trim();

  if (scenarioName) {
    const scenario = document.createElement("span");
    scenario.className = "tc-review-card__scenario";
    scenario.textContent = scenarioName;

    identity.appendChild(scenario);
  }

  const badge = document.createElement("span");

  badge.className = (
    `tc-review-badge `
    + `tc-review-badge--${level}`
  );

  badge.textContent = levelConfig.label;

  header.appendChild(identity);
  header.appendChild(badge);

  card.appendChild(header);

  const reason = String(
    review.reason || ""
  ).trim();

  if (reason) {
    const reasonElement = document.createElement("p");
    reasonElement.className = "tc-review-card__reason";
    reasonElement.textContent = reason;

    card.appendChild(reasonElement);
  }

  appendReviewDetailList(
    card,
    "Concentration detected in",
    review.areas
  );

  appendReviewDetailList(
    card,
    "Functional blocks",
    review.functional_blocks
  );

  return card;
}


function renderRequirementReviews(details) {
  resetRequirementReviews();

  if (
    !requirementReviewSection
    || !requirementReviewList
    || !Array.isArray(details)
  ) {
    return;
  }

  const counts = {
    adequate: 0,
    high_concentration: 0,
    saturated: 0,
  };

  let renderedCards = 0;

  for (const detail of details) {
    const level = String(
      detail?.requirement_review?.level || ""
    ).trim();

    if (
      Object.prototype.hasOwnProperty.call(
        counts,
        level
      )
    ) {
      counts[level] += 1;
    }

    const card = createRequirementReviewCard(
      detail
    );

    if (!card) {
      continue;
    }

    requirementReviewList.appendChild(
      card
    );

    renderedCards += 1;
  }

  if (renderedCards === 0) {
    return;
  }

  if (requirementReviewSummary) {
    requirementReviewSummary.appendChild(
      createReviewSummaryBadge(
        "Adequate",
        counts.adequate,
        "adequate"
      )
    );

    requirementReviewSummary.appendChild(
      createReviewSummaryBadge(
        "High concentration",
        counts.high_concentration,
        "high_concentration"
      )
    );

    requirementReviewSummary.appendChild(
      createReviewSummaryBadge(
        "Saturated",
        counts.saturated,
        "saturated"
      )
    );
  }

  requirementReviewSection.hidden = false;
}
  
  function applyCompletedUi(event) {
    const usage = event.usage || {};
    const stats = event.stats || {};

    lastDownloadUrl = String(
      event.download_url || ""
    );

    if (readyFilename) {
      readyFilename.textContent = (
        event.filename
        || "TC.xlsx"
      );
    }

    if (metricInput) {
      metricInput.textContent = String(
        usage.input_tokens ?? 0
      );
    }

    if (metricOutput) {
      metricOutput.textContent = String(
        usage.output_tokens ?? 0
      );
    }

    if (metricTime) {
      metricTime.textContent = String(
        event.elapsed ?? 0
      );
    }

    if (metricRequirements) {
      metricRequirements.textContent = String(
        stats.requirements_total ?? 0
      );
    }

    if (metricTestCases) {
      metricTestCases.textContent = String(
        stats.test_cases_total ?? 0
      );
    }

    if (metricNotTestable) {
      metricNotTestable.textContent = String(
        stats.requirements_not_testable ?? 0
      );
    }

    if (metricArea) {
      metricArea.textContent = String(
        stats.area_path
        ?? stats.project_id
        ?? "-"
      );
    }

    if (metricCost) {
      metricCost.textContent = formatCost(
        event.cost
      );
    }

    renderRequirementReviews(
  stats.requirement_details
);

    showElement(readyCard);

    if (downloadButton) {
      downloadButton.disabled = !lastDownloadUrl;
    }
  }

  function parseEventLine(line) {
    const cleanLine = String(line || "").trim();

    if (!cleanLine) {
      return null;
    }

    try {
      return JSON.parse(cleanLine);
    } catch (error) {
      console.warn(
        "Invalid NDJSON event ignored.",
        error
      );

      return null;
    }
  }

  async function generateViaStream(
    streamUrl,
    formData
  ) {
    const response = await fetch(
      streamUrl,
      {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": getCookie(
            "csrftoken"
          ),
        },
        credentials: "same-origin",
      }
    );

    const contentType = String(
      response.headers.get("content-type")
      || ""
    ).toLowerCase();

    if (!response.ok) {
      if (contentType.includes("application/json")) {
        const errorData = await response
          .json()
          .catch(() => ({}));

        throw new Error(
          errorData.code
            ? translate(
                errorData.code,
                errorData.message
              )
            : (
                errorData.message
                || translate(
                  "UI_REQUEST_FAILED",
                  "The request failed."
                )
              )
        );
      }

      const errorText = await response
        .text()
        .catch(() => "");

      throw new Error(
        errorText
        || translate(
          "UI_REQUEST_FAILED",
          "The request failed."
        )
      );
    }

    if (
      !response.body
      || !response.body.getReader
    ) {
      throw new Error(
        translate(
          "UI_STREAM_UNSUPPORTED",
          "Streaming is not supported."
        )
      );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = "";
    let totalRequirements = 0;
    let completed = false;

    setProgress(
      2,
      translate(
        "UI_STARTING",
        "Starting generation…"
      )
    );

    const processEvent = (event) => {
      if (!event) {
        return;
      }

      if (event.type === "started") {
        totalRequirements = Number(
          event.total_requirements || 0
        );

        setProgress(
          event.progress ?? 0,
          totalRequirements
            ? (
                `${translate(
                  "UI_PREPARING",
                  "Preparing requirements…"
                )} (0/${totalRequirements})`
              )
            : translate(
                "UI_PREPARING",
                "Preparing requirements…"
              )
        );

        return;
      }

      if (event.type === "requirement_started") {
        const current = Number(
          event.current || 0
        );

        const total = Number(
          event.total || totalRequirements
        );

        const requirement = (
          event.requirement_number
          ?? "?"
        );

        const scenario = event.scenario_name
          ? ` — ${event.scenario_name}`
          : "";

        setProgress(
          event.progress ?? 0,
          (
            `${translate(
              "UI_PROCESSING",
              "Processing requirement"
            )} ${requirement}${scenario} `
            + `(${current}/${total})`
          )
        );

        return;
      }

      if (event.type === "requirement_completed") {
        const current = Number(
          event.current || 0
        );

        const total = Number(
          event.total || totalRequirements
        );

        const requirement = (
          event.requirement_number
          ?? "?"
        );

        setProgress(
          event.progress ?? 0,
          (
            `Requirement ${requirement} completed `
            + `(${current}/${total})`
          )
        );

        return;
      }

      if (event.type === "completed") {
        completed = true;

        setProgress(
          100,
          translate(
            "UI_COMPLETED",
            "Completed. Ready to download."
          )
        );

        applyCompletedUi(event);

        showSuccess(
          "Test cases generated successfully."
        );

        return;
      }

      if (event.type === "error") {
        throw new Error(
          event.code
            ? translate(
                event.code,
                event.message
              )
            : (
                event.message
                || translate(
                  "ERR_STREAM_GENERATION",
                  "Generation failed."
                )
              )
        );
      }
    };

    while (true) {
      const {
        value,
        done,
      } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(
        value,
        {
          stream: true,
        }
      );

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        processEvent(
          parseEventLine(line)
        );
      }
    }

    buffer += decoder.decode();

    if (buffer.trim()) {
      processEvent(
        parseEventLine(buffer)
      );
    }

    if (!completed) {
      throw new Error(
        translate(
          "UI_STREAM_ENDED",
          "The generation stream ended unexpectedly."
        )
      );
    }
  }

  function triggerDownload(blob, filename) {
    const objectUrl = window.URL.createObjectURL(
      blob
    );

    const anchor = document.createElement("a");

    anchor.href = objectUrl;
    anchor.download = filename || "TC.xlsx";

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    window.URL.revokeObjectURL(objectUrl);
  }

  async function downloadXlsx(downloadUrl) {
    const response = await fetch(
      downloadUrl,
      {
        method: "GET",
        credentials: "same-origin",
      }
    );

    if (!response.ok) {
      throw new Error(
        translate(
          "UI_DOWNLOAD_FAILED",
          "Download failed."
        )
      );
    }

    const blob = await response.blob();

    const contentDisposition = String(
      response.headers.get(
        "Content-Disposition"
      )
      || ""
    );

    const filenameMatch = contentDisposition.match(
      /filename="([^"]+)"/i
    );

    const filename = (
      filenameMatch?.[1]
      || "TC.xlsx"
    );

    triggerDownload(
      blob,
      filename
    );
  }

  function getAssignedTo() {
    const assignedTo = String(
      assignedInput?.value || ""
    ).trim();

    return assignedTo || null;
  }

function openDocumentInfoModal() {
  if (!SweetAlert) {
    return;
  }

  SweetAlert.fire({
    icon: "info",
    title: "PDD/FDD document requirements",
    html: `
      <div class="tc-doc-modal">
        <p class="tc-doc-modal__subtitle">
          Process Definition Document (PDD) /
          Functional Design Document (FDD)
        </p>

        <p>
          The generator analyzes the document structure to identify
          each main requirement and split its related content into
          independent blocks before generating test cases.
        </p>

        <h3>Supported document structures</h3>

        <div class="tc-doc-formats">
          <section class="tc-doc-format">
            <h4>Beecker PDD</h4>

            <p>
              Requirements are detected inside the
              <strong>
                Acciones detalladas del proceso TO-BE
              </strong>
              section. The section is commonly numbered as
              <strong>2.4</strong>, but the section number is optional.
            </p>

            <div class="tc-doc-example">
              <span>Classic format</span>

              <pre>2.4 Acciones detalladas del proceso TO-BE

1. Nombre de la acción: Consultar información
Descripción general: ...

2. Nombre de la acción: Validar datos
Descripción general: ...</pre>
            </div>

            <div class="tc-doc-example">
              <span>Numbered format</span>

              <pre>2.4 Acciones detalladas del proceso TO-BE

1. Obtener información de entrada
Descripción general: ...

2. Procesar información
Descripción general: ...</pre>
            </div>
          </section>

          <section class="tc-doc-format">
            <h4>Nestlé PDD</h4>

            <p>
              Requirements are detected inside a
              <strong>Process steps</strong>
              section. The section number may vary, and each
              numbered hash heading starts a new requirement block.
            </p>

            <div class="tc-doc-example">
              <span>Example</span>

              <pre>6.2. Process steps

#1 Open source system
Requirement content...

#2 Enter input data
Requirement content...

#3 Generate output
Requirement content...</pre>
            </div>
          </section>

          <section class="tc-doc-format">
            <h4>Heineken FDD</h4>

            <p>
              Requirements are detected from structured requirement
              IDs. A specific section title is not required. Each
              recognized ID identifies the beginning of a new
              requirement block.
            </p>

            <div class="tc-doc-example">
              <span>Example</span>

              <pre>PRJ.001.001 Start process
Requirement content...

PRJ.001.002 Validate input data
Requirement content...

PRJ.001.003 Generate output
Requirement content...</pre>
            </div>
          </section>
        </div>

        <h3>Required content</h3>

        <ul>
          <li>
            A project ID identifiable in the document or file name.
          </li>

          <li>
            Clear and consistently structured main requirement
            headings.
          </li>

          <li>
            A clear title for each main requirement.
          </li>

          <li>
            The descriptions, validations, tables, and process details
            related to a requirement should appear before the next
            main requirement heading.
          </li>
        </ul>

        <h3>Important</h3>

        <ul>
          <li>
            Use the same heading structure consistently throughout
            the functional section.
          </li>

          <li>
            Internal steps should remain inside their parent
            requirement unless they are intended to be processed
            as independent test scope.
          </li>

          <li>
            Duplicated or ambiguous headings may reduce requirement
            detection accuracy.
          </li>

          <li>
            If no supported structure can be detected reliably, the
            document may not be segmented into individual
            requirements correctly.
          </li>
        </ul>
      </div>
    `,
    confirmButtonText: "Close",
    width: "min(900px, 94vw)",
    allowOutsideClick: true,
    allowEscapeKey: true,
  });
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

          <!-- =========================
               ADEQUATE
          ========================== -->
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
              The requirement represents a cohesive functional unit
              with one main objective and a consistent business result.
            </p>

            <ul class="tc-review-modal-card__list">
              <li>
                Its steps and internal activities belong to the same
                functional flow.
              </li>

              <li>
                It may contain multiple rules, exceptions, systems,
                files, sources, or transformations.
              </li>

              <li>
                These elements continue contributing to the same
                functional objective.
              </li>

              <li>
                Its internal activities do not represent clearly
                independent functional blocks.
              </li>
            </ul>
          </section>


          <!-- =========================
               HIGH CONCENTRATION
          ========================== -->
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
              The requirement still represents one main functional
              objective, but contains significant internal complexity.
            </p>

            <ul class="tc-review-modal-card__list">
              <li>
                It may contain multiple business rules, decisions,
                exceptions, variants, or execution paths.
              </li>

              <li>
                These conditions significantly change how the same
                final result is achieved.
              </li>

              <li>
                The requirement is more complex to validate, but its
                behaviors still belong mainly to the same functional
                unit.
              </li>

              <li>
                There is not enough functional independence to
                consider the internal behaviors separate requirements.
              </li>
            </ul>
          </section>


          <!-- =========================
               SATURATED
          ========================== -->
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
              The requirement contains multiple clearly distinguishable
              functional blocks within the same requirement.
            </p>

            <ul class="tc-review-modal-card__list">
              <li>
                The blocks may have their own functional purpose.
              </li>

              <li>
                They may consume different inputs, sources,
                or artifacts.
              </li>

              <li>
                They may apply their own business rules or
                transformations.
              </li>

              <li>
                They produce identifiable and verifiable results.
              </li>

              <li>
                They can reasonably be tested as separate functional
                units, even when all of them contribute to the same
                higher-level objective.
              </li>
            </ul>
          </section>

        </div>


        <!-- =========================
             IMPORTANT
        ========================== -->
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
              Multiple systems, files, banks, or sources do not
              determine the classification by themselves.
            </span>

            <span>
              The analysis focuses on functional cohesion,
              complexity, and independence between blocks.
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

  fileUiBtn?.addEventListener(
    "click",
    () => fileInput?.click()
  );

  uploadOrb?.addEventListener(
    "click",
    () => fileInput?.click()
  );

  fileInput?.addEventListener(
    "change",
    () => {
      const file = fileInput.files?.[0] || null;
      void selectFile(file);
    }
  );

  clearFileButton?.addEventListener(
    "click",
    (event) => {
      event.preventDefault();
      clearFileSelection();
    }
  );

  requirementsPreviewButton?.addEventListener(
    "click",
    openRequirementsModal
  );

  docInfoBtn?.addEventListener(
    "click",
    openDocumentInfoModal
  );

  requirementReviewInfoBtn?.addEventListener(
  "click",
  openRequirementReviewInfoModal
);

  assignedInput?.addEventListener(
    "input",
    () => {
      assignedInput.classList.remove(
        "is-invalid"
      );
    }
  );

  uploader?.addEventListener(
    "dragover",
    (event) => {
      event.preventDefault();

      uploader.classList.add(
        "is-dragover"
      );
    }
  );

  uploader?.addEventListener(
    "dragleave",
    () => {
      uploader.classList.remove(
        "is-dragover"
      );
    }
  );

  uploader?.addEventListener(
    "drop",
    (event) => {
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
    async (event) => {
      event.preventDefault();

      const streamUrl = (
        form.dataset.generateStreamUrl
        || ""
      );

      if (!streamUrl) {
        await showError(
          translate(
            "UI_GENERATE_URL_MISSING",
            "The generation URL is not configured."
          )
        );

        return;
      }

      if (!selectedFile) {
        await showError(
          translate(
            "UI_SELECT_FILE",
            "Please select a document."
          )
        );

        return;
      }

      if (!lastPreview) {
        await showError(
          translate(
            "UI_ANALYSIS_PENDING",
            "Please wait for document analysis."
          )
        );

        return;
      }

      const assignedTo = getAssignedTo();

      if (!assignedTo) {
        assignedInput?.classList.add(
          "is-invalid"
        );

        assignedInput?.focus();

        await showError(
          translate(
            "UI_SELECT_ASSIGNED",
            "Assigned To is required."
          )
        );

        return;
      }

      if (
        Array.isArray(selectedRequirementNumbers)
        && selectedRequirementNumbers.length === 0
      ) {
        await showError(
          translate(
            "UI_SELECT_REQUIREMENT",
            "Select at least one requirement."
          )
        );

        return;
      }

      const generationFormData = new FormData();

      generationFormData.set(
        "document",
        selectedFile,
        selectedFile.name
      );

      generationFormData.set(
        "assigned_to",
        assignedTo
      );

      generationFormData.set(
        "selected_requirements",
        selectedRequirementNumbers === null
          ? ""
          : selectedRequirementNumbers.join(",")
      );

      resetGenerationResult();
      setProgress(
        0,
        translate(
          "UI_STARTING",
          "Starting generation…"
        )
      );

      setOverlay(true);

      if (submitButton) {
        submitButton.disabled = true;
      }

      try {
  await generateViaStream(
    streamUrl,
    generationFormData
  );
} catch (error) {
  setOverlay(false);
  resetGenerationResult();

  await showError(
    error?.message
    || "An unexpected error occurred."
  );
} finally {
  setOverlay(false);

  if (submitButton) {
    submitButton.disabled = false;
  }
}
    }
  );

  downloadButton?.addEventListener(
    "click",
    async () => {
      if (!lastDownloadUrl) {
        await showError(
          translate(
            "UI_DOWNLOAD_URL_MISSING",
            "The download URL is not available."
          )
        );

        return;
      }

      downloadButton.disabled = true;

      try {
        await downloadXlsx(
          lastDownloadUrl
        );
      } catch (error) {
        await showError(
          error?.message
          || translate(
            "UI_DOWNLOAD_FAILED",
            "Download failed."
          )
        );
      } finally {
        downloadButton.disabled = false;
      }
    }
  );

  if (downloadButton) {
    downloadButton.disabled = true;
  }

  clearRequirementsPreview();
  resetGenerationResult();
  setOverlay(false);
});