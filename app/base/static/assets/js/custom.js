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
        message += " Next: import more files, then continue to Declare Holdings.";
    }

    return message;
}

function gainzShowImportResult(result, fileName, alertClass) {
    var warnings = result.warnings || [];
    var warningRows = result.data_summary ? (result.data_summary.import_warning_rows || []) : (result.warning_rows || []);
    var unresolvedWarningRows = result.data_summary ? (result.data_summary.unresolved_import_warning_rows || []) : [];
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
            warningRows,
            unresolvedWarningRows
        );
    } else {
        $("#import_warning_workflow").hide();
    }

    if (result.data_summary) {
        gainzSetSourceOverlapWorkflow(result.data_summary.source_overlaps || []);
        gainzRenderDataSources(result.data_summary);
        gainzUpdateImportContinuePanel(result.data_summary);
        gainzUpdateImportCurrentDecision(result.data_summary);
    }
}

function gainzConfirmDialog(options) {
    options = options || {};
    var dialog = $("#gainz_confirm_dialog");

    if (dialog.length === 0) {
        $("body").append(
            '<div id="gainz_confirm_dialog" class="gainz-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="gainz_confirm_dialog_title" style="display: none;">' +
                '<div class="gainz-confirm-dialog-card">' +
                    '<h2 id="gainz_confirm_dialog_title"></h2>' +
                    '<div id="gainz_confirm_dialog_message" class="gainz-confirm-dialog-message"></div>' +
                    '<div class="gainz-confirm-dialog-actions">' +
                        '<button type="button" id="gainz_confirm_dialog_cancel" class="btn btn-outline-secondary">Cancel</button>' +
                        '<button type="button" id="gainz_confirm_dialog_confirm" class="btn btn-warning">Continue</button>' +
                    '</div>' +
                '</div>' +
            '</div>'
        );
        dialog = $("#gainz_confirm_dialog");
    }

    $("#gainz_confirm_dialog_title").text(options.title || "Confirm action");
    $("#gainz_confirm_dialog_message").empty();
    String(options.message || "").split("\n").forEach(function(line) {
        $("#gainz_confirm_dialog_message").append($("<p></p>").text(line || "\u00a0"));
    });
    $("#gainz_confirm_dialog_confirm").text(options.confirmText || "Continue");
    $("#gainz_confirm_dialog_cancel").text(options.cancelText || "Cancel");
    $("#gainz_confirm_dialog_confirm").off("click").on("click", function() {
        dialog.hide();
        if (options.onConfirm) {
            options.onConfirm();
        }
    });
    $("#gainz_confirm_dialog_cancel").off("click").on("click", function() {
        dialog.hide();
        if (options.onCancel) {
            options.onCancel();
        }
    });
    dialog.css("display", "flex");
    $("#gainz_confirm_dialog_confirm").focus();
}

function gainzUpdateImportContinuePanel(summary) {
    var panel = $("#import_continue_panel");
    if (panel.length === 0 || !summary) {
        return;
    }

    var transactionCount = summary.transaction_count || 0;
    var unresolvedWarnings = summary.unresolved_import_warning_count || 0;
    var canContinue = transactionCount > 0 && unresolvedWarnings === 0;
    var action = panel.find(".import-continue-action");
    var message = panel.find(".import-continue-message");
    var heading = panel.find("strong").first();

    panel
        .removeClass("alert-success alert-warning")
        .addClass(canContinue ? "alert-success" : "alert-warning");

    if (transactionCount > 0) {
        heading.text(canContinue ? "Import data is ready for the next step." : "Import data is loaded, but review is still needed.");
        message.text(
            canContinue
                ? "Continue when you have loaded the source files you want included in this review pass."
                : "Review " + unresolvedWarnings + " unresolved import warning" + (unresolvedWarnings == 1 ? "" : "s") + " before moving to Declare Holdings."
        );
        action.toggle(canContinue);
        panel.show();
    } else {
        panel.hide();
    }
}

function gainzUpdateImportCurrentDecision(summary) {
    var panel = $("#import_current_decision");
    if (panel.length === 0 || !summary) {
        return;
    }

    var warningRows = summary.unresolved_import_warning_rows || [];
    var sourceOverlaps = summary.source_overlaps || [];
    var transactionCount = summary.transaction_count || 0;
    var task = "Upload source data";
    var why = "Gainz needs source transactions before holdings or reports can be reviewed.";
    var bestAction = "Try demo data or upload one exchange CSV.";

    if (warningRows.length > 0) {
        var firstWarning = warningRows[0] || {};
        var firstOption = (firstWarning.decision_options || [])[0] || {};
        task = "Decide what row " + (firstWarning.row || "this row") + " represents";
        why = firstWarning.card_title || firstWarning.issue || "Gainz found an import warning.";
        bestAction = firstOption.label || "Answer the warning card below.";
    } else if (sourceOverlaps.length > 0) {
        task = "Review possible duplicate source files";
        why = "Gainz found files that may cover the same activity.";
        bestAction = "Open source review and confirm whether one file duplicates another.";
    } else if (transactionCount > 0) {
        task = "Confirm source data is ready";
        why = "Source rows are loaded and no unresolved import warnings are blocking this step.";
        bestAction = "Continue to Declare Holdings when all intended CSVs are loaded.";
    }

    $("#import_current_task").text(task);
    $("#import_current_why").text(why);
    $("#import_current_best_action").text(bestAction);
}

