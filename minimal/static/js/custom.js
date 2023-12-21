<!-- create getObjects javascript function to call the ajax function -->

async function getObjects() {
    var $table = $('#cositable')
    var $remove = $('#remove')
    var selections = []
    const datatest = JSON.stringify($('#cosiform').serialize());
    const objectlist = document.getElementById('objectlist');
    const locale = document.getElementById('locale');
    $.ajax({
        type: 'POST',
        url: "getObjects",
        data: datatest,
        contentType: "application/json;charset=UTF-8",
        dataType: "json",
        success: function (data) {
            var objects = data;
            var $cositable = $('#cositable')
            $cositable.bootstrapTable('destroy').bootstrapTable({
                height: 550,
                toolbar: '#toolbar',
                showToggle: true,
                showColumns: true,
                showColumnsToggleAll: true,
                detailView: true,
                showExport: true,
                clickToSelect: true,
                minumumCountColumns: 2,
                showPaginationSwitch: true,
                pagination: true,
                idField: 'id',
                pageList: [10, 25, 50, 100, 'ALL'],
                showFooter: true,
                sidePagination: 'server',
                locale: $('#locale').val(),
                columns: [
                    [{
                        field: 'state',
                        checkbox: true,
                        rowspan: 2,
                        align: 'center',
                        valign: 'middle'
                    },{
                        title: 'Row ID',
                        field: 'id',
                        rowspan: 2,
                        align: 'center',
                        valign: 'middle',
                        sortable: true,
                        footerFormatter: totalTextFormatter
                    }, {
                        title: 'Object Detail',
                        colspan: 3,
                        align: 'center'
                    }],
                    [{
                        title: 'Object Key',
                        field: 'Key',
                        align: 'center',
                        valign: 'middle',
                        sortable: true,
                        footerFormatter: totalNameFormatter,
                    }, {
                        field: 'Size',
                        title: 'Object Size',
                        sortable: true,
                        align: 'center',
                        footerFormatter: totalSizeFormatter
                    }, {
                        field: 'operate',
                        title: 'Object Operate',
                        align: 'center',
                        clickToSelect: false,
                        events: window.operateEvents,
                        formatter: operateFormatter,
                        clickToSelect: false
                    }]
                ],
                responseHandler: function (res) {
                    $.each(res.rows, function (i, row) {
                        row.state = $.inArray(row.id, selections) !== -1
                    })
                    return res
                },
                detailFormatter: function (index, row) {
                    const html = [];
                    $.each(row, function (key, value) {
                    html.push('<p><b>' + key + ':</b> ' + value + '</p>')
                })
                return html.join('')
            }
            })
            $table.on('check.bs.table uncheck.bs.table ' +
                'check-all.bs.table uncheck-all.bs.table',
                function () {
                    $remove.prop('disabled', !$table.bootstrapTable('getSelections').length)

                    // save your data, here just save the current page
                    selections = getIdSelections()
                    // push or splice the selections if you want to save all data selections
                })

            $table.on('all.bs.table', function (e, name, args) {
                console.log(name, args)
            })

            $remove.click(function () {
                const keys = getKeySelections();
                const ids = getIdSelections();
                $table.bootstrapTable('remove', {
                    field: 'id',
                    values: ids
                })
                deleteObjects(keys)
                $remove.prop('disabled', true)
            })

            $cositable.bootstrapTable('load', objects)
            objectlist.style.display = 'block';
            locale.onchange = function () {
                $cositable.bootstrapTable('refreshOptions', {
                    locale: $(this).val()
                });
            }
        },
        error: function (jqXHR, exception) {
            var msg = '';
            if (jqXHR.status === 0) {
                msg = 'Not connect.\n Verify Network.';
            } else if (jqXHR.status == 404) {
                msg = 'Requested page not found. [404]';
            } else if (jqXHR.status == 500) {
                msg = 'Internal Server Error [500].';
            } else if (exception === 'parsererror') {
                msg = 'Requested JSON parse failed.';
            } else if (exception === 'timeout') {
                msg = 'Time out error.';
            } else if (exception === 'abort') {
                msg = 'Ajax request aborted.';
            } else {
                msg = 'Uncaught Error.\n' + jqXHR.responseText;
            }
            $('#post').html(msg);
        },
    });
}

async function uploadObjects() {
    // Grab the form data and the file input element
    let uploadButton = document.getElementById("upload-button");
    let formData = new FormData(document.getElementById("cosiform"));
    let fileupload = document.getElementById("fileupload");

    // Add the file to the request body
    formData.append("fileupload", fileupload.files[0]);

    // Send the request to the server
    let resp = await fetch('/uploadObjects', {
        method: "POST",
        body: formData
    });

    if (resp.status == 200) {
        // Disable upload button again
        uploadButton.disabled = true;
        fileupload.value = ''
        alert("Uploaded object successfully!");
    } else {
        alert("Object Upload failed!");
    }
}

async function deleteObjects(keys) {

    // Grab the form data and the file input element
    let formData = new FormData(document.getElementById("cosiform"));

    // Add the object kets to be deleted to the request body
    formData.append("keystodelete", keys);

    // Send the request to the server
    await fetch('/deleteObjects', {
        method: "POST",
        body: formData
    });
}

