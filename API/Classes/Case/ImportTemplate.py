from pathlib import Path
import pandas as pd
import string, random, json, os.path, time

from Classes.Base import Config
from Classes.Case.CaseClass import Case
from Classes.Base.FileClass import File

class ImportTemplate():
    def __init__(self,template):
        self.PARAMETERS = File.readParamFile(Path(Config.DATA_STORAGE, 'Parameters.json'))
        self.VARIABLES = File.readParamFile(Path(Config.DATA_STORAGE, 'Variables.json'))
        self.TEMPLATE_PATH = Path(Config.DATA_STORAGE, template)

    def getTechById(self, techs):
        techNames = {}
        for tech in techs:
            techNames[tech['TechId']] = tech['Tech']
        return techNames

    def getTsById(self, timeslices):
        tsNames = {}
        for ts in timeslices:
            tsNames[ts['TsId']] = ts['Ts']
        return tsNames

    def getTsByName(self, timeslices):
        tsNames = {}
        for ts in timeslices:
            tsNames[ts['Ts']] = ts['TsId']
        return tsNames
    
    def getTechGroupById(self, techGroups):
        techGroupNames = {}
        for tech in techGroups:
            techGroupNames[tech['TechGroupId']] = tech['TechGroup']
        return techGroupNames

    def getTechGroupByName(self, techGroups):
        techGroupNames = {}
        for tech in techGroups:
            techGroupNames[tech['TechGroup']] = tech['TechGroupId']
        return techGroupNames

    def getCommById(self, comms):
        commNames = {}
        for comm in comms:
            commNames[comm['CommId']] = comm['Comm']
        return commNames

    def getTechByName(self, techs):
        techNames = {}
        for tech in techs:
            techNames[tech['Tech']] = tech['TechId']
        return techNames

    def getCommByName(self, comms):
        commNames = {}
        for comm in comms:
            commNames[comm['Comm']] = comm['CommId']
        return commNames

    def getEmiById(self, emis):
        emiNames = {}
        for emi in emis:
            emiNames[emi['EmisId']] = emi['Emis']
        return emiNames

    def getEmiByName(self, emis):
        emiNames = {}
        for emi in emis:
            emiNames[emi['Emis']] = emi['EmisId']
        return emiNames

    def getStgById(self, stgs):
        stgNames = {}
        for stg in stgs:
            stgNames[stg['StgId']] = stg['Stg']
        return stgNames

    def getStgByName(self, stgs):
        stgNames = {}
        for stg in stgs:
            stgNames[stg['Stg']] = stg['StgId']
        return stgNames

    def getId(self, type):
        st = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(5))
        return type+'_'+st

    def defaultTech(self, name, desc="Default technology", capunit="GW", actunit="PJ", first=False ):
        if(first):
            id = 'TEC_0'
        else:
            id = self.getId('TEC')
        
        defaultObj = [
            {
                "TechId": id,
                "Tech":name,
                "Desc": desc,
                "CapUnitId": capunit,
                "ActUnitId": actunit,
                "IAR": [],
                "OAR": [],
                "EAR": [],
                "INCR": [],
                "ITCR": [],
            }
        ]
        return defaultObj

    def defaultTechGroup(self, name, desc="Default technology group", first=False):
        if(first):
            id = 'TG_0'
        else:
            id = self.getId('TG')
            
        defaultObj = [
            {
                "TechGroup": name,
                "TechGroupId":id,
                "Desc": desc,
            }
        ]
        return defaultObj
        
    def defaultTs(self, name, desc="Default timeslice", first=False):
        if(first):
            id = 'TS_0'
        else:
            id = self.getId('TS')
        
        defaultTs = [
            {
                "TsId": id,
                "Ts":name,
                "Desc": desc,
                "SE": "SE_0",
                "DT": "DT_0",
                "DTB": "DTB_0"
            }
        ]
        return defaultTs
    
    def defaultSe(self, name, desc="Default season", first=False):
        if(first):
            id = 'SE_0'
        else:
            id = self.getId('SE')
        
        defaultSe = [
            {
                "SeId": id,
                "Se":name,
                "Desc": desc
            }
        ]
        return defaultSe

    def defaultDt(self, name, desc="Default day type", first=False):
        if(first):
            id = 'DT_0'
        else:
            id = self.getId('DT')
        
        defaultDt = [
            {
                "DtId": id,
                "Dt":name,
                "Desc": desc
            }
        ]
        return defaultDt

    def defaultDtb(self, name, desc="Default daily time bracket", first=False):
        if(first):
            id = 'DTB_0'
        else:
            id = self.getId('DTB')
        
        defaultDtb = [
            {
                "DtbId": id,
                "Dtb":name,
                "Desc": desc
            }
        ]
        return defaultDtb
     
    def defaultComm(self, name, desc="Default commodity", unit="PJ", first=False):
        if(first):
            id = 'COM_0'
        else:
            id = self.getId('COM')
        
        defaultComm = [
            {
                "CommId": id,
                "Comm":name,
                "Desc": desc,
                "UnitId": unit
            }
        ]
        return defaultComm

    def defaultEmi(self, name, desc="Default emission", unit="Ton", first=False):
        if(first):
            id = 'EMI_0'
        else:
            id = self.getId('EMI')
        
        defaultEmi = [
            {
                "EmisId": id,
                "Emis":name,
                "Desc": desc,
                "UnitId": unit
            }
        ]
        return defaultEmi

    def defaultStg(self, name, desc="Default storage", unit="MW", first=False):
        if(first):
            id = 'STG_0'
        else:
            id = self.getId('STG')
        
        defaultStg = [
            {
                "StgId": id,
                "Stg":name,
                "Desc": desc,
                "UnitId": unit,
                "TTS": "TEC_0",
                "TFS": "TEC_0",
                "Operation": "Yearly"
            }
        ]
        return defaultStg
    
    def defaultUnit(self):
        id = self.getId('UT')
        defaultUnit = [
            {
                "UnitId": id,
                "Unitname":id,
                "IC": 0,
                "LT": 0,
                "CT": 0,
                "h": False,
                "Fuel": "Lignite"
            }
        ]
        return defaultUnit
        
    def defaultScenario(self, first=False):
        if(first):
            id = 'SC_0'
        else:
            id = self.getId('SC')
        
        defaultObj = [
            {
                "ScenarioId": id,
                "Scenario":id,
                "Desc": "Base scenario",
                "Active": True
            }
        ]
        return defaultObj

    def defaultConstraint(self, first=False):
        if(first):
            id = 'CO_0'
        else:
            id = self.getId('CO')
        
        emptyArray = ['TEC_0']
        defaultObj = [
            {
                "ConId": id,
                "Con":id,
                "Desc": "Default constraint ",
                "Tag": 1,
                "CM": emptyArray
            }
        ]
        return defaultObj
        
    def defaultCase(self, first=False):
        if(first):
            id = 'CS_0'
        else:
            id = self.getId('CS')
        
        defaultObj = [
            {
                "Case": id,
                "CaseId":id,
                "Runtime": "Base scenario",
                "Scenarios": []
            }
        ]
        return defaultObj

    def refR(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['REGION'] not in outObj:
                outObj[obj['REGION']] = {}
            region = obj['REGION']
            val = obj['VALUE']
            #trenutno imamo samojedan trgion pa koristimo RE1
            outObj['RE1'] = val
        return outObj
    
    def refRT(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['TECHNOLOGY'] not in outObj:
                outObj[obj['TECHNOLOGY']] = {}
            tech = obj['TECHNOLOGY']
            val = obj['VALUE']
            outObj[tech] = val
        return outObj

    def refRE(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['EMISSION'] not in outObj:
                outObj[obj['EMISSION']] = {}
            emi = obj['EMISSION']
            val = obj['VALUE']
            outObj[emi] = val
        return outObj

    def refRS(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['STORAGE'] not in outObj:
                outObj[obj['STORAGE']] = {}
            stg = obj['STORAGE']
            val = obj['VALUE']
            outObj[stg] = val
        return outObj
    
    def refRY(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['YEAR'] not in outObj:
                outObj[obj['YEAR']] = {}
            yr = obj['YEAR']
            val = obj['VALUE']
            outObj[yr] = val
        return outObj

    def refRYTCM(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['TECHNOLOGY'] not in outObj:
                outObj[obj['TECHNOLOGY']] = {}
            if obj['FUEL'] not in outObj[obj['TECHNOLOGY']]:
                outObj[obj['TECHNOLOGY']][obj['FUEL']] = {}
            if obj['MODE_OF_OPERATION'] not in outObj[obj['TECHNOLOGY']][obj['FUEL']]:
                outObj[obj['TECHNOLOGY']][obj['FUEL']][obj['MODE_OF_OPERATION']] = {}
            tech = obj['TECHNOLOGY']
            comm = obj['FUEL']
            mod = obj['MODE_OF_OPERATION']
            del obj['REGION']
            del obj['TECHNOLOGY']
            del obj['FUEL']
            del obj['MODE_OF_OPERATION']
            outObj[tech][comm][mod] = obj
        return outObj

    def refRYTEM(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['TECHNOLOGY'] not in outObj:
                outObj[obj['TECHNOLOGY']] = {}
            if obj['EMISSION'] not in outObj[obj['TECHNOLOGY']]:
                outObj[obj['TECHNOLOGY']][obj['EMISSION']] = {}
            if obj['MODE_OF_OPERATION'] not in outObj[obj['TECHNOLOGY']][obj['EMISSION']]:
                outObj[obj['TECHNOLOGY']][obj['EMISSION']][obj['MODE_OF_OPERATION']] = {}
            tech = obj['TECHNOLOGY']
            emi = obj['EMISSION']
            mod = obj['MODE_OF_OPERATION']
            del obj['REGION']
            del obj['TECHNOLOGY']
            del obj['EMISSION']
            del obj['MODE_OF_OPERATION']
            outObj[tech][emi][mod] = obj
        return outObj

    def refRYTM(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['TECHNOLOGY'] not in outObj:
                outObj[obj['TECHNOLOGY']] = {}
            if obj['MODE_OF_OPERATION'] not in outObj[obj['TECHNOLOGY']]:
                outObj[obj['TECHNOLOGY']][obj['MODE_OF_OPERATION']] = {}
            tech = obj['TECHNOLOGY']
            mod = obj['MODE_OF_OPERATION']
            del obj['REGION']
            del obj['TECHNOLOGY']
            del obj['MODE_OF_OPERATION']
            outObj[tech][mod] = obj
        return outObj

    def refRYTTs(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['TECHNOLOGY'] not in outObj:
                outObj[obj['TECHNOLOGY']] = {}
            if obj['TIMESLICE'] not in outObj[obj['TECHNOLOGY']]:
                outObj[obj['TECHNOLOGY']][obj['TIMESLICE']] = {}
            tech = obj['TECHNOLOGY']
            mod = obj['TIMESLICE']
            del obj['REGION']
            del obj['TECHNOLOGY']
            del obj['TIMESLICE']
            outObj[tech][mod] = obj
        return outObj

    def refRYCTs(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['FUEL'] not in outObj:
                outObj[obj['FUEL']] = {}
            if obj['TIMESLICE'] not in outObj[obj['FUEL']]:
                outObj[obj['FUEL']][obj['TIMESLICE']] = {}
            comm = obj['FUEL']
            mod = obj['TIMESLICE']
            del obj['REGION']
            del obj['FUEL']
            del obj['TIMESLICE']
            outObj[comm][mod] = obj
        return outObj

    def refRTSM(self, xlsObj):
        outObj = {}
        for obj in xlsObj:
            if obj['TECHNOLOGY'] not in outObj:
                outObj[obj['TECHNOLOGY']] = {}
            if obj['STORAGE'] not in outObj[obj['TECHNOLOGY']]:
                outObj[obj['TECHNOLOGY']][obj['STORAGE']] = {}
            if obj['MODE_OF_OPERATION'] not in outObj[obj['TECHNOLOGY']][obj['STORAGE']]:
                outObj[obj['TECHNOLOGY']][obj['STORAGE']][obj['MODE_OF_OPERATION']] = {}
            tech = obj['TECHNOLOGY']
            stg = obj['STORAGE']
            mod = obj['MODE_OF_OPERATION']
            val = obj['VALUE']
            outObj[tech][stg][mod] = val
        return outObj
    
    def importProcess(self, data):
        try:
            print('IMPORT STARTED!')
            start_time = time.time()
            template_file = data['osy-template']
            casename = data['osy-casename']
            currency = data['osy-currency']
            version = data['osy-version']
            description = data['osy-desc']
            date = data['osy-date']
            data = data['osy-data']
            tgArray = []
            txtOut = ""

            df_sheet_all = pd.read_excel(self.TEMPLATE_PATH, sheet_name=None, engine='openpyxl')

            techs_xls =  df_sheet_all['TECHNOLOGY']
            comms_xls =  df_sheet_all['FUEL']
            emis_xls =  df_sheet_all['EMISSION']
            stgs_xls =  df_sheet_all['STORAGE']
            years_xls = df_sheet_all['YEAR']
            moo_xls = df_sheet_all['MODE_OF_OPERATION']
            ts_xls = df_sheet_all['TIMESLICE']
            se_xls = df_sheet_all['SEASON']
            dt_xls = df_sheet_all['DAYTYPE']
            dtb_xls = df_sheet_all['DAILYTIMEBRACKET']

            if 'TECHGROUP' in df_sheet_all:
                tg_xls = df_sheet_all['TECHGROUP']
                tg_data = tg_xls.to_json(orient='records', indent=2)
                tgArray = json.loads(tg_data)

            iar_xls = df_sheet_all['InputActivityRatio']
            oar_xls = df_sheet_all['OutputActivityRatio']
            ear_xls = df_sheet_all['EmissionActivityRatio']

            #TECHNOLOGY TO AND FROM STORAGE
            tfs_xls = df_sheet_all['TechnologyFromStorage']
            tts_xls = df_sheet_all['TechnologyToStorage']


            techs_xls.rename(columns = {'VALUE':'TECHNOLOGY'}, inplace = True)
            comms_xls.rename(columns = {'VALUE':'COMMODITY'}, inplace = True)
            emis_xls.rename(columns = {'VALUE':'EMISSION'}, inplace = True)
            stgs_xls.rename(columns = {'VALUE':'STORAGE'}, inplace = True)
            years_xls.rename(columns = {'VALUE':'YEARS'}, inplace = True)
            moo_xls.rename(columns = {'VALUE':'MODE_OF_OPERATION'}, inplace = True)
            ts_xls.rename(columns = {'VALUE':'TIMESLICE'}, inplace = True)
            se_xls.rename(columns = {'VALUE':'SEASON'}, inplace = True)
            dt_xls.rename(columns = {'VALUE':'DAYTYPE'}, inplace = True)
            dtb_xls.rename(columns = {'VALUE':'DAILYTIMEBRACKET'}, inplace = True)

            techs_data = techs_xls.to_json(orient='records', indent=2)
            comms_data = comms_xls.to_json(orient='records', indent=2)
            emis_data = emis_xls.to_json(orient='records', indent=2)
            stgs_data = stgs_xls.to_json(orient='records', indent=2)
            ts_data = ts_xls.to_json(orient='records', indent=2)
            se_data = se_xls.to_json(orient='records', indent=2)
            dt_data = dt_xls.to_json(orient='records', indent=2)
            dtb_data = dtb_xls.to_json(orient='records', indent=2)

            iar_data = iar_xls.to_json(orient='records', indent=2)
            oar_data = oar_xls.to_json(orient='records', indent=2)
            ear_data = ear_xls.to_json(orient='records', indent=2)

            #technology to and from storage
            tts_data = tts_xls.to_json(orient='records', indent=2)
            tfs_data = tfs_xls.to_json(orient='records', indent=2)

            techsArray = json.loads(techs_data)
            commsArray = json.loads(comms_data)
            emisArray = json.loads(emis_data)
            stgsArray = json.loads(stgs_data)
            tsArray = json.loads(ts_data)
            seArray = json.loads(se_data)
            dtArray = json.loads(dt_data)
            dtbArray = json.loads(dtb_data)

            iarArray = json.loads(iar_data)
            oarArray = json.loads(oar_data)
            earArray = json.loads(ear_data)

            #technology to and from storage
            ttsArray = json.loads(tts_data)
            tfsArray = json.loads(tfs_data)

            yearsArray = years_xls['YEARS'].astype(str).values.tolist()
            mooValue = moo_xls['MODE_OF_OPERATION'].count()

            print('READ OF XLS DONE!')
            print("--- %s seconds ---" % (time.time() - start_time))
            txtOut = ("Read of xls template done in --- {} seconds ---{}".format(time.time() - start_time, '\n'))

            timeslices = []
            if not tsArray:
                timeslices.append(self.defaultTs('TS_0', first=True)[0])
            else:
                for i,obj in enumerate(tsArray):
                    timeslice = obj['TIMESLICE']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default timeslice"
                    if i==0:
                        timeslices.append(self.defaultTs(timeslice, desc, True)[0])
                    else:
                        timeslices.append(self.defaultTs(timeslice, desc)[0])

            seasons = []
            if not seArray:
                seasons.append(self.defaultSe(1, first=True)[0])
            else:
                for i,obj in enumerate(seArray):
                    season = obj['SEASON']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default season"
                    if i==0:
                        seasons.append(self.defaultSe(season, desc, True)[0])
                    else:
                        seasons.append(self.defaultSe(season, desc)[0])

            daytypes = []
            if not dtArray:
                daytypes.append(self.defaultDt(1, first=True)[0])
            else:
                for i,obj in enumerate(dtArray):
                    daytype = obj['DAYTYPE']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default day type"
                    if i==0:
                        daytypes.append(self.defaultDt(daytype, desc, True)[0])
                    else:
                        daytypes.append(self.defaultDt(daytype, desc)[0])

            dailytimebrackets = []
            if not dtbArray:
                dailytimebrackets.append(self.defaultDtb(1, first=True)[0])
            else:
                for i,obj in enumerate(dtbArray):
                    dtb = obj['DAILYTIMEBRACKET']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default daily tme bracket"
                    if i==0:
                        dailytimebrackets.append(self.defaultDtb(dtb, desc, True)[0])
                    else:
                        dailytimebrackets.append(self.defaultDtb(dtb, desc)[0])

            techgroups = []
            if not tgArray:
                techgroups.append(self.defaultTechGroup('TG_0', first=True)[0])
            else:
                for i, obj in enumerate(tgArray):
                    tGroup = obj['TECHGROUP']
                    tGroupDesc = obj['DESCRIPTION']
                    if tGroupDesc is None:
                        tGroupDesc = "Default technology group"
                    if i==0:
                        techgroups.append(self.defaultTechGroup(tGroup, tGroupDesc, True)[0])
                    else:
                        techgroups.append(self.defaultTechGroup(tGroup, tGroupDesc)[0])

            techs = []
            if not techsArray:
                techs.append(self.defaultTech('TEC_0', first=True)[0])
            else:
                for obj in techsArray:
                    tech = obj['TECHNOLOGY']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default commodity"

                    if obj.get('UNITOFCAPACITY') is not None:
                        unitcap = obj['UNITOFCAPACITY']
                    else:
                        unitcap = "GW"
                    if obj.get('UNITOFACTIVITY') is not None:
                        unitact = obj['UNITOFACTIVITY']
                    else:
                        unitact = "PJ"

                    if obj==0:
                        techs.append(self.defaultTech(tech, desc, unitcap, unitact, first=True)[0])
                    else:
                        techs.append(self.defaultTech(tech, desc, unitcap, unitact)[0])

            comms = []
            if not commsArray:
                comms.append(self.defaultComm('COM_0', first=True)[0])
            else:
                for obj in commsArray:
                    com = obj['COMMODITY']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default commodity"
                    if obj.get('UNIT') is not None:
                        unit = obj['UNIT']
                    else:
                        unit = "PJ"
                    if obj==0:
                        comms.append(self.defaultComm(com, desc, unit, True)[0])
                    else:
                        comms.append(self.defaultComm(com, desc, unit)[0])

            emis = []
            if not emisArray:
                emis.append(self.defaultEmi('EMI_0', first=True)[0])
            else:
                for obj in emisArray:
                    emi = obj['EMISSION']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default emission"
                    if obj.get('UNIT') is not None:
                        unit = obj['UNIT']
                    else:
                        unit = "Ton"
                    if obj==0:
                        emis.append(self.defaultEmi(emi, desc, unit, True)[0])
                    else:
                        emis.append(self.defaultEmi(emi, desc, unit)[0])

            stgs = []
            #ako nemamo storage ne treba nam ni ndefault ni
            # if not stgsArray:
            #     stgs.append(self.defaultStg('STG_0', first=True)[0])
            # else:
            if stgsArray:
                for obj in stgsArray:
                    stg = obj['STORAGE']
                    if obj.get('DESCRIPTION') is not None:
                        desc = obj['DESCRIPTION']
                    else:
                        desc = "Default storage"
                    if obj.get('UNIT') is not None:
                        unit = obj['UNIT']
                    else:
                        unit = "MW"
                    if obj==0:
                        stgs.append(self.defaultStg(stg, desc, unit, True)[0])
                    else:
                        stgs.append(self.defaultStg(stg, desc, unit)[0])
                


            # #populate IAR and OAR
            # stgId = self.getStgByName(stgs)
            techId = self.getTechByName(techs)
            commId = self.getCommByName(comms)
            emiId = self.getEmiByName(emis)
            stgId = self.getStgByName(stgs)
            
            tgId = self.getTechGroupByName(techgroups)

            iarObj = {}
            oarObj = {}
            ttsObj = {}
            tfsObj = {}
            earObj = {}
            techgroupObj = {}

            for iar in iarArray:
                if iar['TECHNOLOGY'] not in iarObj:
                    iarObj[iar['TECHNOLOGY']] = []
                if commId[iar['FUEL']] not in iarObj[iar['TECHNOLOGY']]:
                    iarObj[iar['TECHNOLOGY']].append(commId[iar['FUEL']])

            for oar in oarArray:
                if oar['TECHNOLOGY'] not in oarObj:
                    oarObj[oar['TECHNOLOGY']] = []
                if commId[oar['FUEL']] not in oarObj[oar['TECHNOLOGY']]:
                    oarObj[oar['TECHNOLOGY']].append(commId[oar['FUEL']])

            for ear in earArray:
                if ear['TECHNOLOGY'] not in earObj:
                    earObj[ear['TECHNOLOGY']] = []
                if emiId[ear['EMISSION']] not in earObj[ear['TECHNOLOGY']]:
                    earObj[ear['TECHNOLOGY']].append(emiId[ear['EMISSION']])

            for tts in ttsArray:
                ttsObj[tts['STORAGE']] = techId[tts['TECHNOLOGY']]
                # if tts['STORAGE'] not in ttsObj:
                #     ttsObj[tts['STORAGE']] = []
                # if techId[tts['TECHNOLOGY']] not in ttsObj[tts['STORAGE']]:
                #     ttsObj[tts['STORAGE']].append(techId[tts['TECHNOLOGY']])

            for tfs in tfsArray:
                tfsObj[tfs['STORAGE']] = techId[tfs['TECHNOLOGY']]
                # if tfs['STORAGE'] not in tfsObj:
                #     tfsObj[tfs['STORAGE']] = []
                # if techId[tfs['TECHNOLOGY']] not in tfsObj[tfs['STORAGE']]:
                #     tfsObj[tfs['STORAGE']].append(techId[tfs['TECHNOLOGY']])





            for tech in techsArray:
                ##if 'TECHGROUP' in tech:
                if tech['TECHNOLOGY'] not in techgroupObj:
                    techgroupObj[tech['TECHNOLOGY']] = []
                if 'TECHGROUP' in tech:
                    if tech['TECHGROUP'] is not None:
                        #techgroupObj[tech['TECHNOLOGY']].append(tgId[tech['TECHGROUP']])
                        #######################################################################3
                        # tg_list = tech['TECHGROUP'].split(",")
                        # for tg in tg_list:
                        #     techgroupObj[tech['TECHNOLOGY']].append(tgId[tg])
                        techgroupObj[tech['TECHNOLOGY']] = [tgId[x.strip()] for x in tech['TECHGROUP'].split(',')]


            for tech in techs:
                if tech['Tech'] in iarObj:
                    tech['IAR'] = iarObj[tech['Tech']]
                if tech['Tech'] in oarObj:
                    tech['OAR'] = oarObj[tech['Tech']]
                if tech['Tech'] in earObj:
                    tech['EAR'] = earObj[tech['Tech']]
                if tech['Tech'] in techgroupObj:
                    tech['TG'] = techgroupObj[tech['Tech']]

            for stg in stgs:
                if stg['Stg'] in ttsObj:
                    stg['TTS'] = ttsObj[stg['Stg']]
                if stg['Stg'] in tfsObj:
                    stg['TFS'] = tfsObj[stg['Stg']]

            print('TECHS COMMS IAR OAR DONE!')
            print("--- %s seconds ---" % (time.time() - start_time))
            txtOut = txtOut + ("Technlogies, commodities, emissions, years, IAR, OAR, EAR done in --- {} seconds ---{}".format(time.time() - start_time, '\n'))

            genData = {}
            genData["osy-version"] = version
            genData["osy-casename"] = casename
            genData["osy-desc"] = description
            genData["osy-date"] = date
            genData["osy-currency"] = currency
            genData["osy-mo"] = str(mooValue)

            genData["osy-tech"] = techs
            genData["osy-techGroups"] = techgroups
            genData["osy-comm"] = comms
            genData["osy-ts"] = timeslices
            genData["osy-se"] = seasons
            genData["osy-dt"] = daytypes
            genData["osy-dtb"] = dailytimebrackets

            genData["osy-emis"] = emis
            genData["osy-stg"] = stgs
            genData["osy-scenarios"] = self.defaultScenario(True)
            genData["osy-constraints"] = []
            genData["osy-years"] = yearsArray

            casename = genData['osy-casename']

            viewDef = {}
            for group, lists in self.VARIABLES.items():
                for list in lists:
                    viewDef[list['id']] = []


            if not os.path.exists(Path(Config.DATA_STORAGE,casename)):
                os.makedirs(Path(Config.DATA_STORAGE,casename))

            genDataPath = Path( Config.DATA_STORAGE,casename, "genData.json")
            File.writeFile(genData, genDataPath)

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

            print('MODEL STRUCTURE FINISHED!')
            print("--- %s seconds ---" % (time.time() - start_time))
            txtOut = txtOut + ("Model structure finished in --- {} seconds ---{}".format(time.time() - start_time, '\n'))

            xlsObject = {}
            
            if data:
                techName = self.getTechById(techs)
                commName = self.getCommById(comms)
                emiName = self.getEmiById(emis)
                tsName = self.getTsById(timeslices)
                stgName = self.getStgById(stgs)

                for key, array in self.PARAMETERS.items():
                    if key != 'R__':
                        print(key + ' PARAM')
                        #procitaj json file koji odgovara xls objektu i updatuj podatke
                        path = Path(Config.DATA_STORAGE,casename, key +'.json')
                        jsonData = File.readFile(path)                            

                        for a in array:
                            txtOut = txtOut + ("Parameter {} done in  --- {} seconds ---{}".format(a['value'], time.time() - start_time, '\n'))
                            #moramo izbaciti spaces iz naziva parama
                            sheet_name = a['value'].replace(" ", "")

                            #ovi su problem jer nisu jednoznacni kad se skrate na 31 char, poseban slucaj
                            if sheet_name == 'TotalTechnologyModelPeriodActivityUpperLimit':
                                sheet_name = 'TotalTechnologyPeriodActivityUp'
                            if sheet_name == 'TotalTechnologyModelPeriodActivityLowerLimit':
                                sheet_name = 'TotalTechnologyPeriodActivityLo'

                            #max duzina sheet name tako da vse moramo skratit na 31 da bi procitali iz xls sheets
                            if len(sheet_name)>31:
                                sheet_name = sheet_name[0:31]
                                
                            #procitaj podatke iz xls
                            if sheet_name in df_sheet_all:
                                print('sheet_name ', sheet_name)
                                #ako ima podataka u xls napravi bjekat od xls podataka
                                xls = df_sheet_all[sheet_name]
                                xlsData = xls.to_json(orient='records', indent=2)
                                xlsArray = json.loads(xlsData)

                                if key == 'R':
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refR(xlsArray)
                                    xlsObject[key] = self.refR(xlsArray)
                                    jsonData[a['id']]['SC_0'][0]['value'] = xlsObject[key]['RE1']

                                if key == 'RT':
                                    xlsObject[key] = self.refRT(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRT(xlsArray)
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for tech, val in el.items():
                                                t = techName[tech] 
                                                if t in xlsObject[key]:
                                                    el[tech] = xlsObject[key][t]

                                if key == 'RE':
                                    xlsObject[key] = self.refRE(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRE(xlsArray)
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for emi, val in el.items():
                                                e = emiName[emi] 
                                                if e in xlsObject[key]:
                                                    el[emi] = xlsObject[key][e]

                                if key == 'RS':
                                    xlsObject[key] = self.refRS(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRS(xlsArray)
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for stg, val in el.items():
                                                e = stgName[stg] 
                                                if e in xlsObject[key]:
                                                    el[stg] = xlsObject[key][e]

                                if key == 'RY':
                                    xlsObject[key] = self.refRY(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRY(xlsArray)
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for yr, val in el.items():
                                                if int(yr) in xlsObject[key]:
                                                    el[yr] = xlsObject[key][int(yr)]

                                if key == 'RYT':
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for arr in xlsArray:
                                                if arr['TECHNOLOGY'] == techName[el['TechId']]:
                                                    for yr, val in el.items():
                                                        if yr != 'TechId':
                                                            el[yr] = arr[yr]
                                                    break
                                    #File.writeFile( jsonData, path)

                                if key == 'RYC':
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for arr in xlsArray:
                                                if arr['FUEL'] == commName[el['CommId']]:
                                                    for yr, val in el.items():
                                                        if yr != 'CommId':
                                                            el[yr] = arr[yr]
                                                    break
                                    #File.writeFile( jsonData, path)
                
                                if key == 'RYE':
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for arr in xlsArray:
                                                if arr['EMISSION'] == emiName[el['EmisId']]:
                                                    for yr, val in el.items():
                                                        if yr != 'EmisId':
                                                            el[yr] = arr[yr]
                                                    break
                                    #File.writeFile( jsonData, path)

                                if key == 'RYS':
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for arr in xlsArray:
                                                if arr['STORAGE'] == stgName[el['StgId']]:
                                                    for yr, val in el.items():
                                                        if yr != 'StgId':
                                                            el[yr] = arr[yr]
                                                    break

                                if key == 'RYTs':
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            for arr in xlsArray:
                                                # if arr['TIMESLICE'] == el['YearSplit']:
                                                if arr['TIMESLICE'] == tsName[el['TsId']]:
                                                    for yr, val in el.items():
                                                        if yr != 'TsId':
                                                            if str(arr['YEAR']) == yr:
                                                                el[yr] = arr['VALUE']
                                                                break

                                if key == 'RYTCM':
                                    xlsObject[key] = self.refRYTCM(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRYTCM(xlsArray)

                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            t = techName[el['TechId']] 
                                            c = commName[el['CommId']]
                                            m = el['MoId']
                                            if t in xlsObject[key]:
                                                if c in xlsObject[key][t]:
                                                    if m in xlsObject[key][t][c]:
                                                        for yr, val in el.items():
                                                            if yr != 'TechId' and yr != 'CommId' and yr != 'MoId':
                                                                el[yr] = xlsObject[key][t][c][m][yr]

                                if key == 'RYTEM':
                                    xlsObject[key] = self.refRYTEM(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRYTEM(xlsArray)
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            t = techName[el['TechId']] 
                                            e = emiName[el['EmisId']]
                                            m = el['MoId']
                                            if t in xlsObject[key]:
                                                if e in xlsObject[key][t]:
                                                    if m in xlsObject[key][t][e]:
                                                        for yr, val in el.items():
                                                            if yr != 'TechId' and yr != 'EmisId' and yr != 'MoId':
                                                                el[yr] = xlsObject[key][t][e][m][yr]

                                if key == 'RTSM':
                                    xlsObject[key] = self.refRTSM(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRTSM(xlsArray)
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            t = techName[el['TechId']] 
                                            s = stgName[el['StgId']]
                                            m = el['MoId']
                                            if t in xlsObject[key]:
                                                if s in xlsObject[key][t]:
                                                    if m in xlsObject[key][t][s]:
                                                        el['Value'] = xlsObject[key][t][s][m]

                                if key == 'RYTM':
                                    xlsObject[key] = self.refRYTM(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRYTM(xlsArray)
         
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            t = techName[el['TechId']] 
                                            m = el['MoId']
                                            if t in xlsObject[key]:
                                                if m in xlsObject[key][t]:
                                                    for yr, val in el.items():
                                                        if yr != 'TechId' and yr != 'MoId':
                                                            el[yr] = xlsObject[key][t][m][yr]

                                if key == 'RYTTs':
                                    xlsObject[key] = self.refRYTTs(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRYTTs(xlsArray)

                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            t = techName[el['TechId']] 
                                            ts = tsName[el['TsId']]
                                            if t in xlsObject[key]:
                                                if ts in xlsObject[key][t]:
                                                    for yr, val in el.items():
                                                        if yr != 'TechId' and yr != 'TsId':
                                                            el[yr] = xlsObject[key][t][ts][yr]
                            
                                if key == 'RYCTs':
                                    xlsObject[key] = self.refRYCTs(xlsArray)
                                    # if key not in xlsObject:
                                    #     xlsObject[key] = self.refRYCTs(xlsArray)
                                    for sc, obj in jsonData[a['id']].items():
                                        for el in obj:
                                            c = commName[el['CommId']] 
                                            ts = tsName[el['TsId']]
                                            if c in xlsObject[key]:
                                                if ts in xlsObject[key][c]:
                                                    for yr, val in el.items():
                                                        if yr != 'CommId' and yr != 'TsId':
                                                            el[yr] = xlsObject[key][c][ts][yr]

                        File.writeFile( jsonData, path)

            os.remove(self.TEMPLATE_PATH)
            print('IMPOERT FINISHED WITH DATA!')
            print("--- %s seconds ---" % (time.time() - start_time))
            txtOut = txtOut + ("IMPORT FINISHED WITH DATA IN  --- {} seconds ---{}".format( time.time() - start_time, '\n'))
            response = {
                "message": "Import process finished!",
                "status_code": "success",
                "output": txtOut
            }  

            return response
        except(IOError, IndexError):
            #raise IndexError
            response = {
                "message": IOError,
                "status_code": "error",
                "output": IndexError
            }  
        except OSError:
            #raise OSError
            response = {
                "message": IOError,
                "status_code": "error",
                "output": IndexError
            }  
