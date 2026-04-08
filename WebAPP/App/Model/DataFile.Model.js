
export class Model {
    constructor (casename, genData, resData, modelFile, pageId) {
      if(casename){

        let cases = resData['osy-cases'];
        let scenarios =  genData['osy-scenarios'];
        //let scenarios =  resData['osy-cases'][0]['Scenarios']
        let cs = null;

        let scMap = {};
        $.each(scenarios, function (id, sc) {
          scMap[sc.ScenarioId] = sc;
        });

        let scBycs = {};
        $.each(resData['osy-cases'], function (id, cs) {
          scBycs[cs.Case] = cs.Scenarios
        });


        // console.log('cases ', cases)
        // console.log('scenarios ', scenarios)
        // console.log('scBycs ', scBycs)

        //26.04.2023. VK
        //dodati eventualno nove scenarije koji su dodani poslije uspjesnog RUN-a i nema ih u resData
        //pored originalnih scenarija u caserunu, potrebno dodati eventualno nove 
        //scenarije koji su dodani poslije uspjesnog RUN-a, kao neaktivne
        let sccsMap = {};
        $.each(cases, function (CsId, csObj) {

          if (!(csObj.Case in sccsMap))
            {sccsMap[csObj.Case] = {}}
          $.each(scBycs[csObj.Case], function (id, scObj) {
              sccsMap[csObj.Case][scObj.ScenarioId] = scObj;
          });


          $.each(scenarios, function (key, obj) {
              if(obj.ScenarioId in sccsMap[csObj.Case] === false){
                  //console.log('obj.Scenario ', obj.Scenario)
                  let sc = JSON.parse(JSON.stringify(obj));
                  sc.Active = false;
                  //console.log('sc ', sc)
                  scBycs[csObj.Case].push(sc);
              }
          });
        });


        //console.log('sccsMap ', sccsMap)

        
        this.casename = casename;
        this.cs = cs;
        this.modelFile = modelFile;
        this.scBycs = scBycs;
        this.title = "Run model";
        this.scenarios = scenarios;
        this.scenariosCount = scenarios.length;
        this.scMap = scMap;
        this.cases = cases;
        this.pageId = pageId;
      }else{
        this.casename = null;
        this.title = "Generate data file";
        this.scenarios = null;
        this.pageId = pageId;
      }
    }
}
