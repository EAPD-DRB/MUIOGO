
import { DataModel} from "./DataModel.Class.js"
import { UNITDEFINITION, VAR_TECH_GROUPS, VAR_COMM_GROUPS, VAR_EMIS_GROUPS, VAR_STORAGE_GROUPS } from "./Const.Class.js";

export class DataModelResult{

    static getVarById(VARIABLES){
        let varById = {};
        const cloneData = JSON.parse(JSON.stringify(VARIABLES));
        $.each(cloneData, function (group, array) {
            $.each(array, function (id, obj) {
                //if(!varById[obj.value]){ varById[obj.value] = {}; }
                obj.group = group;
                varById[obj.id] = obj;
            });
        });
        return varById;       
    }

    static AllVarName(VARIABLES){
        let VarName = {};
        $.each(VARIABLES, function (group, array) {
            VarName[group] = {};
            $.each(array, function (id, obj) {
                VarName[group][obj.id] = obj.value;
            });
        });
        return VarName;
    }

    static getVarialblesObject(VARIABLES){
        let vars = [];
        $.each(VARIABLES, function (group, array) {
            if (group != 'RT'){
                $.each(array, function (id, obj) {
                    //VarName[group][obj.id] = obj.value;
                    let tmp = {};
                    tmp.value = obj.id;
                    tmp.name = obj.value;
    
                    vars.push(tmp)
                });
            }  
        });
        return vars;
    }

    static getViews(VIEWS){
        $.each(VIEWS, function (group, array) {
            let tmp = {};
            tmp['osy-viewId'] = 'null';
            tmp['osy-viewname'] = 'Default view';
            array.unshift(tmp)
        });
        return VIEWS;
    }

    static getAllViews(VIEWS){
        let views = [];
        let tmp = {};
        tmp['osy-viewId'] = 'null';
        tmp['osy-viewname'] = 'Default view';
        views.push(tmp)
        $.each(VIEWS, function (variable, array) {
            $.each(array, function (id, obj) {
                if(obj['osy-viewId'] != "null"){
                    obj['osy-varId'] = variable;
                    views.push(obj);
                }
            });
        });
        return views;
    }

    static getTechData(genData){
        let techData = {};
        $.each(genData['osy-tech'], function (id, obj) {
            techData[obj.Tech] = obj;
        });
        return techData;
    }

    static getTechGroupData(genData){
        let techGroupData = {};
        $.each(genData['osy-techGroups'], function (id, obj) {
            techGroupData[obj.TechGroupId] = obj;
        });
        return techGroupData;
    }

    static getEmiData(genData){
        let emiData = {};
        $.each(genData['osy-emis'], function (id, obj) {
            emiData[obj.Emis] = obj;
        });
        return emiData;
    }

    static getCommData(genData){
        let commData = {};
        $.each(genData['osy-comm'], function (id, obj) {
            commData[obj.Comm] = obj;
        });
        return commData;
    }

    static getConData(genData){
        let conData = {};
        $.each(genData['osy-constraints'], function (id, obj) {
            conData[obj.Con] = obj;
        });
        return conData;
    }

    static getStgData(genData){
        let stgData = {};
        $.each(genData['osy-stg'], function (id, obj) {
            stgData[obj.Stg] = obj;
        });
        return stgData;
    }

