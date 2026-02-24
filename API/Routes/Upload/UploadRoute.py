import shutil
from flask import Blueprint, request, jsonify, send_file, after_this_request
from zipfile import ZipFile
from pathlib import Path
from werkzeug.utils import secure_filename
import os, time, json, glob

from threading import Thread

from Classes.Base import Config
from Classes.Base.FileClass import File

upload_api = Blueprint('UploadRoute', __name__)

#File extension checking
def allowed_filename(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in Config.ALLOWED_EXTENSIONS

#File extension checking
def allowed_filename_xls(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in Config.ALLOWED_EXTENSIONS_XLS

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
        for i in contents:
            k = i.get('Key')
            if k[-1] != '/':
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

def updateTimeslices(casename):
    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
    genData = File.readParamFile(genDataPath)
    ns = int(genData["osy-ns"])
    nd = int(genData["osy-dt"])
    genData["osy-se"] = []
    genData["osy-se"].append({"SeId": "SE_0", "Se": "1", "Desc": "Default season"})

    genData["osy-dt"] = []
    genData["osy-dt"].append({"DtId": "DT_0", "Dt": "1", "Desc": "Default day type"})

    genData["osy-dtb"] = []
    genData["osy-dtb"].append({"DtbId": "DTB_0", "Dtb": "1", "Desc": "Default dialy time bracket"})

    genData["osy-ts"] = []
    for season in range(ns):
        for day in range(nd):
            chunk = {}
            s = str(season + 1)
            d = str(day + 1)
            chunk['TsId'] = "S"+s+d
            chunk['Ts'] = "S"+s+d
            chunk["SE"] = "SE_0"
            chunk["DT"] = "DT_0"
            chunk["DTB"] = "DTB_0"
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

def updateStorageSet(casename):
    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
    genData = File.readParamFile(genDataPath)

    genData["osy-stg"] = []

    File.writeFile( genData, genDataPath)

def updateViewDefintions(casename):
    viewDataPath = Path(Config.DATA_STORAGE,casename,'view','viewDefinitions.json')
    viewDefExisting = File.readParamFile(viewDataPath)
    configPath = Path(Config.DATA_STORAGE, 'Variables.json')
    vars = File.readParamFile(configPath)
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
##############################################################Multithreading example#########################3
class Download(Thread):
    def __init__(self, request, zippedFile):
        Thread.__init__(self)
        self.request = request
        self.zippedFile = zippedFile

    def run(self):
        print("wait few seconds for download to finish")
        time.sleep(20)
        #print(self.request)
        #remove zipped file
        os.remove(self.zippedFile)
        print("Deletion of zip archive done!")


@upload_api.route('/myfunc', methods=["GET", "POST"])
def myfunc():
        thread_a = Download(request.__copy__())
        thread_a.start()
        return "Processing in background", 200

@upload_api.route("/backupCase", methods=['GET'])
def backupCase():
    try:    
        #case = request.form['case']
        #case = request.json['casename']
        case = request.args.get('case')

        casePath = Path('WebAPP', 'DataStorage',case)
        zippedFile = Path('WebAPP', 'DataStorage', case+'.zip')

        '''File system data storage'''
        with ZipFile(zippedFile, 'w') as zipObj:
            # Iterate over all the files in directory
            for folderName, subfolders, filenames in os.walk(str(casePath)):

                for filename in filenames:
                    if filename != 'lp.lp':
                        #create complete filepath of file in directory
                        filePath = os.path.join(folderName, filename)
                        # Add file to zip
                        zipObj.write(filePath)      

            #osemosys 2.1 backup only input files
            # for filename in os.listdir(str(casePath)):
            #     folderName = os.path.join(str(casePath))
            #     if os.path.isfile(os.path.join(folderName, filename)):
            #         if filename != 'data.txt':
            #             #create complete filepath of file in directory
            #             filePath = os.path.join(folderName, filename)
            #             # Add file to zip
            #             zipObj.write(filePath)   

        thread_a = Download(request.__copy__(), zippedFile)
        thread_a.start()

        return send_file(zippedFile.resolve(), as_attachment=True)

    except(IOError):
        return jsonify('No existing cases!'), 404
    except OSError:
        raise OSError

@upload_api.route('/uploadCaseUnchunked_old', methods=['POST'])
def uploadCaseUnchunked_old():
    try:        
        msg = []
        submitted_storage =  request.files.to_dict()
        for files in submitted_storage.items():
            file = files[1]
            submitted_file = file.filename
            
            case = os.path.splitext(submitted_file)[0]

            if submitted_file and allowed_filename(submitted_file):
                filename = secure_filename(submitted_file)
                #spasiti zip u data storage
                file.save(os.path.join(Config.DATA_STORAGE, filename))
                #zipfiles = []
                with ZipFile(os.path.join(Config.DATA_STORAGE, filename)) as zf:
                    errorcode = 1
                    for zippedfile in zf.namelist():
                        # one = zippedfile
                        # two = Path(zippedfile)
                        # name = two.name
                        #zipfiles.append(Path(zippedfile).name)
                        zippedfilepath = Path(zippedfile)
                        zippedfilename = zippedfilepath.name
                        casename = zippedfilepath.parent.name
                        if 'genData.json' == zippedfilename:
                            errorcode = 0
                            
                            if not os.path.exists(Path(Config.DATA_STORAGE,casename)):
                                data = json.loads(zf.read(zippedfile).decode('ISO-8859-1'))
                                #name = data['else-version']
                                name = data.get('osy-version', None)

                                if name == '1.0' or name == '2.0':
                                    zf.extractall(os.path.join(Config.EXTRACT_FOLDER))

                                    #add res view folders with json default files
                                    configPath = Path(Config.DATA_STORAGE, 'Variables.json')
                                    vars = File.readParamFile(configPath)
                                    viewDef = {}
                                    for group, lists in vars.items():
                                        for list in lists:
                                            viewDef[list['id']] = []

                                    resPath = Path(Config.DATA_STORAGE,case,'res')
                                    viewPath = Path(Config.DATA_STORAGE,case,'view')
                                    resDataPath = Path(Config.DATA_STORAGE,case,'view','resData.json')
                                    viewDataPath = Path(Config.DATA_STORAGE,case,'view','viewDefinitions.json')

                                    # remove res and view folder if ver 1.0
                                    if os.path.exists(resPath):
                                        shutil.rmtree(resPath)

                                    if os.path.exists(viewPath):
                                        shutil.rmtree(viewPath)

                                    
                                    os.makedirs(resPath, mode=0o777, exist_ok=False)
                                    os.makedirs(viewPath, mode=0o777, exist_ok=False)
                                    resData = {
                                        "osy-cases":[]
                                    }
                                    File.writeFile( resData, resDataPath)

                                    viewData = {
                                        "osy-views": viewDef
                                    }
                                    File.writeFile( viewData, viewDataPath)

                                    #update for dynamic timeslicec
                                    updateTimeslices(casename)
                                    updateStorageSet(casename)
                                    
                                    msg.append({
                                        "message": "Model " + casename +" have been uploaded!",
                                        "status_code": "success",
                                        "casename": casename
                                    })
                                elif name == '3.0': 
                                    #potrebno dodati tech groups
                                    #case = data.get('osy-casename', None)
                                    zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                                    genData = File.readParamFile(genDataPath)
                                    genData["osy-techGroups"] = []
                                    for dic in genData["osy-tech"]:
                                        dic["TG"] =[]
                                    File.writeFile( genData, genDataPath)
                 
                                    #update for dynamic timeslicec
                                    updateTimeslices(casename)
                                    updateStorageSet(casename)
                                    updateViewDefintions(casename)

                                    msg.append({
                                        "message": "Model " + casename +" have been uploaded!",
                                        "status_code": "success",
                                        "casename": casename
                                    })
                                elif name == '4.0' or name == '4.5' or name == '4.9': 
                                    zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                                    # potrebno updatevoati YearSplit u verziji 5.0 su dinamicki
                                    #update for dynamic timeslicec
                                    updateTimeslices(casename)
                                    updateStorageSet(casename)
                                    updateViewDefintions(casename)
                                    #u 4.5 ver dodani paramteri i varijable
                                    # u 4.9 versiji dodano param DiscountRateIdv
                                    msg.append({
                                        "message_warning": "You have restored a model created in a earlier version of this UI. In order to update to the current version click <b>Update model</b> on the configuration page.",
                                        "message": "Model " + casename +" have been uploaded!",
                                        "status_code": "warning",
                                        "casename": casename
                                    })

                                # elif name == '4.9': 
                                #     zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                                #     # potrebno updatevoati YearSplit u verziji 5.0 su dinamicki
                                #     #update for dynamic timeslicec
                                #     updateTimeslices(casename)

                                #     msg.append({
                                #             "message": "Model " + casename +" have been uploaded!",
                                #             "status_code": "success",
                                #             "casename": casename
                                #         })

                                elif name == '5.0': 
                                    zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                                    updateViewDefintions(casename)
                                    msg.append({
                                        "message": "Model " + casename +" have been uploaded!",
                                        "status_code": "success",
                                        "casename": casename
                                    })
                                else:
                                    msg.append({
                                        "message": "Model " + casename +" is not valid OSEMOSYS ver 1.0, 2.0, 3.0, 4.0 or 5.0 model!",
                                        "status_code": "error"
                                    })
                            else:
                                msg.append({
                                    "message": "Model " + casename + " already exists!",
                                    "status_code": "warning"
                                })
                            
                    if errorcode == 1:
                        msg.append({
                            "message": "ZIP archive " + case +" is not valid archive!",
                            "status_code": "error"
                        })
                os.remove(os.path.join(Config.DATA_STORAGE, filename))
        
        response = {
            "response" :msg
        }

        return jsonify(response), 200
    except(IOError):
        raise IOError
    except OSError:
        raise OSError

def handle_full_zip(file, filepath=None):
    msg = []

    # Ako je file objekat (upload iz browsera)
    if filepath is None:
        submitted_file = file.filename
        filepath = os.path.join(Config.DATA_STORAGE, submitted_file)
        file.save(filepath)
    else:
        submitted_file = os.path.basename(filepath)

    case = os.path.splitext(submitted_file)[0]

    if submitted_file and allowed_filename(submitted_file):
        filename = secure_filename(submitted_file)

        with ZipFile(filepath) as zf:
            errorcode = 1


            # --- Find first genData.json entry (single pass) ---
            target_info = next(
                (zi for zi in zf.infolist() if Path(zi.filename).name == "genData.json"),
                None
            )

            if not target_info:
                # No genData.json at all
                msg.append({
                    "message": f"ZIP archive {case} is not valid archive!",
                    "status_code": "error"
                })
                return jsonify({"response": msg}), 200

            #for zippedfile in zf.namelist():

            zippedfilepath = Path(target_info.filename)
            zippedfilename = zippedfilepath.name
            casename = zippedfilepath.parent.name
            if 'genData.json' == zippedfilename:
                errorcode = 0
                if not os.path.exists(Path(Config.DATA_STORAGE,casename)):
                    data = json.loads(zf.read(target_info).decode('ISO-8859-1'))
                    name = data.get('osy-version', None)
                    # --------------------------- 
                    #     TVOJA ORIGINALNA LOGIKA
                    # ---------------------------
                    if name == '1.0' or name == '2.0':
                        zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                        configPath = Path(Config.DATA_STORAGE, 'Variables.json')
                        vars = File.readParamFile(configPath)
                        viewDef = {}
                        for group, lists in vars.items():
                            for list in lists:
                                viewDef[list['id']] = []
                        resPath = Path(Config.DATA_STORAGE,casename,'res')
                        viewPath = Path(Config.DATA_STORAGE,casename,'view')
                        resDataPath = Path(Config.DATA_STORAGE,case,'view','resData.json')
                        viewDataPath = Path(Config.DATA_STORAGE,case,'view','viewDefinitions.json')
                        if os.path.exists(resPath):
                            shutil.rmtree(resPath)
                        if os.path.exists(viewPath):
                            shutil.rmtree(viewPath)
                        os.makedirs(resPath, mode=0o777, exist_ok=False)
                        os.makedirs(viewPath, mode=0o777, exist_ok=False)
                        resData = {"osy-cases":[]}
                        File.writeFile(resData, resDataPath)
                        viewData = {"osy-views": viewDef}
                        File.writeFile(viewData, viewDataPath)
                        updateTimeslices(casename)
                        updateStorageSet(casename)
                        msg.append({
                            "message": "Model " + casename +" have been uploaded!",
                            "status_code": "success",
                            "casename": casename
                        })
                    elif name == '3.0':
                        zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                        genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                        genData = File.readParamFile(genDataPath)
                        genData["osy-techGroups"] = []
                        for dic in genData["osy-tech"]:
                            dic["TG"] = []
                        File.writeFile(genData, genDataPath)
                        updateTimeslices(casename)
                        updateStorageSet(casename)
                        updateViewDefintions(casename)
                        msg.append({
                            "message": "Model " + casename +" have been uploaded!",
                            "status_code": "success",
                            "casename": casename
                        })
                    elif name in ['4.0', '4.5', '4.9']:
                        zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                        updateTimeslices(casename)
                        updateStorageSet(casename)
                        updateViewDefintions(casename)
                        msg.append({
                            "message_warning": "You have restored a model created in a earlier version...",
                            "message": "Model " + casename +" have been uploaded!",
                            "status_code": "warning",
                            "casename": casename
                        })
                    elif name == '5.0':
                        zf.extractall(os.path.join(Config.EXTRACT_FOLDER))
                        updateViewDefintions(casename)
                        msg.append({
                            "message": "Model " + casename +" have been uploaded!",
                            "status_code": "success",
                            "casename": casename
                        })
                    else:
                        msg.append({
                            "message": "Model " + casename +" is not valid OSEMOSYS!",
                            "status_code": "error"
                        })

                else:
                    msg.append({
                        "message": "Model " + casename + " already exists!",
                        "status_code": "warning"
                    })

            if errorcode == 1:
                msg.append({
                    "message": "ZIP archive " + case +" is not valid archive!",
                    "status_code": "error"
                })

        os.remove(filepath)

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

        # Pretvaranje u int
        dz_chunk_index = int(dz_chunk_index)
        dz_total_chunks = int(dz_total_chunks)

        # -------------------------------
        # 2) Snimi chunk
        # -------------------------------
        chunk_dir = os.path.join(Config.DATA_STORAGE, "_chunks", dz_uuid)
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
        final_zip = os.path.join(Config.DATA_STORAGE, f"{dz_uuid}.zip")

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
        return handle_full_zip(None, final_zip) 

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
                    "template": filename
                })

        response = {
            "response" :msg
        }

        return jsonify(response), 200
    except(IOError):
        raise IOError
    except OSError:
        raise OSError