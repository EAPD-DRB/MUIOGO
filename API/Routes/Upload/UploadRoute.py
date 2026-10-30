import shutil
from flask import Blueprint, request, jsonify, send_file
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path, PurePosixPath
from werkzeug.utils import secure_filename
import os, json, glob


from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.CaseImporter import CaseImporter

upload_api = Blueprint('UploadRoute', __name__)

#File extension checking
def allowed_filename(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in Config.ALLOWED_EXTENSIONS

#File extension checking
def allowed_filename_xls(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in Config.ALLOWED_EXTENSIONS_XLS


def _validate_upload_name(name):
    """Archive labels and chunk IDs are single portable names, never case paths."""
    if not name or name in ('.', '..') or any(char in name for char in ('/', '\\', '\x00', ':')):
        raise PermissionError("Invalid upload name")


def download_dir(prefix, local, bucket, client):
    """
    params:
    - prefix: pattern to match in s3
    - local: local path to folder in which to place files
    - bucket: s3 bucket with target contents
    - client: initialized s3 client object
    """
    keys = []
    dirs = []
    next_token = ''
    base_kwargs = {
        'Bucket':bucket,
        'Prefix':prefix,
    }
    while next_token is not None:
        kwargs = base_kwargs.copy()
        if next_token != '':
            kwargs.update({'ContinuationToken': next_token})
        results = client.list_objects_v2(**kwargs)
        contents = results.get('Contents')
        if contents:
            for i in contents:
                k = i.get('Key')
                if k and not k.endswith('/'):
                    keys.append(k)
                else:
                    dirs.append(k)
        next_token = results.get('NextContinuationToken')
    for d in dirs:
        dest_pathname = os.path.join(local, d)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))
    for k in keys:
        dest_pathname = os.path.join(local, k)
        if not os.path.exists(os.path.dirname(dest_pathname)):
            os.makedirs(os.path.dirname(dest_pathname))
        client.download_file(bucket, k, dest_pathname)

def upload_dir(s3, localDir, awsInitDir, bucketName, tag, prefix=os.sep):
    """
    from current working directory, upload a 'localDir' with all its subcontents (files and subdirectories...)
    to a aws bucket
    Parameters
    ----------
    localDir :   localDirectory to be uploaded, with respect to current working directory
    awsInitDir : prefix 'directory' in aws
    bucketName : bucket in aws
    tag :        tag to select files, like *png
                 NOTE: if you use tag it must be given like --tag '*txt', in some quotation marks... for argparse
    prefix :     to remove initial '/' from file names

    Returns
    -------
    None
    """

    # mydirs daje listu svvih file i folder u localDir npr WebApp/DataStorage/Demo/genData.json
    mydirs = list(localDir.glob('**'))
    for mydir in mydirs:
        fileNames = glob.glob(os.path.join(mydir, tag))
        fileNames = [f for f in fileNames if not Path(f).is_dir()]
        #rows = len(fileNames)
        for i, FullfileName in enumerate(fileNames):
            #dobijemo ime file npr, genData.json
            fileName = str(FullfileName).replace(str(localDir), '')
            if fileName.startswith(prefix):  # only modify the text if it starts with the prefix
                fileName = fileName.replace(prefix, "", 1) # remove one instance of prefix
                fileName = fileName.replace(os.sep, '/')

            awsPath = str(awsInitDir) + '/' + str(fileName)
            # S3.resource.meta.client.upload_file(FullfileName, bucketName, awsPath)
            s3.resource.meta.client.upload_file(FullfileName, bucketName, awsPath)

def updateTimeslices_OnlyTs(casename):
    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
    genData = File.readParamFile(genDataPath)
    ns = int(genData["osy-ns"])
    nd = int(genData["osy-dt"])
    genData["osy-ts"] = []
    for season in range(ns):
        for day in range(nd):
            chunk = {}
            s = str(season + 1)
            d = str(day + 1)
            chunk['TsId'] = "S"+s+d
            chunk['Ts'] = "S"+s+d
            chunk['Desc'] = "Default year split"
            genData["osy-ts"].append(chunk)
    File.writeFile( genData, genDataPath)
    #rename json files with timeslices
    RYTsPath = Path(Config.DATA_STORAGE, casename, 'RYTs.json')
    RYTsPath.write_text(RYTsPath.read_text().replace('YearSplit', 'TsId'))
    RYTTsPath = Path(Config.DATA_STORAGE, casename, 'RYTTs.json')
    RYTTsPath.write_text(RYTTsPath.read_text().replace('Timeslice', 'TsId'))
    RYCTsPath = Path(Config.DATA_STORAGE, casename, 'RYCTs.json')
    RYCTsPath.write_text(RYCTsPath.read_text().replace('Timeslice', 'TsId'))


