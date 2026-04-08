import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Model } from "../Model/DataFile.Model.js";
import { MessageSelect } from "./MessageSelect.js";
import { DefaultObj } from "../../Classes/DefaultObj.Class.js";
import { Sidebar } from "./Sidebar.js";

export default class DataFile {
    static onLoad() {
        Message.loaderStart('Loading data...');
        Base.getSession()
            .then(response => {
                let casename = response.session;
                const promise = [];
                promise.push(casename);
                let genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const resData = Osemosys.getResultData(casename, 'resData.json');
                promise.push(resData);
                const modelFile = Osemosys.readModelFile();
                promise.push(modelFile);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, resData, modelFile] = data;
                let model = new Model(casename, genData, resData, modelFile, "DataFile");
                if (casename) {
                    this.initPage(model);
                } else {
                    Message.loaderEnd();
                    MessageSelect.init(DataFile.refreshPage.bind(DataFile));
                }
            })
            .catch(error => {
                Message.loaderEnd();
                Message.danger(error);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        //console.log('model ', model)
        //Navbar.initPage(model.casename, model.pageId);
        Html.title(model.casename, model.title, "");
        Html.renderCases(model.cases);
        Html.renderModelFile(model.modelFile);
        //potrebno je napraviti render svih scenarija (mozda je dodan novi scenario u medjuvremenu), on mora biti dodan u listu scenarija po case run samo sto nece biti aktivan
        // Html.renderScOrder(model.scBycs[model.cs]);
        //console.log('model.scenarios ',model.scenarios)
        Html.renderScOrder(model.scenarios);
        if (model.casename == null) {
            Message.info("Please select model or create new Model!");
        }
        if (model.scenariosCount > 1) {
            $('#scCommand').show();
        }
        //loadScript("References/smartadmin/js/plugin/jquery-nestable/jquery.nestable.min.js", Nestable.init.bind(null));
        pageSetUp();
        this.initEvents(model);
    }

    static refreshPage(casename) {
        Message.loaderStart('Loading data...');
        Base.setSession(casename)
            .then(response => {
                Message.clearMessages();
                const promise = [];
                promise.push(casename);
                let genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const resData = Osemosys.getResultData(casename, 'resData.json');
                promise.push(resData);
                const modelFile = Osemosys.readModelFile();
                promise.push(modelFile);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, resData, modelFile] = data;
                let model = new Model(casename, genData, resData, modelFile, "DataFile");
                $(".DataFile").hide();
                $("#osy-DataFile").empty();
                $("#osy-runOutput").empty();
                $("#osy-lpOutput").empty();
                // $("#osy-downloadDataFile").hide();
                // $("#osy-downloadResultsFile").hide();
                $("#osy-solver").hide();
                $("#osy-run").hide();
                $(".runOutput").hide();
                $(".lpOutput").hide();
                $(".Results").hide();
                DataFile.initPage(model);
                DataFile.initEvents(model);
            })
            .catch(error => {
                Message.loaderEnd();
                Message.bigBoxInfo(error);
            })
    }

