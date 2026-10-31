import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RYTE.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Chart } from "../../Classes/Chart.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RYTE {
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
                    const RYTEdata = Osemosys.getData(casename, "RYTE.json");
                    promise.push(RYTEdata);
                    return Promise.all(promise);
                } else {
                    let er = {
                        "message": 'There is no model selected!',
                        "status_code": "CaseError"
                    }
                    return Promise.reject(er);
                    //throw new Error(JSON.stringify(er));
                    //MessageSelect.init(RYTE.refreshPage.bind(RYTE));
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTEdata] = data;
                if (RYTEdata['EAR']['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    //throw new Error('Activity');
                    return Promise.reject(er);
                }
                let model = new Model(casename, genData, RYTEdata, group, PARAMETERS, param);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                if (error.status_code == 'CaseError') {
                    MessageSelect.init(RYTE.refreshPage.bind(RYTE));
                }
                else if (error.status_code == 'ActivityError') {
                    MessageSelect.activity(RYTE.refreshPage.bind(RYTE), error.casename);
                }
                Message.warning(error);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        //Navbar.initPage(model.casename);
        Html.title(model.casename, model.PARAMNAMES[model.param], GROUPNAMES[model.group]);
        Html.ddlParams(model.PARAMETERS['RYTE'], model.param);
        Html.ddlTechs(model.techs, model.techs[0]['TechId']);
        Html.ddlEmis(model.emis[model.techs[0]['TechId']], model.emis[model.techs[0]['TechId']][0]['EmisId']);

        let $divGrid = $('#osy-gridRYTE');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, true);
        if (model.scenariosCount > 1) {
            $('#scCommand').show();
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            Html.ddlTechNames(model.techs, model.techs[0]['TechId']);
            Html.ddlEmiNames(model.emis[model.techs[0]['TechId']], model.emis[model.techs[0]['TechId']][0]['EmisId']);
            Grid.applyRYTEFilter($divGrid, model.years);
        }

        let $divChart = $('#osy-chartRYTE');
        var daChart = new $.jqx.dataAdapter(model.srcChart, { autoBind: true });
        Chart.Chart($divChart, daChart, "RYTE", model.series);
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
                const RYTEdata = Osemosys.getData(casename, 'RYTE.json');
                promise.push(RYTEdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTEdata] = data;
                if (RYTEdata['EAR']['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    //throw new Error('Activity');
                    return Promise.reject(er);
                }
                let model = new Model(casename, genData, RYTEdata, 'RYTE', PARAMETERS, PARAMETERS['RYTE'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                setTimeout(function () {
                    if (error.status_code == 'CaseError') {
                        MessageSelect.init(RYTE.refreshPage.bind(RYTE));
                    }
                    else if (error.status_code == 'ActivityError') {
                        MessageSelect.activity(RYTE.refreshPage.bind(RYTE), error.casename);
                    }
                    Message.warning(error.message);
                }, 500);

            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRYTE');
        let $divChart = $('#osy-chartRYTE');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RYTE.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYTEdata").off('click');
        $("#osy-saveRYTEdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            let param = $("#osy-ryt").val();
            let rytData = $divGrid.jqxGrid('getboundrows');
            // Persist stable row IDs and values only; grid labels and units are
            // display metadata. Scenario nulls must survive to preserve inheritance.
            let data = JSON.parse(JSON.stringify(rytData, ['ScId', 'TechId', 'EmisId'].concat(model.years)));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RYTE.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RYTE.json");
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
            $divGrid.jqxGrid('updatebounddata');
            model.param = this.value;
            var configChart = $divChart.jqxChart('getInstance');
            var tech = $("#osy-techs").val();
            var emi = $("#osy-emis").val();
            configChart.source.records = model.chartData[this.value][tech][emi];
            configChart.update();
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
        });

        $("#osy-techs").off('change');
        $('#osy-techs').on('change', function () {
            var param = $("#osy-ryt").val();
            Html.ddlEmis(model.emis[this.value], model.emis[this.value][0]['EmisId']);
            var emi = $("#osy-emis").val();
            var configChart = $divChart.jqxChart('getInstance');
            configChart.source.records = model.chartData[param][this.value][emi];
            configChart.update();
        });

        $("#osy-techNames").off('change');
        $('#osy-techNames').on('change', function () {
            let tech = model.techIds[this.value];
            Html.ddlEmiNames(model.emis[tech], model.emis[tech][0]['EmisId']);
        });

        $("#osy-emis").off('change');
        $('#osy-emis').on('change', function () {
            var param = $("#osy-ryt").val();
            var tech = $("#osy-techs").val();
            var configChart = $divChart.jqxChart('getInstance');
            configChart.source.records = model.chartData[param][tech][this.value];
            configChart.update();
        });

        $("#osy-openScData").off('click');
        $("#osy-openScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var sc = $("#osy-scenarios").val();
            var emi = $("#osy-emiNames").val();
            var tech = $("#osy-techNames").val();
            Grid.applyRYTEFilter($divGrid, model.years, sc, tech, emi);
        });

        $("#osy-removeScData").off('click');
        $("#osy-removeScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var sc = $("#osy-scenarios").val();
            var emi = $("#osy-emiNames").val();
            var tech = $("#osy-techNames").val();
            var rows = $divGrid.jqxGrid('getdisplayrows');
            $.each(rows, function (id, obj) {
                if (obj.Sc == sc && obj.Emi == emi && obj.Tech == tech) {
                    $.each(model.years, function (i, year) {
                        $divGrid.jqxGrid('setcellvalue', obj.uid, year, null);
                    });
                    return false; // breaks
                }
            });
            Grid.applyRYTEFilter($divGrid, model.years);
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
                    let tech = $("#osy-techs").val();
                    let emi = $("#osy-emis").val();

                    //update grid model
                    model.gridData[param] = gridData;

                    //update chart model
                    $.each(model.techs, function (idT, tech) {
                        $.each(model.emis[tech.TechId], function (idT, emi) {
                            let chartData = [];
                            $.each(model.years, function (idY, year) {
                                let chunk = {};
                                chunk['Year'] = year;
                                $.each(gridData, function (id, obj) {
                                    if (obj.TechId == tech.TechId && obj.EmisId == emi.EmisId) {
                                        chunk[obj.ScId] = obj[year];
                                    }
                                });
                                chartData.push(chunk);
                            });
                            model.chartData[param][tech.TechId][emi.EmisId] = chartData;
                        });
                    });

                    var configChart = $divChart.jqxChart('getInstance');
                    configChart.source.records = model.chartData[param][tech][emi];
                    configChart.update();
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
                var emisId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'EmisId');
                var scId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');

                let param = $("#osy-ryt").val();
                let tech = $("#osy-techs").val();
                let emi = $("#osy-emis").val();

                //update chart model
                $.each(model.chartData[param][techId][emisId], function (id, obj) {
                    if (obj.Year == year) {
                        if (value) {
                            obj[scId] = value;
                        } else {
                            obj[scId] = 0;
                        }
                    }
                });
                var configChart = $divChart.jqxChart('getInstance');
                configChart.source.records = model.chartData[param][tech][emi];
                configChart.update();

                //update grid model
                $.each(model.gridData[param], function (id, obj) {
                    if (obj.TechId == techId && obj.EmisId == emisId && obj.ScId == scId) {
                        if (value) {
                            obj[year] = value;
                        } else {
                            obj[year] = 0;
                        }
                    }
                });
            }
        });

        $(".switchChart").off('click');
        $(".switchChart").on('click', function (e) {
            e.preventDefault();
            var configChart = $divChart.jqxChart('getInstance');
            var chartType = $(this).attr('data-chartType');
            configChart.seriesGroups[0].type = chartType;
            if (chartType == 'column') {
                configChart.seriesGroups[0].labels.angle = 90;
            } else {
                configChart.seriesGroups[0].labels.angle = 0;
            }
            configChart.update();
            // $('button a').switchClass( "green", "grey" );
            // $('#'+chartType).switchClass( "grey", "green" );
        });

        $(".toggleLabels").off('click');
        $(".toggleLabels").on('click', function (e) {
            e.preventDefault();
            var configChart = $divChart.jqxChart('getInstance');
            if (configChart.seriesGroups[0].type == 'column') {
                configChart.seriesGroups[0].labels.angle = 90;
            } else {
                configChart.seriesGroups[0].labels.angle = 0;
            }
            configChart.seriesGroups[0].labels.visible = !configChart.seriesGroups[0].labels.visible;
            configChart.update();
        });

        $("#exportPng").off('click');
        $("#exportPng").click(function () {
            $divChart.jqxChart('saveAsPNG', 'RYTE.png', 'https://www.jqwidgets.com/export_server/export.php');
        });

        let res = true;
        $("#resizeColumns").off('click');
        $("#resizeColumns").click(function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
                $divGrid.jqxGrid('autoresizecolumn', 'Tech');
                $divGrid.jqxGrid('autoresizecolumn', 'Emis');
            }
            else {
                $divGrid.jqxGrid('autoresizecolumns');
            }
            res = !res;
        });

        $("#xlsAll").off('click');
        $("#xlsAll").click(function (e) {
            e.preventDefault();
            $divGrid.jqxGrid('exportdata', 'xls', 'RYTE');
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