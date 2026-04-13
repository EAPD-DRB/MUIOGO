import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RTSM.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RTSM {
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
                    const RTSMdata = Osemosys.getData(casename, "RTSM.json");
                    promise.push(RTSMdata);
                    const cases = Base.getCaseStudies();
                    promise.push(cases);
                    return Promise.all(promise);
                } else {
                    let er = {
                        "message": 'There is no model selected!',
                        "status_code": "CaseError"
                    }
                    Message.loaderEnd();
                    return Promise.reject(er);
                    // MessageSelect.init(RTSM.refreshPage.bind(RTSM));
                    // throw new Error('No Model selected');
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RTSMdata, cases] = data;
                //console.log('RTSMdata ', RTSMdata)
                if (RTSMdata[param]['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    return Promise.reject(er);
                } else {
                    let model = new Model(casename, genData, RTSMdata, group, PARAMETERS, param, cases);
                    this.initPage(model);
                    this.initEvents(model);
                }
            })
            .catch(error => {
                if (error.status_code == 'CaseError') {
                    MessageSelect.init(RTSM.refreshPage.bind(RTSM));
                }
                else if (error.status_code == 'ActivityError') {
                    MessageSelect.activity(RTSM.refreshPage.bind(RTSM), error.casename);
                }
                Message.loaderEnd();
                Message.warning(error);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        

        //Navbar.initPage(model.casename);
        Html.title(model.casename, model.PARAMNAMES[model.param], GROUPNAMES[model.group]);
        Html.ddlParams(model.PARAMETERS['RTSM'], model.param);

        let $divGrid = $('#osy-gridRTSM');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns,  {groupable: false, filterable: true,pageable:false, sortable:true});

        if (model.scenariosCount > 1) {
            Html.lblScenario( model.scenariosCount);
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            // Html.ddlTechNames(model.techs[model.param], model.techs[model.param][0]['StgId']);
            // Html.ddlCommNames(model.comms[model.param][model.techs[model.param][0]['StgId']], model.comms[model.param][model.techs[model.param][0]['TechId']][0]['StgId']);
            //Grid.applyRYTCFilter($divGrid, model.years);

            Grid.applyRSTMFilter($divGrid);
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
                const RTSMdata = Osemosys.getData(casename, 'RTSM.json');
                promise.push(RTSMdata);
                const cases = Base.getCaseStudies();
                promise.push(cases);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RTSMdata, cases] = data;
                if (RTSMdata[PARAMETERS['RTSM'][0]['id']]['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    return Promise.reject(er);
                } else {
                    let model = new Model(casename, genData, RTSMdata, 'RTSM', PARAMETERS, PARAMETERS['RTSM'][0]['id'], cases);
                    this.initPage(model);
                    this.initEvents(model);
                }
            })
            .catch(error => {
                setTimeout(function () {
                    if (error.status_code == 'CaseError') {
                        MessageSelect.init(RTSM.refreshPage.bind(RTSM));
                    }
                    else if (error.status_code == 'ActivityError') {
                        MessageSelect.activity(RTSM.refreshPage.bind(RTSM), error.casename);
                    }
                    Message.loaderEnd();
                    Message.warning(error.message);
                }, 500);
            });
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRTSM');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            RTSM.refreshPage(casename);
            Html.updateCasePicker(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);

        });

        $("#osy-saveRTSMdata").off('click');
        $("#osy-saveRTSMdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let param = $("#osy-ryt").val();
            let rytData = $divGrid.jqxGrid('getboundrows');
            let data = JSON.parse(JSON.stringify(rytData, ['ScId', 'TechId', 'StgId', 'MoId', 'Value']));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });
            Osemosys.updateData(saveData, param, "RTSM.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RTSM.json");
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
        });

        $("#osy-ryt").off('change');
        $('#osy-ryt').on('change', function () {
            Message.clearMessages();
            if (model.RTSMdata[this.value]['SC_0'].length === 0) {
                MessageSelect.activity(RTSM.refreshPage.bind(RTSM), model.casename);
                //Message.warning(`There is no data definded for ${model.PARAMNAMES[this.value]} for Model ${model.casename}!`);
            } else {
                Html.title(model.casename, model.PARAMNAMES[this.value], GROUPNAMES[model.group]);
                model.srcGrid.root = this.value;
                $divGrid.jqxGrid('updatebounddata');
                model.param =  this.value;
                Grid.applyRSTMFilter($divGrid);
                $('#definition').html(`${DEF[model.group][model.param].definition}`);
                //Grid.applyGridFilter($divGrid, model.years);
                //update za ddl coms i techs za IAR ili OAR
                // Html.ddlTechs(model.techs[this.value], model.techs[this.value][0]['TechId']);
                // Html.ddlComms(model.comms[this.value][model.techs[this.value][0]['TechId']], model.comms[this.value][model.techs[this.value][0]['TechId']][0]['StgId']);

                // Html.ddlTechNames(model.techs[this.value], model.techs[this.value][0]['TechId']);
                // Html.ddlCommNames(model.comms[this.value][model.techs[this.value][0]['TechId']], model.comms[this.value][model.techs[this.value][0]['TechId']][0]['StgId']);
            }
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
            Grid.applyRSTMFilter($divGrid, sc, model.param);
            Message.smallBoxInfo('Info', 'Scenario data opened!', 2000);
        });
        
        $("#osy-hideScData").off('click');
        $("#osy-hideScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Html.lblScenario( model.scenariosCount);
            Grid.applyRSTMFilter($divGrid);
            Message.smallBoxInfo('Info', 'Scenario data hidden!', 2000);
        });

        $("#osy-removeScData").off('click');
        $("#osy-removeScData").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            Message.loaderStart('Removing scenario data...');
            var sc = $("#osy-scenarios").val();

            var rows = $divGrid.jqxGrid('getdisplayrows');
            $.each(rows, function (id, obj) {
                if (obj.Sc == sc) {
                        $divGrid.jqxGrid('setcellvalue', obj.uid, 'Value', null);   
                }
            });

            Html.lblScenario( model.scenariosCount);
            Grid.applyRSTMFilter($divGrid);
            Message.smallBoxInfo('Info', 'Scenario data removed!', 2000);
            Message.loaderEnd();
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
                    //update grid model
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
                var stgId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'StgId');
                var moId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'MoId');
                var ScId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');

                //update grid model
                $.each(model.gridData[model.param], function (id, obj) {
                    if (obj.TechId == techId && obj.StgId == stgId && obj.ScId == ScId && obj.MoId == moId) {
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
        $("#resizeColumns").on('click', function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
                $divGrid.jqxGrid('autoresizecolumn', 'Tech');
                $divGrid.jqxGrid('autoresizecolumn', 'Stg');
                $divGrid.jqxGrid('autoresizecolumn', 'ModId');
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
            let data = JSON.parse(JSON.stringify(rytData, ['Sc', 'Tech', 'Stg','MoId'].concat(model.years)));

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

        Message.loaderEnd();
    }
}