function gainzRenderSourceOverlapTable(rows) {
    var table = $("#source_overlap_table");
    var tbody = table.find("tbody");
    var firstPanel = $("#source_overlap_first_panel");

    if (table.length === 0 || tbody.length === 0) {
        return;
    }

    tbody.empty();
    if (firstPanel.length) {
        firstPanel.empty();
        if (rows && rows.length > 0) {
            var first = rows[0];
            var details = $('<dl class="guided-review-details"></dl>');
            [
                ["Possible full-history source", (first.name_a || "Source A") + " " + (first.date_range_a || "")],
                ["Possible year-specific source", (first.name_b || "Source B") + " " + (first.date_range_b || "")],
                ["Matching rows", (first.matching_rows || 0) + " (" + (first.overlap_percent || "0%") + ")"],
                ["Next action", first.next_action || "Review sources and remove the duplicate only after confirming the overlap."]
            ].forEach(function(item) {
                details.append(
                    $("<div></div>")
                        .append($("<dt></dt>").text(item[0]))
                        .append($("<dd></dd>").text(item[1]))
                );
            });
            firstPanel
                .append($("<h3></h3>").text("Decide whether these files duplicate the same activity"))
                .append(
                    $("<p></p>").text("These two source files share rows. If one file fully contains the other, keep the fuller source and remove the duplicate from this review pass. If both contain unique records, keep both and document why.")
                )
                .append(details)
                .append(
                    $('<div class="alert alert-light" role="status"></div>')
                        .text("If one file fully contains the other, keep the full-history source and remove only the duplicate after confirming the row coverage. If you are unsure, leave both and document the question for review.")
                )
                .append(
                    $('<div class="guided-review-actions"></div>')
                        .append($('<a class="btn btn-sm btn-primary" href="#source-review">Review row coverage before removing anything</a>'))
                        .append($('<a class="btn btn-sm btn-outline-secondary" href="/export/review_queue?guided=1">Open Guided Review Queue</a>'))
                )
                .show();
        } else {
            firstPanel.hide();
        }
    }

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

function gainzOpenAdvancedImport() {
    var advancedDetails = $("#advanced-import");
    if (advancedDetails.length) {
        advancedDetails.prop("open", true);
    }

    $("#import_review_columns_before_import").prop("checked", true);
    $("#import_upload_result")
        .removeClass("alert-danger alert-info alert-warning")
        .addClass("alert-info")
        .text("Advanced Import is ready. Upload the corrected CSV again, then choose the header row and map the columns before importing.")
        .show();

    var target = advancedDetails.length ? advancedDetails : $("#upload_csv_form");
    if (target.length) {
        $("html, body").animate({ scrollTop: target.offset().top - 90 }, 250);
    }
}

function gainzImportWarningDecisionLabel(decision) {
    return {
        true_zero_value_transfer: "Own wallet/account transfer",
        needs_manual_usd_value: "Sold, spent, or paid to someone",
        unknown_needs_research: "I do not know yet",
        ignore_for_now: "Leave unresolved for draft only",
        note: "Add note"
    }[decision] || "Save";
}

function gainzBuildImportWarningRepairActions(row) {
    var wrapper = $('<div class="guided-review-secondary-actions import-warning-repair-actions" role="group" aria-label="Import warning repair actions"></div>');
    var sourcePath = row.source_path || "";
    var sourceName = row.source || "this source";

    wrapper.append(
        $('<button type="button" class="btn btn-sm btn-outline-secondary import-warning-source-path-button">Show source path</button>')
            .data("source-path", sourcePath)
            .data("source-name", sourceName)
    );
    wrapper.append(
        $('<button type="button" class="btn btn-sm btn-outline-primary import-warning-open-advanced-button">Open Advanced Import / Column Mapping</button>')
    );
    wrapper.append(
        $('<button type="button" class="btn btn-sm btn-outline-danger import-warning-remove-source-button">Remove this source and re-import</button>')
            .data("source", sourcePath)
            .data("source-name", sourceName)
            .prop("disabled", !sourcePath)
    );

    return wrapper;
}

function gainzRemoveImportSourceForReimport(button) {
    var table = $("#import_data_sources_table");
    var removeUrl = table.data("remove-url");
    var source = button.data("source");
    var sourceName = button.data("source-name") || "this source";
    var resultBox = $("#data_source_action_result");

    if (!removeUrl || !source) {
        $("#import_upload_result")
            .removeClass("alert-info alert-warning")
            .addClass("alert-danger")
            .text("Gainz could not locate the exact source path for this warning. Open Review sources and remove the source there.")
            .show();
        return;
    }

    gainzConfirmDialog({
        title: "Remove source before re-import?",
        message: [
            "Remove " + sourceName + " from the current data set so you can re-import it with Advanced Import?",
            "",
            "Gainz will save a new revision. Prior revisions stay available in History.",
            "The original CSV file will not be deleted from disk."
        ].join("\n"),
        confirmText: "Remove Source",
        onConfirm: function() {
            button.prop("disabled", true).text("Removing...");
            resultBox
                .removeClass("alert-danger alert-info alert-success")
                .addClass("alert-info")
                .text("Removing the source, saving a revision, and preparing Advanced Import...")
                .show();

            $.ajax({
                url: removeUrl,
                method: "POST",
                contentType: "application/json",
                data: JSON.stringify({ source: source })
            }).done(function(result) {
                resultBox
                    .removeClass("alert-info alert-danger")
                    .addClass("alert-success")
                    .text(result.message || "Data source removed. Re-import it with Advanced Import.");

                if (result.data_summary) {
                    gainzSetSourceOverlapWorkflow(result.data_summary.source_overlaps || []);
                    gainzRenderDataSources(result.data_summary);
                    gainzSetImportWarningWorkflow(
                        "#import_warning_workflow",
                        "#import_warning_workflow_table",
                        result.data_summary.import_warnings || [],
                        result.data_summary.import_warning_rows || [],
                        result.data_summary.unresolved_import_warning_rows || []
                    );
                    gainzUpdateImportContinuePanel(result.data_summary);
                    gainzUpdateImportCurrentDecision(result.data_summary);
                }

                gainzOpenAdvancedImport();
            }).fail(function(xhr) {
                var message = "Could not remove that data source.";
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    message += " " + xhr.responseJSON.error;
                }
                resultBox
                    .removeClass("alert-info alert-success")
                    .addClass("alert-danger")
                    .text(message)
                    .show();
            }).always(function() {
                button.prop("disabled", false).text("Remove this source and re-import");
            });
        }
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
    var nextAction = "Open the source file and check row " + row + " plus the relevant mapped columns. If the row or column mapping is wrong, remove this source and re-import using Advanced Import. If it belongs in Gainz but the source cannot be fixed, add a source-backed manual transaction.";

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
        nextAction = "Open the source file and check row " + row + " and the USD spot/total USD value column. If the row has a USD value or the wrong column was mapped, remove this source and re-import using Advanced Import with the correct USD spot price or total USD value column. If the row was truly zero-value, keep documentation with the source file.";
    } else if (lower.indexOf("unrecognized transaction type") !== -1) {
        var typeMatch = raw.match(/unrecognized transaction type '([^']+)'/i);
        issue = "Unrecognized transaction type: " + (typeMatch ? typeMatch[1] : "unknown");
        status = "Classification review";
        nextAction = "Open the source file and check row " + row + " plus the type, asset, quantity, and USD columns. If the row should be imported, remove this source and re-import using Advanced Import, or add a source-backed manual transaction.";
    } else if (lower.indexOf("could not identify required columns") !== -1) {
        issue = "Required columns were not identified";
        status = "Mapping needed";
        nextAction = "Open the source file, confirm the header row and the date, type, asset, quantity, and USD value columns, then re-import using Advanced Import.";
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
        source_path: "",
        card_title: "Gainz found an import row that needs review",
        summary: "Review the source row and decide whether this is a missing value, a row that should be imported differently, or a research item.",
        question: "What should happen with this row?",
        decision_options: [
            { decision: "needs_manual_usd_value", label: "This needs a corrected value", style: "primary" },
            { decision: "unknown_needs_research", label: "I do not know yet", style: "secondary" },
            { decision: "ignore_for_now", label: "Leave unresolved for draft only", style: "quiet" }
        ],
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
        actionCell.append(gainzBuildImportWarningRepairActions(row));
        actionCell.append($('<div class="import-warning-source-path-display alert alert-light mt-2" role="status" style="display: none;"></div>'));

        if (reviewUrl) {
            var noteInput = $('<input type="text" class="form-control form-control-sm import-warning-note-input" placeholder="Add note">')
                .val(row.review_note || "");
            actionCell.append(noteInput);
            (row.decision_options || [
                { decision: "true_zero_value_transfer", label: "This went to my own wallet/account", style: "primary" },
                { decision: "needs_manual_usd_value", label: "This was sold, spent, or paid to someone", style: "secondary" },
                { decision: "unknown_needs_research", label: "I do not know yet", style: "secondary" },
                { decision: "ignore_for_now", label: "Leave unresolved for draft only", style: "quiet" }
            ]).forEach(function(action) {
                var button = $('<button type="button" class="btn btn-sm btn-outline-primary import-warning-decision-button"></button>')
                    .text(action.label)
                    .data("decision", action.decision)
                    .data("warning", row.raw || "");
                actionCell.append(button);
            });
            actionCell.append(
                $('<button type="button" class="btn btn-sm btn-outline-secondary import-warning-decision-button">Add note</button>')
                    .data("decision", "note")
                    .data("warning", row.raw || "")
            );
        }

        tableRow.append(actionCell);
        tbody.append(tableRow);
    });
}

