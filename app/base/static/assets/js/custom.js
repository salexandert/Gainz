
// HODL Accounting 
$(document).ready(function() {

    $('#auto_actions_datatable').DataTable({
        "pageLength": 25,
        "order": [[ 1, "desc" ]],
        "columnDefs": [
            { "width": "5%", "targets": 0 },
            { "width": "20%", "targets": 2},
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

    var table = $('#eh_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#eh_stats_datatable tbody').on( 'click', 'tr', function () {
        console.log( table.row( this ).data() );


        var asset = table.row( this ).data()[0]
        var buys = table.row( this ).data()[1]
        var sells = table.row( this ).data()[2]
        var sent = table.row( this ).data()[3]
        var hodl = table.row( this ).data()[8]
        
        var needs_classification = buys - sells
        var min_hodl = buys - sent
        var hodl_text = $('#eh_options').text('')
        var convert_text = $('#convert_text').text('')
        var Sold_or_Lost = buys - hodl
        var expected_hodl = buys - sells
        var hodl_difference = expected_hodl - hodl
        
        if (hodl == "N/A") {
        
            hodl_text.append(asset + ' Selected')
            hodl_text.append("<br>Buys: " + buys + " - Sells: " + sells + " = Needs_Classification: " + needs_classification)
            
            if (needs_classification < 0) { 
                hodl_text.append("<br>Looks like you have more sells than buys. You can add buys manually or import additonal from CSV.")
                
             }

            if (min_hodl >= 0) {
                hodl_text.append("<br>If Converting Sends to Sells minimum HODL is " + min_hodl)
            }

        } else {
            $("#submit_hodl_button").text("Change HODL")

            hodl_text.append(asset + ' Selected')
            hodl_text.append("<br><br>Buys " + buys + " - Sells " + sells + " = Expected HODL of " + expected_hodl)
            hodl_text.append("<br><br>Expected HODL " + expected_hodl + " - HODL" + hodl + " = a difference of " + hodl_difference)
            if (hodl_difference > 0) 
                { 
                    hodl_text.append("<br><br> Since the difference is positive it indicates you may have sold this amount on other exchanges, traded for goods or services (sold), or lost.")
                    hodl_text.append("<br> If you know what transactions are missing its best to add them on the add and manage transactions page. ")
                    hodl_text.append("<br> Otherwise you may use the options below to automatically convert the earliest sends into sells or buys into lost")
                    hodl_text.append("<br> This also many be done manually on the add and manage transactions page")
                    
                    convert_text.append("We can account for " + hodl_difference + " by converting any combination of the below. <br><br>")
                    convert_text.append(sent + " Sends to Sells <br>")
                    // convert_text.append(received + " Received to Buys <br>")
                    convert_text.append(buys + " Buys to Lost <br>")
                } 
            else {
                    hodl_text.append("<br><br> Since the difference is negative it indicates you may have acquired this amount from other sources.")
                    hodl_text.append("<br> If you know what transactions are missing its best to add them on the add and manage transactions page. ")
                    hodl_text.append("<br> Otherwise you may convert the receives into buys. This needs to be done manually on the add and manage transactions page")

                }
            
            


        }

        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_pre_check",
            data: JSON.stringify({
                'row_data': table.row( this ).data()
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                
                $('#auto_actions_datatable').DataTable().clear();
                $('#auto_actions_datatable').DataTable().rows.add(data['auto_suggestions']).draw();
            },   
        });

    });

    $("#auto_action_button").click(function(){

        var table_data = $('#auto_actions_datatable').DataTable().rows( {selected:true} ).data()

        $.ajax({
            type: "POST",
            url: "/hodl_accounting/auto_actions",
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


    $("#submit_hodl_button").click(function(){

        $.ajax({
            type: "POST",
            url: "/hodl_accounting/hodl_info",
            data: JSON.stringify({
                'quantity': $('#hodl_quantity').val(),
                'asset': $('#eh_stats_datatable').DataTable().row( {selected:true} ).data()
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                location.reload()
            },   
        });
    });

    $("#sends_to_sells_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/hodl_accounting/sends_to_sells",
            data: JSON.stringify({
                'quantity': $('#convert_quantity').val(),
                'asset': $('#eh_stats_datatable').DataTable().row( {selected:true} ).data()
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },   
        });
    });

    $("#receives_to_buys_button").click(function(){

        $.ajax({
            type: "POST",
            url: "/hodl_accounting/receive_to_buy",
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
            url: "/hodl_accounting/buys_to_lost",
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
    var table = $('#al_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
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
        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_asset",
            data: JSON.stringify({
                'algo': 'min_gain_long',
                'asset': $('#al_stats_datatable').DataTable().row( {selected:true} ).data(),
                'year': $('#auto_link_year_dropdown').find(":selected").val()
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },   
        });

    });

    $("#min_gain").click(function(){
        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_asset",
            data: JSON.stringify({
                'algo': 'min_gain',
                'asset': $('#al_stats_datatable').DataTable().row( {selected:true} ).data(),
                'year': $('#auto_link_year_dropdown').find(":selected").val()
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },   
        });

    });

    $("#link_w_fifo").click(function(){
        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_asset",
            data: JSON.stringify({
                'algo': 'fifo',
                'asset': $('#al_stats_datatable').DataTable().row( {selected:true} ).data(),
                'year': $('#auto_link_year_dropdown').find(":selected").val()
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert(data)
                location.reload()
            },   
        });

    });

    $("#link_w_filo").click(function(){
        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_asset",
            data: JSON.stringify({
                'algo': 'filo',
                'asset': $('#al_stats_datatable').DataTable().row( {selected:true} ).data(),
                'year': $('#auto_link_year_dropdown').find(":selected").val()
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

    function setStatsImportWarnings(warnings) {
        var warningList = $('#stats_import_warnings_list');
        warningList.empty();

        if (warnings && warnings.length > 0) {
            warnings.forEach(function(warning) {
                warningList.append($('<li>').text(warning));
            });
            $('#stats_import_warnings').show();
        } else {
            $('#stats_import_warnings').hide();
        }
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
            .removeClass('status-matched status-needs-declared-hodl status-mismatch status-unlinked-sales')
            .addClass(summary.reconciliation_class || statusClassName(summary.reconciliation));
        $('#stats_summary_assets_needing_hodl').text(summary.assets_needing_hodl);
        $('#stats_summary_assets_with_mismatches').text(summary.assets_with_mismatches);
        $('#stats_summary_import_warnings').text(summary.import_warnings);
        $('#stats_summary_unlinked_sales').text(summary.unlinked_sales);
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

    function chartCurrency(value) {
        return formatter.format(Number(value || 0));
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

                var declaredHodl = "N/A";
                (return_data['holdings_reconciliation_data'] || []).forEach(function(row) {
                    if (row[0] == 'Declared HODL') {
                        declaredHodl = row[1];
                    }
                });

                var selectedAsset = rowData[0];
                $('#stats_declared_hodl_quantity').attr('placeholder', 'Current holding for ' + selectedAsset);
                $('#stats_declared_hodl_quantity').val(declaredHodl == 'N/A' ? '' : declaredHodl);

                $('#s8949_table').DataTable().clear();
                $('#s8949_table').DataTable().rows.add(return_data['s8949_table_data'] || []).draw();

                $('#l8949_table').DataTable().clear();
                $('#l8949_table').DataTable().rows.add(return_data['l8949_table_data'] || []).draw();

                setStatsReconciliationWarning(return_data['reconciliation_status']);
                setStatsImportWarnings(return_data['import_warnings']);
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
                setStatsImportWarnings(data['import_warnings']);
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

    $("#stats_save_hodl_button").click(function(){
        var rowData = selectedStatsRowData || table.row( {selected:true} ).data();
        var quantity = $('#stats_declared_hodl_quantity').val();

        if (!rowData) {
            alert("Select an asset first.");
            return;
        }

        if (!quantity) {
            alert("Enter the current holding quantity first.");
            return;
        }

        $.ajax({
            type: "POST",
            url: "/stats/set_hodl",
            data: JSON.stringify({
                'asset': rowData[0],
                'quantity': quantity,
            }),
            dataType: "json",
            contentType: 'application/json',
            success: function () {
                location.reload();
            },
        });
    });


} );




// history page code
$(document).ready(function() {

    // init tables
    var table = $('#historypage_datatable').DataTable({
        select: {
            style: 'multi'
        },
    });

    $('#historypage_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });
    
    
    $('#historypage_detailed_datatable').DataTable({
        "pageLength": 50,
        select: {
            style: 'single'
        },
    });


    table.on('select', function(e, dt, type, indexes) {
        

        //If two rows are selected
        if ($('#historypage_datatable').DataTable().rows( {selected:true} ).count() == 2) {
            console.log('two rows selected')

            $.ajax({
                type: "POST",
                url: "/history/compare_selected",
                data: JSON.stringify({
                    'row_data': $('#historypage_datatable').DataTable().rows( {selected:true} ).data(),
                    }),  
    
                contentType: 'application/json',
                success: function (data) { 
                    console.log(data)
                    $('#historypage_stats_datatable').DataTable().clear();
                }

            });
    
        //If one row is selected
        } else {
            console.log('Single Row is selected')
            $.ajax({
                type: "POST",
                url: "/history/selected_save",
                data: JSON.stringify({
                    'row_data': $('#historypage_datatable').DataTable().row( {selected:true} ).data(),
                    }),  
    
                contentType: 'application/json',
                success: function (data) {
    
                    console.log(data)
                    var names = data['column_names']
    
                    // Check if the DataTable is initialized
                    if ($.fn.DataTable.isDataTable('#historypage_stats_datatable')) {
                        // Get the DataTable instance
                        var table = $('#historypage_stats_datatable').DataTable();
    
                        // Loop over the list of names
                        for (var i = 0; i < names.length; i++) {
                            // Check if the column exists
                            if (i < table.columns().count()) {
                                // Update the column title
                                table.column(i).header().innerHTML = names[i];
                            } else {
                                console.log('Column ' + i + ' does not exist');
                            }
                        }
    
                        // Redraw the table to reflect the changes
                        table.columns.adjust().draw();
                    } else {
                        console.log('DataTable is not initialized');
                    }
    
                    $('#historypage_stats_datatable').DataTable().clear();
                    $('#historypage_stats_datatable').DataTable().rows.add(data['rows']).draw();
                    
                        
                },   
            });
        }

    });

    
    $("#load_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/history/load",
            data: JSON.stringify({
                'data': $('#history_datatable').DataTable().row( {selected:true} ).data(),
                
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                location.reload()
            },   
        });
    });


    $("#revert_button").click(function(){

        $.ajax({
            type: "POST",
            url: "/history/revert",
            data: JSON.stringify({
                'data': $('#history_datatable').DataTable().row( {selected:true} ).data(),
                
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                location.reload()

            },   
        });
    });

    $("#delete_button").click(function(){

        $.ajax({
            type: "POST",
            url: "/history/delete",
            data: JSON.stringify({
                'data': $('#history_datatable').DataTable().row( {selected:true} ).data(),
                
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                location.reload()
            },   
        });
    });

    $("#save_button").click(function(){

        $.ajax({
            type: "POST",
            url: "/history/save",
            data: JSON.stringify({
                'data': $('#history_datatable').DataTable().row( {selected:true} ).data(),
                
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                location.reload()
            },   
        });
    });


} );

// export page code
$(document).ready(function() {


    $('#exportpage_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

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
        $.ajax({
            type: "POST",
            url: "/export/save",
            data: JSON.stringify({
                'data': $('#exportpage_stats_datatable').DataTable().row( {selected:true} ).data(),      
              }),  
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert("Saving Export as " + data)
            },   
        });
    });

    $("#audit_packet_button").click(function(){
        $.ajax({
            type: "POST",
            url: "/export/audit_packet",
            data: JSON.stringify({}),
            dataType: "json",
            contentType: 'application/json',
            success: function (data) {
                alert("Audit packet saved to " + data)
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


// Import Transactions Page

$(document).ready(function() {

    $('#import_datatable').DataTable({
        "pageLength": 25,
        select: {
            style: 'single'
        },
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

    


// Add and Manage Transactions Page
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
            url: "/add_transactions/add_transactions_selected_asset",
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
            url: "/add_transactions/delete_transactions",
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
            url: "/add_transactions/add_transactions_selected_asset",
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
            url: "/add_transactions/add_transactions_selected_asset",
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
            url: "/add_transactions/delete_transactions",
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
            url: "/add_transactions/buy_convert",
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
            url: "/add_transactions/receive_convert",
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
            url: "/add_transactions/send_convert",
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

    $('#model_stats_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $('#all_linkable_buys_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    var batch_data = {}

    $('#model_stats_datatable tbody').on( 'click', 'tr', function () {
        $('#model_submit').prop('disabled', false);
    });

    $('#model_submit').on('click', function () {

        $.ajax({
            type: "POST",
            url: "/model/selected_asset",
            data: JSON.stringify({
                'row_data': $('#model_stats_datatable').DataTable().row( {selected:true} ).data(),
                'usd_spot': $('#model_usd_spot').val(),
                'quantity': $('#model_quantity').val(),
                'total_in_usd': $('#total_in_usd').val()
                }),  

            contentType: 'application/json',
            success: function (data) {

                console.log(data)

                batch_data = data

                $('#model_batch_options').children().remove()

                if (data['min_links_batch'].length > 0) {$('#model_batch_options').append('<option>Min Links</option>')}
                if (data['min_gain_batch'].length > 0) {$('#model_batch_options').append('<option>Min Gain</option>')}
                if (data['min_gain_long_batch'].length > 0) {$('#model_batch_options').append('<option>Min Gain Long</option>')}
                if (data['min_gain_short_batch'].length > 0) {$('#model_batch_options').append('<option>Min Gain Short</option>')}

                if (data['max_gain_batch'].length > 0) {$('#model_batch_options').append('<option>Max Gain</option>')}
                if (data['max_gain_long_batch'].length > 0) {$('#model_batch_options').append('<option>Max Gain Long</option>')}
                if (data['max_gain_short_batch'].length > 0) {$('#model_batch_options').append('<option>Max Gain Short</option>')}

                if (data['max_gain_long_batch'].length > 0) { $('#model_batch_options').val('Max Gain Long').change() }
                else if (data['max_gain_batch'].length > 0) { $('#model_batch_options').val('Max Gain').change() }
                else if (data['min_links_batch'].length > 0) {  $('#model_batch_options').val('Min Links').change()  }
                else { $('#model_batch_options').val('') }


                $('#linked_datatable').DataTable().clear();
                $('#linked_datatable').DataTable().rows.add(batch_data['linked']).draw();

                $('#linked_datatable').DataTable().clear();
                $('#linked_datatable').DataTable().rows.add(batch_data['linked']).draw();

                $('#model_quantity').val(data['potential_sale_quantity']) 

                $('#total_in_usd').val(data['total_in_usd'])
                
                
            },   
        });
    } );


    $('#model_batch_options').on('change', function() {
        // alert( $(this).find(":selected").val() );
        
        if ($(this).find(":selected").val() == 'Min Links') {

            $('#model_batches_datatable').DataTable().clear();
            $('#model_batches_datatable').DataTable().rows.add(batch_data['min_links_batch']).draw();
            $('#model_batch_text').html(batch_data['min_links_batch_text']);
        
        } else if ($(this).find(":selected").val() == 'Min Gain') {

            $('#model_batches_datatable').DataTable().clear();
            $('#model_batches_datatable').DataTable().rows.add(batch_data['min_gain_batch']).draw();
            $('#model_batch_text').html(batch_data['min_gain_batch_text']);

        } else if ($(this).find(":selected").val() == 'Min Gain Long') {

            $('#model_batches_datatable').DataTable().clear();
            $('#model_batches_datatable').DataTable().rows.add(batch_data['min_gain_long_batch']).draw();
            $('#model_batch_text').html(batch_data['min_gain_long_batch_text']);

        } else if ($(this).find(":selected").val() == 'Min Gain Short') {

            $('#model_batches_datatable').DataTable().clear();
            $('#model_batches_datatable').DataTable().rows.add(batch_data['min_gain_short_batch']).draw();
            $('#model_batch_text').html(batch_data['min_gain_short_batch_text']);
        
        } else if ($(this).find(":selected").val() == 'Max Gain') {
            
            $('#model_batches_datatable').DataTable().clear();
            $('#model_batches_datatable').DataTable().rows.add(batch_data['max_gain_batch']).draw();
            $('#model_batch_text').html(batch_data['max_gain_batch_text']);
    
        } else if ($(this).find(":selected").val() == 'Max Gain Long') {
                
            $('#model_batches_datatable').DataTable().clear();
            $('#model_batches_datatable').DataTable().rows.add(batch_data['max_gain_long_batch']).draw();
            $('#model_batch_text').html(batch_data['max_gain_long_batch_text']);

        } else if ($(this).find(":selected").val() == 'Max Gain Short') {
                    
            $('#model_batches_datatable').DataTable().clear();
            $('#model_batches_datatable').DataTable().rows.add(batch_data['max_gain_short_batch']).draw();
            $('#model_batch_text').html(batch_data['max_gain_short_batch_text']);
        }

     });



    



    



} );