    static getUnitDataOLD(genData, parameters){
        let unitData = {};
        let techUnits = DataModel.getTechUnits(genData);
        let commUnits = DataModel.getCommUnits(genData);
        let emiUnits = DataModel.getEmiUnits(genData);
        let stgUnits = DataModel.getStgUnits(genData);

        $.each(parameters, function (group, array) {
            unitData[group] = {};
            $.each(array, function (id, obj) {
                unitData[group][obj.id] = {};

                //tech comm parameters
                if(VAR_TECH_COM_GROUPS.includes(group)){
                    $.each(genData['osy-tech'], function (id, tObj) {
                        unitData[group][obj.id][tObj.Tech] = {};
                        unitData[group][obj.id][tObj.Tech]['years'] = 'years';
                        unitData[group][obj.id][tObj.Tech]['percent'] = '%';
                        unitData[group][obj.id][tObj.Tech]['divide'] = '/';
                        unitData[group][obj.id][tObj.Tech]['multiply'] = '*';
                        unitData[group][obj.id][tObj.Tech]['hundert'] = '100';
                        unitData[group][obj.id][tObj.Tech]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][tObj.Tech]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][tObj.Tech]['CapUnitId'] = techUnits[tObj.TechId]['CapUnitId'];
                        unitData[group][obj.id][tObj.Tech]['ActUnitId'] = techUnits[tObj.TechId]['ActUnitId'];
                        unitData[group][obj.id][tObj.Tech]['Currency'] = genData['osy-currency'];
                    });
                }


                //tech parameters
                if(VAR_TECH_GROUPS.includes(group)){
                    $.each(genData['osy-tech'], function (id, tObj) {
                        unitData[group][obj.id][tObj.Tech] = {};
                        unitData[group][obj.id][tObj.Tech]['years'] = 'years';
                        unitData[group][obj.id][tObj.Tech]['percent'] = '%';
                        unitData[group][obj.id][tObj.Tech]['divide'] = '/';
                        unitData[group][obj.id][tObj.Tech]['multiply'] = '*';
                        unitData[group][obj.id][tObj.Tech]['hundert'] = '100';
                        unitData[group][obj.id][tObj.Tech]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][tObj.Tech]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][tObj.Tech]['CapUnitId'] = techUnits[tObj.TechId]['CapUnitId'];
                        unitData[group][obj.id][tObj.Tech]['ActUnitId'] = techUnits[tObj.TechId]['ActUnitId'];
                        unitData[group][obj.id][tObj.Tech]['Currency'] = genData['osy-currency'];
                    });
                }
                //comm parameters
                if(VAR_COMM_GROUPS.includes(group)){
                    $.each(genData['osy-comm'], function (id, cObj) {
                        unitData[group][obj.id][cObj.Comm] = {};
                        unitData[group][obj.id][cObj.Comm]['years'] = 'years';
                        unitData[group][obj.id][cObj.Comm]['percent'] = '%';
                        unitData[group][obj.id][cObj.Comm]['divide'] = '/';
                        unitData[group][obj.id][cObj.Comm]['multiply'] = '*';
                        unitData[group][obj.id][cObj.Comm]['hundert'] = '100';
                        unitData[group][obj.id][cObj.Comm]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][cObj.Comm]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][cObj.Comm]['CommUnit'] = commUnits[cObj.CommId];
                        unitData[group][obj.id][cObj.Comm]['Currency'] = genData['osy-currency'];
                    });
                }
                //emi parameters
                if(VAR_EMIS_GROUPS.includes(group)){
                    $.each(genData['osy-emis'], function (id, eObj) {
                        unitData[group][obj.id][eObj.Emis] = {};
                        unitData[group][obj.id][eObj.Emis]['years'] = 'years';
                        unitData[group][obj.id][eObj.Emis]['percent'] = '%';
                        unitData[group][obj.id][eObj.Emis]['divide'] = '/';
                        unitData[group][obj.id][eObj.Emis]['multiply'] = '*';
                        unitData[group][obj.id][eObj.Emis]['hundert'] = '100';
                        unitData[group][obj.id][eObj.Emis]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][eObj.Emis]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][eObj.Emis]['EmiUnit'] = emiUnits[eObj.EmisId];
                        unitData[group][obj.id][eObj.Emis]['Currency'] = genData['osy-currency'];
                    });
                }
                if(VAR_STORAGE_GROUPS.includes(group)){
                    $.each(genData['osy-stg'], function (id, eObj) {
                        unitData[group][obj.id][eObj.Stg] = {};
                        unitData[group][obj.id][eObj.Stg]['years'] = 'years';
                        unitData[group][obj.id][eObj.Stg]['percent'] = '%';
                        unitData[group][obj.id][eObj.Stg]['divide'] = '/';
                        unitData[group][obj.id][eObj.Stg]['multiply'] = '*';
                        unitData[group][obj.id][eObj.Stg]['hundert'] = '100';
                        unitData[group][obj.id][eObj.Stg]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][eObj.Stg]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][eObj.Stg]['StgUnit'] = stgUnits[eObj.StgId];
                        unitData[group][obj.id][eObj.Stg]['Currency'] = genData['osy-currency'];
                    });
                }
                unitData[group][obj.id]['years'] = 'years';
                unitData[group][obj.id]['number'] = 'number';
                unitData[group][obj.id]['percent'] = '%';
                unitData[group][obj.id]['divide'] = '/';
                unitData[group][obj.id]['multiply'] = '*';
                unitData[group][obj.id]['hundert'] = '100';
                unitData[group][obj.id]['thousand'] = '10<sup>3</sup>';
                unitData[group][obj.id]['milion'] = '10<sup>6</sup>';
                unitData[group][obj.id]['hundert'] = '100';
                unitData[group][obj.id]['thousand'] = '10<sup>3</sup>';
            });
        });
        return unitData;       
    }

    static getUnitData(genData, parameters){
        let unitData = {};
        let techUnits = DataModel.getTechUnits(genData);
        let commUnits = DataModel.getCommUnits(genData);
        let emiUnits = DataModel.getEmiUnits(genData);
        let stgUnits = DataModel.getStgUnits(genData);

        $.each(parameters, function (group, array) {
            unitData[group] = {};
            $.each(array, function (id, obj) {
                unitData[group][obj.id] = {};

                //tech comm parameters
                
                // if(VAR_TECH_COM_GROUPS.includes(group)){
                //     $.each(genData['osy-tech'], function (id, tObj) {
                //         unitData[group][obj.id][tObj.Tech] = {};
                //         unitData[group][obj.id][tObj.Tech]['years'] = 'years';
                //         unitData[group][obj.id][tObj.Tech]['percent'] = '%';
                //         unitData[group][obj.id][tObj.Tech]['divide'] = '/';
                //         unitData[group][obj.id][tObj.Tech]['multiply'] = '*';
                //         unitData[group][obj.id][tObj.Tech]['hundert'] = '100';
                //         unitData[group][obj.id][tObj.Tech]['thousand'] = '10<sup>3</sup>';
                //         unitData[group][obj.id][tObj.Tech]['milion'] = '10<sup>6</sup>';
                //         unitData[group][obj.id][tObj.Tech]['CapUnitId'] = techUnits[tObj.TechId]['CapUnitId'];
                //         unitData[group][obj.id][tObj.Tech]['ActUnitId'] = techUnits[tObj.TechId]['ActUnitId'];
                //         unitData[group][obj.id][tObj.Tech]['Currency'] = genData['osy-currency'];
                // });
                //     $.each(genData['osy-comm'], function (id, cObj) {
                //         unitData[group][obj.id][cObj.Comm] = {};
                //         unitData[group][obj.id][cObj.Comm]['years'] = 'years';
                //         unitData[group][obj.id][cObj.Comm]['percent'] = '%';
                //         unitData[group][obj.id][cObj.Comm]['divide'] = '/';
                //         unitData[group][obj.id][cObj.Comm]['multiply'] = '*';
                //         unitData[group][obj.id][cObj.Comm]['hundert'] = '100';
                //         unitData[group][obj.id][cObj.Comm]['thousand'] = '10<sup>3</sup>';
                //         unitData[group][obj.id][cObj.Comm]['milion'] = '10<sup>6</sup>';
                //         unitData[group][obj.id][cObj.Comm]['CommUnit'] = commUnits[cObj.CommId];
                //         unitData[group][obj.id][cObj.Comm]['Currency'] = genData['osy-currency'];
                //     });
                    
                // }

                //tech parameters
                if(VAR_TECH_GROUPS.includes(group)){
                    $.each(genData['osy-tech'], function (id, tObj) {
                        unitData[group][obj.id][tObj.Tech] = {};
                        unitData[group][obj.id][tObj.Tech]['years'] = 'years';
                        unitData[group][obj.id][tObj.Tech]['percent'] = '%';
                        unitData[group][obj.id][tObj.Tech]['divide'] = '/';
                        unitData[group][obj.id][tObj.Tech]['multiply'] = '*';
                        unitData[group][obj.id][tObj.Tech]['hundert'] = '100';
                        unitData[group][obj.id][tObj.Tech]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][tObj.Tech]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][tObj.Tech]['CapUnitId'] = techUnits[tObj.TechId]['CapUnitId'];
                        unitData[group][obj.id][tObj.Tech]['ActUnitId'] = techUnits[tObj.TechId]['ActUnitId'];
                        unitData[group][obj.id][tObj.Tech]['Currency'] = genData['osy-currency'];
                    });
                }
                //comm parameters
                if(VAR_COMM_GROUPS.includes(group)){
                    $.each(genData['osy-comm'], function (id, cObj) {
                        unitData[group][obj.id][cObj.Comm] = {};
                        unitData[group][obj.id][cObj.Comm]['years'] = 'years';
                        unitData[group][obj.id][cObj.Comm]['percent'] = '%';
                        unitData[group][obj.id][cObj.Comm]['divide'] = '/';
                        unitData[group][obj.id][cObj.Comm]['multiply'] = '*';
                        unitData[group][obj.id][cObj.Comm]['hundert'] = '100';
                        unitData[group][obj.id][cObj.Comm]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][cObj.Comm]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][cObj.Comm]['CommUnit'] = commUnits[cObj.CommId];
                        unitData[group][obj.id][cObj.Comm]['Currency'] = genData['osy-currency'];
                    });
                }
                //emi parameters
                if(VAR_EMIS_GROUPS.includes(group)){
                    $.each(genData['osy-emis'], function (id, eObj) {
                        unitData[group][obj.id][eObj.Emis] = {};
                        unitData[group][obj.id][eObj.Emis]['years'] = 'years';
                        unitData[group][obj.id][eObj.Emis]['percent'] = '%';
                        unitData[group][obj.id][eObj.Emis]['divide'] = '/';
                        unitData[group][obj.id][eObj.Emis]['multiply'] = '*';
                        unitData[group][obj.id][eObj.Emis]['hundert'] = '100';
                        unitData[group][obj.id][eObj.Emis]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][eObj.Emis]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][eObj.Emis]['EmiUnit'] = emiUnits[eObj.EmisId];
                        unitData[group][obj.id][eObj.Emis]['Currency'] = genData['osy-currency'];
                    });
                }
                if(VAR_STORAGE_GROUPS.includes(group)){
                    $.each(genData['osy-stg'], function (id, eObj) {
                        unitData[group][obj.id][eObj.Stg] = {};
                        unitData[group][obj.id][eObj.Stg]['years'] = 'years';
                        unitData[group][obj.id][eObj.Stg]['percent'] = '%';
                        unitData[group][obj.id][eObj.Stg]['divide'] = '/';
                        unitData[group][obj.id][eObj.Stg]['multiply'] = '*';
                        unitData[group][obj.id][eObj.Stg]['hundert'] = '100';
                        unitData[group][obj.id][eObj.Stg]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][eObj.Stg]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][eObj.Stg]['StgUnit'] = stgUnits[eObj.StgId];
                        unitData[group][obj.id][eObj.Stg]['Currency'] = genData['osy-currency'];
                    });
                }
            });
        });
        return unitData;       
    }

    //////////////////////////////////////////////////////// P I V O T///////////////////////////////////////////////////////////////////////////////////

        static getPivot(DATA, genData, VARIABLES, group, param){

        let unitData = this.getUnitData(genData, VARIABLES);
        let paramById = DataModel.getParamById(VARIABLES);
        let techData = this.getTechData(genData);
        let commData = this.getCommData(genData);
        let conData = this.getConData(genData);
        let emiData = this.getEmiData(genData);
        let stgData = this.getStgData(genData);
        let techGroupData = this.getTechGroupData(genData);
        let techGroupNames = DataModel.TechGroupName(genData);
        let years = genData['osy-years']

        let pivotData = [];
        let dataT = {};
        let dataC = {};
        let dataE = {};
        let dataS = {};

        $.each(DATA[param], function (cs, array) {    
            //console.log('DATA[param] ', DATA[param], param) 
            $.each(array, function (id, obj) {

                if(obj.ObjectiveValue){
                    let chunkOv = {};
                    chunkOv['Case'] = cs;
                    chunkOv['Unit'] = 'n/a';
                    chunkOv['Optimal'] = 'Objective Value';
                    chunkOv['Value'] = obj.ObjectiveValue;
                    pivotData.push(chunkOv);
                }
                else{
                    $.each(years, function (idY, year) { 
                        let chunk = {};
                        chunk['Case'] = cs;
    
                        //provjera da li u obj ima Comm, Tech, Stg, Emi... Redosljed je bitan za one varijable koje zavise vise od jednog seta, definicja 
                        //unita ce da zavisi od toga
       
                        if(obj.MoId){
                            chunk['MoId'] = obj.MoId;
                        }
                        if(obj.Ts){
                            chunk['Ts'] = obj.Ts;
                        }
                        chunk['Year'] = year;
                        
                        if(year in obj){
                            chunk['Value'] = obj[year];
                        }
                        else{
                            chunk['Value'] = null;
                        }
                        if(obj.Comm && !obj.Tech){
                            
                            //uslov dodan vk 18072924 ako smo izbrisali commodity a postoji u resulttima
                            if(obj.Comm in commData){
                                chunk['Comm'] = obj.Comm;
                                chunk['CommDesc'] = commData[obj.Comm]["Desc"];
                               
                                dataC = unitData[group][param][obj.Comm];
                                let rule = paramById[group][param]['unitRule'];
                                //console.log('COM ', dataC, rule)
                                chunk['Unit'] = jsonLogic.apply(rule, {...dataC});
                            }
                            else{
                                chunk['Comm'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Comm;
                                chunk['CommDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Comm + " deleted from model";
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
                        if(obj.Con){
                            
                            if(obj.Con in conData){
                                chunk['Con'] = obj.Con;
                                chunk['ConDesc'] = conData[obj.Con]["Desc"];
                                chunk['Unit'] = 'n/a';
                               
                            }
                            else{
                                chunk['Con'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Con;
                                chunk['ConDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Con + " deleted from model";
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
                        if(obj.Stg){
                            
                            if(obj.Stg in stgData){
                                chunk['Stg'] = obj.Stg;
                                chunk['StgDesc'] = stgData[obj.Stg]["Desc"];
                                dataS = unitData[group][param][obj.Stg];
                                let rule = paramById[group][param]['unitRule'];
                                chunk['Unit'] = jsonLogic.apply(rule, {...dataS});
                            }
                            else{
                                chunk['Stg'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Stg;
                                chunk['StgDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Stg + " deleted from model";
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
                        if(obj.Emi){
                            
                            if(obj.Emi in emiData){
                                chunk['Emi'] = obj.Emi;
                                chunk['EmiDesc'] = emiData[obj.Emi]["Desc"];
                                dataE = unitData[group][param][obj.Emi];
                                let rule = paramById[group][param]['unitRule'];
                                chunk['Unit'] = jsonLogic.apply(rule, {...dataE});
                            }
                            else{
                                chunk['Emi'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Emi;
                                chunk['EmiDesc'] =  '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Emi+' deleted from model';
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
                        if(obj.Tech && !obj.Comm){
                            //console.log('techData ', obj.Tech, '------',  techData[obj.Tech])   //DEMINDLFO 
                            //vk 18972024 ovaj uslov dodat - 
                            // ako korisnik izbrise tech on ce ostati u view json filovima i doci ce do greske, ovaj tech se mora ignorisati u pivotdata
                            if(obj.Tech in techData){
                                let rule = paramById[group][param]['unitRule'];
                                if(techData[obj.Tech].TG.length != 0){
                                    $.each(techData[obj.Tech].TG, function (id, tg) {
                                        let tmp = {};
                                        tmp = JSON.parse(JSON.stringify(chunk));
                                        tmp['Tech'] = obj.Tech;  
                                        tmp['TechGroup'] = techGroupNames[tg];
                                        tmp['TechDesc'] = techData[obj.Tech]["Desc"];
                                        tmp['TechGroupDesc'] = techGroupData[tg]["Desc"];
                                        dataT = unitData[group][param][obj.Tech];
                                        tmp['Unit'] = jsonLogic.apply(rule, {...dataT});
                                        pivotData.push(tmp);
                                    })
                                }else{
                                    chunk['Tech'] = obj.Tech;  
                                    chunk['TechGroup'] = 'No group';
                                    chunk['TechDesc'] = techData[obj.Tech]["Desc"];
                                    chunk['TechGroupDesc'] = 'No group';
                                    dataT = unitData[group][param][obj.Tech];
    
                                    chunk['Unit'] = jsonLogic.apply(rule, {...dataT});
                                    pivotData.push(chunk);
                                }
    
                                // console.log('rule ', rule)
                                // console.log('unitData[group][param] ', unitData[group][param])
                                // console.log('dataT ', dataT)
                                dataT = unitData[group][param][obj.Tech];
                                //console.log('TECH ', dataT, rule)
                            }
                            else{
                                chunk['Tech'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech;  
                                chunk['TechGroup'] = 'No group';
                                chunk['TechDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech + " deleted from model";
                                chunk['TechGroupDesc'] = 'No group';
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                                pivotData.push(chunk);
                            }
    
                        }
                        //ako je group koji ima i Tech i Comm
                        if(obj.Tech && obj.Comm){
                            //console.log('techData ', obj.Tech, '------',  techData[obj.Tech])   //DEMINDLFO 
                            //vk 18972024 ovaj uslov dodat - 
                            // ako korisnik izbrise tech on ce ostati u view json filovima i doci ce do greske, ovaj tech se mora ignorisati u pivotdata
                            if(obj.Tech in techData && obj.Comm in commData){
                                let rule = paramById[group][param]['unitRule'];
                                dataT = unitData[group][param][obj.Tech];
                                dataC = unitData[group][param][obj.Comm];

                                //console.log('dataT ', dataT, 'dataC ', dataC, 'rule ', rule, 'group ', group, 'param ', param)

                                if(techData[obj.Tech].TG.length != 0){
                                    $.each(techData[obj.Tech].TG, function (id, tg) {
                                        let tmp = {};
                                        tmp = JSON.parse(JSON.stringify(chunk));
                                        tmp['Tech'] = obj.Tech;  
                                        tmp['TechGroup'] = techGroupNames[tg];
                                        tmp['TechDesc'] = techData[obj.Tech]["Desc"];
                                        tmp['TechGroupDesc'] = techGroupData[tg]["Desc"];
                                        tmp['Unit'] = jsonLogic.apply(rule, {...dataT, ...dataC});

                                        tmp['Comm'] = obj.Comm;
                                        tmp['CommDesc'] = commData[obj.Comm]["Desc"];
                                        pivotData.push(tmp);
                                    })
                                }
                                else{
                                    chunk['Tech'] = obj.Tech;  
                                    chunk['TechGroup'] = 'No group';
                                    chunk['TechDesc'] = techData[obj.Tech]["Desc"];
                                    chunk['TechGroupDesc'] = 'No group';
                                    chunk['Unit'] = jsonLogic.apply(rule, {...dataT, ...dataC});
                                    //pivotData.push(chunk);
                                    chunk['Comm'] = obj.Comm;
                                    chunk['CommDesc'] = commData[obj.Comm]["Desc"];
                                    pivotData.push(chunk);
                                }
                                // chunk['Comm'] = obj.Comm;
                                // chunk['CommDesc'] = commData[obj.Comm]["Desc"];
                                // pivotData.push(chunk);
                                // console.log('rule ', rule)
                                // console.log('unitData[group][param] ', unitData[group][param])
                                // console.log('dataT ', dataT)
                                //dataT = unitData[group][param][obj.Tech];
                                //console.log('TECH ', dataT, rule)
                            }
                            else{
                                chunk['Tech'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech;  
                                chunk['TechGroup'] = 'No group';
                                chunk['TechDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech + " deleted from model";
                                chunk['TechGroupDesc'] = 'No group';
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';

                                chunk['Comm'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Comm;
                                chunk['CommDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Comm + " deleted from model";
                                pivotData.push(chunk);
                            }
                        }
                        if(!obj.Tech){
                            pivotData.push(chunk);
                        }  
                    });
                }
            });
        });
        return pivotData;
    }


    static getPivot_OLD(DATA, genData, VARIABLES, group, param){

        let unitData = this.getUnitData(genData, VARIABLES);
        let paramById = DataModel.getParamById(VARIABLES);
        let techData = this.getTechData(genData);
        let commData = this.getCommData(genData);
        let conData = this.getConData(genData);
        let emiData = this.getEmiData(genData);
        let stgData = this.getStgData(genData);
        let techGroupData = this.getTechGroupData(genData);
        let techGroupNames = DataModel.TechGroupName(genData);
        let years = genData['osy-years']

        console.log('unitData ',unitData)

        let pivotData = [];
        let dataT = {};
        let dataC = {};
        let dataE = {};
        let dataS = {};

        $.each(DATA[param], function (cs, array) {    
            //console.log('DATA[param] ', DATA[param], param) 
            $.each(array, function (id, obj) {

                if(obj.ObjectiveValue){
                    let chunkOv = {};
                    chunkOv['Case'] = cs;
                    chunkOv['Unit'] = 'n/a';
                    chunkOv['Optimal'] = 'Objective Value';
                    chunkOv['Value'] = obj.ObjectiveValue;
                    pivotData.push(chunkOv);
                }
                else{
                    $.each(years, function (idY, year) { 
                        let chunk = {};
                        chunk['Case'] = cs;
    
                        //provjera da li u obj ima Comm, Tech, Stg, Emi... Redosljed je bitan za one varijable koje zavise vise od jednog seta, definicja 
                        //unita ce da zavisi od toga
       
                        if(obj.MoId){
                            chunk['MoId'] = obj.MoId;
                        }
                        if(obj.Ts){
                            chunk['Ts'] = obj.Ts;
                        }
                        chunk['Year'] = year;
                        
                        if(year in obj){
                            chunk['Value'] = obj[year];
                        }
                        else{
                            chunk['Value'] = null;
                        }
    
                        if(obj.Comm){
                            
                            //uslov dodan vk 18072924 ako smo izbrisali commodity a postoji u resulttima
                            if(obj.Comm in commData){
                                chunk['Comm'] = obj.Comm;
                                chunk['CommDesc'] = commData[obj.Comm]["Desc"];
                               
                                dataC = unitData[group][param][obj.Comm];
                                let rule = paramById[group][param]['unitRule'];
                                //console.log('COM ', dataC, rule)
                                chunk['Unit'] = jsonLogic.apply(rule, {...dataC});
                            }
                            else{
                                chunk['Comm'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Comm;
                                chunk['CommDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Comm + " deleted from model";
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
    
                        if(obj.Con){
                            
                            if(obj.Con in conData){
                                chunk['Con'] = obj.Con;
                                chunk['ConDesc'] = conData[obj.Con]["Desc"];
                                chunk['Unit'] = 'n/a';
                               
                            }
                            else{
                                chunk['Con'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Con;
                                chunk['ConDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Con + " deleted from model";
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
    
                        if(obj.Stg){
                            
                            if(obj.Stg in stgData){
                                chunk['Stg'] = obj.Stg;
                                chunk['StgDesc'] = stgData[obj.Stg]["Desc"];
                                dataS = unitData[group][param][obj.Stg];
                                let rule = paramById[group][param]['unitRule'];
                                chunk['Unit'] = jsonLogic.apply(rule, {...dataS});
                            }
                            else{
                                chunk['Stg'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Stg;
                                chunk['StgDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Stg + " deleted from model";
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
                        if(obj.Emi){
                            
                            if(obj.Emi in emiData){
                                chunk['Emi'] = obj.Emi;
                                chunk['EmiDesc'] = emiData[obj.Emi]["Desc"];
                                dataE = unitData[group][param][obj.Emi];
                                let rule = paramById[group][param]['unitRule'];
                                chunk['Unit'] = jsonLogic.apply(rule, {...dataE});
                            }
                            else{
                                chunk['Emi'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' +obj.Emi;
                                chunk['EmiDesc'] =  '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Emi+' deleted from model';
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                            }
                        }
                        if(obj.Tech){
                            //console.log('techData ', obj.Tech, '------',  techData[obj.Tech])   //DEMINDLFO 
                            //vk 18972024 ovaj uslov dodat - 
                            // ako korisnik izbrise tech on ce ostati u view json filovima i doci ce do greske, ovaj tech se mora ignorisati u pivotdata
                            if(obj.Tech in techData){
                                let rule = paramById[group][param]['unitRule'];
                                if(techData[obj.Tech].TG.length != 0){
                                    $.each(techData[obj.Tech].TG, function (id, tg) {
                                        let tmp = {};
                                        tmp = JSON.parse(JSON.stringify(chunk));
                                        tmp['Tech'] = obj.Tech;  
                                        tmp['TechGroup'] = techGroupNames[tg];
                                        tmp['TechDesc'] = techData[obj.Tech]["Desc"];
                                        tmp['TechGroupDesc'] = techGroupData[tg]["Desc"];
                                        dataT = unitData[group][param][obj.Tech];
                                        tmp['Unit'] = jsonLogic.apply(rule, {...dataT});
                                        pivotData.push(tmp);
                                    })
                                }else{
                                    chunk['Tech'] = obj.Tech;  
                                    chunk['TechGroup'] = 'No group';
                                    chunk['TechDesc'] = techData[obj.Tech]["Desc"];
                                    chunk['TechGroupDesc'] = 'No group';
                                    dataT = unitData[group][param][obj.Tech];
    
                                    chunk['Unit'] = jsonLogic.apply(rule, {...dataT});
                                    pivotData.push(chunk);
                                }
    
                                // console.log('rule ', rule)
                                // console.log('unitData[group][param] ', unitData[group][param])
                                // console.log('dataT ', dataT)
                                dataT = unitData[group][param][obj.Tech];
                                //console.log('TECH ', dataT, rule)
                            }
                            else{
                                chunk['Tech'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech;  
                                chunk['TechGroup'] = 'No group';
                                chunk['TechDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech + " deleted from model";
                                chunk['TechGroupDesc'] = 'No group';
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';
                                pivotData.push(chunk);
                            }
    
                        }
                        if(!obj.Tech){
                            pivotData.push(chunk);
                        }
                        
                    });
                }


            });
        });
        return pivotData;
    }


}
