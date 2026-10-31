import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor(casename, genData, RYCTsdata, group, PARAMETERS, param) {
        this.d = 3;
        this.decimal = 'd' + this.d;

        if (casename) {
            let datafields = [];
            let columns = [];

            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);
            let RYCTsgrid = DataModel.RYCTsgrid(genData, RYCTsdata, PARAMETERS);

            let years = genData['osy-years'];
            let comms = genData['osy-comm'];
            let scenarios = genData['osy-scenarios'];

            let scClass = {};
            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
            });

            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'TsId', type: 'string' });
            datafields.push({ name: 'Ts', type: 'string' });
            datafields.push({ name: 'CommId', type: 'string' });
            datafields.push({ name: 'Comm', type: 'string' });
            datafields.push({ name: 'Timeslice', type: 'string' });
            datafields.push({ name: 'UnitId', type: 'string' });
            datafields.push({ name: 'ScDesc', type: 'string' });
            datafields.push({ name: 'CommDesc', type: 'string' });

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
                var scId = $('#osy-gridRYCTs').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: true }); //symbol: ' GWh', symbolPosition: 'right'
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            $('#' + editor[0].id).val(null);
                        }
                    })
                }else{
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: false }); //symbol: ' GWh', symbolPosition: 'right'
                    editor.val(cellvalue);
                }
            }.bind(this);

            let geteditorvalue =  function (row, cellvalue, editor) {
                return editor.val() == null ? null : editor.val();
            }

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', minWidth: 75, maxWidth: 150, filterable: false, menu:false, cellclassname: cellclass });
            columns.push({ text: 'Commodity', datafield: 'Comm', pinned: true, editable: false, align: 'center',minWidth: 75, maxWidth: 150, cellclassname: cellclass });
            columns.push({ text: 'Timeslice', datafield: 'Ts', pinned: true, editable: false, align: 'center',minWidth: 55, maxWidth: 90, filterable: false, cellclassname: cellclass });
            columns.push({ text: 'Unit', datafield: 'UnitId', pinned: true, editable: false, align: 'center', cellsalign: 'center', cellclassname: cellclass,minWidth: 55, maxWidth: 90, sortable:false, filterable: false, menu:false });
            
            $.each(years, function (id, year) {
                datafields.push({ name: year, type: 'number' });
                columns.push({
                    text: year, datafield: year, cellsalign: 'right', align: 'center', columntype: 'numberinput',  cellsformat: this.decimal, minWidth: 55, maxWidth: 110,
                    groupable: false,
                    filterable: false,
                    sortable: false,
                    initeditor: initeditor,
                    validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass,
                    geteditorvalue:geteditorvalue, menu:false
                });
            }.bind(this));

            var srcGrid = {
                datatype: "json",
                localdata: RYCTsgrid,
                root: param,
                datafields: datafields,
            };

            this.casename = casename;
            this.years = years;
            this.comms = comms;
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.datafields = datafields;
            this.columns = columns;
            this.gridData = RYCTsgrid;
            this.genData = genData;
            this.param = param;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.srcGrid = srcGrid;
            this.PARAMETERS = PARAMETERS
        } else {
            this.casename = null;
            this.years = null;
            this.comms = null;
            this.datafields = null;
            this.columns = null;
            this.gridData = null;
            this.genData = null;
            this.param = param;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.srcGrid = null;
            this.PARAMETERS = PARAMETERS
        }
    }
}