function convertFormToJSON(array) {
    const json = {};
    $.each(array, function () {
        json[this.name] = this.value || "";
    });
    return json;
}

function getIdSelections() {
    var $table = $('#cositable')
    return $.map($table.bootstrapTable('getSelections'), function (row) {
        return row.id
    })
}

function getKeySelections() {
    var $table = $('#cositable')
    return $.map($table.bootstrapTable('getSelections'), function (row) {
        return row.Key
    })
}

function operateFormatter(value, row, index) {
    return [
        '<a class="remove" href="javascript:void(0)" title="Delete Object">',
        '<i class="fa fa-trash"></i>',
        '</a>'
    ].join('')
}

window.operateEvents = {
    'click .like': function (e, value, row, index) {
        alert('You click like action, row: ' + JSON.stringify(row))
    },
    'click .remove': function (e, value, row, index) {
        const $table = $('#cositable');
        const objKey = row.Key;
        deleteObjects(objKey)
        $table.bootstrapTable('remove', {
            field: 'id',
            values: [row.id]
        })
    }
}

function totalTextFormatter(data) {
    return 'Total'
}

function totalNameFormatter(data) {
    return data.length
}

function totalPriceFormatter(data) {
    var field = this.field
    return '$' + data.map(function (row) {
        return +row[field].substring(1)
    }).reduce(function (sum, i) {
        return sum + i
    }, 0)
}

function totalSizeFormatter(data) {
    var totalSize = 0;
    var field = this.field
    totalSize = data.map(function (row) {
        return +row[field]
    }).reduce(function (sum, i) {
        return sum + i
    }, 0)
    if (totalSize > 0) {
        totalSize = totalSize / 1024
    }
    return totalSize.toFixed(2) + ' KB'
}

async function sendTestEvent() {

    // Create test event json
    const testEventData = '{"Records":[{"eventVersion":"2.2","eventSource":"aws:s3","awsRegion":"osci6f2aaa342523e77b","eventTime":"2023-12-16T20:15:03.406Z","eventName":"s3:ObjectCreated:Put","userIdentity":{"principalId":"urn:osc:iam::osaid2af1554252c9173:user/user2-cosi"},"requestParameters":{"sourceIPAddress":"10.243.45.15"},"responseElements":{"x-amz-request-id":"c0a84fa3:18ae1b9e066:a13d:199","x-amz-id-2":"3a6fe5c5bf346f3eeaf7a63c1f3fb4fdf66ec36c933f689c16f4905cde1bd414"},"s3":{"s3SchemaVersion":"1.0","configurationId":"cosidemowebhook","bucket":{"name":"bucket-confluent","ownerIdentity":{"principalId":"urn:osc:iam::osaid2af1554252c9173:root"},"arn":"arn:aws:s3:osci6f2aaa342523e77b:osti5fd59b5500bd68cc:bucket-confluent"},"object":{"key":"jinjafilters.py","size":"911","etag":"fc44b090992620a44d94671ada56cc08","sequencer":"8000000000032e492"}}}]}'

    // Grab the form data and the messasge text area element
    let exampleFormControlTextarea1 = document.getElementById("exampleFormControlTextarea1");
    let formData = new FormData();

    // Add the test data to the form data
    formData.append("testdata", testEventData);
    formData.append("exampleFormControlTextarea1", exampleFormControlTextarea1.value);

    // Send the request to the server
    let resp = await fetch('/webhook', {
        method: "POST",
        headers: {
            'Content-Type': 'application/json;charset=utf-8'
        },
        body: testEventData
    });
    if (resp.status != 200) {
        alert("Configuration Update failed!");
    }
}

async function updateDemoConfiguration() {
    let formData = new FormData(document.getElementById("cosiformconfiguration"));
    let kafkaSwitch = document.getElementById("kafkaSwitchCheckChecked");
    let kafkaBroker = document.getElementById("kafkaBroker");
    let kafkaTopic = document.getElementById("kafkaTopic");

    let objectSwitch = document.getElementById("objectSwitchCheckChecked");
    let objectEndpoint = document.getElementById("objectEndpoint");
    let objectAccessKey = document.getElementById("objectAccessKey");
    let objectSecretKey = document.getElementById("objectSecretKey");
    let objectBucket = document.getElementById("objectBucket");

    if (kafkaSwitch.checked) {
        formData.append("kafkaSwitch", "True");
    }
    else {
        formData.append("kafkaSwitch", "False");
    }

    if (objectSwitch.checked) {
        formData.append("objectSwitch", "True");
    }
    else {
        formData.append("objectSwitch", "False");
    }

    formData.append("kafkaBroker", kafkaBroker.value);
    formData.append("kafkaTopic", kafkaTopic.value);
    formData.append("objectSwitch", objectSwitch.value);
    formData.append("objectEndpoint", objectEndpoint.value);
    formData.append("objectAccessKey", objectAccessKey.value);
    formData.append("objectSecretKey", objectSecretKey.value);
    formData.append("objectBucket", objectBucket.value);

    // Send the request to the server
    let resp = await fetch('/configuration', {
        method: "POST",
        body: formData
    });

    if (resp.status != 200) {
        alert("Configuration Update failed!");
    }
}
