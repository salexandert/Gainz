function gainzFormatImportResult(result, fileName) {
    var warnings = result.warnings || [];
    var sourceName = fileName || result.filename || "uploaded file";
    var message = "Imported " + (result.imported_count || 0) + " row(s)";

    if (result.files && result.files.length) {
        sourceName = result.files.length + " demo file(s)";
    }

    message += " from " + sourceName + ".";
    message += " Skipped " + (result.skipped_count || 0) + " row(s).";

    if (result.header_row_used && result.header_row_used > 1) {
        message += " Used header row " + result.header_row_used + ".";
    }

    if (warnings.length > 0) {
        message += " Review " + warnings.length + " warning(s) below before relying on generated reports.";
    } else {
        message += " Next: import more files, then run Auto Link or open Holdings & Accounting.";
    }

    return message;
}

function gainzShowImportResult(result, fileName, alertClass) {
    var warnings = result.warnings || [];
    var warningRows = result.warning_rows || [];
    var resultClass = alertClass || (warnings.length > 0 ? "alert-warning" : "alert-info");

    $("#import_upload_result")
        .removeClass("alert-danger alert-info alert-warning")
        .addClass(resultClass)
        .text(gainzFormatImportResult(result, fileName))
        .show();

    if (warnings.length > 0 || warningRows.length > 0) {
        gainzSetImportWarningWorkflow(
            "#import_warning_workflow",
            "#import_warning_workflow_table",
            warnings,
            warningRows
        );
    } else {
        $("#import_warning_workflow").hide();
    }

    if (result.data_summary) {
        gainzSetSourceOverlapWorkflow(result.data_summary.source_overlaps || []);
        gainzRenderDataSources(result.data_summary);
        gainzUpdateImportContinuePanel(result.data_summary);
    }
}

function gainzUpdateImportContinuePanel(summary) {
    var panel = $("#import_continue_panel");
    if (panel.length === 0 || !summary) {
        return;
    }

    if ((summary.transaction_count || 0) > 0) {
        panel.show();
    } else {
        panel.hide();
    }
}

function gainzRenderSourceOverlapTable(rows) {
    var table = $("#source_overlap_table");
    var tbody = table.find("tbody");

    if (table.length === 0 || tbody.length === 0) {
        return;
    }

    tbody.empty();
    (rows || []).forEach(function(row) {
        var tableRow = $("<tr></tr>");
        tableRow.append(
            $("<td></td>")
                .attr("title", row.source_a || "")
                .append($("<span></span>").text(row.name_a || "Source A"))
                .append("<br>")
                .append($("<small></small>").text(row.date_range_a || ""))
        );
        tableRow.append(
            $("<td></td>")
                .attr("title", row.source_b || "")
                .append($("<span></span>").text(row.name_b || "Source B"))
                .append("<br>")
                .append($("<small></small>").text(row.date_range_b || ""))
        );
        tableRow.append($("<td></td>").text((row.matching_rows || 0) + " (" + (row.overlap_percent || "0%") + ")"));
        tableRow.append(
            $("<td></td>").append(
                $('<span class="gainz-status-badge status-needs-review"></span>').text(row.status || "Needs review")
            )
        );
        tableRow.append($("<td></td>").text(row.message || "Review these source files for overlap."));
        tableRow.append($("<td></td>").text(row.next_action || "Review sources and remove the duplicate only after confirming the overlap."));
        tbody.append(tableRow);
    });
}

function gainzSetSourceOverlapWorkflow(rows) {
    var panel = $("#source_overlap_workflow");
    if (panel.length === 0) {
        return;
    }

    if (rows && rows.length > 0) {
        gainzRenderSourceOverlapTable(rows);
        panel.show();
    } else {
        panel.hide();
    }
}

function gainzRenderDataSources(summary) {
    var table = $("#import_data_sources_table");
    var tbody = table.find("tbody");

    if (!summary || table.length === 0 || tbody.length === 0) {
        return;
    }

    tbody.empty();

    if (!summary.sources || summary.sources.length === 0) {
        tbody.append(
            $("<tr></tr>").append(
                $("<td></td>")
                    .attr("colspan", 5)
                    .addClass("text-muted")
                    .text("No imported data yet.")
            )
        );
        return;
    }

    summary.sources.forEach(function(source) {
        var row = $("<tr></tr>");
        var statusClass = "badge-secondary";

        if (source.has_overlap) {
            statusClass = "badge-warning";
        } else if (source.is_file) {
            statusClass = "badge-success";
        } else if (source.is_gainz_source) {
            statusClass = "badge-info";
        }

        row.append($("<td></td>").attr("title", source.source || "").text(source.name || "Unknown source"));
        row.append($("<td></td>").text(source.count || 0));
        row.append($("<td></td>").text(source.date_range || "N/A"));
        row.append(
            $("<td></td>").append(
                $("<span></span>").addClass("badge").addClass(statusClass).text(source.status || "Not found")
            )
        );

        if (!source.is_gainz_source && source.source !== "Manual / Unknown") {
            row.append(
                $("<td></td>").append(
                    $('<button type="button" class="btn btn-sm btn-outline-danger remove-data-source-button">Remove from Current Data</button>')
                        .data("source", source.source)
                        .data("source-name", source.name || "this source")
                        .data("source-count", source.count || 0)
                )
            );
        } else {
            row.append($("<td></td>").addClass("text-muted").text("Managed by Gainz"));
        }

        tbody.append(row);
    });
}

function gainzShowColumnReviewResult(result) {
    var warnings = result.warnings || [];
    var message = warnings.join(" ") || "Column review needed. Choose the header row and map the columns below.";

    $("#import_warning_workflow").hide();
    $("#import_upload_result")
        .removeClass("alert-danger alert-info alert-warning")
        .addClass("alert-warning")
        .text(message)
        .show();

    gainzRenderColumnMapper(result.mapping);

    var mapper = $("#import_column_mapper");
    if (mapper.length) {
        $("html, body").animate({ scrollTop: mapper.offset().top - 90 }, 250);
    }
}

function gainzParseImportWarning(warning) {
    var raw = String(warning || "");
    var match = raw.match(/^(Skipped|Imported) row (\d+) from ([^:]+?)(?::| with )\s*(.*)$/i);
    var source = "Current import";
    var row = "N/A";
    var detail = raw;
    var issue = raw;
    var status = "Needs review";
    var nextAction = "Review the source row. If it should affect holdings or generated reports, fix the CSV mapping, re-import the source, or add a source-backed manual transaction.";

    if (match) {
        source = match[3];
        row = match[2];
        detail = match[4] || raw;
        issue = detail;
    }

    var lower = raw.toLowerCase();
    if (lower.indexOf("$0 usd spot price") !== -1 || lower.indexOf("usd spot price") !== -1) {
        issue = "$0 USD spot price";
        status = "Price review";
        nextAction = "If the row has a USD value, remove this source and re-import with a mapped USD spot price or total USD value column. If it was truly zero-value, keep documentation with the source file.";
    } else if (lower.indexOf("unrecognized transaction type") !== -1) {
        var typeMatch = raw.match(/unrecognized transaction type '([^']+)'/i);
        issue = "Unrecognized transaction type: " + (typeMatch ? typeMatch[1] : "unknown");
        status = "Classification review";
        nextAction = "Decide whether this row is a buy, sell, send, or receive. If it belongs in Gainz, use column review or add a manual transaction with the source row as support.";
    } else if (lower.indexOf("could not identify required columns") !== -1) {
        issue = "Required columns were not identified";
        status = "Mapping needed";
        nextAction = "Upload the file again with column review enabled, choose the header row, and map date, type, asset, quantity, and USD value columns.";
    } else if (lower.indexOf("could not parse this row") !== -1) {
        issue = "Could not parse row";
        status = "Row review";
        nextAction = "Check the source row's date, type, quantity, and USD value. Correct the CSV or add a manual transaction if the row should be included.";
    }

    return {
        raw: raw,
        source: source,
        row: row,
        issue: issue,
        status: status,
        next_action: nextAction
    };
}

function gainzNormalizeImportWarningRows(warnings, warningRows) {
    if (warningRows && warningRows.length > 0) {
        return warningRows;
    }

    return (warnings || []).map(gainzParseImportWarning);
}

function gainzRenderImportWarningTable(tableSelector, rows) {
    var table = $(tableSelector);
    var tbody = table.find("tbody");
    var reviewUrl = table.data("review-url");

    if (table.length === 0 || tbody.length === 0) {
        return;
    }

    tbody.empty();

    rows.forEach(function (row) {
        var tableRow = $("<tr></tr>");
        tableRow.append($("<td></td>").text(row.source || "Current import"));
        tableRow.append($("<td></td>").text(row.row || "N/A"));
        tableRow.append($("<td></td>").text(row.row_date || ""));
        tableRow.append($("<td></td>").text(row.row_type || ""));
        tableRow.append($("<td></td>").text(row.asset || ""));
        tableRow.append($("<td></td>").text(row.quantity || ""));
        tableRow.append($("<td></td>").text(row.issue || row.raw || "Review import row"));
        tableRow.append($("<td></td>").text(row.likely_category || ""));

        var reviewStatus = row.review_status || row.status || "Needs review";
        var badgeClass = row.is_resolved ? "status-verified" : "status-needs-review";
        var badge = $('<span class="gainz-status-badge"></span>')
            .addClass(badgeClass)
            .text(reviewStatus);
        tableRow.append($("<td></td>").append(badge));

        var decisionText = row.decision_label || "Not reviewed";
        if (row.review_note) {
            decisionText += ": " + row.review_note;
        }
        tableRow.append($("<td></td>").text(decisionText));
        tableRow.append($("<td></td>").text(row.notes || ""));

        var actionCell = $('<td class="import-warning-action"></td>');
        actionCell.append($("<p></p>").text(row.next_action || row.raw || "Review this source row."));

        if (reviewUrl) {
            var noteInput = $('<input type="text" class="form-control form-control-sm import-warning-note-input" placeholder="Add note">')
                .val(row.review_note || "");
            actionCell.append(noteInput);
            [
                ["true_zero_value_transfer", "True zero-value transfer"],
                ["needs_manual_usd_value", "Needs manual USD value"],
                ["ignore_for_now", "Ignore for now"],
                ["note", "Add note"]
            ].forEach(function(action) {
                var button = $('<button type="button" class="btn btn-sm btn-outline-primary import-warning-decision-button"></button>')
                    .text(action[1])
                    .data("decision", action[0])
                    .data("warning", row.raw || "");
                actionCell.append(button);
            });
        }

        tableRow.append(actionCell);
        tbody.append(tableRow);
    });
}

function gainzSetImportWarningWorkflow(panelSelector, tableSelector, warnings, warningRows) {
    var rows = gainzNormalizeImportWarningRows(warnings, warningRows);
    var panel = $(panelSelector);

    if (panel.length === 0) {
        return;
    }

    if (rows.length > 0) {
        gainzRenderImportWarningTable(tableSelector, rows);
        panel.show();
    } else {
        panel.hide();
    }
}

$(document).on("click", ".import-warning-decision-button", function() {
    var button = $(this);
    var table = button.closest("table");
    var reviewUrl = table.data("review-url");
    var note = button.closest("td").find(".import-warning-note-input").val() || "";

    if (!reviewUrl) {
        return;
    }

    button.prop("disabled", true).text("Saving...");
    $.ajax({
        type: "POST",
        url: reviewUrl,
        data: JSON.stringify({
            warning: button.data("warning"),
            decision: button.data("decision"),
            note: note
        }),
        dataType: "json",
        contentType: "application/json",
        success: function(data) {
            if (data.data_summary) {
                gainzSetImportWarningWorkflow(
                    "#import_warning_workflow",
                    "#import_warning_workflow_table",
                    data.data_summary.import_warnings || [],
                    data.data_summary.import_warning_rows || []
                );
                $("#import_upload_result")
                    .removeClass("alert-info alert-danger")
                    .addClass("alert-warning")
                    .text(data.message || "Import warning review decision saved.")
                    .show();
            }
        },
        error: function(xhr) {
            var message = "Review decision could not be saved.";
            if (xhr.responseJSON && xhr.responseJSON.error) {
                message = xhr.responseJSON.error;
            }
            alert(message);
        },
        complete: function() {
            button.prop("disabled", false).text(
                {
                    true_zero_value_transfer: "True zero-value transfer",
                    needs_manual_usd_value: "Needs manual USD value",
                    ignore_for_now: "Ignore for now",
                    note: "Add note"
                }[button.data("decision")] || "Save"
            );
        }
    });
});

function gainzParseDisplayNumber(value) {
    return Number(String(value).replace(/[$,]/g, '').trim());
}

function gainzBuildColumnSelect(field, columns, selectedColumn) {
    var fieldName = field.field;
    var select = $('<select class="form-control import-mapping-select"></select>');

    select.attr("data-field", fieldName);
    select.append($('<option value="">Do not use</option>'));

    (columns || []).forEach(function (column) {
        var option = $("<option></option>").attr("value", column).text(column);
        if (column === selectedColumn) {
            option.attr("selected", "selected");
        }
        select.append(option);
    });

    return select;
}

function gainzRenderHeaderCandidates(candidates) {
    var container = $("#import_header_candidates");
    container.empty();

    if (!candidates || candidates.length === 0) {
        return;
    }

    container.append($('<p class="text-muted mb-2"></p>').text("Possible header rows"));

    candidates.slice(0, 4).forEach(function (candidate) {
        var previewColumns = (candidate.columns || []).slice(0, 5).join(" | ");
        var button = $('<button type="button" class="btn btn-outline-secondary btn-sm mr-2 mb-2 import-header-candidate"></button>');
        button.attr("data-header-row", candidate.row_number);
        button.text("Row " + candidate.row_number + ": " + previewColumns);
        container.append(button);
    });
}

