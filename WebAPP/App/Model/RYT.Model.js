import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor(casename, genData, RYTdata, group, PARAMETERS, param) {

        let paramData = DataModel.getParamData(PARAMETERS);

        this.d = 3;
        this.decimal = 'd' + this.d;

        if (casename) {

            let datafields = [];
            let columns = [];
            let years = genData['osy-years'];
            let techs = genData['osy-tech'];
            let scenarios = genData['osy-scenarios'];
            this.param = param;

            let RYTgrid = DataModel.RYTgrid(genData, RYTdata, PARAMETERS);
            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);

            let scClass = {};
            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
            });

            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'TechId', type: 'string' });
            datafields.push({ name: 'Tech', type: 'string' });
            datafields.push({ name: 'ScDesc', type: 'string' });
            datafields.push({ name: 'TechDesc', type: 'string' });
            datafields.push({ name: 'UnitId', type: 'string' });

            let validation = function (cell, value) {
                if (['CC', 'FC'].includes(this.param)){
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
                    return '<span style="margin: 4px; float:right; ">' + formattedValue + '</span>';
                }
            }.bind(this);

            let initeditor = function (row, cellvalue, editor, data) {
                
                var scId = $('#osy-gridRYT').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: false, allowNull: true }); //symbol: ' GWh', symbolPosition: 'right'
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            editor.jqxNumberInput('val',null); 
                        }
                    })
                }else{
                    editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: false, allowNull: false }); //symbol: ' GWh', symbolPosition: 'right'
                    editor.val(cellvalue);
                }

            }.bind(this);

            let geteditorvalue =  function (row, cellvalue, editor) {           
                return editor.val() == null ? null : editor.val();
            }

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', cellclassname: cellclass, enabletooltips: true, filterable: false, menu:false}); 
            columns.push({ text: 'Technology', datafield: 'Tech', pinned: true, editable: false, align: 'left', cellclassname: cellclass, enabletooltips: true, filterable: true});
            columns.push({ text: 'Unit', datafield: 'UnitId', pinned: true, editable: false, align: 'center', cellsalign: 'center', cellclassname: cellclass, filterable: false, sortable: false,menu:false });

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
                    geteditorvalue:  geteditorvalue,
                    menu:false
                });
            }.bind(this));

            let srcGrid = {
                datatype: "json",
                localdata: RYTgrid,
                root: param,
                datafields: datafields,
            };

            this.casename = casename;
            this.years = years;
            this.techs = techs;
            this.param = param;
            this.techsCount = techs.length
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.columns = columns;
            this.gridData = RYTgrid;
            this.genData = genData;
            this.paramData = paramData;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.srcGrid = srcGrid,
            this.PARAMETERS = PARAMETERS
        } else {
            this.casename = null;
            this.years = null;
            this.techs = null;
            this.columns = null;
            this.gridData = null;
            this.genData = null;
            this.PARAMNAMES = null;
            this.param = param;
            this.group = group;
            this.srcGrid = srcGrid
            this.PARAMETERS = PARAMETERS
        }

    }
}