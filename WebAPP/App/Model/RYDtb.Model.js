import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor(casename, genData, RYTsdata, group, PARAMETERS, param) {
        this.d = 3;
        this.decimal = 'd' + this.d;
        if (casename) {

            let datafields = [];
            let columns = [];
            let years = genData['osy-years'];
            let scenarios = genData['osy-scenarios'];

            let RYDtbgrid = DataModel.RYDtbgrid(genData, RYTsdata);

            let scClass = {};

            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
            });

            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'DtbId', type: 'string' });
            datafields.push({ name: 'Dtb', type: 'string' });
            datafields.push({ name: 'ScDesc', type: 'string' });

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', cellclassname: cellclass, enabletooltips: true, menu:false });
            columns.push({ text: 'Dailytimebracket', datafield: 'Dtb', pinned: true, editable: false, align: 'center', cellclassname: cellclass, enabletooltips: true, menu:false })

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
                if(row == 4 && columnfield == '2020')
                if (value === null || value === '') {
                    return '<span style="margin: 4px; float:right; ">n/a</span>';
                } else {
                    var formattedValue = $.jqx.dataFormat.formatnumber(value, this.decimal);
                    return '<span style="margin: 4px; float:right; ">' + formattedValue + '</span>';
                }

            }.bind(this);

            let initeditor = function (row, cellvalue, editor, data) {
                var scId = $('#osy-gridRYDtb').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: false, allowNull: true }); 
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            editor.jqxNumberInput('val',null); 
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

            $.each(years, function (id, year) {
                datafields.push({ name: year, type: 'number' });
                columns.push({
                    text: year, datafield: year, cellsalign: 'right', align: 'center', columntype: 'numberinput', cellsformat: this.decimal, minWidth: 55, maxWidth: 110,
                    filterable: false,
                    groupable: false,
                    sortable: false,
                    initeditor: initeditor,
                    validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass,
                    geteditorvalue: geteditorvalue, menu:false
                });
            }.bind(this));

            let PARAMNAMES = {};
            $.each(PARAMETERS[group], function (id, obj) {
                PARAMNAMES[obj.id] = obj.value;
            });

            let srcGrid = {
                datatype: "json",
                root: param,
                localdata: RYDtbgrid,
                datafields: datafields,
            };

            this.casename = casename;
            this.years = years;
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.datafields = datafields;
            this.columns = columns;
            this.gridData = RYDtbgrid;
            this.genData = genData;
            this.srcGrid = srcGrid;
            this.param = param;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.PARAMETERS = PARAMETERS;
        } else {
            this.casename = null;
            this.years = null;
            this.datafields = null;
            this.columns = null;
            this.gridData = null;
            this.genData = null;
            this.srcGrid = null;
            this.param = param;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.PARAMETERS = PARAMETERS;
        }

    }
}