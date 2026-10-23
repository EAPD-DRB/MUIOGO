import { DefaultObj } from "../../Classes/DefaultObj.Class.js";
import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {
  constructor(genData, resData, PARAMETERS, INDICATORS, pageId) {
   
    if (genData) {
      this.casename = genData['osy-casename'];
      this.PARAMETERS = PARAMETERS;
      this.techNames = DataModel.TechName(genData);
      this.stgNames = DataModel.StgName(genData);
      this.techGroupNames = DataModel.TechGroupName(genData);
      this.commNames = DataModel.CommName(genData);
      this.tsNames = DataModel.TsName(genData);
      this.seNames = DataModel.SeName(genData);
      this.dtNames = DataModel.DtName(genData);
      this.dtbNames = DataModel.DtbName(genData);
      this.emiNames = DataModel.EmiName(genData);
      this.indicatorTypes = DataModel.getIndicatorTypes(INDICATORS);
      this.caserunByScenario = DataModel.getCaserunByScenario(genData, resData);

      this.title = "Model configuration";
      this.desc = genData['osy-desc'];
      this.mo = genData['osy-mo'];
      this.currency = genData['osy-currency'];
      this.years = genData['osy-years'];
      this.scenarios = genData['osy-scenarios'];
      this.techs = genData['osy-tech'];
      this.stg = genData['osy-stg'];
      this.techGroups = genData['osy-techGroups'];
      this.timeslices = genData['osy-ts'];
      this.seasons = genData['osy-se'];
      this.daytypes = genData['osy-dt'];
      this.dailytimebrackets = genData['osy-dtb'];
      // MUIOGO: cases saved before MUIO 5.7 have no BalanceLevel. They were
      // balanced per timeslice, so show (and save) that instead of a blank.
      this.commodities = genData['osy-comm'].map(c => ({ BalanceLevel: 'Ts', ...c }));
      this.emissions = genData['osy-emis'];
      this.constraints = genData['osy-constraints'];
      // MUIOGO: `|| []` guards pre-v5.6 cases that have no osy-indicators
      // key. Without it, opening any older case throws a JS error.
      this.indicators = genData['osy-indicators'] || [];


      this.techCount = genData['osy-tech'].length;
      this.stgCount = genData['osy-stg'].length;
      this.techGroupCount = genData['osy-techGroups'].length;
      this.commCount = genData['osy-comm'].length;
      this.tsCount = genData['osy-ts'].length;
      this.seCount = genData['osy-se'].length;
      this.dtbCount = genData['osy-dtb'].length;
      this.dtCount = genData['osy-dt'].length;
      this.emisCount = genData['osy-emis'].length;
      this.scenariosCount = genData['osy-scenarios'].length;
      this.constraintsCount = genData['osy-constraints'].length;
      this.indicatorsCount = (genData['osy-indicators'] || []).length;
    
      this.pageId = pageId;
    } else {
      let years = [];
      for (var i = 2020; i <= 2050; i++) { years.push(String(i)); }

      this.casename = null;
      this.PARAMETERS = PARAMETERS;
      this.techNames = { 'TEC_0': 'TEC_0' };
      this.stgNames = { };
      this.techGroupNames = { 'TG_0': 'TG_0'};
      this.commNames = { 'COM_0': 'COM_0' };
      this.emiNames = { 'EMI_0': 'EMI_0' };
      this.caserunByScenario = {'SC_0': []};

      this.tsNames = { 'TS_0': 'TS_0' };
      // this.seNames = { 'SE_0': 'SE_0' };
      // this.dtNames = { 'DT_0': 'DT_0' };
      // this.dtbNames = { 'DTB_0': 'DTB_0' };
      this.seNames = { 'SE_0': 1 };
      this.dtNames = { 'DT_0': 1 };
      this.dtbNames = { 'DTB_0': 1 };


      this.title = "Model configuration";
      this.desc = null;
      this.mo = null;
      this.currency = null;
      this.years = years;
      this.scenarios = DefaultObj.defaultScenario(true);
      this.techs = DefaultObj.defaultTech(true);
      this.stg = [];
      this.techGroups = DefaultObj.defaultTechGroup(true);
      this.commodities = DefaultObj.defaultComm(true);
      this.emissions = DefaultObj.defaultEmi(true);
      this.timeslices = DefaultObj.defaultTs(true);

      this.seasons = DefaultObj.defaultSe(true);
      this.daytypes = DefaultObj.defaultDt(true);
      this.dailytimebrackets = DefaultObj.defaultDtb(true);
      this.indicatorTypes = DataModel.getIndicatorTypes(INDICATORS);

      
      this.constraints = [];
      this.indicators = [];
      this.techCount = 1;
      this.stgCount = 0;
      this.techGroupCount = 1;
      this.tsCount = 1;
      this.seCount = 1;
      this.dtCount = 1;
      this.dtbCount = 1;
      this.commCount = 1;
      this.emisCount = 1;
      this.scenariosCount = 1;
      this.constraintsCount = 0,
         this.indicatorsCount = 0,
      this.pageId = pageId;
    }
  }
}
