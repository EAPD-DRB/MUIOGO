import { DataModel } from "../../Classes/DataModel.Class.js";
import { DataModelResult} from "../../Classes/DataModelResult.Class.js"
import { GROUPNAMES, PARAMORDER, UNITDEFINITION, RESULTGROUPNAMES } from "../../Classes/Const.Class.js";

export class Model {
    
    constructor (PARAMETERS, VARIABLES) {

        let datafieldsParam = [];
        let columnsParam = [];

        let datafieldsVar = [];
        let columnsVar = [];


        let unitsDef = DataModel.getUnitsDef(UNITDEFINITION);
        let paramById = DataModel.getParamById(PARAMETERS);
        let paramNames = DataModel.AllParamName(PARAMETERS);

        let varById = DataModelResult.getVarById(VARIABLES);
        let varNames = DataModelResult.AllVarName(VARIABLES);

        let gridParamData = []
        $.each(PARAMORDER, function (id, group) {   
            $.each(PARAMETERS[group], function (id, obj) {
                let tmp = {};
                tmp['groupId'] = group;
                tmp['groupName'] = GROUPNAMES[group];
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['default'] = obj.default;
                tmp['enable'] = obj.enable;
                tmp['menu'] = obj.menu;
                let rule = obj.unitRule;
                let data = unitsDef;
                tmp['unit'] =jsonLogic.apply(rule, data);
                tmp['unitRule'] = obj.unitRule;
                gridParamData.push(tmp);
            });
        });


        // console.log('gridParamData ', gridParamData)
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
        datafieldsParam.push({ name: 'default', type:'number' }); 
        datafieldsParam.push({ name: 'menu', type:'number' }); 
        datafieldsParam.push({ name: 'enable', type:'bool' }); 
        datafieldsParam.push({ name: 'unit', type:'string' });    
        datafieldsParam.push({ name: 'unitRule' });   

        columnsParam.push({ text: 'groupId', datafield: 'groupId', editable: false, align: 'left',  hidden: true})
        columnsParam.push({ text: 'PARAMETER GROUP', datafield: 'groupName', editable: false, align: 'left', width: '20%', menu: false})
        columnsParam.push({ text: 'id', datafield: 'id', editable: false, align: 'left',  hidden: true, menu: false, sortable:false})
        columnsParam.push({ text: 'PARAMETER NAME', datafield: 'value', editable: false, align: 'left', width: '40%'})
        columnsParam.push({ text: 'DEFAULT VALUE', datafield: 'default', align: 'right', cellsalign: 'right', width: '15%', columntype: 'numberinput', sortable:false, initeditor:initeditor, cellsformat: 'd5', menu: false})
        columnsParam.push({ text: 'ACTIVE', datafield: 'enable', columntype: 'checkbox', align: 'center',  hidden: true, menu: false, sortable:false}),
        columnsParam.push({ text: 'menu', datafield: 'menu', editable: false, align: 'left',  hidden: true, menu: false, sortable:false}),
        columnsParam.push({ text: 'UNIT', datafield: 'unit', editable: false, align: 'center', cellsalign: 'center', width: '15%', menu: false, sortable:false}),
        columnsParam.push({ text: 'UNIT RULE', datafield: 'Unit rule',  align: 'center', width: '10%',  cellsrenderer: cellsrendererbutton, editable:false, sortable:false, menu: false  })

        let srcParamGrid = {
            datatype: "json",
            localdata: gridParamData,
            datafields: datafieldsParam
        };

        //var Grid
        let gridVarData = []
        $.each(RESULTGROUPNAMES, function (group, name) {   
            $.each(VARIABLES[group], function (id, obj) {
                let tmp = {};
                tmp['groupId'] = group;
                tmp['groupName'] = name;
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                let rule = obj.unitRule;
                let data = unitsDef;
                tmp['unit'] =jsonLogic.apply(rule, data);
                tmp['unitRule'] = obj.unitRule;
                gridVarData.push(tmp);
            });
        });

        var cellsrendererbuttonVar = function (row, column, value) { 
            return '<span style="padding:5px; width:100%;" data-toggle="modal" href="#osy-unitRule" class="btn btn-white btn-default updateVarRule" data-id='+ row+' ><i class="fa fa-pencil-square-o fa-lg success"></i>Update rule</span>';
        }

        datafieldsVar.push({ name: 'groupId', type:'string' });
        datafieldsVar.push({ name: 'groupName', type:'string' });        
        datafieldsVar.push({ name: 'id', type:'string' }); 
        datafieldsVar.push({ name: 'value', type:'string' }); 
        datafieldsVar.push({ name: 'name', type:'string' }); 
        datafieldsVar.push({ name: 'unit', type:'string' });    
        datafieldsVar.push({ name: 'unitRule' });   

        columnsVar.push({ text: 'groupId', datafield: 'groupId', editable: false, align: 'left',  hidden: true, sortable:false})
        columnsVar.push({ text: 'VARIABLE GROUP', datafield: 'groupName', editable: false, align: 'left', width: '25%', menu: false})
        columnsVar.push({ text: 'id', datafield: 'id', editable: false, align: 'left',  hidden: true, sortable:false})
        columnsVar.push({ text: 'VARIABLE NAME', datafield: 'value', editable: false, align: 'left', width: '50%'});
        columnsVar.push({ text: 'name', datafield: 'name', editable: false, align: 'left',  hidden: true, menu: false, sortable:false})
        columnsVar.push({ text: 'UNIT', datafield: 'unit', editable: false, align: 'center', cellsalign: 'center', width: '15%', menu: false, sortable:false}),
        columnsVar.push({ text: 'UNIT RULE', datafield: 'Unit rule',  align: 'center', width: '10%',  cellsrenderer: cellsrendererbuttonVar, editable:false, sortable:false, menu: false  })

        let srcVarGrid = {
            datatype: "json",
            localdata: gridVarData,
            datafields: datafieldsVar
        };


        

        this.tab = 'Params';
        this.columnsParam = columnsParam;
        this.gridParamData = gridParamData;
        this.srcParamGrid = srcParamGrid;

        this.columnsVar = columnsVar;
        this.gridVarData = gridVarData;
        this.srcVarGrid = srcVarGrid;

        this.unitsDef = unitsDef;
        this.paramById = paramById;
        this.GROUPNAMES = GROUPNAMES;
        this.RESULTGROUPNAMES = RESULTGROUPNAMES;
        this.paramNames =paramNames;
        this.varNames = varNames;
        //this.unitIdByVal = unitIdByVal;
    }
}
