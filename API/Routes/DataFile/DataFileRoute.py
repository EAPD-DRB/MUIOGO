from flask import Blueprint, Response, jsonify, request, send_file, session
from pathlib import Path
import shutil, datetime, time, os, logging
from Classes.Case.DataFileClass import DataFile
from Classes.Base import Config
from utils import validate_json_fields

logger = logging.getLogger(__name__)

datafile_api = Blueprint('DataFileRoute', __name__)

@datafile_api.route("/generateDataFile", methods=['POST'])
def generateDataFile():
    try:
        casename = request.json['casename']
        caserunname = request.json['caserunname']

        if casename != None:
            txtFile = DataFile(casename)
            txtFile.generateDatafile(caserunname)
            response = {
                "message": "You have created data file!",
                "status_code": "success"
            }      
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/createCaseRun", methods=['POST'])
def createCaseRun():
    try:
        err, code = validate_json_fields('casename', 'caserunname', 'data')
        if err:
            return err, code
        casename = request.json['casename']
        caserunname = request.json['caserunname']
        data = request.json['data']

        if casename != None:
            caserun = DataFile(casename)
            response = caserun.createCaseRun(caserunname, data)
     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/updateCaseRun", methods=['POST'])
def updateCaseRun():
    try:
        err, code = validate_json_fields('casename', 'caserunname', 'oldcaserunname', 'data')
        if err:
            return err, code
        casename = request.json['casename']
        caserunname = request.json['caserunname']
        oldcaserunname = request.json['oldcaserunname']
        data = request.json['data']

        if casename != None:
            caserun = DataFile(casename)
            response = caserun.updateCaseRun(caserunname, oldcaserunname, data)
     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/deleteCaseRun", methods=['POST'])
