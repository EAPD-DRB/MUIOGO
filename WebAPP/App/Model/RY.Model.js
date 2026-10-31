import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor(casename, genData, RYdata, group, PARAMETERS, param) {

        this.d = 3;
        this.decimal = 'd' + this.d;

        if (casename) {

            let datafields = [];
            let datafieldsChart = [];
            let columns = [];
            let series = [];
            let years = genData['osy-years'];
            let scenarios = genData['osy-scenarios'];

            let scClass = {};

            let RYgrid = DataModel.RYgrid(genData, RYdata, PARAMETERS);
            let RYchart = DataModel.RYchart(genData, RYdata);
            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);

            datafields.push({ name: 'Param', type: 'string' });
            datafields.push({ name: 'ParamId', type: 'string' });
            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'UnitId', type: 'string' });
            datafields.push({ name: 'ScDesc', type: 'string' });

            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
                datafieldsChart.push({ name: obj.ScenarioId, type: 'number' });
                series.push({ dataField: obj.ScenarioId, displayText: obj.Scenario });
            });

            let validation = function (cell, value) {
                if (value < 0) {
                    return { result: false, message: 'Value must be positive!' };
                } else {
                    return true;
                }
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
                
                var scId = $('#osy-gridRY').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: true }); //symbol: ' GWh', symbolPosition: 'right'
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            $('#' + editor[0].id).val(null);
                        }
                    })
                }else{
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: false }); //symbol: ' GWh', symbolPosition: 'right'
                }

            }.bind(this);

            let geteditorvalue =  function (row, cellvalue, editor) {
                return editor.val() == null ? null : editor.val();
            }

            var cellclass = function (row, columnfield, value, data) {
                return scClass[data.ScId];
            }

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', minWidth: 75, maxWidth: 200 })
            columns.push({ text: 'Parameter', datafield: 'Param', pinned: true, editable: false, align: 'left', minWidth: 75, maxWidth: 200 })
            columns.push({ text: 'Unit', datafield: 'UnitId', pinned: true, editable: false, align: 'center', cellsalign: 'center', cellclassname: cellclass , minWidth: 55, maxWidth: 110});

            $.each(years, function (id, year) {
                datafields.push({ name: year, type: 'number' });
                columns.push({
                    text: year, datafield: year, cellsalign: 'right', align: 'center', columntype: 'numberinput', cellsformat: this.decimal, minWidth: 55, maxWidth: 110,
                    groupable: false,
                    initeditor: initeditor,
                    validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass,
                    geteditorvalue:  geteditorvalue
                });
            }.bind(this));

            datafieldsChart.push({ name: 'Year', type: 'string' });
            datafieldsChart.push({ name: 'Param', type: 'number' });

            let srcGrid = {
                datatype: "json",
                localdata: RYgrid,
                root: param,
                datafields: datafields,
            };

            var srcChart = {
                datatype: "json",
                localdata: RYchart,
                root: param,
                datafields: datafieldsChart,
            };

            this.casename = casename;
            this.years = years;
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.columns = columns;
            this.series = series;
            this.gridData = RYgrid;
            this.chartData = RYchart;
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
            this.scenarios = null;
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