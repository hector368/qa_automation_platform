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

  const metricInput = document.getElementById(
    "mInput"
  );

  const metricOutput = document.getElementById(
    "mOutput"
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
  const documentInfoButton = document.getElementById(
  "docInfoBtn"
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

    downloadButton.disabled = true;

    metricRequirements.textContent = "0";
    metricTestCases.textContent = "0";
    metricInput.textContent = "0";
    metricOutput.textContent = "0";
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

      if (selected.length === 0) {
        SweetAlert.showValidationMessage(
          "Select at least one requirement."
        );

        return false;
      }

      return selected;
    },
  });

  if (!result.isConfirmed) {
    return;
  }

  selectedRequirementIds = new Set(
    result.value || []
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

    metricInput.textContent = String(
      usage.input_tokens || 0
    );

    metricOutput.textContent = String(
      usage.output_tokens || 0
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
          setProgress(
            event.progress,
            (
              `${event.requirement_id} completed `
              + `(${event.current}/${event.total})`
            )
          );
        }

        if (event.type === "completed") {
          completed = true;

          setProgress(
            100,
            "Completed. Ready to download."
          );

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
      ) {
        await showError(
          "Select at least one requirement."
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

  clearFileSelection();
});