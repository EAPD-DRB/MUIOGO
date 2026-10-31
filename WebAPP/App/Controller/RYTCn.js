import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RYTCn.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Chart } from "../../Classes/Chart.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RYTCn {
    static onLoad(group, param) {
        Base.getSession()
            .then(response => {
                let casename = response['session'];
                if (casename) {
                    const promise = [];
                    promise.push(casename);
                    const genData = Osemosys.getData(casename, 'genData.json');
                    promise.push(genData);
                    const PARAMETERS = Osemosys.getParamFile();
                    promise.push(PARAMETERS);
                    const RYTCndata = Osemosys.getData(casename, "RYTCn.json");
                    promise.push(RYTCndata);
                    return Promise.all(promise);
                } else {
                    let er = {
                        "message": 'There is no model selected!',
                        "status_code": "CaseError"
                    }
                    return Promise.reject(er);
                    //throw new Error(JSON.stringify(er));
                    //MessageSelect.init(RYTCn.refreshPage.bind(RYTCn));
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTCndata] = data;
                if (RYTCndata['CCM']['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    //throw new Error('Activity');
                    return Promise.reject(er);
                }
                let model = new Model(casename, genData, RYTCndata, group, PARAMETERS, param);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                if (error.status_code == 'CaseError') {
                    MessageSelect.init(RYTCn.refreshPage.bind(RYTCn));
                }
                else if (error.status_code == 'ActivityError') {
                    MessageSelect.activity(RYTCn.refreshPage.bind(RYTCn), error.casename);
                }
                Message.warning(error);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        //Navbar.initPage(model.casename);
        Html.title(model.casename, model.PARAMNAMES[model.param], GROUPNAMES[model.group]);
        Html.ddlParams(model.PARAMETERS['RYTCn'], model.param);
        // Html.ddlTechs(model.techs[model.cons[0]['ConId']], model.techs[model.cons[0]['ConId']][0]['TechId']);
        // Html.ddlCons(model.cons, model.cons[0]['ConId']);

        let $divGrid = $('#osy-gridRYTCn');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, {groupable: false, filterable: true, sortable:true});
        if (model.scenariosCount > 1) {
            Html.lblScenario( model.scenariosCount);
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            Grid.applyGridFilter($divGrid, model.years);
        }
        //pageSetUp();
    }

    static refreshPage(casename) {
        Base.setSession(casename)
            .then(response => {
                const promise = [];
                promise.push(casename);
                const genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const PARAMETERS = Osemosys.getParamFile();
                promise.push(PARAMETERS);
                const RYTCndata = Osemosys.getData(casename, 'RYTCn.json');
                promise.push(RYTCndata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTCndata] = data;
                if (RYTCndata['CCM']['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    //throw new Error('Activity');
                    return Promise.reject(er);
                }
                let model = new Model(casename, genData, RYTCndata, 'RYTCn', PARAMETERS, PARAMETERS['RYTCn'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                setTimeout(function () {
                    if (error.status_code == 'CaseError') {
                        MessageSelect.init(RYTCn.refreshPage.bind(RYTCn));
                    }
                    else if (error.status_code == 'ActivityError') {
                        MessageSelect.activity(RYTCn.refreshPage.bind(RYTCn), error.casename);
                    }
                    Message.warning(error.message);
                }, 500);

            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRYTCn');
        let $divChart = $('#osy-chartRYTCn');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RYTCn.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYTCndata").off('click');
        $("#osy-saveRYTCndata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            let param = $("#osy-ryt").val();
            let rytData = $divGrid.jqxGrid('getboundrows');
            // Persist stable row IDs and values only; grid labels and units are
            // display metadata. Scenario nulls must survive to preserve inheritance.
            let data = JSON.parse(JSON.stringify(rytData, ['ScId', 'TechId', 'ConId'].concat(model.years)));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RYTCn.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RYTCn.json");
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
        });

        $("#osy-ryt").off('change');
        $('#osy-ryt').on('change', function () {
            Message.clearMessages();
            Html.title(model.casename, model.PARAMNAMES[this.value], GROUPNAMES[model.group]);
            model.srcGrid.root = this.value;
            model.param = this.value;
            $divGrid.jqxGrid('updatebounddata');
            Grid.applyGridFilter($divGrid, model.years);
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
        });

        // $("#osy-cons").off('change');
        // $('#osy-cons').on('change', function () {
        //     var param = $("#osy-ryt").val();
        //     Html.ddlTechs(model.techs[this.value], model.techs[this.value][0]['TechId']);
        //     //var con = $( "#osy-cons" ).val();
        //     var configChart = $divChart.jqxChart('getInstance');
        //     configChart.source.records = model.chartData[param][model.techs[this.value][0]['TechId']][this.value];
        //     configChart.update();
        // });

        // $("#osy-techs").off('change');
        // $('#osy-techs').on('change', function () {
        //     var param = $("#osy-ryt").val();
        //     var con = $("#osy-cons").val();
        //     var configChart = $divChart.jqxChart('getInstance');
        //     configChart.source.records = model.chartData[param][this.value][con];
        //     configChart.update();
        // });


        $("#osy-scenarios").off('click');
        $("#osy-scenarios").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
        });

        $("#osy-openScData").off('click');
        $("#osy-openScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var sc = $("#osy-scenarios").val();
            Html.lblScenario(sc);
            Grid.applyGridFilter($divGrid, model.years, sc);
            Message.smallBoxInfo('Info', 'Scenario data opened!', 2000);
        });

        $("#osy-hideScData").off('click');
        $("#osy-hideScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Html.lblScenario( model.scenariosCount);
            Grid.applyGridFilter($divGrid, model.years);
            Message.smallBoxInfo('Info', 'Scenario data hidden!', 2000);
        });

        $("#osy-removeScData").off('click');
        $("#osy-removeScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var sc = $("#osy-scenarios").val();
            let rows = $divGrid.jqxGrid('getboundrows');

            $.each(rows, function (id, obj) {
                if (obj.Sc == sc) {
                    $.each(model.years, function (i, year) {
                        //$divGrid.jqxGrid('setcellvalue', obj.uid, year, null);
                        model.gridData[model.param][id][year] = null;
                    });
                }
            });

            model.srcGrid.localdata = model.gridData;
            $divGrid.jqxGrid('updatebounddata');

            Html.lblScenario( model.scenariosCount);
            Grid.applyGridFilter($divGrid, model.years);
            Message.smallBoxInfo('Info', 'Scenario data removed!', 2000);
        });

        let pasteEvent = false;
        $divGrid.bind('keydown', function (event) {
            pasteEvent = false;
            var ctrlDown = false, ctrlKey = 17, cmdKey = 91, vKey = 86, cKey = 67;
            var key = event.charCode ? event.charCode : event.keyCode ? event.keyCode : 0;
            if (key == vKey) {
                pasteEvent = true;

                setTimeout(function () {
                    let gridData = $divGrid.jqxGrid('getboundrows');

                    let param = $("#osy-ryt").val();
                    // let tech = $("#osy-techs").val();
                    // let con = $("#osy-cons").val();

                    //update grid model
                    model.gridData[param] = gridData;
                    //update chart model
                    // $.each(model.cons, function (idT, con) {
                    //     $.each(model.techs[con.ConId], function (idT, tech) {
                    //         let chartData = [];
                    //         $.each(model.years, function (idY, year) {
                    //             let chunk = {};
                    //             chunk['Year'] = year;
                    //             $.each(gridData, function (id, obj) {
                    //                 if (obj.TechId == tech.TechId && obj.ConId == con.ConId) {

                    //                     chunk[obj.ScId] = obj[year];
                    //                 }
                    //             });
                    //             chartData.push(chunk);
                    //         });
                    //         model.chartData[param][tech.TechId][con.ConId] = chartData;
                    //     });
                    // });
                    // var configChart = $divChart.jqxChart('getInstance');
                    // configChart.source.records = model.chartData[param][tech][con];
                    // configChart.update();
                }, 500);
            }
        }).on('cellvaluechanged', function (event) {
            if (!pasteEvent) {
                Pace.restart();
                var args = event.args;
                var year = event.args.datafield;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;
                var techId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'TechId');
                var conId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ConId');
                var scId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');

                let param = $("#osy-ryt").val();
                // let tech = $("#osy-techs").val();
                // let con = $("#osy-cons").val();

                //update chart model
                // $.each(model.chartData[param][techId][conId], function (id, obj) {
                //     if (obj.Year == year) {
                //         if (value) {
                //             obj[scId] = value;
                //         } else {
                //             obj[scId] = 0;
                //         }
                //     }
                // });
                // var configChart = $divChart.jqxChart('getInstance');
                // configChart.source.records = model.chartData[param][tech][con];
                // configChart.update();

                //update grid model
                $.each(model.gridData[param], function (id, obj) {
                    if (obj.TechId == techId && obj.ConId == conId && obj.ScId == scId) {
                        if (value) {
                            obj[year] = value;
                        } else {
                            obj[year] = 0;
                        }
                    }
                });
            }
        });

        // $(".switchChart").off('click');
        // $(".switchChart").on('click', function (e) {
        //     e.preventDefault();
        //     var configChart = $divChart.jqxChart('getInstance');
        //     var chartType = $(this).attr('data-chartType');
        //     configChart.seriesGroups[0].type = chartType;
        //     if (chartType == 'column') {
        //         configChart.seriesGroups[0].labels.angle = 90;
        //     } else {
        //         configChart.seriesGroups[0].labels.angle = 0;
        //     }
        //     configChart.update();
        //     // $('button a').switchClass( "green", "grey" );
        //     // $('#'+chartType).switchClass( "grey", "green" );
        // });

        // $(".toggleLabels").off('click');
        // $(".toggleLabels").on('click', function (e) {
        //     e.preventDefault();
        //     var configChart = $divChart.jqxChart('getInstance');
        //     if (configChart.seriesGroups[0].type == 'column') {
        //         configChart.seriesGroups[0].labels.angle = 90;
        //     } else {
        //         configChart.seriesGroups[0].labels.angle = 0;
        //     }
        //     configChart.seriesGroups[0].labels.visible = !configChart.seriesGroups[0].labels.visible;
        //     configChart.update();
        // });

        // $("#exportPng").off('click');
        // $("#exportPng").click(function () {
        //     $divChart.jqxChart('saveAsPNG', 'RYTCn.png', 'https://www.jqwidgets.com/export_server/export.php');
        // });

        let res = true;
        $("#resizeColumns").off('click');
        $("#resizeColumns").click(function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
                $divGrid.jqxGrid('autoresizecolumn', 'Tech');
                $divGrid.jqxGrid('autoresizecolumn', 'Con');
            }
            else {
                $divGrid.jqxGrid('autoresizecolumns');
            }
            res = !res;
        });

        // $("#xlsAll").off('click');
        // $("#xlsAll").click(function (e) {
        //     e.preventDefault();
        //     $divGrid.jqxGrid('exportdata', 'xls', 'RYTCn');
        // });

        
        $("#xlsAll").off('click');
        $("#xlsAll").click(function (e) {
            e.preventDefault();
            let rytData = $divGrid.jqxGrid('getdisplayrows');
            let data = JSON.parse(JSON.stringify(rytData, ['Sc', 'Tech', 'Con'].concat(model.years)));
            Base.prepareCSV(model.casename, data)
            .then(response =>{
                Message.smallBoxInfo('Case study message', response.message, 3000);
                $('#csvDownload').trigger('click');
                window.location = $('#csvDownload').attr('href');
            })
            .catch(error=>{
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        $("#decUp").off('click');
        $("#decUp").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            model.d++;
            model.decimal = 'd' + parseInt(model.d);
            $divGrid.jqxGrid('refresh');
        });

        $("#decDown").off('click');
        $("#decDown").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            model.d--;
            model.decimal = 'd' + parseInt(model.d);
            $divGrid.jqxGrid('refresh');
        });

        $("#showLog").off('click');
        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
            $('#definition').toggle('slow');
        });
    }
}