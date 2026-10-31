import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { SyncS3 } from "../../Classes/SyncS3.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/Config.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { UNITDEFINITION } from "../../Classes/Const.Class.js";
import { Sidebar } from "./Sidebar.js";

export default class Config {
    static onLoad(){
        Base.getSession()
        .then(response =>{
            let casename = response['session'];
            const promise = [];
            promise.push(casename);
            const PARAMETERS = Osemosys.getParamFile();
            promise.push(PARAMETERS); 
            const VARIABLES = Osemosys.getParamFile('Variables.json');
            promise.push(VARIABLES);
            const DUALS = Osemosys.getParamFile('Duals.json');
            promise.push(DUALS);
            const INDICATORS = Osemosys.getParamFile('Indicators.json');
            promise.push(INDICATORS);
            return Promise.all(promise);
        })
        .then(data => {
            let [casename, PARAMETERS, VARIABLES, DUALS, INDICATORS] = data;
            let model = new Model(casename, PARAMETERS, VARIABLES, DUALS, INDICATORS);
            this.initPage(model);
            this.initEvents(model);
        })
        .catch(error =>{ 
            Message.warning(error);
        });
    }

    static initPage(model){
        Message.clearMessages();
        Html.title(model.casename, "Parameters, Variables, Duals, Indicators", "Year, technology, commodity, emission...");
        Html.renderCounters(model)
        let $divParamGrid = $('#osy-gridParam');
        let $divVarGrid = $('#osy-gridVar');
        let $divDualGrid = $('#osy-gridDual');
        let $divIndicatorGrid = $('#osy-gridIndicator');

        var daParamGrid = new $.jqx.dataAdapter(model.srcParamGrid);        
        Grid.Grid($divParamGrid, daParamGrid, model.columnsParam, {filterable: true, sortable:true, height: $(window).height() - 220})

        var daVarGrid = new $.jqx.dataAdapter(model.srcVarGrid);        
        Grid.Grid($divVarGrid, daVarGrid, model.columnsVar, {filterable: true, sortable:true, height: $(window).height() - 220});

        var daDualGrid = new $.jqx.dataAdapter(model.srcDualGrid);        
        Grid.Grid($divDualGrid, daDualGrid, model.columnsDual, {filterable: true, sortable:true, height: $(window).height() - 220})

        var daIndicatorGrid = new $.jqx.dataAdapter(model.srcIndicatorGrid);       
        Grid.Grid($divIndicatorGrid, daIndicatorGrid, model.columnsIndicator, {filterable: true, sortable:true, height: $(window).height() - 220});
    }

    static refreshPage(casename){
        Base.setSession(casename)
        .then(response =>{
            const promise = [];
            promise.push(casename);
            const PARAMETERS = Osemosys.getParamFile();
            promise.push(PARAMETERS); 
            const VARIABLES = Osemosys.getParamFile('Variables.json');
            promise.push(VARIABLES);
            const DUALS = Osemosys.getParamFile('Duals.json');
            promise.push(DUALS);
            const INDICATORS = Osemosys.getParamFile('Indicators.json');
            promise.push(INDICATORS);
            return Promise.all(promise);
        })
        .then(data => {
            let [casename, PARAMETERS, VARIABLES, DUALS, INDICATORS] = data;
            let model = new Model(casename, PARAMETERS, VARIABLES, DUALS, INDICATORS);
            this.initPage(model);
            this.initEvents(model);
        })
        .catch(error =>{ 
            Message.warning(error);
        });
    }