function gainzRenderSampleRows(sampleRows) {
    var container = $("#import_sample_rows");
    container.empty();

    if (!sampleRows || sampleRows.length === 0) {
        return;
    }

    var columns = Object.keys(sampleRows[0] || {});
    if (columns.length === 0) {
        return;
    }

    container.append($('<p class="text-muted mb-2"></p>').text("Sample rows Gainz will import"));

    var table = $('<table class="table table-sm table-striped table-bordered"></table>');
    var thead = $("<thead></thead>");
    var headerRow = $("<tr></tr>");
    columns.forEach(function (column) {
        headerRow.append($("<th></th>").text(column));
    });
    thead.append(headerRow);
    table.append(thead);

    var tbody = $("<tbody></tbody>");
    sampleRows.forEach(function (sampleRow) {
        var row = $("<tr></tr>");
        columns.forEach(function (column) {
            row.append($("<td></td>").text(sampleRow[column] == null ? "" : sampleRow[column]));
        });
        tbody.append(row);
    });
    table.append(tbody);
    container.append(table);
}

function gainzRenderColumnMapper(mapping) {
    if (!mapping) {
        return;
    }

    var mapper = $("#import_column_mapper");
    var fieldsContainer = $("#import_mapping_fields");
    var warningBox = $("#import_mapping_warning");
    var columns = mapping.columns || [];
    var suggestions = mapping.suggested_mapping || {};
    var missing = mapping.missing_required || [];
    var headerRow = parseInt(mapping.header_row || 1, 10);
    var dataStartRow = parseInt(mapping.data_start_row || (headerRow + 1), 10);

    $("#import_header_row").val(headerRow);
    $("#import_data_start_row").val(dataStartRow);
    fieldsContainer.empty();
    gainzRenderHeaderCandidates(mapping.header_candidates || []);

    (mapping.mapping_fields || []).forEach(function (field) {
        var selectedColumn = suggestions[field.field] || "";
        var wrapper = $('<div class="col-md-4 mb-3"></div>');
        var label = $("<label></label>").text(field.label + (field.required ? " *" : ""));
        wrapper.append(label);
        wrapper.append(gainzBuildColumnSelect(field, columns, selectedColumn));
        fieldsContainer.append(wrapper);
    });

    if (missing.length > 0) {
        warningBox
            .text("Missing required fields: " + missing.join(", ") + ".")
            .show();
    } else if (!mapping.has_pricing) {
        warningBox
            .text("No USD price or total value column was detected. Map one if the source includes it. If the file truly has no USD values, imported reports will need review.")
            .show();
    } else {
        warningBox.hide();
    }

    gainzRenderSampleRows(mapping.sample_rows || []);
    mapper.show();
}

function gainzCollectColumnMapping() {
    var mapping = {};

    $(".import-mapping-select").each(function () {
        var field = $(this).data("field");
        var value = $(this).val();

        if (value) {
            mapping[field] = value;
        }
    });

    return mapping;
}

if (window.Dropzone) {
    Dropzone.options.uploadCsvForm = {
        maxFilesize: 20,
        acceptedFiles: ".csv",
        dictDefaultMessage: "Click or drop files here to upload",
        previewTemplate: [
            '<div class="dz-preview dz-file-preview gainz-upload-preview">',
            '  <div class="dz-details">',
            '    <span class="dz-size" data-dz-size></span>',
            '    <span class="dz-filename" data-dz-name></span>',
            '  </div>',
            '  <div class="dz-progress"><span class="dz-upload" data-dz-uploadprogress></span></div>',
            '  <div class="dz-error-message"><span data-dz-errormessage></span></div>',
            '</div>'
        ].join(''),
        init: function () {
            this.on("sending", function (file, xhr, formData) {
                var reviewColumns = $("#import_review_columns_before_import").is(":checked") ? "1" : "0";
                formData.append("review_columns", reviewColumns);
                $("#import_upload_result")
                    .removeClass("alert-danger alert-warning")
                    .addClass("alert-info")
                    .text("Uploading and importing " + (file.name || "CSV") + ". Large files may take 10-30 seconds while Gainz parses rows, checks duplicates, and saves a revision.")
                    .show();
            });

            this.on("success", function (file, response) {
                var result = response || {};
                if (typeof result === "string") {
                    try {
                        result = JSON.parse(result);
                    } catch (e) {
                        result = {};
                    }
                }

                if (result.mapping_required) {
                    gainzShowColumnReviewResult(result);
                    return;
                }

                $("#import_column_mapper").hide();
                gainzShowImportResult(result, file.name || "uploaded file");
            });

            this.on("error", function (file, response) {
                var message = "Import failed for " + (file.name || "uploaded file") + ".";
                if (response) {
                    message += " " + String(response);
                }

                $("#import_upload_result")
                    .removeClass("alert-info")
                    .addClass("alert-danger")
                    .text(message)
                    .show();
            });
        }
    };
}

$(document).ready(function () {
    function openLinkedDetails(hash) {
        if (!hash || hash.length < 2) {
            return;
        }
        var target = $(hash);
        if (target.length === 0) {
            return;
        }
        if (target.is("details")) {
            target.prop("open", true);
            return;
        }
        target.closest("details").prop("open", true);
    }

    openLinkedDetails(window.location.hash);

    $(document).on("click", 'a[href^="#"]', function () {
        openLinkedDetails($(this).attr("href"));
    });

    $("#import_demo_data_button").on("click", function () {
        var button = $(this);
        var demoUrl = button.data("demo-url");

        button.prop("disabled", true).text("Loading Demo Data...");
        $("#import_upload_result")
            .removeClass("alert-danger alert-warning")
            .addClass("alert-info")
            .text("Loading demo data, checking for duplicate rows, and saving a revision...")
            .show();

        $.post(demoUrl)
            .done(function (result) {
                $("#import_column_mapper").hide();
                gainzShowImportResult(result, "demo data");
            })
            .fail(function (xhr) {
                var message = "Demo import failed.";
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    message += " " + xhr.responseJSON.error;
                }
                $("#import_upload_result")
                    .removeClass("alert-info alert-warning")
                    .addClass("alert-danger")
                    .text(message)
                    .show();
            })
            .always(function () {
                button.prop("disabled", false).text("Try Demo Data");
            });
    });

    $(document).on("click", ".import-header-candidate", function () {
        var headerRow = parseInt($(this).data("header-row"), 10) || 1;
        $("#import_header_row").val(headerRow);
        $("#import_data_start_row").val(headerRow + 1);
        $("#import_preview_mapping_button").trigger("click");
    });

    $("#import_preview_mapping_button").on("click", function () {
        var mapper = $("#import_column_mapper");
        var previewUrl = mapper.data("preview-url");

        $.ajax({
            url: previewUrl,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                header_row: $("#import_header_row").val(),
                data_start_row: $("#import_data_start_row").val()
            })
        }).done(function (result) {
            gainzRenderColumnMapper(result.mapping);
        }).fail(function (xhr) {
            var message = "Could not preview that header row.";
            if (xhr.responseJSON && xhr.responseJSON.error) {
                message += " " + xhr.responseJSON.error;
            }
            $("#import_mapping_warning").text(message).show();
        });
    });

    $("#import_submit_mapping_button").on("click", function () {
        var mapper = $("#import_column_mapper");
        var importUrl = mapper.data("import-url");
        var button = $(this);

        button.prop("disabled", true).text("Importing...");
        $("#import_upload_result")
            .removeClass("alert-danger alert-warning")
            .addClass("alert-info")
            .text("Importing with your mapped columns. Large files may take 10-30 seconds while Gainz parses rows, checks duplicates, and saves a revision.")
            .show();

        $.ajax({
            url: importUrl,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                header_row: $("#import_header_row").val(),
                data_start_row: $("#import_data_start_row").val(),
                column_mapping: gainzCollectColumnMapping()
            })
        }).done(function (result) {
            if (result.mapping_required) {
                gainzShowColumnReviewResult(result);
                return;
            }

            mapper.hide();
            gainzShowImportResult(result, "mapped CSV");
        }).fail(function (xhr) {
            var message = "Mapped import failed.";
            if (xhr.responseJSON && xhr.responseJSON.error) {
                message += " " + xhr.responseJSON.error;
            }
            $("#import_upload_result")
                .removeClass("alert-info alert-warning")
                .addClass("alert-danger")
                .text(message)
                .show();
        }).always(function () {
            button.prop("disabled", false).text("Import With These Columns");
        });
    });

    $(document).on("click", ".remove-data-source-button", function () {
        var button = $(this);
        var table = $("#import_data_sources_table");
        var removeUrl = table.data("remove-url");
        var source = button.data("source");
        var sourceName = button.data("source-name") || "this source";
        var sourceCount = button.data("source-count") || 0;
        var resultBox = $("#data_source_action_result");
        var confirmation = [
            "Remove " + sourceCount + " transaction(s) from " + sourceName + " in the current data set?",
            "",
            "Gainz will save a new revision. Prior revisions stay available in History.",
            "The original CSV file will not be deleted from disk."
        ].join("\n");

        if (!window.confirm(confirmation)) {
            return;
        }

        button.prop("disabled", true).text("Removing...");
        resultBox
            .removeClass("alert-danger alert-info alert-success")
            .addClass("alert-info")
            .text("Removing data source, recalculating links and summaries, and saving a new revision. This can take a few seconds on large data sets...")
            .show();

        $.ajax({
            url: removeUrl,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ source: source })
        }).done(function (result) {
            resultBox
                .removeClass("alert-info alert-danger")
                .addClass("alert-success")
                .text(result.message || "Data source removed and new revision saved.");
            window.setTimeout(function () {
                window.location.reload();
            }, 900);
        }).fail(function (xhr) {
            var message = "Could not remove that data source.";
            if (xhr.responseJSON && xhr.responseJSON.error) {
                message += " " + xhr.responseJSON.error;
            }
            resultBox
                .removeClass("alert-info alert-success")
                .addClass("alert-danger")
                .text(message)
                .show();
            button.prop("disabled", false).text("Remove from Current Data");
        });
    });
});

