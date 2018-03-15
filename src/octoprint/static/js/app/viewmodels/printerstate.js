$(function() {
    function PrinterStateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.stateString = ko.observable(undefined);
        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);
        self.isSdReady = ko.observable(undefined);

        self.enablePrint = ko.pureComputed(function() {
            return self.isOperational() && self.isReady() && !self.isPrinting() && self.loginState.isUser() && self.filename() != undefined;
        });
        self.enablePause = ko.pureComputed(function() {
            return self.isOperational() && (self.isPrinting() || self.isPaused()) && self.loginState.isUser();
        });
        self.enableCancel = ko.pureComputed(function() {
            return self.isOperational() && (self.isPrinting() || self.isPaused()) && self.loginState.isUser();
        });

        self.filename = ko.observable(undefined);
        self.filepath = ko.observable(undefined);
        self.progress = ko.observable(undefined);
        self.filesize = ko.observable(undefined);
        self.filepos = ko.observable(undefined);
        self.printTime = ko.observable(undefined);
        self.printTimeLeft = ko.observable(undefined);
        self.printTimeLeftOrigin = ko.observable(undefined);
        self.sd = ko.observable(undefined);
        self.timelapse = ko.observable(undefined);

        self.busyFiles = ko.observableArray([]);

        self.filament = ko.observableArray([]);
        self.estimatedPrintTime = ko.observable(undefined);
        self.lastPrintTime = ko.observable(undefined);

        self.currentHeight = ko.observable(undefined);

        self.TITLE_PRINT_BUTTON_PAUSED = gettext("Restarts the print job from the beginning");
        self.TITLE_PRINT_BUTTON_UNPAUSED = gettext("Starts the print job");
        self.TITLE_PAUSE_BUTTON_PAUSED = gettext("Resumes the print job");
        self.TITLE_PAUSE_BUTTON_UNPAUSED = gettext("Pauses the print job");

        self.titlePrintButton = ko.observable(self.TITLE_PRINT_BUTTON_UNPAUSED);
        self.titlePauseButton = ko.observable(self.TITLE_PAUSE_BUTTON_UNPAUSED);

        self.estimatedPrintTimeString = ko.pureComputed(function() {
            if (self.lastPrintTime())
                return formatFuzzyPrintTime(self.lastPrintTime());
            if (self.estimatedPrintTime())
                return formatFuzzyPrintTime(self.estimatedPrintTime());
            return "-";
        });
        self.byteString = ko.pureComputed(function() {
            if (!self.filesize())
                return "-";
            var filepos = self.filepos() ? formatSize(self.filepos()) : "-";
            return filepos + " / " + formatSize(self.filesize());
        });
        self.heightString = ko.pureComputed(function() {
            if (!self.currentHeight())
                return "-";
            return _.sprintf("%.02fmm", self.currentHeight());
        });
        self.printTimeString = ko.pureComputed(function() {
            if (!self.printTime())
                return "-";
            return formatDuration(self.printTime());
        });
        self.printTimeLeftString = ko.pureComputed(function() {
            if (self.printTimeLeft() == undefined) {
                if (!self.printTime() || !(self.isPrinting() || self.isPaused())) {
                    return "-";
                } else {
                    return gettext("Still stabilizing...");
                }
            } else {
                return formatFuzzyPrintTime(self.printTimeLeft());
            }
        });
        self.printTimeLeftOriginString = ko.pureComputed(function() {
            var value = self.printTimeLeftOrigin();
            switch (value) {
                case "linear": {
                    return gettext("Based on a linear approximation (very low accuracy, especially at the beginning of the print)");
                }
                case "analysis": {
                    return gettext("Based on the estimate from analysis of file (medium accuracy)");
                }
                case "mixed-analysis": {
                    return gettext("Based on a mix of estimate from analysis and calculation (medium accuracy)");
                }
                case "average": {
                    return gettext("Based on the average total of past prints of this model with the same printer profile (usually good accuracy)");
                }
                case "mixed-average": {
                    return gettext("Based on a mix of average total from past prints and calculation (usually good accuracy)");
                }
                case "estimate": {
                    return gettext("Based on the calculated estimate (best accuracy)");
                }
                default: {
                    return "";
                }
            }
        });
        self.printTimeLeftOriginClass = ko.pureComputed(function() {
            var value = self.printTimeLeftOrigin();
            switch (value) {
                default:
                case "linear": {
                    return "text-error";
                }
                case "analysis":
                case "mixed-analysis": {
                    return "text-warning";
                }
                case "average":
                case "mixed-average":
                case "estimate": {
                    return "text-success";
                }
            }
        });
        self.progressString = ko.pureComputed(function() {
            if (!self.progress())
                return 0;
            return self.progress();
        });
        self.progressBarString = ko.pureComputed(function() {
            if (!self.progress()) {
                return "";
            }
            return _.sprintf("%d%%", self.progress());
        });
        self.pauseString = ko.pureComputed(function() {
            if (self.isPaused())
                return gettext("Continue");
            else
                return gettext("Pause");
        });

        self.timelapseString = ko.pureComputed(function() {
            var timelapse = self.timelapse();

            if (!timelapse || !timelapse.hasOwnProperty("type"))
                return "-";

            var type = timelapse["type"];
            if (type == "zchange") {
                return gettext("On Z Change");
            } else if (type == "timed") {
                return gettext("Timed") + " (" + timelapse["options"]["interval"] + " " + gettext("sec") + ")";
            } else {
                return "-";
            }
        });
        self.get_t_id = ko.computed(function() {
          $.ajax({
            type:"GET",
            contentType: "application/json; charset=UTF-8",
            url: API_BASEURL + "files/local/" + self.filename(),
            headers: { 'X-Api-Key': 'UTALab16' },
            success:function (api_file_data){
              var file_data_t_id = JSON.stringify(api_file_data.trans_id)
              return file_data_t_id;
            },
            error: function(errMsg){
              console.log("No file is loaded.");
              return gettext("Not Available")
            }
          });
        });

        self.t_id = ko.computed(function () {
          if (self.isPrinting() || self.isPaused() || self.isError()) {
            return self.get_t_id()
            console.log(file_data_t_id);
          } else {
            return gettext("---")
          }
        });

        self.fromCurrentData = function(data) {
            self._fromData(data);
        };

        self.fromHistoryData = function(data) {
            self._fromData(data);
        };

        self.fromTimelapseData = function(data) {
            self.timelapse(data);
        };

        self._fromData = function(data) {
            self._processStateData(data.state);
            self._processJobData(data.job);
            self._processProgressData(data.progress);
            self._processZData(data.currentZ);
            self._processBusyFiles(data.busyFiles);
        };

        self._processStateData = function(data) {
            var prevPaused = self.isPaused();

            self.stateString(gettext(data.text));
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isSdReady(data.flags.sdReady);

            if (self.isPaused() != prevPaused) {
                if (self.isPaused()) {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_PAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_PAUSED);
                } else {
                    self.titlePrintButton(self.TITLE_PRINT_BUTTON_UNPAUSED);
                    self.titlePauseButton(self.TITLE_PAUSE_BUTTON_UNPAUSED);
                }
            }
        };

        self._processJobData = function(data) {
            if (data.file) {
                self.filename(data.file.name);
                self.filepath(data.file.path);
                self.filesize(data.file.size);
                self.sd(data.file.origin == "sdcard");
            } else {
                self.filename(undefined);
                self.filepath(undefined);
                self.filesize(undefined);
                self.sd(undefined);
            }

            self.estimatedPrintTime(data.estimatedPrintTime);
            self.lastPrintTime(data.lastPrintTime);

            var result = [];
            if (data.filament && typeof(data.filament) == "object" && _.keys(data.filament).length > 0) {
                for (var key in data.filament) {
                    if (!_.startsWith(key, "tool") || !data.filament[key] || !data.filament[key].hasOwnProperty("length") || data.filament[key].length <= 0) continue;

                    result.push({
                        name: ko.observable(gettext("Tool") + " " + key.substr("tool".length)),
                        data: ko.observable(data.filament[key])
                    });
                }
            }
            self.filament(result);
        };

        self._processProgressData = function(data) {
            if (data.completion) {
                self.progress(data.completion);
            } else {
                self.progress(undefined);
            }
            self.filepos(data.filepos);
            self.printTime(data.printTime);
            self.printTimeLeft(data.printTimeLeft);
            self.printTimeLeftOrigin(data.printTimeLeftOrigin);
        };

        self._processZData = function(data) {
            self.currentHeight(data);
        };

        self._processBusyFiles = function(data) {
            var busyFiles = [];
            _.each(data, function(entry) {
                if (entry.hasOwnProperty("path") && entry.hasOwnProperty("origin")) {
                    busyFiles.push(entry.origin + ":" + entry.path);
                }
            });
            self.busyFiles(busyFiles);
        };

        self.print = function() {
			$("#studentIdModal").modal('show');
			console.log("Showing student id modal");

			var m_request_body = JSON.stringify({type: "device_id", device: "DEV_ID"});

			console.log(m_request_body);

			$.ajax({
				url: "FLUD_BASE/materials.php",
				type:"POST",
				dataType: "json",
				contentType: "application/json; charset=UTF-8",
				data: m_request_body,
				success: function(data)
				{
					console.log("Got response from materials.php");
					console.log(data);

					var f_selector = document.getElementById("sel_filament");

					f_selector.options.length = 0;

					for ( var i = 0; i < data.length; i++) {
						var f_item = data[i], id = f_item.m_id, desc = "($" +f_item.price + "/" + f_item.unit + ") - " + f_item.m_name;
						var option = document.createElement("option");
						option.value = id;
						option.textContent = desc;
						f_selector.appendChild(option);
					};
          $("#sel_filament").prepend("<option value='-1' hidden='hidden' selected='selected'>Select Material</option>");
				}
			});

			$.ajax({
				url: "FLUD_BASE/purpose.php",
				dataType: 'json',
				type: "GET",
				success: function(data)
				{
					console.log("Got response from purpose.php");
					console.log(data);

					var p_selector = document.getElementById("sel_purpose");

					p_selector.options.length = 0;

					for ( var i = 0; i < data.length; i++) {
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

			$("#studentIdModal").on('shown', function() {
				$("#studentId").val('');
                $("#studentId2").val('');
				$("#studentId").focus();
				$("#studentIdVerification").attr("disabled", "disabled");
			});

			$("#studentIdVerification").unbind("click").on("click", function()
			{
				var trans_response = "";

				if ( $("#studentId").val().length != 10) {
					return false;
				}

				$.ajax({
					type:"GET",
					contentType: "application/json; charset=UTF-8",
					url: API_BASEURL + "files/local/" + self.filename(),
					headers: { 'X-Api-Key': 'UTALab16' },
					success:function (api_file_data){
						var postBody = {type: "print", device_id: "DEV_ID"};

						postBody.uta_id = $("#studentId").val()
						postBody.m_id = document.getElementById("sel_filament").options[document.getElementById("sel_filament").selectedIndex].value;
						postBody.p_id = document.getElementById("sel_purpose").options[document.getElementById("sel_purpose").selectedIndex].value;

						postBody.filename = self.filename();
						postBody.est_filament_used = api_file_data.est_flmnt_vol;
						postBody.est_build_time = api_file_data.est_build_time;

						console.log(JSON.stringify(postBody));

						$.ajax({
							type:"POST",
							dataType: "json",
							contentType: "application/json; charset=UTF-8",
							url:"FLUD_BASE/flud.php",
							data:JSON.stringify(postBody),
							success: function(success_data){
								console.log("got success back");
								console.log(success_data);
								trans_response = success_data;
								console.log("Transaction ID is:");
								console.log(trans_response["trans_id"]);

								$("#studentIdModal").modal('hide');

								if(trans_response.hasOwnProperty('ERROR')){
									alert(trans_response["ERROR"]);
								}

								if(trans_response.hasOwnProperty('authorized')){
									if (trans_response["authorized"] === "Y"){

										console.log("User Authorized");

										var tranBody = JSON.stringify({command:"id", trans_id:trans_response["trans_id"]});
										$.ajax({
											type:"POST",
											dataType: "json",
											contentType: "application/json; charset=UTF-8",
											url: API_BASEURL + "files/local/" + self.filename(),
											data:tranBody,
											success: function(response){console.log("Successfully saved trasaction ID data");
																		console.log(response);}
										});

										console.log(self.filename());

										if (self.isPaused()) {
											$("#confirmation_dialog .confirmation_dialog_message").text(gettext("This will restart the print job from the beginning."));
											$("#confirmation_dialog .confirmation_dialog_acknowledge").unbind("click");
											$("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {e.preventDefault(); $("#confirmation_dialog").modal("hide"); self._jobCommand("restart");});
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
							error: function(errMsg){
								$("#studentIdModal").modal('hide');
								console.log("Connection to flud.php errored out. Error details:");
								console.log(errMsg);
								alert("Timeout error. Please inform current supervisor.");
								}
						});
					}
				});
			});
        };

        self.onlyPause = function() {
            OctoPrint.job.pause();
        };

        self.onlyResume = function() {
            OctoPrint.job.resume();
        };

        self.pause = function(action) {
            OctoPrint.job.togglePause();
        };

        self.cancel = function() {
            $("#cancelIdModal").modal('show');
            console.log("Showing kill confirm modal");
            $("#cancelIdModal").on('shown', function() {
                $("#studentId1").val('');
                $("#studentId2").val('');
                $("#studentId2").focus();
                $("#studentIdVerification2").attr("disabled", "disabled");
            });

            $("#studentIdVerification2").unbind("click").on("click", function()
            {
                if ( $("#studentId2").val().length != 10) {
                    return false;
                }
                else{
                  OctoPrint.job.cancel();
                }
            });
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        PrinterStateViewModel,
        ["loginStateViewModel", "settingsViewModel"],
        ["#state_wrapper", "#drop_overlay"]
    ]);
});
