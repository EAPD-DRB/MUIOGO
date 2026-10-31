import { DataModel } from "../../Classes/DataModel.Class.js";
import { GROUPNAMES } from "../../Classes/Const.Class.js";

export class Model {

    constructor(casename, genData, viewData, viewTEData, PARAMETERS) {

        this.d = 2;
        this.decimal = 'd' + this.d;
        if (casename) {

            let datafields = [];
            let columns = [];

            let years = genData['osy-years'];
            let techs = genData['osy-tech'];
            let comms = genData['osy-comm'];
            let emis = genData['osy-emis'];
            let scenarios = genData['osy-scenarios'];

            let TechName = DataModel.TechName(genData);
            let TsName = DataModel.TsName(genData);
            let CommName = DataModel.CommName(genData);
            let EmiName = DataModel.EmiName(genData);
            let ConName = DataModel.ConName(genData);
            let ScName = DataModel.ScName(genData);
            let unitData = DataModel.getUnitData(genData, PARAMETERS);
            let paramById = DataModel.getParamById(PARAMETERS);

            let scClass = {};

            $.each(scenarios, function (id, obj) {
                scClass[obj.ScenarioId] = 'SC_' + id;
            });

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

            let cellsrendererPinned = function (row, columnfield, value, defaulthtml, columnproperties) {
                if (value == '') {
                    return '<span style="margin: 4px; float:left; color: #a6a6a6; " >n/a</span>';
                }
            }.bind(this);

            let initeditor = function (row, cellvalue, editor, data) {
                editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: true }); //symbol: ' GWh', symbolPosition: 'right'

                var scId = $('#osy-gridViewData').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            $('#' + editor[0].id).val(null);
                        }
                    })
                }
            }.bind(this);

            let initeditorRT = function (row, cellvalue, editor, data) {
                editor.jqxNumberInput({ decimalDigits: this.d, spinButtons: true, allowNull: true }); //symbol: ' GWh', symbolPosition: 'right'

                var scId = $('#osy-gridRT').jqxGrid('getcellvalue', row, 'ScId');
                if (scId !== 'SC_0') {
                    $('#' + editor[0].id + ' input').keydown(function (event) {
                        if (event.keyCode === 46 || event.keyCode === 8) {
                            $('#' + editor[0].id).val(null);
                        }
                    })
                }
            }.bind(this);

            //grid datafields
            datafields.push({ name: 'ScId', type: 'string' });
            datafields.push({ name: 'Sc', type: 'string' });
            datafields.push({ name: 'TsId', type: 'string' });
            datafields.push({ name: 'Ts', type: 'string' });
            datafields.push({ name: 'groupId', type: 'string' });
            datafields.push({ name: 'groupName', type: 'string' });
            datafields.push({ name: 'param', type: 'string' });
            datafields.push({ name: 'paramName', type: 'string' });
            datafields.push({ name: 'TechId', type: 'string' });
            datafields.push({ name: 'TechName', type: 'string' });
            datafields.push({ name: 'CommId', type: 'string' });
            datafields.push({ name: 'CommName', type: 'string' });
            datafields.push({ name: 'EmisId', type: 'string' });
            datafields.push({ name: 'EmisName', type: 'string' });
            datafields.push({ name: 'ConId', type: 'string' });
            datafields.push({ name: 'ConName', type: 'string' });

            datafields.push({ name: 'MoId', type: 'string' });
            datafields.push({ name: 'UnitId', type: 'string' });

            columns.push({ text: 'ScId', datafield: 'ScId', editable: false, align: 'left', hidden: true });
            columns.push({ text: 'SCENARIO', datafield: 'Sc', editable: false, filterable: true, align: 'left', minWidth: 55, cellclassname: cellclass, menu:false });
            columns.push({ text: 'GROUP', datafield: 'groupId', editable: false, align: 'left', hidden: true });
            columns.push({ text: 'GROUP NAME', datafield: 'groupName', editable: false, filterable: true, align: 'left', hidden: true, cellclassname: cellclass, menu:false });
            columns.push({ text: 'param', datafield: 'param', editable: false, align: 'left', hidden: true });
            columns.push({ text: 'PARAMETER NAME', datafield: 'paramName', editable: false, filterable: true, align: 'left', minWidth: 75, cellclassname: cellclass, menu:false });
            columns.push({ text: 'UNIT', datafield: 'UnitId', editable: false, align: 'center', cellsalign: 'center', minWidth: 55, cellclassname: cellclass, menu:false });
            columns.push({ text: 'TECHNOLOGY', datafield: 'TechId', editable: false, align: 'left', hidden: true });
            columns.push({ text: 'TECHNOLOGY', datafield: 'TechName', editable: false, filterable: true, align: 'left', cellsrenderer: cellsrendererPinned, minWidth: 55, cellclassname: cellclass, menu:false });
            columns.push({ text: 'COMMODITY', datafield: 'CommId', editable: false, align: 'left', hidden: true });
            columns.push({ text: 'COMMODITY', datafield: 'CommName', editable: false, filterable: true, align: 'left', cellsrenderer: cellsrendererPinned, minWidth: 55, cellclassname: cellclass, menu:false });
            columns.push({ text: 'EMISSION', datafield: 'EmisId', editable: false, align: 'left', hidden: true });
            columns.push({ text: 'EMISSION', datafield: 'EmisName', editable: false, filterable: true, align: 'left', cellsrenderer: cellsrendererPinned, minWidth: 55, cellclassname: cellclass, menu:false });
            columns.push({ text: 'CONSTRAINT', datafield: 'ConId', editable: false, align: 'left', hidden: true });
            columns.push({ text: 'CONSTRAINT', datafield: 'ConName', editable: false, filterable: true, align: 'left', cellsrenderer: cellsrendererPinned, minWidth: 55, cellclassname: cellclass, menu:false })
            columns.push({ text: 'TIMESLICE', datafield: 'Ts', editable: false, filterable: true, align: 'left', cellsrenderer: cellsrendererPinned, minWidth: 55, cellclassname: cellclass, menu:false });
            columns.push({ text: 'MoO', datafield: 'MoId', editable: false, align: 'left', cellsrenderer: cellsrendererPinned, minWidth: 50, cellclassname: cellclass, menu:false});

            //datafields and columns
            $.each(years, function (id, year) {
                datafields.push({ name: year, type: 'number' });
                columns.push({
                    text: year, datafield: year, cellsalign: 'right', align: 'center', columntype: 'numberinput', cellsformat: 'd2', minWidth: 75,
                    filterable: false,
                    groupable: false,
                    initeditor: initeditor,
                    validation: validation,
                    cellsrenderer: cellsrenderer,
                    cellclassname: cellclass, menu:false
                });
            });

            $.each(viewData, function (byType, obj1) {
                $.each(obj1, function (tech, array) {
                    $.each(array, function (id, obj) {
                        obj['groupName'] = GROUPNAMES[obj.groupId];
                        obj['Sc'] = ScName[obj['ScId']];

                        if(obj.TsId != null){
                            obj['Ts'] = TsName[obj.TsId];
                        }

                        if (obj.Tech == null && obj.EmisId == null) {
                            obj['TechName'] = TechName[obj.TechId];
                            obj['CommName'] = null;
                            obj['EmisName'] = null;
                            obj['ConName'] = null;

                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data = unitData[obj.groupId][obj.param][obj.TechId];
                            obj['UnitId'] = jsonLogic.apply(rule, data);
                        }
                        if (obj.CommId == null && obj.EmisId == null && obj.ConId != null) {
                            obj['TechName'] = TechName[obj.TechId];
                            obj['CommName'] = null;
                            obj['EmisName'] = null;
                            obj['ConName'] = ConName[obj.ConId];
                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data = unitData[obj.groupId][obj.param][obj.TechId];
                            obj['UnitId'] = jsonLogic.apply(rule, data);
                        }
                        else if (obj.TechId == null && obj.EmisId == null) {
                            obj['TechName'] = null;
                            obj['CommName'] = CommName[obj.CommId];
                            obj['EmisName'] = null;
                            obj['ConName'] = null;
                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data = unitData[obj.groupId][obj.param][obj.CommId];
                            obj['UnitId'] = jsonLogic.apply(rule, data);
                        }
                        else if (obj.TechId == null && obj.CommId == null) {
                            obj['TechName'] = null;
                            obj['CommName'] = null;
                            obj['EmisName'] = EmiName[obj.EmisId];
                            obj['ConName'] = null;
                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data = unitData[obj.groupId][obj.param][obj.EmisId];
                            obj['UnitId'] = jsonLogic.apply(rule, data);
                        }
                        //RYTCM
                        else if (obj.EmisId == null) {
                            obj['TechName'] = TechName[obj.TechId];
                            obj['CommName'] = CommName[obj.CommId];
                            obj['EmisName'] = null;
                            obj['ConName'] = null;
                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data1 = unitData[obj.groupId][obj.param][obj.CommId];
                            let data2 = unitData[obj.groupId][obj.param][obj.TechId];
                            const data = { ...data1, ...data2 };
                            obj['UnitId'] = jsonLogic.apply(rule, data);

                        }
                        //RYTEM
                        else if (obj.CommId == null) {
                            obj['TechName'] = TechName[obj.TechId];
                            obj['CommName'] = null;
                            obj['EmisName'] = EmiName[obj.EmisId];
                            obj['ConName'] = null;
                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data1 = unitData[obj.groupId][obj.param][obj.EmisId];
                            let data2 = unitData[obj.groupId][obj.param][obj.TechId];
                            const data = { ...data1, ...data2 };
                            obj['UnitId'] = jsonLogic.apply(rule, data);
                        }

                    });
                });
            });

            let gridData = viewData;

            let srcGrid = {
                datatype: "json",
                localdata: gridData,
                root: genData["osy-tech"][0]['TechId'],
                datafields: datafields,
            };

            //RT RE
            $.each(viewTEData, function (byType, obj1) {
                $.each(obj1, function (tech, array) {
                    $.each(array, function (id, obj) {
                        obj['groupName'] = GROUPNAMES[obj['groupId']];
                        obj['Sc'] = ScName[obj['ScId']];
                        if (byType == 'Tech') {
                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data = unitData[obj.groupId][obj.param][tech];
                            obj['UnitId'] = jsonLogic.apply(rule, data);
                        }
                        else if (byType == 'Emi') {
                            let rule = paramById[obj.groupId][obj.param]['unitRule'];
                            let data = unitData[obj.groupId][obj.param][tech];
                            obj['UnitId'] = jsonLogic.apply(rule, data);
                        }
                    });
                });
            });

            let datafieldsRT = [];
            let columnsRT = [];

            datafieldsRT.push({ name: 'ScId', type: 'string' });
            datafieldsRT.push({ name: 'Sc', type: 'string' });

            datafieldsRT.push({ name: 'groupId', type: 'string' });
            datafieldsRT.push({ name: 'groupName', type: 'string' });
            datafieldsRT.push({ name: 'param', type: 'string' });
            datafieldsRT.push({ name: 'paramName', type: 'string' });
            datafieldsRT.push({ name: 'value', type: 'number' });
            datafieldsRT.push({ name: 'UnitId', type: 'string' });

            columnsRT.push({ text: 'ScId', datafield: 'ScId', editable: false, align: 'left', hidden: true });
            columnsRT.push({ text: 'SCENARIO', datafield: 'Sc', editable: false, align: 'left', cellclassname: cellclass, menu:false }); // minWidth: 75, maxWidth: 150,

            columnsRT.push({ text: 'GROUP', datafield: 'groupId', editable: false, align: 'left', hidden: true });
            columnsRT.push({ text: 'GROUP NAME', datafield: 'groupName', editable: false, align: 'left', hidden: true });
            columnsRT.push({ text: 'param', datafield: 'param', editable: false, align: 'left', hidden: true });
            columnsRT.push({ text: 'PARAMETER NAME', datafield: 'paramName', editable: false, align: 'left', minWidth: 75, cellclassname: cellclass, menu:false });
            columnsRT.push({ text: 'UNIT', datafield: 'UnitId', editable: false, align: 'center', cellsalign: 'center', minWidth: 55, cellclassname: cellclass, menu:false });
            columnsRT.push({
                text: 'Value', datafield: 'value', editable: true, cellsalign: 'right', align: 'center', columntype: 'numberinput', cellsformat: 'd2', minWidth: 75,
                initeditor: initeditorRT,
                validation: validation,
                cellsrenderer: cellsrenderer,
                cellclassname: cellclass, menu:false
            });

            let srcRTGrid = {
                datatype: "json",
                localdata: viewTEData,
                root: genData["osy-tech"][0]['TechId'],
                datafields: datafieldsRT,
            };

            this.group = 'ViewData';
            this.casename = casename;
            this.techs = techs;
            this.TechName = TechName;
            this.EmiName = EmiName;
            this.CommName = CommName;
            this.comms = comms;
            this.emis = emis;
            this.years = years;
            this.scenarios = scenarios;
            this.columns = columns;
            this.gridData = gridData;
            this.srcGrid = srcGrid;

            this.gridRTData = viewTEData;
            this.srcRTGrid = srcRTGrid;
            this.columnsRT = columnsRT;
            this.datafieldsRT = datafieldsRT;
        } else {
            this.casename = null;
            this.columns = null;
            this.gridData = null;
            this.srcGrid = srcGrid
        }
    }
}