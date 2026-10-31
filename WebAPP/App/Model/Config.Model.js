import { DataModel } from "../../Classes/DataModel.Class.js";
import { GROUPNAMES, PARAMORDER, UNITDEFINITION, RESULTGROUPNAMES } from "../../Classes/Const.Class.js";

export class Model {
    
    constructor (casename, PARAMETERS, VARIABLES, DUALS, INDICATORS) {
        this.casename = casename;

        let datafieldsParam = [];
        let columnsParam = [];

        let datafieldsVar = [];
        let columnsVar = [];
        let datafieldsIndicators = [];
        let columnsIndicators = [];

        let unitsDef = DataModel.getUnitsDef(UNITDEFINITION);
        let indicatorDef = DataModel.getIndicatorDef(VARIABLES);

        let paramById = DataModel.getParamById(PARAMETERS);
        let paramNames = DataModel.getParamData(PARAMETERS);

        let varNames = DataModel.getParamData(VARIABLES);

        let dualData = DataModel.getParamData(DUALS);
        let indicatorData = DataModel.getParamData(INDICATORS );

        ///////////////////////////////// PARAMS
        let gridParamData = []
        $.each(PARAMORDER, function (id, group) {   
            $.each(PARAMETERS[group], function (id, obj) {
                let tmp = {};
                tmp['groupId'] = group;
                tmp['groupName'] = GROUPNAMES[group];
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['default'] = obj.default;
                tmp['enable'] = obj.enable;
                tmp['menu'] = obj.menu;
                let rule = obj.unitRule;
                let data = unitsDef;
                tmp['unit'] =jsonLogic.apply(rule, data);
                tmp['unitRule'] = obj.unitRule;
                tmp['setrelation'] = obj.setrelation;
                gridParamData.push(tmp);
            });
        });

        var cellsrendererbutton = function (row, column, value) { 
            return '<span style="padding:5px; width:100%;" data-toggle="modal" href="#osy-unitRule" class="btn btn-white btn-default updateRule" data-id='+ row+' ><i class="fa fa-pencil-square-o  fa-lg primary"></i>Update rule</span>';
        }

        let initeditor = function(row, cellvalue, editor, data) {
            editor.jqxNumberInput({ decimalDigits: 5, spinButtons: true, allowNull: false   }); //symbol: ' GWh', symbolPosition: 'right'
        }

        datafieldsParam.push({ name: 'groupId', type:'string' });
        datafieldsParam.push({ name: 'groupName', type:'string' });        
        datafieldsParam.push({ name: 'id', type:'string' }); 
        datafieldsParam.push({ name: 'value', type:'string' }); 
        datafieldsParam.push({ name: 'name', type:'string' }); 
        datafieldsParam.push({ name: 'default', type:'number' }); 
        datafieldsParam.push({ name: 'menu', type:'number' }); 
        datafieldsParam.push({ name: 'enable', type:'bool' }); 
        datafieldsParam.push({ name: 'setrelation', type:'array' }); 
        datafieldsParam.push({ name: 'unit', type:'string' });    
        datafieldsParam.push({ name: 'unitRule' });   

        columnsParam.push({ text: 'groupId', datafield: 'groupId', editable: false, align: 'left',  hidden: true})
        columnsParam.push({ text: 'PARAMETER GROUP', datafield: 'groupName', editable: false, align: 'left', width: '20%', menu: false})
        columnsParam.push({ text: 'id', datafield: 'id', editable: false, align: 'left',  hidden: true, menu: false, sortable:false})
        columnsParam.push({ text: 'PARAMETER NAME', datafield: 'value', editable: false, align: 'left', width: '40%'})
        columnsParam.push({ text: 'NAME', datafield: 'name', editable: false, align: 'left',  hidden: true, menu: false, sortable:false}),
        columnsParam.push({ text: 'DEFAULT VALUE', datafield: 'default', align: 'right', cellsalign: 'right', width: '15%', columntype: 'numberinput', sortable:false, initeditor:initeditor, cellsformat: 'd5', menu: false})
        columnsParam.push({ text: 'ACTIVE', datafield: 'enable', columntype: 'checkbox', align: 'center',  hidden: true, menu: false, sortable:false}),
        columnsParam.push({ text: 'menu', datafield: 'menu', editable: false, align: 'left',  hidden: true, menu: false, sortable:false}),
        columnsParam.push({ text: 'setrelation', datafield: 'setrelation', editable: false, align: 'left',  hidden: true, menu: false, sortable:false}),
        columnsParam.push({ text: 'UNIT', datafield: 'unit', editable: false, align: 'center', cellsalign: 'center', width: '15%', menu: false, sortable:false}),
        columnsParam.push({ text: 'UNIT RULE', datafield: 'Unit rule',  align: 'center', width: '10%',  cellsrenderer: cellsrendererbutton, editable:false, sortable:false, menu: false  })

        let srcParamGrid = {
            datatype: "json",
            localdata: gridParamData,
            datafields: datafieldsParam
        };

        ///////////////////////////////////////// VARIABLES
        let gridVarData = []
        $.each(RESULTGROUPNAMES, function (group, name) {   
            $.each(VARIABLES[group], function (id, obj) {
                let tmp = {};
                tmp['groupId'] = group;
                tmp['groupName'] = name;
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['setrelation'] = obj.setrelation;
                let rule = obj.unitRule;
                let data = unitsDef;
                tmp['unit'] =jsonLogic.apply(rule, data);
                tmp['unitRule'] = obj.unitRule;
                gridVarData.push(tmp);
            });
        });

        datafieldsVar.push({ name: 'groupId', type:'string' });
        datafieldsVar.push({ name: 'groupName', type:'string' });        
        datafieldsVar.push({ name: 'id', type:'string' }); 
        datafieldsVar.push({ name: 'value', type:'string' }); 
        datafieldsVar.push({ name: 'name', type:'string' }); 
        datafieldsVar.push({ name: 'setrelation', type:'array' }); 
        datafieldsVar.push({ name: 'unit', type:'string' });    
        datafieldsVar.push({ name: 'unitRule' });   

        columnsVar.push({ text: 'groupId', datafield: 'groupId', editable: false, align: 'left',  hidden: true, sortable:false})
        columnsVar.push({ text: 'VARIABLE GROUP', datafield: 'groupName', editable: false, align: 'left', width: '25%', menu: false})
        columnsVar.push({ text: 'id', datafield: 'id', editable: false, align: 'left',  hidden: true, sortable:false})
        columnsVar.push({ text: 'NAME', datafield: 'value', editable: false, align: 'left', width: '50%'});
        columnsVar.push({ text: 'name', datafield: 'name', editable: false, align: 'left',  hidden: true, menu: false, sortable:false})
        columnsVar.push({ text: 'setrelation', datafield: 'setrelation', editable: false, align: 'left',  hidden: true, menu: false, sortable:false}),
        columnsVar.push({ text: 'UNIT', datafield: 'unit', editable: false, align: 'center', cellsalign: 'center', width: '15%', menu: false, sortable:false}),
        columnsVar.push({ text: 'UNIT RULE', datafield: 'Unit rule',  align: 'center', width: '10%',  cellsrenderer: cellsrendererbutton, editable:false, sortable:false, menu: false  })

        let srcVarGrid = {
            datatype: "json",
            localdata: gridVarData,
            datafields: datafieldsVar
        };

        ///////////////////////////////////////////////// DUALS 
        let gridDualData = []
        $.each(DUALS, function (group, array) {
            $.each(array, function (id, obj) {
                let tmp = {};
                tmp['groupId'] = group;
                tmp['groupName'] = RESULTGROUPNAMES[group];;
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['setrelation'] = obj.setrelation;
                let rule = obj.unitRule;
                let data = unitsDef;
                tmp['unit'] =jsonLogic.apply(rule, data);
                tmp['unitRule'] = obj.unitRule;
                gridDualData.push(tmp);
            });
        });

        let srcDualGrid = {
            datatype: "json",
            localdata: gridDualData,
            datafields: datafieldsVar
        };

        ////////////////////////////////////////////////////////////////////// INDICATORS
            let indicatorRuleData = Object.fromEntries(Object.entries(indicatorDef).map(([k,v])=>[k,v.name]));

            let gridIndicatorData = []
            $.each(INDICATORS, function (group, array) {
            $.each(array, function (id, obj) {
                let tmp = {};
                tmp['groupId'] = group;
                tmp['groupName'] = RESULTGROUPNAMES[group];;
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['setrelation'] = obj.setrelation;
                let indicatorRule = obj.formulaRule;
                
                tmp['formula'] =jsonLogic.apply(indicatorRule, indicatorRuleData);
                tmp['formulaRule'] = indicatorRule;
                let rule = obj.unitRule;
                let data = unitsDef;
                tmp['unit'] =jsonLogic.apply(rule, data);
                tmp['unitRule'] = obj.unitRule;
                gridIndicatorData.push(tmp);
            });
        });

        var cellsrendererbuttonIndicator = function (row, column, value) {
            return '<span style="padding:5px; width:100%;" data-toggle="modal" href="#osy-indicatorFormulaModal" class="btn btn-white btn-default updateIndicatorFormula" data-id='+ row+' ><i class="fa fa-pencil-square-o fa-lg success"></i>Update rule</span>';
        }

        datafieldsIndicators.push({ name: 'groupId', type:'string' });
        datafieldsIndicators.push({ name: 'groupName', type:'string' });        
        datafieldsIndicators.push({ name: 'id', type:'string' }); 
        datafieldsIndicators.push({ name: 'value', type:'string' }); 
        datafieldsIndicators.push({ name: 'name', type:'string' }); 
        datafieldsIndicators.push({ name: 'setrelation', type:'array' }); 
        datafieldsIndicators.push({ name: 'formula', type:'string' });    
        datafieldsIndicators.push({ name: 'formulaRule' });   
        datafieldsIndicators.push({ name: 'unit', type:'string' });    
        datafieldsIndicators.push({ name: 'unitRule' });   

        columnsIndicators.push({ text: 'groupId', datafield: 'groupId', editable: false, align: 'left',  hidden: true, sortable:false})
        columnsIndicators.push({ text: 'INDICATOR GROUP', datafield: 'groupName', editable: false, align: 'left', width: '15%', menu: false})
        columnsIndicators.push({ text: 'id', datafield: 'id', editable: false, align: 'left',  hidden: true, sortable:false})
        columnsIndicators.push({ text: 'INDICATOR NAME', datafield: 'value', editable: false, align: 'left', width: '20%'});
        columnsIndicators.push({ text: 'name', datafield: 'name', editable: false, align: 'left',  hidden: true, menu: false, sortable:false})
        columnsIndicators.push({ text: 'setrelation', datafield: 'setrelation', editable: false, align: 'left',  hidden: true, menu: false, sortable:false}),
        columnsIndicators.push({ text: 'FORMULA', datafield: 'formula', editable: false, align: 'center', cellsalign: 'center', width: '30%', menu: false, sortable:false,  hidden: false}),
        columnsIndicators.push({ text: 'FORMULA RULE', datafield: 'formulaRule',  align: 'center', width: '10%',  cellsrenderer: cellsrendererbuttonIndicator, editable:false, sortable:false, menu: false,  hidden: true  })
        columnsIndicators.push({ text: 'UNIT', datafield: 'unit', editable: false, align: 'center', cellsalign: 'center', width: '15%', menu: false, sortable:false}),
        columnsIndicators.push({ text: 'UNIT RULE', datafield: 'Unit rule',  align: 'center', width: '10%',  cellsrenderer: cellsrendererbutton, editable:false, sortable:false, menu: false  })

        let srcIndicatorGrid = {    
            datatype: "json",
            localdata: gridIndicatorData,
            datafields: datafieldsIndicators
        };
        /////////////////////////////////////////////////////////////////////
        this.tab = 'Params';

        this.columnsParam = columnsParam;
        this.gridParamData = gridParamData;
        this.ParamCounts = gridParamData.length;
        this.srcParamGrid = srcParamGrid;

        this.columnsVar = columnsVar;
        this.gridVarData = gridVarData;
        this.VarCounts = gridVarData.length;
        this.srcVarGrid = srcVarGrid;

        this.columnsDual = columnsVar;
        this.gridDualData = gridDualData;
        this.DualCounts = gridDualData.length;
        this.srcDualGrid = srcDualGrid;
        this.dualData = dualData;

        this.columnsIndicator = columnsIndicators;
        this.gridIndicatorData = gridIndicatorData;
        this.IndicatorCounts = gridIndicatorData.length;    
        this.srcIndicatorGrid = srcIndicatorGrid;
        this.indicatorData = indicatorData;
        this.indicatorRuleData = indicatorRuleData;
        this.indicatorDef = indicatorDef;

        this.unitsDef = unitsDef;
        this.paramById = paramById;
        this.GROUPNAMES = GROUPNAMES;
        this.RESULTGROUPNAMES = RESULTGROUPNAMES;
        this.paramNames =paramNames;
        this.varNames = varNames;
    }
}