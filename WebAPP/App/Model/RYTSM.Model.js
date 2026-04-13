import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor(casename, genData, RYTSMdata, group, PARAMETERS, param, cases) {
        this.d = 3;
        this.decimal = 'd' + this.d;
        if (casename) {

            let datafields = [];
            let columns = [];

            let years = genData['osy-years'];
            //let comms = genData['osy-comm'];
            let techs = genData['osy-tech'];
            let scenarios = genData['osy-scenarios'];
            let mods = DataModel.Mods(genData);

            let RYTSMgrid = DataModel.RYTSMgrid(genData, RYTSMdata, PARAMETERS);

            let techIds = DataModel.TechId(genData);
            let ActivityTechs = DataModel.activityTechs(techs);
            let ActivityComms = DataModel.activityComms(genData);

            let PARAMNAMES = DataModel.ParamName(PARAMETERS[group]);
            
            let scClass = {};
            //datafieldsChart.push({ name: 'Year', type: 'string' });
            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
                //datafieldsChart.push({ name: obj.ScenarioId, type: 'number' });
                //series.push({ dataField: obj.ScenarioId, displayText: obj.Scenario });
            });

            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'TechId', type: 'string' });
            datafields.push({ name: 'Tech', type: 'string' });
            datafields.push({ name: 'StgId', type: 'string' });
            datafields.push({ name: 'Stg', type: 'string' });
            datafields.push({ name: 'MoId', type: 'string' });
            datafields.push({ name: 'UnitId', type: 'string' });
            datafields.push({ name: 'ScDesc', type: 'string' });
            datafields.push({ name: 'TechDesc', type: 'string' });
            datafields.push({ name: 'StgDesc', type: 'string' });

            columns.push({ text: 'Scenario', datafield: 'Sc', pinned: true, editable: false, align: 'left', cellclassname: cellclass, filterable: false  });
            columns.push({ text: 'Technology', datafield: 'Tech', pinned: true, editable: false, align: 'center', cellclassname: cellclass });
            columns.push({ text: 'Storage', datafield: 'Stg', pinned: true, editable: false, align: 'center', cellclassname: cellclass  });
            columns.push({ text: 'MoO', datafield: 'MoId', pinned: true, editable: false, align: 'center', cellsalign: 'center', cellclassname: cellclass, filterable: false  });
            columns.push({ text: 'Unit', datafield: 'UnitId', pinned: true, editable: false, align: 'center', cellsalign: 'center', cellclassname: cellclass, filterable: false  });


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
                
                var scId = $('#osy-gridRYTSM').jqxGrid('getcellvalue', row, 'ScId');
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
                    geteditorvalue: geteditorvalue
                });
            }.bind(this));

            var srcGrid = {
                datatype: "json",
                localdata: RYTSMgrid,
                root: param,
                datafields: datafields,
            };

            this.casename = casename;
            this.cases = cases;
            this.years = years;
            this.mods = mods;
            this.scenarios = scenarios;
            this.scenariosCount = scenarios.length;
            // this.techs = ActivityTechs;
            // this.stgs = ActivityComms;
            // this.techIds = techIds;
            this.datafields = datafields;
            this.columns = columns;

            this.RYTSMdata = RYTSMdata;
            this.gridData = RYTSMgrid;
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
            // this.techs = null;
            // this.stgs = null;
            // this.techIds = null;
            // this.datafields = null;

            this.columns = null;

            this.RYTSMdata = null;
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