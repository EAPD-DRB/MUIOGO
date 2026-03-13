import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Model } from "../Model/DataFile.Model.js";
import { MessageSelect } from "./MessageSelect.js";
import { DefaultObj } from "../../Classes/DefaultObj.Class.js";
import { Sidebar } from "./Sidebar.js";

export default class DataFile {
    static async onLoad() {
        Message.loaderStart('Loading data...');
        try {
            const response = await Base.getSession();
            const casename = response.session;
            const [genData, resData] = await Promise.all([
                Osemosys.getData(casename, 'genData.json'),
                Osemosys.getResultData(casename, 'resData.json'),
            ]);
            const model = new Model(casename, genData, resData, "DataFile");
            if (casename) {
                this.initPage(model);
            } else {
                Message.loaderEnd();
                MessageSelect.init(DataFile.refreshPage.bind(DataFile));
            }
        } catch (error) {
            Message.loaderEnd();
            Message.danger(error);
        }
    }

    static initPage(model) {
        Message.clearMessages();
        //console.log('model ', model)
        //Navbar.initPage(model.casename, model.pageId);
        Html.title(model.casename, model.title, "");
        Html.renderCases(model.cases);
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

    static async refreshPage(casename) {
        Message.loaderStart('Loading data...');
        try {
            await Base.setSession(casename);
            Message.clearMessages();
            const [genData, resData] = await Promise.all([
                Osemosys.getData(casename, 'genData.json'),
                Osemosys.getResultData(casename, 'resData.json'),
            ]);
            const model = new Model(casename, genData, resData, "DataFile");
            $(".DataFile").hide();
            $("#osy-DataFile").empty();
            $("#osy-runOutput").empty();
            $("#osy-lpOutput").empty();
            $("#osy-solver").hide();
            $("#osy-run").hide();
            $(".runOutput").hide();
            $(".lpOutput").hide();
            $(".Results").hide();
            DataFile.initPage(model);
            DataFile.initEvents(model);
        } catch (error) {
            Message.loaderEnd();
            Message.bigBoxInfo(error);
        }
    }

    static initEvents(model) {

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            DataFile.refreshPage(casename);
            Message.smallBoxInfo("Case selection", casename + " is selected!", 3000);
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

        $("#btnSaveOrder").off('click');
        $("#btnSaveOrder").on('click', function (event) {
            Message.clearMessages();
            Message.bigBoxSuccess('Sceanario order', 'You have updated scenarios order data!', 3000);
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
        $("#osy-caseRun").on('validationSuccess', async function (event) {
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

            try {
                if (update) {
                    const response = await Osemosys.updateCaseRun(model.casename, caserunname, oldcaserunname, caseData);
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
                } else {
                    const response = await Osemosys.createCaseRun(model.casename, caserunname, caseData);
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
                }
            } catch (error) {
                Message.bigBoxDanger('Error message', error, null);
            }
        });

        $("#osy-generateDataFile").off('click');
        $("#osy-generateDataFile").on('click', async function (event) {
            Pace.restart();
            Message.loaderStart('Generating data file!');
            try {
                const genResponse = await Osemosys.generateDataFile(model.casename, model.cs);
                if (genResponse.status_code == "success") {
                    const DataFile = await Osemosys.readDataFile(model.casename, model.cs);
                    const message = genResponse.message;
                    $(".DataFile").show();
                    $("#osy-runOutput").empty();
                    $("#osy-lpOutput").empty();
                    $(".runOutput").hide();
                    $(".lpOutput").hide();
                    $(".Results").hide();
                    $(".batchOutput").hide();
                    Html.renderDataFile(DataFile, model);
                    if (Base.HEROKU == 0) {
                        $("#osy-run").show();
                    }
                    Message.loaderEnd();
                    Message.smallBoxInfo('Generate message', message, 3000);
                }
            } catch (error) {
                Message.loaderEnd();
                Message.bigBoxDanger('Error message', error, null);
            }
        });


        $("#osy-run").off('click');
        $("#osy-run").on('click', async function (event) {
            Pace.restart();
            Message.loaderStart('Optimization in process!');
            let solver = 'cbc';
            try {
                const response = await Osemosys.run(model.casename, solver, model.cs);
                Message.clearMessages();
                if (response.status_code == "success" || response.status_code == "warning") {
                    Message.loaderEnd();
                    $(".runOutput").show();
                    $(".lpOutput").show();
                    $(".Results").show();
                    $(".batchOutput").hide();
                    $("#osy-batchOutput").empty();
                    $("#osy-runOutput").empty();
                    $("#osy-runOutput").html('<pre class="log-output">' + response.cbc_message, response.cbc_stdmsg + '</pre>');
                    $("#osy-lpOutput").empty();
                    $("#osy-lpOutput").html('<pre class="log-output">' + response.glpk_message, response.glpk_stdmsg + '</pre>');
                    const csvs = await Base.getResultCSV(model.casename, model.cs);
                    Html.renderCSV(csvs, model.cs);
                    Sidebar.Reload(model.casename);
                    Message.clearMessages();
                    if (response.status_code == "success") {
                        Message.successOsy(response.timer);
                        Message.bigBoxSuccess('Run message', response.timer, 3000);
                    } else {
                        Message.warningOsy(response.timer);
                    }
                }
                if (response.status_code == "error") {
                    Message.loaderEnd();
                    $(".runOutput").show();
                    $(".lpOutput").show();
                    $(".Results").show();
                    $(".batchOutput").hide();
                    $("#osy-batchOutput").empty();
                    $("#osy-runOutput").empty();
                    $("#osy-runOutput").html('<pre class="log-output">' + response.cbc_message, response.cbc_stdmsg + '</pre>');
                    $("#osy-lpOutput").empty();
                    $("#osy-lpOutput").html('<pre class="log-output">' + response.glpk_message, response.glpk_stdmsg + '</pre>');
                    Message.clearMessages();
                    Message.dangerOsy(response.timer);
                }
            } catch (error) {
                console.log('error ', error);
                Message.loaderEnd();
                Message.bigBoxDanger('Error message', error, null);
            }
        });

        //$("#osy-Cases").off('click');
        $("#osy-Cases").on('click', '.selectCS', async function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Html.renderScOrder(model.scBycs[model.cs]);
            Message.clearMessages();
            console.log('select, ', model);
            var caserunanme = $(this).attr('data-ps');
            model.cs = caserunanme;
            Html.renderScOrder(model.scBycs[model.cs]);

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

            try {
                const [DataFile, ResultCSV] = await Promise.all([
                    Osemosys.readDataFile(model.casename, model.cs),
                    Base.getResultCSV(model.casename, model.cs),
                ]);
                console.log('data ', [DataFile, ResultCSV]);
                if (ResultCSV.length != 0) {
                    $(".Results").show();
                    Html.renderCSV(ResultCSV, model.cs);
                }
                if (DataFile) {
                    $(".DataFile").show();
                    $("#osy-runCaseDiv").show();
                    $("#osy-caseRunName").text(model.cs);
                    $("#osy-generateDataFile").show();
                    Html.renderDataFile(DataFile, model);
                } else if (!DataFile && ResultCSV.length == 0) {
                    $(".DataFile").hide();
                    $(".Results").hide();
                    $("#osy-runCaseDiv").show();
                    $("#osy-caseRunName").text(model.cs);
                    $("#osy-generateDataFile").show();
                    Message.smallBoxWarning("Run case message", "Please generate data file!", 3000);
                }
            } catch (error) {
                Message.danger(error);
            }
            Message.smallBoxInfo("Case selection", caserunanme + " is selected!", 3000);
        });


        //$("#osy-Cases").off('click');
        $("#osy-Cases").on('click', '.validateInputs', async function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Message.clearMessages();
            var caserunanme = $(this).attr('data-ps');
            try {
                const response = await Osemosys.validateInputs(model.casename, caserunanme);
                if (response.status_code == "success") {
                    $('#osy-validation').modal('toggle');
                    $("#valCasrunname").text(caserunanme);
                    $("#valOutput").html('<pre class="log-output">' + response.msg + '</pre>');
                }
                if (response.status_code == "warning") {
                    $('#osy-validation').modal('toggle');
                    $("#valOutput").html('<pre class="log-output">' + response.msg + '</pre>');
                }
                if (response.status_code == "error") {
                    Message.smallBoxWarning('Data file warning', response.msg, 8000);
                }
            } catch (error) {
                Message.danger(error);
            }
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
            }, async function (ButtonPressed) {
                if (ButtonPressed === "Yes") {
                    Message.loaderStart('Deleteing case data...');
                    try {
                        const response = await Base.deleteCaseRun(model.casename, caserunname, false);
                        Message.clearMessages();
                        Message.loaderEnd();
                        if (response.status_code == "success") {
                            Message.bigBoxSuccess('Delete message', response.message, 3000);
                            Html.removeCase(caserunname);
                            model.cases = model.cases.filter(function(el) { return el.Case != caserunname; });
                            delete model.scBycs[caserunname];
                            Sidebar.Reload(model.casename);
                            if (model.cs == caserunname || model.cs == '') {
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
                    } catch (error) {
                        console.log(error);
                        Message.danger(error);
                    }
                }
                if (ButtonPressed === "No") {
                    Message.bigBoxInfo("Confirmation message", "You pressed No...", 3000);
                }
            });
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
            }, async function (ButtonPressed) {
                if (ButtonPressed === "Yes") {
                    Message.loaderStart('Deleteing case results...');
                    try {
                        const response = await Base.deleteCaseRun(model.casename, caserunname, true);
                        Message.clearMessages();
                        Message.loaderEnd();
                        if (response.status_code == "success") {
                            Message.bigBoxSuccess('Delete message', response.message, 3000);
                            Sidebar.Reload(model.casename);
                            if (model.cs == caserunname || model.cs == '') {
                                Html.title(model.casename, model.title, '');
                                model.cs = null;
                                $(".runOutput").hide();
                                $(".lpOutput").hide();
                                $(".DataFile").hide();
                                $(".Results").hide();
                                $(".batchOutput").hide();
                                $("#osy-batchRun").hide();
                                $('.checkbox').prop('checked', false);
                            }
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
                    } catch (error) {
                        console.log(error);
                        Message.danger(error);
                    }
                }
                if (ButtonPressed === "No") {
                    Message.bigBoxInfo("Confirmation message", "You pressed No...", 3000);
                }
            });
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
        $("#osy-batchRun").on('click', async function (event) {
            Pace.restart();
            Message.loaderStart('BATCH RUN! Plese wait...');

            let batchRunCases = [];
            $("input:checkbox[name=type]:checked").each(function() {
                batchRunCases.push($(this).val());
            });

            try {
                const response = await Osemosys.batchRun(model.casename, batchRunCases);
                Message.loaderEnd();
                $(".runOutput").hide();
                $(".lpOutput").hide();
                $(".Results").hide();
                $("#osy-runOutput").empty();
                $("#osy-lpOutput").empty();
                Sidebar.Reload(model.casename);
                Message.clearMessages();
                if (response.status == 'Success') {
                    Message.successOsy('<pre>' + response.msg + '</pre>');
                } else {
                    Message.dangerOsy('<pre>' + response.msg + '</pre>');
                }
                $(".batchOutput").show();
                $("#osy-batchOutput").empty();
                $("#osy-batchOutput").html('<pre class="log-output">' + response.log + '</pre>');
            } catch (error) {
                Message.bigBoxDanger(error);
            }
        });

        $("#osy-cleanUp").off('click');
        $("#osy-cleanUp").on('click', async function () {
            Pace.restart();
            Message.loaderStart('Recycle all results! Plese wait...');

            try {
                const response = await Osemosys.cleanUp(model.casename);
                Message.loaderEnd();
                $(".runOutput").hide();
                $(".lpOutput").hide();
                $(".Results").hide();
                $("#osy-runOutput").empty();
                $("#osy-lpOutput").empty();

                Sidebar.Reload(model.casename);
                Message.clearMessages();

                if (response.status_code == 'success') {
                    Message.bigBoxSuccess('Delete message', response.message, 3000);
                } else {
                    Message.dangerOsy('<pre>' + response.message + '</pre>');
                }
            } catch (error) {
                Message.bigBoxDanger(error);
            }
        });

        Message.loaderEnd();
    }
}