function gainzImportWarningOptionClass(option) {
    if (option.style == "primary") {
        return "btn-primary";
    }
    if (option.style == "quiet") {
        return "btn-outline-secondary";
    }
    return "btn-outline-primary";
}

function gainzBuildImportWarningDecisionActions(row) {
    var decisionActions = $('<div class="guided-review-actions mt-2" role="group" aria-label="Import warning decisions"></div>');
    var options = row.decision_options || [
        { decision: "true_zero_value_transfer", label: "This went to my own wallet/account", style: "primary" },
        { decision: "needs_manual_usd_value", label: "This was sold, spent, or paid to someone", style: "secondary" },
        { decision: "unknown_needs_research", label: "I do not know yet", style: "secondary" },
        { decision: "ignore_for_now", label: "Leave unresolved for draft only", style: "quiet" }
    ];

    options.forEach(function(option) {
        decisionActions.append(
            $('<button type="button" class="btn btn-sm import-warning-decision-button"></button>')
                .addClass(gainzImportWarningOptionClass(option))
                .text(option.label)
                .data("decision", option.decision)
                .data("warning", row.raw || "")
        );
    });
    decisionActions.append(
        $('<button type="button" class="btn btn-sm btn-outline-secondary import-warning-show-repair-button">The CSV imported incorrectly</button>')
    );

    return decisionActions;
}

function gainzBuildImportWarningDisclosure(row) {
    var sourceDetails = $('<details class="gainz-advanced-details mt-3 import-warning-source-details"></details>');
    sourceDetails.append($('<summary>Show source path</summary>'));
    sourceDetails.append(
        $('<div class="gainz-import-detail-body"></div>')
            .append(
                $('<button type="button" class="btn btn-sm btn-outline-secondary import-warning-source-path-button">Show source path</button>')
                    .data("source-path", row.source_path || "")
                    .data("source-name", row.source || "this source")
            )
            .append($('<div class="import-warning-source-path-display alert alert-light mt-2" role="status" style="display: none;"></div>'))
    );

    var repairDetails = $('<details class="gainz-advanced-details mt-3 import-warning-repair-details"></details>');
    repairDetails.append($('<summary>Advanced import repair</summary>'));
    repairDetails.append(
        $('<div class="gainz-import-detail-body"></div>')
            .append($('<p class="mb-2"></p>').text("Use this only if the CSV row or column mapping appears wrong."))
            .append(gainzBuildImportWarningRepairActions(row))
            .append($('<a class="btn btn-sm btn-outline-primary ml-2" href="#manual-transactions">Add manual rows</a>'))
            .append($('<a class="btn btn-sm btn-outline-primary ml-2" href="#source-review">Review sources</a>'))
    );

    return $('<div></div>').append(sourceDetails).append(repairDetails);
}

function gainzRenderFirstImportWarning(panelSelector, rows, options) {
    var panel = $(panelSelector);
    options = options || {};

    if (panel.length === 0) {
        return;
    }

    panel.empty();
    if (!rows || rows.length === 0) {
        if (options.recordedDecisionLabel) {
            panel
                .append(
                    $('<div class="alert alert-success mb-0" role="status"></div>')
                        .text("Decision recorded: " + options.recordedDecisionLabel + ". All import warnings are reviewed.")
                )
                .show();
            return;
        }
        panel.hide();
        return;
    }

    var row = rows[0];
    var hasDecision = !!row.decision;
    var title = hasDecision
        ? "Current warning: " + (row.review_status || row.status || "Needs review")
        : (row.card_title || "First warning to review");
    var details = $('<dl class="guided-review-details"></dl>');
    [
        ["Source", row.source || "Current import"],
        ["Row", row.row || "N/A"],
        ["Transaction", row.raw_row_type || row.row_type || "N/A"],
        ["Amount", (row.quantity || "N/A") + (row.asset ? " " + row.asset : "")],
        ["USD amount", row.raw_usd_amount || "$0"],
        ["Note", row.notes || "N/A"],
        ["Decision", (row.decision_label || "Not reviewed") + (row.review_note ? ": " + row.review_note : "")]
    ].forEach(function(item) {
        details.append(
            $("<div></div>")
                .append($("<dt></dt>").text(item[0]))
                .append($("<dd></dd>").text(item[1]))
        );
    });

    if (options.recordedDecisionLabel) {
        panel.append(
            $('<div class="alert alert-success" role="status"></div>')
                .text("Decision recorded: " + options.recordedDecisionLabel + ". " + (hasDecision ? "This warning still needs follow-up before reports are ready." : "Showing the next unresolved warning."))
        );
    }

    if (hasDecision) {
        panel.append(
            $('<div class="alert alert-warning" role="status"></div>')
                .text("A review decision is recorded, but this warning still blocks filing-ready output until the source row is fixed, documented, or sent for research.")
        );
    }

    panel
        .append($("<h3></h3>").text(title))
        .append($("<p></p>").text(row.summary || "Review this row before using generated reports."))
        .append(details)
        .append(row.nearby_summary ? $('<div class="alert alert-light" role="status"></div>').text(row.nearby_summary) : $())
        .append($('<p class="import-warning-question"></p>').append($("<strong></strong>").text(row.question || "What happened?")))
        .append(gainzBuildImportWarningDecisionActions(row))
        .append(
            $('<input type="text" class="form-control form-control-sm import-warning-note-input mt-3" placeholder="Optional note">')
                .val(row.review_note || "")
        )
        .append(gainzBuildImportWarningDisclosure(row))
        .show();
}

