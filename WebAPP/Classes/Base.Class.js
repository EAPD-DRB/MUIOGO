import { Message } from "./Message.Class.js";
import { Html } from "./Html.Class.js";
import { SyncS3 } from "./SyncS3.Class.js";

export class Base {
    static HEROKU = 0;
    static AWS_SYNC = 0;
    //init sync flag to pull from S3 only one time when visit home page
    static INIT_SYNC = 1;

    static apiUrl() {
        if (this.HEROKU == 1) {
            return "https://osemosys.herokuapp.com/";
        }
        return `${window.location.origin}/`;
    }

    static initSyncS3() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "initSyncS3",
                async: true,
                type: 'GET',
                dataType: 'json',
                credentials: 'include',
                xhrFields: { withCredentials: true },
                crossDomain: true,
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static getSession() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "getSession",
                async: true,
                type: 'GET',
                dataType: 'json',
                credentials: 'include',
                xhrFields: { withCredentials: true },
                crossDomain: true,
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static setSession(titlecs) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "setSession",
                async: true,
                type: 'POST',
                data: JSON.stringify({ "case": titlecs }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                credentials: 'include',
                xhrFields: { withCredentials: true },
                crossDomain: true,
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static getCaseStudies() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "getCases",
                async: true,
                type: 'GET',
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                //credentials: 'include',
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }

                    reject(error);
                }
            });
        });
    }

    static getResultCSV(casename, caserunname) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "getResultCSV",
                async: true,
                type: 'POST',
                data: JSON.stringify({ "casename": casename, "caserunname": caserunname }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static getCaseDesc(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "getDesc",
                async: true,
                type: 'POST',
                data: JSON.stringify({ "casename": casename }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static copyCaseStudy(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "copyCase",
                async: true,
                type: 'POST',
                data: JSON.stringify({ "casename": casename }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    //custom exception
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static deleteCaseStudy(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "deleteCase",
                async: true,
                type: 'POST',
                data: JSON.stringify({ "casename": casename }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    //custom exception
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static deleteCaseRun(casename, caserunname, resultsOnly) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: this.apiUrl() + "deleteCaseRun",
                async: true,
                type: 'POST',
                data: JSON.stringify({ "casename": casename, "caserunname": caserunname, "resultsOnly": resultsOnly }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr, status, error) {
                    //custom exception
                    if (error == 'UNKNOWN') { error = xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

  

    static prepareCSV(casename, jsonData) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:this.apiUrl() + "prepareCSV",
                async: true,  
                type: 'POST',
                data: JSON.stringify({ "casename": casename, 'jsonData':  jsonData}),
                //dataType: "json",
                contentType: 'application/json',
                success: function (result) {          
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    //custom exception
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }




    static uploadFunction = function () {
        Dropzone.autoDiscover = false;

        var MyDropzone = new Dropzone("#myDropzone", {
            //url: "http://127.0.0.1:5000/upload",
            url: Base.apiUrl() + "uploadCase",
            addRemoveLinks: true,
            maxFilesize: 5120, // 5GB upload size
            
            paramName: "file",    
            chunking: true,
            forceChunking: true,
            parallelChunkUploads: false,
            uploadMultiple: false,
            chunkSize: 500 * 1024 * 1024,  // 500MB chunkovi
            retryChunks: true,
            retryChunksLimit: 5,
            timeout: null,                // bez globalnog timeouta za velike fajlove


            acceptedFiles: "application/zip, .zip",
            dictDefaultMessage: `
                    <span class="text-center">
                      <span class="font-lg visible-xs-block visible-sm-block visible-lg-block"><span class="font-lg">
                        <i class="fa fa-caret-right text-danger"></i> Drop Case <span class="font-xs">to restore
                      </span>
                    </span>
                    <span>&nbsp&nbsp<h4 class="display-inline"> (Or Click)</h4></span> `,
            dictResponseError: 'Error uploading file!',
            dictFileTooBig: ` <i class="fa fa-caret-right text-danger"></i>Filers too big!`,
            dictRemoveFile: `Remove Case!`,
            dictInvalidFileType: "Not valid Osemosys ver 1.0 case!",
            // accept: function(file, done) {
            //   if (file.name == "justinbieber.jpg") {
            //     done("Naha, you don't.");
            //   }
            //   else { done(); }
            // },
            success: function (file, response) {
                console.log('response ', response   )
           
                if (response.response[0]['status_code'] == 'success') {
                    let casename = response.response[0]['casename'];
                         console.log('casename ', casename   )
                    Html.apendModel(casename);
                    Message.bigBoxSuccess("Upload response", response.response[0]['message'], null);
                    //value.previewElement.innerHTML = "";
                    $('#modalrestore').modal('toggle');
                    if (Base.AWS_SYNC == 1) {
                        SyncS3.deleteResultsPreSync(casename)
                            .then(response => {
                                SyncS3.uploadSync(casename);
                            });
                    }
                } else if (response.response[0]['status_code'] == 'warning') {

                }
                // $.each(file, function (key, value) {
                //     if (response.response[key]['status_code'] == 'success') {

                //         //let casename = value.name.slice(0, -4)
                //         let casename = response.response[key]['casename'];
                //         Html.apendModel(casename);
                //         Message.bigBoxSuccess("Upload response", response.response[key]['message'], null);
                //         value.previewElement.innerHTML = "";
                //         $('#modalrestore').modal('toggle');
                //         if (Base.AWS_SYNC == 1) {
                //             SyncS3.deleteResultsPreSync(casename)
                //                 .then(response => {
                //                     SyncS3.uploadSync(casename);
                //                 });
                //         }

                //     } else if (response.response[key]['status_code'] == 'warning') {
                //         $('.dz-file-preview').removeClass("dz-success").addClass("dz-error")
                //         //$(".dz-error-mark svg").css("background", "red"); 
                //         //Message.bigBoxWarning("Upload response", response.response[key]['message'], null);
                //         let casename = response.response[key]['casename'];
                //         Html.apendModel(casename);
                //         Message.bigBoxSuccess("Upload response", response.response[key]['message'], null);
                //         Message.warningOsy(response.response[key]['message_warning'])
                //         value.previewElement.innerHTML = "";
                //         $('#modalrestore').modal('toggle');
                //         if (Base.AWS_SYNC == 1) {
                //             SyncS3.deleteResultsPreSync(casename)
                //                 .then(response => {
                //                     SyncS3.uploadSync(casename);
                //                 });
                //         }
                //     } else if (response.response[key]['status_code'] == 'error') {
                //         $('.dz-file-preview').removeClass("dz-success").addClass("dz-error")
                //         //$(".dz-error-mark svg").css("background", "red"); 
                //         Message.bigBoxDanger("Upload response", response.response[key]['message'], null);
                //     }
                // });
            },
            error: function (file, error) {
                Message.bigBoxDanger("Upload response", file.name + " failed to upload! " + error + " Please remove from dropzone.", null);
            },
            
        });
    }

    static uploadXls = function () {
            var casename = $("#osy-casename").val().trim();
            //console.log('casename ', casename)
            var MyDropzone = new Dropzone("div#importDropzone", {
                //url: "http://127.0.0.1:5000/upload",
                url: Base.apiUrl() + "uploadXls",
                addRemoveLinks: true,
                maxFilesize: 1024,//2GB upload size
                uploadMultiple: false,
                acceptedFiles: ".xlsx",
                dictDefaultMessage: `
                        <span class="text-center">
                          <span class="font-lg visible-xs-block visible-sm-block visible-lg-block"><span class="font-lg">
                            <i class="fa fa-caret-right text-danger"></i> Drop .xls template <span class="font-xs">to import
                          </span>
                        </span>
                        <span>&nbsp&nbsp<h4 class="display-inline"> (Or Click)</h4></span> `,
                dictResponseError: 'Error uploading file!',
                dictFileTooBig: ` <i class="fa fa-caret-right text-danger"></i>Filers too big!`,
                dictRemoveFile: `Remove Case!`,
                dictInvalidFileType: "Not valid .xlsx file!",
                success: function (file, response) {
                    //console.log('file ',file )
                    console.log('response ', response)
                    console.log('response ', response.template)
                    console.log('file ', file.name)
                    let res = response.response[0];
                    if (res['status_code'] == 'success') {
                        Html.enableImportProcess();
                        Message.successOsy(res['message']);
                        
                        Message.bigBoxSuccess("Upload response", res['message'], 3000);
                        $("#osy-template").val(res.template);
                        $('#modalrestore').modal('toggle');

                    } else if (res['status_code'] == 'warning') {
                        Message.warningOsy(res['message']);
                        $("#osy-newImport").show();
                        Message.bigBoxWarning("Upload response", res['message'], null);
                    } else if (res['status_code'] == 'error') {
                        Message.dangerOsy(res['message'])
                        $("#osy-newImport").show();
                        Message.bigBoxDanger("Upload response", res['message'], null);
                    }
                },
                error: function (file, error) {
                    Message.bigBoxDanger("Upload response", file.name + " failed to upload! " + error + " Please remove from dropzone.", null);
                },
            });
    }
}