// Holdings & Accounting
$(document).ready(function() {
    if ($('#eh_stats_datatable').length == 0) {
        return;
    }

    var holdingsDifferenceYearlyTable = null;
    var holdingsDifferenceTransactionsTable = null;
    var holdingsClassificationReviewTable = null;
    var holdingsCurrentBreakdown = null;

    function holdingsParseQuantity(value) {
        if (value === undefined || value === null || value === 'N/A') {
            return null;
        }

        var parsed = gainzParseDisplayNumber(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function holdingsFormatQuantity(value) {
        if (value === null || value === undefined || !Number.isFinite(value)) {
            return '--';
        }

        return value.toFixed(8).replace(/0+$/, '').replace(/\.$/, '') || '0';
    }

    function holdingsStatusClass(status) {
        return 'status-' + String(status || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    }

    function holdingsSetBadge(status) {
        var badge = $('#holdings_status_badge');
        var className = holdingsStatusClass(status);
        badge
            .removeClass('status-matched status-verified status-needs-declared-holdings status-mismatch status-needs-review status-unlinked-sales status-needs-user-research')
            .addClass(className)
            .text(status);
    }

    function holdingsSetSummary(summary) {
        if (!summary) {
            return;
        }

        $('#holdings_summary_asset_count').text(summary.asset_count);
        $('#holdings_summary_need_holdings').text(summary.assets_needing_holdings);
        $('#holdings_summary_matched').text(summary.assets_matched);
        $('#holdings_summary_mismatch').text(summary.assets_with_mismatch);
    }

    function holdingsRowStatus(rowData) {
        if (!rowData) {
            return 'unknown';
        }

        var buys = holdingsParseQuantity(rowData[1]) || 0;
        var sells = holdingsParseQuantity(rowData[2]) || 0;
        var soldUnlinked = holdingsParseQuantity(rowData[3]) || 0;
        var holdings = holdingsParseQuantity(rowData[8]);

        if (holdings === null) {
            return 'needs';
        }

        if (soldUnlinked > 0.00000001) {
            return 'unlinked';
        }

        if (Math.abs((buys - sells) - holdings) <= 0.00000001) {
            return 'matched';
        }

        return 'mismatch';
    }

    function holdingsRowsSet(rows) {
        if (!rows) {
            return;
        }

        table.clear();
        table.rows.add(rows).draw();
    }

    function holdingsSelectedAssetRow() {
        return table.row({selected:true}).data();
    }

    function holdingsSelectAsset(asset) {
        var selectedRow = null;
        table.rows().deselect();
        table.rows(function(index, rowData) {
            if (rowData && rowData[0] == asset) {
                selectedRow = rowData;
                return true;
            }
            return false;
        }).select();

        return selectedRow;
    }

    function holdingsScrollTo(selector) {
        var target = $(selector);
        if (target.length == 0) {
            return;
        }

        $('html, body').animate({
            scrollTop: Math.max(target.offset().top - 90, 0)
        }, 250);
    }

    function holdingsHideSendDisposalRecommendation() {
        $('#holdings_send_disposal_recommendation').hide();
        $('#holdings_send_disposal_text').text('');
    }

    function holdingsRenderSendDisposalRecommendation(summary) {
        var asset = summary.asset || (holdingsSelectedAssetRow() || [])[0] || '';
        var recommendedQuantity = holdingsParseQuantity(summary.recommended_disposal_quantity);
        var sendQuantity = holdingsParseQuantity(summary.send_quantity);
        var difference = holdingsParseQuantity(summary.difference);

        if (!summary.has_send_disposal_recommendation || !recommendedQuantity || recommendedQuantity <= 0) {
            holdingsHideSendDisposalRecommendation();
            return;
        }

        $('#convert_quantity').val(holdingsFormatQuantity(recommendedQuantity));
        $('#holdings_send_disposal_text').text(
            'Gainz found a ' + holdingsFormatQuantity(difference) + ' ' + asset +
            ' review difference and ' + holdingsFormatQuantity(sendQuantity) +
            ' ' + asset + ' of imported sends. If source records show ' +
            holdingsFormatQuantity(recommendedQuantity) +
            ' left your ownership or was sent elsewhere and traded/sold, classify that documented quantity as disposals and run FIFO. Owner transfers should remain transfers.'
        );
        $('#holdings_send_disposal_recommendation').show();
    }

    function holdingsClearDifferenceBreakdown() {
        holdingsCurrentBreakdown = null;
        $('#holdings_difference_breakdown').hide();
        $('#holdings_difference_formula').text('Select an asset to see how the difference was calculated.');
        $('#holdings_difference_declared_formula, #holdings_difference_transfer_formula, #holdings_difference_interpretation').text('');
        $('#holdings_difference_transaction_count').text('0 transactions');
        $('#holdings_breakdown_buys, #holdings_breakdown_sells, #holdings_breakdown_sends, #holdings_breakdown_receives, #holdings_breakdown_imported_net').text('--');
        holdingsHideSendDisposalRecommendation();

        if (holdingsClassificationReviewTable) {
            holdingsClassificationReviewTable.clear().draw();
        }

        if (holdingsDifferenceYearlyTable) {
            holdingsDifferenceYearlyTable.clear().draw();
        }

        if (holdingsDifferenceTransactionsTable) {
            holdingsDifferenceTransactionsTable.clear().draw();
        }
    }

    function holdingsShowDifferenceLoading(rowData) {
        holdingsCurrentBreakdown = null;
        $('#holdings_difference_breakdown').show();
        $('#holdings_difference_formula').text('Loading ' + rowData[0] + ' timeline...');
        $('#holdings_difference_declared_formula, #holdings_difference_transfer_formula, #holdings_difference_interpretation').text('');
        $('#holdings_difference_transaction_count').text('Loading');
        $('#holdings_breakdown_buys, #holdings_breakdown_sells, #holdings_breakdown_sends, #holdings_breakdown_receives, #holdings_breakdown_imported_net').text('--');
        holdingsHideSendDisposalRecommendation();

        if (holdingsClassificationReviewTable) {
            holdingsClassificationReviewTable.clear().draw();
        }

        if (holdingsDifferenceYearlyTable) {
            holdingsDifferenceYearlyTable.clear().draw();
        }

        if (holdingsDifferenceTransactionsTable) {
            holdingsDifferenceTransactionsTable.clear().draw();
        }
    }

    function holdingsRenderDifferenceBreakdown(data) {
        holdingsCurrentBreakdown = data || null;
        var summary = data && data.summary ? data.summary : {};
        var transactionCount = summary.transaction_count || 0;

        $('#holdings_difference_breakdown').show();
        $('#holdings_difference_formula').text(summary.expected_formula || 'No activity found for this asset.');
        $('#holdings_difference_declared_formula').text(summary.difference_formula || '');
        $('#holdings_difference_transfer_formula').text(summary.transfer_formula || '');
        $('#holdings_difference_interpretation').text(summary.interpretation || '');
        $('#holdings_breakdown_buys').text(summary.buy_quantity || '--');
        $('#holdings_breakdown_sells').text(summary.sell_quantity || '--');
        $('#holdings_breakdown_sends').text(summary.send_quantity || '--');
        $('#holdings_breakdown_receives').text(summary.receive_quantity || '--');
        $('#holdings_breakdown_imported_net').text(summary.imported_net || '--');
        $('#holdings_difference_transaction_count')
            .removeClass('status-matched status-verified status-needs-declared-holdings status-mismatch status-needs-review status-unlinked-sales status-needs-user-research')
            .addClass(holdingsStatusClass(summary.status))
            .text(transactionCount + ' transaction' + (transactionCount == 1 ? '' : 's'));
        holdingsRenderSendDisposalRecommendation(summary);

        if (summary.basis_review_status == 'needs_research') {
            $('#basis_review_note').val(summary.basis_review_note || '');
            $('#holdings_save_message')
                .removeClass('alert-success')
                .addClass('alert-warning')
                .text('Missing basis for ' + summary.asset + ' is marked as needs user research. Exports remain draft/not filing-ready until resolved.')
                .show();
        }

        if (holdingsClassificationReviewTable) {
            holdingsClassificationReviewTable.clear();
            holdingsClassificationReviewTable.rows.add(data.classification_rows || []).draw();
        }

        if (holdingsDifferenceYearlyTable) {
            holdingsDifferenceYearlyTable.clear();
            holdingsDifferenceYearlyTable.rows.add(data.yearly_rows || []).draw();
        }

        if (holdingsDifferenceTransactionsTable) {
            holdingsDifferenceTransactionsTable.clear();
            holdingsDifferenceTransactionsTable.rows.add(data.transaction_rows || []).draw();
        }
    }

    function holdingsLoadDifferenceBreakdown(rowData) {
        if (!rowData) {
            holdingsClearDifferenceBreakdown();
            return;
        }

        holdingsShowDifferenceLoading(rowData);

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/difference_breakdown",
            data: JSON.stringify({
                'asset': rowData
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                holdingsRenderDifferenceBreakdown(data);
            },
            error: function () {
                $('#holdings_difference_formula').text('Could not load the transaction timeline for this asset.');
                $('#holdings_difference_transaction_count').text('Error');
            },
        });
    }

    function holdingsSetReadinessBadge(status) {
        $('#holdings_readiness_badge')
            .removeClass('status-matched status-verified status-needs-declared-holdings status-mismatch status-needs-review status-unlinked-sales status-needs-user-research')
            .addClass(holdingsStatusClass(status))
            .text(status);
    }

    function holdingsSetReadinessMessage(message, level) {
        var className = level == 'success' ? 'alert-success' : (level == 'warning' ? 'alert-warning' : 'alert-info');
        $('#holdings_readiness_message')
            .removeClass('alert-info alert-warning alert-success')
            .addClass(className)
            .text(message);
    }

    function holdingsRenderReadiness(rowData, precheckData) {
        if (!rowData) {
            $('#holdings_readiness_asset, #holdings_readiness_holdings, #holdings_readiness_unlinked, #holdings_readiness_difference').text('--');
            $('#holdings_run_fifo_button').prop('disabled', true).text('Run FIFO Auto Link for Selected Asset');
            $('#holdings_leave_basis_unresolved_button').prop('disabled', true);
            holdingsSetReadinessBadge('Select asset');
            holdingsSetReadinessMessage('Select an asset to see the next review step.', 'info');
            return;
        }

        var asset = rowData[0];
        var buys = holdingsParseQuantity(rowData[1]) || 0;
        var sells = holdingsParseQuantity(rowData[2]) || 0;
        var soldUnlinked = holdingsParseQuantity(rowData[3]) || 0;
        var declaredHoldings = holdingsParseQuantity(rowData[8]);
        var expectedHoldings = buys - sells;
        var difference = declaredHoldings === null ? null : expectedHoldings - declaredHoldings;
        var tolerance = 0.00000001;

        $('#holdings_readiness_asset').text(asset);
        $('#holdings_readiness_holdings').text(declaredHoldings === null ? 'Not declared' : holdingsFormatQuantity(declaredHoldings));
        $('#holdings_readiness_unlinked').text(holdingsFormatQuantity(soldUnlinked));
        $('#holdings_readiness_difference').text(difference === null ? '--' : holdingsFormatQuantity(difference));
        $('#holdings_run_fifo_button').prop('disabled', soldUnlinked <= tolerance).text('Run FIFO Auto Link for Selected Asset');
        $('#holdings_leave_basis_unresolved_button').prop('disabled', soldUnlinked <= tolerance);

        if (declaredHoldings === null) {
            holdingsSetReadinessBadge('Needs declared holdings');
            holdingsSetReadinessMessage('Enter the amount of ' + asset + ' you currently hold, then save it before reviewing links or exports.', 'info');
            return;
        }

        if (soldUnlinked > tolerance) {
            holdingsSetReadinessBadge('Unlinked sales');
            holdingsSetReadinessMessage(asset + ' has sales without complete basis links. Run FIFO Auto Link for this asset or review links manually before using generated reports.', 'warning');
            return;
        }

        if (difference !== null && Math.abs(difference) > tolerance) {
            holdingsSetReadinessBadge('Needs Review');
            if (difference > 0) {
                holdingsSetReadinessMessage('Imported buys and sells imply more ' + asset + ' than declared. Review the timeline for missing disposals, sends, losses, or other records before using generated reports.', 'warning');
            } else {
                holdingsSetReadinessMessage('Declared holdings are higher than imported buys and sells explain. Review missing acquisitions, income, gifts, transfers, or external records before using generated reports.', 'warning');
            }
            return;
        }

        holdingsSetReadinessBadge('Verified');
        holdingsSetReadinessMessage(asset + ' has declared holdings, no unlinked sales, and no quantity difference in Gainz. Review supporting reports on Stats & Charts, then Export when ready.', 'success');
    }

    function holdingsLoadPrecheck(rowData) {
        var precheckTable = $('#auto_actions_datatable').DataTable();

        if (!rowData) {
            precheckTable.clear().draw();
            holdingsRenderReadiness(null, null);
            return;
        }

        precheckTable.clear().draw();

        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_pre_check",
            data: JSON.stringify({
                'row_data': rowData
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                precheckTable.clear();
                precheckTable.rows.add(data['auto_suggestions'] || []).draw();
                holdingsRenderReadiness(rowData, data);
            },
            error: function () {
                holdingsRenderReadiness(rowData, null);
            },
        });
    }

    function holdingsLoadRow(rowData) {
        $('#holdings_save_message').hide().text('');
        holdingsRenderSelection(rowData);

        if (!rowData) {
            $('#auto_actions_datatable').DataTable().clear().draw();
            holdingsClearDifferenceBreakdown();
            holdingsRenderReadiness(null, null);
            return;
        }

        holdingsRenderReadiness(rowData, null);
        holdingsLoadDifferenceBreakdown(rowData);
        holdingsLoadPrecheck(rowData);
    }

    function holdingsRenderSelection(rowData) {
        if (!rowData) {
            $('#holdings_workbench_title').text('Step 3 Asset Workbench');
            $('#holdings_selected_asset').text('Select an asset above to begin.');
            $('#holdings_expected_from_activity, #holdings_declared_current, #holdings_difference, #holdings_unlinked_sales').text('--');
            $('#holdings_next_action').text('Pick an asset to see the next action.');
            $('#holdings_quantity').attr('placeholder', 'Select an asset first').val('');
            $('#convert_quantity').attr('placeholder', 'Quantity to resolve').val('');
            holdingsSetBadge('Needs asset');
            holdingsClearDifferenceBreakdown();
            return;
        }

        var asset = rowData[0];
        var buys = holdingsParseQuantity(rowData[1]) || 0;
        var sells = holdingsParseQuantity(rowData[2]) || 0;
        var soldUnlinked = holdingsParseQuantity(rowData[3]) || 0;
        var holdings = holdingsParseQuantity(rowData[8]);
        var expectedHoldings = buys - sells;

        $('#holdings_workbench_title').text('Step 3 ' + asset + ' Workbench');
        $('#holdings_selected_asset').text(asset + ' selected');
        $('#holdings_expected_from_activity').text(holdingsFormatQuantity(expectedHoldings));
        $('#holdings_unlinked_sales').text(holdingsFormatQuantity(soldUnlinked));
        $('#holdings_quantity').attr('placeholder', 'Current holding for ' + asset);
        $('#convert_quantity').attr('placeholder', 'Quantity to classify for ' + asset);
        $('#convert_text').text('Use these tools only when supported by source records. If you know the missing transaction, adding the actual transaction is preferable to automatic classification. Owner transfers should stay as transfers.');

        if (holdings === null) {
            $('#holdings_declared_current').text('--');
            $('#holdings_difference').text('--');
            $('#holdings_quantity').val('');
            $('#convert_quantity').val('');
            $('#holdings_next_action').text('Enter the amount of ' + asset + ' you want Gainz to use for reconciliation. Keep source records for the amount entered.');
            holdingsSetBadge('Needs declared holdings');
            return;
        }

        var difference = expectedHoldings - holdings;
        $('#holdings_declared_current').text(holdingsFormatQuantity(holdings));
        $('#holdings_difference').text(holdingsFormatQuantity(difference));
        $('#holdings_quantity').val(holdingsFormatQuantity(holdings));

        if (Math.abs(difference) <= 0.00000001 && soldUnlinked <= 0.00000001) {
            $('#holdings_next_action').text(asset + ' has no quantity difference from imported buys and sells. Review source records, lots, and basis links before using generated reports.');
            holdingsSetBadge('Verified');
        } else if (soldUnlinked > 0.00000001) {
            $('#holdings_next_action').text(asset + ' still has unlinked sales. Run Auto Link or manually review links before using generated reports.');
            holdingsSetBadge('Unlinked sales');
        } else if (difference > 0) {
            $('#holdings_next_action').text('The calculated net from imported buys and sells is higher than declared ' + asset + '. Review source records for missing disposals, transfers, losses, or other activity before using generated reports.');
            $('#convert_quantity').val(holdingsFormatQuantity(difference));
            $('#convert_text').text('If source records show selected sends left your ownership or were sent elsewhere and traded/sold, classify only the documented quantity as disposals. Owner transfers should stay as transfers.');
            holdingsSetBadge('Needs Review');
        } else {
            $('#holdings_next_action').text('Declared holdings are higher than imported buys and sells currently explain. Review missing acquisitions, income, gifts, transfers, or other records that may need basis support.');
            $('#convert_quantity').val('');
            holdingsSetBadge('Needs Review');
        }
    }

    $('#auto_actions_datatable').DataTable({
        "pageLength": 25,
        "order": [[ 1, "desc" ]],
        "columnDefs": [
            { "width": "5%", "targets": 0 },
            { "width": "20%", "targets": 2},
            {
                "targets": 2,
                "render": function(data, type) {
                    if (type !== 'display') {
                        return data;
                    }

                    var status = String(data || '');
                    var className = status.toLowerCase() == 'passed' || status.toLowerCase() == 'complete'
                        ? 'status-verified'
                        : 'status-needs-review';

                    return '<span class="gainz-status-badge ' + className + '">' + status + '</span>';
                }
            },
            // {
            //     "targets": [ 3,4 ],
            //     "visible": false,
            //     "searchable": false
            // },
          ],
        select: {
            style: 'multiple'
        },
    });

    holdingsDifferenceYearlyTable = $('#holdings_difference_yearly_datatable').DataTable({
        "pageLength": 10,
        "order": [[ 0, "asc" ]],
    });

    holdingsClassificationReviewTable = $('#holdings_classification_review_datatable').DataTable({
        "pageLength": 10,
        "order": [[ 0, "asc" ]],
        "columnDefs": [
            {
                "targets": 5,
                "render": function(data, type) {
                    if (type !== 'display') {
                        return data;
                    }

                    var status = String(data || '');
                    var className = status.toLowerCase().indexOf('possible') >= 0
                        ? 'status-unlinked-sales'
                        : 'status-needs-review';

                    return '<span class="gainz-status-badge ' + className + '">' + status + '</span>';
                }
            }
        ],
    });

    holdingsDifferenceTransactionsTable = $('#holdings_difference_transactions_datatable').DataTable({
        "pageLength": 25,
        "order": [[ 0, "asc" ]],
    });

    var activeHoldingsFilter = 'all';

    var table = $('#eh_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $.fn.dataTable.ext.search.push(function(settings, rowData) {
        if (settings.nTable.id !== 'eh_stats_datatable') {
            return true;
        }

        if (activeHoldingsFilter == 'all') {
            return true;
        }

        return holdingsRowStatus(rowData) == activeHoldingsFilter;
    });

    function holdingsApplySummaryFilter(filterName, options) {
        options = options || {};
        activeHoldingsFilter = filterName || 'all';
        $('.holdings-progress-action')
            .removeClass('active')
            .attr('aria-pressed', 'false');
        $('.holdings-progress-action[data-holdings-filter="' + activeHoldingsFilter + '"]')
            .addClass('active')
            .attr('aria-pressed', 'true');

        table.search('').draw();

        var labels = {
            all: {
                message: 'Showing all assets. Select any row to declare holdings or review the current next action.',
                scroll: '#eh_stats_datatable'
            },
            needs: {
                message: 'Showing assets that still need declared holdings. Select one, enter what you currently hold, then save.',
                scroll: '#eh_stats_datatable'
            },
            matched: {
                message: 'Showing verified assets. These have no quantity difference in Gainz. Use Stats & Charts or Export to review the supporting reports.',
                scroll: '#eh_stats_datatable'
            },
            mismatch: {
                message: 'Showing assets that need review because declared holdings and imported buys/sells differ. Select one to review possible missing records or unsupported classifications.',
                scroll: '#eh_stats_datatable'
            }
        };
        var label = labels[activeHoldingsFilter] || labels.all;
        var visibleRows = table.rows({ filter: 'applied' }).data();

        $('#holdings_summary_action').text(
            label.message + ' ' + visibleRows.length + ' asset' + (visibleRows.length == 1 ? '' : 's') + ' shown.'
        );

        if (visibleRows.length > 0 && activeHoldingsFilter != 'all') {
            table.rows().deselect();
            var firstVisibleRow = visibleRows[0];
            table.rows(function(index, rowData) {
                return rowData && firstVisibleRow && rowData[0] == firstVisibleRow[0];
            }).select();
            holdingsLoadRow(firstVisibleRow);
            if (!options.skipScroll) {
                holdingsScrollTo('#holdings_selected_asset');
            }
        } else {
            table.rows().deselect();
            holdingsLoadRow(null);
            if (!options.skipScroll) {
                holdingsScrollTo(label.scroll);
            }
        }
    }

    $('.holdings-progress-action').on('click', function() {
        holdingsApplySummaryFilter($(this).data('holdings-filter'));
    });

    $('#eh_stats_datatable tbody').on( 'click', 'tr', function () {
        holdingsLoadRow(table.row(this).data());
    });

    holdingsApplySummaryFilter('all', { skipScroll: true });

    function holdingsRefreshBulkButtonText() {
        var asset = String($('#bulk_primary_asset').val() || 'BTC').trim().toUpperCase() || 'BTC';
        $('#bulk_primary_asset').val(asset);
        $('#bulk_set_non_primary_zero_button').text('Set All Non-' + asset + ' Assets To 0');
    }

    $('#bulk_primary_asset').on('input blur', holdingsRefreshBulkButtonText);
    holdingsRefreshBulkButtonText();

    $('#bulk_set_non_primary_zero_button').click(function() {
        var button = $(this);
        var primaryAsset = String($('#bulk_primary_asset').val() || 'BTC').trim().toUpperCase() || 'BTC';
        var primaryQuantity = $('#bulk_primary_quantity').val();

        if (!primaryQuantity && primaryQuantity !== '0') {
            alert('Enter the current holdings quantity for ' + primaryAsset + '.');
            return;
        }

        if (!window.confirm('Save current holdings as ' + primaryAsset + ' ' + primaryQuantity + ' and set every other tracked asset to 0?')) {
            return;
        }

        var startedAt = Date.now();
        button.prop('disabled', true).text('Saving revision...');
        $('#bulk_holdings_message')
            .removeClass('alert-success alert-warning')
            .addClass('alert-info')
            .text('Saving current holdings, recalculating reconciliation, and writing a new revision. Large data sets may take 10-30 seconds; keep this tab open.')
            .show();

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/bulk_holdings",
            data: JSON.stringify({
                'primary_asset': primaryAsset,
                'primary_quantity': primaryQuantity
            }),
            dataType: "json",
            contentType: 'application/json',
            success: function(data) {
                holdingsRowsSet(data['stats_table_rows']);
                holdingsSetSummary(data['holdings_summary']);
                var updatedRow = holdingsSelectAsset(primaryAsset);
                holdingsLoadRow(updatedRow);
                $('#bulk_holdings_message')
                    .removeClass('alert-info alert-warning')
                    .addClass('alert-success')
                    .text(data['message'] + ' Confirmation: ' + primaryAsset + ' ' + data['primary_quantity'] + ', all others 0. Completed in ' + Math.max(1, Math.round((Date.now() - startedAt) / 1000)) + ' second(s).')
                    .show();
                holdingsScrollTo('#bulk_holdings_message');
            },
            error: function(xhr) {
                var message = 'Bulk holdings could not be saved.';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    message = xhr.responseJSON.message;
                }
                $('#bulk_holdings_message')
                    .removeClass('alert-info alert-success')
                    .addClass('alert-warning')
                    .text(message)
                    .show();
            },
            complete: function() {
                holdingsRefreshBulkButtonText();
                button.prop('disabled', false);
            },
        });
    });

    $("#auto_action_button").click(function(){

        var table_data = $('#auto_actions_datatable').DataTable().rows( {selected:true} ).data()

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/auto_actions",
            data: JSON.stringify({
                'table_data': $('#auto_actions_datatable').DataTable().rows( {selected:true} ).data(),
                'asset': $('#add_transactions_stats_datatable').DataTable().row( {selected:true} ).data(),
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                // console.log(data)
                for (var i = 0; i < data.length; i++) {

                    showSwal('warning-message-and-confirmation', 'Creating Sell' + data[i]['quantity'], 'Use ')

                }

            },
        });
    });


    $("#submit_holdings_button").click(function(){
        var rowData = holdingsSelectedAssetRow();
        var quantity = $('#holdings_quantity').val();
        var saveButton = $(this);

        if (!rowData) {
            alert("Select an asset first.");
            return;
        }

        if (!quantity) {
            alert("Enter the current holdings quantity first.");
            return;
        }

        $('#holdings_save_message').hide().text('');
        saveButton.prop('disabled', true).text('Saving...');

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/holdings_info",
            data: JSON.stringify({
                'quantity': quantity,
                'asset': rowData
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                holdingsRowsSet(data['stats_table_rows']);
                holdingsSetSummary(data['holdings_summary']);
                var updatedRow = null;
                var rows = table.rows().data();
                for (var i = 0; i < rows.length; i++) {
                    if (rows[i] && rows[i][0] == rowData[0]) {
                        updatedRow = rows[i];
                        break;
                    }
                }

                if (updatedRow) {
                    table.rows(function(index, data) {
                        return data && data[0] == updatedRow[0];
                    }).select();
                }

                holdingsRenderSelection(updatedRow || rowData);
                holdingsLoadDifferenceBreakdown(updatedRow || rowData);
                holdingsLoadPrecheck(updatedRow || rowData);
                $('#holdings_quantity').focus().select();
                $('#holdings_save_message')
                    .removeClass('alert-warning')
                    .addClass('alert-success')
                    .text(data['message'] || 'Declared holdings saved.')
                    .show();
            },
            error: function () {
                alert("Declared holdings could not be saved. Please try again.");
            },
            complete: function () {
                saveButton.prop('disabled', false).text('Save Declared Holdings');
            },
        });
    });

    $("#zero_holdings_button").click(function(){
        var rowData = holdingsSelectedAssetRow();

        if (!rowData) {
            alert("Select an asset first.");
            return;
        }

        if (!window.confirm('Save declared holdings of 0 for ' + rowData[0] + '? Use this only when your records show you currently hold none of this asset.')) {
            return;
        }

        $('#holdings_quantity').val('0');
        $('#submit_holdings_button').trigger('click');
    });

    $("#holdings_run_fifo_button").click(function(){
        var rowData = holdingsSelectedAssetRow();
        var button = $(this);
        var asset = rowData ? rowData[0] : null;

        if (!rowData) {
            holdingsSetReadinessMessage('Select an asset before running FIFO Auto Link.', 'warning');
            return;
        }

        if (!window.confirm('Run FIFO Auto Link for ' + asset + '? Gainz will create basis links for review and save a new revision if links are added.')) {
            return;
        }

        var startedAt = Date.now();
        button.prop('disabled', true).text('Linking and saving...');
        holdingsSetReadinessMessage('Running FIFO Auto Link for ' + asset + ', recalculating basis links, and saving a revision. This can take 10-30 seconds on large data sets; keep this tab open.', 'info');

        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_asset",
            data: JSON.stringify({
                'algo': 'fifo',
                'asset': rowData,
                'year': 'All Time'
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                holdingsSetReadinessMessage((data || 'FIFO Auto Link complete.') + ' Completed in ' + Math.max(1, Math.round((Date.now() - startedAt) / 1000)) + ' second(s). Refreshing review data...', 'success');
                window.setTimeout(function () {
                    location.reload();
                }, 900);
            },
            error: function () {
                holdingsSetReadinessMessage('FIFO Auto Link could not run. Review source records or use Auto Link manually.', 'warning');
                button.prop('disabled', false).text('Run FIFO Auto Link for Selected Asset');
            },
        });
    });

    function holdingsLeaveBasisUnresolved() {
        var rowData = holdingsSelectedAssetRow();
        var asset = rowData ? rowData[0] : null;
        var note = $('#basis_review_note').val();

        if (!rowData) {
            alert('Select an asset first.');
            return;
        }

        if (!window.confirm('Leave missing basis for ' + asset + ' unresolved as needs user research? Generated exports will remain draft/not filing-ready.')) {
            return;
        }

        $('#leave_basis_unresolved_button, #holdings_leave_basis_unresolved_button').prop('disabled', true).text('Saving...');
        $.ajax({
            type: "POST",
            url: "/holdings_accounting/leave_basis_unresolved",
            data: JSON.stringify({
                'asset': rowData,
                'note': note
            }),
            dataType: "json",
            contentType: 'application/json',
            success: function(data) {
                holdingsRowsSet(data['stats_table_rows']);
                holdingsSetSummary(data['holdings_summary']);
                var updatedRow = holdingsSelectAsset(asset);
                holdingsRenderSelection(updatedRow || rowData);
                holdingsRenderDifferenceBreakdown(data['difference_breakdown']);
                holdingsLoadPrecheck(updatedRow || rowData);
                $('#holdings_save_message')
                    .removeClass('alert-success')
                    .addClass('alert-warning')
                    .text(data['message'] || (asset + ' left unresolved as needs user research.'))
                    .show();
                holdingsScrollTo('#holdings_save_message');
            },
            error: function(xhr) {
                var message = 'Basis review status could not be saved.';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    message = xhr.responseJSON.message;
                }
                alert(message);
            },
            complete: function() {
                $('#leave_basis_unresolved_button').prop('disabled', false).text('Leave Unresolved / Needs Research');
                $('#holdings_leave_basis_unresolved_button').text('Leave Missing Basis As Needs Research');
                holdingsRenderReadiness();
            },
        });
    }

    $('#leave_basis_unresolved_button, #holdings_leave_basis_unresolved_button').click(function() {
        holdingsLeaveBasisUnresolved();
    });

    function holdingsClassifyDocumentedSends() {
        var rowData = holdingsSelectedAssetRow();
        var quantity = $('#convert_quantity').val();
        var asset = rowData ? rowData[0] : null;

        if (!rowData) {
            alert("Select an asset first.");
            return;
        }

        if (!quantity || (holdingsParseQuantity(quantity) || 0) <= 0) {
            alert("Enter the documented send quantity to classify.");
            return;
        }

        if (!window.confirm('Classify ' + quantity + ' ' + asset + ' of documented sends as disposals and run FIFO Auto Link? Owner transfers should remain transfers.')) {
            return;
        }

        $('#sends_to_sells_button, #classify_sends_fifo_button').prop('disabled', true).text('Classifying...');
        $('#holdings_save_message').hide().text('');

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/sends_to_sells",
            data: JSON.stringify({
                'quantity': quantity,
                'asset': rowData,
                'auto_link': true
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                holdingsRowsSet(data['stats_table_rows']);
                holdingsSetSummary(data['holdings_summary']);

                var updatedRow = holdingsSelectAsset(asset);
                holdingsRenderSelection(updatedRow || rowData);
                holdingsRenderDifferenceBreakdown(data['difference_breakdown']);
                holdingsLoadPrecheck(updatedRow || rowData);

                var message = data['message'] || 'Documented sends classified for review.';
                if (data['auto_link_failures'] && data['auto_link_failures'].length > 0) {
                    message += ' Remaining basis review: ' + data['auto_link_failures'].map(function(failure) {
                        return failure.asset + ' ' + failure.unlinked_quantity + ' unlinked';
                    }).join('; ') + '.';
                    $('#holdings_save_message')
                        .removeClass('alert-success')
                        .addClass('alert-warning');
                } else {
                    $('#holdings_save_message')
                        .removeClass('alert-warning')
                        .addClass('alert-success');
                }
                $('#holdings_save_message').text(message).show();
                holdingsScrollTo('#holdings_save_message');
            },
            error: function (xhr) {
                var message = 'Documented sends could not be classified. Review the selected asset and quantity, then try again.';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    message = xhr.responseJSON.message;
                }
                alert(message);
            },
            complete: function () {
                $('#sends_to_sells_button').prop('disabled', false).text('Classify Documented Sends as Disposals');
                $('#classify_sends_fifo_button').prop('disabled', false).text('Classify Documented Sends And Run FIFO');
            },
        });
    }

    $("#sends_to_sells_button, #classify_sends_fifo_button").click(function(){
        holdingsClassifyDocumentedSends();
    });

    $("#receives_to_buys_button").click(function(){

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/receive_to_buy",
            data: JSON.stringify({
                'quantity': $('#convert_quantity').val(),
                'asset': $('#eh_stats_datatable').DataTable().row( {selected:true} ).data()
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                location.reload()
            },
        });
    });

    $("#buys_to_lost_button").click(function(){

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/buys_to_lost",
            data: JSON.stringify({
                'quantity': $('#convert_quantity').val(),
                'asset': $('#eh_stats_datatable').DataTable().row( {selected:true} ).data()
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                location.reload()
            },
        });
    });

});


