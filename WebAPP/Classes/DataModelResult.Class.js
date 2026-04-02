
import { DataModel} from "./DataModel.Class.js"
import { VAR_TECH_GROUPS, VAR_COMM_GROUPS, VAR_EMIS_GROUPS, VAR_STORAGE_GROUPS, VAR_CON_GROUPS } from "./Const.Class.js";

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
                        unitData[group][obj.id][tObj.Tech]['number'] = 'number';
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
                // con parameters
                if (VAR_CON_GROUPS.includes(group)) {
                    $.each(genData['osy-constraints'], function (id, cObj) {
                        unitData[group][obj.id][cObj.Con] = {};
                        unitData[group][obj.id][cObj.Con]['years'] = 'years';
                        unitData[group][obj.id][cObj.Con]['percent'] = '%';
                        unitData[group][obj.id][cObj.Con]['divide'] = '/';
                        unitData[group][obj.id][cObj.Con]['multiply'] = '*';
                        unitData[group][obj.id][cObj.Con]['hundert'] = '100';
                        unitData[group][obj.id][cObj.Con]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][cObj.Con]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][cObj.Con]['Currency'] = genData['osy-currency'];
                        unitData[group][obj.id][cObj.Con]['number'] = 'number';
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

        //console.log('unitData ',unitData)

        let pivotData = [];
        let dataT = {};
        let dataC = {};
        let dataE = {};
        let dataS = {};
        let dataCon = {};

        $.each(DATA[param], function (cs, array) {    
            //console.log('DATA ', DATA[param]) 
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
                        // if(obj.Tech){
                        //     chunk['Tech'] = obj.Tech;  
                        //     dataT = unitData[group][param][obj.Tech];
                        // }
    
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
                            // console.log('Value ', obj[year], ' cs ', cs,  ' year ', year , ' param ', param)
                            //console.log('Value ', obj[year])
                            chunk['Value'] = null;
                        }
    
                        // let rule = paramById[group][param]['unitRule'];
                        // const data = {...dataC, ...dataE, ...dataS};
                        // chunk['Unit'] = jsonLogic.apply(rule, data);
                        

                        if (obj.Comm && !obj.Tech) {
                            
                            //uslov dodan vk 18072924 ako smo izbrisali commodity a postoji u resulttima
                            if(obj.Comm in commData){
                                chunk['Comm'] = obj.Comm;
                                chunk['CommDesc'] = commData[obj.Comm]["Desc"];
                               
                                dataC = unitData[group][param][obj.Comm];
                                let rule = paramById[group][param]['unitRule'];
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

                                dataCon = unitData[group][param][obj.Con];
                                let rule = paramById[group][param]['unitRule'];
                                chunk['Unit'] = jsonLogic.apply(rule, { ...dataCon });
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
                        if (obj.Tech && !obj.Comm) {
                            //console.log('techData ', obj.Tech, '------',  techData[obj.Tech])   //DEMINDLFO 
                            //vk 18972024 ovaj uslov dodat - ako korisnik izbrise tech on ce ostati u view json filovima i doci ce do greske, ovaj tech se mora ignorisati u pivotdata
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
                        if (obj.Tech && obj.Comm) {
                            if (obj.Tech in techData && obj.Comm in commData) {
                                let rule = paramById[group][param]['unitRule'];
                                dataT = unitData[group][param][obj.Tech];
                                dataC = unitData[group][param][obj.Comm];

                                // console.log('dataT ', dataT, 'dataC ', dataC, 'rule ', rule, 'group ', group, 'param ', param)
                                if (techData[obj.Tech].TG.length != 0) {
                                    $.each(techData[obj.Tech].TG, function (id, tg) {
                                        let tmp = {};
                                        tmp = JSON.parse(JSON.stringify(chunk));
                                        tmp['Tech'] = obj.Tech;
                                        tmp['TechGroup'] = techGroupNames[tg];
                                        tmp['TechDesc'] = techData[obj.Tech]["Desc"];
                                        tmp['TechGroupDesc'] = techGroupData[tg]["Desc"];

                                        console.log('jsonLogic.apply(rule, {...dataT, ...dataC}) ', jsonLogic.apply(rule, { ...dataT, ...dataC }));
                                        tmp['Unit'] = jsonLogic.apply(rule, { ...dataT, ...dataC });

                                        tmp['Comm'] = obj.Comm;
                                        tmp['CommDesc'] = commData[obj.Comm]["Desc"];
                                        pivotData.push(tmp);
                                    })
                                }
                                else {
                                    chunk['Tech'] = obj.Tech;
                                    chunk['TechGroup'] = 'No group';
                                    chunk['TechDesc'] = techData[obj.Tech]["Desc"];
                                    chunk['TechGroupDesc'] = 'No group';
                                    chunk['Unit'] = jsonLogic.apply(rule, { ...dataT, ...dataC });
                                    //pivotData.push(chunk);
                                    chunk['Comm'] = obj.Comm;
                                    chunk['CommDesc'] = commData[obj.Comm]["Desc"];
                                    pivotData.push(chunk);
                                }
                            }
                            else {
                                chunk['Tech'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech;
                                chunk['TechGroup'] = 'No group';
                                chunk['TechDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Tech + " deleted from model";
                                chunk['TechGroupDesc'] = 'No group';
                                chunk['Unit'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> n/a';

                                chunk['Comm'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Comm;
                                chunk['CommDesc'] = '<i class="fa fa-exclamation-triangle danger" aria-hidden="true"></i> ' + obj.Comm + " deleted from model";
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

    // static getPivot(DATA, genData, VARIABLES, group, param){

    //     let unitData = this.getUnitData(genData, VARIABLES);
    //     let paramById = DataModel.getParamById(VARIABLES);
    //     let years = genData['osy-years']
    //     let techData = this.getTechData(genData);
    //     let techGroupNames = DataModel.TechGroupName(genData);

    //     let pivotData = [];
    //     let dataT = {};
    //     let dataC = {};
    //     let dataE = {};

    //     $.each(DATA[param], function (cs, array) {     
    //         $.each(array, function (id, obj) {

    //             let chunk = {};
    //             chunk['Case'] = cs;
    //             if(obj.Tech){
    //                 if(techData[obj.Tech].TG.length != 0){
    //                     $.each(techData[obj.Tech].TG, function (id, tg) {
    //                         chunk['Tech'] = obj.Tech;  
    //                         chunk['TechGroup'] = techGroupNames[tg];
    //                         dataT = unitData[group][param][obj.Tech];
    //                     })
    //                 }else{
    //                     chunk['Tech'] = obj.Tech;  
    //                     chunk['TechGroup'] = 'No group';
    //                     dataT = unitData[group][param][obj.Tech];
    //                 }

    //             }
    //             if(obj.Comm){
    //                 chunk['Comm'] = obj.Comm;
    //                 dataC = unitData[group][param][obj.Comm];
    //             }
    //             if(obj.Emi){
    //                 chunk['Emi'] = obj.Emi;
    //                 dataE = unitData[group][param][obj.Emi];
    //             }
    //             if(obj.MoId){
    //                 chunk['MoId'] = obj.MoId;
    //             }
    //             if(obj.Ts){
    //                 chunk['Ts'] = obj.Ts;
    //             }

    //             let rule = paramById[group][param]['unitRule'];
    //             const data = {...dataT, ...dataC, ...dataE};
    //             chunk['Unit'] = jsonLogic.apply(rule, data);

    //             $.each(years, function (idY, year) { 
    //                 let tmp = {};
    //                 tmp = JSON.parse(JSON.stringify(chunk));
    //                 tmp['Year'] = year;
    //                 tmp['Value'] = obj[year];
    //                 pivotData.push(tmp);
    //             });

    //         });
    //     });
    //     return pivotData;
    // }

    ////////////////////////////////////////////////////////JSON data structures
/*
    static RT(RTdata){
        let RT = {};
        const cloneData = JSON.parse(JSON.stringify(RTdata));
        $.each(cloneData, function (param, obj1) {
            RT[param] = {};
            $.each(obj1, function (sc, array) {
                RT[param][sc] = {};
                $.each(array, function (id, obj) { 
                    RT[param][sc] = obj
                });
            });
        });
        return RT;
    }

    static RTgrid(RTdata){
        // // let scName = this.ScName(genData);
        // // let scData = this.getScData(genData);
        // // let paramName = this.ParamName(PARAMETERS['RT']);
        // // let unitData = this.getUnitData(genData, PARAMETERS);
        // // let paramById = this.getParamById(PARAMETERS);
        // const cloneData = JSON.parse(JSON.stringify(RTdata));
        // let RTgrid = {}

        // $.each(cloneData, function (param, paramObj) {
        //     RTgrid[param] = [];
        //     $.each(paramObj, function (sc, array) {
        //         $.each(array, function (id, obj) {
        //             // obj['ParamId'] = param;
        //             // obj['Param'] = paramName[param];
        //             // // obj['ScId'] = sc;
        //             // // obj['Sc'] = scName[sc];
        //             // obj['ScId'] = sc;
        //             // obj['Sc'] = scData[sc]['Scenario'];
        //             // obj['ScDesc'] = scData[sc]['Desc'];
        //             // $.each(genData['osy-tech'], function (id, tech) {
        //             //     let rule = paramById['RT'][param]['unitRule'];
        //             //     let data = unitData['RT'][param][tech.TechId];
        //             //     obj[tech.TechId+'_UnitId'] = jsonLogic.apply(rule, data);
        //             // });
        //             RTgrid[param].push(obj);
        //         }); 
        //     });
        // });
        return RTdata;
    }

    static RTchart(RTdata){
        //let techName = this.TechName(genData);
        // let RTchart = {};
        // //RYTdata[VC] = [{tech, Sc,2000, 2020...}]
        // //let data = this.RT(RTdata);
        // $.each(RTdata, function (param, obj) {
        //     let chartData = {};
           
        //     $.each(obj, function (cs, obj1) {
        //         chartData[cs] = [];
        //         $.each(obj1, function (tech, val) {
        //             let chunk = {};
        //             chunk['Tech'] = tech
        //             // $.each(genData['osy-tech'], function (idT, tech) {
        //             //     let chunk = {};
        //             //     chunk['TechId'] = tech.TechId;
        //             //     chunk['Tech'] = techName[tech.TechId];
        //             //     $.each(genData['osy-scenarios'], function (idS, sc) {
        //             //         if (typeof data[param][sc.ScenarioId][tech.TechId] !== "undefined" ){
        //             //             chunk[sc.ScenarioId] = data[param][sc.ScenarioId][tech.TechId];
        //             //         }
        //             //     });
        //             //     RTchart[param].push(chunk);
        //         });  
        //         RTchart[param] = chartData; 
        //     });             
        // });
        return RTdata;
    }

    static RYT(RYTdata){
        let RYT = {};
        const cloneData = JSON.parse(JSON.stringify(RYTdata));
        $.each(cloneData, function (param, obj1) {
            RYT[param] = {};
            $.each(obj1, function (cs, array) {
                RYT[param][cs] = {};
                $.each(array, function (id, obj) {
                    RYT[param][cs][obj.Tech] = obj
                    delete obj.Tech;
                });
            });
        });
        return RYT;
    }

    static RYTgrid(RYTdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);
        const cloneData = JSON.parse(JSON.stringify(RYTdata));
        let RYTgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYTgrid[param] = {};
            $.each(paramObj, function (cs, array) {
                RYTgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = obj.Tech;
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    let rule = paramById['RYT'][param]['unitRule'];
                    let data = unitData['RYT'][param][obj.Tech];

                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTgrid[param][cs].push(obj);
                }); 
            });
        });
        return RYTgrid;
    }

    static RYTchart(genData, RYTdata){
        let RYTchart = {};
        let data = this.RYT(RYTdata);
        $.each(RYTdata, function (param, obj) {
            let chartData = {};
            $.each(obj, function (cs, obj1) {
                chartData[cs] = [];
                $.each(genData['osy-years'], function (idY, year) { 
                    let chunk = {};
                    chunk['Year'] = year;
                    $.each(genData['osy-tech'], function (idT, tech) {
                    //$.each( data[param][cs], function (tech, obj2) {
                        
                        if (data[param][cs][tech.Tech]){
                            chunk[tech.Tech] = data[param][cs][tech.Tech][year];
                        }else{
                            //chunk[tech.Tech] = null
                        }
                        //chunk[tech] = data[param][cs][tech][year]  
                    });        
                    chartData[cs].push(chunk); 
                });        
            });
            RYTchart[param] = chartData; 
        });
        return RYTchart;
    }

    static RYE(RYEdata){
        let RYE = {};
        const cloneData = JSON.parse(JSON.stringify(RYEdata));
        $.each(cloneData, function (param, obj1) {
            RYE[param] = {};
            $.each(obj1, function (cs, array) {
                RYE[param][cs] = {};
                $.each(array, function (id, obj) {
                    RYE[param][cs][obj.Emi] = obj
                    delete obj.Emi;
                    // delete obj.Emis;
                    // delete obj.ScId;
                    // delete obj.Sc;
                });
            });
        });
        return RYE;
    }

    static RYEgrid(RYEdata, genData, PARAMETERS){
        let emiData = this.getEmiData(genData);
        // let scData = this.getScData(genData);
        // let unitData = this.getUnitData(genData, PARAMETERS);
        // let paramById = this.getParamById(PARAMETERS);
        const cloneData = JSON.parse(JSON.stringify(RYEdata));
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);

        let RYEgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYEgrid[param] = [];
            $.each(paramObj, function (cs, array) {
                RYEgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Emi'] = obj.Emi;
                    obj['EmiDesc'] = emiData[obj.Emi]['Desc'];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scData[sc]['Scenario'];
                    // obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYE'][param]['unitRule'];
                    let data = unitData['RYE'][param][obj.Emi];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYEgrid[param][cs].push(obj);
                }); 
            });
        });
        return RYEgrid;
    }

    static RYEchart(genData, RYEdata){
        let RYEchart = {};
        let data = this.RYE(RYEdata);
        $.each(RYEdata, function (param, obj) {
            let chartData = {};
            $.each(obj, function (cs, obj1) {
                chartData[cs] = [];
                $.each(genData['osy-years'], function (idY, year) { 
                    let chunk = {};
                    chunk['Year'] = year;
                    //$.each(genData['osy-emis'], function (idC, emi) {
                    $.each( data[param][cs], function (emi, obj2) {
                        //chunk[emi.Emis] = data[param][cs][emi.Emis][year]  
                        chunk[emi] = data[param][cs][emi][year]
                    });
                    chartData[cs].push(chunk);
                });
            });
            RYEchart[param] = chartData; 
            
        });
        return RYEchart;
    }

    static RYTM(RYTMdata){
        let RYTM = {};
        const cloneData = JSON.parse(JSON.stringify(RYTMdata));
        $.each(cloneData, function (param, obj1) {
            RYTM[param] = {};
            $.each(obj1, function (cs, array) {
                RYTM[param][cs] = {};
                $.each(array, function (id, obj) {
                    if(!RYTM[param][cs][obj.Tech]){ RYTM[param][cs][obj.Tech] = {}; }
                    RYTM[param][cs][obj.Tech][obj.MoId] = obj;
                    delete obj.Tech;
                    delete obj.MoId;                    
                });
            });
        });
        return RYTM;
    }

    static RYTMgrid(RYTMdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYTMdata));
        let RYTMgrid = {};

        $.each(cloneData, function (param, obj) {
            RYTMgrid[param] = [];
            $.each(obj, function (cs, array) {
                RYTMgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = obj.Tech
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    let rule = paramById['RYTM'][param]['unitRule'];
                    let data = unitData['RYTM'][param][obj.Tech];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTMgrid[param][cs].push(obj);
                });
            });
        });
        return RYTMgrid;
    }

    static RYTMchart(genData, RYTMdata){
        let RYTM = this.RYTM(RYTMdata);
        let mods = DataModel.Mods(genData);
        let RYTMchart = {};

        $.each(RYTMdata, function (param, obj) {
            let chartData = {}
    
            $.each(obj, function (cs, obj1) {
                chartData[cs] = {};
                $.each(mods, function (idS, mo) {   
                    chartData[cs][mo] = []; 
                    $.each(genData['osy-years'], function (idY, year) {                  
                        let chunk = {};
                        chunk['Year'] = year;
                        $.each(genData['osy-tech'], function (idT, tech) {     
                            if(RYTM[param][cs][tech.Tech]){
                                chunk[tech.Tech] = RYTM[param][cs][tech.Tech][mo][year];
                            }else{
                                //chunk[tech.Tech] = null;
                            }
                            
                        // $.each(genData['osy-scenarios'], function (idS, sc) {
                        //     chunk[sc.ScenarioId] = RYTM[param][sc.ScenarioId][tech.TechId][mo][year];
                        // });
                        
                        });  
                        chartData[cs][mo].push(chunk);            
                    });
                });
            }); 
            RYTMchart[param] = chartData;    
        });       
        return RYTMchart;
    }

    static RYTC(RYTCdata){
        let RYTC = {};
        const cloneData = JSON.parse(JSON.stringify(RYTCdata));
        $.each(cloneData, function (param, obj1) {
            RYTC[param] = {};
            $.each(obj1, function (cs, array) {
                RYTC[param][cs] = {};
                $.each(array, function (id, obj) {
                    if(!RYTC[param][cs][obj.Tech]){ RYTC[param][cs][obj.Tech] = {}; }
                        RYTC[param][cs][obj.Tech][obj.Comm] = obj;
                        delete obj.Tech;
                        delete obj.Comm;   
                });
            });
        });
        return RYTC;
    }

    static RYTCTechs(RYTCdata){
        let RYTCTechs = {};
        let RYTC = this.RYTC(RYTCdata);
        $.each(RYTC, function (param, obj1) {
            RYTCTechs[param] = {};
            $.each(obj1, function (cs, array) {
                RYTCTechs[param][cs] = Object.keys(array);
            });
        });
        return RYTCTechs;
    }

    static RYTCgrid(RYTCdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let commData = this.getCommData(genData);
        // let unitData = this.getUnitData(genData, PARAMETERS);
        // let paramById = DataModel.getParamById(PARAMETERS);

        let cloneData = JSON.parse(JSON.stringify(RYTCdata));
        let RYTCgrid = {};

        $.each(cloneData, function (param, obj) {
            RYTCgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYTCgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.Tech]['Tech'];
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    obj['Comm'] = commData[obj.Comm]['Comm'];
                    obj['CommDesc'] = commData[obj.Comm]['Desc'];
                    // let rule = paramById['RYTC'][param]['unitRule'];
                    // let data = unitData['RYTC'][param][obj.Tech];
                    // obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTCgrid[param][cs].push(obj);
                });
            });
        });
        return RYTCgrid;
    }

    static RYTCchart(genData, RYTCdata){
        let RYTCchart = {};
        let RYTC = this.RYTC(RYTCdata);
        $.each(RYTC, function (param, obj1) {
            RYTCchart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYTCchart[param][cs] = {};
                    $.each(obj2, function (tech, obj3) {

                        if(!RYTCchart[param][cs][tech]){ RYTCchart[param][cs][tech] = []; }
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;

                            $.each(RYTC[param][cs][tech], function (comm, obj) {
                                chunk[comm] = obj[year]
                            });
                            RYTCchart[param][cs][tech].push(chunk);
                        });
                    });
                }
            });
        });
        return RYTCchart;
    }

    static RYTCchartAll(genData, RYTCdata){
        let RYTCchart = {};
        let RYTC = this.RYTC(RYTCdata);
        $.each(RYTC, function (param, obj1) {
            RYTCchart[param] = {};
            $.each(genData['osy-years'], function (idY, year) {
                let chunk = {};
                chunk['Year'] = year;
                $.each(obj1, function (cs, obj2) {
                    if (obj2.length !== 0){
                        RYTCchart[param][cs] = [];

                            $.each(obj2, function (tech, obj3) {

                            //if(!RYTCchart[param][cs][tech]){ RYTCchart[param][cs][tech] = []; }
                    


                                $.each(RYTC[param][cs][tech], function (comm, obj) {
                                    chunk[tech+'_'+comm] = obj[year]
                                });
                                RYTCchart[param][cs].push(chunk);
                            });
                    }
                });
                    
            });
        });
        return RYTCchart;
    }

    static RYTE(RYTEdata){
        let RYTE = {};
        const cloneData = JSON.parse(JSON.stringify(RYTEdata));
        $.each(cloneData, function (param, obj1) {
            RYTE[param] = {};
            $.each(obj1, function (sc, array) {
                RYTE[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTE[param][sc][obj.Tech]){ RYTE[param][sc][obj.Tech] = {}; }
                        RYTE[param][sc][obj.Tech][obj.Emi] = obj;
                        delete obj.Tech;
                        delete obj.Emis;   
                });
            });
        });
        return RYTE;
    }

    static RYTEgrid(RYTEdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let emiData = this.getEmiData(genData);
        
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);

        let cloneData = JSON.parse(JSON.stringify(RYTEdata));
        let RYTEgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTEgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYTEgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.Tech]['Tech'];
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    obj['Emis'] = emiData[obj.Emi]['Emis'];
                    obj['EmiDesc'] = emiData[obj.Emi]['Desc'];
                    let rule = paramById['RYTE'][param]['unitRule'];
                    let data = unitData['RYTE'][param][obj.Emi];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTEgrid[param][cs].push(obj);
                });
            });
        });
        return RYTEgrid;
    }

    static RYTETechs(RYTEdata){
        let RYTETechs = {};
        let RYTE = this.RYTE(RYTEdata);
        $.each(RYTE, function (param, obj1) {
            RYTETechs[param] = {};
            $.each(obj1, function (cs, array) {
                RYTETechs[param][cs] = Object.keys(array);
            });
        });
        return RYTETechs;
    }

    static RYTEchart(genData, RYTEdata){
        let RYTEchart = {};
        let RYTE = this.RYTE(RYTEdata);
        $.each(RYTE, function (param, obj1) {
            RYTEchart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYTEchart[param][cs] = {};
                    $.each(obj2, function (tech, obj3) {

                        if(!RYTEchart[param][cs][tech]){ RYTEchart[param][cs][tech] = []; }
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;

                            $.each(obj3, function (comm, obj) {
                                chunk[comm] = obj[year]
                            });
                            RYTEchart[param][cs][tech].push(chunk);
                        });
                    });
                }
            });
        });
        return RYTEchart;
    }

    static RYTTs(RYTTsdata){
        let RYTTs = {};
        const cloneData = JSON.parse(JSON.stringify(RYTTsdata));
        $.each(cloneData, function (param, obj1) {
            RYTTs[param] = {};
            $.each(obj1, function (sc, array) {
                RYTTs[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTTs[param][sc][obj.Tech]){ RYTTs[param][sc][obj.Tech] = {}; }
                    RYTTs[param][sc][obj.Tech][obj.Ts] = obj;
                    delete obj.Tech;
                    delete obj.Ts;                    
                });
            });
        });
        return RYTTs;
    }

    static RYTTsgrid(RYTTsdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let cloneData = JSON.parse(JSON.stringify(RYTTsdata));

        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);

        let RYTTsgrid = {};

        $.each(cloneData, function (param, obj) {
            RYTTsgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYTTsgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.Tech]['Tech'];
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    let rule = paramById['RYTTs'][param]['unitRule'];
                    let data = unitData['RYTTs'][param][obj.Tech];
                    obj['UnitId'] = jsonLogic.apply(rule, data);

                    RYTTsgrid[param][cs].push(obj);
                });
            });
        });
        return RYTTsgrid;
    }

    static RYTTschart(genData, RYTTsdata){
        let RYTTs = this.RYTTs(RYTTsdata);
        //let timeslices = this.Timeslices(genData);
        let RYTTschart = {};
        $.each(RYTTs, function (param, obj1) {
            RYTTschart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYTTschart[param][cs] = {};
                    $.each(obj2, function (tech, obj3) {

                        if(!RYTTschart[param][cs][tech]){ RYTTschart[param][cs][tech] = []; }
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;
                            $.each(obj3, function (ts, obj) {
                                chunk[ts] = obj[year]
                            });
                            RYTTschart[param][cs][tech].push(chunk);
                        });
                    });
                }
            });
        });  
        return RYTTschart;
    }

    static RYCTs(RYCTsdata){
        let RYCTs = {};
        const cloneData = JSON.parse(JSON.stringify(RYCTsdata));
        $.each(cloneData, function (param, obj1) {
            RYCTs[param] = {};
            $.each(obj1, function (sc, array) {
                RYCTs[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYCTs[param][sc][obj.Comm]){ RYCTs[param][sc][obj.Comm] = {}; }
                    RYCTs[param][sc][obj.Comm][obj.Ts] = obj;
                    delete obj.Comm;
                    delete obj.Ts; 
                });
            });
        });
        return RYCTs;
    }

    static RYCTsgrid(RYCTsdata, genData, PARAMETERS){
        let commData = this.getCommData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYCTsdata));
        let RYCTsgrid = {};

        $.each(cloneData, function (param, obj) {
            RYCTsgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYCTsgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Comm'] = commData[obj.Comm]['Comm'];
                    obj['CommDesc'] = commData[obj.Comm]['Desc'];
                    let rule = paramById['RYCTs'][param]['unitRule'];
                    let data = unitData['RYCTs'][param][obj.Comm];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYCTsgrid[param][cs].push(obj);
                });
            });
        });
        return RYCTsgrid;
    }

    static RYCTschart(genData, RYCTsdata){
        let RYCTs = this.RYCTs(RYCTsdata);
        let RYCTschart = {};
        $.each(RYCTs, function (param, obj1) {
            RYCTschart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYCTschart[param][cs] = {};
                    $.each(obj2, function (comm, obj3) {
                        if(!RYCTschart[param][cs][comm]){ RYCTschart[param][cs][comm] = []; }
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;
                            $.each(obj3, function (ts, obj) {
                                chunk[ts] = obj[year]
                            });
                            RYCTschart[param][cs][comm].push(chunk);
                        });
                    });
                }
            });
        });  
        return RYCTschart;
    }

    static RYTEM(RYTEMdata){
        let RYTEM = {};
        const cloneData = JSON.parse(JSON.stringify(RYTEMdata));
        $.each(cloneData, function (param, obj1) {
            RYTEM[param] = {};
            $.each(obj1, function (sc, array) {
                RYTEM[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTEM[param][sc][obj.Tech]){ RYTEM[param][sc][obj.Tech] = {}; }
                    if(!RYTEM[param][sc][obj.Tech][obj.Emi]){ RYTEM[param][sc][obj.Tech][obj.Emi] = {}; }
                        RYTEM[param][sc][obj.Tech][obj.Emi][obj.MoId] = obj;
                        delete obj.Tech;
                        delete obj.Emi; 
                        delete obj.MoId;   
                });
            });
        });
        return RYTEM;
    }

    static RYTEMTechs(RYTEMdata){
        let RYTEMTechs = {};
        let RYTEM = this.RYTEM(RYTEMdata);
        $.each(RYTEM, function (param, obj1) {
            RYTEMTechs[param] = {};
            $.each(obj1, function (cs, array) {
                RYTEMTechs[param][cs] = Object.keys(array);
            });
        });
        return RYTEMTechs;
    }

    static RYTEMEmis(RYTEMdata){
        let RYTEMemis = {};
        let RYTEM = this.RYTEM(RYTEMdata);
        $.each(RYTEM, function (param, obj1) {
            RYTEMemis[param] = {};
            $.each(obj1, function (cs, obj2) {
                RYTEMemis[param][cs] = {};
                $.each(obj2, function (tech, array) {
                    RYTEMemis[param][cs][tech] = Object.keys(array);
                });
            });
        });
        return RYTEMemis;
    }

    static RYTEMgrid(RYTEMdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let emiData = this.getEmiData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);
        
        let cloneData = JSON.parse(JSON.stringify(RYTEMdata));
        let RYTEMgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTEMgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYTEMgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.Tech]['Tech'];
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    obj['Emis'] = emiData[obj.Emi]['Emis'];
                    obj['EmiDesc'] = emiData[obj.Emi]['Desc'];

                    let rule = paramById['RYTEM'][param]['unitRule'];
                    let data1 = unitData['RYTEM'][param][obj.Emi];
                    let data2 = unitData['RYTEM'][param][obj.Tech];
                    const data = {...data1, ...data2};
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTEMgrid[param][cs].push(obj);
                });
            });
        });
        return RYTEMgrid;
    }

    static RYTEMchart(genData, RYTEMdata){
        let RYTEMchart = {};
        let RYTEM = this.RYTEM(RYTEMdata);
        $.each(RYTEM, function (param, obj1) {
            RYTEMchart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYTEMchart[param][cs] = {};
                    $.each(obj2, function (tech, obj3) {
                        if(!RYTEMchart[param][cs][tech]){ RYTEMchart[param][cs][tech] = {}; }
                        $.each(genData['osy-years'], function (idY, year) {
                            $.each(obj3, function (emi, obj4) {
                                if(!RYTEMchart[param][cs][tech][emi]){ RYTEMchart[param][cs][tech][emi] = []; }
                                let chunk = {};
                                chunk['Year'] = year;
                                $.each(obj4, function (mod, obj) {
                                    chunk[mod] = obj[year]
                                });
                                RYTEMchart[param][cs][tech][emi].push(chunk);
                            });  
                        });
                    });
                }
            });
        });  
        return RYTEMchart;
    }

    static RYTCTs(RYTCTsMdata){
        let RYTCTs = {};
        const cloneData = JSON.parse(JSON.stringify(RYTCTsMdata));
        $.each(cloneData, function (param, obj1) {
            RYTCTs[param] = {};
            $.each(obj1, function (sc, array) {
                RYTCTs[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTCTs[param][sc][obj.Tech]){ RYTCTs[param][sc][obj.Tech] = {}; }
                    if(!RYTCTs[param][sc][obj.Tech][obj.Comm]){ RYTCTs[param][sc][obj.Tech][obj.Comm] = {}; }
                    RYTCTs[param][sc][obj.Tech][obj.Comm][obj.Ts] = obj;
                        delete obj.Tech;
                        delete obj.Comm; 
                        delete obj.Ts;   
                });
            });
        });
        return RYTCTs;
    }

    static RYTCTsTechs(RYTCTsdata){
        let RYTCTsTechs = {};
        let RYTCTs = this.RYTCTs(RYTCTsdata);
        $.each(RYTCTs, function (param, obj1) {
            RYTCTsTechs[param] = {};
            $.each(obj1, function (cs, array) {
                RYTCTsTechs[param][cs] = Object.keys(array);
            });
        });
        return RYTCTsTechs;
    }

    static RYTCTsComms(RYTCTsdata){
        let RYTCTsComms = {};
        let RYTCTs = this.RYTCTs(RYTCTsdata);
        $.each(RYTCTs, function (param, obj1) {
            RYTCTsComms[param] = {};
            $.each(obj1, function (cs, obj2) {
                RYTCTsComms[param][cs] = {};
                $.each(obj2, function (comm, array) {
                    RYTCTsComms[param][cs][comm] = Object.keys(array);
                });
            });
        });
        return RYTCTsComms;
    }

    static RYTCTsgrid(RYTCTsdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let commData = this.getCommData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);
        
        let cloneData = JSON.parse(JSON.stringify(RYTCTsdata));
        let RYTCTsgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTCTsgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYTCTsgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.Tech]['Tech'];
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    obj['Comm'] = commData[obj.Comm]['Comm'];
                    obj['commDesc'] = commData[obj.Comm]['Desc'];

                    let rule = paramById['RYTCTs'][param]['unitRule'];
                    let data1 = unitData['RYTCTs'][param][obj.Comm];
                    let data2 = unitData['RYTCTs'][param][obj.Tech];
                    const data = {...data1, ...data2};
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTCTsgrid[param][cs].push(obj);
                });
            });
        });
        return RYTCTsgrid;
    }

    static RYTCTschart(genData, RYTCTsdata){
        let RYTCTschart = {};
        let RYTCTs = this.RYTCTs(RYTCTsdata);
        $.each(RYTCTs, function (param, obj1) {
            RYTCTschart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYTCTschart[param][cs] = {};
                    $.each(obj2, function (tech, obj3) {
                        if(!RYTCTschart[param][cs][tech]){ RYTCTschart[param][cs][tech] = {}; }
                        $.each(genData['osy-years'], function (idY, year) {
       
                            $.each(obj3, function (comm, obj4) {
                                if(!RYTCTschart[param][cs][tech][comm]){ RYTCTschart[param][cs][tech][comm] = []; }
                                let chunk = {};
                                chunk['Year'] = year;
                                $.each(obj4, function (ts, obj) {
                                    chunk[ts] = obj[year]
                                });
                                RYTCTschart[param][cs][tech][comm].push(chunk);
                            });
                            
                           
                        });
                    });
                }
            });
        });  
        return RYTCTschart;
    }

    static RYTMTs(RYTMTsMdata){
        let RYTMTs = {};
        const cloneData = JSON.parse(JSON.stringify(RYTMTsMdata));
        $.each(cloneData, function (param, obj1) {
            RYTMTs[param] = {};
            $.each(obj1, function (sc, array) {
                RYTMTs[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTMTs[param][sc][obj.Tech]){ RYTMTs[param][sc][obj.Tech] = {}; }
                    if(!RYTMTs[param][sc][obj.Tech][obj.MoId]){ RYTMTs[param][sc][obj.Tech][obj.MoId] = {}; }
                    RYTMTs[param][sc][obj.Tech][obj.MoId][obj.Ts] = obj;
                        delete obj.Tech;
                        delete obj.MoId; 
                        delete obj.Ts;   
                });
            });
        });
        return RYTMTs;
    }

    static RYTMTsgrid(RYTMTsdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        // let mods = DataModel.Mods(genData);
        // let ts = DataModel.Timeslices(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);
        
        let cloneData = JSON.parse(JSON.stringify(RYTMTsdata));
        let RYTMTsgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTMTsgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYTMTsgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.Tech]['Tech'];
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];

                    let rule = paramById['RYTMTs'][param]['unitRule'];
                    let data = unitData['RYTMTs'][param][obj.Tech];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTMTsgrid[param][cs].push(obj);
                });
            });
        });
        return RYTMTsgrid;
    }

    static RYTMTschart(genData, RYTMTsdata){
        let RYTMTschart = {};
        let RYTMTs = this.RYTMTs(RYTMTsdata);
        $.each(RYTMTs, function (param, obj1) {
            RYTMTschart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYTMTschart[param][cs] = {};
                    $.each(obj2, function (tech, obj3) {
                        if(!RYTMTschart[param][cs][tech]){ RYTMTschart[param][cs][tech] = {}; }
                        $.each(genData['osy-years'], function (idY, year) {
                            $.each(obj3, function (mod, obj4) {
                                if(!RYTMTschart[param][cs][tech][mod]){ RYTMTschart[param][cs][tech][mod] = []; }
                                let chunk = {};
                                chunk['Year'] = year;
                                $.each(obj4, function (ts, obj) {
                                    chunk[ts] = obj[year]
                                });
                                RYTMTschart[param][cs][tech][mod].push(chunk);
                            });
                        });
                    });
                }
            });
        });  
        return RYTMTschart;
    }

    static RYTCMTs(RYTCMTsMdata){
        let RYTCMTs = {};
        const cloneData = JSON.parse(JSON.stringify(RYTCMTsMdata));
        $.each(cloneData, function (param, obj1) {
            RYTCMTs[param] = {};
            $.each(obj1, function (cs, array) {
                RYTCMTs[param][cs] = {};
                $.each(array, function (id, obj) {
                    if(!RYTCMTs[param][cs][obj.Tech]){ RYTCMTs[param][cs][obj.Tech] = {}; }
                    if(!RYTCMTs[param][cs][obj.Tech][obj.Comm]){ RYTCMTs[param][cs][obj.Tech][obj.Comm] = {}; }
                    if(!RYTCMTs[param][cs][obj.Tech][obj.Comm][obj.MoId]){ RYTCMTs[param][cs][obj.Tech][obj.Comm][obj.MoId] = {}; }

                    RYTCMTs[param][cs][obj.Tech][obj.Comm][obj.MoId][obj.Ts] = obj;
                        delete obj.Tech;
                        delete obj.Comm; 
                        delete obj.MoId;
                        delete obj.Ts;   
                });
            });
        });
        return RYTCMTs;
    }

    static RYTCMTsTechs(RYTCMTsdata){
        let RYTCTsTechs = {};
        let RYTCMTs = this.RYTCMTs(RYTCMTsdata);
        $.each(RYTCMTs, function (param, obj1) {
            RYTCTsTechs[param] = {};
            $.each(obj1, function (cs, array) {
                RYTCTsTechs[param][cs] = Object.keys(array);
            });
        });
        return RYTCTsTechs;
    }

    static RYTCMTsComms(RYTCMTsdata){
        let RYTCTsComms = {};
        let RYTCMTs = this.RYTCMTs(RYTCMTsdata);
        $.each(RYTCMTs, function (param, obj1) {
            RYTCTsComms[param] = {};
            $.each(obj1, function (cs, obj2) {
                RYTCTsComms[param][cs] = {};
                $.each(obj2, function (comm, array) {
                    RYTCTsComms[param][cs][comm] = Object.keys(array);
                });
            });
        });
        return RYTCTsComms;
    }

    static RYTCMTsgrid(RYTCMTsdata, genData, PARAMETERS){
        let techData = this.getTechData(genData);
        let commData = this.getCommData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = DataModel.getParamById(PARAMETERS);
        
        let cloneData = JSON.parse(JSON.stringify(RYTCMTsdata));
        let RYTCMTsgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTCMTsgrid[param] = {};
            $.each(obj, function (cs, array) {
                RYTCMTsgrid[param][cs] = [];
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.Tech]['Tech'];
                    obj['TechDesc'] = techData[obj.Tech]['Desc'];
                    obj['Comm'] = commData[obj.Comm]['Comm'];
                    obj['commDesc'] = commData[obj.Comm]['Desc'];

                    let rule = paramById['RYTCMTs'][param]['unitRule'];
                    let data1 = unitData['RYTCMTs'][param][obj.Comm];
                    let data2 = unitData['RYTCMTs'][param][obj.Tech];
                    const data = {...data1, ...data2};
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTCMTsgrid[param][cs].push(obj);
                });
            });
        });
        return RYTCMTsgrid;
    }

    static RYTCMTschart(genData, RYTCMTsdata){
        let RYTCTschart = {};
        let RYTCMTs = this.RYTCMTs(RYTCMTsdata);
        $.each(RYTCMTs, function (param, obj1) {
            RYTCTschart[param] = {};
            $.each(obj1, function (cs, obj2) {
                if (obj2.length !== 0){
                    RYTCTschart[param][cs] = {};
                    $.each(obj2, function (tech, obj3) {
                        if(!RYTCTschart[param][cs][tech]){ RYTCTschart[param][cs][tech] = {}; }
                        $.each(genData['osy-years'], function (idY, year) {
       
                            $.each(obj3, function (comm, obj4) {
                                if(!RYTCTschart[param][cs][tech][comm]){ RYTCTschart[param][cs][tech][comm] = []; }
                                $.each(obj4, function (mod, obj5) {
                                    if(!RYTCTschart[param][cs][tech][comm][mod]){ RYTCTschart[param][cs][tech][comm][mod] = []; }
                                    let chunk = {};
                                    chunk['Year'] = year;
                                    $.each(obj5, function (ts, obj) {
                                        chunk[ts] = obj[year]
                                    });
                                    RYTCTschart[param][cs][tech][comm][mod].push(chunk);
                                });

                            });
                            
                           
                        });
                    });
                }
            });
        });  
        return RYTCTschart;
    }
        */
}