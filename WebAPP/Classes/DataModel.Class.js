// Adapt source parameter JSON for lookups, editable grids, and charts. Group
// names encode dimensions (RYTCM = region/year/technology/commodity/mode).
// Keep stable IDs for persistence; attach display names and units only in views.
import { UNITDEFINITION, PARAM_TECH_GROUPS, PARAM_COMM_GROUPS, PARAM_EMIS_GROUPS, PARAM_STORAGE_GROUPS } from "./Const.Class.js";

export class DataModel{

    //RYT->VC->{}
    static getParamById(parameters){
        let paramById = {};
        const cloneData = JSON.parse(JSON.stringify(parameters));
        $.each(cloneData, function (group, array) {
            paramById[group] = {};
            $.each(array, function (id, obj) {
                paramById[group][obj.id] = obj;
                delete obj.id;
            });
        });
        return paramById;       
    }

    static getUnitData(genData, parameters){
        let unitData = {};
        let techUnits = this.getTechUnits(genData);
        let commUnits = this.getCommUnits(genData);
        let emiUnits = this.getEmiUnits(genData);
        let stgUnits = this.getStgUnits(genData);

        $.each(parameters, function (group, array) {
            unitData[group] = {};
            $.each(array, function (id, obj) {
                unitData[group][obj.id] = {};
                //tech parameters
                //console.log(group, obj.id)
                if(PARAM_TECH_GROUPS.includes(group)){
                    $.each(genData['osy-tech'], function (id, tObj) {
                        unitData[group][obj.id][tObj.TechId] = {};
                        unitData[group][obj.id][tObj.TechId]['years'] = 'years';
                        unitData[group][obj.id][tObj.TechId]['percent'] = '%';
                        unitData[group][obj.id][tObj.TechId]['divide'] = '/';
                        unitData[group][obj.id][tObj.TechId]['multiply'] = '*';
                        unitData[group][obj.id][tObj.TechId]['hundert'] = '100';
                        unitData[group][obj.id][tObj.TechId]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][tObj.TechId]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][tObj.TechId]['CapUnitId'] = techUnits[tObj.TechId]['CapUnitId'];
                        unitData[group][obj.id][tObj.TechId]['ActUnitId'] = techUnits[tObj.TechId]['ActUnitId'];
                        unitData[group][obj.id][tObj.TechId]['Currency'] = genData['osy-currency'];
                    });
                }
                if(PARAM_COMM_GROUPS.includes(group)){
                    //comm parameters
                    $.each(genData['osy-comm'], function (id, cObj) {
                        unitData[group][obj.id][cObj.CommId] = {};
                        unitData[group][obj.id][cObj.CommId]['years'] = 'years';
                        unitData[group][obj.id][cObj.CommId]['percent'] = '%';
                        unitData[group][obj.id][cObj.CommId]['divide'] = '/';
                        unitData[group][obj.id][cObj.CommId]['multiply'] = '*';
                        unitData[group][obj.id][cObj.CommId]['hundert'] = '100';
                        unitData[group][obj.id][cObj.CommId]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][cObj.CommId]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][cObj.CommId]['CommUnit'] = commUnits[cObj.CommId];
                        unitData[group][obj.id][cObj.CommId]['Currency'] = genData['osy-currency'];
                    });
                }
                if(PARAM_EMIS_GROUPS.includes(group)){
                    //emi parameters
                    $.each(genData['osy-emis'], function (id, eObj) {
                        unitData[group][obj.id][eObj.EmisId] = {};
                        unitData[group][obj.id][eObj.EmisId]['years'] = 'years';
                        unitData[group][obj.id][eObj.EmisId]['percent'] = '%';
                        unitData[group][obj.id][eObj.EmisId]['divide'] = '/';
                        unitData[group][obj.id][eObj.EmisId]['multiply'] = '*';
                        unitData[group][obj.id][eObj.EmisId]['hundert'] = '100';
                        unitData[group][obj.id][eObj.EmisId]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][eObj.EmisId]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][eObj.EmisId]['EmiUnit'] = emiUnits[eObj.EmisId];
                        unitData[group][obj.id][eObj.EmisId]['Currency'] = genData['osy-currency'];
                    });
                }
                if(PARAM_STORAGE_GROUPS.includes(group)){
                    $.each(genData['osy-stg'], function (id, eObj) {
                        unitData[group][obj.id][eObj.StgId] = {};
                        unitData[group][obj.id][eObj.StgId]['years'] = 'years';
                        unitData[group][obj.id][eObj.StgId]['percent'] = '%';
                        unitData[group][obj.id][eObj.StgId]['divide'] = '/';
                        unitData[group][obj.id][eObj.StgId]['multiply'] = '*';
                        unitData[group][obj.id][eObj.StgId]['hundert'] = '100';
                        unitData[group][obj.id][eObj.StgId]['thousand'] = '10<sup>3</sup>';
                        unitData[group][obj.id][eObj.StgId]['milion'] = '10<sup>6</sup>';
                        unitData[group][obj.id][eObj.StgId]['StgUnit'] = stgUnits[eObj.StgId];
                        unitData[group][obj.id][eObj.StgId]['Currency'] = genData['osy-currency'];
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

    static getRuleData(UNITDEFINITION){
        let ruleData = {};
        $.each(UNITDEFINITION, function (id, obj) {
            ruleData[id] = obj['name'];
        });
        return ruleData;       
    }

    static getUnitsDef(UNITDEFINITION){
        let unitsDef = {};
        $.each(UNITDEFINITION, function (id, obj) {
            unitsDef[id] = obj.name;
        });        
        return unitsDef;
    }

    static getIndicatorDef(VARIABLES){
        let indDef = {};
        indDef['divide'] = { name: ' / ', ruleVal: {"var":"divide"}};
        indDef['multiply'] = { name: ' * ', ruleVal: {"var":"multiply"}};
        $.each(VARIABLES, function (group, array) {
            $.each(array, function (i, obj) {
                obj.group = group;
                obj.ruleVal = {"var":obj.id};
                indDef[obj.id] = obj;
            });   
        });        
        return indDef;
    }


    static getIndicatorTypes(INDICATORS){
        let indTypes = [];
        $.each(INDICATORS, function (group, array) {
            $.each(array, function (i, obj) {
                indTypes.push(obj);
            });   
        });        
        return indTypes;
    }

    //get name from id
    static TechName(genData){
        let techNames = {};
        $.each(genData['osy-tech'], function (id, obj) {
            techNames[obj.TechId] = obj['Tech'];
        });
        return techNames;
    }

    static TechIdByName(genData){
        let techNames = {};
        $.each(genData['osy-tech'], function (id, obj) {
            techNames[obj.Tech] = obj.TechId;
        });
        return techNames;
    }

    static TechGroupName(genData){
        let techGroupNames = {};
        $.each(genData['osy-techGroups'], function (id, obj) {
            techGroupNames[obj.TechGroupId] = obj.TechGroup;
        });
        return techGroupNames;
    }

    /////////////////////////////////////////////////
    //tech data by id
    static getTechData(genData){
        let techNames = {};
        $.each(genData['osy-tech'], function (id, obj) {
            techNames[obj['TechId']] = obj;
        });
        return techNames;
    }

    static getStgData(genData){
        let stgNames = {};
        $.each(genData['osy-stg'], function (id, obj) {
            stgNames[obj['StgId']] = obj;
        });
        return stgNames;
    }

    static StgName(genData){
        let stgNames = {};
        $.each(genData['osy-stg'], function (id, obj) {
            stgNames[obj.StgId] = obj['Stg'];
        });
        return stgNames;
    }
    
    static getTsData(genData){
        let tsNames = {};
        $.each(genData['osy-ts'], function (id, obj) {
            tsNames[obj['TsId']] = obj;
        });
        return tsNames;
    }

    static getSeData(genData){
        let seNames = {};
        $.each(genData['osy-se'], function (id, obj) {
            seNames[obj['SeId']] = obj;
        });
        return seNames;
    }

    static getDtData(genData){
        let dtNames = {};
        $.each(genData['osy-dt'], function (id, obj) {
            dtNames[obj['DtId']] = obj;
        });
        return dtNames;
    }

    static getDtbData(genData){
        let dtbNames = {};
        $.each(genData['osy-dtb'], function (id, obj) {
            dtbNames[obj['DtbId']] = obj;
        });
        return dtbNames;
    }

    static getStgData(genData){
        let stgNames = {};
        $.each(genData['osy-stg'], function (id, obj) {
            stgNames[obj['StgId']] = obj;
        });
        return stgNames;
    }

    static getScData(genData){
        let ScNames = {};
        $.each(genData['osy-scenarios'], function (id, obj) {
            ScNames[obj['ScenarioId']] = obj;
        });
        return ScNames;
    }

    static getCommData(genData){
        let commData = {};
        $.each(genData['osy-comm'], function (id, obj) {
            commData[obj['CommId']] = obj;
        });
        return commData;
    }

    static getEmiData(genData){
        let emiData = {};
        $.each(genData['osy-emis'], function (id, obj) {
            emiData[obj['EmisId']] = obj;
        });
        return emiData;
    }

    static getConData(genData){
        let conData = {};
        $.each(genData['osy-constraints'], function (id, obj) {
            conData[obj['ConId']] = obj;
        });
        return conData;
    }

    ///////////////////////////////////

    //get id from name
    static TechId(genData){
        let techIds = {};
        $.each(genData['osy-tech'], function (id, obj) {
            techIds[obj['Tech']] = obj['TechId'];
        });
        return techIds;
    }

    static ConId(genData){
        let conID = {};
        $.each(genData['osy-constraints'], function (id, obj) {
            conID[obj['Con']] = obj['ConId'];
        });
        return conID;
    }

    static getTechUnits(genData){
        let TechUnits = {};
        $.each(genData['osy-tech'], function (id, obj) {
            TechUnits[obj.TechId] = {};
            TechUnits[obj.TechId]['CapUnitId'] = obj['CapUnitId'];
            TechUnits[obj.TechId]['ActUnitId'] = obj['ActUnitId'];
        });
        return TechUnits;
    }

    static getCommUnits(genData){
        let CommUnits = {};
        $.each(genData['osy-comm'], function (id, obj) {
            CommUnits[obj['CommId']] = obj['UnitId'];
        });
        return CommUnits;
    }

    static getEmiUnits(genData){
        let EmiUnits = {};
        $.each(genData['osy-emis'], function (id, obj) {
            EmiUnits[obj['EmisId']] = obj['UnitId'];
        });
        return EmiUnits;
    }

    static getStgUnits(genData){
        let StgUnits = {};
        $.each(genData['osy-stg'], function (id, obj) {
            StgUnits[obj['StgId']] = obj['UnitId'];
        });
        return StgUnits;
    }

    static CommName(genData){
        let commNames = {};
        $.each(genData['osy-comm'], function (id, obj) {
            commNames[obj['CommId']] = obj['Comm'];
        });
        return commNames;
    }

    static TsName(genData){
        let tsNames = {};
        $.each(genData['osy-ts'], function (id, obj) {
            tsNames[obj['TsId']] = obj['Ts'];
        });
        return tsNames;
    }


    static SeName(genData){
        let seNames = {};
        $.each(genData['osy-se'], function (id, obj) {
            seNames[obj['SeId']] = obj['Se'];
        });
        return seNames;
    }

    static DtName(genData){
        let dtNames = {};
        $.each(genData['osy-dt'], function (id, obj) {
            dtNames[obj['DtId']] = obj['Dt'];
        });
        return dtNames;
    }

    static DtbName(genData){
        let dtbNames = {};
        $.each(genData['osy-dtb'], function (id, obj) {
            dtbNames[obj['DtbId']] = obj['Dtb'];
        });
        return dtbNames;
    }

    static StgName(genData){
        let stgNames = {};
        $.each(genData['osy-stg'], function (id, obj) {
            stgNames[obj['StgId']] = obj['Stg'];
        });
        return stgNames;
    }

    static EmiName(genData){
        let emiNames = {};
        $.each(genData['osy-emis'], function (id, obj) {
            emiNames[obj['EmisId']] = obj['Emis'];
        });
        return emiNames;
    }

    static ScName(genData){
        let ScNames = {};
        $.each(genData['osy-scenarios'], function (id, obj) {
            ScNames[obj['ScenarioId']] = obj['Scenario'];
        });
        return ScNames;
    }

    static ConName(genData){
        let conNames = {};
        $.each(genData['osy-constraints'], function (id, obj) {
            conNames[obj.ConId] = obj.Con;
        });
        return conNames;
    }

    static ParamName(parameters){
        let ParamName = {};
        $.each(parameters, function (id, obj) {
            ParamName[obj.id] = obj.value;
        });
        return ParamName;
    }

    static AllParamName(parameters){
        let ParamName = {};
        $.each(parameters, function (group, array) {
            ParamName[group] = {};
            $.each(array, function (id, obj) {
                //ParamName[group][obj.id] = obj.value;
                ParamName[group][obj.id] = obj.value ?? obj.Indicator;
            });
        });
        return ParamName;
    }

    static getParamData(parameters){
        let ParamName = {};
        $.each(parameters, function (group, array) {
            ParamName[group] = {};
            $.each(array, function (id, obj) {
                ParamName[group][obj.id] = obj;
            });
        });
        return ParamName;
    }

    // static Timeslices(genData){
    //     let ts = [];
    //     let ns = parseInt(genData['osy-ns'])
    //     let nd = parseInt(genData['osy-dt'])

    //     for (let i = 1; i <= ns; i++) {
    //         for (let j = 1; j <= nd; j++) {
    //             ts.push('S'+i.toString()+j.toString())
    //         }
    //     }
    //     return ts;
    // }

    static Mods(genData){
        let mods = [];
        let mo = parseInt(genData['osy-mo'])

        for (let j = 1; j <= mo; j++) {
            mods.push(j)
        }
        return mods;
    }

    /////////////////////////////////////////////////IAR OAR EAR
    static activityTechs(techs){
        let ActivityTechs = {};
        ActivityTechs['IAR'] = [];
        ActivityTechs['OAR'] = [];
        $.each(techs, function (id, obj) {
            if (obj.IAR.length != 0 ) {
                ActivityTechs['IAR'].push(obj)
            }
            if ( obj.OAR.length != 0) {
                ActivityTechs['OAR'].push(obj)
            }
        });
        return ActivityTechs;
    }

    static getAllActivityTechs(techs){
        let ActivityTechs = [];
        let tmp = {};
        $.each(techs, function (id, obj) {
            if (obj.IAR.length != 0 || obj.OAR.length != 0) {
                if (!(obj.TechId in tmp)){
                    tmp[obj.TechId] = obj.Tech;
                    let chunk = {};
                    chunk['TechId'] = obj.TechId;
                    chunk['Tech'] = obj.Tech;
                    ActivityTechs.push(chunk)
                }  
            }
        });
        return ActivityTechs;
    }

    static getAllActivityTechsSankey(techs, techSelect, TechNames){
        let index = 0;
        let ActivityTechs = {};
        ActivityTechs['ddlTechs'] = [];
        ActivityTechs['label'] = [];
        ActivityTechs['color'] = [];
        ActivityTechs['labelIndex'] = {};

        ActivityTechs['actIAR'] = {};
        ActivityTechs['actOAR'] = {};
        let tmp = {};
        $.each(techs, function (id, obj) {
            if (obj.IAR.length != 0 || obj.OAR.length != 0) {
                if (!(obj.TechId in tmp)){
                    tmp[obj.TechId] = obj.Tech;
                    let chunk = {};
                    chunk['TechId'] = obj.TechId;
                    chunk['Tech'] = obj.Tech;
                    ActivityTechs['ddlTechs'].push(chunk)
                } 
                if (typeof ActivityTechs['labelIndex'][obj.TechId] === "undefined" ){
                    if (techSelect == null){
                        ActivityTechs['labelIndex'][obj.TechId] = index;
                        ActivityTechs['label'].push(TechNames[obj.TechId]);
                        index++;
                        ActivityTechs['color'].push('#3a3f51');
                    }else{
                        if(techSelect.includes(obj.TechId)){
                            ActivityTechs['labelIndex'][obj.TechId] = index;
                            ActivityTechs['label'].push(TechNames[obj.TechId]);
                            index++;
                            ActivityTechs['color'].push('#3a3f51');
                        }
                    }
                } 
            }

            if (obj.IAR.length != 0 ) {
                $.each(obj.IAR, function (i, cIarId) {
                    if (typeof ActivityTechs['actIAR'][cIarId] === "undefined") {
                        ActivityTechs['actIAR'][cIarId] = [];
                    }
                    if (techSelect == null){
                        ActivityTechs['actIAR'][cIarId].push(obj.TechId)
                    }else{
                        if(techSelect.includes(obj.TechId)){
                            ActivityTechs['actIAR'][cIarId].push(obj.TechId)
                        }
                    }
                })
            }
            if (obj.OAR.length != 0 ) {
                $.each(obj.OAR, function (i, cIarId) {
                    if (typeof ActivityTechs['actOAR'][cIarId] === "undefined") {
                        ActivityTechs['actOAR'][cIarId] = [];
                    }
                    if (techSelect == null){
                        ActivityTechs['actOAR'][cIarId].push(obj.TechId)
                    }else{
                        if(techSelect.includes(obj.TechId)){
                            ActivityTechs['actOAR'][cIarId].push(obj.TechId)
                        }
                    }
                    
                })
            }
        });
        return ActivityTechs;
    }

    static activityComms(genData){
        let ActivityComms = {};
        ActivityComms['IAR'] = {};
        ActivityComms['OAR'] = {};
        let techs = genData['osy-tech'];
        let comms = genData['osy-comm'];

        $.each(techs, function (idT, objT) {
            if (objT.IAR.length != 0 ) {
                ActivityComms['IAR'][objT.TechId] = [];
                $.each(comms, function (idC, objC) {
                    if(objT.IAR.includes(objC.CommId)){
                        ActivityComms['IAR'][objT.TechId].push(objC);
                    }
                });
            }
            if ( objT.OAR.length != 0) {
                ActivityComms['OAR'][objT.TechId] = [];
                $.each(comms, function (idC, objC) {
                    if(objT.OAR.includes(objC.CommId)){
                      
                        ActivityComms['OAR'][objT.TechId].push(objC);
                    }
                });
            }
        });
        return ActivityComms;
    }

    //////////////////////////////////////////////////RES DATA
    static getDemandComms(RYCdata, years){
        let demandComms = [];
        //console.log('years ', years)
        $.each(RYCdata, function (param, obj) {
           
            if(param == 'AAD' || param == 'SAD'){
                $.each(obj, function (sc, array) {
                    //console.log('param ', param, ' sc ', sc)
                    $.each(array, function (id, objC) {
                        $.each(years, function (i, year) {
      
                            //console.log(i, year)
                            //console.log('objC[year] ',objC[year])
                            if(objC[year] != 0 && objC[year]!=null){
                                // if(param =='SAD'){
                                //     console.log(objC.CommId, year)
                                //     console.log('objC[year] ',objC[year])
                                // }
                                if(!demandComms.includes(objC.CommId)){
                                    demandComms.push(objC.CommId);
                                }
                                return;
                            }
                        });
                    });
                });
            }
        });
        return demandComms;
    }

    static RESData(genData, demandComms){
        let techs = genData['osy-tech'];
        let comms = genData['osy-comm'];

        let RES = {};
        RES.Techs = [];
        RES.Data = {};
        RES.Data['IAR'] = {};
        RES.Data['OAR'] = {};

        let arrays = {};
        arrays['IAR'] = [];
        arrays['OAR'] = [];

        RES.Techs.push({'TechId': 'DS', 'Tech': 'Missing Source Technology', 'TechDesc': 'Missing Source Technology', '$checked': true});
        RES.Techs.push({'TechId': 'DT', 'Tech': 'Missing Target Technology', 'TechDesc': 'Missing Target Technology', '$checked': true});
        RES.Techs.push({'TechId': 'FD', 'Tech': 'Final demand', 'TechDesc': 'Final demand', '$checked': true});

        $.each(techs, function (idT, objT) {
            //dio za tehnlogije
            if (objT.IAR.length != 0 || objT.OAR.length != 0){
                RES.Techs.push({'TechId': objT.TechId, 'Tech': objT.Tech, 'TechDesc': objT.Desc, '$checked': true});
            }
            if (objT.IAR.length != 0 ) {
                RES.Data['IAR'][objT.TechId] = [];
                $.each(comms, function (idC, objC) {
                    if(objT.IAR.includes(objC.CommId)){
                        RES.Data['IAR'][objT.TechId].push(objC.CommId);
                        if(!arrays.IAR.includes(objC.CommId)){
                            arrays.IAR.push(objC.CommId);
                        }
                    }
                });
            }
            if ( objT.OAR.length != 0) {
                RES.Data['OAR'][objT.TechId] = [];
                $.each(comms, function (idC, objC) {
                    if(objT.OAR.includes(objC.CommId)){  
                        RES.Data['OAR'][objT.TechId].push(objC.CommId);
                        if(!arrays.OAR.includes(objC.CommId)){
                            arrays.OAR.push(objC.CommId);
                        }
                    }
                });
            }
        });

        //SINGLES
        RES.Singles = {};
        RES.Singles['IAR'] = [];
        RES.Singles['OAR'] = [];
        RES.Singles['FD'] = [];
       // RES.Data['IAR']['DS'] = [];
        //RES.Data['OAR']['DT'] = [];
        $.each(arrays.IAR, function (id, iarComm) {
            if(!arrays.OAR.includes(iarComm)){
                //RES.Data['IAR']['DS'].push(iarComm);
                RES.Singles['IAR'].push(iarComm)
            }
        });


        RES.Singles['FD'] = demandComms;
        $.each(arrays.OAR, function (id, oarComm) {
            if(!arrays.IAR.includes(oarComm)){
                //RES.Data['OAR']['DT'].push(oarComm);

                //ako Singles nisu u FD onda idu u Singles OAR
                //Ako Sinlges jesu u FD onda idu u FD, pored toga svi koji su u FD treba da ostanu tu
                // if(demandComms.includes(oarComm)){
                //     RES.Singles['FD'].push(oarComm)
                // }
                // else{
                //     RES.Singles['OAR'].push(oarComm)
                // }

                if(!demandComms.includes(oarComm)){
                    RES.Singles['OAR'].push(oarComm);
                }
            }
        });
        return RES;
    }

    // static activityCommsArray(genData){
    //     let ActivityComms = {};

    //     let techs = genData['osy-tech'];
    //     let comms = genData['osy-comm'];

    //     ActivityComms['IAR'] = [];
    //     ActivityComms['OAR'] = [];
    //     $.each(techs, function (idT, objT) {
    //         if (objT.IAR.length != 0 ) {  
    //             $.each(comms, function (idC, objC) {
    //                 if(objT.IAR.includes(objC.CommId)){
    //                     if(!ActivityComms.IAR.includes(objC.CommId)){
    //                         ActivityComms['IAR'].push(objC.CommId);
    //                     }
                        
    //                 }
    //             });
    //         }
    //         if ( objT.OAR.length != 0) {  
    //             $.each(comms, function (idC, objC) {
    //                 if(objT.OAR.includes(objC.CommId)){
    //                     if(!ActivityComms.OAR.includes(objC.CommId)){
    //                         ActivityComms['OAR'].push(objC.CommId);
    //                     }
    //                 }
    //             });
    //         }
    //     });
    //     return ActivityComms;
    // }

    // static RESSingles(genData){
    //     let activityCommsarray = DataModel.activityCommsArray(genData);
    //     let Singles = {};
    //     Singles['IAR'] = [];
    //     Singles['OAR'] = [];
    //     $.each(activityCommsarray.IAR, function (id, iarComm) {
    //         if(!activityCommsarray.OAR.includes(iarComm)){
    //             Singles['IAR'].push(iarComm)
    //         }
    //     });
    //     $.each(activityCommsarray.OAR, function (id, oarComm) {
    //         if(!activityCommsarray.IAR.includes(oarComm)){
    //             Singles['OAR'].push(oarComm)
    //         }
    //     });
    //     return Singles;
    // }

    //////////////////////////////////////////INCR ITCR
    static inputCapTechs(techs){
        let ActivityTechs = {};
        ActivityTechs['INCR'] = [];
        ActivityTechs['ITCR'] = [];
        $.each(techs, function (id, obj) {
            if (obj.INCR.length != 0 ) {
                ActivityTechs['INCR'].push(obj)
            }
            if ( obj.ITCR.length != 0) {
                ActivityTechs['ITCR'].push(obj)
            }
        });
        return ActivityTechs;
    }

    static inputCapComms(genData){
        let ActivityComms = {};
        ActivityComms['INCR'] = {};
        ActivityComms['ITCR'] = {};
        let techs = genData['osy-tech'];
        let comms = genData['osy-comm'];

        $.each(techs, function (idT, objT) {
            if (objT.INCR.length != 0 ) {
                ActivityComms['INCR'][objT.TechId] = [];
                $.each(comms, function (idC, objC) {
                    if(objT.INCR.includes(objC.CommId)){
                        ActivityComms['INCR'][objT.TechId].push(objC);
                    }
                });
            }
            if ( objT.ITCR.length != 0) {
                ActivityComms['ITCR'][objT.TechId] = [];
                $.each(comms, function (idC, objC) {
                    if(objT.ITCR.includes(objC.CommId)){
                      
                        ActivityComms['ITCR'][objT.TechId].push(objC);
                    }
                });
            }
        });
        return ActivityComms;
    }

    static emissionTechs(techs){
        let ActivityEmis = []
        $.each(techs, function (id, obj) {
            if (obj.EAR.length != 0 ) {
                ActivityEmis.push(obj);
            }
        });
        return ActivityEmis;
    }

    static activityEmis(genData){
        let ActivityEmis = {};
        ActivityEmis = {};
        let techs = genData['osy-tech'];
        let emis = genData['osy-emis'];

        $.each(techs, function (idT, objT) {
            if (objT.EAR.length != 0 ) {
                ActivityEmis[objT.TechId] = [];
                $.each(emis, function (idC, objE) {
                    if(objT.EAR.includes(objE.EmisId)){
                        ActivityEmis[objT.TechId].push(objE);
                    }
                });
            }
        });
        return ActivityEmis;
    }

    static constraintsCM(constraints){
        let constraintsCM = []
        $.each(constraints, function (id, obj) {
            if (obj.CM.length != 0 ) {
                constraintsCM.push(obj);
            }
        });
        return constraintsCM;
    }

    static constraintTechs(genData){
        let ConstraintTechs = {};
        let cons = genData['osy-constraints'];
        let techs = genData['osy-tech'];

        $.each(cons, function (id, con) {
            if (con.CM.length != 0 ) {
                ConstraintTechs[con.ConId] = [];
                $.each(techs, function (idT, obj) {
                    if(con.CM.includes(obj.TechId)){
                        ConstraintTechs[con.ConId].push(obj);
                    }
                });
            }
        });
        return ConstraintTechs;
    }

    static getCaserunByScenario(genData, resData){
        let scenarios = genData["osy-scenarios"];
        let caseruns = resData["osy-cases"];
        let csbysc = {};
        $.each(scenarios, function (i, objSc) {
            csbysc[objSc.ScenarioId] = [];
            if (caseruns.length != 0) {
                $.each(caseruns, function (j, objCs) {
                    $.each(objCs.Scenarios, function (k, objCsSc) {
                        if(objCsSc.Active == true && objSc.ScenarioId == objCsSc.ScenarioId){
                            csbysc[objSc.ScenarioId].push(objCs.Case)
                        }
                    });
                });
            }
        });
        return csbysc;
    }

    // Each group has three projections: <group>() indexes rows by entity IDs,
    // <group>grid() adds labels/units, and <group>chart() rearranges series.
    // Clone first: the projections remove ID fields or add display metadata.
    static R(Rdata){
        let R = {};
        const cloneData = JSON.parse(JSON.stringify(Rdata));
        $.each(cloneData, function (param, obj1) {
            R[param] = {};
            $.each(obj1, function (sc, array) {
                R[param][sc] = {};
                $.each(array, function (id, obj) { 
                    R[param][sc] = obj
                });
            });
        });
        return R;
    }

    static Rgrid(genData, Rdata, PARAMETERS){
        // let scName = this.ScName(genData);
        let scData = this.getScData(genData);
        let paramName = this.ParamName(PARAMETERS['R']);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        const cloneData = JSON.parse(JSON.stringify(Rdata));
        let Rgrid = {};
        $.each(cloneData, function (param, paramObj) {
            Rgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ParamId'] = param;
                    obj['Param'] = paramName[param];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['R'][param]['unitRule'];
                    let data = unitData['R'][param];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    Rgrid[param].push(obj);
                }); 
            });
        });
        return Rgrid;
    }

    static Rchart(genData, Rdata){
        let Rchart = {};
        let data = this.R(Rdata);
        $.each(Rdata, function (param, obj1) {
            Rchart[param] = [];
            let chunk = {};
            chunk['value'] = param;
            $.each(genData['osy-scenarios'], function (idS, sc) {
                if (typeof data[param][sc.ScenarioId]['value'] !== "undefined" ){
                    chunk[sc.ScenarioId] = data[param][sc.ScenarioId]['value'];
                }
            });
            Rchart[param].push(chunk);             
        });
        return Rchart;
    }

    static RY(RYdata){
        let RY = {};
        const cloneData = JSON.parse(JSON.stringify(RYdata));
        $.each(cloneData, function (param, obj1) {
            RY[param] = {};
            $.each(obj1, function (sc, array) {
                RY[param][sc] = {};
                $.each(array, function (id, obj) {
                    RY[param][sc] = obj
                });
            });
        });
        return RY;
    }

    static RYgrid(genData, RYdata, PARAMETERS){
        // let scName = this.ScName(genData);
        let scData = this.getScData(genData);
        let paramName = this.ParamName(PARAMETERS['RY']);
        const cloneData = JSON.parse(JSON.stringify(RYdata));
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let RYgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ParamId'] = param;
                    obj['Param'] = paramName[param];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RY'][param]['unitRule'];
                    let data = unitData['RY'][param];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYgrid[param].push(obj);
                }); 
            });
        });
        return RYgrid;
    }

    static RYchart(genData, RYdata){
        let RYchart = {};
        let RY = this.RY(RYdata);

        $.each(RY, function (param, array) {
            let chartData = [];
            $.each(genData['osy-years'], function (idY, year) { 
                let chunk = {};
                chunk['Year'] = year;
                $.each(genData['osy-scenarios'], function (idS, sc) {
                    chunk[sc.ScenarioId] = RY[param][sc.ScenarioId][year];
                });
                chartData.push(chunk);
            });
            RYchart[param] = chartData; 
        });
        return RYchart;
    }

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

    static RTgrid(genData, RTdata, PARAMETERS){
        // let scName = this.ScName(genData);
        let scData = this.getScData(genData);
        let paramName = this.ParamName(PARAMETERS['RT']);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        const cloneData = JSON.parse(JSON.stringify(RTdata));
        let RTgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RTgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ParamId'] = param;
                    obj['Param'] = paramName[param];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    $.each(genData['osy-tech'], function (id, tech) {
                        let rule = paramById['RT'][param]['unitRule'];
                        let data = unitData['RT'][param][tech.TechId];
                        obj[tech.TechId+'_UnitId'] = jsonLogic.apply(rule, data);
                    });
                    RTgrid[param].push(obj);
                }); 
            });
        });
        return RTgrid;
    }

    static RTchart(genData, RTdata){
        let techName = this.TechName(genData);
        let RTchart = {};
        //RYTdata[VC] = [{tech, Sc,2000, 2020...}]
        let data = this.RT(RTdata);
        $.each(RTdata, function (param, obj1) {
            RTchart[param] = [];
            $.each(genData['osy-tech'], function (idT, tech) {
                let chunk = {};
                chunk['TechId'] = tech.TechId;
                chunk['Tech'] = techName[tech.TechId];
                $.each(genData['osy-scenarios'], function (idS, sc) {
                    if (typeof data[param][sc.ScenarioId][tech.TechId] !== "undefined" ){
                        chunk[sc.ScenarioId] = data[param][sc.ScenarioId][tech.TechId];
                    }
                });
                RTchart[param].push(chunk);
            });                
        });
        return RTchart;
    }

    static RS(RSdata){
        let RS = {};
        const cloneData = JSON.parse(JSON.stringify(RSdata));
        $.each(cloneData, function (param, obj1) {
            RS[param] = {};
            $.each(obj1, function (sc, array) {
                RS[param][sc] = {};
                $.each(array, function (id, obj) { 
                    RS[param][sc] = obj
                });
            });
        });
        return RS;
    }

    static RSgrid(genData, RSdata, PARAMETERS){
        // let scName = this.ScName(genData);
        let scData = this.getScData(genData);
        let paramName = this.ParamName(PARAMETERS['RS']);
        let unitData = this.getUnitData(genData, PARAMETERS);
        //console.log('unitData ', unitData)
        let paramById = this.getParamById(PARAMETERS);
        //console.log('paramById ', paramById)
        const cloneData = JSON.parse(JSON.stringify(RSdata));
        let RSgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RSgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ParamId'] = param;
                    obj['Param'] = paramName[param];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    $.each(genData['osy-stg'], function (id, stg) {
                        let rule = paramById['RS'][param]['unitRule'];
                        let data = unitData['RS'][param][stg.StgId];
                        obj[stg.StgId+'_UnitId'] = jsonLogic.apply(rule, data);
                    });
                    RSgrid[param].push(obj);
                }); 
            });
        });
        return RSgrid;
    }

    static RSchart(genData, RSdata){
        let stgName = this.StgName(genData);
        let RSchart = {};
        let data = this.RS(RSdata);
        $.each(RSdata, function (param, obj1) {
            RSchart[param] = [];
            $.each(genData['osy-stg'], function (idT, stg) {
                let chunk = {};
                chunk['StgId'] = stg.StgId;
                chunk['Stg'] = stgName[stg.StgId];
                $.each(genData['osy-scenarios'], function (idS, sc) {
                    if (typeof data[param][sc.ScenarioId][stg.StgId] !== "undefined" ){
                        chunk[sc.ScenarioId] = data[param][sc.ScenarioId][stg.StgId];
                    }
                });
                RSchart[param].push(chunk);
            });                
        });
        return RSchart;
    }

    static RE(REdata){
        let RE = {};
        const cloneData = JSON.parse(JSON.stringify(REdata));
        $.each(cloneData, function (param, obj1) {
            RE[param] = {};
            $.each(obj1, function (sc, array) {
                RE[param][sc] = {};
                $.each(array, function (id, obj) { 
                    RE[param][sc] = obj
                });
            });
        });
        return RE;
    }

    static REgrid(genData, REdata, PARAMETERS){
        //let scName = this.ScName(genData);
        let scData = this.getScData(genData);
        let paramName = this.ParamName(PARAMETERS['RE']);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        const cloneData = JSON.parse(JSON.stringify(REdata));
        let REgrid = {};
        $.each(cloneData, function (param, paramObj) {
            REgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ParamId'] = param;
                    obj['Param'] = paramName[param];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    $.each(genData['osy-emis'], function (id, emi) {
                        let rule = paramById['RE'][param]['unitRule'];
                        let data = unitData['RE'][param][emi.EmisId];
                        obj[emi.EmisId+'_UnitId'] = jsonLogic.apply(rule, data);
                    });
                    REgrid[param].push(obj);
                }); 
            });
        });
        return REgrid;
    }

    static REchart(genData, REdata){
        let emiName = this.EmiName(genData);
        let REchart = {};
        //RYTdata[VC] = [{tech, Sc,2000, 2020...}]
        let data = this.RE(REdata);
        $.each(REdata, function (param, obj1) {
            REchart[param] = [];
            $.each(genData['osy-emis'], function (idT, emi) {
                let chunk = {};
                chunk['EmiId'] = emi.EmisId;
                chunk['Emi'] = emiName[emi.EmisId];
                $.each(genData['osy-scenarios'], function (idS, sc) {
                    if (typeof data[param][sc.ScenarioId][emi.EmisId] !== "undefined" ){
                        chunk[sc.ScenarioId] = data[param][sc.ScenarioId][emi.EmisId];
                    }
                });
                REchart[param].push(chunk);
            });                
        });
        return REchart;
    }

    static RYT(RYTdata){
        let RYT = {};
        const cloneData = JSON.parse(JSON.stringify(RYTdata));
        $.each(cloneData, function (param, obj1) {
            RYT[param] = {};
            $.each(obj1, function (sc, array) {
                RYT[param][sc] = {};
                $.each(array, function (id, obj) {
                    RYT[param][sc][obj.TechId] = obj
                    delete obj.TechId;
                    delete obj.Tech;
                    delete obj.ScId;
                    delete obj.Sc;
                });
            });
        });
        return RYT;
    }

    static RYTgrid(genData, RYTdata, PARAMETERS){
        // let techName = this.TechName(genData);
        let techData = this.getTechData(genData);
        // let scName = this.ScName(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);

        const cloneData = JSON.parse(JSON.stringify(RYTdata));
        let RYTgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYTgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYT'][param]['unitRule'];
                    let data = unitData['RYT'][param][obj.TechId];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTgrid[param].push(obj);
                }); 
            });
        });
        return RYTgrid;
    }

    static RYTchart(genData, RYTdata){
        let RYTchart = {};
        //RYTdata[VC] = [{tech, Sc,2000, 2020...}]
        let data = this.RYT(RYTdata);
        $.each(RYTdata, function (param, obj1) {
            let chartData = {};
            $.each(genData['osy-years'], function (idY, year) { 
                $.each(genData['osy-tech'], function (idT, tech) {
                    let chunk = {};
                    chunk['Year'] = year;
                    if(!chartData[tech.TechId]){ chartData[tech.TechId] = []; }
                    $.each(genData['osy-scenarios'], function (idS, sc) {
                        if (typeof data[param][sc.ScenarioId][tech.TechId] !== "undefined" ){
                            chunk[sc.ScenarioId] = data[param][sc.ScenarioId][tech.TechId][year];
                        }
                    });
                    chartData[tech.TechId].push(chunk);
                });                
            });
            RYTchart[param] = chartData; 
        });
        return RYTchart;
    }

    static RYS(RYSdata){
        let RYS = {};
        const cloneData = JSON.parse(JSON.stringify(RYSdata));
        $.each(cloneData, function (param, obj1) {
            RYS[param] = {};
            $.each(obj1, function (sc, array) {
                RYS[param][sc] = {};
                $.each(array, function (id, obj) {
                    RYS[param][sc][obj.StgId] = obj
                    delete obj.StgId;
                    delete obj.Stg;
                    delete obj.ScId;
                    delete obj.Sc;
                });
            });
        });
        return RYS;
    }

    static RYSgrid(genData, RYSdata, PARAMETERS){
        let stgData = this.getStgData(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);

        //console.log('unitData grid ', unitData)

        const cloneData = JSON.parse(JSON.stringify(RYSdata));
        let RYSgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYSgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['Stg'] = stgData[obj.StgId]['Stg'];
                    obj['StgDesc'] = stgData[obj.StgId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYS'][param]['unitRule'];
                    let data = unitData['RYS'][param][obj.StgId];
                    // console.log('rule ', rule)
                    // console.log('data ', data)
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    //console.log('obj[UnitId ', obj['UnitId'] )
                    RYSgrid[param].push(obj);
                }); 
            });
        });
        return RYSgrid;
    }

    static RYTM(RYTMdata){
        let RYTM = {};
        const cloneData = JSON.parse(JSON.stringify(RYTMdata));
        $.each(cloneData, function (param, obj1) {
            RYTM[param] = {};
            $.each(obj1, function (sc, array) {
                RYTM[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTM[param][sc][obj.TechId]){ RYTM[param][sc][obj.TechId] = {}; }
                    RYTM[param][sc][obj.TechId][obj.MoId] = obj;
                    delete obj.TechId;
                    delete obj.MoId;                    
                });
            });
        });
        return RYTM;
    }

    static RYTMgrid(genData, RYTMdata, PARAMETERS){
        // let techName = this.TechName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let scData = this.getScData(genData);

        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYTMdata));
        let RYTMgrid = {};

        $.each(cloneData, function (param, obj) {
            RYTMgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    // obj['Tech'] = techName[obj['TechId']];
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYTM'][param]['unitRule'];
                    let data = unitData['RYTM'][param][obj.TechId];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTMgrid[param].push(obj);
                });
            });
        });
        return RYTMgrid;
    }

    static RYTMchart(genData, RYTMdata){
        let RYTM = this.RYTM(RYTMdata);
        let mods = this.Mods(genData);
        let RYTMchart = {};

        $.each(RYTMdata, function (param, obj1) {
            let chartData = {}
            $.each(genData['osy-tech'], function (idT, tech) {     
                chartData[tech.TechId] = {};
                $.each(mods, function (idS, mo) {   
                    chartData[tech.TechId][mo] = []; 
                    $.each(genData['osy-years'], function (idY, year) {                  
                        let chunk = {};
                        chunk['Year'] = year;
                        $.each(genData['osy-scenarios'], function (idS, sc) {
                            chunk[sc.ScenarioId] = RYTM[param][sc.ScenarioId][tech.TechId][mo][year];
                        });
                        chartData[tech.TechId][mo].push(chunk);
                    });              
                });
            }); 
            RYTMchart[param] = chartData;    
        });       
        return RYTMchart;
    }

    static RYC(RYCdata){
        let RYC = {};
        const cloneData = JSON.parse(JSON.stringify(RYCdata));
        $.each(cloneData, function (param, obj1) {
            RYC[param] = {};
            $.each(obj1, function (sc, array) {
                RYC[param][sc] = {};
                $.each(array, function (id, obj) {
                    RYC[param][sc][obj.CommId] = obj
                    delete obj.CommId;
                    delete obj.Comm;
                    delete obj.ScId;
                    delete obj.Sc;
                });
            });
        });
        return RYC;
    }

    static RYCgrid(genData, RYCdata, PARAMETERS){
        // let commName = this.CommName(genData);
        // let scName = this.ScName(genData);
        let commData = this.getCommData(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYCdata));
        let RYCgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYCgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['Comm'] = commName[obj['CommId']];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    obj['Comm'] = commData[obj.CommId]['Comm'];
                    obj['CommDesc'] = commData[obj.CommId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYC'][param]['unitRule'];
                    let data = unitData['RYC'][param][obj.CommId];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYCgrid[param].push(obj);
                }); 
            });
        });
        return RYCgrid;
    }

    static RYCchart(genData, RYCdata){
        let RYCchart = {};
        let data = this.RYC(RYCdata);
        $.each(RYCdata, function (param, array) {
            let chartData = {};
            $.each(genData['osy-years'], function (idY, year) { 
                $.each(genData['osy-comm'], function (idC, comm) {
                    let chunk = {};
                    chunk['Year'] = year;
                    if(!chartData[comm.CommId]){ chartData[comm.CommId] = []; }
                    $.each(genData['osy-scenarios'], function (idS, sc) {
                         chunk[sc.ScenarioId] = data[param][sc.ScenarioId][comm.CommId][year];
                    });
                    chartData[comm.CommId].push(chunk);
                });
            });
            RYCchart[param] = chartData; 
            
        });
        return RYCchart;
    }

    static RYCn(RYCndata){
        let RYCn = {};
        const cloneData = JSON.parse(JSON.stringify(RYCndata));
        $.each(cloneData, function (param, obj1) {
            RYCn[param] = {};
            $.each(obj1, function (sc, array) {
                RYCn[param][sc] = {};
                $.each(array, function (id, obj) {
                    RYCn[param][sc][obj.ConId] = obj
                    delete obj.ConId;
                });
            });
        });
        return RYCn;
    }

    static RYCngrid(genData, RYCndata, PARAMETERS){
        // let conName = this.ConName(genData);
        // let scName = this.ScName(genData);

        let conData = this.getConData(genData);
        let scData = this.getScData(genData);

        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYCndata));
        let RYCngrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYCngrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['Con'] = conName[obj.ConId];
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];

                    obj['Con'] = conData[obj.ConId]['Con'];
                    obj['ConDesc'] = conData[obj.ConId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYCn'][param]['unitRule'];
                    let data = unitData['RYCn'][param][obj.ConId];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYCngrid[param].push(obj);
                }); 
            });
        });
        return RYCngrid;
    }

    static RYCnchart(genData, RYCndata){
        let RYCnchart = {};
        let data = this.RYCn(RYCndata);
        $.each(RYCndata, function (param, array) {
            let chartData = {};
            $.each(genData['osy-years'], function (idY, year) { 
                $.each(genData['osy-constraints'], function (idC, con) {
                    let chunk = {};
                    chunk['Year'] = year;
                    if(!chartData[con.ConId]){ chartData[con.ConId] = []; }
                    $.each(genData['osy-scenarios'], function (idS, sc) {
                         chunk[sc.ScenarioId] = data[param][sc.ScenarioId][con.ConId][year];
                    });
                    chartData[con.ConId].push(chunk);
                });
            });
            RYCnchart[param] = chartData; 
            
        });
        return RYCnchart;
    }

    static RYE(RYEdata){
        let RYE = {};
        const cloneData = JSON.parse(JSON.stringify(RYEdata));
        $.each(cloneData, function (param, obj1) {
            RYE[param] = {};
            $.each(obj1, function (sc, array) {
                RYE[param][sc] = {};
                $.each(array, function (id, obj) {
                    RYE[param][sc][obj.EmisId] = obj
                    delete obj.EmisId;
                    // delete obj.Emis;
                    // delete obj.ScId;
                    // delete obj.Sc;
                });
            });
        });
        return RYE;
    }

    static RYEgrid(genData, RYEdata, PARAMETERS){
        // let emiName = this.EmiName(genData);
        // let scName = this.ScName(genData);
        let emiData = this.getEmiData(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYEdata));
        let RYEgrid = {};
        $.each(cloneData, function (param, paramObj) {
            RYEgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['Emis'] = emiData[obj.EmisId]['Emis'];
                    obj['EmiDesc'] = emiData[obj.EmisId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYE'][param]['unitRule'];
                    let data = unitData['RYE'][param][obj.EmisId];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYEgrid[param].push(obj);
                }); 
            });
        });
        return RYEgrid;
    }

    static RYEchart(genData, RYEdata){
        let RYEchart = {};
        let data = this.RYE(RYEdata);
        $.each(RYEdata, function (param, array) {
            let chartData = {};
            $.each(genData['osy-years'], function (idY, year) { 
                $.each(genData['osy-emis'], function (idC, emi) {
                    let chunk = {};
                    chunk['Year'] = year;
                    if(!chartData[emi.EmisId]){ chartData[emi.EmisId] = []; }
                    $.each(genData['osy-scenarios'], function (idS, sc) {
                         chunk[sc.ScenarioId] = data[param][sc.ScenarioId][emi.EmisId][year];
                    });
                    chartData[emi.EmisId].push(chunk);
                });
            });
            RYEchart[param] = chartData; 
            
        });
        return RYEchart;
    }

    static RYTs(RYTsdata){
        let RYTs = {};
        const cloneData = JSON.parse(JSON.stringify(RYTsdata));
        $.each(cloneData, function (param, obj1) {
            RYTs[param] = {};
            $.each(obj1, function (sc, array) {
                RYTs[param][sc] = {};
                $.each(array, function (id, obj) {
                    RYTs[param][sc][obj['YearSplit']] = obj;
                    delete obj.YearSplit;
                });
            });
        });
        return RYTs;
    }

    static RYTsgrid(genData, RYTsdata){
        let scData = this.getScData(genData);
        let tsData = this.getTsData(genData);
        let cloneData = JSON.parse(JSON.stringify(RYTsdata));
        let RYTsgrid = {};

        //console.log('tsData ',tsData)
        $.each(cloneData, function (param, paramObj) {
            RYTsgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['TsId'] = obj.TsId;
                    obj['Ts'] = tsData[obj.TsId]['Ts'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    RYTsgrid[param].push(obj);
                }); 
            });
        });
        return RYTsgrid;
    }

    static RYDtbgrid(genData, RYDtbdata){
        let scData = this.getScData(genData);
        let dtbData = this.getDtbData(genData);
        let cloneData = JSON.parse(JSON.stringify(RYDtbdata));
        let RYDtbgrid = {};

        $.each(cloneData, function (param, paramObj) {
            RYDtbgrid[param] = [];
            $.each(paramObj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['DtbId'] = obj.DtbId;
                    obj['Dtb'] = dtbData[obj.DtbId]['Dtb'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    RYDtbgrid[param].push(obj);
                }); 
            });
        });
        return RYDtbgrid;
    }

    static RYSeDtgrid(genData, RYSeDtdata, PARAMETERS){
     
        let seData = this.getSeData(genData);
        let scData = this.getScData(genData);
        let dtData = this.getDtData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);


        let cloneData = JSON.parse(JSON.stringify(RYSeDtdata));
        let RYSeDtgrid = {};

        // console.log('unitData ',unitData)
        // console.log('cloneData ',cloneData)
        $.each(cloneData, function (param, obj) {
            RYSeDtgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    obj['Se'] = seData[obj.SeId]['Se'];
                    obj['SeDesc'] = seData[obj.SeId]['Desc'];

                    obj['Dt'] = dtData[obj.DtId]['Dt'];
                    let rule = paramById['RYSeDt'][param]['unitRule'];
                    let data = unitData['RYSeDt'][param];
                    obj['UnitId'] = jsonLogic.apply(rule, data);

                    RYSeDtgrid[param].push(obj);
                });
            });
        });
        return RYSeDtgrid;
    }

    static RYTschart(genData, RYTsdata){
        let RYTs = this.RYTs(RYTsdata);
        let RYTschart = {};
        $.each(RYTsdata, function (param, obj1) {
            let chartData = []
            $.each(obj1, function (sc, array) {        
                $.each(array, function (id, obj) {
                    //if(!chartData[obj.YearSplit]){ chartData[obj.YearSplit] = []; }
                    chartData[obj.YearSplit] = [];  
                    $.each(genData['osy-years'], function (idY, year) {                  
                        let chunk = {};
                        chunk['Year'] = year;
                        $.each(genData['osy-scenarios'], function (idS, sc) {
                            chunk[sc.ScenarioId] = RYTs[param][sc.ScenarioId][obj.YearSplit][year];
                        });
                        chartData[obj.YearSplit].push(chunk);
                    });              
                });
            }); 
            RYTschart[param] = chartData;    
        });       
        return RYTschart;
    }

    static RYTC(RYTCdata){
        let RYTC = {};
        const cloneData = JSON.parse(JSON.stringify(RYTCdata));
        $.each(cloneData, function (param, obj1) {
            RYTC[param] = {};
            $.each(obj1, function (sc, array) {
                RYTC[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTC[param][sc][obj.TechId]){ RYTC[param][sc][obj.TechId] = {}; }
                        RYTC[param][sc][obj.TechId][obj.CommId] = obj;
                        delete obj.TechId;
                        delete obj.CommId;   
                });
            });
        });
        return RYTC;
    }

    static RYTCgrid(genData, RYTCdata){
        // let techName = this.TechName(genData);
        // let commName = this.CommName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let commData = this.getCommData(genData);
        let scData = this.getScData(genData);

        let cloneData = JSON.parse(JSON.stringify(RYTCdata));
        let RYTCgrid = {};

        $.each(cloneData, function (param, obj) {
            RYTCgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    // obj['Tech'] = techName[obj['TechId']];
                    // obj['Comm'] = commName[obj['CommId']];
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    obj['Comm'] = commData[obj.CommId]['Comm'];
                    obj['CommDesc'] = commData[obj.CommId]['Desc'];
                    RYTCgrid[param].push(obj);
                });
            });
        });
        return RYTCgrid;
    }

    static RYTCchart(genData, RYTCdata){
        let RYTCchart = {};
        let RYCT = this.RYTC(RYTCdata);
        $.each(RYTCdata, function (param, obj1) {
            RYTCchart[param] = {};
            $.each(obj1, function (sc, array) {
                if (array.length !== 0){
                    $.each(array, function (id, obj) {
                        if(!RYTCchart[param][obj.TechId]){ RYTCchart[param][obj.TechId] = {}; }
                        RYTCchart[param][obj.TechId][obj.CommId] =[]
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;
                            $.each(genData['osy-scenarios'], function (idS, sc) {
                                chunk[sc.ScenarioId] = RYCT[param][sc.ScenarioId][obj.TechId][obj.CommId][year];
                            });
                            RYTCchart[param][obj.TechId][obj.CommId].push(chunk);
                        });
                    });
                }
            });
        });
        return RYTCchart;
    }

    static RYTCM(RYTCMdata){
        // Source: [parameter][scenario] -> rows {TechId, CommId, MoId, <year>: value}.
        // Lookup: [parameter][scenario][technology][commodity][mode] -> year values.
        let RYTCM = {};
        const cloneData = JSON.parse(JSON.stringify(RYTCMdata));
        $.each(cloneData, function (param, obj1) {
            RYTCM[param] = {};
            $.each(obj1, function (sc, array) {
                RYTCM[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTCM[param][sc][obj.TechId]){ RYTCM[param][sc][obj.TechId] = {}; }
                    if(!RYTCM[param][sc][obj.TechId][obj.CommId]){ RYTCM[param][sc][obj.TechId][obj.CommId] = {}; }
                        RYTCM[param][sc][obj.TechId][obj.CommId][obj.MoId] = obj;
                        delete obj.TechId;
                        delete obj.CommId; 
                        delete obj.MoId;   
                });
            });
        });
        return RYTCM;
    }

    static RYTCMgrid(genData, RYTCMdata, PARAMETERS){
        // let techName = this.TechName(genData);
        // let commName = this.CommName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let commData = this.getCommData(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYTCMdata));
        let RYTCMgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTCMgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    // obj['Tech'] = techName[obj['TechId']];
                    // obj['Comm'] = commName[obj['CommId']];
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['Comm'] = commData[obj.CommId]['Comm'];
                    obj['CommDesc'] = commData[obj.CommId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYTCM'][param]['unitRule'];
                    let data1 = unitData['RYTCM'][param][obj.CommId];
                    let data2 = unitData['RYTCM'][param][obj.TechId];
                    const data = {...data1, ...data2};
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTCMgrid[param].push(obj);
                });
            });
        });
        return RYTCMgrid;
    }

    static RYTCMchart(genData, RYTCMdata){
        let RYTCMchart = {};
        let RYTCM = this.RYTCM(RYTCMdata);
        $.each(RYTCMdata, function (param, obj1) {
            RYTCMchart[param] = {};
            $.each(obj1, function (sc, array) {
                if (array.length !== 0){
                    $.each(array, function (id, obj) {
                        if(!RYTCMchart[param][obj.TechId]){ RYTCMchart[param][obj.TechId] = {}; }
                        if(!RYTCMchart[param][obj.TechId][obj.CommId]){ RYTCMchart[param][obj.TechId][obj.CommId] = {}; }
                        RYTCMchart[param][obj.TechId][obj.CommId][obj.MoId] =[]
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;
                            $.each(genData['osy-scenarios'], function (idS, sc) {
                                chunk[sc.ScenarioId] = RYTCM[param][sc.ScenarioId][obj.TechId][obj.CommId][obj.MoId][year];
                            });
                            RYTCMchart[param][obj.TechId][obj.CommId][obj.MoId].push(chunk);
                        });
                    });
                }
            });
        });
        return RYTCMchart;
    }

    static RTSM(RTSMdata){
        let RTSM = {};
        const cloneData = JSON.parse(JSON.stringify(RTSMdata));
        $.each(cloneData, function (param, obj1) {
            RTSM[param] = {};
            $.each(obj1, function (sc, array) {
                RYTSM[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RTSM[param][sc][obj.TechId]){ RTSM[param][sc][obj.TechId] = {}; }
                    if(!RTSM[param][sc][obj.TechId][obj.StgId]){ RTSM[param][sc][obj.TechId][obj.StgId] = {}; }
                        RTSM[param][sc][obj.TechId][obj.StgId][obj.MoId] = obj;
                        delete obj.TechId;
                        delete obj.StgId; 
                        delete obj.MoId;   
                });
            });
        });
        return RTSM;
    }

    static RTSMgrid(genData, RTSMdata, PARAMETERS){
        // let techName = this.TechName(genData);
        // let commName = this.CommName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let stgData = this.getStgData(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RTSMdata));
        //console.log('cloneData ', cloneData)

        let RTSMgrid = {};
        $.each(cloneData, function (param, obj) {
            RTSMgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['Stg'] = stgData[obj.StgId]['Stg'];
                    obj['StgDesc'] = stgData[obj.StgId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RTSM'][param]['unitRule'];
                    let data1 = unitData['RTSM'][param][obj.StgId];
                    let data2 = unitData['RTSM'][param][obj.TechId];
                    const data = {...data1, ...data2};
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RTSMgrid[param].push(obj);
                });
            });
        });
        return RTSMgrid;
    }

    static RYTSM(RYTSMdata){
        let RYTSM = {};
        const cloneData = JSON.parse(JSON.stringify(RYTSMdata));
        $.each(cloneData, function (param, obj1) {
            RYTSM[param] = {};
            $.each(obj1, function (sc, array) {
                RYTSM[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTSM[param][sc][obj.TechId]){ RYTSM[param][sc][obj.TechId] = {}; }
                    if(!RYTSM[param][sc][obj.TechId][obj.StgId]){ RYTSM[param][sc][obj.TechId][obj.StgId] = {}; }
                        RYTSM[param][sc][obj.TechId][obj.StgId][obj.MoId] = obj;
                        delete obj.TechId;
                        delete obj.StgId; 
                        delete obj.MoId;   
                });
            });
        });
        return RYTSM;
    }

    static RYTSMgrid(genData, RYTSMdata, PARAMETERS){
        // let techName = this.TechName(genData);
        // let commName = this.CommName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let stgData = this.getStgData(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYTSMdata));
        //console.log('cloneData ', cloneData)
        let RYTSMgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTSMgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['Stg'] = stgData[obj.StgId]['Stg'];
                    obj['StgDesc'] = stgData[obj.StgId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYTSM'][param]['unitRule'];
                    let data1 = unitData['RYTSM'][param][obj.StgId];
                    let data2 = unitData['RYTSM'][param][obj.TechId];
                    const data = {...data1, ...data2};
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTSMgrid[param].push(obj);
                });
            });
        });
        return RYTSMgrid;
    }

    static RYTE(RYTEdata){
        let RYTE = {};
        const cloneData = JSON.parse(JSON.stringify(RYTEdata));
        $.each(cloneData, function (param, obj1) {
            RYTE[param] = {};
            $.each(obj1, function (sc, array) {
                RYTE[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTE[param][sc][obj.TechId]){ RYTE[param][sc][obj.TechId] = {}; }
                        RYTE[param][sc][obj.TechId][obj.EmisId] = obj;
                        delete obj.TechId;
                        delete obj.EmisId;   
                });
            });
        });
        return RYTE;
    }

    static RYTEgrid(genData, RYTEdata){
        // let techName = this.TechName(genData);
        // let emiName = this.EmiName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let emiData = this.getEmiData(genData);
        let scData = this.getScData(genData);
        let cloneData = JSON.parse(JSON.stringify(RYTEdata));
        let RYTEgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTEgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    // obj['Tech'] = techName[obj['TechId']];
                    // obj['Emis'] = emiName[obj['EmisId']];
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['Emis'] = emiData[obj.EmisId]['Emis'];
                    obj['EmiDesc'] = emiData[obj.EmisId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    RYTEgrid[param].push(obj);
                });
            });
        });
        return RYTEgrid;
    }

    static RYTEchart(genData, RYTEdata){
        let RYTEchart = {};
        let RYTE = this.RYTE(RYTEdata);
        $.each(RYTEdata, function (param, obj1) {
            RYTEchart[param] = {};
            $.each(obj1, function (sc, array) {
                if (array.length !== 0){
                    $.each(array, function (id, obj) {
                        if(!RYTEchart[param][obj.TechId]){ RYTEchart[param][obj.TechId] = {}; }
                        RYTEchart[param][obj.TechId][obj.EmisId] =[]
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;
                            $.each(genData['osy-scenarios'], function (idS, sc) {
                                chunk[sc.ScenarioId] = RYTE[param][sc.ScenarioId][obj.TechId][obj.EmisId][year];
                            });
                            RYTEchart[param][obj.TechId][obj.EmisId].push(chunk);
                        });
                    });
                }
            });
        });
        return RYTEchart;
    }

    static RYTCn(RYTCndata){
        let RYTCn = {};
        const cloneData = JSON.parse(JSON.stringify(RYTCndata));
        $.each(cloneData, function (param, obj1) {
            RYTCn[param] = {};
            $.each(obj1, function (sc, array) {
                RYTCn[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTCn[param][sc][obj.TechId]){ RYTCn[param][sc][obj.TechId] = {}; }
                        RYTCn[param][sc][obj.TechId][obj.ConId] = obj;
                        delete obj.TechId;
                        delete obj.ConId;   
                });
            });
        });
        return RYTCn;
    }

    static RYTCngrid(genData, RYTCndata){
        // let techName = this.TechName(genData);
        // let conName = this.ConName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let conData = this.getConData(genData);
        let scData = this.getScData(genData);
        let cloneData = JSON.parse(JSON.stringify(RYTCndata));
        let RYTCngrid = {};

        $.each(cloneData, function (param, obj) {
            RYTCngrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    // obj['Tech'] = techName[obj['TechId']];
                    // obj['Con'] = conName[obj['ConId']];
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['Con'] = conData[obj.ConId]['Con'];
                    obj['ConDesc'] = conData[obj.ConId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    RYTCngrid[param].push(obj);
                });
            });
        });
        return RYTCngrid;
    }

    static RYTCnchart(genData, RYTCndata){
        let RYTCnchart = {};
        let RYCTn = this.RYTCn(RYTCndata);
        $.each(RYTCndata, function (param, obj1) {
            RYTCnchart[param] = {};
            $.each(obj1, function (sc, array) {
                if (array.length !== 0){
                    $.each(array, function (id, obj) {
                        if(!RYTCnchart[param][obj.TechId]){ RYTCnchart[param][obj.TechId] = {}; }
                        RYTCnchart[param][obj.TechId][obj.ConId] =[]
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;
                            $.each(genData['osy-scenarios'], function (idS, sc) {
                                chunk[sc.ScenarioId] = RYCTn[param][sc.ScenarioId][obj.TechId][obj.ConId][year];
                            });
                            RYTCnchart[param][obj.TechId][obj.ConId].push(chunk);
                        });
                    });
                }
            });
        });
        return RYTCnchart;
    }

    static RYTEM(RYTEMdata){
        let RYTEM = {};
        const cloneData = JSON.parse(JSON.stringify(RYTEMdata));
        $.each(cloneData, function (param, obj1) {
            RYTEM[param] = {};
            $.each(obj1, function (sc, array) {
                RYTEM[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTEM[param][sc][obj.TechId]){ RYTEM[param][sc][obj.TechId] = {}; }
                    if(!RYTEM[param][sc][obj.TechId][obj.EmisId]){ RYTEM[param][sc][obj.TechId][obj.EmisId] = {}; }
                        RYTEM[param][sc][obj.TechId][obj.EmisId][obj.MoId] = obj;
                        delete obj.TechId;
                        delete obj.EmisId; 
                        delete obj.MoId;   
                });
            });
        });
        return RYTEM;
    }

    static RYTEMgrid(genData, RYTEMdata, PARAMETERS){
        // let techName = this.TechName(genData);
        // let emiName = this.EmiName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let emiData = this.getEmiData(genData);
        let scData = this.getScData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYTEMdata));
        let RYTEMgrid = {};
        $.each(cloneData, function (param, obj) {
            RYTEMgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    // obj['Tech'] = techName[obj['TechId']];
                    // obj['Emis'] = emiName[obj['EmisId']];
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['Emis'] = emiData[obj.EmisId]['Emis'];
                    obj['EmiDesc'] = emiData[obj.EmisId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    let rule = paramById['RYTEM'][param]['unitRule'];
                    let data1 = unitData['RYTEM'][param][obj.EmisId];
                    let data2 = unitData['RYTEM'][param][obj.TechId];
                    const data = {...data1, ...data2};
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYTEMgrid[param].push(obj);
                });
            });
        });
        return RYTEMgrid;
    }

    static RYTEMchart(genData, RYTEMdata){
        let RYTEMchart = {};
        let RYTEM = this.RYTEM(RYTEMdata);
        $.each(RYTEMdata, function (param, obj1) {
            RYTEMchart[param] = {};
            $.each(obj1, function (sc, array) {
                if (array.length !== 0){
                    $.each(array, function (id, obj) {
                        if(!RYTEMchart[param][obj.TechId]){ RYTEMchart[param][obj.TechId] = {}; }
                        if(!RYTEMchart[param][obj.TechId][obj.EmisId]){ RYTEMchart[param][obj.TechId][obj.EmisId] = {}; }
                        RYTEMchart[param][obj.TechId][obj.EmisId][obj.MoId] =[]
                        $.each(genData['osy-years'], function (idY, year) {
                            let chunk = {};
                            chunk['Year'] = year;
                            $.each(genData['osy-scenarios'], function (idS, sc) {
                                chunk[sc.ScenarioId] = RYTEM[param][sc.ScenarioId][obj.TechId][obj.EmisId][obj.MoId][year];
                            });
                            RYTEMchart[param][obj.TechId][obj.EmisId][obj.MoId].push(chunk);
                        });
                    });
                }
            });
        });
        return RYTEMchart;
    }

    static RYTTs(RYTTsdata){
        let RYTTs = {};
        const cloneData = JSON.parse(JSON.stringify(RYTTsdata));
        $.each(cloneData, function (param, obj1) {
            RYTTs[param] = {};
            $.each(obj1, function (sc, array) {
                RYTTs[param][sc] = {};
                $.each(array, function (id, obj) {
                    if(!RYTTs[param][sc][obj.TechId]){ RYTTs[param][sc][obj.TechId] = {}; }
                    RYTTs[param][sc][obj.TechId][obj.Timeslice] = obj;
                    delete obj.TechId;
                    delete obj.Timeslice;                    
                });
            });
        });
        return RYTTs;
    }

    static RYTTsgrid(genData, RYTTsdata){
        // let techName = this.TechName(genData);
        // let scName = this.ScName(genData);
        let techData = this.getTechData(genData);
        let tsData = this.getTsData(genData);
        let scData = this.getScData(genData);
        let cloneData = JSON.parse(JSON.stringify(RYTTsdata));
        let RYTTsgrid = {};

        $.each(cloneData, function (param, obj) {
            RYTTsgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    //obj['TsId'] = obj.TsId;
                    obj['Ts'] = tsData[obj.TsId]['Ts'];
                    obj['Tech'] = techData[obj.TechId]['Tech'];
                    obj['TechDesc'] = techData[obj.TechId]['Desc'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    RYTTsgrid[param].push(obj);
                });
            });
        });
        return RYTTsgrid;
    }

    static RYTTschart(genData, RYTTsdata){
        let RYTs = this.RYTTs(RYTTsdata);
        let timeslices = this.Timeslices(genData);
        let RYTTschart = {};

        $.each(RYTTsdata, function (param, obj1) {
            let chartData = {}
            $.each(genData['osy-tech'], function (idT, tech) {     
                chartData[tech.TechId] = {};
                $.each(timeslices, function (idS, ts) {   
                    chartData[tech.TechId][ts] = []; 
                    $.each(genData['osy-years'], function (idY, year) {                  
                        let chunk = {};
                        chunk['Year'] = year;
                        $.each(genData['osy-scenarios'], function (idS, sc) {
                            chunk[sc.ScenarioId] = RYTs[param][sc.ScenarioId][tech.TechId][ts][year];
                        });
                        chartData[tech.TechId][ts].push(chunk);
                    });              
                });
            }); 
            RYTTschart[param] = chartData;    
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
                    if(!RYCTs[param][sc][obj.CommId]){ RYCTs[param][sc][obj.CommId] = {}; }
                    RYCTs[param][sc][obj.CommId][obj.Timeslice] = obj;
                    delete obj.CommId;
                    delete obj.Timeslice; 
                });
            });
        });
        return RYCTs;
    }

    static RYCTsgrid(genData, RYCTsdata, PARAMETERS){
        // let commName = this.CommName(genData);
        // let scName = this.ScName(genData);
        let commData = this.getCommData(genData);
        let scData = this.getScData(genData);
        let tsData = this.getTsData(genData);
        let unitData = this.getUnitData(genData, PARAMETERS);
        let paramById = this.getParamById(PARAMETERS);
        let cloneData = JSON.parse(JSON.stringify(RYCTsdata));
        let RYCTsgrid = {};

        $.each(cloneData, function (param, obj) {
            RYCTsgrid[param] = [];
            $.each(obj, function (sc, array) {
                $.each(array, function (id, obj) {
                    // obj['ScId'] = sc;
                    // obj['Sc'] = scName[sc];
                    // obj['Comm'] = commName[obj.CommId];
                    obj['Comm'] = commData[obj.CommId]['Comm'];
                    obj['CommDesc'] = commData[obj.CommId]['Desc'];
                    obj['ScId'] = sc;
                    obj['Sc'] = scData[sc]['Scenario'];
                    obj['ScDesc'] = scData[sc]['Desc'];
                    obj['Ts'] = tsData[obj.TsId]['Ts'];
                    let rule = paramById['RYCTs'][param]['unitRule'];
                    let data = unitData['RYCTs'][param][obj.CommId];
                    obj['UnitId'] = jsonLogic.apply(rule, data);
                    RYCTsgrid[param].push(obj);
                });
            });
        });
        return RYCTsgrid;
    }

    static RYCTschart(genData, RYCTsdata){

        let RYCTs = this.RYCTs(RYCTsdata);
        let timeslices = this.Timeslices(genData);

        let RYCTschart = {};


        $.each(RYCTsdata, function (param, obj1) {
            let chartData = {}
            $.each(genData['osy-comm'], function (idT, comm) {     
                chartData[comm.CommId] = {};
                $.each(timeslices, function (idS, ts) {   
                    chartData[comm.CommId][ts] = []; 
                    $.each(genData['osy-years'], function (idY, year) {                  
                        let chunk = {};
                        chunk['Year'] = year;
                        $.each(genData['osy-scenarios'], function (idS, sc) {
                            chunk[sc.ScenarioId] = RYCTs[param][sc.ScenarioId][comm.CommId][ts][year];
                        });
                        chartData[comm.CommId][ts].push(chunk);
                    });              
                });
            }); 
            RYCTschart[param] = chartData;    
        }); 
        return RYCTschart;
    }
}
