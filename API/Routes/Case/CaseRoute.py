from flask import Blueprint, jsonify, request, session, send_file
import os
from pathlib import Path
import shutil
import pandas as pd
from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.CaseClass import Case
from Classes.Case.UpdateCaseClass import UpdateCase
from Classes.Case.ImportTemplate import ImportTemplate
from Classes.Base.SyncS3 import SyncS3

case_api = Blueprint('CaseRoute', __name__)

@case_api.route("/initSyncS3", methods=['GET'])
def initSyncS3():
    try:
        #sync bucket with local storage
        syncS3 = SyncS3()
        cases = syncS3.getCasesSyncInit()
        for case in cases:
            syncS3.downloadSync(case, Config.DATA_STORAGE, Config.S3_BUCKET)
        #downoload param file from S3 bucket
        syncS3.downloadSync('Parameters.json', Config.DATA_STORAGE, Config.S3_BUCKET)
        response = {
            "message": "Cases syncronized with S3 bucket!",
            "status_code": "success"
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/getCases", methods=['GET'])
def getCases():
    try:
        cases = [ f.name for f in os.scandir(Config.DATA_STORAGE) if f.is_dir() ]
        return jsonify(cases), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/getResultCSV", methods=['POST'])
def getResultCSV():
    try:
        casename = request.json['casename']
        caserunname = request.json['caserunname']
        csvFolder = Path(Config.DATA_STORAGE,casename,"res", caserunname, "csv")
        if os.path.isdir(csvFolder):
            csvs = [ f.name for f in os.scandir(csvFolder) ]
        else:
            csvs = []
        return jsonify(csvs), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/getDesc", methods=['POST'])
def getDesc():
    try:
        casename = request.json['casename']
        genDataPath = Path(Config.DATA_STORAGE,casename,"genData.json")
        genData = File.readFile(genDataPath)
        response = {
            "message": "Get model description success",
            "desc": genData['osy-desc']
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/copyCase", methods=['POST'])
def copy():
    try:
        case = request.json['casename']
        active_case = session.get('osycase')

        if not active_case:
            return jsonify({'message': 'No active session.', 'status_code': 'error'}), 403
        if case != active_case:
            return jsonify({'message': 'Unauthorised: case does not match active session.', 'status_code': 'error'}), 403

        case_copy = case + '_copy'
        casePath = Path(Config.DATA_STORAGE, case_copy, 'genData.json')

        src =  Path(Config.DATA_STORAGE, case)
        dest =  Path(Config.DATA_STORAGE, case + '_copy')

        if(os.path.isdir(dest)):
            response = {
                "message": 'Model <b>'+ case + '_copy</b> already exists, please rename existing model first!',
                "status_code": "warning"
            }
        else:
            shutil.copytree(str(src), str(dest) )
            #rename casename in genData
            genData = File.readFile(casePath)
            genData['osy-casename'] = case_copy
            File.writeFile(genData, casePath)
            response = {
                "message": 'Model <b>'+ case + '</b> copied!',
                "status_code": "success"
            }
        return(response)
    except(IOError):
        raise IOError
    except OSError:
        raise OSError

@case_api.route("/deleteCase", methods=['POST'])
def deleteCase():
    try:
        case = request.json['casename']
        active_case = session.get('osycase')

        if not active_case:
            return jsonify({'message': 'No active session.', 'status_code': 'error'}), 403
        if case != active_case:
            return jsonify({'message': 'Unauthorised: case does not match active session.', 'status_code': 'error'}), 403

        casePath = Path(Config.DATA_STORAGE, case)
        shutil.rmtree(casePath)

        session['osycase'] = None
        response = {
            "message": 'Model <b>'+ case + '</b> deleted!',
            "status_code": "success_session"
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        raise OSError

@case_api.route("/getResultData", methods=['POST'])
def getResultData():
    try:
        casename = request.json['casename']
        dataJson = request.json['dataJson']
        if casename != None:
            dataPath = Path(Config.DATA_STORAGE,casename,'view',dataJson)
            data = File.readFile(dataPath)
            response = data   

        else:  
            response = None     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/getParamFile", methods=['POST'])
def getParamFile():
    try:
        dataJson = request.json['dataJson']
        configPath = Path(Config.DATA_STORAGE, dataJson)
        ConfigFile = File.readParamFile(configPath)
        response = ConfigFile       
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/resultsExists", methods=['POST'])
def resultsExists():
    try:
        casename = request.json['casename']
        if casename != None:
            resPath = Path(Config.DATA_STORAGE, casename, 'view', 'RYT.json')
            dataPath = Path(Config.DATA_STORAGE,casename,'view','resData.json')
            data = File.readFile(dataPath)
            if os.path.isfile(resPath) and data['osy-cases']:
                RYTTs = File.readFile(resPath)
                if data['osy-cases'] and RYTTs["ANC"]:
                    response = True      
                else:
                    response = False 
            else:
                response = False
        else:
            response = False
        #response = True
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/saveParamFile", methods=['POST'])
def saveParamFile():
    try:
        ParamData = request.json['ParamData']
        VarData = request.json['VarData']

        paramPath = Path(Config.DATA_STORAGE, 'Parameters.json')
        varPath = Path(Config.DATA_STORAGE, 'Variables.json')
        File.writeFile( ParamData, paramPath)
        File.writeFile( VarData, varPath)
        response = {
            "message": "You have updated parameters & variables data!",
            "status_code": "success"
        }
       
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/saveScOrder", methods=['POST'])
def saveScOrder():
    try:
        data = request.json['data']
        case = request.json['casename']
        genDataPath = Path(Config.DATA_STORAGE, case, 'genData.json')
        genData = File.readFile(genDataPath)
        genData['osy-scenarios'] = data
        File.writeFile( genData, genDataPath)
        response = {
            "message": "You have updated scenarios order data!",
            "status_code": "success"
        }
       
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/updateData", methods=['POST'])
def updateData():
    try:
        data = request.json['data']
        param = request.json['param']
        case = session.get('osycase', None)
        dataJson = request.json['dataJson']
        
        # Early return if case is None - prevents UnboundLocalError
        if case is None:
            return jsonify({
                "message": "No active case session found. Please select a case first.",
                "status_code": "error"
            }), 400
        
        dataPath = Path(Config.DATA_STORAGE, case, dataJson)
        sourceData = File.readFile(dataPath)
        sourceData[param] = data
        File.writeFile(sourceData, dataPath)
        #File.writeFileUJson(sourceData, dataPath)
        response = {
            "message": "Your data has been saved!",
            "status_code": "success"
        }      
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/saveCase", methods=['POST'])
def saveCase():
    try:
        genData = request.json['data']
        casename = genData['osy-casename']
        case = session.get('osycase', None)

        configPath = Path(Config.DATA_STORAGE, 'Variables.json')
        vars = File.readParamFile(configPath)

        
        # viewDef = {}
        # for group, lists in vars.items():
        #     for list in lists:
        #         viewDef[list['id']] = []

        #ukoliko dodamo varijablu onda se prilikom update case treba taj var dodati defaultno u view Definition
        # viewDataPath = Path(Config.DATA_STORAGE,casename,'view','viewDefinitions.json')
        # viewDefExisting = File.readParamFile(viewDataPath)
        # configPath = Path(Config.DATA_STORAGE, 'Variables.json')
        # vars = File.readParamFile(configPath)
        # viewDef = {}
        # for group, lists in vars.items():
        #     for list in lists:
        #         if list['id'] not in viewDefExisting["osy-views"]:
        #             viewDef[list['id']] = []
        #         else:
        #             viewDef[list['id']] = viewDefExisting["osy-views"][list['id']]


        #ako je izabran case, edit mode
        if case != None and case != '':
            genDataPath = Path(Config.DATA_STORAGE, case, "genData.json")

            ##update za view i res ukoliko nema
            resPath = Path(Config.DATA_STORAGE,case,'res')
            viewPath = Path(Config.DATA_STORAGE,case,'view')
            resDataPath = Path(Config.DATA_STORAGE,case,'view','resData.json')
            viewDataPath = Path(Config.DATA_STORAGE,case,'view','viewDefinitions.json')

            # viewDataPathExisting = Path(Config.DATA_STORAGE,casename,'view','viewDefinitions.json')
            viewDefExisting = File.readParamFile(viewDataPath)
            viewDef = {}
            for group, lists in vars.items():
                for list in lists:
                    if list['id'] not in viewDefExisting["osy-views"]:
                        viewDef[list['id']] = []
                    else:
                        viewDef[list['id']] = viewDefExisting["osy-views"][list['id']]

            viewData = {
                    "osy-views": viewDef
                }
            File.writeFile( viewData, viewDataPath)
            
            if not os.path.exists(resPath):
                os.makedirs(resPath, exist_ok=True)

            if not os.path.exists(viewPath):
                os.makedirs(viewPath, exist_ok=True)
                resData = {
                    "osy-cases":[]
                }
                File.writeFile( resData, resDataPath)




            #edit case sa istim imenom
            if case == casename:
                #update modela 
                caseUpdate = UpdateCase(case, genData)
                caseUpdate.updateCase() 

                #update genData
                File.writeFile( genData, genDataPath)

                ###########################potrebno updateovati i resData ukoliko smo brisali ili dodavali scenarios

                response = {
                    "message": "Your model configuration has been updated!",
                    "status_code": "edited"
                }
            #edit case sa drugim imenom, moramo provjeriit da li novo ime postoji u sistemu
            else:
                if not os.path.exists(Path(Config.DATA_STORAGE,casename)):

                    #update modela 
                    caseUpdate = UpdateCase(case, genData)
                    caseUpdate.updateCase() 

                    #update gen data sa novim imenom
                    File.writeFile( genData, genDataPath)

                    #nedostaje update resData u smislu novih ili izbirsanih scenarija
                    #rename case sa novim imenom
                    os.rename(Path(Config.DATA_STORAGE,case), Path(Config.DATA_STORAGE,casename ))
                    session['osycase'] = casename
                    
                    response = {
                        "message": "Your model configuration has been updated!",
                        "status_code": "edited"
                    }
                #ako vec postoji case sa istim imenom
                else:
                    response = {
                        "message": "Model with same name already exists!",
                        "status_code": "exist"
                    }
        #novi case 
        else:
            if not os.path.exists(Path(Config.DATA_STORAGE,casename)):
                viewDef = {}
                for group, lists in vars.items():
                    for list in lists:
                        viewDef[list['id']] = []

                session['osycase'] = casename
                os.makedirs(Path(Config.DATA_STORAGE,casename))
                genDataPath = Path(Config.DATA_STORAGE, casename, "genData.json")
                File.writeFile( genData, genDataPath)
                case = Case(casename, genData)
                case.createCase()  

                resPath = Path(Config.DATA_STORAGE,casename,'res')
                viewPath = Path(Config.DATA_STORAGE,casename,'view')
                resDataPath = Path(Config.DATA_STORAGE,casename,'view','resData.json')
                viewDataPath = Path(Config.DATA_STORAGE,casename,'view','viewDefinitions.json')
                if not os.path.exists(resPath):
                    os.makedirs(resPath, exist_ok=True)
                if not os.path.exists(viewPath):
                    os.makedirs(viewPath, exist_ok=True)
                    resData = {
                        "osy-cases":[]
                    }
                    File.writeFile( resData, resDataPath)

                    viewData = {
                        "osy-views": viewDef
                    }
                    File.writeFile( viewData, viewDataPath)

                response = {
                    "message": "Your model configuration has been saved!",
                    "status_code": "created"
                }
            else:
                response = {
                    "message": "Model with same name already exists!",
                    "status_code": "exist"
                }       

        return jsonify(response), 200
    except(IOError):
        return jsonify('Error saving model IOError!'), 404

@case_api.route("/prepareCSV", methods=['POST'])
def prepareCSV():
    try:
        casename = request.json['casename']
        jsonData = request.json['jsonData']

        Pd = pd.DataFrame(jsonData)

        i=0
        for p_col in Config.PINNED_COLUMNS:
            if p_col in Pd.columns:    
                col = Pd[p_col]
                Pd.drop(labels=[p_col], axis=1,inplace = True)
                Pd.insert(i, p_col, col)
                i=i+1

        Pd.to_csv(Path(Config.DATA_STORAGE,casename,'export.csv'), index = None)

        # Pd.to_excel(Path(Config.DATA_STORAGE,casename,'export.xlsx'))
        
        response = {
            "message": 'CSV data downloaded!',
            "status_code": "success"
        }
        return jsonify(response), 200

    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/downloadCSV", methods=['GET'])
def downloadCSV():
    try:
        casename = session.get('osycase', None)
        dataFile = Path(Config.DATA_STORAGE,casename,'export.csv')
        
        dir = Path(Config.DATA_STORAGE,casename)
        return send_file(dataFile.resolve(), as_attachment=True,mimetype='application/csv', max_age=0)
        #return send_from_directory(dir, 'export.csv', as_attachment=True)
    except(IOError):
        return jsonify('No existing cases!'), 404

@case_api.route("/importTemplate", methods=['POST'])
def run():
    try:
        data = request.json['data']
        template = ImportTemplate(data["osy-template"])
        response = template.importProcess(data)
 
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404
    except(IndexError):
        return jsonify('No existing cases!'), 404


####################################################################################OBSOLETE AND SyncS3###################################################

# @case_api.route("/getData", methods=['POST'])
# def getData():
#     try:
#         start = time.time()
#         casename = request.json['casename']
#         dataJson = request.json['dataJson']
#         if casename != None:
#             dataPath = Path(Config.DATA_STORAGE,casename,dataJson)
#             data = File.readFile(dataPath)
#             diff = time.time() - start
#             print('get data time ', diff)
#             response = data   

#         else:  
#             response = None     
#         return jsonify(response), 200
#     except(IOError):
#         return jsonify('No existing cases!'), 404

# @case_api.route("/deleteResultsPreSync", methods=['POST'])
# def deleteResultsPreSync():
#     try:        
#         case = request.json['casename']
        
#         resPath = Path(Config.DATA_STORAGE, case, 'res')
#         dataPath = Path(Config.DATA_STORAGE, case, 'data.txt')
#         shutil.rmtree(resPath)
#         os.remove(dataPath)

#         response = {
#             "message": 'Case <b>'+ case + '</b> deleted!',
#             "status_code": "success"
#         }
#         return jsonify(response), 200
#     except(IOError):
#         return jsonify('No existing cases!'), 404
#     except OSError:
#         raise OSError


# @case_api.route("/uploadSync", methods=['POST'])
# def uploadSync():
#     try:        
#         case = request.json['casename']

#         s3 = SyncS3()
#         localDir = Path(Config.DATA_STORAGE, case)
#         s3.uploadSync(localDir, case, Config.S3_BUCKET, '*')

#         response = {
#             "message": 'Case <b>'+ case + '</b> syncronized!',
#             "status_code": "success"
#         }
#         return jsonify(response), 200
#     except(IOError):
#         return jsonify('No existing cases!'), 404
#     except OSError:
#         raise OSError

# @case_api.route("/deleteSync", methods=['POST'])
# def deleteSync():
#     try:        
#         case = request.json['casename']

#         s3 = SyncS3()
#         s3.deleteCase(case)

#         response = {
#             "message": 'Case <b>'+ case + '</b> deleted!',
#             "status_code": "success"
#         }
#         return jsonify(response), 200
#     except(IOError):
#         return jsonify('No existing cases!'), 404
#     except OSError:
#         raise OSError

# @case_api.route("/updateSync", methods=['POST'])
# def updateSync():
#     try:        
#         case = request.json['casename']
#         filename = request.json['file']

#         s3 = SyncS3()
#         localDir = Path(Config.DATA_STORAGE, case, str(filename))
#         s3.updateSync(localDir, case, Config.S3_BUCKET)

#         response = {
#             "message": 'Case <b>'+ case + '</b> deleted!',
#             "status_code": "success"
#         }
#         return jsonify(response), 200
#     except(IOError):
#         return jsonify('No existing cases!'), 404
#     except OSError:
#         raise OSError

# @case_api.route("/updateSyncParamFile", methods=['GET'])
# def updateSyncParamFile():
#     try:        

#         case = ''
#         s3 = SyncS3()
#         localDir = Path(Config.DATA_STORAGE, "Parameters.json")

#         s3.updateSync(localDir, case, Config.S3_BUCKET)

#         response = {
#             "message": 'Case <b>'+ case + '</b> deleted!',
#             "status_code": "success"
#         }
#         return jsonify(response), 200
#     except(IOError):
#         return jsonify('No existing cases!'), 404
#     except OSError:
#         raise OSError