@upload_api.route("/backupCase", methods=['GET'])
def backupCase():
    try:    
        #case = request.form['case']
        #case = request.json['casename']
        case = request.args.get('case')

        casePath = Path(Config.validate_path(Config.DATA_STORAGE, case))
        zippedFile = Path(Config.validate_path(Config.DATA_STORAGE, f"{case}.zip"))

        '''File system data storage'''
        # DEFLATE rather than the ZipFile default of ZIP_STORED. Case backups are
        # JSON/CSV/text (model inputs, solver results, pivot views) which compress
        # ~15-30x; storing them uncompressed made the demo archive 48 MB and a real
        # country case ~944 MB. Every standard reader (Python zipfile, unzip, OS
        # archivers) handles DEFLATE, and the read/extract paths are unchanged, so
        # existing STORED backups still restore.
        with ZipFile(zippedFile, 'w', compression=ZIP_DEFLATED) as zipObj:
            # Iterate over all the files in directory
            for folderName, subfolders, filenames in os.walk(str(casePath)):

                for filename in filenames:
                    if filename != 'lp.lp':
                        filePath = os.path.join(folderName, filename)
                        # PurePosixPath enforces forward-slash separators in the ZIP
                        # regardless of host OS, required by the ZIP spec and ensures
                        # Windows-created backups restore correctly on Linux/macOS.
                        arcname = str(PurePosixPath(case) / os.path.relpath(filePath, str(casePath)).replace('\\', '/'))
                        zipObj.write(filePath, arcname=arcname)

            #osemosys 2.1 backup only input files
            # for filename in os.listdir(str(casePath)):
            #     folderName = os.path.join(str(casePath))
            #     if os.path.isfile(os.path.join(folderName, filename)):
            #         if filename != 'data.txt':
            #             #create complete filepath of file in directory
            #             filePath = os.path.join(folderName, filename)
            #             # Add file to zip
            #             zipObj.write(filePath)   

        response = send_file(zippedFile.resolve(), as_attachment=True)

        # send_file marks the response direct_passthrough, and werkzeug skips
        # the ClosingIterator that fires call_on_close for passthrough bodies
        # (get_app_iter returns the raw file iterable), so the callback would
        # never run under a real server. Disabling passthrough restores the
        # wrapper; close() then closes the file handle first and runs the
        # callback after, so the zip survives the whole download and the
        # delete also succeeds on Windows, where removing an in-use file
        # would fail.
        response.direct_passthrough = False

        def remove_zip():
            try:
                os.remove(zippedFile)
            except OSError:
                pass

        response.call_on_close(remove_zip)
        return response

    except PermissionError:
        return jsonify({"error": "Invalid path"}), 400
    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500

