$(function() {
    function PrinterStateViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];

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
        self.progress = ko.observable(undefined);
        self.filesize = ko.observable(undefined);
        self.filepos = ko.observable(undefined);
        self.printTime = ko.observable(undefined);
        self.printTimeLeft = ko.observable(undefined);
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
                return formatDuration(self.lastPrintTime());
            if (self.estimatedPrintTime())
                return formatDuration(self.estimatedPrintTime());
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
                    return gettext("Calculating...");
                }
            } else {
                return formatFuzzyEstimation(self.printTimeLeft());
            }
        });
        self.progressString = ko.pureComputed(function() {
            if (!self.progress())
                return 0;
            return self.progress();
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
                self.filesize(data.file.size);
                self.sd(data.file.origin == "sdcard");
            } else {
                self.filename(undefined);
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
        };

        self._processZData = function(data) {
            self.currentHeight(data);
        };

        self._processBusyFiles = function(data) {
            var busyFiles = [];
            _.each(data, function(entry) {
                if (entry.hasOwnProperty("name") && entry.hasOwnProperty("origin")) {
                    busyFiles.push(entry.origin + ":" + entry.name);
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
						var p_item = data[i], p_id = p_item.purp_id, p_desc = p_item.purpose
						var option = document.createElement("option");
						option.value = p_id;
						option.textContent = p_desc;
						p_selector.appendChild(option);
					};
				}
			});
			
			console.log("sent AJAX requests for purpose and materials");
			
			$("#studentIdModal").on('shown', function() {
				$("#studentId").val('');
				$("#studentId").focus();
				$("#studentIdVerification").attr("disabled", "disabled");
			});
			
			$("#studentIdVerification").unbind("click").on("click", function()
			{
				console.log("on click function activated");
				var trans_response = "";
				if ( $("#studentId").val().length != 10) {
					return false;
				}
				var postBody = JSON.stringify({type: "utaid", number: $("#studentId").val(), device: "DEV_ID"});
				console.log(postBody);
				
				$.ajax({
					type:"POST",
					dataType: "json",
					contentType: "application/json; charset=UTF-8",
					url:"FLUD_BASE/flud.php",
					data:postBody,
					success: function(success_data){
						console.log("got success back");
						console.log(success_data);
						trans_response = success_data;
						console.log("Transaction ID is:");
						console.log(trans_response["trans_id"]);
						if (trans_response["authorized"] === "Y"){
							
							console.log("User Authorized");
							
							var tranBody = JSON.stringify({command:"id", trans_id:trans_response["trans_id"]});
							$.ajax({
								type:"POST",
								dataType: "json",
								contentType: "application/json; charset=UTF-8",
								url: API_BASEURL + "files/local/" + self.filename(),
								data:tranBody,
								success: function(response){console.log("Successfully saved data");
															console.log(response);}
							});
							
							console.log(self.filename());
							
							if (self.isPaused()) {
								$("#confirmation_dialog .confirmation_dialog_message").text(gettext("This will restart the print job from the beginning."));
								$("#confirmation_dialog .confirmation_dialog_acknowledge").unbind("click");
								$("#confirmation_dialog .confirmation_dialog_acknowledge").click(function(e) {e.preventDefault(); $("#confirmation_dialog").modal("hide"); self._jobCommand("restart");});
								$("#confirmation_dialog").modal("show");
							} else {
								self._jobCommand("start");
							}
							
						}
						else {
							console.log("User Not Authorized!");
							$("#studentIdModal").modal('hide');
							return false;
						}
						},
					failure: function(errMsg){
						console.log("errored out");
						console.log(errMsg);
						}
				});
			});
			
			

        };

        self.pause = function() {
            self._jobCommand("pause");
        };

        self.cancel = function() {
            self._jobCommand("cancel");
        };

        self._jobCommand = function(command, callback) {
            $.ajax({
                url: API_BASEURL + "job",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({command: command}),
                success: function(response) {
                    if (callback != undefined) {
                        callback();
                    }
                }
            });
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        PrinterStateViewModel,
        ["loginStateViewModel"],
        ["#state_wrapper", "#drop_overlay"]
    ]);
});
