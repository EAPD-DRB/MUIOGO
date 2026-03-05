import os
from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.OsemosysClass import Osemosys
from Classes.Case.CaseClass import Case

class UpdateCase(Osemosys):
    def __init__(self, case, genData):
        Osemosys.__init__(self, case)
        self.genDataUpdate =  genData
        self.case = case

    def update_R(self):
        try:
            rJson = File.readFile(self.rPath) 
            Rsource = self.R(rJson)
            scenarios = self.genDataUpdate['osy-scenarios']
            Rdata = {}
            for r in self.PARAMETERS['R']:
                Rdata[r['id']] = {}
                for sc in scenarios:
                    Rdata[r['id']][sc['ScenarioId']] = []
                    chunk = {}
                    if self.keys_exists(Rsource, r['id'], sc['ScenarioId'], 'value'):
                        chunk['value'] = Rsource[r['id']][sc['ScenarioId']]['value']
                    elif sc['ScenarioId'] == 'SC_0':
                        chunk['value'] = r['default']
                    else:
                        chunk['value'] = None
                    Rdata[r['id']][sc['ScenarioId']].append(chunk)


            File.writeFile( Rdata, self.rPath)
        except(IOError):
            raise IOError

    def update_RY(self):
        try:
            ryJson = File.readFile(self.ryPath) 
            RYsource = self.RY(ryJson)
            years = self.genDataUpdate['osy-years']
            scenarios = self.genDataUpdate['osy-scenarios']

            RYdata = {}
            for ry in self.PARAMETERS['RY']:
                RYdata[ry['id']] = {}
                for sc in scenarios:
                    RYdata[ry['id']][sc['ScenarioId']] = []
                    chunk = {}
                    #chunk['ryVar'] = ry['id']
                    for year in years:
                        if self.keys_exists(RYsource, ry['id'], sc['ScenarioId'], year):
                            chunk[year] = RYsource[ry['id']][sc['ScenarioId']][year]
                        elif sc['ScenarioId'] == 'SC_0':
                            chunk[year] = ry['default']
                        else:
                            chunk[year] = None
                    RYdata[ry['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYdata, self.ryPath)
        except(IOError):
            raise IOError

    def update_RT(self):
        try:
            rtJson = File.readFile(self.rtPath) 
            RTsource = self.RT(rtJson)
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            RTdata = {}
            for rt in self.PARAMETERS['RT']:
                RTdata[rt['id']] = {}
                for sc in scenarios:
                    RTdata[rt['id']][sc['ScenarioId']] = []
                    chunk = {}
                    for tech in techs:
                        if self.keys_exists(RTsource, rt['id'], sc['ScenarioId'], tech['TechId']):
                            chunk[tech['TechId']] = RTsource[rt['id']][sc['ScenarioId']][tech['TechId']]
                        elif sc['ScenarioId'] == 'SC_0':
                            chunk[tech['TechId']] = rt['default']
                        else:
                            chunk[tech['TechId']] = None
                    RTdata[rt['id']][sc['ScenarioId']].append(chunk)
            File.writeFile( RTdata, self.rtPath)
        except(IOError):
            raise IOError

    def update_RE(self):
        try:
            reJson = File.readFile(self.rePath) 
            REsource = self.RE(reJson)
            emis = self.genDataUpdate['osy-emis']
            scenarios = self.genDataUpdate['osy-scenarios']

            RTdata = {}
            for rt in self.PARAMETERS['RE']:
                RTdata[rt['id']] = {}
                for sc in scenarios:
                    RTdata[rt['id']][sc['ScenarioId']] = []
                    chunk = {}
                    for emi in emis:
                        if self.keys_exists(REsource, rt['id'], sc['ScenarioId'], emi['EmisId']):
                            chunk[emi['EmisId']] = REsource[rt['id']][sc['ScenarioId']][emi['EmisId']]
                        elif sc['ScenarioId'] == 'SC_0':
                            chunk[emi['EmisId']] = rt['default']
                        else:
                            chunk[emi['EmisId']] = None
                    RTdata[rt['id']][sc['ScenarioId']].append(chunk)


            File.writeFile( RTdata, self.rePath)
        except(IOError):
            raise IOError

    def update_RS(self):
        try:
            if os.path.isfile(self.rsPath):
                rsJson = File.readFile(self.rsPath) 
                RSsource = self.RS(rsJson)
                stgs = self.genDataUpdate['osy-stg']
                scenarios = self.genDataUpdate['osy-scenarios']

                RSdata = {}
                for rs in self.PARAMETERS['RS']:
                    RSdata[rs['id']] = {}
                    for sc in scenarios:
                        RSdata[rs['id']][sc['ScenarioId']] = []
                        chunk = {}
                        for stg in stgs:
                            if self.keys_exists(RSsource, rs['id'], sc['ScenarioId'], stg['StgId']):
                                chunk[stg['StgId']] = RSsource[rs['id']][sc['ScenarioId']][stg['StgId']]
                            elif sc['ScenarioId'] == 'SC_0':
                                chunk[stg['StgId']] = rs['default']
                            else:
                                chunk[stg['StgId']] = None
                        RSdata[rs['id']][sc['ScenarioId']].append(chunk)
                File.writeFile( RSdata, self.rsPath)
            else:
                case = Case(self.case, self.genDataUpdate)
                case.default_RS()
        except(IOError):
            raise IOError
        
    def update_RTSM(self):
        try:
            if os.path.isfile(self.rtsmPath):
                rtsmJson = File.readFile(self.rtsmPath) 
                RTSMsource = self.RTSM(rtsmJson)

                stgs = self.genDataUpdate['osy-stg']
                scenarios = self.genDataUpdate['osy-scenarios']
                mo = int(self.genDataUpdate['osy-mo'])+1
                
                RTSMdata = {}
                for ryt in self.PARAMETERS['RTSM']:
                    RTSMdata[ryt['id']] = {}
                    for sc in scenarios:
                        RTSMdata[ryt['id']][sc['ScenarioId']] = [] 
                        for stg in stgs:
                            if stg[ryt['id']]:
                                #for tech in stg[ryt['id']]:
                                tech = stg[ryt['id']]
                                for m in range(1, mo):
                                    chunk = {}
                                    chunk['StgId'] = stg['StgId']
                                    chunk['TechId'] = tech
                                    chunk['MoId'] = m
                      
                                    # if RYTCsource[ryt['id']][year][tech['TechId']][emi]:
                                    if self.keys_exists(RTSMsource, ryt['id'], sc['ScenarioId'], stg['StgId'], tech, m):
                                        chunk['Value'] = RTSMsource[ryt['id']][sc['ScenarioId']][stg['StgId']][tech][m]
                                    elif sc['ScenarioId'] == 'SC_0':
                                        chunk['Value'] = ryt['default']
                                    else:
                                        chunk['Value'] = None
                                    RTSMdata[ryt['id']][sc['ScenarioId']].append(chunk)

                File.writeFile( RTSMdata, self.rtsmPath)
            else:
                case = Case(self.case, self.genDataUpdate)
                case.default_RTSM()
        except(IOError):
            raise IOError
        
    def update_RYCn(self):
        try:
            rycnJson = File.readFile(self.rycnPath) 
            RYCnsource = self.RYCn(rycnJson)
            years = self.genDataUpdate['osy-years']
            scenarios = self.genDataUpdate['osy-scenarios']
            constraints = self.genDataUpdate['osy-constraints']
            RYCndata = {}
            for ryt in self.PARAMETERS['RYCn']:
                RYCndata[ryt['id']] = {}
                for sc in scenarios:
                    RYCndata[ryt['id']][sc['ScenarioId']] = []  
                    for con in constraints:
                        chunk = {}
                        chunk['ConId'] = con['ConId']
                        for year in years:
                            if self.keys_exists(RYCnsource, ryt['id'], sc['ScenarioId'], year, con['ConId']):
                                chunk[year] = RYCnsource[ryt['id']][sc['ScenarioId']][year][con['ConId']]
                            elif  sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYCndata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYCndata, self.rycnPath)
        except(IOError):
            raise IOError

    def update_RYT(self):
        try:
            rytJson = File.readFile(self.rytPath) 
            RYTsource = self.RYT(rytJson)
            years = self.genDataUpdate['osy-years']
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            
            RYTdata = {}
            for ryt in self.PARAMETERS['RYT']:
                RYTdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTdata[ryt['id']][sc['ScenarioId']] = []
                    for tech in techs:
                        chunk = {}
                        chunk['TechId'] = tech['TechId']
                        for year in years:
                            if self.keys_exists(RYTsource, ryt['id'], sc['ScenarioId'], year, tech['TechId']):
                                chunk[year] = RYTsource[ryt['id']][sc['ScenarioId']][year][tech['TechId']]

                            elif  sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYTdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTdata, self.rytPath)
        except(IOError):
            raise IOError

    def update_RYS(self):
        try:
            if os.path.isfile(self.rysPath):
                rysJson = File.readFile(self.rysPath) 
                RYSsource = self.RYS(rysJson)
                years = self.genDataUpdate['osy-years']
                stgs = self.genDataUpdate['osy-stg']
                scenarios = self.genDataUpdate['osy-scenarios']
                
                RYSdata = {}
                for rys in self.PARAMETERS['RYS']:
                    RYSdata[rys['id']] = {}
                    for sc in scenarios:
                        RYSdata[rys['id']][sc['ScenarioId']] = []
                        for stg in stgs:
                            chunk = {}
                            chunk['StgId'] = stg['StgId']
                            for year in years:
                                if self.keys_exists(RYSsource, rys['id'], sc['ScenarioId'], year, stg['StgId']):
                                    chunk[year] = RYSsource[rys['id']][sc['ScenarioId']][year][stg['StgId']]

                                elif  sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = rys['default']
                                else:
                                    chunk[year] = None
                            RYSdata[rys['id']][sc['ScenarioId']].append(chunk)

                File.writeFile( RYSdata, self.rysPath)
            else:
                case = Case(self.case, self.genDataUpdate)
                case.default_RYS()
        except(IOError):
            raise IOError
        
    def update_RYTCn(self):
        try:
            rytcnJson = File.readFile(self.rytcnPath) 
            RYTCnsource = self.RYTCn(rytcnJson)
            years = self.genDataUpdate['osy-years']
            scenarios = self.genDataUpdate['osy-scenarios']
            constraints = self.genDataUpdate['osy-constraints']
            
            RYTCndata = {}
            for ryt in self.PARAMETERS['RYTCn']:
                RYTCndata[ryt['id']] = {}
                for sc in scenarios:
                    RYTCndata[ryt['id']][sc['ScenarioId']] = []  
                    for con in constraints:
                        # imamo samo jedan skup tech za constraints
                        # if con[ryt['id']]:
                        if con['CM']:
                            # for tech in con[ryt['id']]:
                            for tech in con['CM']:
                                chunk = {}
                                chunk['TechId'] = tech
                                chunk['ConId'] = con['ConId']
                                for year in years:
                                    if self.keys_exists(RYTCnsource, ryt['id'], sc['ScenarioId'], year, tech, con['ConId']):
                                        chunk[year] = RYTCnsource[ryt['id']][sc['ScenarioId']][year][tech][con['ConId']]
                                    elif sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None
                                RYTCndata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTCndata, self.rytcnPath)
        except(IOError):
            raise IOError

    def update_RYTM(self):
        try:
            rytmJson = File.readFile(self.rytmPath) 
            RYTMsource = self.RYTM(rytmJson)

            mo = int(self.genDataUpdate['osy-mo'])+1
            years = self.genDataUpdate['osy-years']
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            
            RYTMdata = {}
            for ryt in self.PARAMETERS['RYTM']:
                RYTMdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTMdata[ryt['id']][sc['ScenarioId']] = [] 
                    for tech in techs:
                        for m in range(1, mo):
                            chunk = {}
                            chunk['TechId'] = tech['TechId']
                            chunk['MoId'] = m
                            for year in years:
                                if self.keys_exists(RYTMsource, ryt['id'], sc['ScenarioId'], year, tech['TechId'], m):
                                    chunk[year] = RYTMsource[ryt['id']][sc['ScenarioId']][year][tech['TechId']][m]
                                elif sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = ryt['default']
                                else:
                                    chunk[year] = None
                            RYTMdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTMdata, self.rytmPath)

        except(IOError):
            raise IOError

    def update_RYC(self):
        try:
            rycJson = File.readFile(self.rycPath) 
            RYCsource = self.RYC(rycJson)
            years = self.genDataUpdate['osy-years']
            comms = self.genDataUpdate['osy-comm']
            scenarios = self.genDataUpdate['osy-scenarios']
           
            RYCdata = {}
            for ryt in self.PARAMETERS['RYC']:
                RYCdata[ryt['id']] = {}
                for sc in scenarios:
                    RYCdata[ryt['id']][sc['ScenarioId']] = []                
                    for comm in comms:
                        chunk = {}
                        chunk['CommId'] = comm['CommId']
                        for year in years:
                            if self.keys_exists(RYCsource, ryt['id'], sc['ScenarioId'], year, comm['CommId']):
                                chunk[year] = RYCsource[ryt['id']][sc['ScenarioId']][year][comm['CommId']]
                            elif sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYCdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYCdata, self.rycPath)
        except(IOError):
            raise IOError

    def update_RYE(self):
        try:
            ryeJson = File.readFile(self.ryePath) 
            RYEsource = self.RYE(ryeJson)
            years = self.genDataUpdate['osy-years']
            emis = self.genDataUpdate['osy-emis']
            scenarios = self.genDataUpdate['osy-scenarios']
            
            RYEdata = {}
            for ryt in self.PARAMETERS['RYE']:
                RYEdata[ryt['id']] = {}
                for sc in scenarios:
                    RYEdata[ryt['id']][sc['ScenarioId']] = []  
                    for emi in emis:
                        chunk = {}
                        chunk['EmisId'] = emi['EmisId']
                        for year in years:
                            if self.keys_exists(RYEsource, ryt['id'], sc['ScenarioId'], year, emi['EmisId']):
                                chunk[year] = RYEsource[ryt['id']][sc['ScenarioId']][year][emi['EmisId']]
                            elif sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYEdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYEdata, self.ryePath)
        except(IOError):
            raise IOError

    def update_RYTs(self):
        try:
            rytsJson = File.readFile(self.rytsPath) 
            RYTssource = self.RYTs(rytsJson)
            years = self.genDataUpdate['osy-years']
            scenarios = self.genDataUpdate['osy-scenarios']
            timeslices = self.genDataUpdate['osy-ts']            
            RYTsdata = {}
            for ryt in self.PARAMETERS['RYTs']:
                RYTsdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTsdata[ryt['id']][sc['ScenarioId']] = []  
                    for ts in timeslices:
                        chunk = {}
                        chunk['TsId'] = ts['TsId']
                        for year in years:
                            if self.keys_exists(RYTssource, ryt['id'], sc['ScenarioId'], year, ts['TsId']):
                                chunk[year] = RYTssource[ryt['id']][sc['ScenarioId']][year][ts['TsId']]
                            elif sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYTsdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTsdata, self.rytsPath)
        except(IOError):
            raise IOError

    def update_RYDtb(self):
        try:
            if os.path.isfile(self.rydtbPath):
                rydtbJson = File.readFile(self.rydtbPath) 
                RYDtbsource = self.RYDtb(rydtbJson)
                years = self.genDataUpdate['osy-years']
                scenarios = self.genDataUpdate['osy-scenarios']
                dailytimebrackets = self.genDataUpdate['osy-dtb']            
                RYDtbdata = {}
                for ryt in self.PARAMETERS['RYDtb']:
                    RYDtbdata[ryt['id']] = {}
                    for sc in scenarios:
                        RYDtbdata[ryt['id']][sc['ScenarioId']] = []  
                        for dtb in dailytimebrackets:
                            chunk = {}
                            chunk['DtbId'] = dtb['DtbId']
                            for year in years:
                                if self.keys_exists(RYDtbsource, ryt['id'], sc['ScenarioId'], year, dtb['DtbId']):
                                    chunk[year] = RYDtbsource[ryt['id']][sc['ScenarioId']][year][dtb['DtbId']]
                                elif sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = ryt['default']
                                else:
                                    chunk[year] = None
                            RYDtbdata[ryt['id']][sc['ScenarioId']].append(chunk)
                File.writeFile( RYDtbdata, self.rydtbPath)
            else:
                case = Case(self.case, self.genDataUpdate)
                case.default_RYDtb()
            
        except(IOError):
            raise IOError

    def update_RYSeDt(self):
        try:
            if os.path.isfile(self.rysedtPath):
                rysedtJson = File.readFile(self.rysedtPath) 
                RYSeDtsource = self.RYSeDt(rysedtJson)

                years = self.genDataUpdate['osy-years']
                seasons = self.genDataUpdate['osy-se']
                scenarios = self.genDataUpdate['osy-scenarios']
                daytypes = self.genDataUpdate['osy-dt']

                RYSeDtdata = {}
                for ryt in self.PARAMETERS['RYSeDt']:
                    RYSeDtdata[ryt['id']] = {}
                    for sc in scenarios:
                        RYSeDtdata[ryt['id']][sc['ScenarioId']] = []  
                        for se in seasons:
                            for dt in daytypes:
                                chunk = {}
                                chunk['SeId'] = se['SeId']
                                chunk['DtId'] = dt['DtId']
                                for year in years:
                                    if self.keys_exists(RYSeDtsource, ryt['id'], sc['ScenarioId'], year, se['SeId'], dt['DtId']):
                                        chunk[year] = RYSeDtsource[ryt['id']][sc['ScenarioId']][year][se['SeId']][dt['DtId']]
                                    elif sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None
                                RYSeDtdata[ryt['id']][sc['ScenarioId']].append(chunk)

                File.writeFile( RYSeDtdata, self.rysedtPath)
            else:
                case = Case(self.case, self.genDataUpdate)
                case.default_RYSeDt()
        except(IOError):
            raise IOError
              
    def update_RYTC(self):
        try:
            rytcJson = File.readFile(self.rytcPath) 
            RYTCsource = self.RYTC(rytcJson)

            years = self.genDataUpdate['osy-years']
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            
            RYTCdata = {}
            for ryt in self.PARAMETERS['RYTC']:
                RYTCdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTCdata[ryt['id']][sc['ScenarioId']] = [] 
                    for tech in techs:
                        if tech[ryt['id']]:
                            for comm in tech[ryt['id']]:
                                chunk = {}
                                chunk['TechId'] = tech['TechId']
                                chunk['CommId'] = comm
                                for year in years:
                                    if self.keys_exists(RYTCsource, ryt['id'], sc['ScenarioId'], year, tech['TechId'], comm):
                                        chunk[year] = RYTCsource[ryt['id']][sc['ScenarioId']][year][tech['TechId']][comm]
                                    elif sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None
                                RYTCdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTCdata, self.rytcPath)

        except(IOError):
            raise IOError

    def update_RYTCM(self):
        try:
            rytcmJson = File.readFile(self.rytcmPath) 
            RYTCMsource = self.RYTCM(rytcmJson)

            years = self.genDataUpdate['osy-years']
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            mo = int(self.genDataUpdate['osy-mo'])+1
            
            RYTEMdata = {}
            for ryt in self.PARAMETERS['RYTCM']:
                RYTEMdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTEMdata[ryt['id']][sc['ScenarioId']] = [] 
                    for tech in techs:
                        if tech[ryt['id']]:
                            for com in tech[ryt['id']]:
                                for m in range(1, mo):
                                    chunk = {}
                                    chunk['TechId'] = tech['TechId']
                                    chunk['CommId'] = com
                                    chunk['MoId'] = m
                                    for year in years:
                                        # if RYTCsource[ryt['id']][year][tech['TechId']][emi]:
                                        if self.keys_exists(RYTCMsource, ryt['id'], sc['ScenarioId'], year, tech['TechId'], com, m):
                                            chunk[year] = RYTCMsource[ryt['id']][sc['ScenarioId']][year][tech['TechId']][com][m]
                                        elif sc['ScenarioId'] == 'SC_0':
                                            chunk[year] = ryt['default']
                                        else:
                                            chunk[year] = None
                                    RYTEMdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTEMdata, self.rytcmPath)

        except(IOError):
            raise IOError

    def update_RYTSM(self):
        try:
            if os.path.isfile(self.rytsmPath):
                rytsmJson = File.readFile(self.rytsmPath) 
                RYTSMsource = self.RYTSM(rytsmJson)

                years = self.genDataUpdate['osy-years']
                stgs = self.genDataUpdate['osy-stg']
                scenarios = self.genDataUpdate['osy-scenarios']
                mo = int(self.genDataUpdate['osy-mo'])+1
                
                RYTSMdata = {}
                for ryt in self.PARAMETERS['RYTSM']:
                    RYTSMdata[ryt['id']] = {}
                    for sc in scenarios:
                        RYTSMdata[ryt['id']][sc['ScenarioId']] = [] 
                        for stg in stgs:
                            if stg[ryt['id']]:
                                #for tech in stg[ryt['id']]:
                                tech = stg[ryt['id']]
                                for m in range(1, mo):
                                    chunk = {}
                                    chunk['StgId'] = stg['StgId']
                                    chunk['TechId'] = tech
                                    chunk['MoId'] = m
                                    for year in years:
                                        # if RYTCsource[ryt['id']][year][tech['TechId']][emi]:
                                        if self.keys_exists(RYTSMsource, ryt['id'], sc['ScenarioId'], year, stg['StgId'], tech, m):
                                            chunk[year] = RYTSMsource[ryt['id']][sc['ScenarioId']][year][stg['StgId']][tech][m]
                                        elif sc['ScenarioId'] == 'SC_0':
                                            chunk[year] = ryt['default']
                                        else:
                                            chunk[year] = None
                                    RYTSMdata[ryt['id']][sc['ScenarioId']].append(chunk)


                File.writeFile( RYTSMdata, self.rytsmPath)
            else:
                case = Case(self.case, self.genDataUpdate)
                case.default_RYTSM()
        except(IOError):
            raise IOError
        
    def update_RYTE(self):
        try:
            ryteJson = File.readFile(self.rytePath) 
            RYTEsource = self.RYTE(ryteJson)

            years = self.genDataUpdate['osy-years']
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            
            RYTEdata = {}
            for ryt in self.PARAMETERS['RYTE']:
                RYTEdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTEdata[ryt['id']][sc['ScenarioId']] = [] 
                    for tech in techs:
                        if tech[ryt['id']]:
                            for comm in tech[ryt['id']]:
                                chunk = {}
                                chunk['TechId'] = tech['TechId']
                                chunk['EmisId'] = comm
                                for year in years:
                                    # if RYTCsource[ryt['id']][year][tech['TechId']][comm]:
                                    if self.keys_exists(RYTEsource, ryt['id'], sc['ScenarioId'], year, tech['TechId'], comm):
                                        chunk[year] = RYTEsource[ryt['id']][sc['ScenarioId']][year][tech['TechId']][comm]
                                    elif sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None
                                RYTEdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTEdata, self.rytePath)

        except(IOError):
            raise IOError

    def update_RYTEM(self):
        try:
            rytemJson = File.readFile(self.rytemPath) 
            RYTEMsource = self.RYTEM(rytemJson)

            years = self.genDataUpdate['osy-years']
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            mo = int(self.genDataUpdate['osy-mo'])+1
            
            RYTEMdata = {}
            for ryt in self.PARAMETERS['RYTEM']:
                RYTEMdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTEMdata[ryt['id']][sc['ScenarioId']] = [] 
                    for tech in techs:
                        #samo ako tech ima emisije tj. EAR Emission activity ratio, posto smo dodali pored EAR i EACR Emission Activity Change Ratio u grupu RYTEM moramo promijeniti uslov
                        # if tech[ryt['id']]:
                        if tech['EAR']:
                            #for emi in tech[ryt['id']]:
                            for emi in tech['EAR']:
                                for m in range(1, mo):
                                    chunk = {}
                                    chunk['TechId'] = tech['TechId']
                                    chunk['EmisId'] = emi
                                    chunk['MoId'] = m
                                    for year in years:
                                        # if RYTCsource[ryt['id']][year][tech['TechId']][emi]:
                                        if self.keys_exists(RYTEMsource, ryt['id'], sc['ScenarioId'], year, tech['TechId'], emi, m):
                                            chunk[year] = RYTEMsource[ryt['id']][sc['ScenarioId']][year][tech['TechId']][emi][m]
                                        elif sc['ScenarioId'] == 'SC_0':
                                            chunk[year] = ryt['default']
                                        else:
                                            chunk[year] = None
                                    RYTEMdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTEMdata, self.rytemPath)

        except(IOError):
            raise IOError

    def update_RYTTs(self):
        try:
            ryttsJson = File.readFile(self.ryttsPath) 
            RYTTssource = self.RYTTs(ryttsJson)

            years = self.genDataUpdate['osy-years']
            techs = self.genDataUpdate['osy-tech']
            scenarios = self.genDataUpdate['osy-scenarios']
            timeslices = self.genDataUpdate['osy-ts']

            RYTTsdata = {}
            for ryt in self.PARAMETERS['RYTTs']:
                RYTTsdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTTsdata[ryt['id']][sc['ScenarioId']] = []  
                    for tech in techs:
                        for ts in timeslices:
                            chunk = {}
                            chunk['TechId'] = tech['TechId']
                            chunk['TsId'] = ts['TsId']
                            for year in years:
                                if self.keys_exists(RYTTssource, ryt['id'], sc['ScenarioId'], year, tech['TechId'], ts['TsId']):
                                    chunk[year] = RYTTssource[ryt['id']][sc['ScenarioId']][year][tech['TechId']][ts['TsId']]
                                elif sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = ryt['default']
                                else:
                                    chunk[year] = None
                            RYTTsdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTTsdata, self.ryttsPath)
        except(IOError):
            raise IOError

    def update_RYCTs(self):
        try:
            ryctsJson = File.readFile(self.ryctsPath) 
            RYCTssource = self.RYCTs(ryctsJson)

            years = self.genDataUpdate['osy-years']
            comms = self.genDataUpdate['osy-comm']
            scenarios = self.genDataUpdate['osy-scenarios']
            timeslices = self.genDataUpdate['osy-ts']


            RYCTsdata = {}
            for ryt in self.PARAMETERS['RYCTs']:
                RYCTsdata[ryt['id']] = {}
                for sc in scenarios:
                    RYCTsdata[ryt['id']][sc['ScenarioId']] = []  
                    for comm in comms:
                        for ts in timeslices:
                            chunk = {}
                            chunk['CommId'] = comm['CommId']
                            chunk['TsId'] = ts['TsId']
                            for year in years:
                                if self.keys_exists(RYCTssource, ryt['id'], sc['ScenarioId'], year, comm['CommId'], ts['TsId']):
                                    chunk[year] = RYCTssource[ryt['id']][sc['ScenarioId']][year][comm['CommId']][ts['TsId']]
                                elif sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = ryt['default']
                                else:
                                    chunk[year] = None
                            RYCTsdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYCTsdata, self.ryctsPath)
        except(IOError):
            raise IOError
    
    def updateCase(self):
        try:
            for group, array in self.PARAMETERS.items():
                if array:
                    func_name = f"update_{group}"
                    func = getattr(self, func_name)
                    func()
        except(IOError):
            raise IOError
