import { DataModel } from "../../Classes/DataModel.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";

export class Model {

    constructor(casename, genData, RSdata, group, PARAMETERS, param) {
        this.d = 0;
        //this.decimal = 'd' + this.d;
        this.decimal = "n0";

        if (casename) {

            let datafields = [];
            let datafieldsChart = [];
            let columns = [];
            let series = [];

            let stgs = genData['osy-stg'];
            let scenarios = genData['osy-scenarios'];
            this.param = param;

            let RSgrid = DataModel.RSgrid(genData, RSdata, PARAMETERS);
            let RSchart = DataModel.RSchart(genData, RSdata);
            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);

            let stgUnit = {};
            $.each(RSgrid, function (paramId, array) {
                stgUnit[paramId] = {};
                $.each(array, function (id, obj) {
                    $.each(stgs, function (idT, stg) {
                        stgUnit[paramId][stg.StgId] = obj[stg.StgId + '_UnitId'];
                    });
                });
            });

            let scClass = {};

            //datafieldsChart.push({ name: 'TechId', type:'string' });
            datafieldsChart.push({ name: 'Stg', type: 'string' });

            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
                datafieldsChart.push({ name: obj.ScenarioId, type: 'number' });
                series.push({ dataField: obj.ScenarioId, displayText: obj.Scenario });
            });

            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'ParamId', type: 'string' });
            datafields.push({ name: 'Param', type: 'string' });
            datafields.push({ name: 'ScDesc', type: 'string' });

            let validation = function (cell, value) {
                if (['TMPAL', 'TMPAU'].includes(this.param)){
                    return true;
                }else{
                    if (value < 0) {
                        return { result: false, message: 'Value must be positive!' };
                    } else {
                        return true;
                    }
                }
            }.bind(this);

            var cellclass = function (row, columnfield, value, data) {
                return scClass[data.ScId];
            }

            let cellsrenderer = function (row, columnfield, value, defaulthtml, columnproperties) {
                if (value === null || value === '') {
                    return '<span style="margin: 4px; float:right; ">n/a</span>';
                } else {
                    var formattedValue = $.jqx.dataFormat.formatnumber(value, this.decimal);

                    // if(columnfield == 'TEC_0' && row == 0){
                    //     console.log('cellsrenderer ', value)
                    //     console.log('formattedValue ', formattedValue)
                    // }

                    return '<span style="margin: 4px; float:right; ">' + formattedValue + '</span>';
                }

            }.bind(this);

            let initeditor = function (row, cellvalue, editor, data) {                
                var scId = $('#osy-gridRS').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: true }); 
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            $('#' + editor[0].id).val(null);
                        }
                    })
                }else{
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: false, allowNull: false }); 
                    editor.val(cellvalue);
                }

            }.bind(this);

            let geteditorvalue =  function (row, cellvalue, editor) {
                return editor.val() == null ? null : editor.val();
            }

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', cellclassname: cellclass, minWidth: 75, maxWidth: 200, menu:false }); // minWidth: 75, maxWidth: 150,
            columns.push({ text: 'Parameter', datafield: 'Param', pinned: true, editable: false, align: 'left', cellclassname: cellclass, minWidth: 75, maxWidth: 200 , menu:false});

            let stgIds = [];
            $.each(stgs, function (id, stg) {
                stgIds.push(stg.StgId);
                datafields.push({ name: stg.StgId, type: 'number' });
                columns.push({
                    text: stg.Stg + ' <small  style="color:darkgrey">[ ' + stgUnit[param][stg.StgId] + ' ]</small>', 
                    datafield: stg.StgId, cellsalign: 'right', align: 'center', columntype: 'numberinput', cellsformat: this.decimal, minWidth: 150, maxWidth: 300,
                    groupable: false,
                    initeditor: initeditor,
                    validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass,
                    geteditorvalue:  geteditorvalue, menu:false
                });
            }.bind(this));

            let srcGrid = {
                datatype: "json",
                localdata: RSgrid,
                root: param,
                datafields: datafields,
            };

            var srcChart = {
                datatype: "json",
                localdata: RSchart,
                root: param,
                datafields: datafieldsChart,
            };

            this.casename = casename;
            // this.param = param;
            //this.years = years;
            this.stgs = stgs;
            this.stgIds = stgIds;
            this.stgCount = stgs.length
            this.stgUnit = stgUnit;
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.columns = columns;
            this.series = series;
            this.gridData = RSgrid;
            this.chartData = RSchart;
            this.genData = genData;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.srcGrid = srcGrid,
                this.srcChart = srcChart,
                this.PARAMETERS = PARAMETERS
        } else {
            this.casename = null;
            this.years = null;
            this.stgs = null;
            // this.datafields = null; 
            // this.datafieldsChart = null; 
            this.columns = null;
            this.series = null;
            this.gridData = null;
            this.chartData = null;
            this.genData = null;
            this.PARAMNAMES = null;
            this.param = param;
            this.group = group;
            this.srcGrid = srcGrid
            this.srcChart = srcChartm
            this.PARAMETERS = PARAMETERS
        }

    }
}