// Auto Link Page
$(document).ready(function() {
    if ($('#al_stats_datatable').length == 0) {
        return;
    }

    var table = $('#al_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    function autoLinkShowResult(message, isError) {
        $('#auto_link_all_result')
            .removeClass('text-muted text-danger text-success')
            .addClass(isError ? 'text-danger' : 'text-success')
            .text(message);
    }

    function selectedAutoLinkAsset() {
        return table.row({selected:true}).data();
    }

    function runSelectedAutoLink(algo) {
        var selectedAsset = selectedAutoLinkAsset();

        if (!selectedAsset) {
            autoLinkShowResult('Select an asset row before running that method.', true);
            return;
        }

        autoLinkShowResult('Running ' + algo.replace(/_/g, ' ').toUpperCase() + ' Auto Link for ' + selectedAsset[0] + ', recalculating basis links, and saving a revision. Keep this tab open.', false);

        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_asset",
            data: JSON.stringify({
                'algo': algo,
                'asset': selectedAsset,
                'year': $('#auto_link_year_dropdown').find(":selected").val()
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                autoLinkShowResult(data || 'Auto Link complete. Review generated links before using reports.', false);
                window.setTimeout(function () {
                    location.reload();
                }, 800);
            },
            error: function () {
                autoLinkShowResult('Auto Link could not run. Review the selected asset and try again.', true);
            },
        });
    }

    $("#auto_link_all_fifo").click(function(){
        var button = $(this);
        var originalText = button.text();
        var endpoint = button.data('url') || "/auto_link/auto_link_all_fifo";
        var startedAt = Date.now();

        autoLinkShowResult('Running FIFO Auto Link across assets with unlinked sales, recalculating basis links, and saving a revision. Large data sets may take 10-30 seconds; keep this tab open.', false);
        button.prop('disabled', true).text('Linking and saving...');

        $.ajax({
            type: "POST",
            url: endpoint,
            data: JSON.stringify({
                'year': $('#auto_link_year_dropdown').find(":selected").val()
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                var message = data && data.message ? data.message : 'FIFO Auto Link complete. Review generated links before using reports.';
                message += ' Completed in ' + Math.max(1, Math.round((Date.now() - startedAt) / 1000)) + ' second(s).';
                autoLinkShowResult(message, false);
                window.setTimeout(function () {
                    location.reload();
                }, 1000);
            },
            error: function () {
                autoLinkShowResult('FIFO Auto Link could not run. Review imports and basis lots, then try again.', true);
            },
            complete: function () {
                button.prop('disabled', false).text(originalText);
            },
        });
    });


    // $('#al_stats_datatable tbody').on( 'click', 'tr', function () {


    //     $.ajax({
    //         type: "POST",
    //         url: "/auto_link/auto_link_pre_check",
    //         data: JSON.stringify({
    //             'row_data': table.row( this ).data()
    //           }),

    //         contentType: 'application/json',
    //         success: function (data) {
    //             console.log(data)

    //             $('#al_options').html(data['message'])

    //         },
    //     });

    // } );

    $("#min_gain_long").click(function(){
        runSelectedAutoLink('min_gain_long');
    });

    $("#min_gain").click(function(){
        runSelectedAutoLink('min_gain');
    });

    $("#link_w_fifo").click(function(){
        runSelectedAutoLink('fifo');
    });

    $("#link_w_filo").click(function(){
        runSelectedAutoLink('filo');
    });



} );


