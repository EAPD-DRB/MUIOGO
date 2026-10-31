import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RS.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Chart } from "../../Classes/Chart.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";
// import { Sidebar } from "./Sidebar.js";

export default class RS {
    static onLoad(group, param) {
        Message.loaderStart('Loading data...');
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
                    const RTdata = Osemosys.getData(casename, 'RS.json');
                    promise.push(RTdata);
                    return Promise.all(promise);
                } else {
                    MessageSelect.init(RS.refreshPage.bind(RS));
                    Message.loaderEnd();
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RSdata] = data;
                let model = new Model(casename, genData, RSdata, group, PARAMETERS, param);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.warning(error);
                Message.loaderEnd();
            });
    }

    static initPage(model) {
        Message.clearMessages();
        Html.title(model.casename, model.PARAMNAMES[model.param], GROUPNAMES[model.group]);
        Html.ddlParams(model.PARAMETERS[model.group], model.param);

        let $divGrid = $('#osy-gridRS');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, {pageable: false, autoheight:true})

        if (model.scenariosCount > 1) {
            Html.lblScenario( model.scenariosCount);
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            Grid.applyRSFilter($divGrid, model.stgs);
        }

        var daChart = new $.jqx.dataAdapter(model.srcChart, { autoBind: true });
        let $divChart = $('#osy-chartRS');
        if (['TMPAL', 'TMPAU'].includes(this.param)){
            Chart.Chart($divChart, daChart, "RS", model.series, 'Stg', 'Year', 'auto');
        }else{
            Chart.Chart($divChart, daChart, "RS", model.series, 'Stg');
        }
        
        //pageSetUp();
    }

    static refreshPage(casename) {
        Message.loaderStart('Loading data...');
        Base.setSession(casename)
            .then(response => {
                const promise = [];
                promise.push(casename);
                const genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const PARAMETERS = Osemosys.getParamFile();
                promise.push(PARAMETERS);
                const RTdata = Osemosys.getData(casename, 'RS.json');
                promise.push(RTdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RSdata] = data;
                let model = new Model(casename, genData, RSdata, 'RS', PARAMETERS, PARAMETERS['RS'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.warning(error);
                Message.loaderEnd();
            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRS');
        let $divChart = $('#osy-chartRS');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RS.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRSdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let param = $("#osy-ryt").val();
            let rsData = $divGrid.jqxGrid('getboundrows');
            // Persist stable row IDs and values only; grid labels and units are
            // display metadata. Scenario nulls must survive to preserve inheritance.
            let data = JSON.parse(JSON.stringify(rsData, ['ScId'].concat(model.stgIds)));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RS.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RS.json");
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
        });

        //change of ddl parameters
        $('#osy-ryt').on('change', function () {
            Html.title(model.casename, model.PARAMNAMES[this.value], GROUPNAMES[model.group]);
            model.srcGrid.root = this.value;
            let newParam = this.value;
            $divGrid.jqxGrid('updatebounddata');
            $.each(model.stgs, function (idT, stg) {
                $divGrid.jqxGrid('setcolumnproperty', stg.StgId, 'text', stg.Stg + ' <small style="color:darkgrey">[ ' + model.stgUnit[newParam][stg.StgId] + ' ]</small>');
            });
            model.param = this.value;
            Grid.applyRSFilter($divGrid, model.stgs);
            var configChart = $divChart.jqxChart('getInstance');
            configChart.source.records = model.chartData[this.value];

            if (['TMPAL', 'TMPAU'].includes(this.value)){
                configChart.valueAxis.minValue = 'auto';
            }else{
                configChart.valueAxis.minValue = 0;
            }

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
            var param = $("#osy-ryt").val();
            Html.lblScenario(sc);
            // let group = $divGrid.jqxGrid('getgroup', 0);
            Grid.applyRSFilter($divGrid, model.stgs, sc, model.PARAMNAMES[param]);
            Message.smallBoxInfo('Info', 'Scenario data opened!', 2000);
        });

        
        $("#osy-hideScData").off('click');
        $("#osy-hideScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Html.lblScenario( model.scenariosCount);
            Grid.applyRSFilter($divGrid, model.stgs);
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
                    $.each(model.stgs, function (i, stg) {
                        //$divGrid.jqxGrid('setcellvalue', obj.uid, tech.TechId, null);
                        model.gridData[model.param][id][stg.StgId] = null;
                    });
                }
            });
            model.srcGrid.localdata = model.gridData;
            $divGrid.jqxGrid('updatebounddata');


            let chartData = [];
            $.each(model.stgs, function (id, stg) {
                let chunk = {};
                chunk['StgId'] = stg.StgId;
                chunk['Stg'] =stg.Stg;
                $.each(model.gridData[model.param], function (id, rtDataObj) {
                    chunk[rtDataObj.ScId] = rtDataObj[stg.StgId];
                });
                chartData.push(chunk);
                model.chartData[model.param] = chartData;
            });


            var configChart = $divChart.jqxChart('getInstance');
            configChart.source.records = model.chartData[model.param];
            configChart.update();

            Html.lblScenario( model.scenariosCount);
            Grid.applyRSFilter($divGrid, model.stgs);
            Message.smallBoxInfo('Info', 'Scenario data removed!', 2000);
        });

        let pasteEvent = false;
        $divGrid.bind('keydown', function (event) {
            pasteEvent = false;
            let integerFlag =  true;
            var ctrlDown = false, ctrlKey = 17, cmdKey = 91, vKey = 86, cKey = 67;
            var key = event.charCode ? event.charCode : event.keyCode ? event.keyCode : 0;
            if (key == vKey) {
                pasteEvent = true;
                setTimeout(function () {
                    let gridData = $divGrid.jqxGrid('getboundrows');
                    let param = $("#osy-ryt").val();
                    let chartData = [];
                    $.each(model.stgs, function (id, stg) {
                        let chunk = {};
                        chunk['StgId'] = stg.StgId;
                        chunk['Stg'] = stg.Stg;
                        $.each(gridData, function (id, rtDataObj) {
                            //chunk[rtDataObj.ScId] = rtDataObj[stg.StgId];

                            //provjeriti da li je integer  
                            if(!Number.isInteger(rtDataObj[stg.StgId]) && rtDataObj[stg.StgId] != null ){
                                integerFlag = false;
                                rtDataObj[stg.StgId] = Math.ceil(rtDataObj[stg.StgId]);
                                chunk[rtDataObj.ScId] = rtDataObj[stg.StgId];
                            }
                            else{
                                chunk[rtDataObj.ScId] = rtDataObj[stg.StgId];
                            }
                        });
                        chartData.push(chunk);
                        model.chartData[param] = chartData;
                    });
                    model.gridData[param] = gridData;

                    var configChart = $divChart.jqxChart('getInstance');
                    configChart.source.records = model.chartData[param];
                    configChart.update();
                    if(!integerFlag){
                        Message.bigBoxWarning('WARNING', "Some of the values were not integer, they are rounded to higher number.", 3000)
                    }
                }, 1000);
            }
        }).on('cellvaluechanged', function (event) {
            if (!pasteEvent) {
                //Pace.restart();
                var args = event.args;
                var stg = event.args.datafield;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;
                var stgId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'StgId');
                var scId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                let param = $("#osy-ryt").val();

                $.each(model.chartData[param], function (id, obj) {
                    if (obj.StgId == stg) {
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
                            obj[stg] = value;
                        } else {
                            obj[stg] = 0;
                        }
                    }
                });

                var configChart = $divChart.jqxChart('getInstance');
                configChart.source.records = model.chartData[param];
                configChart.update();
            }
        });

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

        $("#exportPng").click(function () {
            $divChart.jqxChart('saveAsPNG', 'RS.png', 'https://www.jqwidgets.com/export_server/export.php');
        });

        $("#osy-getColumns").off('click');
        $("#getColumns").on('click', function () {
            $divGrid.jqxGrid('openColumnChooser');
        });

        let res = true;
        $("#resizeColumns").click(function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
                $divGrid.jqxGrid('autoresizecolumn', 'Param');
            }
            else {
                $divGrid.jqxGrid('autoresizecolumns');
            }
            res = !res;
        });

        $("#xlsAll").click(function (e) {
            e.preventDefault();
            $divGrid.jqxGrid('exportdata', 'xls', 'RS');
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
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
            $('#definition').toggle('slow');
        });

        Message.loaderEnd();
    }
}