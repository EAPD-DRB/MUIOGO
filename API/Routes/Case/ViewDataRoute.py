from flask import Blueprint, jsonify, request
from Classes.Case.OsemosysClass import Osemosys

viewdata_api = Blueprint('ViewDataRoute', __name__)

@viewdata_api.route("/viewData", methods=['POST'])
def viewData():
    try:
        casename = request.json['casename']
        if casename != None:
            osy = Osemosys(casename)
            data = {}
            data['Tech'] = osy.viewDataByTech()
            data['Comm'] = osy.viewDataByComm()
            data['Emi'] = osy.viewDataByEmi()
            response = data    
        else:  
            response = None     
        return jsonify(response), 200
    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404

@viewdata_api.route("/viewTEData", methods=['POST'])
def viewTEData():
    try:
        casename = request.json['casename']
        if casename != None:
            osy = Osemosys(casename)
            data = {}
            data['Tech'] = osy.viewRTByTech()
            data['Emi'] = osy.viewREByEmi()
            response = data    
        else:  
            response = None     
        return jsonify(response), 200
    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404

@viewdata_api.route("/updateViewData", methods=['POST'])
def updateViewData():
    try:
        #casename, updateType, groupId, paramId, TechId, CommId, EmisId, Timeslice
        casename = request.json['casename']
        #updateType = request.json['updateType']
        year = request.json['year']
        ScId = request.json['ScId']
        groupId = request.json['groupId']
        paramId = request.json['paramId']
        TechId = request.json['TechId']
        CommId = request.json['CommId']
        EmisId = request.json['EmisId']
        Timeslice = request.json['Timeslice']
        value = request.json['value']

        if casename != None:
            osy = Osemosys(casename)
            osy.updateViewData(casename, year, ScId, groupId, paramId, TechId, CommId, EmisId, Timeslice, value)
            response = {
                "message": "You have updated view data!",
                "status_code": "success"
            }
        else:
            response = {
                "message": "No case data selected!",
                "status_code": "error"
            }
       
        return jsonify(response), 200
    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404

@viewdata_api.route("/updateTEViewData", methods=['POST'])
def updateTEViewData():
    try:
        #casename, updateType, groupId, paramId, TechId, CommId, EmisId, Timeslice
        casename = request.json['casename']
        scId = request.json['scId']
        groupId = request.json['groupId']
        paramId = request.json['paramId']
        techId = request.json['techId']
        emisId = request.json['emisId']
        value = request.json['value']

        if casename != None:
            osy = Osemosys(casename)
            data = osy.updateTEViewData(casename, scId, groupId, paramId, techId, emisId, value)
            response = {
                "message": "You have updated view data!",
                "status_code": "success"
            }
        else:
            response = {
                "message": "No case data selected!",
                "status_code": "error"
            }
       
        return jsonify(response), 200
    except PermissionError:
        return jsonify({'message': 'Invalid path.', 'status_code': 'error'}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404