    static initEvents(model){
        let $divParamGrid = $('#osy-gridParam');
        let $divVarGrid = $('#osy-gridVar');
        let $divDualGrid = $('#osy-gridDual');
        let $divIndicatorGrid = $('#osy-gridIndicator');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function(e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            Sidebar.Reload(casename);
            Config.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#osy-saveData").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            /////////////// params
            let paramData = $('#osy-gridParam').jqxGrid('getrows');
            let ParamData = {};
            $.each(paramData, function (id, obj) {
                let tmp = {};
                if (typeof(ParamData[obj.groupId]) === 'undefined') {
                    ParamData[obj.groupId] = new Array();
                }
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['default'] = obj.default;
                tmp['enable'] = obj.enable;
                tmp['menu'] = obj.menu;
                tmp['setrelation'] = obj.setrelation;
                tmp['unitRule'] = obj.unitRule;
                ParamData[obj.groupId].push(tmp);
            });
            
            ////////////// vars
            let varData = $('#osy-gridVar').jqxGrid('getrows');
            let VarData = {};
            $.each(varData, function (id, obj) {
                let tmp = {};
                if (typeof(VarData[obj.groupId]) === 'undefined') {
                    VarData[obj.groupId] = new Array();
                }
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['setrelation'] = obj.setrelation;
                tmp['unitRule'] = obj.unitRule;
                VarData[obj.groupId].push(tmp);
            });

            //////////// duals
            let dualData = $('#osy-gridDual').jqxGrid('getrows');
            let DualData = {};
            $.each(dualData, function (id, obj) {
                let tmp = {};
                if (typeof(DualData[obj.groupId]) === 'undefined') {
                    DualData[obj.groupId] = new Array();
                }
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['setrelation'] = obj.setrelation;
                tmp['unitRule'] = obj.unitRule;
                DualData[obj.groupId].push(tmp);
            });

            ///////////// indicators
             let indicatorData = $('#osy-gridIndicator').jqxGrid('getrows');
             let IndicatorData = {};
            $.each(indicatorData, function (id, obj) {
                let tmp = {};
                if (typeof(IndicatorData[obj.groupId]) === 'undefined') {
                    IndicatorData[obj.groupId] = new Array();
                }
                tmp['id'] = obj.id;
                tmp['value'] = obj.value;
                tmp['name'] = obj.name;
                tmp['setrelation'] = obj.setrelation;
                tmp['unitRule'] = obj.unitRule;
                tmp['formulaRule'] = obj.formulaRule;
                IndicatorData[obj.groupId].push(tmp);
            });

            Osemosys.saveParamFile(ParamData, VarData, DualData, IndicatorData)
            .then(response =>{
                Message.bigBoxSuccess('Model message', response.message, 3000);
                //sync S3
                if (Base.AWS_SYNC == 1){
                    SyncS3.updateSyncParamFile();
                }
            })
            .catch(error=>{
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        //TABS CHANGE EVENT
        $(".nav-tabs li a").off('click');
        $('.nav-tabs li a').on("click", function(event, ui) { 
            var id = $(this).attr('id'); 
            model.tab = id;              
        });

        //update rule button
        // $(document).undelegate(".updateRule","click");
        // $(document).delegate(".updateRule","click",function(e){
        //     e.preventDefault();
        //     e.stopImmediatePropagation();
        //     var id = $(this).attr('data-id');
        //     var groupId = $('#osy-gridParam').jqxGrid('getcellvalue', id, 'groupId');
        //     var paramId = $('#osy-gridParam').jqxGrid('getcellvalue', id, 'id');

        //     $('#unitTitle').html(
        //         `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
        //             <i class="fa-fw fa fa-tags"></i><strong>RULE</strong>
        //             ${model.paramNames[groupId][paramId]}
        //             <small id="groupId" data-groupId="${groupId}"> [${model.GROUPNAMES[groupId]}]</small>
        //         </h6>
        //         `
        //     );
        //     $('#ruleResult').html(
        //         `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
        //             <i class="fa-fw fa fa-tags"></i><strong>Result formula for</strong>
        //             ${model.paramNames[groupId][paramId]}
        //             <small id="groupId" data-groupId="${groupId}"> [${model.GROUPNAMES[groupId]}]</small>
        //         </h6>
        //         `
        //     );

        //     let unitRule = model.gridParamData[id]['unitRule'];
        //     // let unitRule = model.paramById[groupId][paramId]['unitRule'];

        //     Html.renderUnitRules(unitRule, model.unitsDef);    

        //     let rule = $("#osy-unitRuleSort2").jqxSortable("toArray");

        //     let arrayRule ='';
        //     $.each(rule, function (id, rule) {
        //         arrayRule += UNITDEFINITION[rule]['name'];
        //     });
        //     $('#ruleFormula').html(`<p>${arrayRule}</p>`);
        //     $('#ruleFormula').show();
                   
        // });

        // $(document).undelegate(".updateVarRule","click");
        // $(document).delegate(".updateVarRule","click",function(e){
        //     e.preventDefault();
        //     e.stopImmediatePropagation();
        //     var id = $(this).attr('data-id');
        //     var groupId = $('#osy-gridVar').jqxGrid('getcellvalue', id, 'groupId');
        //     var paramId = $('#osy-gridVar').jqxGrid('getcellvalue', id, 'id');
            
        //     $('#unitTitle').html(
        //         `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
        //             <i class="fa-fw fa fa-tags"></i><strong>RULE</strong>
        //             ${model.varNames[groupId][paramId]}
        //             <small id="groupId" data-groupId="${groupId}"> [${model.RESULTGROUPNAMES[groupId]}]</small>
        //         </h6>
        //         `
        //     );
        //     $('#ruleResult').html(
        //         `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
        //             <i class="fa-fw fa fa-tags"></i><strong>Result formula for</strong>
        //             ${model.varNames[groupId][paramId]}
        //             <small id="groupId" data-groupId="${groupId}"> [${model.RESULTGROUPNAMES[groupId]}]</small>
        //         </h6>
        //         `
        //     );

        //     let unitRule = model.gridVarData[id]['unitRule'];
        //     // let unitRule = model.paramById[groupId][paramId]['unitRule'];

        //     Html.renderUnitRules(unitRule, model.unitsDef);    

        //     let rule = $("#osy-unitRuleSort2").jqxSortable("toArray");

        //     let arrayRule ='';
        //     $.each(rule, function (id, rule) {
        //         arrayRule += UNITDEFINITION[rule]['name'];
        //     });
        //     $('#ruleFormula').html(`<p>${arrayRule}</p>`);
        //     $('#ruleFormula').show();
                   
        // });

        /////////////////////////////////////////////////VARS PARAMS DUALS IND ///////////// UNIT RULES
        $(document).undelegate(".updateRule","click");
        $(document).delegate(".updateRule","click",function(e){
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            
            var groupId, paramId, name, groupname, unitRule;
            if(model.tab == 'Params'){
                groupId = $('#osy-gridParam').jqxGrid('getcellvalue', id, 'groupId');
                paramId = $('#osy-gridParam').jqxGrid('getcellvalue', id, 'id');
                name = model.paramNames[groupId][paramId].value;
                groupname = model.GROUPNAMES[groupId];
                unitRule = model.gridParamData[id]['unitRule'];
            }
            else if(model.tab == 'Vars'){
                groupId = $('#osy-gridVar').jqxGrid('getcellvalue', id, 'groupId');
                paramId = $('#osy-gridVar').jqxGrid('getcellvalue', id, 'id');
                name = model.varNames[groupId][paramId].value;
                groupname = model.RESULTGROUPNAMES[groupId];    
                unitRule = model.gridVarData[id]['unitRule'];
            }
            else if(model.tab == 'Indicators'){
                groupId = $('#osy-gridIndicator').jqxGrid('getcellvalue', id, 'groupId');
                paramId = $('#osy-gridIndicator').jqxGrid('getcellvalue', id, 'id');
                name = model.indicatorData[groupId][paramId].value;
                groupname = model.RESULTGROUPNAMES[groupId];    
                unitRule = model.gridIndicatorData[id]['unitRule'];
            }
            else if(model.tab == 'Duals'){
                groupId = $('#osy-gridDual').jqxGrid('getcellvalue', id, 'groupId');
                paramId = $('#osy-gridDual').jqxGrid('getcellvalue', id, 'id');
                name = model.dualData[groupId][paramId].value;
                groupname = model.RESULTGROUPNAMES[groupId];    
                unitRule = model.gridDualData[id]['unitRule'];
            }

            $('#unitTitle').html(
                `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
                    <i class="fa-fw fa fa-tags"></i><strong>RULE</strong>
                    ${name}
                    <small id="groupId" data-groupId="${groupId}"> [${groupname}]</small>
                </h6>
                `
            );
            $('#ruleResult').html(
                `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
                    <i class="fa-fw fa fa-tags"></i><strong>Result formula for</strong>
                    ${name}
                    <small id="groupId" data-groupId="${groupId}"> [${groupname}]</small>
                </h6>
                `
            );
            Html.renderUnitRules(unitRule, model.unitsDef);    
            let rule = $("#osy-unitRuleSort2").jqxSortable("toArray");

            let arrayRule ='';
            $.each(rule, function (id, rule) {
                arrayRule += UNITDEFINITION[rule]['name'];
            });
            $('#ruleFormula').html(`<p>${arrayRule}</p>`);
            $('#ruleFormula').show();
                   
        });

        //modal save rule
        $("#btnSaveRule").off('click');
        $("#btnSaveRule").on('click', function (event) {
            let rule = $("#osy-unitRuleSort2").jqxSortable("toArray")

            let paramId = $('#paramId').attr("data-paramId");
            let groupId = $('#groupId').attr("data-groupId") 

            let arrayRule = [];
            $.each(rule, function (id, rule) {
                arrayRule.push(UNITDEFINITION[rule]['val'])
            });

            let unitRule = {
                "cat": arrayRule
            };

            if(model.tab == 'Params'){
                $.each(model.gridParamData, function (id, obj) {
                    if (obj.id == paramId && obj.groupId == groupId){
                        obj.unit =jsonLogic.apply(unitRule, model.unitsDef);
                        obj.unitRule = unitRule;
                    }
                });
                model.srcParamGrid.localdata = model.gridParamData;
                $divParamGrid.jqxGrid('updatebounddata');
                Message.smallBoxInfo('Rule updated for ', model.paramNames[groupId][paramId], 3000);
            }
            else if(model.tab == 'Vars'){
                $.each(model.gridVarData, function (id, obj) {
                    if (obj.id == paramId && obj.groupId == groupId){
                        obj.unit =jsonLogic.apply(unitRule, model.unitsDef);
                        obj.unitRule = unitRule;
                    }
                });
                model.srcVarGrid.localdata = model.gridVarData;
                $divVarGrid.jqxGrid('updatebounddata');
                Message.smallBoxInfo('Rule updated for ', model.varNames[groupId][paramId], 3000);
            }
            else if(model.tab == 'Indicators'){
                $.each(model.gridIndicatorData, function (id, obj) {
                    if (obj.id == paramId && obj.groupId == groupId){
                        obj.unit =jsonLogic.apply(unitRule, model.unitsDef);
                        obj.unitRule = unitRule;
                    }
                });
                model.srcIndicatorGrid.localdata = model.gridIndicatorData;
                $divIndicatorGrid.jqxGrid('updatebounddata');
                Message.smallBoxInfo('Rule updated for ', model.indicatorData[groupId][paramId], 3000);
            }

            $('#osy-unitRule').modal('toggle');
             
        });

        $('#osy-unitRuleSort2').on('stop', function () { 
            let rule = $("#osy-unitRuleSort2").jqxSortable("toArray");

            let arrayRule ='';
            $.each(rule, function (id, rule) {
                arrayRule += UNITDEFINITION[rule]['name'];
            });
            $('#ruleFormula').html(`<p>${arrayRule}</p>`);
            $('#ruleFormula').show();
         }); 

        $('#osy-unitRuleSort2').on('receive', function () { 
            let rule = $("#osy-unitRuleSort2").jqxSortable("toArray");

            let arrayRule ='';
            $.each(rule, function (id, rule) {
                arrayRule += UNITDEFINITION[rule]['name'];
            });
            $('#ruleFormula').html(`<p>${arrayRule}</p>`);
            $('#ruleFormula').show();
         }); 

         $('#osy-unitRuleSort2').on('remove', function () { 
         
        })

        ///////////////////////////////////////////////// INDICATORS ///////////// FORMULA RULES
        $(document).undelegate(".updateIndicatorFormula","click");
        $(document).delegate(".updateIndicatorFormula","click",function(e){
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            
            var groupId, paramId, name, groupname, formulaRule;
            groupId = $('#osy-gridIndicator').jqxGrid('getcellvalue', id, 'groupId');
            paramId = $('#osy-gridIndicator').jqxGrid('getcellvalue', id, 'id');
            name = model.indicatorData[groupId][paramId].value;
            groupname = model.RESULTGROUPNAMES[groupId];    
            formulaRule = model.gridIndicatorData[id]['formulaRule'];

            $('#indTitle').html(
                `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
                    <i class="fa-fw fa fa-tags"></i><strong>RULE</strong>
                    ${name}
                    <small id="groupId" data-groupId="${groupId}"> [${groupname}]</small>
                </h6>
                `
            );
            $('#indResult').html(
                `<h6 id="paramId" data-paramId ="${paramId}" style="display: inline-block;">
                    <i class="fa-fw fa fa-tags"></i><strong>Result formula for</strong>
                    ${name}
                    <small id="groupId" data-groupId="${groupId}"> [${groupname}]</small>
                </h6>
                `
            );
            Html.renderIndicatorFormula(formulaRule, model.indicatorRuleData, model.indicatorDef);    
            let rule = $("#osy-indFormulaSort2").jqxSortable("toArray");

            let arrayRule = name +' = ';
            $.each(rule, function (id, r) {
                arrayRule +=  model.indicatorDef[r]['name'];
            });
            $('#formulaView').html(`<p>${arrayRule}</p>`);
            $('#formulaView').show();
                   
        });

        //modal save rule
        $("#btnSaveFormula").off('click');
        $("#btnSaveFormula").on('click', function (event) {
            let rule = $("#osy-indFormulaSort2").jqxSortable("toArray")

            let paramId = $('#paramId').attr("data-paramId");
            let groupId = $('#groupId').attr("data-groupId") 

            let arrayRule = [];
            $.each(rule, function (id, rule) {
                arrayRule.push( model.indicatorDef[rule].ruleVal);
            });

            let formulaRule = {
                "cat": arrayRule
            };

            $.each(model.gridIndicatorData, function (id, obj) {
                if (obj.id == paramId && obj.groupId == groupId){
                    obj.formula =jsonLogic.apply(formulaRule,  model.indicatorRuleData);
                    obj.formulaRule = formulaRule;
                }
            });
            model.srcIndicatorGrid.localdata = model.gridIndicatorData;
            $divIndicatorGrid.jqxGrid('updatebounddata');
            Message.smallBoxInfo('Rule updated for ', model.indicatorData[groupId][paramId].value, 3000);

            $('#osy-indicatorFormulaModal').modal('toggle');
             
        });

        $('#osy-indFormulaSort2').on('stop', function () { 
                let rule = $("#osy-indFormulaSort2").jqxSortable("toArray");

                let arrayRule ='';
                $.each(rule, function (id, rule) {
                    arrayRule += model.indicatorDef[rule]['name'];
                });
                $('#formulaView').html(`<p>${arrayRule}</p>`);
                $('#formulaView').show();
        }); 

        $('#osy-indFormulaSort2').on('receive', function () { 
                let rule = $("#osy-indFormulaSort2").jqxSortable("toArray");

                let arrayRule ='';
                $.each(rule, function (id, rule) {
                    arrayRule += model.indicatorDef[rule]['name'];
                });
                $('#formulaView').html(`<p>${arrayRule}</p>`);
                $('#formulaView').show();
        }); 

        $('#osy-indFormulaSort2').on('remove', function () { 
        
        })
        
    }
}