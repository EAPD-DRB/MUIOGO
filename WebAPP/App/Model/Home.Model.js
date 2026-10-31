export class Model {
    
    constructor (casename, cases, genData) {
       
        if (casename){
            this.casename = casename; 
            this.cases = cases;
            this.pageID = 'Home'
        }else{
            this.casename = null; 
            this.cases = cases;
            this.pageID = 'Home'
        }

    }
}
