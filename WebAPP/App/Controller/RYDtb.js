import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RYDtb.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RYDtb {
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
                    const RYTsdata = Osemosys.getData(casename, 'RYDtb.json');
                    promise.push(RYTsdata);
                    return Promise.all(promise);
                } else {
                    MessageSelect.init(RYDtb.refreshPage.bind(RYDtb));
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTsdata] = data;
                let model = new Model(casename, genData, RYTsdata, group, PARAMETERS, param);
                this.initPage(model);
                this.initEvents(model);
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
        //Html.ddlTimeslices($('#osy-timeslices1'), model.timeslices);

        let $divGrid = $('#osy-gridRYDtb');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, { sortable:true});

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
                const RYTsdata = Osemosys.getData(casename, 'RYDtb.json');
                promise.push(RYTsdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTsdata] = data;
                let model = new Model(casename, genData, RYTsdata, 'RYDtb', PARAMETERS, PARAMETERS['RYDtb'][0]['id']);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.loaderEnd();
                Message.warning(error);
            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRYDtb');
        //let $divChart = $('#osy-chartRYTs');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RYDtb.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYDtbdata").off('click');
        $("#osy-saveRYDtbdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            let rytsData = $divGrid.jqxGrid('getboundrows');
            let param = $("#osy-ryt").val();
            let data = JSON.parse(JSON.stringify(rytsData, ['ScId', 'DtbId'].concat(model.years)));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RYDtb.json")
                .then(response => {
                    //model.gridData[model.param] = JSON.parse(daRYTsData);
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RYDtb.json");
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
            $divGrid.jqxGrid('updatebounddata');
            model.param = this.value;
            Grid.applyGridFilter($divGrid, model.years);
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
                if (obj.Sc == sc ) {
                    $.each(model.years, function (i, year) {
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
                    //update model
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
                var DtbId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'DtbId');
                var scId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                let param = $("#osy-ryt").val();

                //update model grid
                $.each(model.gridData[param], function (id, obj) {
                    if (obj.DtbId == DtbId && obj.ScId == scId) {
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
                $divGrid.jqxGrid('autoresizecolumn', 'Dtb');
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
            let data = JSON.parse(JSON.stringify(rytData, ['Sc', 'Dtb'].concat(model.years)));
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