import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RYTC.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Chart } from "../../Classes/Chart.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class RYTC {
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
                    const RYTCdata = Osemosys.getData(casename, "RYTC.json");
                    promise.push(RYTCdata);
                    const cases = Base.getCaseStudies();
                    promise.push(cases);
                    return Promise.all(promise);
                } else {
                    let er = {
                        "message": 'There is no model selected!',
                        "status_code": "CaseError"
                    }
                    return Promise.reject(er);
                    // MessageSelect.init(RYTC.refreshPage.bind(RYTC));
                    // throw new Error('No model selected');
                }
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTCdata, cases] = data;
                if (RYTCdata[param]['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    return Promise.reject(er);
                } else {
                    let model = new Model(casename, genData, RYTCdata, group, PARAMETERS, param, cases);
                    this.initPage(model);
                    this.initEvents(model);
                }
            })
            .catch(error => {
                if (error.status_code == 'CaseError') {
                    MessageSelect.init(RYTC.refreshPage.bind(RYTC));
                }
                else if (error.status_code == 'ActivityError') {
                    MessageSelect.activity(RYTC.refreshPage.bind(RYTC), error.casename);
                }
                Message.warning(error);
            });
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
                const RYTCdata = Osemosys.getData(casename, 'RYTC.json');
                promise.push(RYTCdata);
                const cases = Base.getCaseStudies();
                promise.push(cases);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, PARAMETERS, RYTCdata, cases] = data;
                if (RYTCdata['INCR']['SC_0'].length == 0 && RYTCdata['ITCR']['SC_0'].length == 0) {
                    let er = {
                        "message": 'There is no activity defined!',
                        "status_code": "ActivityError",
                        "casename": casename
                    }
                    return Promise.reject(er);
                } else {
                    let param;
                    if (RYTCdata['INCR']['SC_0'].length == 0){
                        param = 'ITCR';
                    }else{
                        param = 'INCR';
                    }
                    
                    let model = new Model(casename, genData, RYTCdata, 'RYTC', PARAMETERS, param, cases);
                    this.initPage(model);
                    this.initEvents(model);
                }
            })
            .catch(error => {
                setTimeout(function () {
                    if (error.status_code == 'CaseError') {
                        MessageSelect.init(RYTC.refreshPage.bind(RYTC));
                    }
                    else if (error.status_code == 'ActivityError') {
                        MessageSelect.activity(RYTC.refreshPage.bind(RYTC), error.casename);
                    }
                    Message.warning(error.message);
                }, 500);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        Html.title(model.casename, model.PARAMNAMES[model.param], GROUPNAMES[model.group]);
        Html.ddlParams(model.PARAMETERS['RYTC'], model.param);

        // Html.ddlTechs(model.techs[model.param], model.techs[model.param][0]['TechId']);
        // Html.ddlComms(model.comms[model.param][model.techs[model.param][0]['TechId']], model.comms[model.param][model.techs[model.param][0]['TechId']][0]['CommId']);
        
        let $divGrid = $('#osy-gridRYTC');
        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns, {filterable: true, sortable:true});
        //Grid.Grid($divGrid, daGrid, model.columns, true);

        if (model.scenariosCount > 1) {
            Html.lblScenario( model.scenariosCount);
            Html.ddlScenarios(model.scenarios, model.scenarios[1]['ScenarioId']);
            Grid.applyGridFilter($divGrid, model.years);
        }
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridRYTC');
        let $divChart = $('#osy-chartRYTC');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            RYTC.refreshPage(casename);
            Html.updateCasePicker(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveRYTCdata").off('click');
        $("#osy-saveRYTCdata").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let param = $("#osy-ryt").val();
            let rytData = $divGrid.jqxGrid('getboundrows');
            let data = JSON.parse(JSON.stringify(rytData, ['ScId', 'TechId', 'CommId'].concat(model.years)));

            let saveData = {};
            $.each(data, function (id, obj) {
                if (!saveData[obj.ScId]) { saveData[obj.ScId] = []; }
                saveData[obj.ScId].push(obj);
                delete obj.ScId;
            });

            Osemosys.updateData(saveData, param, "RYTC.json")
                .then(response => {
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    //sync S3
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, "RYTC.json");
                    }
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
        });

        $("#osy-ryt").off('change');
        $('#osy-ryt').on('change', function () {
            Message.clearMessages();
            if (model.RYTCdata[this.value]['SC_0'].length === 0) {
                MessageSelect.activity(RYTC.refreshPage.bind(RYTC), model.casename);
                Message.warning(`There is no data definded for ${model.PARAMNAMES[this.value]} for model ${model.casename}!`);
            } else {
                Html.title(model.casename, model.PARAMNAMES[this.value], GROUPNAMES[model.group]);
                model.srcGrid.root = this.value;
                $divGrid.jqxGrid('updatebounddata');
                model.param = this.value;

                //update za ddl coms i techs za IAR ili OAR
                // Html.ddlTechs(model.techs[this.value], model.techs[this.value][0]['TechId']);
                // Html.ddlComms(model.comms[this.value][model.techs[this.value][0]['TechId']], model.comms[this.value][model.techs[this.value][0]['TechId']][0]['CommId']);

                // Html.ddlTechNames(model.techs[this.value], model.techs[this.value][0]['TechId']);
                // Html.ddlCommNames(model.comms[this.value][model.techs[this.value][0]['TechId']], model.comms[this.value][model.techs[this.value][0]['TechId']][0]['CommId']);

                // var configChart = $divChart.jqxChart('getInstance');
                // var tech = $("#osy-techs").val();
                // var comm = $("#osy-comms").val();
                // configChart.source.records = model.chartData[this.value][tech][comm];
                // configChart.update();
                $('#definition').html(`${DEF[model.group][model.param].definition}`);
            }
        });

        // $("#osy-techs").off('change');
        // $('#osy-techs').on('change', function () {
        //     var param = $("#osy-ryt").val();
        //     Html.ddlComms(model.comms[param][this.value], model.comms[param][this.value][0]['CommId']);
        //     var comm = $("#osy-comms").val();
        //     var configChart = $divChart.jqxChart('getInstance');
        //     configChart.source.records = model.chartData[param][this.value][comm];
        //     configChart.update();
        // });

        // $("#osy-comms").off('change');
        // $('#osy-comms').on('change', function () {
        //     var param = $("#osy-ryt").val();
        //     var tech = $("#osy-techs").val();
        //     var configChart = $divChart.jqxChart('getInstance');
        //     configChart.source.records = model.chartData[param][tech][this.value];
        //     configChart.update();
        // });

        // $("#osy-techNames").off('change');
        // $('#osy-techNames').on('change', function () {
        //     var param = $("#osy-ryt").val();
        //     let tech = model.techIds[this.value];
        //     Html.ddlCommNames(model.comms[param][tech], model.comms[param][tech][0]['CommId']);
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
            // var comm = $("#osy-commNames").val();
            // var tech = $("#osy-techNames").val();
            // Grid.applyRYTCFilter($divGrid, model.years, sc, tech, comm);
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
            // var comm = $("#osy-commNames").val();
            // var tech = $("#osy-techNames").val();
            // var rows = $divGrid.jqxGrid('getdisplayrows');
            // $.each(rows, function (id, obj) {
            //     if (obj.Sc == sc && obj.Comm == comm && obj.Tech == tech) {
            //         $.each(model.years, function (i, year) {
            //             $divGrid.jqxGrid('setcellvalue', obj.uid, year, null);
            //         });
            //         return false; // breaks
            //     }
            // });
            // Grid.applyRYTCFilter($divGrid, model.years);

            var rows = $divGrid.jqxGrid('getdisplayrows');
            $.each(rows, function (id, obj) {
                if (obj.Sc == sc) {
                    $.each(model.years, function (i, year) {
                        $divGrid.jqxGrid('setcellvalue', obj.uid, year, null);
                    });
                }
            });

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
                    let tech = $("#osy-techs").val();
                    let comm = $("#osy-comms").val();

                    //update grid model
                    model.gridData[param] = gridData;

                    //update chart model
                    // $.each(model.techs[param], function (idT, tech) {
                    //     $.each(model.comms[param][tech.TechId], function (idT, comm) {
                    //         let chartData = [];
                    //         $.each(model.years, function (idY, year) {
                    //             let chunk = {};
                    //             chunk['Year'] = year;
                    //             $.each(gridData, function (id, obj) {
                    //                 if (obj.TechId == tech.TechId && obj.CommId == comm.CommId) {
                    //                     chunk[obj.ScId] = obj[year];
                    //                 }
                    //             });
                    //             chartData.push(chunk);
                    //         });
                    //         model.chartData[param][tech.TechId][comm.CommId] = chartData;
                    //     });
                    // });

                    // var configChart = $divChart.jqxChart('getInstance');
                    // configChart.source.records = model.chartData[param][tech][comm];
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
                var commId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'CommId');
                var ScId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');

                // let param = $("#osy-ryt").val();
                // let tech = $("#osy-techs").val();
                // let comm = $("#osy-comms").val();

                //update chart model
                // $.each(model.chartData[param][techId][commId], function (id, obj) {
                //     if (obj.Year == year) {
                //         if (value) {
                //             obj[ScId] = value;
                //         } else {
                //             obj[ScId] = 0;
                //         }
                //     }
                // });

                // var configChart = $divChart.jqxChart('getInstance');
                // configChart.source.records = model.chartData[param][tech][comm];
                // configChart.update();

                //update grid model
                $.each(model.gridData[model.param], function (id, obj) {
                    if (obj.TechId == techId && obj.CommId == commId && obj.ScId == ScId) {
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

        $("#exportPng").off('click');
        $("#exportPng").on('click', function () {
            $("#osy-chartRYTC").jqxChart('saveAsPNG', 'RYTC.png', 'https://www.jqwidgets.com/export_server/export.php');
        });

        let res = true;
        $("#resizeColumns").off('click');
        $("#resizeColumns").on('click', function () {
            if (res) {
                $divGrid.jqxGrid('autoresizecolumn', 'Sc');
                $divGrid.jqxGrid('autoresizecolumn', 'Tech');
                $divGrid.jqxGrid('autoresizecolumn', 'Comm');
            }
            else {
                $divGrid.jqxGrid('autoresizecolumns');
            }
            res = !res;
        });

        $("#xlsAll").off('click');
        $("#xlsAll").on('click', function (e) {
            e.preventDefault();
            $("#osy-gridRYTC").jqxGrid('exportdata', 'xls', 'RYTC');
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