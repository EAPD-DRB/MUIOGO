export class DefaultObj{
    static getId(type) {
        // Math.random should be unique because of its seeding algorithm.
        // Convert it to base 36 (numbers + letters), and grab the first 9 characters
        // after the decimal.
        return type+'_' + Math.random().toString(36).substr(2, 5);
    }
    static defaultSe(first=false, seCount=0){
        let id;
        if(first){
            id = 'SE_0';
        }else{
            id = this.getId('SE');
        }
        let defaultSe = [
            {
                "SeId": id,
                "Se":seCount+1,
                "Desc": "Default season"
            }
        ];
        return defaultSe;
    }

    static defaultDt(first=false, dtCount=0){
        let id;
        if(first){
            id = 'DT_0';
        }else{
            id = this.getId('DT');
        }
        let defaultDt = [
            {
                "DtId": id,
                "Dt":dtCount+1,
                "Desc": "Default day type"
            }
        ];
        return defaultDt;
    }

    static defaultDtb(first=false, dtbCount=0){
        let id;
        let idNumber;
        if(first){
            id = 'DTB_0';
        }else{
            id = this.getId('DTB');
        }
        let defaultDtb = [
            {
                "DtbId": id,
                "Dtb":dtbCount+1,
                "Desc": "Default dialy time bracket"
            }
        ];
        return defaultDtb;
    }

    static defaultTs(first=false){
        let id;
        if(first){
            id = 'TS_0';
        }else{
            id = this.getId('TS');
        }
        let emptyArray = [];
        let defaultTs = [
            {
                "TsId": id,
                "Ts":id,
                "Desc": "Default year split",
                "SE": "SE_0",
                "DT": "DT_0",
                "DTB": "DTB_0"
            }
        ];
        return defaultTs;
    }

    static defaultTech(first=false){
        let id;
        if(first){
            id = 'TEC_0';
        }else{
            id = this.getId('TEC');
        }
        let emptyArray = [];
        let defaultObj = [
            {
                "TechId": id,
                "Tech":id,
                "Desc": "Default technology",
                "CapUnitId": "GW",
                "ActUnitId": "PJ",
                "TG": emptyArray,
                "IAR": emptyArray,
                "OAR": emptyArray,
                "EAR": emptyArray,
                "INCR": emptyArray,
                "ITCR": emptyArray,
            }
        ];
        return defaultObj;
    }

    static defaultTechGroup(first=false){
        let id;
        if(first){
            id = 'TG_0';
        }else{
            id = this.getId('TG');
        }
        let defaultObj = [
            {
                "TechGroup": id,
                "TechGroupId":id,
                "Desc": "Default technology group",
            }
        ];
        return defaultObj;
    }

    static defaultComm(first=false){
        let id;
        if(first){
            id = 'COM_0';
        }else{
            id = this.getId('COM');
        }
        let defaultComm = [
            {
                "CommId": id,
                "Comm":id,
                "Desc": "Default commodity",
                "BalanceLevel": "Ts",
                "UnitId": "PJ"
            }
        ];
        return defaultComm;
    }

    static defaultEmi(first=false){
        let id;
        if(first){
            id = 'EMI_0';
        }else{
            id = this.getId('EMI');
        }
        let defaultEmi = [
            {
                "EmisId": id,
                "Emis":id,
                "Desc": "Default emission",
                "UnitId": "Ton"
            }
        ];
        return defaultEmi;
    }

    static defaultUnit(){
        let id = this.getId('UT');
        let defaultUnit = [
            {
                "UnitId": id,
                "Unitname":id,
                "IC": 0,
                "LT": 0,
                "CT": 0,
                "h": false,
                "Fuel": "Lignite"
            }
        ];
        return defaultUnit;
    }

    static defaultStg(first=false){
        let id;
        if(first){
            id = 'STG_0';
        }else{
            id = this.getId('STG');
        }
        let defaultObj = [
            {
                "StgId": id,
                "Stg":id,
                "Desc": "Default storage",
                "UnitId": "PJ",
                "TTS": "",
                "TFS": "",
                "Operation": "Yearly"
            }
        ];
        return defaultObj;
    }

    static defaultScenario(first=false){
        let id;
        let active;
        if(first){
            id = 'SC_0';
            active = true;
        }else{
            id = this.getId('SC');
            active = false; //new scenarios are inactive by default
        }
        let defaultObj = [
            {
                "ScenarioId": id,
                "Scenario":id,
                "Desc": "Base scenario",
                "Active": active
            }
        ];
        return defaultObj;
    }

    static defaultConstraint(first=false){
        let id;
        if(first){
            id = 'CO_0';
        }else{
            id = this.getId('CO');
        }
        let emptyArray = [];
        let defaultObj = [
            {
                "ConId": id,
                "Con":id,
                "Desc": "Default constraint ",
                "Tag": 1,
                "CM": emptyArray
            }
        ];
        return defaultObj;
    }

    static defaultIndicator(first=false){
        let id;
        if(first){
            id = 'IN_0';
        }else{
            id = this.getId('IN');
        }
        let emptyArray = [];
        let defaultObj = [
            {
                "IndicatorId": id,
                "Indicator":id,
                "Desc": "Default indicator",
                "IndicatorTypeId": "PI_i",
                "Sets": emptyArray
            }
        ];
        return defaultObj;
    }

    static defaultCase(first=false){
        let id;
        if(first){
            id = 'CS_0';
        }else{
            id = this.getId('CS');
        }
        let defaultObj = [
            {
                "Case": id,
                "CaseId":id,
                "Runtime": "Base scenario",
                "Scenarios": []
            }
        ];
        return defaultObj;
    }
}
