
export class Model {
    constructor (casename, modelFile, pageId) {
      if(casename){        

        this.casename = casename || null;
        this.title = "Model file";
        this.modelFile = modelFile || "";
        this.pageId = pageId;

      }else{
        this.casename = null;
        this.title = "Model file";
        this.scenarios = null;
        this.pageId = pageId;
      }
    }
}
