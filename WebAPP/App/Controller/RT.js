import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RT.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Chart } from "../../Classes/Chart.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RT {
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
                    const RTdata = Osemosys.getData(casename, 'RT.json');
                    promise.push(RTdata);
                    return Promise.all(promise);
                } else {
                    MessageSelect.init(RT.refreshPage.bind(RT));
                    Message.loaderEnd();
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RTdata] = data;
                let model = new Model(casename, genData, RTdata, group, PARAMETERS, param);
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

        if(model.param == 'OL'){
            $('#decBtns').hide();
        }

        let $divGrid = $('#osy-gridRT');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, {pageable: false, autoheight: true})

        if (model.scenariosCount > 1) {
            Html.lblScenario( model.scenariosCount);
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            Grid.applyRTFilter($divGrid, model.techs);
        }

        var daChart = new $.jqx.dataAdapter(model.srcChart, { autoBind: true });
        let $divChart = $('#osy-chartRT');
        if (['TMPAL', 'TMPAU'].includes(this.param)){
            Chart.Chart($divChart, daChart, "RT", model.series, 'Tech', 'Year', 'auto');
        }else{
            Chart.Chart($divChart, daChart, "RT", model.series, 'Tech');
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
                const RTdata = Osemosys.getData(casename, 'RT.json');
                promise.push(RTdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RTdata] = data;
                let model = new Model(casename, genData, RTdata, 'RT', PARAMETERS, PARAMETERS['RT'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.warning(error);
                Message.loaderEnd();
            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRT');
        let $divChart = $('#osy-chartRT');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RT.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYTdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let param = $("#osy-ryt").val();
            let rtData = $divGrid.jqxGrid('getboundrows');
            // Persist stable row IDs and values only; grid labels and units are
            // display metadata. Scenario nulls must survive to preserve inheritance.
            let data = JSON.parse(JSON.stringify(rtData, ['ScId'].concat(model.techIds)));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RT.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RT.json");
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

            if(this.value == 'OL'){
                model.d=0;
                model.decimal = 'n0';
                $('#decBtns').hide();
            }else{
                model.d=2;
                model.decimal = 'd' + model.d;
                $('#decBtns').show();
            }

            $divGrid.jqxGrid('updatebounddata');

            $.each(model.techs, function (idT, tech) {
                $divGrid.jqxGrid('setcolumnproperty', tech.TechId, 'text', tech.Tech + ' <small style="color:darkgrey">[ ' + model.techUnit[newParam][tech.TechId] + ' ]</small>');
            });
            model.param = this.value;
            Grid.applyRTFilter($divGrid, model.techs);
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
            Grid.applyRTFilter($divGrid, model.techs, sc, model.PARAMNAMES[param]);
            Message.smallBoxInfo('Info', 'Scenario data opened!', 2000);
        });

        $("#osy-hideScData").off('click');
        $("#osy-hideScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Html.lblScenario( model.scenariosCount);
            Grid.applyRTFilter($divGrid, model.techs);
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
                    $.each(model.techs, function (i, tech) {
                        model.gridData[model.param][id][tech.TechId] = null;
                    });
                }
            });
            model.srcGrid.localdata = model.gridData;
            $divGrid.jqxGrid('updatebounddata');

            let chartData = [];
            $.each(model.techs, function (id, tech) {
                let chunk = {};
                chunk['TechId'] = tech.TechId;
                chunk['Tech'] = tech.Tech;
                $.each(model.gridData[model.param], function (id, rtDataObj) {
                    chunk[rtDataObj.ScId] = rtDataObj[tech.TechId];
                });
                chartData.push(chunk);
                model.chartData[model.param] = chartData;
            });

            var configChart = $divChart.jqxChart('getInstance');
            configChart.source.records = model.chartData[model.param];
            configChart.update();

            Html.lblScenario( model.scenariosCount);
            Grid.applyRTFilter($divGrid, model.techs);
            Message.smallBoxInfo('Info', 'Scenario data removed!', 2000);
        });

        Number.prototype.countDecimals = function () {
            if(Math.floor(this.valueOf()) === this.valueOf()) return 0;
            return this.toString().split(".")[1].length || 0; 
        }

        let pasteEvent = false;
        let integerFlag = true;
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
                    $.each(model.techs, function (id, tech) {
                        let chunk = {};
                        chunk['TechId'] = tech.TechId;
                        chunk['Tech'] = tech.Tech;
                        $.each(gridData, function (id, rtDataObj) {
                            //provjeriti da li je integer  
                            if(!Number.isInteger(rtDataObj[tech.TechId]) && rtDataObj[tech.TechId] != null && model.param =='OL'){
                                integerFlag = false;
                                rtDataObj[tech.TechId] = Math.ceil(rtDataObj[tech.TechId]);
                                chunk[rtDataObj.ScId] = rtDataObj[tech.TechId];
                            }
                            else{
                                chunk[rtDataObj.ScId] = rtDataObj[tech.TechId];
                            }

                        });
                        chartData.push(chunk);
                        model.chartData[param] = chartData;
                    });
                    model.gridData[param] = gridData;
                    $divGrid.jqxGrid('updatebounddata');
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
                var args = event.args;
                var tech = event.args.datafield;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;
                var techId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'TechId');
                var scId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                let param = $("#osy-ryt").val();

                $.each(model.chartData[param], function (id, obj) {
                    if (obj.TechId == tech) {
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
                            obj[tech] = value;
                        } else {
                            obj[tech] = 0;
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
            $divChart.jqxChart('saveAsPNG', 'RT.png', 'https://www.jqwidgets.com/export_server/export.php');
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

        $("#xlsAll").off('click');
        $("#xlsAll").click(function (e) {
            e.preventDefault();
            let rytData = $divGrid.jqxGrid('getdisplayrows');
            let data = JSON.parse(JSON.stringify(rytData, ['Sc', 'Param'].concat(model.techIds)));

            let dataNames = [];
            let tmp={};
            $.each(data[0], function (id, val) { 
                if (id != "Sc" && id != "Param") {
                    let techName = model.techNames[id];
                    tmp[techName] = val;
                }else{
                    tmp[id] = val;
                }
            });
            dataNames.push(tmp)

            Base.prepareCSV(model.casename, dataNames)
            .then(response =>{
                Message.smallBoxInfo('Model message', response.message, 3000);
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
            if (model.d == 5){
                Message.smallBoxWarning('WARNING', 'You have reached max number of decimal places (5).', 4000)
            }
            else{
                model.d++;
                model.decimal = 'd' + parseInt(model.d);
                $divGrid.jqxGrid('updatebounddata');
            }
        });

        $("#decDown").off('click');
        $("#decDown").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (model.d == 0){
                Message.smallBoxWarning('WARNING', 'Number of decimal places cannot be lower then 0.', 4000)
            }
            else{
                model.d--;
                model.decimal = 'd' + parseInt(model.d);
                $divGrid.jqxGrid('updatebounddata');
            }
        });

        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
            $('#definition').toggle('slow');
        });

        Message.loaderEnd();
    }
}