import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RYT.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RYT {
    static onLoad(group, param) {
        Message.loaderStart('Loading data...');
        Base.getSession()
            .then(response => {
                let start = performance.now();
                let casename = response['session'];
                if (casename) {
                    const promise = [];
                    promise.push(casename);
                    const genData = Osemosys.getData(casename, 'genData.json');
                    promise.push(genData);
                    const PARAMETERS = Osemosys.getParamFile();
                    promise.push(PARAMETERS);
                    const RYTdata = Osemosys.getData(casename, 'RYT.json');
                    promise.push(RYTdata);
                    promise.push(start);
                    //console.log('performance get data from API ', performance.now() - start);

                    return Promise.all(promise);
                } else {
                    Message.loaderEnd();
                    MessageSelect.init(RYT.refreshPage.bind(RYT));
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTdata, start] = data;
                //console.log('performance read data from promise ', performance.now() - start);
                let model = new Model(casename, genData, RYTdata, group, PARAMETERS, param);
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
        Html.ddlParams(model.PARAMETERS[model.group], model.param);
        
        
        let $divGrid = $('#osy-gridRYT');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, {filterable: true, sortable:true});

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
                const RYTdata = Osemosys.getData(casename, 'RYT.json');
                promise.push(RYTdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTdata] = data;
                let model = new Model(casename, genData, RYTdata, 'RYT', PARAMETERS, PARAMETERS['RYT'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.loaderEnd();
                Message.warning(error);
            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRYT');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RYT.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYTdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let param = $("#osy-ryt").val();
            let rytData = $divGrid.jqxGrid('getboundrows');

            let data = JSON.parse(JSON.stringify(rytData, ['ScId', 'TechId'].concat(model.years)));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RYT.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RYT.json");
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
        });

        //change of ddl parameters
        $('#osy-ryt').on('change', function () {
            $divGrid.jqxGrid('showloadelement');
            Html.title(model.casename, model.PARAMNAMES[this.value], GROUPNAMES[model.group]);
            model.param = this.value;
            model.srcGrid.root = this.value;
            //deciml values by params
            // let decimal = Functions.getDecimalPlaces(model.paramData[model.group][this.value]['default']);
            // model.param = this.value;
            // model.d = decimal;
            // model.decimal = 'd' + model.d;
            $divGrid.jqxGrid('updatebounddata');
            Grid.applyGridFilter($divGrid, model.years);
            Html.lblScenario( model.scenariosCount);
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
                Pace.restart();
                var args = event.args;
                var year = event.args.datafield;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;
                var techId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'TechId');
                var scId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                let param = $("#osy-ryt").val();                
                $.each(model.gridData[param], function (id, obj) {
                    if (obj.TechId == techId && obj.ScId == scId) {
                        if (value) {
                            obj[year] = value;
                        } else {
                            obj[year] = 0;
                        }
                    }
                });
            }
        });

        $("#resizeColumns").off('click');
        let res = true;
        $("#resizeColumns").click(function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Tech');
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
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
            let data = JSON.parse(JSON.stringify(rytData, ['Sc', 'Tech'].concat(model.years)));

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
        $("#showLog").on('click',function (e) {
            e.preventDefault();
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
            $('#definition').toggle('slow');
        });
        Message.loaderEnd();
    }
}