// stats page code
$(document).ready(function() {

    function setStatsReconciliationWarning(status) {
        if (status && status.message) {
            $('#stats_reconciliation_warning_text').text(status.message);
            $('#stats_reconciliation_warning').show();
        } else {
            $('#stats_reconciliation_warning').hide();
        }
    }

    function setStatsImportWarnings(warnings, warningRows) {
        gainzSetImportWarningWorkflow(
            "#stats_import_warnings",
            "#stats_import_warnings_table",
            warnings,
            warningRows
        );
    }

    function statusClassName(status) {
        var normalizedStatus = String(status || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        return 'status-' + normalizedStatus;
    }

    function statusBadgeHtml(status) {
        if (!status) {
            return '';
        }

        return '<span class="gainz-status-badge ' + statusClassName(status) + '">' + status + '</span>';
    }

    function setStatsSummary(summary) {
        if (!summary) {
            return;
        }

        $('#stats_summary_reconciliation')
            .text(summary.reconciliation)
            .removeClass('status-matched status-verified status-needs-declared-holdings status-mismatch status-needs-review status-unlinked-sales')
            .addClass(summary.reconciliation_class || statusClassName(summary.reconciliation));
        $('#stats_summary_assets_needing_holdings').text(summary.assets_needing_holdings);
        $('#stats_summary_assets_with_mismatches').text(summary.assets_with_mismatches);
        $('#stats_summary_import_warnings').text(summary.import_warnings);
        $('#stats_summary_unlinked_sales').text(summary.unlinked_sales);
        setStatsAutoFixPanel(summary);
    }

    function setStatsAutoFixPanel(summary) {
        if (summary && Number(summary.unlinked_sales || 0) > 0) {
            $('#stats_auto_fix_panel').show();
        } else {
            $('#stats_auto_fix_panel').hide();
        }
    }

    function setAllHoldingsReconciliation(rows) {
        if (!$.fn.DataTable.isDataTable('#statspage_all_holdings_reconciliation_datatable')) {
            return;
        }

        $('#statspage_all_holdings_reconciliation_datatable').DataTable().clear();
        $('#statspage_all_holdings_reconciliation_datatable').DataTable().rows.add(rows || []).draw();
    }

    var formatter = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    });

    var myChart = null;
    var selectedStatsRowData = null;
    var activeStatsAssetFilter = 'all';

    function chartCurrency(value) {
        return formatter.format(Number(value || 0));
    }

    function statsParseQuantity(value) {
        if (value === undefined || value === null || value === 'N/A') {
            return null;
        }

        var parsed = gainzParseDisplayNumber(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function statsRegexEscape(value) {
        return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function resetGainzChart(message) {
        if (myChart != null) {
            myChart.destroy();
            myChart = null;
        }

        $('#gainz_chart_subtitle').text('Select an asset');
        $('#gainz_chart_empty_state').text(message || 'Select an asset to view current-lot unrealized gain or loss.').show();
    }

    function renderGainzChart(returnData, selectedAsset) {
        var chartData = returnData['unrealized_chart_data'] || [];
        var currentSpot = Number(returnData['chart_current_usd_spot'] || 0);
        var canvas = document.getElementById("gainzChart");

        if (myChart != null) {
            myChart.destroy();
            myChart = null;
        }

        if (currentSpot > 0) {
            $('#stats_usd_spot').val(currentSpot.toFixed(2));
            $('#gainz_chart_subtitle').text(selectedAsset + ' at ' + chartCurrency(currentSpot) + ' USD spot');
        } else {
            $('#gainz_chart_subtitle').text(selectedAsset);
        }

        if (!canvas || chartData.length == 0) {
            $('#gainz_chart_empty_state').text('No current lots are available for this asset.').show();
            return;
        }

        if (typeof Chart === 'undefined') {
            $('#gainz_chart_empty_state').text('Chart library did not load.').show();
            return;
        }

        $('#gainz_chart_empty_state').hide();

        var ctx = canvas.getContext("2d");
        var pointColors = chartData.map(function(point) {
            return Number(point.y) >= 0 ? "#2dce89" : "#f5365c";
        });

        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: "Unrealized Gain/Loss",
                    borderColor: "#1f8ef1",
                    backgroundColor: "rgba(31, 142, 241, 0.08)",
                    pointBackgroundColor: pointColors,
                    pointBorderColor: pointColors,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    borderWidth: 2,
                    data: chartData
                }]
            },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                elements: {
                    line: {
                        tension: 0.08
                    }
                },
                legend: {
                    display: false
                },
                tooltips: {
                    callbacks: {
                        label: function(tooltipItem, data) {
                            var point = data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index];
                            return [
                                "Gain/Loss: " + point.gain_loss,
                                "Quantity: " + point.quantity,
                                "USD Spot: " + point.usd_spot,
                                "Cost Basis: " + point.cost_basis,
                                "Current Value: " + point.current_value
                            ];
                        }
                    }
                },
                scales: {
                    xAxes: [{
                        type: "time",
                        distribution: "series",
                        time: {
                            unit: 'month',
                            tooltipFormat: 'll'
                        },
                        scaleLabel: {
                            display: true,
                            labelString: 'Date Acquired'
                        }
                    }],
                    yAxes: [{
                        ticks: {
                            beginAtZero: false,
                            callback: function(value) {
                                return chartCurrency(value);
                            }
                        },
                        scaleLabel: {
                            display: true,
                            labelString: 'Unrealized Gain/Loss'
                        },
                        gridLines: {
                            drawBorder: false,
                            zeroLineColor: "rgba(0,0,0,0.25)",
                            color: 'rgba(0,0,0,0.05)'
                        }
                    }]
                }
            }
        });
    }

    function loadSelectedStatsAsset(rowData, currentUsdSpot) {
        if (!rowData) {
            resetGainzChart('Select an asset to view current-lot unrealized gain or loss.');
            return;
        }

        selectedStatsRowData = rowData;

        $.ajax({
            type: "POST",
            url: "/stats/selected_asset",
            data: JSON.stringify({
                'row_data': rowData,
                'start_date': $("#start_date").length ? $("#start_date").datetimepicker().val() : '',
                'end_date': $("#end_date").length ? $("#end_date").datetimepicker().val() : '',
                'year': $('#stats_page_year_dropdown').find(":selected").val(),
                'current_usd_spot': currentUsdSpot || ''
            }),
            contentType: 'application/json',
            success: function (return_data) {
                $('#statspage_detailed_datatable').DataTable().clear();
                $('#statspage_detailed_datatable').DataTable().rows.add(return_data['detailed_stats'] || []).draw();

                $('#statspage_sells_datatable').DataTable().clear();
                $('#statspage_sells_datatable').DataTable().rows.add(return_data['sells_table_data'] || return_data['sells'] || []).draw();

                $('#statspage_holdings_reconciliation_datatable').DataTable().clear();
                $('#statspage_holdings_reconciliation_datatable').DataTable().rows.add(return_data['holdings_reconciliation_data'] || []).draw();

                $('#statspage_holdings_lots_datatable').DataTable().clear();
                $('#statspage_holdings_lots_datatable').DataTable().rows.add(return_data['holdings_lot_table_data'] || []).draw();

                var selectedAsset = rowData[0];

                $('#s8949_table').DataTable().clear();
                $('#s8949_table').DataTable().rows.add(return_data['s8949_table_data'] || []).draw();

                $('#l8949_table').DataTable().clear();
                $('#l8949_table').DataTable().rows.add(return_data['l8949_table_data'] || []).draw();

                setStatsReconciliationWarning(return_data['reconciliation_status']);
                setStatsImportWarnings(return_data['import_warnings'], return_data['import_warning_rows']);
                setStatsSummary(return_data['stats_summary']);
                setAllHoldingsReconciliation(return_data['holdings_reconciliation_table_data']);
                $('#collapse_sales, #collapse_8949_long, #collapse_8949_short').collapse('show');
                renderGainzChart(return_data, selectedAsset);
            },
        });
    }

    function getStatsRowForAsset(asset) {
        var statsRows = table.rows().data();

        for (var i = 0; i < statsRows.length; i++) {
            if (statsRows[i] && statsRows[i][0] == asset) {
                return statsRows[i];
            }
        }

        return null;
    }

    function statsScrollTo(selector) {
        var target = $(selector);
        if (target.length == 0) {
            return;
        }

        $('html, body').animate({
            scrollTop: Math.max(target.offset().top - 90, 0)
        }, 250);
    }

    function statsSetSummaryAction(actionName) {
        $('.stats-summary-action')
            .removeClass('active')
            .attr('aria-pressed', 'false');
        $('.stats-summary-action[data-stats-summary-action="' + actionName + '"]')
            .addClass('active')
            .attr('aria-pressed', 'true');
    }

    function statsShowSummaryMessage(message) {
        $('#stats_summary_action').text(message).show();
    }

    function statsClearAssetFilter() {
        activeStatsAssetFilter = 'all';
        if ($.fn.DataTable.isDataTable('#statspage_stats_datatable')) {
            table.search('').draw();
        }
    }

    function statsClearHoldingsFilter() {
        holdingsReconciliationTable.search('');
        holdingsReconciliationTable.columns().search('').draw();
    }

    function statsSelectFirstVisibleAsset() {
        var visibleRows = table.rows({ filter: 'applied' }).data();
        table.rows().deselect();

        if (visibleRows.length == 0) {
            return 0;
        }

        var firstVisibleRow = visibleRows[0];
        table.rows(function(index, rowData) {
            return rowData && firstVisibleRow && rowData[0] == firstVisibleRow[0];
        }).select();
        loadSelectedStatsAsset(firstVisibleRow, $('#stats_usd_spot').val());

        return visibleRows.length;
    }

    function statsFocusHoldingsRows(statuses, emptyMessage, populatedMessage) {
        statsClearAssetFilter();
        statsClearHoldingsFilter();

        if (statuses && statuses.length > 0) {
            var statusRegex = '^(' + statuses.map(statsRegexEscape).join('|') + ')$';
            holdingsReconciliationTable.column(6).search(statusRegex, true, false).draw();
        } else {
            holdingsReconciliationTable.draw();
        }

        $('#collapse_portfolio_holdings_reconciliation').collapse('show');

        var visibleRows = holdingsReconciliationTable.rows({ filter: 'applied' }).data();
        holdingsReconciliationTable.rows().deselect();

        if (visibleRows.length > 0) {
            var firstRow = visibleRows[0];
            holdingsReconciliationTable.rows(function(index, rowData) {
                return rowData && firstRow && rowData[0] == firstRow[0];
            }).select();

            var statsRow = getStatsRowForAsset(firstRow[0]);
            if (statsRow) {
                loadSelectedStatsAsset(statsRow, $('#stats_usd_spot').val());
            }

            statsShowSummaryMessage(populatedMessage + ' ' + visibleRows.length + ' asset' + (visibleRows.length == 1 ? '' : 's') + ' shown.');
        } else {
            statsShowSummaryMessage(emptyMessage);
        }

        statsScrollTo('#statspage_all_holdings_reconciliation_datatable');
    }

    function statsFocusImportWarnings() {
        statsClearAssetFilter();
        statsClearHoldingsFilter();

        if ($('#stats_import_warnings').is(':visible')) {
            statsShowSummaryMessage('Showing import warnings that need review before using generated reports.');
            statsScrollTo('#stats_import_warnings');
        } else {
            statsShowSummaryMessage('No import warnings are currently reported for this save.');
            statsScrollTo('#stats_summary_band');
        }
    }

    function statsFocusUnlinkedSales() {
        activeStatsAssetFilter = 'unlinked-sales';
        statsClearHoldingsFilter();
        table.search('').draw();

        var visibleRows = statsSelectFirstVisibleAsset();
        $('#collapse_sales').collapse('show');

        if ($('#stats_auto_fix_panel').is(':visible')) {
            statsScrollTo('#stats_auto_fix_panel');
        } else {
            statsScrollTo('#statspage_stats_datatable');
        }

        if (visibleRows > 0) {
            statsShowSummaryMessage('Showing assets with unlinked sales. ' + visibleRows + ' asset' + (visibleRows == 1 ? '' : 's') + ' shown; run FIFO Auto Link or inspect the selected asset.');
        } else {
            statsShowSummaryMessage('No assets currently have unlinked sales.');
        }
    }

    function statsHandleSummaryClick(actionName) {
        statsSetSummaryAction(actionName);

        if (actionName == 'reconciliation') {
            statsFocusHoldingsRows(
                ['Needs Review', 'Needs declared holdings', 'Unlinked sales'],
                'Reconciliation is ready; all holdings rows are verified.',
                'Showing holdings rows keeping reconciliation from ready.'
            );
        } else if (actionName == 'assets-needing-holdings') {
            statsFocusHoldingsRows(
                ['Needs declared holdings'],
                'No assets need declared holdings right now.',
                'Showing assets that still need declared holdings.'
            );
        } else if (actionName == 'needs-review') {
            statsFocusHoldingsRows(
                ['Needs Review', 'Unlinked sales'],
                'No holdings rows need review right now.',
                'Showing holdings rows that need review.'
            );
        } else if (actionName == 'import-warnings') {
            statsFocusImportWarnings();
        } else if (actionName == 'unlinked-sales') {
            statsFocusUnlinkedSales();
        }
    }


    if ($(".datetimepicker").length != 0) {
        $('.datetimepicker').datetimepicker({
          icons: {
            time: "fa fa-clock-o",
            date: "fa fa-calendar",
            up: "fa fa-chevron-up",
            down: "fa fa-chevron-down",
            previous: 'fa fa-chevron-left',
            next: 'fa fa-chevron-right',
            today: 'fa fa-screenshot',
            clear: 'fa fa-trash',
            close: 'fa fa-remove'
          }
        });
      }



    // on start_date change
    $("#start_date").datetimepicker().on('dp.change', function(ev){
        // console.log($("#start_date").datetimepicker().val())

        $.ajax({
            type: "POST",
            url: "/stats/date_range",
            data: JSON.stringify({
                'start_date': $("#start_date").datetimepicker().val(),
                'end_date': $("#end_date").datetimepicker().val()
                }),

            contentType: 'application/json',
            success: function (data) {
                // console.log(data)

                $('#statspage_stats_datatable').DataTable().clear();
                $('#statspage_stats_datatable').DataTable().rows.add(data['stats_table_rows']).draw();

                $('#stats_table_title').text('All Asset Stats for ' + data['date_range']['start_date'] + ' - ' + data['date_range']['end_date'])
                $('#detailed_stats_title').text('Detailed Asset Stats for ' + data['date_range']['start_date'] + ' - ' + data['date_range']['end_date'])

            },
        });
    });


    // on end_date change
    $("#end_date").datetimepicker().on('dp.change', function(ev){

        $.ajax({
            type: "POST",
            url: "/stats/date_range",
            data: JSON.stringify({
                'start_date': $("#start_date").datetimepicker().val(),
                'end_date': $("#end_date").datetimepicker().val()
                }),

            contentType: 'application/json',
            success: function (data) {
                // console.log(data)

                $('#statspage_stats_datatable').DataTable().clear();
                $('#statspage_stats_datatable').DataTable().rows.add(data['stats_table_rows']).draw();

                $('#stats_table_title').text('All Asset Stats for ' + data['date_range']['start_date'] + ' - ' + data['date_range']['end_date'])
                $('#detailed_stats_title').text('Detailed Asset Stats for ' + data['date_range']['start_date'] + ' - ' + data['date_range']['end_date'])

            },
        });
    });


    // init tables
    var table = $('#statspage_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $.fn.dataTable.ext.search.push(function(settings, rowData) {
        if (settings.nTable.id !== 'statspage_stats_datatable') {
            return true;
        }

        if (activeStatsAssetFilter == 'unlinked-sales') {
            return (statsParseQuantity(rowData[3]) || 0) > 0.00000001;
        }

        return true;
    });

    $('#statspage_detailed_datatable').DataTable({
        "pageLength": 50,
        select: {
            style: 'single'
        },
    });

    $('#statspage_links_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#statspage_sells_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#s8949_table').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#l8949_table').DataTable({
        select: {
            style: 'single'
        },
    });


    $('#statspage_buys_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#statspage_holdings_reconciliation_datatable').DataTable({
        "pageLength": 25,
        "searching": false,
        "paging": false,
        "info": false,
        "ordering": false,
        "columnDefs": [
            {
                "targets": 1,
                "render": function(data, type, row) {
                    if (type !== 'display' || !row || row[0] !== 'Status') {
                        return data;
                    }

                    return statusBadgeHtml(data);
                }
            }
        ],
        select: {
            style: 'single'
        },
    });

    var holdingsReconciliationTable = $('#statspage_all_holdings_reconciliation_datatable').DataTable({
        "pageLength": 25,
        "order": [[ 0, "asc" ]],
        "columnDefs": [
            {
                "targets": 6,
                "render": function(data, type) {
                    if (type !== 'display') {
                        return data;
                    }

                    return statusBadgeHtml(data);
                }
            }
        ],
        select: {
            style: 'single'
        },
    });

    $('.stats-summary-action').on('click', function() {
        statsHandleSummaryClick($(this).data('stats-summary-action'));
    });

    $("#stats_auto_fix_safe_button").click(function(){
        var button = $(this);
        var selectedAsset = selectedStatsRowData ? selectedStatsRowData[0] : null;

        $('#stats_auto_fix_result').removeClass('text-danger').text('');
        button.prop('disabled', true).text('Linking...');

        $.ajax({
            type: "POST",
            url: "/stats/auto_fix_safe",
            data: JSON.stringify({
                'year': $('#stats_page_year_dropdown').find(":selected").val()
            }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                table.clear();
                table.rows.add(data['stats_table_rows'] || []).draw();
                setStatsReconciliationWarning(data['reconciliation_status']);
                setStatsImportWarnings(data['import_warnings'], data['import_warning_rows']);
                setStatsSummary(data['stats_summary']);
                setAllHoldingsReconciliation(data['holdings_reconciliation_table_data']);
                $('#stats_auto_fix_result').text(data['message'] || 'FIFO auto-link complete. Review the generated links.');
                $('#stats_auto_fix_panel').show();

                if (selectedAsset) {
                    var refreshedSelectedRow = getStatsRowForAsset(selectedAsset);
                    if (refreshedSelectedRow) {
                        loadSelectedStatsAsset(refreshedSelectedRow, $('#stats_usd_spot').val());
                    }
                }
            },
            error: function () {
                $('#stats_auto_fix_result')
                    .addClass('text-danger')
                    .text('FIFO auto-link could not run. Please try Auto Link or review the data manually.');
            },
            complete: function () {
                button.prop('disabled', false).text('Run FIFO Auto Link');
            },
        });
    });

    $('#statspage_holdings_lots_datatable').DataTable({
        "pageLength": 25,
        "order": [[ 2, "asc" ]],
        select: {
            style: 'single'
        },
    });

    $("#stats_usd_spot").on('change', function(){
        loadSelectedStatsAsset(selectedStatsRowData || table.row({selected:true}).data(), $(this).val());
    });


    $('#stats_page_year_dropdown').on('change', function() {

        // console.log($(this).find(":selected").val())

        $.ajax({
            type: "POST",
            url: "/stats/date_range",
            data: JSON.stringify({
                'year': $(this).find(":selected").val(),
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                // console.log(data)

                $('#statspage_stats_datatable').DataTable().clear();
                $('#statspage_stats_datatable').DataTable().rows.add(data['stats_table_rows']).draw();
                setStatsReconciliationWarning(data['reconciliation_status']);
                setStatsImportWarnings(data['import_warnings'], data['import_warning_rows']);
                setAllHoldingsReconciliation(data['holdings_reconciliation_table_data']);
                $('#statspage_detailed_datatable').DataTable().clear().draw();
                $('#statspage_sells_datatable').DataTable().clear().draw();
                $('#statspage_holdings_lots_datatable').DataTable().clear().draw();
                $('#statspage_holdings_reconciliation_datatable').DataTable().clear().draw();
                $('#s8949_table').DataTable().clear().draw();
                $('#l8949_table').DataTable().clear().draw();
                setStatsSummary(data['stats_summary']);
                $('#collapse_sales, #collapse_8949_long, #collapse_8949_short').collapse('hide');
                $('#stats_usd_spot').val('');
                selectedStatsRowData = null;
                resetGainzChart();

            },
        });

    });

    $('#statspage_stats_datatable tbody').on( 'click', 'tr', function () {
        loadSelectedStatsAsset(table.row(this).data(), $('#stats_usd_spot').val());
    } );

    $('#statspage_all_holdings_reconciliation_datatable tbody').on( 'click', 'tr', function () {
        var reconciliationRow = holdingsReconciliationTable.row(this).data();

        if (!reconciliationRow) {
            return;
        }

        var statsRow = getStatsRowForAsset(reconciliationRow[0]);
        if (statsRow) {
            loadSelectedStatsAsset(statsRow, $('#stats_usd_spot').val());
        }
    } );


} );




