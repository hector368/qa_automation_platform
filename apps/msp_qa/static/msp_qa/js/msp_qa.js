/**
 * MSP QA Matrix
 * Seleccion multiple, revision fila por fila y escritura por lotes.
 */
(function () {
  "use strict";

  var workspace = document.getElementById("mspWorkspace");

  if (!workspace) {
    return;
  }

  var catalogUrl = workspace.dataset.catalogUrl;
  var previewUrl = workspace.dataset.previewUrl;
  var editUrl = workspace.dataset.editUrl;
  var batchWriteUrl = workspace.dataset.batchWriteUrl;
  var isConfigured = workspace.dataset.configured === "1";

  var catalogCount = document.getElementById("catalogCount");
  var selectedCount = document.getElementById("selectedCount");
  var skippedCount = document.getElementById("skippedCount");
  var skippedBtn = document.getElementById("skippedBtn");
  var selectRowsBtn = document.getElementById("selectRowsBtn");
  var refreshCatalogBtn =
    document.getElementById("refreshCatalogBtn");
  var progressBar = document.getElementById("progressBar");
  var progressFill = document.getElementById("progressFill");
  var catalogHelp = document.getElementById("catalogHelp");

  var selectionPanel = document.getElementById("selectionPanel");
  var previewRowId = document.getElementById("previewRowId");
  var previewTableBody =
    document.getElementById("previewTableBody");
  var prevRowBtn = document.getElementById("prevRowBtn");
  var nextRowBtn = document.getElementById("nextRowBtn");
  var rowPosition = document.getElementById("rowPosition");
  var previewNotes = document.getElementById("previewNotes");
  var writeBtn = document.getElementById("writeBtn");
  var writeCount = document.getElementById("writeCount");

  var resultsPanel = document.getElementById("resultsPanel");
  var resultsSummary = document.getElementById("resultsSummary");
  var resultsTableBody =
    document.getElementById("resultsTableBody");
  var resultsNotes = document.getElementById("resultsNotes");

  var catalogItems = [];
  var skippedProjects = [];
  var selectedIds = [];

  var previewRows = [];
  var previewId = "";
  var columnLabels = {};
  var currentIndex = 0;
  var editedFields = {};
  var editingField = "";

  var SweetAlert = window.Swal || null;

  function escapeHtml(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function showError(title, message) {
    if (SweetAlert) {
      SweetAlert.fire({
        icon: "error",
        title: title,
        text: message,
        confirmButtonText: "Got it"
      });

      return;
    }

    window.console.error(title, message);
  }

  function setProgress(percentage) {
    progressBar.hidden = false;
    progressFill.style.width = Math.min(
      100,
      Math.max(0, Number(percentage) || 0)
    ) + "%";
  }

  function hideProgress() {
    progressBar.hidden = true;
    progressFill.style.width = "0%";
  }

  /**
   * Lee una respuesta NDJSON evento por evento, sin esperar al final.
   */
  function streamNdjson(url, options, onEvent) {
    return fetch(url, options).then(function (response) {
      if (!response.ok) {
        return response.json().catch(function () {
          return null;
        }).then(function (payload) {
          throw new Error(
            payload && payload.message
              ? payload.message
              : "The request could not be completed."
          );
        });
      }

      var reader = response.body.getReader();
      var decoder = new TextDecoder();
      var buffer = "";

      function handleLine(line) {
        if (line.trim()) {
          onEvent(JSON.parse(line));
        }
      }

      function pump() {
        return reader.read().then(function (result) {
          if (result.done) {
            handleLine(buffer);
            return;
          }

          buffer += decoder.decode(result.value, { stream: true });

          var lines = buffer.split("\n");
          buffer = lines.pop();

          lines.forEach(handleLine);

          return pump();
        });
      }

      return pump();
    });
  }

  function getCsrfToken() {
    var field = document.querySelector(
      'input[name="csrfmiddlewaretoken"]'
    );

    return field ? field.value : "";
  }

  function findItem(mspId) {
    for (var index = 0; index < catalogItems.length; index += 1) {
      if (catalogItems[index].msp_id === mspId) {
        return catalogItems[index];
      }
    }

    return null;
  }

  function buildNote(title, entries) {
    var block = document.createElement("div");
    block.className = "msp-diagnostic";

    var heading = document.createElement("div");
    heading.className = "msp-diagnostic__title";
    heading.textContent = title;

    var chips = document.createElement("div");
    chips.className = "msp-chips";

    entries.forEach(function (entry) {
      var chip = document.createElement("span");
      chip.className = "msp-chip";
      chip.textContent = entry.label;

      if (entry.value) {
        var value = document.createElement("span");
        value.className = "msp-chip__value";
        value.textContent = entry.value;
        chip.appendChild(value);
      }

      chips.appendChild(chip);
    });

    block.appendChild(heading);
    block.appendChild(chips);

    return block;
  }

  // ====================================================================
  // Visor de la fila actual
  // ====================================================================

  function postForm(url, fields) {
    var body = new URLSearchParams();

    Object.keys(fields).forEach(function (key) {
      body.append(key, fields[key]);
    });

    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": getCsrfToken(),
        Accept: "application/json"
      },
      body: body.toString()
    }).then(function (response) {
      return response.json().catch(function () {
        return null;
      }).then(function (payload) {
        if (!response.ok || !payload || payload.ok === false) {
          throw new Error(
            payload && payload.message
              ? payload.message
              : "The edit could not be saved."
          );
        }

        return payload;
      });
    });
  }

  function currentRowEdits() {
    var row = previewRows[currentIndex];

    if (!row) {
      return [];
    }

    return editedFields[row.msp_id] || [];
  }

  function saveEdit(field, value) {
    var row = previewRows[currentIndex];

    postForm(editUrl, {
      preview_id: previewId,
      msp_id: row.msp_id,
      field: field,
      value: value
    }).then(function (payload) {
      previewRows[currentIndex] = payload.row;
      editedFields[payload.row.msp_id] = payload.edited_fields || [];
      editingField = "";
      renderCurrentRow();
    }).catch(function (error) {
      showError("Edit", error.message);
      editingField = "";
      renderCurrentRow();
    });
  }

  function buildEditor(field, value) {
    var wrapper = document.createElement("div");
    wrapper.className = "msp-cell";

    var input = document.createElement("input");
    input.type = "text";
    input.className = "msp-cell__input";
    input.value = value === null || value === undefined
      ? ""
      : String(value);

    var save = document.createElement("button");
    save.type = "button";
    save.className = "msp-edit-btn msp-edit-btn--save";
    save.textContent = "✓";
    save.title = "Save";

    var cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "msp-edit-btn msp-edit-btn--cancel";
    cancel.textContent = "✕";
    cancel.title = "Cancel";

    function commit() {
      saveEdit(field, input.value);
    }

    function abort() {
      editingField = "";
      renderCurrentRow();
    }

    save.addEventListener("click", commit);
    cancel.addEventListener("click", abort);

    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        commit();
      }

      if (event.key === "Escape") {
        event.preventDefault();
        abort();
      }
    });

    wrapper.appendChild(input);
    wrapper.appendChild(save);
    wrapper.appendChild(cancel);

    window.setTimeout(function () {
      input.focus();
      input.select();
    }, 0);

    return wrapper;
  }

  function buildValueCell(field, value, isEmpty) {
    if (editingField === field) {
      return buildEditor(field, value);
    }

    var wrapper = document.createElement("div");
    wrapper.className = "msp-cell";

    var textNode = document.createElement("span");
    textNode.className = "msp-cell__text";
    textNode.textContent = isEmpty
      ? "left untouched"
      : String(value);

    if (currentRowEdits().indexOf(field) >= 0) {
      var tag = document.createElement("span");
      tag.className = "msp-edited-tag";
      tag.textContent = "edited";
      textNode.appendChild(tag);
    }

    var pencil = document.createElement("button");
    pencil.type = "button";
    pencil.className = "msp-edit-btn";
    pencil.textContent = "✏️";
    pencil.title = "Edit this value";

    pencil.addEventListener("click", function () {
      editingField = field;
      renderCurrentRow();
    });

    wrapper.appendChild(textNode);
    wrapper.appendChild(pencil);

    return wrapper;
  }

  function renderCurrentRow() {
    previewTableBody.innerHTML = "";

    var row = previewRows[currentIndex];

    if (!row) {
      previewRowId.textContent = "—";
      rowPosition.textContent = "0 / 0";
      return;
    }

    previewRowId.textContent = row.msp_id || "—";

    Object.keys(columnLabels).forEach(function (field) {
      var value = row[field];
      var isEmpty = value === null || value === "" ||
        typeof value === "undefined";

      var tr = document.createElement("tr");
      tr.className = isEmpty
        ? "msp-table__row--empty"
        : "msp-table__row--filled";

      var nameCell = document.createElement("td");
      nameCell.className = "msp-table__name";
      nameCell.textContent = columnLabels[field];

      var valueCell = document.createElement("td");
      valueCell.className = "msp-table__value";
      valueCell.appendChild(buildValueCell(field, value, isEmpty));

      tr.appendChild(nameCell);
      tr.appendChild(valueCell);
      previewTableBody.appendChild(tr);
    });

    rowPosition.textContent = (currentIndex + 1) + " / " +
      previewRows.length;

    prevRowBtn.disabled = currentIndex === 0;
    nextRowBtn.disabled = currentIndex >= previewRows.length - 1;
  }

  function moveRow(step) {
    var nextIndex = currentIndex + step;

    if (nextIndex < 0 || nextIndex >= previewRows.length) {
      return;
    }

    currentIndex = nextIndex;
    editingField = "";
    renderCurrentRow();
  }

  function clearPreview() {
    previewRows = [];
    previewId = "";
    currentIndex = 0;
    editedFields = {};
    editingField = "";
    previewTableBody.innerHTML = "";
    previewNotes.innerHTML = "";
    selectionPanel.hidden = true;
  }

  function runPreview() {
    clearPreview();
    resultsPanel.hidden = true;

    var items = selectedIds.map(function (mspId) {
      var item = findItem(mspId);

      return {
        project: item.project_name,
        block: item.block_code
      };
    });

    var body = new URLSearchParams();
    body.append("items", JSON.stringify(items));

    selectRowsBtn.disabled = true;
    catalogHelp.textContent = "Extracting the selected rows…";
    setProgress(0);

    return streamNdjson(previewUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": getCsrfToken(),
        Accept: "application/x-ndjson"
      },
      body: body.toString()
    }, function (event) {
      if (event.type === "error") {
        throw new Error(event.message);
      }

      if (event.type === "item_completed") {
        setProgress(event.progress);
        catalogHelp.textContent = "Reading " + event.current +
          " of " + event.total + " · " + event.project_name;
        return;
      }

      if (event.type !== "completed") {
        return;
      }

      previewRows = event.rows || [];
      previewId = event.preview_id || "";
      columnLabels = event.column_labels || {};
      currentIndex = 0;

      writeCount.textContent = String(previewRows.length);
      writeBtn.disabled = previewRows.length === 0;

      renderCurrentRow();

      var failures = event.failures || [];

      if (failures.length > 0) {
        previewNotes.appendChild(
          buildNote(
            "Rows that could not be read (" + failures.length + ")",
            failures.map(function (failure) {
              return {
                label: failure.project_name + "_" +
                  failure.block_code,
                value: failure.reason
              };
            })
          )
        );
      }

      selectionPanel.hidden = previewRows.length === 0 &&
        failures.length === 0;

      catalogHelp.textContent = previewRows.length +
        " row(s) ready to review.";

      if (selectionPanel.scrollIntoView) {
        selectionPanel.scrollIntoView({
          behavior: "smooth",
          block: "nearest"
        });
      }
    }).catch(function (error) {
      catalogHelp.textContent = "The preview could not be built.";
      showError("Preview", error.message);
    }).then(function () {
      hideProgress();
      selectRowsBtn.disabled = catalogItems.length === 0;
    });
  }

  // ====================================================================
  // Catalogo y seleccion
  // ====================================================================

  function buildPickListHtml(items) {
    if (items.length === 0) {
      return '<li class="msp-pick__empty">No rows match</li>';
    }

    return items.map(function (item) {
      var checked = selectedIds.indexOf(item.msp_id) >= 0
        ? " checked"
        : "";

      return '<li class="req-item" data-search="' +
        escapeHtml(
          (item.msp_id + " " + item.block_label).toLowerCase()
        ) +
        '"><label><input type="checkbox" class="msp-pick-check"' +
        ' data-id="' + escapeHtml(item.msp_id) + '"' + checked +
        '><span class="req-num">' + escapeHtml(item.msp_id) +
        '</span><span class="req-title">' +
        escapeHtml(item.block_label) + '</span></label></li>';
    }).join("");
  }

  function openPickModal() {
    if (!SweetAlert || catalogItems.length === 0) {
      return;
    }

    SweetAlert.fire({
      title: "",
      width: "min(980px, 92vw)",
      showCancelButton: true,
      confirmButtonText: "Apply selection",
      cancelButtonText: "Cancel",
      html: '<div class="req-modal msp-pick">' +
        '<div class="req-modal__header">' +
        '<div class="req-modal__title">Select rows</div>' +
        '<div class="req-modal__badges">' +
        '<span class="badge-mini">📋 Rows: ' +
        catalogItems.length + '</span>' +
        '<span class="badge-mini">✅ Selected: ' +
        '<span id="modalSelCount">0</span></span>' +
        '</div>' +
        '<div class="req-modal__toolbar">' +
        '<div class="req-toolbar__actions">' +
        '<button type="button" class="req-chip" id="pickAll">' +
        '<span class="req-chip__icon">✅</span>Select all</button>' +
        '<button type="button" class="req-chip req-chip--ghost"' +
        ' id="pickNone"><span class="req-chip__icon">🧹</span>' +
        'Clear</button>' +
        '</div>' +
        '<input type="text" id="pickSearch"' +
        ' placeholder="Filter by ID or block…" autocomplete="off">' +
        '</div></div>' +
        '<div class="req-modal__list"><ul class="req-list"' +
        ' id="pickList">' + buildPickListHtml(catalogItems) +
        '</ul></div></div>',
      didOpen: function (modal) {
        var checks = Array.prototype.slice.call(
          modal.querySelectorAll(".msp-pick-check")
        );
        var counter = modal.querySelector("#modalSelCount");
        var search = modal.querySelector("#pickSearch");

        function visibleChecks() {
          return checks.filter(function (check) {
            return !check.closest(".req-item").hidden;
          });
        }

        function updateCounter() {
          counter.textContent = String(
            checks.filter(function (check) {
              return check.checked;
            }).length
          );
        }

        checks.forEach(function (check) {
          check.addEventListener("change", updateCounter);
        });

        modal.querySelector("#pickAll")
          .addEventListener("click", function () {
            visibleChecks().forEach(function (check) {
              check.checked = true;
            });
            updateCounter();
          });

        modal.querySelector("#pickNone")
          .addEventListener("click", function () {
            visibleChecks().forEach(function (check) {
              check.checked = false;
            });
            updateCounter();
          });

        search.addEventListener("input", function () {
          var query = search.value.trim().toLowerCase();

          checks.forEach(function (check) {
            var item = check.closest(".req-item");
            item.hidden = query.length > 0 &&
              item.dataset.search.indexOf(query) < 0;
          });
        });

        updateCounter();
        search.focus();
      },
      preConfirm: function () {
        return Array.prototype.slice.call(
          document.querySelectorAll(".msp-pick-check:checked")
        ).map(function (check) {
          return check.dataset.id;
        });
      }
    }).then(function (result) {
      if (!result.isConfirmed) {
        return;
      }

      selectedIds = result.value || [];
      selectedCount.textContent = String(selectedIds.length);

      if (selectedIds.length === 0) {
        clearPreview();
        return;
      }

      runPreview();
    });
  }

  function showSkippedProjects() {
    if (!SweetAlert || skippedProjects.length === 0) {
      return;
    }

    var listHtml = skippedProjects.map(function (entry) {
      return "<li><strong>" + escapeHtml(entry.project_name) +
        "</strong><span>" + escapeHtml(entry.reason) +
        "</span></li>";
    }).join("");

    SweetAlert.fire({
      icon: "info",
      title: "Skipped projects",
      html: '<p style="margin:0 0 14px;font-size:14px;">' +
        "These projects produced no rows, so they are not in the " +
        "list above.</p>" +
        '<ul class="msp-skipped-list">' + listHtml + "</ul>",
      width: "min(640px, 92vw)",
      confirmButtonText: "Got it"
    });
  }

  function loadCatalog(forceRefresh) {
    selectRowsBtn.disabled = true;
    refreshCatalogBtn.disabled = true;
    selectedIds = [];
    selectedCount.textContent = "0";
    clearPreview();
    resultsPanel.hidden = true;

    catalogHelp.textContent = "Reading project descriptions…";
    setProgress(0);

    var url = catalogUrl + (forceRefresh ? "?refresh=1" : "");

    return streamNdjson(url, {
      headers: { Accept: "application/x-ndjson" }
    }, function (event) {
      if (event.type === "error") {
        throw new Error(event.message);
      }

      if (event.type === "project_completed") {
        setProgress(event.progress);
        catalogHelp.textContent = "Reading " + event.current +
          " of " + event.total + " · " + event.project_name;
        return;
      }

      if (event.type !== "completed") {
        return;
      }

      catalogItems = event.items || [];
      skippedProjects = event.skipped || [];

      catalogCount.textContent = String(catalogItems.length);
      skippedCount.textContent = String(skippedProjects.length);
      skippedBtn.disabled = skippedProjects.length === 0;

      catalogHelp.textContent = catalogItems.length +
        " row(s) available" +
        (event.from_cache ? " (from cache)" : "") + ".";

      selectRowsBtn.disabled = catalogItems.length === 0;
    }).catch(function (error) {
      catalogHelp.textContent = "The catalog could not be loaded.";
      showError("Catalog", error.message);
    }).then(function () {
      hideProgress();
      refreshCatalogBtn.disabled = false;
    });
  }

  // ====================================================================
  // Escritura y resultados
  // ====================================================================

  function addSummaryItem(label, value) {
    var item = document.createElement("div");
    item.className = "msp-summary__item";

    var term = document.createElement("dt");
    term.textContent = label;

    var description = document.createElement("dd");
    description.textContent = value;

    item.appendChild(term);
    item.appendChild(description);
    resultsSummary.appendChild(item);
  }

  function renderResults(payload) {
    var result = payload.result || {};
    var rows = result.rows || [];

    resultsSummary.innerHTML = "";
    addSummaryItem("Rows inserted", String(result.inserted || 0));
    addSummaryItem("Rows updated", String(result.updated || 0));
    addSummaryItem(
      "Cells written",
      String(result.updated_cells || 0)
    );

    resultsTableBody.innerHTML = "";

    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.className = "msp-table__row--filled";

      var idCell = document.createElement("td");
      idCell.className = "msp-table__name";
      idCell.textContent = row.msp_id;

      var actionCell = document.createElement("td");
      var badge = document.createElement("span");
      badge.className = "msp-action msp-action--" + row.action;
      badge.textContent = row.action === "inserted"
        ? "Inserted"
        : "Updated";
      actionCell.appendChild(badge);

      var rowCell = document.createElement("td");
      rowCell.className = "msp-table__value";
      rowCell.textContent = String(row.row_number);

      var columnsCell = document.createElement("td");
      columnsCell.className = "msp-table__value";
      columnsCell.textContent = String(
        (row.written_columns || []).length
      );

      tr.appendChild(idCell);
      tr.appendChild(actionCell);
      tr.appendChild(rowCell);
      tr.appendChild(columnsCell);
      resultsTableBody.appendChild(tr);
    });

    resultsNotes.innerHTML = "";

    if ((result.duplicate_ids || []).length > 0) {
      resultsNotes.appendChild(
        buildNote(
          "IDs that appear more than once in the matrix",
          result.duplicate_ids.map(function (entry) {
            return {
              label: entry.msp_id,
              value: "rows " + entry.rows.join(", ")
            };
          })
        )
      );
    }

    resultsPanel.hidden = false;

    if (resultsPanel.scrollIntoView) {
      resultsPanel.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
      });
    }
  }

  function runBatchWrite() {
    var items = selectedIds.map(function (mspId) {
      var item = findItem(mspId);

      return {
        project: item.project_name,
        block: item.block_code
      };
    });

    var body = new URLSearchParams();
    body.append("items", JSON.stringify(items));
    body.append("preview_id", previewId);

    writeBtn.disabled = true;
    catalogHelp.textContent = "Writing to the matrix…";
    setProgress(0);

    streamNdjson(batchWriteUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": getCsrfToken(),
        Accept: "application/x-ndjson"
      },
      body: body.toString()
    }, function (event) {
      if (event.type === "error") {
        throw new Error(event.message);
      }

      if (event.type === "item_completed") {
        setProgress(event.progress);
        catalogHelp.textContent = "Re-reading " + event.current +
          " of " + event.total + " · " + event.project_name;
        return;
      }

      if (event.type === "writing") {
        setProgress(event.progress);
        catalogHelp.textContent = "Writing " + event.total_rows +
          " row(s) to the matrix…";
        return;
      }

      if (event.type === "completed") {
        setProgress(100);
        renderResults(event);

        catalogHelp.textContent = "Done in " +
          event.elapsed_seconds + "s.";
      }
    }).catch(function (error) {
      showError("Write to matrix", error.message);
      catalogHelp.textContent = "The write did not complete.";
    }).then(function () {
      hideProgress();
      writeBtn.disabled = previewRows.length === 0;
    });
  }

  function countEditedRows() {
    var edited = Object.keys(editedFields).filter(function (mspId) {
      return (editedFields[mspId] || []).length > 0;
    }).length;

    if (edited === 0) {
      return "";
    }

    return ", including " + edited + " with manual edits";
  }

  function confirmBatchWrite() {
    if (previewRows.length === 0) {
      return;
    }

    var confirmation = SweetAlert
      ? SweetAlert.fire({
          icon: "question",
          title: "Write to the matrix",
          text: previewRows.length + " row(s) will be written" +
            countEditedRows() + ". Existing IDs are overwritten " +
            "in place; new ones are inserted at the top. Continue?",
          showCancelButton: true,
          confirmButtonText: "Yes, write them",
          cancelButtonText: "Cancel"
        }).then(function (result) {
          return result.isConfirmed;
        })
      : Promise.resolve(true);

    confirmation.then(function (confirmed) {
      if (confirmed) {
        runBatchWrite();
      }
    });
  }

  selectRowsBtn.addEventListener("click", openPickModal);
  skippedBtn.addEventListener("click", showSkippedProjects);
  writeBtn.addEventListener("click", confirmBatchWrite);

  prevRowBtn.addEventListener("click", function () {
    moveRow(-1);
  });

  nextRowBtn.addEventListener("click", function () {
    moveRow(1);
  });

  refreshCatalogBtn.addEventListener("click", function () {
    loadCatalog(true);
  });

  if (isConfigured) {
    loadCatalog(false);
  } else {
    catalogHelp.textContent =
      "Configure the connection to load the catalog.";
    hideProgress();
  }
})();
