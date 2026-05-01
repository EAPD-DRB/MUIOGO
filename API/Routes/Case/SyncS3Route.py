from flask import Blueprint, jsonify, request
import os
from pathlib import Path
import shutil
from Classes.Base import Config
from Classes.Base.SyncS3 import SyncS3

syncs3_api = Blueprint('SyncS3Route', __name__)

@syncs3_api.route("/deleteResultsPreSync", methods=['POST'])
def deleteResultsPreSync():
    try:        
        case = request.json['casename']
        
        resPath = Path(Config.DATA_STORAGE, case, 'res')
        dataPath = Path(Config.DATA_STORAGE, case, 'data.txt')
        shutil.rmtree(resPath)
        os.remove(dataPath)

        response = {
            "message": 'Case <b>'+ case + '</b> deleted!',
            "status_code": "success"
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500

@syncs3_api.route("/uploadSync", methods=['POST'])
def uploadSync():
    try:        
        case = request.json['casename']

        s3 = SyncS3()
        localDir = Path(Config.DATA_STORAGE, case)
        s3.uploadSync(localDir, case, Config.S3_BUCKET, '*')

        response = {
            "message": 'Case <b>'+ case + '</b> syncronized!',
            "status_code": "success"
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500

@syncs3_api.route("/deleteSync", methods=['POST'])
def deleteSync():
    try:        
        case = request.json['casename']

        s3 = SyncS3()
        s3.deleteSync(case)

        response = {
            "message": 'Case <b>'+ case + '</b> deleted!',
            "status_code": "success"
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500

@syncs3_api.route("/updateSync", methods=['POST'])
def updateSync():
    try:        
        case = request.json['casename']
        filename = request.json['file']

        s3 = SyncS3()
        localDir = Path(Config.DATA_STORAGE, case, str(filename))
        s3.updateSync(localDir, case, Config.S3_BUCKET)

        response = {
            "message": 'Case <b>'+ case + '</b> deleted!',
            "status_code": "success"
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500

@syncs3_api.route("/updateSyncParamFile", methods=['GET'])
def updateSyncParamFile():
    try:        

        case = ''
        s3 = SyncS3()
        localDir = Path(Config.DATA_STORAGE, "Parameters.json")

        s3.updateSync(localDir, case, Config.S3_BUCKET)

        response = {
            "message": 'Case <b>'+ case + '</b> deleted!',
            "status_code": "success"
        }
        return jsonify(response), 200
    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500