    static initEvents(model) {
        const renderLogText = (selector, primary, secondary = '') => {
            Html.renderPreformatted(selector, `${primary || ''}${secondary || ''}`);
        };

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            DataFile.refreshPage(casename);
            Message.smallBoxInfo("Case selection", casename + " is selected!", 3000);
        });

        $("#osy-logFile").off('click');
        $("#osy-logFile").on('click', function (event) {
            Message.loaderStart('Generating log file!')
            Osemosys.readLogFile()
            .then(response => {
                Message.loaderEnd();
                Html.renderPreformatted('#osy-logFiletxt', response, 'No runtime log available yet.\n');
                $("#osy-LogFileModal").modal("show");
            })
            .catch(error => {
                Message.loaderEnd();
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        $("#osy-btnScOrder").off('click');
        $("#osy-btnScOrder").on('click', function (event) {
            // console.log('model, ', model)
            // console.log('model.scenarios ',model.scenarios);
            // console.log('model.scBycs[model.cs] ',model.scBycs)
            if(model.cs in  model.scBycs){
                Html.renderScOrder( model.scBycs[model.cs]);
            }else{
                Html.renderScOrder(model.scenarios);
            }

            //nove scenarije dodjeamo sad u modelu ovaj dio je nepotreban
            // if(model.cs in  model.scBycs){
            //     //pored originalnih scenarija u caserunu, potrebno dodati eventualno nove
            //     //scenarije koji su dodani poslije uspjesnog RUN-a, kao neaktivne
            //     let sccsMap = {};
            //     $.each(model.scBycs[model.cs], function (id, scObj) {
            //         sccsMap[scObj.ScenarioId] = scObj;
            //     });
            //     //create shallow copy of array
            //     let scArray = model.scBycs[model.cs].slice()
            //     $.each(model.scenarios, function (key, obj) {
            //         if(obj.ScenarioId in sccsMap === false){
            //             console.log('obj.Scenario ', obj.Scenario)
            //             let sc = JSON.parse(JSON.stringify(obj));
            //             sc.Active = false;
            //             console.log('sc ', sc)
            //             scArray.push(sc);
            //         }
            //     });
            //     Html.renderScOrder(scArray);
            // }else{
            //     Html.renderScOrder(model.scenarios);
            // }

        });

        function setAllCheckboxes(state) {
            // Targetiramo checkboxove SAMO u #osy-scOrder (SC_0 ostaje netaknut jer je disabled i u #osy-sc0)
            $('#osy-scOrder input[type="checkbox"]:not(:disabled)')
                .prop('checked', state)
                .trigger('change'); // ako imaš logiku na change eventu
        }

        function syncToggleAllButton() {
            const $btn = $('#toggle-all');
            const $boxes = $('#osy-scOrder input[type="checkbox"]:not(:disabled)');
            const allChecked = $boxes.length > 0 && !$boxes.is(':not(:checked)');
            const $icon = $btn.find('i.fa');

            if (allChecked) {
                $icon.removeClass('fa-square-o').addClass('fa-check-square-o');
                $btn.find('span').text('Uncheck all');
            } else {
                $icon.removeClass('fa-check-square-o').addClass('fa-square-o');
                $btn.find('span').text('Check all');
            }
        }

        syncToggleAllButton();

        $("#toggle-all").off('click');
        $('#toggle-all').on('click', function (e) {
            
            e.preventDefault();
            e.stopPropagation();

            const $btn = $(this);
            // Skup svih "normalnih" checkboxova (osim disabled i osim SC_0)
            const $boxes = $('#osy-scOrder input[type="checkbox"]:not(:disabled)');
            // Provjera: ima li ijedan nečekiran?
            const anyUnchecked = $boxes.is(':not(:checked)');

            // Ako ima nečekiranih → čekiraj sve, inače → poništi sve
            setAllCheckboxes(anyUnchecked);

            syncToggleAllButton();

        });


        $("#btnSaveOrder").off('click');
        $("#btnSaveOrder").on('click', function (event) {
            Message.clearMessages();
            Message.bigBoxWarning('Scenario Order Updated', 'You have updated the order of scenarios. To apply your changes, please click Update Case.', 4000);
            $('#osy-order').modal('toggle');

            //nema potrebe da spasavmo scenario order jer se on ada nalazi u resData
            // let order = $("#osy-scOrder").jqxSortable("toArray")
            // var scAcitive = new Array();
            // $.each($('input[type="checkbox"]:checked'), function (key, value) {
            //     scAcitive.push($(value).attr("id"));
            // });
            // let scOrder = DefaultObj.defaultScenario(true);

            // $.each(order, function (id, sc) {
            //     let tmp = {};
            //     if (scAcitive.includes(sc)) {
            //         tmp['ScenarioId'] = sc;
            //         tmp['Scenario'] = model.scMap[sc]['Scenario'];
            //         tmp['Desc'] = model.scMap[sc]['Desc'];
            //         tmp['Active'] = true
            //     } else {
            //         tmp['ScenarioId'] = sc;
            //         tmp['Scenario'] = model.scMap[sc]['Scenario'];
            //         tmp['Desc'] = model.scMap[sc]['Desc'];
            //         tmp['Active'] = false;
            //     }
            //     scOrder.push(tmp);
            // });

            // Osemosys.saveScOrder(scOrder, model.casename)
            // .then(response => {
            //     if (response.status_code == "success") {
            //         $('#osy-order').modal('toggle');
            //         model.scenarios = scOrder;
            //         Message.clearMessages();
            //         Message.bigBoxSuccess('Sceanario order', response.message, 3000);
            //         //sync S3
            //         if (Base.AWS_SYNC == 1) {
            //             Base.updateSync(model.casename, "genData.json");
            //         }
            //     }
            // })
            // .catch(error => {
            //     Message.bigBoxDanger('Error message', error, null);
            // })
        });

        $("#osy-caseRun").jqxValidator({
            hintType: 'label',
            animationDuration: 500,
            rules: [
                { input: '#osy-casename', message: "Case name is required field!", action: 'keyup', rule: 'required' },
                {
                    input: '#osy-casename', message: "Entered case name is not allowed!", action: 'keyup', rule: function (input, commit) {
                        var casename = $("#osy-casename").val();
                        var result = (/^[a-zA-Z0-9-_ ]*$/.test(casename));
                        return result;
                    }
                }
            ]
        });

        let update = false;
        $("#osy-createCaseRun").off('click');
        $("#osy-createCaseRun").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            $("#osy-caseRun").jqxValidator('validate')
        });

        $("#osy-updateCaseRun").off('click');
        $("#osy-updateCaseRun").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            update = true;
            $("#osy-caseRun").jqxValidator('validate')
        });

        $("#osy-newCaseRun").off('click');
        $("#osy-newCaseRun").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            update = false;
            Html.title(model.casename, model.title, "");
            Html.renderScOrder(model.scenarios);
            model.cs = '';
            Message.clearMessages();
            $("#osy-casename").val(null);
            $("#osy-desc").val(null);
            $('#tabs a[href="#tabCases"]').tab('show');
            $("#osy-createCaseRun").show();
            $("#osy-updateCaseRun").hide();
            $("#osy-newCaseRun").hide();

            $("#osy-runCaseDiv").hide();
            $("#osy-generateDataFile").hide();
            $("#osy-solver").hide();
            $("#osy-run").hide();

            $(".runOutput").hide();
            $(".lpOutput").hide();
            $(".DataFile").hide();
            $(".Results").hide();

            $(".batchOutput").hide();
            $("#osy-batchRun").hide();
            $('.checkbox').prop('checked', false);
        });

        $("#osy-caseRun").off('validationSuccess');
        $("#osy-caseRun").on('validationSuccess', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            Pace.restart();

            var caserunname = $("#osy-casename").val();
            let oldcaserunname = model.cs;
            var desc = $("#osy-desc").val();

            let order = $("#osy-scOrder").jqxSortable("toArray")
            var scAcitive = new Array();

            $.each($('input[type="checkbox"]:checked'), function (key, value) {
                scAcitive.push($(value).attr("id"));
            });

            let scOrder = DefaultObj.defaultScenario(true);
            $.each(order, function (id, sc) {
                let tmp = {};
                if (scAcitive.includes(sc)) {
                    tmp['ScenarioId'] = sc;
                    tmp['Scenario'] = model.scMap[sc]['Scenario'];
                    tmp['Desc'] = model.scMap[sc]['Desc'];
                    tmp['Active'] = true
                } else {
                    tmp['ScenarioId'] = sc;
                    tmp['Scenario'] = model.scMap[sc]['Scenario'];
                    tmp['Desc'] = model.scMap[sc]['Desc'];
                    tmp['Active'] = false;
                }
                scOrder.push(tmp);
            });

            let caseId = DefaultObj.getId('CS');

            let caseData = {
                "Case": caserunname,
                "CaseId": caseId,
                "Desc": desc,
                "Runtime": Date().toLocaleString('en-US', { hour12: false, hour: "numeric", minute: "numeric" }),
                "Scenarios": scOrder
            }

            if (update) {
                Osemosys.updateCaseRun(model.casename, caserunname, oldcaserunname, caseData)
                .then(response => {
                    Message.clearMessages();
                    if (response.status_code == 'success') {
                        model.cs = caserunname;
                        $.each(model.cases, function (id, cs) {
                            if (cs.Case == oldcaserunname) {
                                model.cases[id] = caseData;
                            }
                        });
                        model.scBycs[model.cs] = scOrder;
                        Html.title(model.casename, model.title, caserunname);
                        Html.renderCases(model.cases);
                        $('#tabs a[href="#tabCases"]').tab('show');
                        $("#osy-runCaseDiv").show();
                        $("#osy-caseRunName").text(caserunname);
                        $('#osy-generateDataFile').show();
                        $("#osy-newCaseRun").show();
                        $(".DataFile").hide();
                        $(".runOutput").hide();
                        $(".lpOutput").hide();
                        $(".Results").hide();
                        $(".batchOutput").hide();
                        $("#osy-batchRun").hide();
                        $('.checkbox').prop('checked', false);
                        Message.smallBoxInfo('Generate message', response.message, 3000);
                    }
                    if (response.status_code == 'exist') {
                        Message.smallBoxWarning('Generate message', response.message, 3000);
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
            } else {
                Osemosys.createCaseRun(model.casename, caserunname, caseData)
                .then(response => {
                    Message.clearMessages();
                    if (response.status_code == 'success') {
                        $("#osy-runCaseDiv").show();
                        $("#osy-caseRunName").text(caserunname);
                        $('#osy-generateDataFile').show();
                        model.cs = caserunname;
                        model.cases.push(caseData);
                        model.scBycs[model.cs] = scOrder;
                        $("#osy-createCaseRun").hide();
                        $("#osy-updateCaseRun").show();
                        $("#osy-newCaseRun").show();

                        $(".batchOutput").hide();
                        $("#osy-batchRun").hide();
                        $('.checkbox').prop('checked', false);
                        Html.renderCases(model.cases);
                        Html.title(model.casename, model.title, caserunname);
                        Message.smallBoxInfo('Generate message', response.message, 3000);
                    }
                    if (response.status_code == 'exist') {
                        Message.smallBoxWarning('Generate message', response.message, 3000);
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
            }

        });

        $("#osy-generateDataFile").off('click');
        $("#osy-generateDataFile").on('click', function (event) {
            Pace.restart();
            Message.loaderStart('Generating data file!')
            Osemosys.generateDataFile(model.casename, model.cs)
            .then(response => {
                if (response.status_code == "success") {
                    const promise = [];
                    let DataFile = Osemosys.readDataFile(model.casename, model.cs);
                    promise.push(DataFile);
                    promise.push(response.message);
                    return Promise.all(promise);
                }
            })
            .then(response => {
                let [DataFile, message] = response;
                $(".DataFile").show();
                $("#osy-runOutput").empty();
                $("#osy-lpOutput").empty();
                $(".runOutput").hide();
                $(".lpOutput").hide();
                $(".Results").hide();
                $(".batchOutput").hide();
                Html.renderDataFile(DataFile, model)
                ///////////////////////////////////////////////////////////////////
                //$("#osy-downloadDataFile").show();
                //ne moramo updateovati S3 sa data file
                // if (Base.AWS_SYNC == 1){
                //     Base.updateSync(model.casename, "data.txt");
                // }
                if (Base.HEROKU == 0) {
                    $("#osy-run").show();
                    //$("#osy-solver").show();
                }
                //Message.clearMessages();
                //Message.bigBoxSuccess('Generate message', message, 3000);
                Message.loaderEnd();
                Message.smallBoxInfo('Generate message', message, 3000);
            })
            .catch(error => {
                Message.loaderEnd();
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        $("#osy-run").off('click');
        $("#osy-run").on('click', function (event) {
            Pace.restart();
            Message.loaderStart('Optimization in process!')

            
            // const logBox = document.getElementById("logBox");
            // const eventSource = new EventSource("http://127.0.0.1:5002/stream_logs");

            // eventSource.onmessage = function (e) {
            //     console.log('e.data ', e.data)
            //     logBox.innerHTML += e.data + "<br>";
            //     logBox.scrollTop = logBox.scrollHeight;   // auto-scroll
            // };





            //////////////////////////////////////////////////////////////////////////////////////

            //promijenjeno da radimo samo sa cBCsolverom
            //let solver = $('input[name="solver"]:checked').val();
            let solver = 'cbc';
            Osemosys.run(model.casename, solver, model.cs)
            .then(response => {
                Message.clearMessages();
                //console.log('response ',response)
                if (response.status_code == "success") {
                    Message.loaderEnd();
                    $(".runOutput").show();
                    $(".lpOutput").show();
                    $(".Results").show();
                    $(".batchOutput").hide();
                    $("#osy-batchOutput").empty();
                    $("#osy-runOutput").empty();
                    renderLogText('#osy-runOutput', response.cbc_message, response.cbc_stdmsg);
                    $("#osy-lpOutput").empty();
                    renderLogText('#osy-lpOutput', response.glpk_message, response.glpk_stdmsg);
                    Base.getResultCSV(model.casename, model.cs)
                        .then(csvs => {
                            Html.renderCSV(csvs, model.cs)
                        });
                    Sidebar.Reload(model.casename);
                    Message.clearMessages();
                    Message.successOsy( response.timer);
                    Message.bigBoxSuccess('Run message', response.timer, 3000);
                }
                if (response.status_code == "warning") {
                    Message.loaderEnd();
                    $(".runOutput").show();
                    $(".lpOutput").show();
                    $(".Results").show();
                    $(".batchOutput").hide();
                    $("#osy-batchOutput").empty();
                    $("#osy-runOutput").empty();
                    renderLogText('#osy-runOutput', response.cbc_message, response.cbc_stdmsg);
                    $("#osy-lpOutput").empty();
                    renderLogText('#osy-lpOutput', response.glpk_message, response.glpk_stdmsg);
                    Base.getResultCSV(model.casename, model.cs)
                        .then(csvs => {
                            Html.renderCSV(csvs, model.cs)
                        });
                    Sidebar.Reload(model.casename);
                    Message.clearMessages();
                    Message.warningOsy( response.timer );
                }
                if (response.status_code == "error") {
                    Message.loaderEnd();
                    $(".runOutput").show();
                    $(".lpOutput").show();
                    $(".Results").show();
                    $(".batchOutput").hide();
                    $("#osy-batchOutput").empty();
                    $("#osy-runOutput").empty();
                    renderLogText('#osy-runOutput', response.cbc_message, response.cbc_stdmsg);
                    $("#osy-lpOutput").empty();
                    renderLogText('#osy-lpOutput', response.glpk_message, response.glpk_stdmsg);
                    Message.clearMessages();
                    // let errormsg = '';
                    // if (response.glpk_message != "" || response.glpk_stdmsg != "") {
                    //     errormsg += 'Error occured during creation of LP file, GLPK run! See LP file (GLPK) log for more details. '
                    // }
                    // if (response.cbc_message != "" || response.cbc_stdmsg != "") {
                    //     errormsg += 'Error occured during optimization process, CBC run! See CBC solver log for more details.'
                    // }

                    // Message.dangerOsy(errormsg);
                    Message.dangerOsy( response.timer );
                }
            })
            .catch(error => {
                console.log('error ',error)
                Message.loaderEnd();
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        //$("#osy-Cases").off('click');
        $("#osy-Cases").on('click', '.selectCS', function (e) {
            //$(document).delegate(".selectCS","click",function(e){
            e.preventDefault();
            e.stopImmediatePropagation();
            Html.renderScOrder( model.scBycs[model.cs]);
            Message.clearMessages();
            console.log('select, ', model)
            var caserunanme = $(this).attr('data-ps');
            model.cs = caserunanme;
            Html.renderScOrder( model.scBycs[model.cs]);

            Html.resData(model);
            Html.title(model.casename, model.title, caserunanme);

            $("#osy-createCaseRun").hide();
            $("#osy-updateCaseRun").show();
            $("#osy-newCaseRun").show();

            $("#osy-generateDataFile").hide();
            $("#osy-solver").hide();
            $("#osy-run").hide();
            $("#osy-runCaseDiv").hide();

            $(".runOutput").hide();
            $(".lpOutput").hide();
            $(".batchOutput").hide();
            $("#osy-batchRun").hide();
            $('.checkbox').prop('checked', false);

            Osemosys.readDataFile(model.casename, model.cs)
            .then(response => {
                let DataFile = response;
                const promise = [];
                promise.push(DataFile);
                let ResultCSV = Base.getResultCSV(model.casename, model.cs)
                promise.push(ResultCSV);
                return Promise.all(promise);
            })
            .then(data => {
                let [DataFile, ResultCSV] = data;
                console.log('data ', data)
                if (ResultCSV.length != 0) {
                    $(".Results").show();
                    Html.renderCSV(ResultCSV, model.cs)
                }
                if (DataFile) {
                    $(".DataFile").show();
                    $("#osy-runCaseDiv").show();
                    $("#osy-caseRunName").text(model.cs);
                    $("#osy-generateDataFile").show();

                    Html.renderDataFile(DataFile, model);
                }
                else if(!DataFile && ResultCSV.length == 0){
                    $(".DataFile").hide();
                    $(".Results").hide();
                    //$("#osy-generateDataFile").hide();

                    $("#osy-runCaseDiv").show();
                    $("#osy-caseRunName").text(model.cs);
                    $("#osy-generateDataFile").show();
                    Message.smallBoxWarning("Run case message", "Please generate data file!", 3000);
                }
            })
            .catch(error => {
                Message.danger(error);
            });
            Message.smallBoxInfo("Case selection", caserunanme + " is selected!", 3000);
        });


        //$("#osy-Cases").off('click');
        $("#osy-Cases").on('click', '.validateInputs', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Message.clearMessages();
            var caserunanme = $(this).attr('data-ps');
            //console.log('caserunanme ', caserunanme)
            Osemosys.validateInputs(model.casename, caserunanme)
            .then(response => {
                //console.log('response ', response)
                if (response.status_code == "success") {
                    $('#osy-validation').modal('toggle');
                    $("#valCasrunname").text(caserunanme)
                    Html.renderPreformatted('#valOutput', response.msg);
                }
                if (response.status_code == "warning") {
                    $('#osy-validation').modal('toggle');
                    Html.renderPreformatted('#valOutput', response.msg);
                }
                if (response.status_code == "error") {
                    //Message.warningOsy(response.msg);
                    Message.smallBoxWarning('Data file warning', response.msg, 8000)
                }
            })
            .catch(error => {
                Message.danger(error);
            });
        });

        //$(document).delegate(".deleteCase", "click", function (e) {
        // $(".deleteCase").off('click');
        // $(".deleteCase").on('click', function (e) {
        //$("#osy-Cases").off('click');
        $("#osy-Cases").on('click', '.deleteCase', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var caserunname = $(this).attr('data-ps');
            $.SmartMessageBox({
                title: "Confirmation Box!",
                content: "You are about to delete <b class='danger'>" + caserunname + "</b> case run! Are you sure?",
                buttons: '[No][Yes]'
            }, function (ButtonPressed) {
                if (ButtonPressed === "Yes") {
                    Message.loaderStart('Deleteing case data...');
                    Base.deleteCaseRun(model.casename, caserunname, false)
                        .then(response => {
                            Message.clearMessages();
                            Message.loaderEnd();
                            if (response.status_code == "success") {
                                Message.bigBoxSuccess('Delete message', response.message, 3000);
                                //REFRESH
                                Html.removeCase(caserunname);
                                //remove case from model
                                model.cases = model.cases.filter(function(el) { return el.Case != caserunname; });
                                delete model.scBycs[caserunname];

                                //relod sidebar
                                Sidebar.Reload(model.casename);

                                if (model.cs == caserunname || model.cs == ''){
                                    Html.title(model.casename, model.title, '');
                                    model.cs = null;
                                    $("#osy-casename").val(null);
                                    $("#osy-desc").val(null);
                                    $("#osy-createCaseRun").show();
                                    $("#osy-updateCaseRun").hide();
                                    $("#osy-newCaseRun").hide();

                                    $("#osy-generateDataFile").hide();
                                    $("#osy-runCaseDiv").hide();
                                    $("#osy-solver").hide();
                                    $("#osy-run").hide();

                                    $(".runOutput").hide();
                                    $(".lpOutput").hide();
                                    $(".DataFile").hide();
                                    $(".Results").hide();

                                    $(".batchOutput").hide();
                                    $("#osy-batchRun").hide();
                                    $('.checkbox').prop('checked', false);
                                }
                                //remove case from view json files
                                //sync with s3
                                if (Base.AWS_SYNC == 1) {
                                    SyncS3.deleteSync(caserunname);
                                }
                            }
                            // if(response.status_code=="success_session"){
                            //     Message.bigBoxSuccess('Delete message', response.message, 3000);
                            //     Message.info( "Please select existing or create new case to proceed!");
                            //     if (model.casename = casename){
                            //         // Sidebar.Load(null, null);
                            //         Sidebar.Reload(null);
                            //         //Routes.removeRoutes(model.PARAMETERS);
                            //     }
                            //     //REFRESH
                            //     Html.removeCase(casename);
                            //     if (Base.AWS_SYNC == 1){
                            //         Base.deleteSync(casename);
                            //     }
                            // }
                            if (response.status_code == "info") {
                                Message.info(response.message);
                            }
                            if (response.status_code == "warning") {
                                Message.warning(response.message);
                            }

                        })
                        .catch(error => {
                            console.log(error)
                            Message.danger(error);
                        });
                }
                if (ButtonPressed === "No") {
                    Message.bigBoxInfo("Confirmation message", "You pressed No...", 3000)
                }
            });
            //e.preventDefault();
            e.stopImmediatePropagation();
        });

        $("#osy-Cases").on('click', '.deleteCaseResults', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var caserunname = $(this).attr('data-ps');
            $.SmartMessageBox({
                title: "Confirmation Box!",
                content: "You are about to delete <b class='danger'>" + caserunname + "</b> case run results! Are you sure?",
                buttons: '[No][Yes]'
            }, function (ButtonPressed) {
                if (ButtonPressed === "Yes") {
                    Message.loaderStart('Deleteing case results...');
                    Base.deleteCaseRun(model.casename, caserunname, true)
                        .then(response => {
                            Message.clearMessages();
                            Message.loaderEnd();
                            if (response.status_code == "success") {
                                Message.bigBoxSuccess('Delete message', response.message, 3000);
                                //REFRESH
                                //Html.removeCase(caserunname);
                                //remove case from model
                                //model.cases = model.cases.filter(function(el) { return el.Case != caserunname; });
                                //delete model.scBycs[caserunname];

                                //relod sidebar
                                Sidebar.Reload(model.casename);

                                if (model.cs == caserunname || model.cs == ''){
                                    Html.title(model.casename, model.title, '');
                                    model.cs = null;
                                    // $("#osy-casename").val(null);
                                    // $("#osy-desc").val(null);
                                    // $("#osy-createCaseRun").show();
                                    // $("#osy-updateCaseRun").hide();
                                    // $("#osy-newCaseRun").hide();

                                    // $("#osy-generateDataFile").hide();
                                    // $("#osy-runCaseDiv").hide();
                                    // $("#osy-solver").hide();
                                    // $("#osy-run").hide();

                                    $(".runOutput").hide();
                                    $(".lpOutput").hide();
                                    $(".DataFile").hide();
                                    $(".Results").hide();

                                    $(".batchOutput").hide();
                                    $("#osy-batchRun").hide();
                                    $("#osy-runCaseDiv").hide();
                                    $('.checkbox').prop('checked', false);
                                }
                                //remove case from view json files
                                //sync with s3
                                if (Base.AWS_SYNC == 1) {
                                    SyncS3.deleteSync(caserunname);
                                }
                            }

                            if (response.status_code == "info") {
                                Message.info(response.message);
                            }
                            if (response.status_code == "warning") {
                                Message.warning(response.message);
                            }

                        })
                        .catch(error => {
                            console.log(error)
                            Message.danger(error);
                        });
                }
                if (ButtonPressed === "No") {
                    Message.bigBoxInfo("Confirmation message", "You pressed No...", 3000)
                }
            });
            //e.preventDefault();
            e.stopImmediatePropagation();
        });

        //$(".Cases").off('click');
        $('#osy-Cases').on('click', '.checkbox', function(e){
            // var val = $(this).val();
            // $('input[value!='+val+'].checkboxgroup').attr('checked',false);
            let batchRunCases = [];
            $("input:checkbox[name=type]:checked").each(function(){
                batchRunCases.push($(this).val());
            });
            //console.log('batchRunCases ', batchRunCases)
            if(batchRunCases.length>1){
                //$("#osy-runCaseDiv").show();
                //$("#osy-caseRunName").text("BATCH RUN");
                $('#osy-batchRun').show();
            }
            else{
                //$("#osy-runCaseDiv").hide();
                $('#osy-batchRun').hide();
            }
          });

        $("#osy-batchRun").off('click');
        $("#osy-batchRun").on('click', function (event) {
            //console.log('BATCH RUN')
            Pace.restart();
            Message.loaderStart('BATCH RUN! Plese wait...');

            let batchRunCases = [];
            $("input:checkbox[name=type]:checked").each(function(){
                batchRunCases.push($(this).val());
            });

            Osemosys.batchRun(model.casename, batchRunCases)
            //Osemosys.generateDataFile(model.casename, batchRunCases[0])
            .then(response => {
                Message.loaderEnd();
                //Message.smallBoxInfo('Generate message', response.message, 3000);
                // console.log('response ', response.log);
                // Message.bigBoxDefault("BATCH RUN!", response.log)
                $(".runOutput").hide();
                $(".lpOutput").hide();
                $(".Results").hide();
                $("#osy-runOutput").empty();
                $("#osy-lpOutput").empty();

                Sidebar.Reload(model.casename);
                Message.clearMessages();

                if(response.status == 'Success'){
                    Message.successOsy('<pre>' + response.msg + '</pre>');
                    //Message.successOsy('<pre>Run finished in ' + response.time + ' \n' + response.msg + '</pre>');
                }
                else{
                    Message.dangerOsy('<pre>' + response.msg + '</pre>');
                }


                $(".batchOutput").show();
                $("#osy-batchOutput").empty();
                Html.renderPreformatted('#osy-batchOutput', response.log);

            })
            .catch(error => {
                Message.bigBoxDanger(error)
            })

        });

        $("#osy-cleanUp").off('click');
        $("#osy-cleanUp").on('click', function (event) {
            //console.log('BATCH RUN')
            Pace.restart();
            Message.loaderStart('Recycle all results! Plese wait...');

            Osemosys.cleanUp(model.casename)
            .then(response => {
                Message.loaderEnd();
                $(".runOutput").hide();
                $(".DataFile").hide();
                $(".lpOutput").hide();
                $(".Results").hide();
                $(".batchOutput").hide();
                $("#osy-runCaseDiv").hide();
                $("#osy-runOutput").empty();
                $("#osy-lpOutput").empty();
                $('.Cases').tab('show');

                console.log('response clean up ', response) 

                Sidebar.Reload(model.casename);
                Message.clearMessages();

                if(response.status_code == 'success'){
                    Message.bigBoxSuccess('Delete message', response.message, 3000);
                    //Message.successOsy('<pre>' + response.message + '</pre>');
                    //Message.successOsy('<pre>Run finished in ' + response.time + ' \n' + response.msg + '</pre>');
                }
                else{
                    Message.dangerOsy('<pre>' + response.message + '</pre>');
                }
            })
            .catch(error => {
                Message.bigBoxDanger(error)
            })

        });

        Message.loaderEnd();
    }
}

