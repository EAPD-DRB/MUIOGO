import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RYTTs.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RYTTs {
    static onLoad(group, param) {
        Message.loaderStart('Loading data...');
        Base.getSession()
            .then(response => {
                let casename = response['session'];
                if (casename) {
                    let start = performance.now();
                    const promise = [];
                    promise.push(casename);
                    const genData = Osemosys.getData(casename, 'genData.json');
                    promise.push(genData);
                    const PARAMETERS = Osemosys.getParamFile();
                    promise.push(PARAMETERS);
                    const RYTTsdata = Osemosys.getData(casename, "RYTTs.json");
                    promise.push(RYTTsdata);
                    promise.push(start);
                    //console.log('performance get data from API ', performance.now() - start);
                    return Promise.all(promise);
                } else {
                    Message.loaderEnd();
                    MessageSelect.init(RYTTs.refreshPage.bind(RYTTs));
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTTsdata, start] = data;
                //console.log('performance read data from promise ', performance.now() - start);
                let model = new Model(casename, genData, RYTTsdata, group, PARAMETERS, param);
                //console.log('performance model ', performance.now() - start);
                this.initPage(model);
                //console.log('performance idit page ', performance.now() - start);
                this.initEvents(model);
                //console.log('performance events ', performance.now() - start);
            })
            .catch(error => {
                Message.loaderEnd();
                Message.warning(error);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        //Navbar.initPage(model.casename);
        Html.title(model.casename, model.PARAMNAMES[model.param], GROUPNAMES[model.group]);
        Html.ddlParams(model.PARAMETERS['RYTTs'], model.param);

        let $divGrid = $('#osy-gridRYTTs');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, {groupable: false, filterable: true, sortable:true});

        if (model.scenariosCount > 1) {
            Html.lblScenario( model.scenariosCount);
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            Grid.applyGridFilter($divGrid, model.years);
        }
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
                const RYTTsdata = Osemosys.getData(casename, 'RYTTs.json');
                promise.push(RYTTsdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTTsdata] = data;
                let model = new Model(casename, genData, RYTTsdata, 'RYTTs', PARAMETERS, PARAMETERS['RYTTs'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.loaderEnd();
                Message.warning(error);
            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRYTTs');

        $("#casePicker").off('click');
        //odabir novog Model iz Model pickera
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RYTTs.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYTTsdata").off('click');
        $("#osy-saveRYTTsdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            let start = performance.now();

            let param = $("#osy-ryt").val();
            let rytData = $divGrid.jqxGrid('getboundrows');
            let data = JSON.parse(JSON.stringify(rytData, ['ScId', 'TechId', 'TsId'].concat(model.years)));
            let saveData = {};

            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                //delete obj.ScId;
            });

            // console.log('data preparation for save ', performance.now() - start);

            Osemosys.updateData(saveData, param, "RYTTs.json")
                .then(response => {
                    //console.log('response from api ', performance.now() - start);
                    //model.gridData[model.param] = JSON.parse(RYTmodel);
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RYTTs.json");
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
        });

        //change of ddl parameters
        $("#osy-ryt").off('change');
        $('#osy-ryt').on('change', function () {
            let $divGrid = $divGrid;
            model.srcGrid.root = this.value;
            model.param = this.value;
            $divGrid.jqxGrid('updatebounddata');


            // var configChart = $divChart.jqxChart('getInstance');
            // var tech = $("#osy-techs").val();
            // var ts = $("#osy-timeslices1").val();
            // configChart.source.records = model.chartData[this.value][tech][ts];
            // configChart.update();
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
                    model.gridData[param] = gridData;
                }, 500);
                
            }
        }).on('cellvaluechanged', function (event) {
            if (!pasteEvent) {
                //Pace.restart();
                pasteEvent = false;
                var args = event.args;
                var year = event.args.datafield;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;

                var techId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'TechId');
                var tsId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'TsId');
                var ScId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                $.each(model.gridData[model.param], function (id, obj) {
                    if (obj.TechId == techId && obj.TsId == tsId && obj.ScId == ScId) {
                        if (value) {
                            obj[year] = value;
                        } else {
                            obj[year] = 0;
                        }
                    }
                });
            }
        });

        let res = true;
        $("#resizeColumns").off('click');
        $("#resizeColumns").click(function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
                $divGrid.jqxGrid('autoresizecolumn', 'Tech');
                $divGrid.jqxGrid('autoresizecolumn', 'Ts');
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
            let data = JSON.parse(JSON.stringify(rytData, ['Sc', 'Tech', 'Ts'].concat(model.years)));

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

        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
            $('#definition').toggle('slow');
        });

        Message.loaderEnd();
    }
}