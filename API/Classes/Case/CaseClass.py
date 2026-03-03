from pathlib import Path
from Classes.Base import Config
from Classes.Base.FileClass import File

class Case:
    def __init__(self, case, genData):
        self.case = case
        self.PARAMETERS = File.readParamFile(Path(Config.DATA_STORAGE, 'Parameters.json'))
        self.genData =  genData
        self.jsonPath = {}
        for group, array in self.PARAMETERS.items():
            if array:
                self.jsonPath[group] = Path(Config.DATA_STORAGE, case, group+".json")

    def default_R(self):
        try:
            scenarios = self.genData['osy-scenarios']
            Rdata = {}
            for rt in self.PARAMETERS['R']:
                Rdata[rt['id']] = {}
                for sc in scenarios:
                    Rdata[rt['id']][sc['ScenarioId']] = []
                    chunk = {}
                    if sc['ScenarioId'] == 'SC_0':
                        chunk['value'] = rt['default']
                    else:
                        chunk['value'] = None
                    Rdata[rt['id']][sc['ScenarioId']].append(chunk)

            # File.writeFile( Rdata, self.Rpath)
            File.writeFile( Rdata, self.jsonPath['R'])
        except(IOError):
            raise

    def default_RY(self):
        try:
            years = self.genData['osy-years']
            scenarios = self.genData['osy-scenarios']
            RYdata = {}
            for ry in self.PARAMETERS['RY']:
                RYdata[ry['id']] = {}
                for sc in scenarios:
                    RYdata[ry['id']][sc['ScenarioId']] = []
                    chunk = {}
                    for year in years:
                        if sc['ScenarioId'] == 'SC_0':
                            chunk[year] = ry['default']
                        else:
                            chunk[year] = None
                    RYdata[ry['id']][sc['ScenarioId']].append(chunk)
            File.writeFile( RYdata, self.jsonPath['RY'])
        except(IOError):
            raise

    def default_RT(self):
        try:
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            RTdata = {}
            for rt in self.PARAMETERS['RT']:
                RTdata[rt['id']] = {}
                for sc in scenarios:
                    RTdata[rt['id']][sc['ScenarioId']] = []
                    chunk = {}
                    for tech in techs:
                        if sc['ScenarioId'] == 'SC_0':
                            chunk[tech['TechId']] = rt['default']
                        else:
                            chunk[tech['TechId']] = None
                    RTdata[rt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RTdata, self.jsonPath['RT'])
        except(IOError):
            raise

    def default_RE(self):
        try:
            emis = self.genData['osy-emis']
            scenarios = self.genData['osy-scenarios']
            REdata = {}
            for rt in self.PARAMETERS['RE']:
                REdata[rt['id']] = {}
                for sc in scenarios:
                    REdata[rt['id']][sc['ScenarioId']] = []
                    chunk = {}
                    for emi in emis:
                        if sc['ScenarioId'] == 'SC_0':
                            chunk[emi['EmisId']] = rt['default']
                        else:
                            chunk[emi['EmisId']] = None
                    REdata[rt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( REdata, self.jsonPath['RE'])
        except(IOError):
            raise

    def default_RS(self):
        try:
            stgs = self.genData['osy-stg']
            scenarios = self.genData['osy-scenarios']
            RSdata = {}
            for rs in self.PARAMETERS['RS']:
                RSdata[rs['id']] = {}
                for sc in scenarios:
                    RSdata[rs['id']][sc['ScenarioId']] = []
                    chunk = {}
                    for stg in stgs:
                        if sc['ScenarioId'] == 'SC_0':
                            chunk[stg['StgId']] = rs['default']
                        else:
                            chunk[stg['StgId']] = None
                    RSdata[rs['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RSdata, self.jsonPath['RS'])
        except(IOError):
            raise
        
    def default_RYCn(self):
        try:
            years = self.genData['osy-years']
            scenarios = self.genData['osy-scenarios']
            constraints = self.genData['osy-constraints']
            
            RYCndata = {}
            for ryt in self.PARAMETERS['RYCn']:
                RYCndata[ryt['id']] = {}
                for sc in scenarios:
                    RYCndata[ryt['id']][sc['ScenarioId']] = []  
                    for con in constraints:
                        chunk = {}
                        chunk['ConId'] = con['ConId']
                        for year in years:
                            if sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYCndata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYCndata, self.jsonPath['RYCn'])
        except(IOError):
            raise

    def default_RYTs(self):
        try:
            years = self.genData['osy-years']
            scenarios = self.genData['osy-scenarios']
            timeslices = self.genData['osy-ts']
            RYTsdata = {}
            for ryt in self.PARAMETERS['RYTs']:
                RYTsdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTsdata[ryt['id']][sc['ScenarioId']] = []    
                    for ts in timeslices:
                        chunk = {}
                        chunk['TsId'] = ts['TsId']
                        for year in years:
                            if sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYTsdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTsdata, self.jsonPath['RYTs'])
        except(IOError):
            raise

    def default_RYDtb(self):
        try:
            years = self.genData['osy-years']
            scenarios = self.genData['osy-scenarios']
            dailytimebrackets = self.genData['osy-dtb']
            RYDtbdata = {}
            for ryt in self.PARAMETERS['RYDtb']:
                RYDtbdata[ryt['id']] = {}
                for sc in scenarios:
                    RYDtbdata[ryt['id']][sc['ScenarioId']] = []    
                    for dtb in dailytimebrackets:
                        chunk = {}
                        chunk['DtbId'] = dtb['DtbId']
                        for year in years:
                            if sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYDtbdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYDtbdata, self.jsonPath['RYDtb'])
        except(IOError):
            raise

    def default_RYSeDt(self):
        try:
            years = self.genData['osy-years']
            seasons = self.genData['osy-se']
            scenarios = self.genData['osy-scenarios']
            daytypes = self.genData['osy-dt']
            
            RYSeDtsdata = {}
            for ryt in self.PARAMETERS['RYSeDt']:
                RYSeDtsdata[ryt['id']] = {}
                for sc in scenarios:
                    RYSeDtsdata[ryt['id']][sc['ScenarioId']] = []  
                    for se in seasons:
                        for dt in daytypes:
                            chunk = {}
                            chunk['SeId'] = se['SeId']
                            chunk['DtId'] = dt['DtId']
                            for year in years:
                                if sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = ryt['default']
                                else:
                                    chunk[year] = None
                            RYSeDtsdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYSeDtsdata, self.jsonPath['RYSeDt'])
        except(IOError):
            raise
           
    def default_RYT(self):
        try:
            years = self.genData['osy-years']
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            
            RYTdata = {}
            for ryt in self.PARAMETERS['RYT']:
                RYTdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTdata[ryt['id']][sc['ScenarioId']] = []
                    for tech in techs:
                        chunk = {}
                        chunk['TechId'] = tech['TechId']
                        for year in years:
                            if sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYTdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTdata, self.jsonPath['RYT'])
        except(IOError):
            raise

    def default_RYS(self):
        try:
            years = self.genData['osy-years']
            stgs = self.genData['osy-stg']
            scenarios = self.genData['osy-scenarios']
            
            RYSdata = {}
            for rys in self.PARAMETERS['RYS']:
                RYSdata[rys['id']] = {}
                for sc in scenarios:
                    RYSdata[rys['id']][sc['ScenarioId']] = []
                    for stg in stgs:
                        chunk = {}
                        chunk['StgId'] = stg['StgId']
                        for year in years:
                            if sc['ScenarioId'] == 'SC_0':
                                chunk[year] = rys['default']
                            else:
                                chunk[year] = None
                        RYSdata[rys['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYSdata, self.jsonPath['RYS'])
        except(IOError):
            raise
        
    def default_RYTCn(self):
        try:
            years = self.genData['osy-years']
            scenarios = self.genData['osy-scenarios']
            constraints = self.genData['osy-constraints']
            
            RYTCndata = {}
            for ryt in self.PARAMETERS['RYTCn']:
                RYTCndata[ryt['id']] = {}
                for sc in scenarios:
                    RYTCndata[ryt['id']][sc['ScenarioId']] = []  
                    for con in constraints:
                        if con['CM']:
                            for tech in con['CM']:
                                chunk = {}
                                chunk['TechId'] = tech
                                chunk['ConId'] = con['ConId']
                                for year in years:
                                    if sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None
                                RYTCndata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTCndata, self.jsonPath['RYTCn'])
        except(IOError):
            raise

    def default_RYTM(self):
        try:
            mo = int(self.genData['osy-mo'])+1
            years = self.genData['osy-years']
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            
            RYTMdata = {}
            for rytm in self.PARAMETERS['RYTM']:
                RYTMdata[rytm['id']] = {}
                for sc in scenarios:
                    RYTMdata[rytm['id']][sc['ScenarioId']] = []
                    for tech in techs:
                        for m in range(1, mo):
                            chunk = {}
                            chunk['TechId'] = tech['TechId']
                            chunk['MoId'] = m
                            for year in years:
                                if sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = rytm['default']
                                else:
                                    chunk[year] = None
                            RYTMdata[rytm['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTMdata, self.jsonPath['RYTM'])
        except(IOError):
            raise

    def default_RYC(self):
        try:
            years = self.genData['osy-years']
            comms = self.genData['osy-comm']
            scenarios = self.genData['osy-scenarios']
            
            RYCdata = {}
            for ryt in self.PARAMETERS['RYC']:
                RYCdata[ryt['id']] = {}
                for sc in scenarios:
                    RYCdata[ryt['id']][sc['ScenarioId']] = []
                    for comm in comms:
                        chunk = {}
                        chunk['CommId'] = comm['CommId']
                        for year in years:
                            if sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYCdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYCdata, self.jsonPath['RYC'])
        except(IOError):
            raise

    def default_RYE(self):
        try:
            years = self.genData['osy-years']
            emis = self.genData['osy-emis']
            scenarios = self.genData['osy-scenarios']
            
            RYEdata = {}
            for ryt in self.PARAMETERS['RYE']:
                RYEdata[ryt['id']] = {}
                for sc in scenarios:
                    RYEdata[ryt['id']][sc['ScenarioId']] = []
                    for emi in emis:
                        chunk = {}
                        chunk['EmisId'] = emi['EmisId']
                        for year in years:
                            if sc['ScenarioId'] == 'SC_0':
                                chunk[year] = ryt['default']
                            else:
                                chunk[year] = None
                        RYEdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYEdata, self.jsonPath['RYE'])
        except(IOError):
            raise

    def default_RYTC(self):
        try:
            years = self.genData['osy-years']
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            
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
                                    if sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None 
                                RYTCdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTCdata, self.jsonPath['RYTC'])
        except(IOError):
            raise

    def default_RYTCM(self):
        try:
            years = self.genData['osy-years']
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            mo = int(self.genData['osy-mo'])+1
            
            RYTCMdata = {}
            for ryt in self.PARAMETERS['RYTCM']:
                RYTCMdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTCMdata[ryt['id']][sc['ScenarioId']] = []  
                    for tech in techs:
                        if tech[ryt['id']]:
                            for comm in tech[ryt['id']]:
                                for m in range(1, mo):
                                    chunk = {}
                                    chunk['TechId'] = tech['TechId']
                                    chunk['CommId'] = comm
                                    chunk['MoId'] = m
                                    for year in years:
                                        if sc['ScenarioId'] == 'SC_0':
                                            chunk[year] = ryt['default']
                                        else:
                                            chunk[year] = None
                                    RYTCMdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTCMdata, self.jsonPath['RYTCM'])
        except(IOError):
            raise

    def default_RYTSM(self):
        try:
            years = self.genData['osy-years']
            stgs = self.genData['osy-stg']
            scenarios = self.genData['osy-scenarios']
            mo = int(self.genData['osy-mo'])+1
            
            RYTSMdata = {}
            for ryt in self.PARAMETERS['RYTSM']:
                RYTSMdata[ryt['id']] = {}
                for sc in scenarios:
                    RYTSMdata[ryt['id']][sc['ScenarioId']] = []  
                    for stg in stgs:
                        if stg[ryt['id']]:
                            #for tech in stg[ryt['id']]:
                            for m in range(1, mo):
                                chunk = {}
                                chunk['StgId'] = stg['StgId']
                                chunk['TechId'] = stg[ryt['id']]
                                chunk['MoId'] = m
                                for year in years:
                                    if sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None
                                RYTSMdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTSMdata, self.jsonPath['RYTSM'])
        except(IOError):
            raise

    def default_RTSM(self):
        try:
            stgs = self.genData['osy-stg']
            scenarios = self.genData['osy-scenarios']
            mo = int(self.genData['osy-mo'])+1
            
            RTSMdata = {}
            for ryt in self.PARAMETERS['RTSM']:
                RTSMdata[ryt['id']] = {}
                for sc in scenarios:
                    RTSMdata[ryt['id']][sc['ScenarioId']] = []  
                    for stg in stgs:
                        if stg[ryt['id']]:
                            #for tech in stg[ryt['id']]:
                            for m in range(1, mo):
                                chunk = {}
                                chunk['StgId'] = stg['StgId']
                                chunk['TechId'] = stg[ryt['id']]
                                chunk['MoId'] = m
                                if sc['ScenarioId'] == 'SC_0':
                                    chunk['Value'] = ryt['default']
                                else:
                                    chunk['Value'] = None
                                RTSMdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RTSMdata, self.jsonPath['RTSM'])
        except(IOError):
            raise
           
    def default_RYTE(self):
        try:
            years = self.genData['osy-years']
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            
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
                                    if sc['ScenarioId'] == 'SC_0':
                                        chunk[year] = ryt['default']
                                    else:
                                        chunk[year] = None
                                RYTEdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTEdata, self.jsonPath['RYTE'])
        except(IOError):
            raise

    def default_RYTEM(self):
        try:
            years = self.genData['osy-years']
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            mo = int(self.genData['osy-mo'])+1
            
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
                                        if sc['ScenarioId'] == 'SC_0':
                                            chunk[year] = ryt['default']
                                        else:
                                            chunk[year] = None
                                    RYTEMdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTEMdata, self.jsonPath['RYTEM'])
        except(IOError):
            raise

    def default_RYTTs(self):
        try:
            years = self.genData['osy-years']
            techs = self.genData['osy-tech']
            scenarios = self.genData['osy-scenarios']
            timeslices = self.genData['osy-ts']
            
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
                                if sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = ryt['default']
                                else:
                                    chunk[year] = None
                            RYTTsdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYTTsdata, self.jsonPath['RYTTs'])
        except(IOError):
            raise

    def default_RYCTs(self):
        try:
            years = self.genData['osy-years']
            comms = self.genData['osy-comm']
            scenarios = self.genData['osy-scenarios']
            timeslices = self.genData['osy-ts']
            
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
                                if sc['ScenarioId'] == 'SC_0':
                                    chunk[year] = ryt['default']
                                else:
                                    chunk[year] = None
                            RYCTsdata[ryt['id']][sc['ScenarioId']].append(chunk)

            File.writeFile( RYCTsdata, self.jsonPath['RYCTs'])
        except(IOError):
            raise

    def createCase(self):
        try:
            for group, array in self.PARAMETERS.items():
                if array:
                    func_name = f"default_{group}"
                    func = getattr(self, func_name)
                    func()
            
        except(IOError):
            raise
