import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor(casename, genData, RYTCMdata, group, PARAMETERS, param, cases) {
        this.d = 3;
        this.decimal = 'd' + this.d;
        if (casename) {

            let datafields = [];
            let columns = [];
            let series = [];

            let years = genData['osy-years'];
            let techs = genData['osy-tech'];
            let scenarios = genData['osy-scenarios'];

            let RYTCMgrid = DataModel.RYTCMgrid(genData, RYTCMdata, PARAMETERS);
            let RYTCMchart = DataModel.RYTCMchart(genData, RYTCMdata);
            let techIds = DataModel.TechId(genData);
            let ActivityTechs = DataModel.activityTechs(techs);
            let ActivityComms = DataModel.activityComms(genData);
            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);
            let mods = DataModel.Mods(genData);

            let scClass = {};

            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
            });

            var cellclass = function (row, columnfield, value, data) {
                return scClass[data.ScId];
            }

            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'TechId', type: 'string' });
            datafields.push({ name: 'Tech', type: 'string' });
            datafields.push({ name: 'CommId', type: 'string' });
            datafields.push({ name: 'Comm', type: 'string' });
            datafields.push({ name: 'MoId', type: 'string' });
            datafields.push({ name: 'UnitId', type: 'string' });
            datafields.push({ name: 'ScDesc', type: 'string' });
            datafields.push({ name: 'TechDesc', type: 'string' });
            datafields.push({ name: 'CommDesc', type: 'string' });

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', cellclassname: cellclass, filterable: false, menu:false  });
            columns.push({ text: 'Technology', datafield: 'Tech', pinned: true, editable: false, align: 'center', cellclassname: cellclass });
            columns.push({ text: 'Commodity', datafield: 'Comm', pinned: true, editable: false, align: 'center', cellclassname: cellclass  });
            columns.push({ text: 'MoO', datafield: 'MoId', pinned: true, editable: false, align: 'center', cellsalign: 'center', cellclassname: cellclass, filterable: false, menu:false  });
            columns.push({ text: 'Unit', datafield: 'UnitId', pinned: true, editable: false, align: 'center', cellsalign: 'center', cellclassname: cellclass, sortable:false, filterable: false, menu:false  });

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
                
                var scId = $('#osy-gridRYTCM').jqxGrid('getcellvalue', row, 'ScId');
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

            $.each(years, function (id, year) {
                datafields.push({ name: year, type: 'number' });
                columns.push({
                    text: year, datafield: year, cellsalign: 'right', align: 'center', columntype: 'numberinput', cellsformat: this.decimal, minWidth: 55, maxWidth: 110,
                    groupable: false,
                    filterable: false,
                    sortable: false,
                    initeditor: initeditor,
                    validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass,
                    geteditorvalue: geteditorvalue, menu:false
                });
            }.bind(this));

            var srcGrid = {
                datatype: "json",
                localdata: RYTCMgrid,
                root: param,
                datafields: datafields,
            };

            this.casename = casename;
            this.cases = cases;
            this.years = years;
            this.mods = mods;
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            this.techs = ActivityTechs;
            this.comms = ActivityComms;
            this.techIds = techIds;
            this.datafields = datafields;
            this.columns = columns;
            this.RYTCMdata = RYTCMdata;
            this.gridData = RYTCMgrid;
            this.genData = genData;
            this.param = param;
            this.PARAMNAMES = PARAMNAMES;
            this.group = group;
            this.srcGrid = srcGrid;
            this.PARAMETERS = PARAMETERS;
        } else {
            this.casename = null;
            this.years = null;
            this.scenarios = null;
            this.scenariosCount = null;
            this.techs = null;
            this.comms = null;
            this.techIds = null;
            this.datafields = null;
            this.columns = null;
            this.RYTCMdata = null;
            this.gridData = null;
            this.genData = null;
            this.param = null;
            this.PARAMNAMES = null;
            this.group = group;
            this.srcGrid = null;
            this.PARAMETERS = null;
        }

    }
}