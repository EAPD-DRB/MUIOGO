import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor(casename, genData, REdata, group, PARAMETERS, param) {
        this.d = 3;
        this.decimal = 'd' + this.d;

        if (casename) {

            let datafields = [];
            let datafieldsChart = [];
            let columns = [];
            let series = [];

            let emis = genData['osy-emis'];
            let scenarios = genData['osy-scenarios'];

            let REgrid = DataModel.REgrid(genData, REdata, PARAMETERS);
            let REchart = DataModel.REchart(genData, REdata);
            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);

            let emiUnit = {};;
            $.each(REgrid, function (paramId, array) {
                emiUnit[paramId] = {};
                $.each(array, function (id, obj) {
                    $.each(emis, function (idE, emi) {
                        emiUnit[paramId][emi.EmisId] = obj[emi.EmisId + '_UnitId'];
                    });
                });
            });

            let scClass = {};

            datafieldsChart.push({ name: 'Emi', type: 'string' });
            datafieldsChart.push({ name: 'EmiId', type: 'string' });

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
                if (value < 0) {
                    return { result: false, message: 'Value must be positive!' };
                } else {
                    return true;
                }
            }

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
                
                var scId = $('#osy-gridRE').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: true }); 
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            $('#' + editor[0].id).val(null);
                        }
                    })
                }else{
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: false }); 
                }

            }.bind(this);

            let geteditorvalue =  function (row, cellvalue, editor) {
                return editor.val() == null ? null : editor.val();
            }

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', cellclassname: cellclass, minWidth: 75, maxWidth: 200, menu: false }); 
            columns.push({ text: 'Parameter', datafield: 'Param', pinned: true, editable: false, align: 'left', cellclassname: cellclass, minWidth: 75, maxWidth: 200, menu: false });

            let emiIds = [];
            $.each(emis, function (id, emi) {
                emiIds.push(emi.EmisId);
                datafields.push({ name: emi.EmisId, type: 'number' });
                columns.push({
                    text: emi.Emis + ' <small  style="color:darkgrey">[ ' + emiUnit[param][emi.EmisId] + ' ]</small>', datafield: emi.EmisId, cellsalign: 'right', align: 'center', columntype: 'numberinput', 
                    cellsformat: this.decimal, minWidth: 110, maxWidth: 200,
                    groupable: false,
                    initeditor: initeditor,
                    //validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass,
                    geteditorvalue:  geteditorvalue, menu: false
                });
            }.bind(this));

            let srcGrid = {
                datatype: "json",
                localdata: REgrid,
                root: param,
                datafields: datafields,
            };

            var srcChart = {
                datatype: "json",
                localdata: REchart,
                //root: param+ '>' + techs[0]['TechId'],
                root: param,
                datafields: datafieldsChart,
            };

            this.casename = casename;
            this.emis = emis;
            this.emiIds = emiIds;
            this.emiNames = DataModel.EmiName(genData);
            this.emiUnit = emiUnit;
            this.emiCount = emis.length
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.columns = columns;
            this.series = series;
            this.gridData = REgrid;
            this.chartData = REchart;
            this.genData = genData;
            this.param = param;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.srcGrid = srcGrid,
                this.srcChart = srcChart,
                this.PARAMETERS = PARAMETERS
        } else {
            this.casename = null;
            this.years = null;
            this.techs = null;
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