function gainzSetImportWarningWorkflow(panelSelector, tableSelector, warnings, warningRows, unresolvedWarningRows, options) {
    var rows = gainzNormalizeImportWarningRows(warnings, warningRows);
    options = options || {};
    var queueRows = (
        unresolvedWarningRows && unresolvedWarningRows.length > 0
            ? unresolvedWarningRows
            : rows.filter(function(row) { return !row.is_resolved; })
    );
    var panel = $(panelSelector);

    if (panel.length === 0) {
        return;
    }

    if (queueRows.length > 0) {
        gainzRenderFirstImportWarning("#import_warning_first_panel", queueRows, options);
        gainzRenderImportWarningTable(tableSelector, rows);
        panel.show();
    } else {
        gainzRenderImportWarningTable(tableSelector, rows);
        if (options.recordedDecisionLabel) {
            gainzRenderFirstImportWarning("#import_warning_first_panel", [], options);
            panel.show();
        } else {
            gainzRenderFirstImportWarning("#import_warning_first_panel", []);
            panel.hide();
        }
    }
}

$(document).on("click", ".import-warning-decision-button", function() {
    var button = $(this);
    var reviewContext = button.closest("[data-review-url]");
    var noteContext = button.closest("td, .guided-review-panel");
    var reviewUrl = reviewContext.data("review-url");
    var note = noteContext.find(".import-warning-note-input").val() || "";

    if (!reviewUrl) {
        return;
    }

    button.prop("disabled", true).text("Saving...");
    var decisionLabel = gainzImportWarningDecisionLabel(button.data("decision"));
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
                    data.data_summary.import_warning_rows || [],
                    data.data_summary.unresolved_import_warning_rows || [],
                    { recordedDecisionLabel: decisionLabel }
                );
                gainzUpdateImportContinuePanel(data.data_summary);
                gainzUpdateImportCurrentDecision(data.data_summary);
                var unresolvedCount = data.data_summary.unresolved_import_warning_count || 0;
                var savedMessage = unresolvedCount > 0
                    ? (data.message || "Import warning review decision saved.") + " " + unresolvedCount + " unresolved warning" + (unresolvedCount == 1 ? " remains." : "s remain.")
                    : "All import warnings are reviewed. Continue to Declare Holdings when your source data is loaded.";
                $("#import_upload_result")
                    .removeClass("alert-info alert-danger alert-warning")
                    .addClass(unresolvedCount > 0 ? "alert-warning" : "alert-success")
                    .text(savedMessage)
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
            button.prop("disabled", false).text(gainzImportWarningDecisionLabel(button.data("decision")));
        }
    });
});

$(document).on("click", ".import-warning-source-path-button", function() {
    var button = $(this);
    var display = button.closest("td, .guided-review-panel").find(".import-warning-source-path-display").first();
    var sourcePath = button.data("source-path");
    var sourceName = button.data("source-name") || "this source";

    if (!display.length) {
        return;
    }

    if (sourcePath) {
        display.text("Source path for " + sourceName + ": " + sourcePath);
    } else {
        display.text("Gainz only has the source filename for this warning. Open Review sources to find the exact source path, or re-import the CSV with Advanced Import.");
    }
    display.show();
});

$(document).on("click", ".import-warning-open-advanced-button", function() {
    gainzOpenAdvancedImport();
});

$(document).on("click", ".import-warning-show-repair-button", function() {
    var panel = $(this).closest(".guided-review-panel");
    var repairDetails = panel.find(".import-warning-repair-details").first();
    if (repairDetails.length) {
        repairDetails.prop("open", true);
        $("html, body").animate({ scrollTop: repairDetails.offset().top - 90 }, 250);
    }
});

$(document).on("click", ".import-warning-remove-source-button", function() {
    gainzRemoveImportSourceForReimport($(this));
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

        gainzConfirmDialog({
            title: "Remove data source?",
            message: confirmation,
            confirmText: "Remove Source",
            onConfirm: function() {
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
            }
        });
    });
});

