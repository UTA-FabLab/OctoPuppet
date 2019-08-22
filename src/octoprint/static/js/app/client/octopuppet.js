function checkStatus(file, paused) {
    $.ajax({
        type: "GET",
        contentType: "application/json; charset=UTF-8",
        url: API_BASEURL + "FabAppData/status",
        headers: { 'X-Api-Key': 'UTALab16' },
        success: function (data) {
            var status = data["status"];
            if (status != 200) {
                $("#confirmModal").modal('show');
                $(document).ready(function () {
                    $('#proceed').click(function () {
                        OctoPuppet(file, paused);
                    });
                });
                $(document).ready(function () {
                    $('#cancel').click(function () {
                        var stop = "cancel";
                    });
                });
                if (stop == "cancel") {
                    return false;
                }
            }
            else {
                OctoPuppet(file, paused);
            }
        }
    });
}

function OctoPuppet(file, paused) {
    $("#studentIdModal").modal('show');
    console.log("Showing student id modal");

    var m_request_body = JSON.stringify({ type: "device_id" });
    console.log(m_request_body);
    $.ajax({
        url: API_BASEURL + "FabAppData/materials",
        headers: { 'X-Api-Key': 'UTALab16' },
        type: "POST",
        contentType: "application/json; charset=UTF-8",
        data: m_request_body,
        dataType: "json",
        success: function (data) {
            console.log("Got response from materials.php");
            console.log(data);
            var f_selector = document.getElementById("sel_filament");
            f_selector.options.length = 0;
            for (var i = 0; i < data.length; i++) {
                var f_item = data[i], id = f_item.m_id, desc = "($" + f_item.price + "/" + f_item.unit + ") - " + f_item.m_name;
                var option = document.createElement("option");
                option.value = id;
                option.textContent = desc;
                f_selector.appendChild(option);
            };
            $("#sel_filament").prepend("<option value='-1' hidden='hidden' selected='selected'>Select Material</option>");
        }
    });

    $.ajax({
        url: API_BASEURL + "FabAppData/purpose",
        headers: { 'X-Api-Key': 'UTALab16' },
        type: "POST",
        contentType: "application/json; charset=UTF-8",
        data: m_request_body,
        dataType: "json",
        success: function (data) {
            console.log("Got response from purpose.php");
            console.log(data);
            var p_selector = document.getElementById("sel_purpose");
            p_selector.options.length = 0;
            for (var i = 0; i < data.length; i++) {
                var p_item = data[i], p_id = p_item.p_id, p_desc = p_item.purpose
                var option = document.createElement("option");
                option.value = p_id;
                option.textContent = p_desc;
                p_selector.appendChild(option);
            };
            $("#sel_purpose").prepend("<option value='-1' hidden='hidden' selected='selected'>Select Purpose</option>");
        }
    });

    console.log("sent AJAX requests for purpose and materials");

    $("#studentIdModal").on('shown', function () {
        $("#studentId").val('');
        $("#studentId2").val('');
        $("#studentId").focus();
        $("#studentIdVerification").attr("disabled", "disabled");
    });

    $("#studentIdVerification").unbind("click").on("click", function () {
        var trans_response = "";
        if ($("#studentId").val().length != 10) {
            return false;
        }
        $.ajax({
            type: "GET",
            contentType: "application/json; charset=UTF-8",
            url: API_BASEURL + "files/local/" + file,
            headers: { 'X-Api-Key': 'UTALab16' },
            success: function (api_file_data) {
                var postBody = { type: "print" };
                postBody.uta_id = $("#studentId").val()
                postBody.m_id = document.getElementById("sel_filament").options[document.getElementById("sel_filament").selectedIndex].value;
                postBody.p_id = document.getElementById("sel_purpose").options[document.getElementById("sel_purpose").selectedIndex].value;
                postBody.filename = file;
                postBody.est_filament_used = api_file_data.est_flmnt_vol;
                postBody.est_build_time = api_file_data.est_build_time;
                console.log(JSON.stringify(postBody));
                $.ajax({
                    url: API_BASEURL + "FabAppData/flud",
                    headers: { 'X-Api-Key': 'UTALab16' },
                    type: "POST",
                    contentType: "application/json; charset=UTF-8",
                    data: JSON.stringify(postBody),
                    dataType: "json",
                    success: function (success_data) {
                        console.log("got success back");
                        console.log(success_data);
                        trans_response = success_data;
                        console.log("Transaction ID is:");
                        console.log(trans_response["trans_id"]);
                        $("#studentIdModal").modal('hide');
                        if (trans_response.hasOwnProperty('ERROR')) {
                            alert(trans_response["ERROR"]);
                        }
                        if (trans_response.hasOwnProperty('authorized')) {
                            if (trans_response["authorized"] === "Y") {
                                console.log("User Authorized");
                                var tranBody = JSON.stringify({ command: "id", trans_id: trans_response["trans_id"] });
                                $.ajax({
                                    type: "POST",
                                    dataType: "json",
                                    contentType: "application/json; charset=UTF-8",
                                    url: API_BASEURL + "files/local/" + file,
                                    data: tranBody,
                                    success: function (response) {
                                        console.log("Successfully saved trasaction ID data");
                                        console.log(response);
                                    }
                                });
                                if (paused != null) {
                                    $("#confirmation_dialog .confirmation_dialog_message").text(gettext("This will restart the print job from the beginning."));
                                    $("#confirmation_dialog .confirmation_dialog_acknowledge").unbind("click");
                                    $("#confirmation_dialog .confirmation_dialog_acknowledge").click(function (e) { e.preventDefault(); $("#confirmation_dialog").modal("hide"); self._jobCommand("restart"); });
                                    $("#confirmation_dialog").modal("show");
                                } else {
                                    OctoPrint.job.start();
                                }
                            }
                            else {
                                alert("User Not Authorized!");
                                return false;
                            }
                        }
                    },
                    error: function (errMsg) {
                        console.log("Error with the offline method.");
                    }
                });
            }
        });
    });
}

function endTransaction() {
    postBody = { type:"update_end_time" }
    $.ajax({
        url: API_BASEURL + "FabAppData/end",
        headers: { 'X-Api-Key': 'UTALab16' },
        type: "POST",
        contentType: "application/json; charset=UTF-8",
        data: JSON.stringify(postBody),
        dataType: "json",
        success: function (success_data) {
            console.log("Ticket ended succesfully on FabApp");
        }
            
    });
}