// history page code
$(document).ready(function() {
    if ($('#historypage_datatable').length === 0) {
        return;
    }

    $('#historypage_datatable').DataTable({
        order: [],
        pageLength: 25
    });

    $('.history-restore-form').on('submit', function() {
        var button = $(this).find('button[type="submit"]');
        var revision = button.data('revision') || 'this revision';
        var description = button.data('description') || '';
        var message = [
            'Restore revision ' + revision + ' as the latest Gainz revision?',
            '',
            description,
            '',
            'This will not delete newer saves. Gainz will create a new revision from the selected save.'
        ].join('\n');

        if (!window.confirm(message)) {
            return false;
        }

        button.prop('disabled', true).text('Restoring...');
        return true;
    });
} );

// export page code
$(document).ready(function() {


    $('#exportpage_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    function exportOutputPayload() {
        var isReady = String($('#draft_export_ack_panel').data('ready')) == '1';
        return {
            'output_location': $('#export_output_location').val(),
            'draft_acknowledged': isReady || $('#draft_export_ack').is(':checked')
        };
    }

    function exportResponsePath(data) {
        if (typeof data == 'string') {
            return data;
        }

        return data && data.path ? data.path : '';
    }

    function exportReadyForOutput() {
        var isReady = String($('#draft_export_ack_panel').data('ready')) == '1';
        if (isReady || $('#draft_export_ack').is(':checked')) {
            return true;
        }

        $('#export_button_text').text('Check the draft-output acknowledgement before generating files with unresolved review items.');
        return false;
    }

    function updatePacketPreviewOutputFolder() {
        var selectedFolder = $('#export_output_location option:selected').data('folder') || '';
        $('#packet_preview_output_folder').text(selectedFolder || 'Not selected');
    }

    $('#export_output_location').on('change', updatePacketPreviewOutputFolder);
    updatePacketPreviewOutputFolder();

    // $('#exportpage_stats_datatable tbody').on( 'click', 'tr', function () {
    //     console.log( table.row( this ).data() );
    //     $.ajax({
    //         type: "POST",
    //         url: "/stats/selected_asset",
    //         data: JSON.stringify({
    //             'row_data': table.row( this ).data(),
    //             'start_date': $('#export_datepicker').data('daterangepicker')['startDate'],
    //             'end_date': $('#export_datepicker').data('daterangepicker')['endDate']
    //             }),

    //         contentType: 'application/json',
    //         success: function (data) {

    //             console.log(data)

    //             $('#statspage_detailed_datatable').DataTable().clear();
    //             $('#statspage_detailed_datatable').DataTable().rows.add(data['detailed_stats']).draw();
    //         },
    //     });
    // } );


    $("#export_button").click(function(){
        if (!exportReadyForOutput()) {
            return;
        }

        $('#export_button_text').text('Creating Excel export...');
        $.ajax({
            type: "POST",
            url: "/export/save",
            data: JSON.stringify(exportOutputPayload()),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                var outputPath = exportResponsePath(data);
                $('#export_button_text').text("Export saved to " + outputPath);
                alert("Export saved to " + outputPath)
            },
            error: function (xhr) {
                var message = "Export failed. Check the output folder and app log, then try again.";
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    message = xhr.responseJSON.message;
                }
                $('#export_button_text').text(message);
            },
        });
    });

    $("#audit_packet_button").click(function(){
        if (!exportReadyForOutput()) {
            return;
        }

        $('#export_button_text').text('Generating audit packet...');
        $.ajax({
            type: "POST",
            url: "/export/audit_packet",
            data: JSON.stringify(exportOutputPayload()),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                var outputPath = exportResponsePath(data);
                $('#export_button_text').text("Audit packet saved to " + outputPath);
                if (data && data.success_url) {
                    window.location.href = data.success_url;
                } else {
                    alert("Audit packet saved to " + outputPath)
                }
            },
            error: function (xhr) {
                var message = "Audit packet failed. Check the readiness blockers, output folder, and app log, then try again.";
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    message = xhr.responseJSON.message;
                }
                $('#export_button_text').text(message);
            },
        });
    });

});




