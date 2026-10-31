import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RY.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Chart } from "../../Classes/Chart.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";
// import { Sidebar } from "./Sidebar.js";

export default class RY {
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
                    const RYdata = Osemosys.getData(casename, 'RY.json');
                    promise.push(RYdata);
                    return Promise.all(promise);
                    ;
                } else {
                    MessageSelect.init(RY.refreshPage.bind(RY));
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYdata] = data;
                let model = new Model(casename, genData, RYdata, group, PARAMETERS, param);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.warning(error);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        // Sidebar.Load(model.PARAMETERS);
        //Navbar.initPage(model.casename);
        Html.title(model.casename, model.PARAMNAMES[model.param], GROUPNAMES[model.group]);
        Html.ddlParams(model.PARAMETERS[model.group], model.param);

        let $divGrid = $('#osy-gridRY');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, {pageable: false});

        if (model.scenariosCount > 1) {
            Html.lblScenario( model.scenariosCount);
            
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            Grid.applyGridFilter($divGrid, model.years);
        }

        var daChart = new $.jqx.dataAdapter(model.srcChart, { autoBind: true });
        let $divChart = $('#osy-chartRY');
        Chart.Chart($divChart, daChart, "RY", model.series);
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
                const RYdata = Osemosys.getData(casename, 'RY.json');
                promise.push(RYdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYdata] = data;
                let model = new Model(casename, genData, RYdata, 'RY', PARAMETERS, PARAMETERS['RY'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.warning(error);
            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRY');
        let $divChart = $('#osy-chartRY');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RY.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYTdata").off('click');
        $("#osy-saveRYTdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let param = $("#osy-ryt").val();
            let ryData = $divGrid.jqxGrid('getboundrows');

            // Persist stable row IDs and values only; grid labels and units are
            // display metadata. Scenario nulls must survive to preserve inheritance.
            let daRYData = JSON.parse(JSON.stringify(ryData, ['ScId'].concat(model.years)))

            let saveData = {};
            $.each(daRYData, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RY.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RY.json");
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
        });

        //change of ddl parameters
        $("#osy-ryt").off('click');
        $('#osy-ryt').on('change', function () {
            Html.title(model.casename, model.PARAMNAMES[this.value], GROUPNAMES[model.group]);
            model.srcGrid.root = this.value;
            model.param = this.value;
            $divGrid.jqxGrid('updatebounddata');
            var configChart = $divChart.jqxChart('getInstance');
            configChart.source.records = model.chartData[this.value];
            configChart.update();
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
        });

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
            Html.lblScenario( model.scenariosCount);
            Grid.applyGridFilter($divGrid, model.years, sc);
            Message.smallBoxInfo('Info', 'Scenario data hidden!', 2000);
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
                if (obj.Sc == sc && obj.Param == model.PARAMNAMES[model.param]) {
                    $.each(model.years, function (i, year) {
                        //$divGrid.jqxGrid('setcellvalue', obj.uid, year, null);
                        model.gridData[model.param][id][year] = null;
                    });
                }
            });

            model.srcGrid.localdata = model.gridData;
            $divGrid.jqxGrid('updatebounddata');


            let chartData = [];
            $.each(model.years, function (idY, year) {
                let chunk = {};
                chunk['Year'] = year;
                $.each(model.gridData[model.param], function (id, rytDataObj) {
                    chunk[rytDataObj.ScId] = rytDataObj[year];
                });
                chartData.push(chunk);
            });

            //update model
            model.chartData[model.param] = chartData;
            var configChart = $divChart.jqxChart('getInstance');
            configChart.source.records = model.chartData[model.param];
            configChart.update();

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
                    let chartData = [];
                    $.each(model.years, function (idY, year) {
                        let chunk = {};
                        chunk['Year'] = year;
                        $.each(gridData, function (id, rytDataObj) {
                            chunk[rytDataObj.ScId] = rytDataObj[year];
                        });
                        chartData.push(chunk);
                    });

                    //update model
                    model.chartData[param] = chartData;
                    model.gridData[param] = gridData;

                    var configChart = $divChart.jqxChart('getInstance');
                    configChart.source.records = model.chartData[param];
                    configChart.update();
                }, 1000);
            }
        }).on('cellvaluechanged', function (event) {
            if (!pasteEvent) {
                Pace.restart();
                var args = event.args;
                var year = event.args.datafield;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;
                var paramId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'param');
                var scId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                let param = $("#osy-ryt").val();
                //update model chart
                $.each(model.chartData[param], function (id, obj) {
                    if (obj.Year == year) {
                        if (value) {
                            obj[scId] = value;
                        } else {
                            obj[scId] = 0;
                        }
                    }
                });
                //update model grid
                $.each(model.gridData[param], function (id, obj) {
                    if (obj.ParamId == param && obj.ScId == scId) {
                        if (value) {
                            obj[year] = value;
                        } else {
                            obj[year] = 0;
                        }
                    }
                });
                var configChart = $divChart.jqxChart('getInstance');
                configChart.source.records = model.chartData[param];
                configChart.update();
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
            $divChart.jqxChart('saveAsPNG', 'RY.png', 'https://www.jqwidgets.com/export_server/export.php');
        });

        let res = true;
        $("#resizeColumns").off('click');
        $("#resizeColumns").click(function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
                $divGrid.jqxGrid('autoresizecolumn', 'Param');
                $divGrid.jqxGrid('autoresizecolumn', 'UnitId');
            }
            else {
                $divGrid.jqxGrid('autoresizecolumns');
            }
            res = !res;
        });

        $("#xlsAll").off('click');
        $("#xlsAll").click(function (e) {
            e.preventDefault();
            $divGrid.jqxGrid('exportdata', 'xls', 'RY');
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

        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`
                ${DEF[model.group][model.param].definition}
            `);
            $('#definition').toggle('slow');
        });
    }
}