// Holdings reconciliation
$(document).ready(function() {
    if ($('#eh_stats_datatable').length == 0) {
        return;
    }

    var holdingsDifferenceYearlyTable = null;
    var holdingsDifferenceTransactionsTable = null;
    var holdingsClassificationReviewTable = null;
    var holdingsCurrentBreakdown = null;
    var holdingsContext = $('#holdings_page_context');
    var holdingsIsGuided = String(holdingsContext.data('guided-mode')) == '1';
    var holdingsMode = String(holdingsContext.data('holdings-mode') || 'full');
    var activeHoldingsFilter = 'all';

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

    function holdingsDifferenceForRow(rowData) {
        if (!rowData) {
            return null;
        }

        var buys = holdingsParseQuantity(rowData[1]) || 0;
        var sells = holdingsParseQuantity(rowData[2]) || 0;
        var holdings = holdingsParseQuantity(rowData[8]);
        return holdings === null ? null : (buys - sells) - holdings;
    }

    function holdingsStatusLabel(status) {
        if (status == 'needs') {
            return 'Needs holdings';
        }
        if (status == 'matched') {
            return 'Verified';
        }
        if (status == 'unlinked') {
            return 'Unlinked sales';
        }
        if (status == 'mismatch') {
            return 'Needs Review';
        }
        return 'Review';
    }

    function holdingsActionForRow(rowData) {
        var status = holdingsRowStatus(rowData);
        var asset = rowData ? rowData[0] : 'asset';

        if (status == 'needs') {
            return 'Enter what you currently hold for ' + asset + '.';
        }
        if (status == 'unlinked') {
            return 'Review missing basis links before using reports.';
        }
        if (status == 'mismatch') {
            return 'Investigate the holdings gap and document the next decision.';
        }
        if (status == 'matched') {
            return 'Verified in Gainz. Review supporting records when exporting.';
        }
        return 'Select this asset to continue.';
    }

    function holdingsFilterMatches(rowData, filterName) {
        var status = holdingsRowStatus(rowData);

        if (filterName == 'all') {
            return true;
        }
        if (filterName == 'review') {
            return status == 'mismatch' || status == 'unlinked';
        }
        return status == filterName;
    }

    function holdingsGuidedEligibleRows() {
        var rows = [];
        if (!holdingsIsGuided) {
            return rows;
        }

        table.rows().every(function() {
            var rowData = this.data();
            if (!rowData) {
                return;
            }

            if (holdingsMode == 'reconcile') {
                if (holdingsFilterMatches(rowData, 'review')) {
                    rows.push(rowData);
                }
                return;
            }

            if (holdingsFilterMatches(rowData, activeHoldingsFilter)) {
                rows.push(rowData);
            }
        });

        return rows;
    }

    function holdingsUpdateGuidedCards() {
        if (!holdingsIsGuided || $('#holdings_guided_asset_cards').length == 0) {
            return;
        }

        var selectedRow = holdingsSelectedAssetRow();
        var selectedAsset = selectedRow ? selectedRow[0] : '';
        var eligibleRows = holdingsGuidedEligibleRows();
        var eligibleAssets = eligibleRows.map(function(rowData) { return rowData[0]; });

        $('.holdings-asset-card').each(function() {
            var card = $(this);
            var asset = String(card.data('asset') || '');
            var rowData = null;
            table.rows().every(function() {
                var candidate = this.data();
                if (candidate && candidate[0] == asset) {
                    rowData = candidate;
                }
            });

            if (!rowData) {
                card.hide();
                return;
            }

            var status = holdingsRowStatus(rowData);
            var statusClassSource = status == 'needs' ? 'Needs declared holdings' : holdingsStatusLabel(status);
            var difference = holdingsDifferenceForRow(rowData);
            var isEligible = eligibleAssets.indexOf(asset) >= 0;
            var isActive = selectedAsset == asset;
            var showCard = holdingsMode == 'reconcile' ? isActive : isEligible;

            card
                .toggle(showCard)
                .toggleClass('active', isActive)
                .attr('aria-pressed', isActive ? 'true' : 'false');
            card.find('[data-card-status]')
                .removeClass('status-matched status-verified status-needs-declared-holdings status-mismatch status-needs-review status-unlinked-sales status-needs-user-research')
                .addClass(holdingsStatusClass(statusClassSource))
                .text(holdingsStatusLabel(status));
            card.find('[data-card-action]').text(holdingsActionForRow(rowData));
            card.find('[data-card-holdings]').text(holdingsParseQuantity(rowData[8]) === null ? 'Not entered' : holdingsFormatQuantity(holdingsParseQuantity(rowData[8])));
            card.find('[data-card-unlinked]').text(holdingsFormatQuantity(holdingsParseQuantity(rowData[3]) || 0));
            card.find('[data-card-difference]').text(difference === null ? '--' : holdingsFormatQuantity(difference));
        });

        var activeIndex = eligibleAssets.indexOf(selectedAsset);
        var empty = eligibleRows.length == 0;
        $('#holdings_guided_queue_empty').toggle(empty);
        $('#holdings_guided_asset_cards, .holdings-guided-queue-actions').toggle(!empty);

        if (holdingsMode == 'reconcile') {
            $('#holdings_guided_queue_title').text('Current gap');
            $('#holdings_guided_queue_status').text(empty ? 'No current gaps need review.' : 'Gap ' + (activeIndex + 1) + ' of ' + eligibleRows.length + '. Review this one before moving on.');
            $('#holdings_guided_prev_asset').prop('disabled', activeIndex <= 0);
            $('#holdings_guided_next_asset').prop('disabled', activeIndex < 0 || activeIndex >= eligibleRows.length - 1);
        } else {
            $('#holdings_guided_queue_title').text('Asset cards');
            $('#holdings_guided_queue_status').text(empty ? 'No assets match this filter.' : eligibleRows.length + ' asset' + (eligibleRows.length == 1 ? '' : 's') + ' shown for this step.');
            $('.holdings-guided-queue-actions').hide();
        }
    }

    function holdingsRowsSet(rows) {
        if (!rows) {
            return;
        }

        table.clear();
        table.rows.add(rows).draw();
        holdingsUpdateGuidedCards();
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

        holdingsUpdateGuidedCards();
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

    function holdingsSetContextualActions(rowData, context) {
        context = context || {};
        var selected = !!rowData;
        var soldUnlinked = context.soldUnlinked || 0;
        var difference = context.difference;
        var declaredHoldings = context.declaredHoldings;
        var tolerance = 0.00000001;
        var actionButtons = $('#holdings_run_fifo_button, #holdings_leave_basis_unresolved_button, #sends_to_sells_button, #classify_sends_fifo_button, #buys_to_lost_button');

        actionButtons
            .prop('disabled', true)
            .hide();
        $('#convert_quantity').prop('disabled', !selected);
        $('#basis_review_note').prop('disabled', !selected);

        if (!selected) {
            $('#holdings_contextual_action_hint')
                .removeClass('alert-success alert-warning alert-info')
                .addClass('alert-light')
                .text('Pick a gap to see the supported actions for that exact issue.');
            return;
        }

        if (declaredHoldings === null) {
            $('#holdings_contextual_action_hint')
                .removeClass('alert-success alert-warning alert-light')
                .addClass('alert-info')
                .text('Declare current holdings first. Gainz needs that before it can decide whether this asset has a real gap.');
            return;
        }

        if (soldUnlinked > tolerance) {
            $('#holdings_run_fifo_button, #holdings_leave_basis_unresolved_button').prop('disabled', false).show();
            $('#holdings_contextual_action_hint')
                .removeClass('alert-success alert-light alert-info')
                .addClass('alert-warning')
                .text('This asset has sales without complete basis. Start with FIFO Auto Link, or leave missing basis as needs research if records are not available yet.');
            return;
        }

        if (difference !== null && Math.abs(difference) > tolerance) {
            $('#holdings_leave_basis_unresolved_button').prop('disabled', false).show();
            if (difference > 0) {
                $('#sends_to_sells_button, #classify_sends_fifo_button').prop('disabled', false).show();
                $('#holdings_contextual_action_hint')
                    .removeClass('alert-success alert-light alert-info')
                    .addClass('alert-warning')
                    .text('Imported buys/sells imply more than you declared. Review sends or missing disposals; only classify documented sends when records support it.');
            } else {
                $('#buys_to_lost_button').prop('disabled', false).show();
                $('#holdings_contextual_action_hint')
                    .removeClass('alert-success alert-light alert-info')
                    .addClass('alert-warning')
                    .text('Declared holdings are higher than imported activity explains. Look for missing acquisitions, income, gifts, or transfer records; document uncertainty if needed.');
            }
            return;
        }

        $('#holdings_contextual_action_hint')
            .removeClass('alert-warning alert-light alert-info')
            .addClass('alert-success')
            .text('This asset is currently verified in Gainz. Move to the next gap or open Reports & Export.');
    }

    function holdingsRenderReadiness(rowData, precheckData) {
        if (!rowData) {
            $('#holdings_readiness_asset, #holdings_readiness_holdings, #holdings_readiness_unlinked, #holdings_readiness_difference').text('--');
            $('#holdings_run_fifo_button').prop('disabled', true).text('Run FIFO Auto Link for Selected Asset');
            $('#holdings_leave_basis_unresolved_button').prop('disabled', true);
            holdingsSetContextualActions(null);
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
        holdingsSetContextualActions(rowData, {
            soldUnlinked: soldUnlinked,
            difference: difference,
            declaredHoldings: declaredHoldings
        });

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
        $('#zero_holdings_confirm_panel').hide();
        holdingsRenderSelection(rowData);

        if (!rowData) {
            $('#auto_actions_datatable').DataTable().clear().draw();
            holdingsClearDifferenceBreakdown();
            holdingsRenderReadiness(null, null);
            holdingsUpdateGuidedCards();
            return;
        }

        holdingsRenderReadiness(rowData, null);
        holdingsLoadDifferenceBreakdown(rowData);
        holdingsLoadPrecheck(rowData);
        holdingsUpdateGuidedCards();
    }

    function holdingsRenderSelection(rowData) {
        if (!rowData) {
            $('#holdings_workbench_title').text(holdingsIsGuided ? (holdingsMode == 'reconcile' ? 'Current Gap' : 'Current Asset') : 'Asset Workbench');
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

        $('#holdings_workbench_title').text(holdingsIsGuided ? asset : asset + ' Workbench');
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

    var table = $('#eh_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $.fn.dataTable.ext.search.push(function(settings, rowData) {
        if (settings.nTable.id !== 'eh_stats_datatable') {
            return true;
        }

        return holdingsFilterMatches(rowData, activeHoldingsFilter);
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
            },
            review: {
                message: 'Showing one review gap at a time. Work the selected asset, then move to the next gap.',
                scroll: '#holdings_guided_queue'
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
                holdingsScrollTo(holdingsIsGuided ? '#holdings_guided_queue' : '#holdings_selected_asset');
            }
        } else {
            table.rows().deselect();
            holdingsLoadRow(null);
            if (!options.skipScroll) {
                holdingsScrollTo(label.scroll);
            }
        }
        holdingsUpdateGuidedCards();
    }

    $('.holdings-progress-action').on('click', function() {
        holdingsApplySummaryFilter($(this).data('holdings-filter'));
    });

    $('#eh_stats_datatable tbody').on( 'click', 'tr', function () {
        holdingsLoadRow(table.row(this).data());
    });

    $('#holdings_guided_asset_cards').on('click', '.holdings-asset-card', function() {
        var asset = $(this).data('asset');
        var rowData = holdingsSelectAsset(asset);
        holdingsLoadRow(rowData);
        holdingsScrollTo('#holdings_selected_asset');
    });

    function holdingsMoveGuidedQueue(delta) {
        var rows = holdingsGuidedEligibleRows();
        if (rows.length == 0) {
            return;
        }

        var selectedRow = holdingsSelectedAssetRow();
        var selectedAsset = selectedRow ? selectedRow[0] : '';
        var currentIndex = rows.findIndex(function(rowData) { return rowData[0] == selectedAsset; });
        if (currentIndex < 0) {
            currentIndex = 0;
        }

        var nextIndex = Math.min(Math.max(currentIndex + delta, 0), rows.length - 1);
        var nextRow = rows[nextIndex];
        holdingsSelectAsset(nextRow[0]);
        holdingsLoadRow(nextRow);
        holdingsScrollTo('#holdings_guided_queue');
    }

    $('#holdings_guided_prev_asset').on('click', function() {
        holdingsMoveGuidedQueue(-1);
    });

    $('#holdings_guided_next_asset').on('click', function() {
        holdingsMoveGuidedQueue(1);
    });

    $(document).on('click', '#holdings_next_gap_button', function() {
        holdingsMoveGuidedQueue(1);
    });

    function holdingsShowDeclaredCompletion(summaryText) {
        if (!holdingsIsGuided || holdingsMode != 'declare') {
            return;
        }

        $('#holdings_stage_callout').hide();
        $('#holdings_completion_summary').text(summaryText || 'All tracked assets now have declared current holdings for this review pass.');
        $('#holdings_completion_actions').html(
            '<a class="btn btn-sm btn-primary" href="/holdings_accounting/?guided=1&amp;mode=reconcile">Continue to Reconcile Gaps</a> ' +
            '<button type="button" id="holdings_edit_after_completion" class="btn btn-sm btn-outline-secondary">Edit declared holdings</button>'
        );
        $('#holdings_completion_panel').show();
    }

    $(document).on('click', '#holdings_edit_after_completion', function() {
        $('#holdings_completion_panel').hide();
        $('#holdings_stage_callout').show();
        holdingsScrollTo('#holdings_guided_queue');
    });

    var initialHoldingsFilter = holdingsIsGuided && holdingsMode == 'declare'
        ? 'needs'
        : (holdingsIsGuided && holdingsMode == 'reconcile' ? 'review' : 'all');
    holdingsApplySummaryFilter(initialHoldingsFilter, { skipScroll: true });

    function holdingsAutoAdvanceAfterDeclare(savedAsset) {
        if (!holdingsIsGuided || holdingsMode != 'declare') {
            return false;
        }

        activeHoldingsFilter = 'needs';
        table.search('').draw();
        var remainingRows = [];
        table.rows().every(function() {
            var rowData = this.data();
            if (rowData && rowData[0] != savedAsset && holdingsRowStatus(rowData) == 'needs') {
                remainingRows.push(rowData);
            }
        });

        if (remainingRows.length > 0) {
            var nextRow = remainingRows[0];
            holdingsSelectAsset(nextRow[0]);
            holdingsLoadRow(nextRow);
            $('#holdings_save_message')
                .removeClass('alert-warning')
                .addClass('alert-success')
                .text('Declared holdings for ' + savedAsset + ' saved. Next: ' + nextRow[0] + ' is ready for holdings entry.')
                .show();
            holdingsScrollTo('#holdings_selected_asset');
            return true;
        }

        table.rows().deselect();
        holdingsLoadRow(null);
        holdingsUpdateGuidedCards();
        $('#holdings_guided_queue_empty')
            .removeClass('alert-success')
            .addClass('alert-info')
            .html('All listed assets now have declared holdings. <a href="/holdings_accounting/?guided=1&amp;mode=reconcile">Continue to Reconcile Gaps</a>.')
            .show();
        holdingsShowDeclaredCompletion('Declared holdings for ' + savedAsset + ' saved. All listed assets now have declared holdings.');
        holdingsScrollTo('#holdings_guided_queue');
        return true;
    }

    function holdingsRefreshBulkRows() {
        var rows = $('.bulk-holdings-row');
        rows.find('.bulk-remove-holding-row').prop('disabled', rows.length <= 1);
        $('#bulk_set_non_primary_zero_button').text('Save These Holdings And Set The Rest To 0');
    }

    function holdingsNewBulkRow(index) {
        return $(
            '<div class="bulk-holdings-row">' +
                '<div>' +
                    '<label for="bulk_holding_asset_' + index + '">Asset</label>' +
                    '<input id="bulk_holding_asset_' + index + '" class="form-control text-uppercase bulk-holdings-asset" placeholder="ETH">' +
                '</div>' +
                '<div>' +
                    '<label for="bulk_holding_quantity_' + index + '">Current holdings</label>' +
                    '<input id="bulk_holding_quantity_' + index + '" type="number" step="any" min="0" class="form-control bulk-holdings-quantity" placeholder="0.00000000">' +
                '</div>' +
                '<div class="bulk-holdings-row-actions">' +
                    '<button type="button" class="btn btn-outline-secondary bulk-remove-holding-row">Remove</button>' +
                '</div>' +
            '</div>'
        );
    }

    function holdingsCollectBulkRows() {
        var rows = [];
        var seenAssets = {};
        var error = '';

        $('.bulk-holdings-row').each(function(index) {
            var rowNumber = index + 1;
            var assetInput = $(this).find('.bulk-holdings-asset');
            var quantityInput = $(this).find('.bulk-holdings-quantity');
            var asset = String(assetInput.val() || '').trim().toUpperCase();
            var quantity = quantityInput.val();

            assetInput.val(asset);

            if (!asset && !quantity) {
                return;
            }

            if (!asset) {
                error = 'Enter an asset symbol for row ' + rowNumber + '.';
                return false;
            }

            if (!quantity && quantity !== '0') {
                error = 'Enter the current holdings quantity for ' + asset + '.';
                return false;
            }

            if (seenAssets[asset]) {
                error = asset + ' appears more than once. Combine duplicate rows before saving.';
                return false;
            }

            var parsedQuantity = Number(quantity);
            if (!Number.isFinite(parsedQuantity) || parsedQuantity < 0) {
                error = 'Enter a valid non-negative current holdings quantity for ' + asset + '.';
                return false;
            }

            seenAssets[asset] = true;
            rows.push({
                asset: asset,
                quantity: quantity
            });
        });

        if (!error && rows.length == 0) {
            error = 'Enter at least one current holding before saving.';
        }

        return {
            rows: rows,
            error: error
        };
    }

    function holdingsDescribeBulkRows(rows) {
        return rows.map(function(row) {
            return row.asset + ' ' + row.quantity;
        }).join(', ');
    }

    $('#bulk_add_holding_row_button').click(function() {
        var index = $('.bulk-holdings-row').length + 1;
        $('#bulk_holdings_rows').append(holdingsNewBulkRow(index));
        holdingsRefreshBulkRows();
        $('#bulk_holdings_rows .bulk-holdings-row:last .bulk-holdings-asset').focus();
    });

    $('#bulk_holdings_rows').on('click', '.bulk-remove-holding-row', function() {
        if ($('.bulk-holdings-row').length <= 1) {
            return;
        }
        $(this).closest('.bulk-holdings-row').remove();
        holdingsRefreshBulkRows();
    });

    $('#bulk_holdings_rows').on('blur', '.bulk-holdings-asset', function() {
        $(this).val(String($(this).val() || '').trim().toUpperCase());
    });

    holdingsRefreshBulkRows();

    function holdingsSaveBulkHoldings(holdingsRows) {
        var button = $('#bulk_set_non_primary_zero_button');
        var startedAt = Date.now();
        button.prop('disabled', true).text('Saving revision...');
        $('#bulk_holdings_confirm_panel').hide();
        $('#bulk_holdings_message')
            .removeClass('alert-success alert-warning')
            .addClass('alert-info')
            .text('Saving current holdings, recalculating reconciliation, and writing a new revision. Large data sets may take 10-30 seconds; keep this tab open.')
            .show();

        $.ajax({
            type: "POST",
            url: "/holdings_accounting/bulk_holdings",
            data: JSON.stringify({
                'holdings': holdingsRows
            }),
            dataType: "json",
            contentType: 'application/json',
            success: function(data) {
                holdingsRowsSet(data['stats_table_rows']);
                holdingsSetSummary(data['holdings_summary']);
                var updatedRow = holdingsSelectAsset(data['primary_asset']);
                holdingsLoadRow(updatedRow);
                $('#bulk_holdings_message')
                    .removeClass('alert-info alert-warning')
                    .addClass('alert-success')
                    .html(
                        '<strong>Bulk holdings saved.</strong> ' +
                        $('<span></span>').text(data['message'] + ' Completed in ' + Math.max(1, Math.round((Date.now() - startedAt) / 1000)) + ' second(s).').html() +
                        ' <a class="btn btn-sm btn-primary ml-2" href="/holdings_accounting/?guided=1&amp;mode=reconcile">Continue to Reconcile Gaps</a>'
                    )
                    .show();
                holdingsShowDeclaredCompletion(data['message']);
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
                holdingsRefreshBulkRows();
                button.prop('disabled', false);
            },
        });
    }

    $('#bulk_set_non_primary_zero_button').click(function() {
        var collected = holdingsCollectBulkRows();

        if (collected.error) {
            $('#bulk_holdings_message')
                .removeClass('alert-info alert-success')
                .addClass('alert-warning')
                .text(collected.error)
                .show();
            return;
        }

        $('#bulk_holdings_confirm_text').text('Save current holdings as ' + holdingsDescribeBulkRows(collected.rows) + ' and set every other tracked asset to 0?');
        $('#bulk_holdings_confirm_panel')
            .data('holdings-rows', collected.rows)
            .show();
        holdingsScrollTo('#bulk_holdings_confirm_panel');
    });

    $('#bulk_holdings_confirm_no').click(function() {
        $('#bulk_holdings_confirm_panel').hide();
    });

    $('#bulk_holdings_confirm_yes').click(function() {
        holdingsSaveBulkHoldings($('#bulk_holdings_confirm_panel').data('holdings-rows') || []);
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
                holdingsAutoAdvanceAfterDeclare(rowData[0]);
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

        $('#zero_holdings_confirm_text').text('Save declared holdings of 0 for ' + rowData[0] + '? Use this only when your records show you currently hold none of this asset.');
        $('#zero_holdings_confirm_panel').show();
        holdingsScrollTo('#zero_holdings_confirm_panel');
    });

    $("#zero_holdings_confirm_no").click(function(){
        $('#zero_holdings_confirm_panel').hide();
    });

    $("#zero_holdings_confirm_yes").click(function(){
        $('#zero_holdings_confirm_panel').hide();

        $('#holdings_quantity').val('0');
        $('#submit_holdings_button').trigger('click');
    });

    var holdingsPendingConfirmAction = null;

    function holdingsShowActionConfirm(title, message, confirmText, callback) {
        holdingsPendingConfirmAction = callback;
        $('#holdings_action_confirm_title').text(title);
        $('#holdings_action_confirm_text').text(message);
        $('#holdings_action_confirm_yes').text(confirmText || 'Continue');
        $('#holdings_action_confirm_panel').show();
        holdingsScrollTo('#holdings_action_confirm_panel');
    }

    $('#holdings_action_confirm_no').click(function() {
        holdingsPendingConfirmAction = null;
        $('#holdings_action_confirm_panel').hide();
    });

    $('#holdings_action_confirm_yes').click(function() {
        var action = holdingsPendingConfirmAction;
        holdingsPendingConfirmAction = null;
        $('#holdings_action_confirm_panel').hide();
        if (action) {
            action();
        }
    });

    function holdingsRunFifoForRow(rowData) {
        var button = $('#holdings_run_fifo_button');
        var asset = rowData ? rowData[0] : null;

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
    }

    $("#holdings_run_fifo_button").click(function(){
        var rowData = holdingsSelectedAssetRow();
        var asset = rowData ? rowData[0] : null;

        if (!rowData) {
            holdingsSetReadinessMessage('Select an asset before running FIFO Auto Link.', 'warning');
            return;
        }

        holdingsShowActionConfirm(
            'Run FIFO Auto Link?',
            'Run FIFO Auto Link for ' + asset + '? Gainz will create basis links for review and save a new revision if links are added.',
            'Run FIFO Auto Link',
            function() {
                holdingsRunFifoForRow(rowData);
            }
        );
    });

    function holdingsSaveBasisUnresolved(rowData, asset, note) {
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
                    .html(
                        '<strong>Decision recorded.</strong> ' +
                        $('<span></span>').text((data['message'] || (asset + ' left unresolved as needs user research.')) + ' This remains a draft blocker.').html() +
                        ' <button type="button" id="holdings_next_gap_button" class="btn btn-sm btn-primary ml-2">Next gap</button>' +
                        ' <a class="btn btn-sm btn-outline-primary ml-2" href="/export/review_queue?guided=1">Open Guided Review Queue</a>'
                    )
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

    function holdingsLeaveBasisUnresolved() {
        var rowData = holdingsSelectedAssetRow();
        var asset = rowData ? rowData[0] : null;
        var note = $('#basis_review_note').val();

        if (!rowData) {
            alert('Select an asset first.');
            return;
        }

        holdingsShowActionConfirm(
            'Leave gap unresolved?',
            'Leave missing basis for ' + asset + ' unresolved as needs user research? Generated exports will remain draft/not filing-ready.',
            'Leave As Needs Research',
            function() {
                holdingsSaveBasisUnresolved(rowData, asset, note);
            }
        );
    }

    $('#leave_basis_unresolved_button, #holdings_leave_basis_unresolved_button').click(function() {
        holdingsLeaveBasisUnresolved();
    });

    function holdingsSaveDocumentedSendClassification(rowData, asset, quantity) {
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

        holdingsShowActionConfirm(
            'Classify documented sends?',
            'Classify ' + quantity + ' ' + asset + ' of documented sends as disposals and run FIFO Auto Link? Owner transfers should remain transfers.',
            'Classify And Link',
            function() {
                holdingsSaveDocumentedSendClassification(rowData, asset, quantity);
            }
        );
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
        var form = $(this);
        var button = form.find('button[type="submit"]');
        var revision = button.data('revision') || 'this revision';
        var description = button.data('description') || '';
        var message = [
            'Restore revision ' + revision + ' as the latest Gainz revision?',
            '',
            description,
            '',
            'This will not delete newer saves. Gainz will create a new revision from the selected save.'
        ].join('\n');

        gainzConfirmDialog({
            title: 'Restore revision?',
            message: message,
            confirmText: 'Restore Revision',
            onConfirm: function() {
                button.prop('disabled', true).text('Restoring...');
                form.get(0).submit();
            }
        });
        return false;
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
