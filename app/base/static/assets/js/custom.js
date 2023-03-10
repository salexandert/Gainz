
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


    $('#al_stats_datatable tbody').on( 'click', 'tr', function () {
        
 
        $.ajax({
            type: "POST",
            url: "/auto_link/auto_link_pre_check",
            data: JSON.stringify({
                'row_data': table.row( this ).data()
              }),  

            contentType: 'application/json',
            success: function (data) {
                // console.log(data)

                $('#al_options').html(data['message'])
            
            },   
        });

    } );

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
                'asset': $('#al_stats_datatable').DataTable().row( {selected:true} ).data()
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
                'asset': $('#al_stats_datatable').DataTable().row( {selected:true} ).data()
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
    

    $('#statspage_buys_datatable').DataTable({
        select: {
            style: 'single'
        },
    });

    $("#stats_usd_spot").on('change', function(){
        
        $.ajax({
            type: "POST",
            url: "/stats/selected_asset",
            data: JSON.stringify({
                'row_data': table.row( {selected:true}).data(),
                'start_date': $("#start_date").datetimepicker().val(),
                'end_date': $("#end_date").datetimepicker().val(),
                'year': $('#stats_page_year_dropdown').find(":selected").val(),
                'current_usd_spot': $(this).val()
                }),  

            contentType: 'application/json',
            success: function (return_data) {

                // console.log(return_data)
                
                $('#statspage_detailed_datatable').DataTable().clear();
                $('#statspage_detailed_datatable').DataTable().rows.add(return_data['detailed_stats']).draw();
                                
                if (myChart!=null) {myChart.destroy();}

                var ctx = document.getElementById("gainzChart").getContext("2d");

                chartColor = "#FFFFFF";
                gradientStroke = ctx.createLinearGradient(500, 0, 100, 0);
                gradientStroke.addColorStop(0, '#80b6f4');
                gradientStroke.addColorStop(1, chartColor);
            
                gradientFill = ctx.createLinearGradient(0, 170, 0, 50);
                gradientFill.addColorStop(0, "rgba(128, 182, 244, 0)");
                gradientFill.addColorStop(1, "rgba(249, 99, 59, 0.40)");

                myChart = new Chart(ctx, {
                  type: 'line',
                  data: {
                    datasets: [
                        {
                            label: "Value",
                            borderColor: "#6bd098",
                            fill: false,
                            borderWidth: 3,
                            data: return_data['unrealized_chart_data']
                        },
                    ]
                },
                  options: {
                    elements: {
                        line: {
                            tension: 0.08
                        }
                    },
                    tooltips: {
                        callbacks: {
                            label: function(tooltipItem, data) {
                                var value = data.datasets[tooltipItem.datasetIndex].label || '';
                                if (value) { value += ': '; }
                                value += formatter.format(tooltipItem.yLabel)

                                var quantity = "Quantity: " 
                                quantity += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['quantity']
                                
                                var usd_spot = "USD Spot: "
                                usd_spot += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['usd_spot']

                                var cost_baisis = "Cost Baisis: "
                                cost_baisis += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['cost_baisis']

                                var gain_loss = "Gain/Loss: "
                                gain_loss += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['gain_loss']
                        
                                return [value, quantity, usd_spot, cost_baisis, gain_loss];
                            }
                        }
                      },


                    responsive: true,
                    title:      {
                        display: false,
                        text:    "Gainz Chart"
                    },
                    scales: {
                        
                        xAxes: [{
                            type: "time",
                            time: {
                                unit: 'month',
                                tooltipFormat: 'll'
                            },
                            scaleLabel: {
                                display:     true,
                                labelString: 'Date'
                            },
                            
                        }],
                        
                        yAxes: [{
                            ticks: {
                                beginAtZero: false,
                                callback: function(value, index, values) {
                                  if(parseInt(value) >= 1000){
                                    return '$' + value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                                  } else {
                                    return '$' + value;
                                  }
                                }
                            },

                            scaleLabel: {
                                display:     true,
                                labelString: 'Value (Quantity * USD Spot)'
                            },

                              gridLines: {
                                drawBorder: false,
                                zeroLineColor: "transparent",
                                color: 'rgba(255,255,255,0.05)'
                              }
                        }]
                    }
                }
                });
                    
            },   
        });

        

    });


    var formatter = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
      
        // These options are needed to round to whole numbers if that's what you want.
        //minimumFractionDigits: 0, // (this suffices for whole numbers, but will print 2500.10 as $2,500.1)
        //maximumFractionDigits: 0, // (causes 2500.99 to be printed as $2,501)
      });


    // Init Charts
    var myChart=null;




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
    
            },   
        });
    
    });

    $('#statspage_stats_datatable tbody').on( 'click', 'tr', function () {
        // console.log( table.row( this ).data() );

        $.ajax({
            type: "POST",
            url: "/stats/selected_asset",
            data: JSON.stringify({
                'row_data': table.row( this ).data(),
                'start_date': $("#start_date").datetimepicker().val(),
                'end_date': $("#end_date").datetimepicker().val(),
                'year': $('#stats_page_year_dropdown').find(":selected").val(),
                }),  

            contentType: 'application/json',
            success: function (return_data) {

                // console.log(return_data)
                
                $('#statspage_detailed_datatable').DataTable().clear();
                $('#statspage_detailed_datatable').DataTable().rows.add(return_data['detailed_stats']).draw();

                $('#statspage_sells_datatable').DataTable().clear();
                $('#statspage_sells_datatable').DataTable().rows.add(return_data['sells_table_data']).draw();
                
                
                $('#s8949_table').DataTable().clear();
                $('#s8949_table').DataTable().rows.add(return_data['s8949_table_data']).draw();

                $('#l8949_table').DataTable().clear();
                $('#l8949_table').DataTable().rows.add(return_data['l8949_table_data']).draw();

                // $('#statspage_buys_datatable').DataTable().clear();
                // $('#statspage_buys_datatable').DataTable().rows.add(return_data['buys']).draw();

                
                if (myChart!=null) {myChart.destroy();}

                var ctx = document.getElementById("gainzChart").getContext("2d");

                chartColor = "#FFFFFF";
                gradientStroke = ctx.createLinearGradient(500, 0, 100, 0);
                gradientStroke.addColorStop(0, '#80b6f4');
                gradientStroke.addColorStop(1, chartColor);
            
                gradientFill = ctx.createLinearGradient(0, 170, 0, 50);
                gradientFill.addColorStop(0, "rgba(128, 182, 244, 0)");
                gradientFill.addColorStop(1, "rgba(249, 99, 59, 0.40)");

                myChart = new Chart(ctx, {
                  type: 'line',
                  data: {
                    datasets: [
                            {
                                label: "Value",
                                borderColor: "#6bd098",
                                fill: false,
                                borderWidth: 3,
                                data: return_data['unrealized_chart_data']
                            },
                        ]
                    },
                  options: {
                    elements: {
                        line: {
                            tension: 0.08
                        }
                    },
                    tooltips: {
                        callbacks: {
                            label: function(tooltipItem, data) {
                                var value = data.datasets[tooltipItem.datasetIndex].label || '';
                                if (value) { value += ': '; }
                                value += formatter.format(tooltipItem.yLabel)

                                var quantity = "Quantity: " 
                                quantity += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['quantity']
                                
                                var usd_spot = "USD Spot: "
                                usd_spot += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['usd_spot']

                                var cost_baisis = "Cost Baisis: "
                                cost_baisis += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['cost_baisis']

                                var gain_loss = "Gain/Loss: "
                                gain_loss += data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index]['gain_loss']
                        
                                return [value, quantity, usd_spot, cost_baisis, gain_loss];
                            }
                        }
                      },


                    responsive: true,
                    title:      {
                        display: false,
                        text:    "Gainz Chart"
                    },
                    scales: {
                        
                        xAxes: [{
                            type: "time",
                            time: {
                                unit: 'month',
                                tooltipFormat: 'll'
                            },
                            scaleLabel: {
                                display:     true,
                                labelString: 'Date'
                            },
                            
                        }],
                        
                        yAxes: [{
                            ticks: {
                                beginAtZero: false,
                                callback: function(value, index, values) {
                                  if(parseInt(value) >= 1000){
                                    return '$' + value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                                  } else {
                                    return '$' + value;
                                  }
                                }
                            },

                            scaleLabel: {
                                display:     true,
                                labelString: 'Value (Quantity * USD Spot)'
                            },

                              gridLines: {
                                drawBorder: false,
                                zeroLineColor: "transparent",
                                color: 'rgba(255,255,255,0.05)'
                              }
                        }]
                    }
                }
                });


                    
            },   
        });
    } );


} );




// history page code
$(document).ready(function() {

    var table = $('#history_datatable').DataTable({
        select: {
            style: 'single'
        },
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