@upload_api.route('/uploadCaseUnchunked_old', methods=['POST'])
def uploadCaseUnchunked_old():
    """Keep the old endpoint on the same validated importer as current uploads."""
    try:
        messages = []
        for file in request.files.values():
            response, status = handle_full_zip(file)
            if status != 200:
                return response, status
            messages.extend(response.get_json()["response"])
        return jsonify({"response": messages}), 200
    except PermissionError:
        return jsonify({"error": "Invalid path"}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def handle_full_zip(file, filepath=None):
    """HTTP wrapper around CaseImporter.import_zip: save/validate the upload, run the
    shared import pipeline, jsonify its messages. The zip-processing logic itself
    lives in Classes/Case/CaseImporter.py so installers run the exact same code."""
    msg = []

    # Ako je file objekat (upload iz browsera)
    if filepath is None:
        submitted_file = file.filename
        # A multipart filename is an archive label, never a path into a case.
        # Check before saving: otherwise even a rejected non-ZIP could overwrite
        # another case's JSON or shared configuration under DataStorage.
        _validate_upload_name(submitted_file)
        if not allowed_filename(submitted_file):
            raise PermissionError("Invalid archive filename")
        filepath = Config.validate_path(Config.DATA_STORAGE, submitted_file)
        file.save(filepath)
    else:
        filepath = Config.validate_path(Config.DATA_STORAGE, filepath)
        submitted_file = os.path.basename(filepath)

    if submitted_file and allowed_filename(submitted_file):
        # cleanup=True: the upload flow has always removed the saved archive after import.
        msg = CaseImporter.import_zip(filepath, cleanup=True)

    return jsonify({"response": msg}), 200

@upload_api.route('/uploadCase', methods=['POST'])
def uploadCase():
    try:
        # -------------------------------
        # 1) Primanje Dropzone chunk meta
        # -------------------------------
        dz_uuid = request.form.get("dzuuid")
        dz_chunk_index = request.form.get("dzchunkindex")
        dz_total_chunks = request.form.get("dztotalchunkcount")
        file = request.files.get("file")

        # Ako nije chunked upload (chrome browser dev mode)
        if dz_uuid is None:
            # ==========================
            #     TVOJ ORIGINALNI KOD
            # ==========================
            return handle_full_zip(file)

        _validate_upload_name(dz_uuid)

        # Pretvaranje u int
        dz_chunk_index = int(dz_chunk_index)
        dz_total_chunks = int(dz_total_chunks)

        # -------------------------------
        # 2) Snimi chunk
        # -------------------------------
        chunk_dir = Config.validate_path(Config.DATA_STORAGE, Path("_chunks", dz_uuid))
        os.makedirs(chunk_dir, exist_ok=True)

        chunk_path = os.path.join(chunk_dir, f"chunk_{dz_chunk_index}")
        file.save(chunk_path)

        # -------------------------------
        # 3) Provjeri jesu li stigli svi
        # -------------------------------
        chunks_received = len(os.listdir(chunk_dir))

        if chunks_received < dz_total_chunks:
            return jsonify({"status": f"received {chunks_received}/{dz_total_chunks}"}), 200

        # -------------------------------
        # 4) Spajanje ZIP fajla
        # -------------------------------
        final_zip_name = f"{dz_uuid}.zip"
        final_zip = Config.validate_path(Config.DATA_STORAGE, final_zip_name)

        with open(final_zip, "wb") as merged:
            for i in range(dz_total_chunks):
                part_path = os.path.join(chunk_dir, f"chunk_{i}")
                with open(part_path, "rb") as part:
                    merged.write(part.read())

        # Očisti chunk folder
        shutil.rmtree(chunk_dir)

        # Now remove parent folder if it is empty
        parent = os.path.dirname(chunk_dir)
        if os.path.exists(parent) and not os.listdir(parent):
            os.rmdir(parent)

        # -------------------------------
        # 5) Pokreni TVOJ originalni ZIP handler
        # -------------------------------
        #return handle_full_zip(open(final_zip, "rb"), final_zip)
        # Pass the name relative to DataStorage: handle_full_zip validates it again,
        # and validate_path refuses absolute paths.
        return handle_full_zip(None, final_zip_name)

    except PermissionError:
        return jsonify({"error": "Invalid path"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@upload_api.route('/uploadXls', methods=['POST'])
def uploadXls():
    try: 
        msg = []
        submitted_storage =  request.files.to_dict()
        for files in submitted_storage.items():
            file = files[1]
            submitted_file = file.filename
            
            case = os.path.splitext(submitted_file)[0]

            if submitted_file and allowed_filename_xls(submitted_file):
                filename = secure_filename(submitted_file)
                #spasiti zip u data storage
                file.save(os.path.join(Config.DATA_STORAGE, filename))

                #ako ima space u umenu rename file
                # filename_nosapces = filename[:]
                # filename_nosapces.replace(" ","")
                # if( filename_nosapces != filename):
                #     os.rename(os.path.join(Config.DATA_STORAGE, filename), os.path.join(Config.DATA_STORAGE, filename_nosapces))
                #     filename = filename_nosapces
        
                msg.append({
                    "message": "Template " + submitted_file +" have been uploaded!",
                    "status_code": "success",
                    "casename": case,
                    "template": filename
                })
            else:
                msg.append({
                    "message": "Template " + submitted_file +" is not valid .xlsx file!",
                    "status_code": "warning",
                    "casename": case,
                    "template": submitted_file
                })

        response = {
            "response" :msg
        }

        return jsonify(response), 200
    except OSError:
        return jsonify({'message': 'A filesystem error occurred.', 'status_code': 'error'}), 500