// Add and Manage Links Page
$(document).ready(function() {


    $('#addlinks_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#addlinks_sells_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#linked_datatable').DataTable({
        select: {
            style: 'multiple'
        },
    });

    $('#linkable_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#add_links_all_links_datatable').DataTable({
        select: {
            style: 'multiple'
        },
    });


    $('#checkbox_unlinked').on('click', function() {

        if ($('#addlinks_stats_datatable').DataTable().row( {selected:true} ).length > 0 ) {

            $.ajax({
                type: "POST",
                url: "/add_links/add_links_selected_asset",
                data: JSON.stringify({
                    'row_data': $('#addlinks_stats_datatable').DataTable().row( {selected:true} ).data(),
                    'start_date': '',
                    'end_date': '',
                    'unlinked_remaining': $('#checkbox_unlinked').is(':checked')
                    }),

                contentType: 'application/json',
                success: function (data) {

                    // console.log(data)


                    $('#addlinks_sells_datatable').DataTable().clear();
                    $('#addlinks_sells_datatable').DataTable().rows.add(data['sells']).draw();

                    $('#add_links_all_links_datatable').DataTable().clear();
                    $('#add_links_all_links_datatable').DataTable().rows.add(data['all_links']).draw();

                },
            });

        }

    });

    $('#addlinks_stats_datatable tbody').on( 'click', 'tr', function () {
        // console.log( $('#addlinks_stats_datatable').DataTable().row( this ).data() );

        $.ajax({
            type: "POST",
            url: "/add_links/add_links_selected_asset",
            data: JSON.stringify({
                'row_data': $('#addlinks_stats_datatable').DataTable().row( this ).data(),
                'start_date': '',
                'end_date': '',
                'unlinked_remaining': $('#checkbox_unlinked').is(':checked')
                }),

            contentType: 'application/json',
            success: function (data) {

                // console.log(data)


                $('#addlinks_sells_datatable').DataTable().clear();
                $('#addlinks_sells_datatable').DataTable().rows.add(data['sells']).draw();

                $('#add_links_all_links_datatable').DataTable().clear();
                $('#add_links_all_links_datatable').DataTable().rows.add(data['all_links']).draw();


            },
        });

    });

    var batch_data = {}

    $('#addlinks_sells_datatable tbody').on( 'click', 'tr', function () {
        console.log( $('#addlinks_sells_datatable').DataTable().row( this ).data() );

        $.ajax({
            type: "POST",
            url: "/add_links/linkable_data",
            data: JSON.stringify({
                'row_data': $('#addlinks_sells_datatable').DataTable().row( this ).data()
              }),

            contentType: 'application/json',
            success: function (data) {
                // console.log(data)

                batch_data = data

                $('#add_links_batch_options').children().remove()

                $('#linked_datatable').DataTable().clear();
                $('#linked_datatable').DataTable().rows.add(data['linked']).draw();

                $('#linkable_datatable').DataTable().clear();
                $('#linkable_datatable').DataTable().rows.add(data['linkable']).draw();

                $('#unlinkable_datatable').DataTable().clear();
                $('#unlinkable_datatable').DataTable().rows.add(data['unlinkable']).draw();



                if (data['min_links_batch'].length > 0) {$('#add_links_batch_options').append('<option>Min Links</option>')}
                if (data['min_gain_batch'].length > 0) {$('#add_links_batch_options').append('<option>Min Gain</option>')}
                if (data['min_gain_long_batch'].length > 0) {$('#add_links_batch_options').append('<option>Min Gain Long</option>')}
                if (data['min_gain_short_batch'].length > 0) {$('#add_links_batch_options').append('<option>Min Gain Short</option>')}

                if (data['max_gain_batch'].length > 0) {$('#add_links_batch_options').append('<option>Max Gain</option>')}
                if (data['max_gain_long_batch'].length > 0) {$('#add_links_batch_options').append('<option>Max Gain Long</option>')}
                if (data['max_gain_short_batch'].length > 0) {$('#add_links_batch_options').append('<option>Max Gain Short</option>')}

                if (data['max_gain_long_batch'].length > 0) { $('#add_links_batch_options').val('Max Gain Long').change() }
                else if (data['max_gain_batch'].length > 0) { $('#add_links_batch_options').val('Max Gain').change() }
                else if (data['min_links_batch'].length > 0) {  $('#add_links_batch_options').val('Min Links').change()  }
                else { $('#add_links_batch_options').val('') }


                $('#all_linkable_buys_datatable').DataTable().clear();
                $('#all_linkable_buys_datatable').DataTable().rows.add(batch_data['all_linkable_buys_datatable']).draw();

                $('#model_quantity').val(data['potential_sale_quantity'])

                $('#total_in_usd').val(data['total_in_usd'])


            },
        });
    } );


    $('#add_links_batch_options').on('change', function() {
        // alert( $(this).find(":selected").val() );

        if ($(this).find(":selected").val() == 'Min Links') {

            $('#add_links_batches_datatable').DataTable().clear();
            $('#add_links_batches_datatable').DataTable().rows.add(batch_data['min_links_batch']).draw();
            $('#add_links_batch_text').html(batch_data['min_links_batch_text']);

        } else if ($(this).find(":selected").val() == 'Min Gain') {

            $('#add_links_batches_datatable').DataTable().clear();
            $('#add_links_batches_datatable').DataTable().rows.add(batch_data['min_gain_batch']).draw();
            $('#add_links_batch_text').html(batch_data['min_gain_batch_text']);

        } else if ($(this).find(":selected").val() == 'Min Gain Long') {

            $('#add_links_batches_datatable').DataTable().clear();
            $('#add_links_batches_datatable').DataTable().rows.add(batch_data['min_gain_long_batch']).draw();
            $('#add_links_batch_text').html(batch_data['min_gain_long_batch_text']);

        } else if ($(this).find(":selected").val() == 'Min Gain Short') {

            $('#add_links_batches_datatable').DataTable().clear();
            $('#add_links_batches_datatable').DataTable().rows.add(batch_data['min_gain_short_batch']).draw();
            $('#add_links_batch_text').html(batch_data['min_gain_short_batch_text']);

        } else if ($(this).find(":selected").val() == 'Max Gain') {

            $('#add_links_batches_datatable').DataTable().clear();
            $('#add_links_batches_datatable').DataTable().rows.add(batch_data['max_gain_batch']).draw();
            $('#add_links_batch_text').html(batch_data['max_gain_batch_text']);

        } else if ($(this).find(":selected").val() == 'Max Gain Long') {

            $('#add_links_batches_datatable').DataTable().clear();
            $('#add_links_batches_datatable').DataTable().rows.add(batch_data['max_gain_long_batch']).draw();
            $('#add_links_batch_text').html(batch_data['max_gain_long_batch_text']);

        } else if ($(this).find(":selected").val() == 'Max Gain Short') {

            $('#add_links_batches_datatable').DataTable().clear();
            $('#add_links_batches_datatable').DataTable().rows.add(batch_data['max_gain_short_batch']).draw();
            $('#add_links_batch_text').html(batch_data['max_gain_short_batch_text']);
        }

     });


    $("#link_button").click(function(){
        // alert($('#linkable_datatable').DataTable().row( {selected:true} ).data());
        // alert($('#sells_datatable').DataTable().row( {selected:true} ).data());
        $.ajax({
            type: "POST",
            url: "/add_links/link_button",
            data: JSON.stringify({
                'sell_data': $('#addlinks_sells_datatable').DataTable().row( {selected:true} ).data(),
                'buy_data': $('#linkable_datatable').DataTable().row( {selected:true} ).data(),

              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert("Creating and Saving New Links!")
                $('#sells_datatable').DataTable().clear();
                $('#sells_datatable').DataTable().rows.add(data).draw();
                location.reload()
            },
        });
    });

    $("#add_links_batch_button").click(function(){
        // alert($('#linkable_datatable').DataTable().row( {selected:true} ).data());
        // alert($('#sells_datatable').DataTable().row( {selected:true} ).data());
        $.ajax({
            type: "POST",
            url: "/add_links/link_batch",
            data: JSON.stringify({
                'sell_data': $('#addlinks_sells_datatable').DataTable().row( {selected:true} ).data(),
                'buy_data': $('#add_links_batches_datatable').DataTable().rows().data(),

              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert("Posting a new link!")
                location.reload()
            },
        });
    });


    $("#addlinks_linked_delete_link").click(function(){

        // console.log( $('#linked_datatable').DataTable().rows( {selected:true} ).data() )


        $.ajax({
            type: "POST",
            url: "/add_links/delete_link_from_linked",
            data: JSON.stringify({
                'links': $('#linked_datatable').DataTable().rows( {selected:true} ).data(),
                'symbol': $('#addlinks_sells_datatable').DataTable().row( {selected:true} ).data()[1],
                'sell_time_stamp': $('#addlinks_sells_datatable').DataTable().row( {selected:true} ).data()[2]
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert("Deleting link(s)!")
                location.reload()
            },
        });

    });


    $("#addlinks_alllinks_delete_link").click(function(){

        // console.log( $('#add_links_all_links_datatable').DataTable().rows( {selected:true} ).data() )


        $.ajax({
            type: "POST",
            url: "/add_links/delete_link",
            data: JSON.stringify({
                'links': $('#add_links_all_links_datatable').DataTable().rows( {selected:true} ).data(),
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert("Deleting link(s)!")
                location.reload()
            },
        });

    });


} );


// Import & Manage Data Page

$(document).ready(function() {

    $('#import_datatable').DataTable({
        "pageLength": 25,
        select: {
            style: 'single'
        },
    });

    function manualTransactionRowHtml() {
        return '' +
            '<tr>' +
            '<td><select name="manual_type[]" class="form-control">' +
            '<option value="buy">Buy</option>' +
            '<option value="sell">Sell</option>' +
            '</select></td>' +
            '<td><input type="datetime-local" name="manual_timestamp[]" class="form-control"></td>' +
            '<td><input type="text" name="manual_symbol[]" class="form-control text-uppercase" placeholder="BTC"></td>' +
            '<td><input type="number" step="any" min="0" name="manual_quantity[]" class="form-control" placeholder="0.00000000"></td>' +
            '<td><input type="number" step="any" min="0" name="manual_usd_spot[]" class="form-control" placeholder="65000.00"></td>' +
            '<td><button type="button" class="btn btn-sm btn-outline-danger remove-manual-row-button">Remove</button></td>' +
            '</tr>';
    }

    $('#add_manual_transaction_row').on('click', function() {
        $('#manual_transactions_table tbody').append(manualTransactionRowHtml());
    });

    $('#manual_transactions_table').on('click', '.remove-manual-row-button', function() {
        $(this).closest('tr').remove();

        if ($('#manual_transactions_table tbody tr').length == 0) {
            $('#manual_transactions_table tbody').append(manualTransactionRowHtml());
        }
    });



} );


// Sweet Alerts
function showSwal(type, title, text) {
    if (type == 'basic') {
      Swal.fire({
        title: "Message Title",
        text: text,
        customClass: {
          confirmButton: 'btn btn-success'
        },
        buttonsStyling: false

      })

    } else if (type == 'question') {

      Swal.fire({
        title: title,
        text: text,
        type: 'question',
        customClass: {
          confirmButton: 'btn btn-info'
        },
        buttonsStyling: false,
      })
    }

    else if (type == 'warning-message-and-confirmation') {
        const swalWithBootstrapButtons = Swal.mixin({
          customClass: {
            confirmButton: 'btn btn-success',
            cancelButton: 'btn btn-danger'
          },
          buttonsStyling: false
        })

        swalWithBootstrapButtons.fire({
          title: title,
          text: text,
          type: 'warning',
          showCancelButton: true,
          confirmButtonText: 'Yes, create it',
          cancelButtonText: 'No, cancel!',
          reverseButtons: true
        }).then((result) => {
          if (result.value) {
            swalWithBootstrapButtons.fire(
              'Deleted!',
              'Your file has been deleted.',
              'success'
            )
          } else if (
            /* Read more about handling dismissals below */
            result.dismiss === Swal.DismissReason.cancel
          ) {
            swalWithBootstrapButtons.fire(
              'Cancelled',
              'Your imaginary file is safe :)',
              'error'
            )
          }
        })
      }
}




// Add Manual Transactions Page
$(document).ready(function() {


    $('#add_transactions_stats_datatable').DataTable({
        "pageLength": 25,
        select: {
            style: 'single'
        },
    });

    $('#add_transactions_sells_datatable').DataTable({
        "pageLength": 10,
        select: {
            style: 'single'
        },
    });

    $('#add_transactions_buys_datatable').DataTable({
        "pageLength": 10,
        select: {
            style: 'single'
        },
    });

    $('#add_transactions_sends_datatable').DataTable({
        "pageLength": 10,
        select: {
            style: 'single'
        },
    });

    $('#add_transactions_receive_datatable').DataTable({
        "pageLength": 10,
        select: {
            style: 'multiple'
        },
    });




    $('#add_transactions_stats_datatable tbody').on( 'click', 'tr', function () {

        $.ajax({
            type: "POST",
            url: "/import_data/add_transactions_selected_asset",
            data: JSON.stringify({
                'row_data':  $('#add_transactions_stats_datatable').DataTable().row( this ).data(),
                'unlinked_remaining': $('#manage_trans_buys_checkbox_unlinked').is(':checked')
                }),

            contentType: 'application/json',
            success: function (data) {

                // console.log(data)

                $('#add_transactions_sells_datatable').DataTable().clear();
                $('#add_transactions_sells_datatable').DataTable().rows.add(data['sells']).draw();

                $('#add_transactions_buys_datatable').DataTable().clear();
                $('#add_transactions_buys_datatable').DataTable().rows.add(data['buys']).draw();

                $('#add_transactions_sends_datatable').DataTable().clear();
                $('#add_transactions_sends_datatable').DataTable().rows.add(data['sends']).draw();

                $('#add_transactions_receive_datatable').DataTable().clear();
                $('#add_transactions_receive_datatable').DataTable().rows.add(data['receives']).draw();




            },
        });
    } );



    $("#sells_delete_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/import_data/delete_transactions",
            data: JSON.stringify({
                'row_data': $('#add_transactions_sells_datatable').DataTable().row( {selected:true} ).data(),
                'asset': $('#add_transactions_stats_datatable').DataTable().row( {selected:true} ).data(),
                'type': 'sell'
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },
        });
    });

    $('#manage_trans_buys_checkbox_unlinked').on('click', function() {

        var json_data = {
            'row_data':  $('#add_transactions_stats_datatable').DataTable().row( {selected:true} ).data(),
            'unlinked_remaining': $('#manage_trans_buys_checkbox_unlinked').is(':checked'),
        }

        if ($('#manage_transactions_usd_spot').val()) {
            // console.log($('#manage_transactions_usd_spot').val())
            json_data['usd_spot'] = $('#manage_transactions_usd_spot').val()
        }

        $.ajax({
            type: "POST",
            url: "/import_data/add_transactions_selected_asset",
            data: JSON.stringify(json_data),

            contentType: 'application/json',
            success: function (data) {

                console.log(data)

                $('#add_transactions_sells_datatable').DataTable().clear();
                $('#add_transactions_sells_datatable').DataTable().rows.add(data['sells']).draw();

                $('#add_transactions_buys_datatable').DataTable().clear();
                $('#add_transactions_buys_datatable').DataTable().rows.add(data['buys']).draw();

                $('#add_transactions_sends_datatable').DataTable().clear();
                $('#add_transactions_sends_datatable').DataTable().rows.add(data['sends']).draw();

                $('#add_transactions_receive_datatable').DataTable().clear();
                $('#add_transactions_receive_datatable').DataTable().rows.add(data['receives']).draw();
            },
        });

    });

    $("#manage_transactions_usd_spot").on('change', function(){

        // console.log($(this).val())

        $.ajax({
            type: "POST",
            url: "/import_data/add_transactions_selected_asset",
            data: JSON.stringify({
                'row_data':  $('#add_transactions_stats_datatable').DataTable().row( {selected:true} ).data(),
                'unlinked_remaining': $('#manage_trans_buys_checkbox_unlinked').is(':checked'),
                'usd_spot': $(this).val()
                }),

            contentType: 'application/json',
            success: function (data) {

                console.log(data)

                $('#add_transactions_sells_datatable').DataTable().clear();
                $('#add_transactions_sells_datatable').DataTable().rows.add(data['sells']).draw();

                $('#add_transactions_buys_datatable').DataTable().clear();
                $('#add_transactions_buys_datatable').DataTable().rows.add(data['buys']).draw();

                $('#add_transactions_sends_datatable').DataTable().clear();
                $('#add_transactions_sends_datatable').DataTable().rows.add(data['sends']).draw();

                $('#add_transactions_receive_datatable').DataTable().clear();
                $('#add_transactions_receive_datatable').DataTable().rows.add(data['receives']).draw();



            },
        });

    });

    $("#buys_delete_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/import_data/delete_transactions",
            data: JSON.stringify({
                'row_data': $('#add_transactions_buys_datatable').DataTable().row( {selected:true} ).data(),
                'asset': $('#add_transactions_stats_datatable').DataTable().row( {selected:true} ).data(),
                'type': 'buy'
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },
        });
    });

    $("#buys_convert_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/import_data/buy_convert",
            data: JSON.stringify({
                'row_data': $('#add_transactions_buys_datatable').DataTable().row( {selected:true} ).data(),
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },
        });
    });

    $("#receive_convert_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/import_data/receive_convert",
            data: JSON.stringify({
                'table_data': $('#add_transactions_receive_datatable').DataTable().rows( {selected:true} ).data(),
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },
        });
    });

    $("#send_convert_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/import_data/send_convert",
            data: JSON.stringify({
                'row_data': $('#add_transactions_sends_datatable').DataTable().row( {selected:true} ).data(),
              }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },
        });
    });

} );




