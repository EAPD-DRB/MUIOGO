import { DataModel } from "../../Classes/DataModel.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";

export class Model {

    constructor(casename, genData, RTdata, group, PARAMETERS, param) {
        if(param == 'OL'){
            this.d = 0;
            this.decimal = 'n0';

        }
        else{
            this.d = 2;
            this.decimal = 'd' + this.d;
        }

        if (casename) {

            let datafields = [];
            let datafieldsChart = [];
            let columns = [];
            let series = [];

            let techs = genData['osy-tech'];
            let scenarios = genData['osy-scenarios'];
            this.param = param;

            let RTgrid = DataModel.RTgrid(genData, RTdata, PARAMETERS);
            let RTchart = DataModel.RTchart(genData, RTdata);
            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);

            let techUnit = {};;
            $.each(RTgrid, function (paramId, array) {
                techUnit[paramId] = {};
                $.each(array, function (id, obj) {
                    $.each(techs, function (idT, tech) {
                        techUnit[paramId][tech.TechId] = obj[tech.TechId + '_UnitId'];
                    });
                });
            });

            let scClass = {};

            //datafieldsChart.push({ name: 'TechId', type:'string' });
            datafieldsChart.push({ name: 'Tech', type: 'string' });

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
                    } 
                    else if(!Number.isInteger(value) && this.param =='OL'){
                        return { result: false, message: 'Operation life cannot be decimal number!' };
                    }
                    else {
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
                    return '<span style="margin: 4px; float:right; ">' + formattedValue + '</span>';
                }

            }.bind(this);

            let initeditor = function (row, cellvalue, editor, data) {                
                var scId = $('#osy-gridRT').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: true }); 
                    //editor.jqxNumberInput({ spinButtons: true, allowNull: true }); 
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            $('#' + editor[0].id).val(null);
                        }
                    })
                }else{
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: false, allowNull: false }); 
                    //editor.jqxNumberInput({  spinButtons: false, allowNull: false }); 
                    editor.val(cellvalue);
                }

            }.bind(this);

            let geteditorvalue =  function (row, cellvalue, editor) {
                return editor.val() == null ? null : editor.val();
            }

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', cellclassname: cellclass, minWidth: 75, maxWidth: 200, menu: false }); // minWidth: 75, maxWidth: 150,
            columns.push({ text: 'Parameter', datafield: 'Param', pinned: true, editable: false, align: 'left', cellclassname: cellclass, minWidth: 75, maxWidth: 200, menu: false });

            let techIds = [];
            $.each(techs, function (id, tech) {
                techIds.push(tech.TechId);
                let techName = tech.Tech + ' <small  style="color:darkgrey">[ ' + techUnit[param][tech.TechId] + ' ]</small>'
                datafields.push({ name: tech['TechId'], type: 'number' });
                columns.push({
                    text: techName, 
                    datafield: tech.TechId, cellsalign: 'right', align: 'center', columntype: 'numberinput', cellsformat: this.decimal, minWidth: 150, maxWidth: 300,
                    groupable: false,
                    initeditor: initeditor,
                    validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass,
                    geteditorvalue:  geteditorvalue, menu: false
                });
            }.bind(this));

            let srcGrid = {
                datatype: "json",
                localdata: RTgrid,
                root: param,
                datafields: datafields,
            };

            var srcChart = {
                datatype: "json",
                localdata: RTchart,
                root: param,
                datafields: datafieldsChart,
            };

            this.casename = casename;
            this.techs = techs;
            this.techIds = techIds;
            this.techNames = DataModel.TechName(genData);
            this.techsCount = techs.length
            this.techUnit = techUnit;
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.columns = columns;
            this.series = series;
            this.gridData = RTgrid;
            this.chartData = RTchart;
            this.genData = genData;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.srcGrid = srcGrid,
            this.srcChart = srcChart,
            this.PARAMETERS = PARAMETERS
        } 
        else {
            this.casename = null;
            this.years = null;
            this.techs = null;
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