def deleteCaseRun():
    try:
        err, code = validate_json_fields('casename', 'caserunname', 'resultsOnly')
        if err:
            return err, code

        casename = request.json['casename']
        caserunname = request.json['caserunname']
        resultsOnly = request.json['resultsOnly']

        if not casename:
            return jsonify({'message': 'No model selected.', 'status_code': 'error'}), 400

        Config.validate_path(Config.DATA_STORAGE, os.path.join(casename, 'res', caserunname or ''))
        casePath = Path(Config.DATA_STORAGE, casename, 'res', caserunname)
        if not resultsOnly:
            shutil.rmtree(casePath)
        else:
            for item in os.listdir(casePath):
                item_path = os.path.join(casePath, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

        caserun = DataFile(casename)
        response = caserun.deleteCaseRun(caserunname, resultsOnly)
        return jsonify(response), 200
    except FileNotFoundError:
        return jsonify('No existing cases!'), 404
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500

@datafile_api.route("/deleteScenarioCaseRuns", methods=['POST'])
def deleteScenarioCaseRuns():
    try:
        scenarioId = request.json['scenarioId']
        casename = request.json['casename']

        if casename != None:
            caserun = DataFile(casename)
            response = caserun.deleteScenarioCaseRuns(scenarioId)
     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/saveView", methods=['POST'])
def saveView():
    try:
        casename = request.json['casename']
        param = request.json['param']
        data = request.json['data']

        if casename != None:
            caserun = DataFile(casename)
            response = caserun.saveView(data, param)
     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/updateViews", methods=['POST'])
def updateViews():
    try:
        casename = request.json['casename']
        param = request.json['param']
        data = request.json['data']

        if casename != None:
            caserun = DataFile(casename)
            response = caserun.updateViews(data, param)
     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/readDataFile", methods=['POST'])
def readDataFile():
    try:
        casename = request.json['casename']
        caserunname = request.json['caserunname']
        if casename != None:
            txtFile = DataFile(casename)
            data = txtFile.readDataFile(caserunname)
            response = data    
        else:  
            response = None     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/readModelFile", methods=['GET'])
def readModelFile():
    model_path = Path(Config.SOLVERs_FOLDER, 'model.v.5.4.txt')
    if not model_path.is_file():
        return jsonify({'message': 'Model file not found.', 'status_code': 'error'}), 404

    text = model_path.read_text(encoding="utf-8", errors="replace")
    return Response(text, mimetype="text/plain; charset=utf-8")


@datafile_api.route("/readLogFile", methods=['GET'])
def readLogFile():
    try:
        log_path = Config.get_runtime_log_path()
    except OSError:
        return Response("Runtime logging is not available.\n", mimetype="text/plain; charset=utf-8")

    if not log_path.is_file():
        return Response("No runtime log available yet.\n", mimetype="text/plain; charset=utf-8")

    text = log_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return Response("No runtime log available yet.\n", mimetype="text/plain; charset=utf-8")
    return Response(text, mimetype="text/plain; charset=utf-8")
    
@datafile_api.route("/validateInputs", methods=['POST'])
def validateInputs():
    try:
        casename = request.json['casename']
        caserunname = request.json['caserunname']
        if casename != None:
            df = DataFile(casename)
            validation = df.validateInputs(caserunname)
            response = validation    
        else:  
            response = None     
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/downloadDataFile", methods=['GET'])
def downloadDataFile():
    try:
        #casename = request.json['casename']
        #casename = 'DEMO CASE'
        # txtFile = DataFile(casename)
        # downloadPath = txtFile.downloadDataFile()
        # response = {
        #     "message": "You have downloaded data.txt to "+ str(downloadPath) +"!",
        #     "status_code": "success"
        # }         
        # return jsonify(response), 200
        #path = "/Examples.pdf"
        case = session.get('osycase', None)
        if case is None:
            return jsonify({'message': 'No active session. Please select a model first.', 'status_code': 'error'}), 400
        caserunname = request.args.get('caserunname')
        if not caserunname:
            return jsonify({'message': 'Missing required parameter: caserunname.', 'status_code': 'error'}), 400
        Config.validate_path(Config.DATA_STORAGE, os.path.join(case or '', 'res', caserunname or ''))
        dataFile = Path(Config.DATA_STORAGE,case, 'res',caserunname, 'data.txt')
        return send_file(dataFile.resolve(), as_attachment=True, max_age=0)

    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/downloadFile", methods=['GET'])
def downloadFile():
    try:
        case = session.get('osycase', None)
        if case is None:
            return jsonify({'message': 'No active session. Please select a model first.', 'status_code': 'error'}), 400
        file = request.args.get('file')
        if not file:
            return jsonify({'message': 'Missing required parameter: file.', 'status_code': 'error'}), 400
        Config.validate_path(Config.DATA_STORAGE, os.path.join(case or '', 'res', 'csv', file or ''))
        dataFile = Path(Config.DATA_STORAGE,case,'res','csv',file)
        return send_file(dataFile.resolve(), as_attachment=True, max_age=0)

    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/downloadCSVFile", methods=['GET'])
def downloadCSVFile():
    try:
        case = session.get('osycase', None)
        if case is None:
            return jsonify({'message': 'No active session. Please select a model first.', 'status_code': 'error'}), 400
        file = request.args.get('file')
        caserunname = request.args.get('caserunname')
        if not file:
            return jsonify({'message': 'Missing required parameter: file.', 'status_code': 'error'}), 400
        if not caserunname:
            return jsonify({'message': 'Missing required parameter: caserunname.', 'status_code': 'error'}), 400
        Config.validate_path(Config.DATA_STORAGE, os.path.join(case or '', 'res', caserunname or '', 'csv', file or ''))
        dataFile = Path(Config.DATA_STORAGE,case,'res',caserunname,'csv',file)
        return send_file(dataFile.resolve(), as_attachment=True, max_age=0)

    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/downloadResultsFile", methods=['GET'])
def downloadResultsFile():
    try:
        case = session.get('osycase', None)
        if case is None:
            return jsonify({'message': 'No active session. Please select a model first.', 'status_code': 'error'}), 400
        caserunname = request.args.get('caserunname')
        if not caserunname:
            return jsonify({'message': 'Missing required parameter: caserunname.', 'status_code': 'error'}), 400
        Config.validate_path(Config.DATA_STORAGE, os.path.join(case or '', 'res', caserunname or ''))
        dataFile = Path(Config.DATA_STORAGE,case, 'res', caserunname,'results.txt')
        return send_file(dataFile.resolve(), as_attachment=True, max_age=0)

    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404

@datafile_api.route("/run", methods=['POST'])
def run():
    try:
        err, code = validate_json_fields('casename', 'caserunname', 'solver')
        if err:
            return err, code
        casename = request.json['casename']
        caserunname = request.json['caserunname']
        solver = request.json['solver']
        logger.info("Starting optimization process for model %s caserun %s", casename, caserunname)
        txtFile = DataFile(casename)
        response = txtFile.run(solver, caserunname)
        logger.info("Optimization finished for model %s caserun %s", casename, caserunname)
        return jsonify(response), 200
    # except Exception as ex:
    #     print(ex)
    #     return ex, 404
    
    except(IOError):
        return jsonify('No existing cases!'), 404
    
@datafile_api.route("/batchRun", methods=['POST'])
def batchRun():
    try:
        err, code = validate_json_fields('modelname', 'cases')
        if err:
            return err, code
        start = time.time()
        modelname = request.json['modelname']
        cases = request.json['cases']

        if modelname != None:
            txtFile = DataFile(modelname)
            for caserun in cases:
                logger.info("Generating data file for model %s caserun %s", modelname, caserun)
                txtFile.generateDatafile(caserun)

            response = txtFile.batchRun( 'CBC', cases) 
        end = time.time()  
        response['time'] = end-start 
        return jsonify(response), 200
    except(IOError):
        return jsonify('Error!'), 404
    
@datafile_api.route("/cleanUp", methods=['POST'])
def cleanUp():
    try:
        modelname = request.json['modelname']

        if modelname != None:
            model = DataFile(modelname)
            logger.info("Cleaning up results for model %s", modelname)
            response = model.cleanUp()

        return jsonify(response), 200
    except(IOError):
        return jsonify('Error!'), 404