// Model Page
$(document).ready(function() {

    var modelStatsTable = $('#model_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    var allModelLotsTable = $('#all_linkable_buys_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    var modelBatchTable = $('#model_batches_datatable').DataTable({
        "pageLength": 25,
        select: {
            style: 'single'
        },
    });

    var batch_data = {};
    var selectedModelRow = null;

    function modelSetWarnings(warnings) {
        var warningBox = $('#model_warnings');
        warningBox.empty();

        if (warnings && warnings.length > 0) {
            warnings.forEach(function(warning) {
                warningBox.append($('<div>').text(warning));
            });
            warningBox.show();
        } else {
            warningBox.hide();
        }
    }

    function modelRenderBatch(batchKey) {
        if (!batch_data || !batch_data.batches_by_key) {
            return;
        }

        var batch = batch_data.batches_by_key[batchKey];
        if (!batch) {
            modelBatchTable.clear().draw();
            return;
        }

        var summary = batch.summary || {};
        $('#model_summary_method').text(batch.label || 'FIFO');
        $('#model_summary_quantity').text(summary.quantity_display || '--');
        $('#model_summary_proceeds').text(summary.proceeds_display || '--');
        $('#model_summary_cost_basis').text(summary.cost_basis_display || '--');
        $('#model_summary_gain_loss').text(summary.gain_loss_display || '--');
        $('#model_summary_long').text((summary.long_quantity_display || '0') + ' / ' + (summary.long_gain_loss_display || '$0.00'));
        $('#model_summary_short').text((summary.short_quantity_display || '0') + ' / ' + (summary.short_gain_loss_display || '$0.00'));

        modelBatchTable.clear();
        modelBatchTable.rows.add(batch.rows || []).draw();
        $('#model_result_panel').show();
    }

    $('#model_stats_datatable tbody').on( 'click', 'tr', function () {
        selectedModelRow = modelStatsTable.row(this).data();
        $('#model_submit').prop('disabled', false);
        if (selectedModelRow) {
            $('#model_selected_asset').text(selectedModelRow[0] + ' selected');
        }
    });

    $('#model_submit').on('click', function () {
        if (!selectedModelRow) {
            alert('Select an asset first.');
            return;
        }

        var button = $(this);
        button.prop('disabled', true).text('Modeling...');

        $.ajax({
            type: "POST",
            url: "/model/selected_asset",
            data: JSON.stringify({
                'row_data': selectedModelRow,
                'usd_spot': $('#model_usd_spot').val(),
                'quantity': $('#model_quantity').val(),
                'total_in_usd': $('#total_in_usd').val()
                }),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                batch_data = data;

                $('#model_batch_options').children().remove();
                (data.batch_options || []).forEach(function(option) {
                    var label = option.label;
                    if (option.key == data.default_batch_key) {
                        label = label + ' (Default)';
                    }
                    $('#model_batch_options').append(
                        $('<option>').val(option.key).text(label)
                    );
                });

                $('#model_quantity').val(data.potential_sale_quantity_display || data.potential_sale_quantity);
                $('#total_in_usd').val(data.total_in_usd);
                allModelLotsTable.clear();
                allModelLotsTable.rows.add(data.all_linkable_buys_datatable || []).draw();
                modelSetWarnings(data.warnings);

                if (data.default_batch_key) {
                    $('#model_batch_options').val(data.default_batch_key);
                    modelRenderBatch(data.default_batch_key);
                } else {
                    modelBatchTable.clear().draw();
                    $('#model_result_panel').hide();
                    modelSetWarnings(['No current lots are available to model this sale.']);
                }
            },
            error: function (xhr) {
                var message = 'Model sale could not run. Check the asset, sale amount, and USD spot.';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    message = xhr.responseJSON.error;
                }
                modelSetWarnings([message]);
            },
            complete: function () {
                button.prop('disabled', false).text('Model FIFO Sale');
            },
        });
    } );


    $('#model_batch_options').on('change', function() {
        modelRenderBatch($(this).find(":selected").val());

     });











} );
