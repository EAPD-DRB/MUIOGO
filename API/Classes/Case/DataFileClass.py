from pathlib import Path
import pandas as pd
import traceback
import json, shutil, os, time, subprocess
import logging
from collections import defaultdict
from itertools import product

logger = logging.getLogger(__name__)

from Classes.Base import Config
from Classes.Case.OsemosysClass import Osemosys
from Classes.Base.FileClass import File
from Classes.Base.CustomThreadClass import CustomThread
class DataFile(Osemosys):
    # def __init__(self, case):
    #     Osemosys.__init__(self, case)

    def gen_Conversions(self):
        self.seasons = ''
        for seId in self.seIDs:
            self.seasons += '{} '.format(self.seMap[seId]) 

        self.daytypes = ''
        for dtId in self.dtIDs:
            self.daytypes += '{} '.format(self.dtMap[dtId]) 

        self.dailytimebrackets = ''
        for dtbId in self.dtbIDs:
            self.dailytimebrackets += '{} '.format(self.dtbMap[dtbId]) 

        timeslices = self.genData["osy-ts"]
        seasons = self.genData["osy-se"]
        daytypes = self.genData["osy-dt"]
        dailytypebrackets = self.genData["osy-dtb"]

        seString = ''
        dtString = ''
        dtbString = ''
        for ts in timeslices:           
            seString += '{} '.format(ts['Ts'])
            for se in seasons:
                if se['SeId'] == ts['SE']:
                    seString += '{} '.format(1)
                else:
                    seString += '{} '.format(0)

            dtString += '{} '.format(ts['Ts'])
            for dt in daytypes :
                if dt['DtId'] == ts['DT']:
                    dtString += '{} '.format(1)
                else:
                    dtString += '{} '.format(0)


            dtbString += '{} '.format(ts['Ts'])
            for dtb in dailytypebrackets :
                if dtb['DtbId'] == ts['DTB']:
                    dtbString += '{} '.format(1)
                else:
                    dtbString += '{} '.format(0)


            seString += '{}'.format('\n')
            dtString += '{}'.format('\n')
            dtbString += '{}'.format('\n')

        seString += '{}{}'.format(";",'\n')
        dtString += '{}{}'.format(";",'\n')            
        dtbString += '{}{}'.format(";",'\n')

        self.f.write('{} {} {} {} {} {}'.format('param', 'Conversionls','default', 0, ':','\n'))
        self.f.write('{}{}{}'.format(self.seasons, ':=', '\n'))
        self.f.write('{}{}'.format(seString,'\n'))

        self.f.write('{} {} {} {} {} {}'.format('param', 'Conversionld','default', 0, ':','\n'))
        self.f.write('{}{}{}'.format(self.daytypes, ':=', '\n'))
        self.f.write('{}{}'.format(dtString,'\n'))

        self.f.write('{} {} {} {} {} {}'.format('param', 'Conversionlh','default', 0, ':','\n'))
        self.f.write('{}{}{}'.format(self.dailytimebrackets, ':=', '\n'))
        self.f.write('{}{}'.format(dtbString,'\n'))

    def gen_R(self):
        r = self.R(File.readFile(self.rPath))
        for id, param in self.PARAM['R'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for sc in self.scOrder:
                if r[id][sc['ScId']]['value'] is not None and sc['Active'] == True:
                    tmp = r[id][sc['ScId']]['value']
            self.f.write('{} {} {}'.format('RE1', tmp, '\n'))
            self.f.write('{} {}'.format(';', '\n'))

    def gen_RCn(self):
        rcn = self.RCn()
        self.f.write('{} {} {} {} {} {}'.format('param', 'UDCTag','default', -1, ':','\n'))
        self.f.write('{}{}{}'.format(self.cons, ':=', '\n'))
        rcnString = ''
        for conId in self.conIDs:
            if rcn[conId] is not None:
                tmp = rcn[conId]
                rcnString += '{} '.format(tmp)
        self.f.write('{}{}{}'.format('RE1 ', rcnString, '\n'))
        self.f.write('{}{}'.format(';', '\n'))

    def gen_RY(self):
        ry = self.RY(File.readFile(self.ryPath))
        for id, param in self.PARAM['RY'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':','\n'))
            self.f.write('{}{}{}'.format(self.years, ':=', '\n'))
            ryString = ''
            for yearId in self.yearIDs:
                for sc in self.scOrder:
                    if ry[id][sc['ScId']][yearId] is not None and sc['Active'] == True:
                        tmp = ry[id][sc['ScId']][yearId]
                ryString += '{} '.format(tmp)
            self.f.write('{}{}{}'.format('RE1 ', ryString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RT(self):
        rt = self.RT(File.readFile(self.rtPath))
        for id, param in self.PARAM['RT'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':','\n'))
            self.f.write('{}{}{}'.format(self.techs, ':=', '\n'))
            rtString = ''
            for techId in self.techIDs:
                for sc in self.scOrder:
                    if rt[id][sc['ScId']][techId] is not None and sc['Active'] == True:
                        tmp = rt[id][sc['ScId']][techId]
                rtString += '{} '.format(tmp)
            self.f.write('{}{}{}'.format('RE1 ', rtString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RE(self):
        re = self.RE(File.readFile(self.rePath))
        for id, param in self.PARAM['RE'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':','\n'))
            self.f.write('{}{}{}'.format(self.emis, ':=', '\n'))
            reString = ''
            for emiId in self.emiIDs:
                for sc in self.scOrder:
                    if re[id][sc['ScId']][emiId] is not None and sc['Active'] == True:
                        tmp = re[id][sc['ScId']][emiId]
                reString += '{} '.format(tmp)
            self.f.write('{}{}{}'.format('RE1 ', reString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RS(self):
        re = self.RS(File.readFile(self.rsPath))
        for id, param in self.PARAM['RS'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':','\n'))
            self.f.write('{}{}{}'.format(self.stgs, ':=', '\n'))
            rsString = ''
            for stgId in self.stgIDs:
                for sc in self.scOrder:
                    if re[id][sc['ScId']][stgId] is not None and sc['Active'] == True:
                        tmp = re[id][sc['ScId']][stgId]
                rsString += '{} '.format(tmp)
            self.f.write('{}{}{}'.format('RE1 ', rsString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RTSM(self):
        rtsm = self.RTSM(File.readFile(self.rtsmPath))
        for id, param in self.PARAM['RTSM'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for stgId in self.stgIDs:
                regionHeader = True
                rytcString = ''
                defaultValueFlag = False
                for storageTechId in self.storageTechIDs[id][stgId]:
         
                    # self.f.write('{}{}'.format('[RE1,'+ self.techMap[activityTechId] + ','+ self.commMap[activityCommId] +',*,*]:', '\n'))
                    # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    for mod in self.modIds:
                        
                        
                        # for yearId in self.yearIDs:
                        for sc in self.scOrder:
                            rtsmValue = rtsm[id][sc['ScId']][stgId][storageTechId][mod]
                            if rtsmValue is not None and sc['Active'] == True:
                                if rtsmValue != self.defaultValue[id]:
                                    defaultValueFlag = True
                                tmp = rtsmValue
                        rytcString += '{} '.format(tmp)
                if defaultValueFlag:
                    if regionHeader:
                        regionHeader = False   
                        self.f.write('{}{}'.format('[RE1,'+ self.techMap[storageTechId]  +',*,*]:', '\n'))
                        self.f.write('{}{}{}'.format( self.mods, ':=', '\n'))
                    self.f.write('{} {}{}'.format(self.stgMap[stgId], rytcString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYCn(self):
        rycn = self.RYCn(File.readFile(self.rycnPath))
        for id, param in self.PARAM['RYCn'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            self.f.write('{} {}'.format('[RE1,*,*]:', '\n'))
            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
            for conId in self.conIDs:
                rycnString = ''
                for yearId in self.yearIDs:
                    for sc in self.scOrder:
                        if rycn[id][sc['ScId']][yearId][conId] is not None and sc['Active'] == True:
                            tmp = rycn[id][sc['ScId']][yearId][conId]
                    rycnString += '{} '.format(tmp)
                self.f.write('{} {}{}'.format(self.conMap[conId], rycnString, '\n'))
        self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTs(self):
        ryts = self.RYTs(File.readFile(self.rytsPath))
        for id, param in self.PARAM['RYTs'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':','\n'))
            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
            for timesliceId in self.timesliceIDs:
                rytsString = ''
                #defaultValueFlag = False
                for yearId in self.yearIDs:
                    for sc in self.scOrder:
                        rytsValue = ryts[id][sc['ScId']][yearId][timesliceId]
                        if rytsValue is not None and sc['Active'] == True:
                            # if rytsValue != self.defaultValue[id]:
                            #     defaultValueFlag = True
                            tmp = rytsValue
                    rytsString += '{} '.format(tmp)
                #if defaultValueFlag:                        
                self.f.write('{} {}{}'.format(self.tsMap[timesliceId], rytsString, '\n'))
        self.f.write('{}{}'.format(';', '\n'))

    def gen_RYDtb(self):
        rydtb = self.RYDtb(File.readFile(self.rydtbPath))
        for id, param in self.PARAM['RYDtb'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':','\n'))
            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
            for dtbId in self.dtbIDs:
                rydtbString = ''
                #defaultValueFlag = False
                for yearId in self.yearIDs:
                    for sc in self.scOrder:
                        rydtbValue = rydtb[id][sc['ScId']][yearId][dtbId]
                        if rydtbValue is not None and sc['Active'] == True:
                            # if rytsValue != self.defaultValue[id]:
                            #     defaultValueFlag = True
                            tmp = rydtbValue
                    rydtbString += '{} '.format(tmp)
                #if defaultValueFlag:                        
                self.f.write('{} {}{}'.format(self.dtbMap[dtbId], rydtbString, '\n'))
        self.f.write('{}{}'.format(';', '\n'))

    def gen_RYSeDt(self):
        rysedt = self.RYSeDt(File.readFile(self.rysedtPath))
        for id, param in self.PARAM['RYSeDt'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for seId in self.seIDs:
                regionHeader = True
                # self.f.write('{} {}'.format('[RE1,'+ self.commMap[commId] +',*,*]:', '\n'))
                # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                for dtId in self.dtIDs:
                    rysedtString = ''
                    defaultValueFlag = False
                    for yearId in self.yearIDs:
                        for sc in self.scOrder:
                            rysedtValue = rysedt[id][sc['ScId']][yearId][seId][dtId]
                            if rysedtValue is not None and sc['Active'] == True:
                                if rysedtValue != self.defaultValue[id]:
                                    defaultValueFlag = True
                                tmp = rysedtValue
                        rysedtString += '{} '.format(tmp)
                    if defaultValueFlag:
                        if regionHeader:
                            regionHeader = False   
                            # self.f.write('{} {}'.format('[RE1,'+ self.seMap[seId] +',*,*]:', '\n'))
                            self.f.write('{} {}'.format('['+ str(self.seMap[seId]) +',*,*]:', '\n'))
                            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                        self.f.write('{} {}{}'.format(self.dtMap[dtId], rysedtString, '\n'))
        self.f.write('{}{}'.format(';', '\n'))

    def gen_RYT(self):
        ryt = self.RYT(File.readFile(self.rytPath))

        for id, param in self.PARAM['RYT'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            regionHeader = True
            for techId in self.techIDs:
                rytString = ''
                defaultValueFlag = False
                for yearId in self.yearIDs:
                    for sc in self.scOrder:
                        rytValue = ryt[id][sc['ScId']][yearId][techId]
                        if rytValue is not None and sc['Active'] == True:
                            if rytValue != self.defaultValue[id]:
                                defaultValueFlag = True
                            tmp = rytValue
                    #if defaultValueFlag:
                    rytString += '{} '.format(tmp)
                if defaultValueFlag:
                    if regionHeader:
                        regionHeader = False   
                        self.f.write('{} {}'.format('[RE1,*,*]:', '\n'))
                        self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    self.f.write('{} {}{}'.format(self.techMap[techId], rytString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYS(self):
        rys = self.RYS(File.readFile(self.rysPath))

        for id, param in self.PARAM['RYS'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            regionHeader = True
            for stgId in self.stgIDs:
                rysString = ''
                defaultValueFlag = False
                for yearId in self.yearIDs:
                    for sc in self.scOrder:
                        rysValue = rys[id][sc['ScId']][yearId][stgId]
                        if rysValue is not None and sc['Active'] == True:
                            if rysValue != self.defaultValue[id]:
                                defaultValueFlag = True
                            tmp = rysValue
                    #if defaultValueFlag:
                    rysString += '{} '.format(tmp)
                if defaultValueFlag:
                    if regionHeader:
                        regionHeader = False   
                        self.f.write('{} {}'.format('[RE1,*,*]:', '\n'))
                        self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    self.f.write('{} {}{}'.format(self.stgMap[stgId], rysString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTCn(self):
        rytcn = self.RYTCn(File.readFile(self.rytcnPath))
        for id, param in self.PARAM['RYTCn'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for conId in self.conIDs:
                
                if self.keys_exists(self.constraintTechIDs, id, conId):
                    for constraintTechId in self.constraintTechIDs[id][conId]:
                        regionHeader = True
                        defaultValueFlag = False
                        # self.f.write('{}{}'.format('[RE1,'+ self.techMap[constraintTechId] +',*,*]:', '\n'))
                        # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                        rytcnString = ''
                        for yearId in self.yearIDs:
                            for sc in self.scOrder:
                                rytcnValue = rytcn[id][sc['ScId']][yearId][constraintTechId][conId]
                                if rytcnValue is not None and sc['Active'] == True:
                                    if rytcnValue != self.defaultValue[id]:
                                        defaultValueFlag = True
                                    tmp = rytcnValue
                            rytcnString += '{} '.format(tmp)
                        if defaultValueFlag:
                            if regionHeader:
                                regionHeader = False   
                                self.f.write('{}{}'.format('[RE1,'+ self.techMap[constraintTechId] +',*,*]:', '\n'))
                                self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                            self.f.write('{} {}{}'.format(self.conMap[conId], rytcnString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTM(self):
        rytm = self.RYTM(File.readFile(self.rytmPath))
        for id, param in self.PARAM['RYTM'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            
            for techId in self.techIDs:
                regionHeader = True
                # self.f.write('{} {}'.format('[RE1,'+ self.techMap[techId] +',*,*]:', '\n'))
                # self.f.write('{}{}{}'.format(self.years, ':=', '\n'))
                for mod in self.modIds:
                    rytmString = ''
                    defaultValueFlag = False
                    for yearId in self.yearIDs:
                        for sc in self.scOrder:
                            rytmValue = rytm[id][sc['ScId']][yearId][techId][mod]
                            if rytmValue is not None and sc['Active'] == True:
                                if rytmValue != self.defaultValue[id]:
                                    defaultValueFlag = True
                                tmp = rytmValue
                        rytmString += '{} '.format(tmp)
                    if defaultValueFlag:
                        if regionHeader:
                            regionHeader = False   
                            self.f.write('{} {}'.format('[RE1,'+ self.techMap[techId] +',*,*]:', '\n'))
                            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                        self.f.write('{} {}{}'.format(mod, rytmString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYC(self):
        ryc = self.RYC(File.readFile(self.rycPath))
        for id, param in self.PARAM['RYC'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            # self.f.write('{} {}'.format('[RE1,*,*]:', '\n'))
            # self.f.write('{}{}{}'.format(self.years, ':=', '\n'))
            regionHeader = True
            for commId in self.commIDs:
                rycString = ''
                defaultValueFlag = False
                for yearId in self.yearIDs:
                    for sc in self.scOrder:
                        rycValue = ryc[id][sc['ScId']][yearId][commId]
                        if rycValue is not None and sc['Active'] == True:
                            if rycValue != self.defaultValue[id]:
                                defaultValueFlag = True
                            tmp = rycValue
                    rycString += '{} '.format(tmp)
                if defaultValueFlag:
                    if regionHeader:
                        regionHeader = False   
                        self.f.write('{} {}'.format('[RE1,*,*]:', '\n'))
                        self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    self.f.write('{} {}{}'.format(self.commMap[commId], rycString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYE(self):
        rye = self.RYE(File.readFile(self.ryePath))
        for id, param in self.PARAM['RYE'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            regionHeader = True
            # self.f.write('{} {}'.format('[RE1,*,*]:', '\n'))
            # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
            for emiId in self.emiIDs:
                ryeString = ''
                defaultValueFlag = False
                for yearId in self.yearIDs:
                    for sc in self.scOrder:
                        ryeValue = rye[id][sc['ScId']][yearId][emiId]
                        if ryeValue is not None and sc['Active'] == True:
                            if ryeValue != self.defaultValue[id]:
                                defaultValueFlag = True
                            tmp = ryeValue
                    ryeString += '{} '.format(tmp)
                if defaultValueFlag:
                    if regionHeader:
                        regionHeader = False   
                        self.f.write('{} {}'.format('[RE1,*,*]:', '\n'))
                        self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    self.f.write('{} {}{}'.format(self.emiMap[emiId], ryeString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTC(self):
        rytc = self.RYTC(File.readFile(self.rytcPath))
        for id, param in self.PARAM['RYTC'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for inputCapTechId in self.inputCapTechIds[id]:
                regionHeader = True
                for inputCapCommId in self.inputCapCommIds[id][inputCapTechId]:
                    rytcString = ''
                    defaultValueFlag = False
                    for yearId in self.yearIDs:
                        for sc in self.scOrder:
                            rytcValue = rytc[id][sc['ScId']][yearId][inputCapTechId][inputCapCommId]
                            if rytcValue is not None and sc['Active'] == True:
                                if rytcValue != self.defaultValue[id]:
                                    defaultValueFlag = True
                                tmp = rytcValue
                        rytcString += '{} '.format(tmp)
                    if defaultValueFlag:
                        if regionHeader:
                            regionHeader = False   
                            self.f.write('{}{}'.format('[RE1,'+ self.techMap[inputCapTechId] + ',*,*]:', '\n'))
                            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                        self.f.write('{} {}{}'.format(self.commMap[inputCapCommId], rytcString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTCM(self):
        rytcm = self.RYTCM(File.readFile(self.rytcmPath))
        for id, param in self.PARAM['RYTCM'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for activityTechId in self.activityTechIDs[id]:
                for activityCommId in self.activityCommIDs[id][activityTechId]:
                    regionHeader = True
                    # self.f.write('{}{}'.format('[RE1,'+ self.techMap[activityTechId] + ','+ self.commMap[activityCommId] +',*,*]:', '\n'))
                    # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    for mod in self.modIds:
                        rytcString = ''
                        defaultValueFlag = False
                        for yearId in self.yearIDs:
                            for sc in self.scOrder:
                                rytcmValue = rytcm[id][sc['ScId']][yearId][activityTechId][activityCommId][mod]
                                if rytcmValue is not None and sc['Active'] == True:
                                    if rytcmValue != self.defaultValue[id]:
                                        defaultValueFlag = True
                                    tmp = rytcmValue
                            rytcString += '{} '.format(tmp)
                        if defaultValueFlag:
                            if regionHeader:
                                regionHeader = False   
                                self.f.write('{}{}'.format('[RE1,'+ self.techMap[activityTechId] + ','+ self.commMap[activityCommId] +',*,*]:', '\n'))
                                self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                            self.f.write('{} {}{}'.format(mod, rytcString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTSM(self):
        rytsm = self.RYTSM(File.readFile(self.rytsmPath))
        for id, param in self.PARAM['RYTSM'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for stgId in self.stgIDs:
                
                for storageTechId in self.storageTechIDs[id][stgId]:
                    regionHeader = True
                    # self.f.write('{}{}'.format('[RE1,'+ self.techMap[activityTechId] + ','+ self.commMap[activityCommId] +',*,*]:', '\n'))
                    # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    for mod in self.modIds:
                        rytcString = ''
                        defaultValueFlag = False
                        for yearId in self.yearIDs:
                            for sc in self.scOrder:
                                rytsmValue = rytsm[id][sc['ScId']][yearId][stgId][storageTechId][mod]
                                if rytsmValue is not None and sc['Active'] == True:
                                    if rytsmValue != self.defaultValue[id]:
                                        defaultValueFlag = True
                                    tmp = rytsmValue
                            rytcString += '{} '.format(tmp)
                        if defaultValueFlag:
                            if regionHeader:
                                regionHeader = False   
                                self.f.write('{}{}'.format('[RE1,'+ self.stgMap[stgId] + ','+ self.techMap[storageTechId] +',*,*]:', '\n'))
                                self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                            self.f.write('{} {}{}'.format(mod, rytcString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTE(self):
        ryte = self.RYTE(File.readFile(self.rytePath))
        for id, param in self.PARAM['RYTE'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for emissionTechId in self.emissionTechIDs[id]:
                regionHeader = True
                for activityEmissionId in self.activityEmissionIDs[id][emissionTechId]:
                    defaultValueFlag = False
                    ryteString = ''
                    for yearId in self.yearIDs:
                        for sc in self.scOrder:
                            ryteValue = ryte[id][sc['ScId']][yearId][emissionTechId][activityEmissionId]
                            if ryteValue is not None and sc['Active'] == True:
                                if ryteValue != self.defaultValue[id]:
                                    defaultValueFlag = True
                                tmp = ryteValue
                        ryteString += '{} '.format(tmp)
                    if defaultValueFlag:
                        if regionHeader:
                            regionHeader = False   
                            self.f.write('{}{}'.format('[RE1,'+ self.techMap[emissionTechId] +  ','+ self.emiMap[activityEmissionId] + ',*,*]:', '\n'))
                            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                        self.f.write('{} {}{}'.format(1, ryteString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTEM(self):
        rytem = self.RYTEM(File.readFile(self.rytemPath))
        for id, param in self.PARAM['RYTEM'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for emissionTechId in self.emissionTechIDs[id]:
                for activityEmissionId in self.activityEmissionIDs[id][emissionTechId]:
                    regionHeader = True
                    # self.f.write('{}{}'.format('[RE1,'+ self.techMap[emissionTechId] +  ','+ self.emiMap[activityEmissionId] + ',*,*]:', '\n'))
                    # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                    for mod in self.modIds:
                        ryteString = ''
                        defaultValueFlag = False
                        for yearId in self.yearIDs:
                            for sc in self.scOrder:
                                rytemValue = rytem[id][sc['ScId']][yearId][emissionTechId][activityEmissionId][mod]
                                if rytemValue is not None and sc['Active'] == True:
                                    if rytemValue != self.defaultValue[id]:
                                        defaultValueFlag = True
                                    tmp = rytemValue
                            ryteString += '{} '.format(tmp)
                        if defaultValueFlag:
                            if regionHeader:
                                regionHeader = False   
                                self.f.write('{}{}'.format('[RE1,'+ self.techMap[emissionTechId] +  ','+ self.emiMap[activityEmissionId] + ',*,*]:', '\n'))
                                self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                            self.f.write('{} {}{}'.format(mod, ryteString, '\n'))
            self.f.write('{}{}'.format(';', '\n'))

    def gen_RYTTs(self):
        rytts = self.RYTTs(File.readFile(self.ryttsPath))
        for id, param in self.PARAM['RYTTs'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for techId in self.techIDs:
                regionHeader = True
                # self.f.write('{} {}'.format('[RE1,'+ self.techMap[techId] +',*,*]:', '\n'))
                # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                for timesliceId in self.timesliceIDs:
                    ryttsString = ''
                    defaultValueFlag = False
                    for yearId in self.yearIDs:
                        for sc in self.scOrder:
                            ryttsValue =  rytts[id][sc['ScId']][yearId][techId][timesliceId]
                            if ryttsValue is not None and sc['Active'] == True:
                                if ryttsValue != self.defaultValue[id]:
                                    defaultValueFlag = True
                                tmp = ryttsValue
                        ryttsString += '{} '.format(tmp)
                    if defaultValueFlag:
                        if regionHeader:
                            regionHeader = False   
                            self.f.write('{} {}'.format('[RE1,'+ self.techMap[techId] +',*,*]:', '\n'))
                            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                        self.f.write('{} {}{}'.format(self.tsMap[timesliceId], ryttsString, '\n'))
        self.f.write('{}{}'.format(';', '\n'))

    def gen_RYCTs(self):
        rycts = self.RYCTs(File.readFile(self.ryctsPath))
        for id, param in self.PARAM['RYCTs'].items():
            self.f.write('{} {} {} {} {} {}'.format('param', param,'default', self.defaultValue[id], ':=','\n'))
            for commId in self.commIDs:
                regionHeader = True
                # self.f.write('{} {}'.format('[RE1,'+ self.commMap[commId] +',*,*]:', '\n'))
                # self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                for timesliceId in self.timesliceIDs:
                    ryctsString = ''
                    defaultValueFlag = False
                    for yearId in self.yearIDs:
                        for sc in self.scOrder:
                            ryctsValue = rycts[id][sc['ScId']][yearId][commId][timesliceId]
                            if ryctsValue is not None and sc['Active'] == True:
                                if ryctsValue != self.defaultValue[id]:
                                    defaultValueFlag = True
                                tmp = ryctsValue
                        ryctsString += '{} '.format(tmp)
                    if defaultValueFlag:
                        if regionHeader:
                            regionHeader = False   
                            self.f.write('{} {}'.format('[RE1,'+ self.commMap[commId] +',*,*]:', '\n'))
                            self.f.write('{}{}{}'.format( self.years, ':=', '\n'))
                        self.f.write('{} {}{}'.format(self.tsMap[timesliceId], ryctsString, '\n'))
        self.f.write('{}{}'.format(';', '\n'))

    def generateDatafile( self, caserunname ):
        try:
            self.defaultValue = self.getParamDefaultValues()
            self.emiIDs = self.getEmiIds()
            self.stgIDs = self.getStgIds()
            self.techIDs = self.getTechIds()
            self.commIDs = self.getCommIds()
            self.conIDs = self.getConIds()
            self.scOrder = self.getScOrder(caserunname)

            self.emiMap = self.getEmisMap()
            self.techMap = self.getTechsMap()
            self.tsMap = self.getTsMap()
            self.commMap = self.getCommsMap()
            self.conMap = self.getConsMap()
            self.stgMap = self.getStgMap()
            self.StgByType = self.getStgByType()

            self.seIDs = self.getSeIds()
            self.seMap = self.getSeMap()
            self.dtIDs = self.getDtIds()
            self.dtMap = self.getDtMap()
            self.dtbIDs = self.getDtbIds()
            self.dtbMap = self.getDtbMap()
            
            self.yearIDs = self.getYears()
            # self.timesliceIDs = self.getTimeslices()
            self.timesliceIDs = self.getTsIds()
            self.modIds = self.getMods()

            self.activityTechIDs = self.getActivityTechIds()
            self.activityCommIDs = self.getActivityCommIds()

            self.storageTechIDs = self.getStorageTechIds()

            self.inputCapTechIds = self.getInputCapTechIds()
            self.inputCapCommIds = self.getInputCapCommIds()

            self.emissionTechIDs = self.getActivityEmissionTechIds()
            self.activityEmissionIDs = self.getActivityEmisionIds()

            self.constraintTechIDs = self.getConstraintTechIds()

            self.stgs = ''
            for stgId in self.stgIDs:
                self.stgs += '{} '.format(self.stgMap[stgId]) 

            self.yearlyStgs = ''
            self.dailyStgs = ''
            for stgType, sbt in self.StgByType.items():
                if stgType == 'Yearly':
                    for s in sbt:
                        self.yearlyStgs += '{} '.format(s) 
                else:
                    for s in sbt:
                        self.dailyStgs += '{} '.format(s)      

            self.techs = ''
            for techId in self.techIDs:
                self.techs += '{} '.format(self.techMap[techId]) 

            self.comms = ''
            for commId in self.commIDs:
                self.comms += '{} '.format(self.commMap[commId]) 

            self.emis = ''
            for emiId in self.emiIDs:
                self.emis += '{} '.format(self.emiMap[emiId])

            self.years = ''
            for yearId in self.yearIDs:
               self.years += '{} '.format(yearId)

            self.timeslices = ''
            for timesliceId in self.timesliceIDs:
                self.timeslices += '{} '.format(self.tsMap[timesliceId])

            self.seasons = ''
            for seId in self.seIDs:
                self.seasons += '{} '.format(self.seMap[seId]) 

            self.daytypes = ''
            for dtId in self.dtIDs:
                self.daytypes += '{} '.format(self.dtMap[dtId]) 

            self.dailytimebrackets = ''
            for dtbId in self.dtbIDs:
                self.dailytimebrackets += '{} '.format(self.dtbMap[dtbId]) 

            self.mods = ''
            for modId in self.modIds:
                self.mods += '{} '.format(modId)

            self.cons = ''
            for conId in self.conIDs:
                self.cons += '{} '.format(self.conMap[conId])

            # path = '"{}"'.format(self.resPath.resolve())
            self.resPath = Path('..', '..', '..', '..', 'WebAPP', 'DataStorage', self.case, 'res',caserunname, 'csv')
            path = '"{}"'.format(self.resPath)

            dataFilePath = Path(Config.DATA_STORAGE, self.case, 'res',caserunname,'data.txt')


            # self.f = open(self.dataFile, mode="w", encoding='utf-8')
            #self.f = open(dataFilePath, mode="w", encoding='utf-8')

            with open(dataFilePath, "w", encoding="utf-8") as self.f:
                #f.write(json.dumps(data, ensure_ascii=False,  indent=4, sort_keys=False))
                self.f.write('####################\n#Sets#\n####################\n')
                self.f.write('{} {}'.format('#', '\n'))
               
                self.f.write('{} {} {} {}{}{}'.format('set', 'REGION',':=', 'RE1', ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'TECHNOLOGY',':=', self.techs, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'COMMODITY',':=', self.comms, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'EMISSION',':=', self.emis, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'STORAGE',':=',self.stgs, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'YEAR',':=', self.years, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'SEASON',':=', self.seasons, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'DAYTYPE',':=', self.daytypes, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'DAILYTIMEBRACKET',':=', self.dailytimebrackets, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'TIMESLICE',':=', self.timeslices, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'MODE_OF_OPERATION',':=', self.mods, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'STORAGEINTRADAY',':=', self.dailyStgs, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'STORAGEINTRAYEAR',':=', self.yearlyStgs, ';', '\n'))
                self.f.write('{} {} {} {}{}{}'.format('set', 'UDC',':=', self.cons, ';', '\n'))
                self.f.write('####################\n#Parameters#\n####################\n')

                #path
                # self.f.write('{}{}'.format('#', '\n'))
                # self.f.write('{} {} {} {} {} {}'.format('param', 'ResultsPath',':=', path, ';', '\n'))
                # self.f.write('{}{}'.format('', '\n'))
                
                #trade route hard code
                self.f.write('{} {} {} {} {} {}'.format('param', 'TradeRoute ','default', '0', ':=','\n'))
                self.f.write('{} {}'.format(';', '\n'))
                self.f.write('{} {}'.format('', '\n'))

                #hard code to test 
                # self.f.write('{} {} {} {} {} {}'.format('param', 'DaysInDayType ','default', '0', ':=','\n'))
                # self.f.write('{} {}'.format(';', '\n'))
                # self.f.write('{} {}'.format('', '\n'))

                self.gen_Conversions()
                self.gen_RCn()
                #dznamicaly call function depending on defined params
                for group, array in self.PARAM.items():
                    if array:
                        func_name = Config.GEN_F[group]
                        func = getattr(self,func_name) 
                        func() 

                self.f.write('{}{}'.format('#', '\n'))
                self.f.write('{}'.format('end;'))
            # self.f.close
            # if not os.path.exists(Path(Config.DATA_STORAGE,self.case,'res', 'csv')):
            #     resName = Path(Config.DATA_STORAGE,self.case,'res', 'csv')
            #     os.makedirs(resName, mode=0o777, exist_ok=False)

                #os.makedirs(name,0777)

        #ovako prosljedjujemo exception u prethodnom slucaju vracamo response u funkciju koja poziva writeFile
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def createCaseRun(self, caserunname, data):
        try:
            caseRunPath = Path(Config.DATA_STORAGE,self.case,'res', caserunname)
            csvPath = Path(Config.DATA_STORAGE,self.case,'res', caserunname, 'csv')
            resDataPath = Path(Config.DATA_STORAGE,self.case,'view', 'resData.json')

            if not os.path.exists(caseRunPath):
                os.makedirs(caseRunPath)
                os.makedirs(csvPath)
                if not os.path.exists(resDataPath):
                    File.writeFile( data, resDataPath)
                else:
                    resData = File.readFile(resDataPath)
                    resData['osy-cases'].append(data)
                    File.writeFile( resData, resDataPath)
                response = {
                    "message": "You have created a case run!",
                    "status_code": "success"
                } 
            else:
                response = {
                    "message": "Case with same name already exists!",
                    "status_code": "exist"
                } 

            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def deleteScenarioCaseRuns(self, scenarioId):
        try:
            resData = File.readFile(self.resDataPath)
            cases = resData['osy-cases']

            for cs in cases:
                for sc in cs['Scenarios']:
                    if sc['ScenarioId'] == scenarioId:
                        cs['Scenarios'].remove(sc)


            File.writeFile(resData, self.resDataPath)
            response = {
                "message": "You have deleted scenario from caseruns!",
                "status_code": "success"
            } 


            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def updateCaseRun(self, caserunname, oldcaserunname, data):
        try:
            caseRunPath = Path(Config.DATA_STORAGE,self.case,'res', oldcaserunname)
            newcaseRunPath = Path(Config.DATA_STORAGE,self.case,'res', caserunname)
            csvPath = Path(Config.DATA_STORAGE,self.case,'res', caserunname, 'csv')
            resDataPath = Path(Config.DATA_STORAGE,self.case,'view', 'resData.json')

            if not os.path.exists(newcaseRunPath):
                os.rename(caseRunPath, newcaseRunPath)

                if not os.path.exists(csvPath):
                    os.makedirs(csvPath)

                resData = File.readFile(resDataPath)

                resdata = resData['osy-cases']
                for i, case in enumerate(resdata):
                    if case['Case'] == oldcaserunname:
                        resData['osy-cases'][i] = data

                File.writeFile( resData, resDataPath)
                response = {
                    "message": "You have updated a case run!",
                    "status_code": "success"
                } 
            elif os.path.exists(newcaseRunPath) and caserunname==oldcaserunname:
                if not os.path.exists(csvPath):
                    os.makedirs(csvPath)

                resData = File.readFile(resDataPath)

                resdata = resData['osy-cases']
                for i, case in enumerate(resdata):
                    if case['Case'] == oldcaserunname:
                        resData['osy-cases'][i] = data

                File.writeFile( resData, resDataPath)
                response = {
                    "message": "You have updated a case run!",
                    "status_code": "success"
                } 
            else:
                response = {
                    "message": "Case with same name already exists!",
                    "status_code": "exist"
                } 

            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def deleteCaseResultsJSON(self, caserunname):
        try:
            csvPath = Path(self.resultsPath, caserunname, "csv")
            if os.path.exists(csvPath):
                shutil.rmtree(csvPath)

            for group, array in self.VARIABLES.items():
                #if group != 'RYS':
                path = Path(self.viewFolderPath, group+'.json')
                if path.is_file():
                    jsonFile = File.readFile(path)
                    for obj in array:
                        #potrebna provjera jer smo u 4.5 verziji dodali varijablu EBAC i dolazilo je do greske jer nije bilo u reyultataima
                        if obj['id'] in jsonFile:
                            if caserunname in jsonFile[obj['id']]:
                                del jsonFile[obj['id']][caserunname]
                    File.writeFile(jsonFile, path)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError
        
    def deleteCaseRun(self, caserunname, resultsOnly):
        try:
            #caseRunPath = Path(Config.DATA_STORAGE,self.case,'res', caserunname)
            #resDataPath = Path(Config.DATA_STORAGE,self.case,'view', 'resData.json')


            if not resultsOnly:
                resData = File.readFile(self.resDataPath)

                for obj in resData['osy-cases']:
                    if obj['Case'] == caserunname:
                        resData['osy-cases'].remove(obj)

                File.writeFile( resData, self.resDataPath)

            #delete from view folder
            for group, array in self.VARIABLES.items():
                #if group != 'RYS':
                path = Path(self.viewFolderPath, group+'.json')
                if path.is_file():
                    jsonFile = File.readFile(path)
                    for obj in array:
                        if obj['id'] in jsonFile:
                            if caserunname in jsonFile[obj['id']]:
                                del jsonFile[obj['id']][caserunname]
                    File.writeFile(jsonFile, path)
                    
            response = {
                "message": "You have deleted a case run!",
                "status_code": "success"
            } 

            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def cleanUp(self):
        try:

            #delete from view folder
            # moramo izbrisati res i view folder ostaviti samo resData.json i viewDefinitions.json

            # self.resultsPath = Path(Config.DATA_STORAGE,case,'res')
            # self.viewFolderPath = Path(Config.DATA_STORAGE,case,'view')
            # folder_path = "C:/putanja/do/foldera"

            for caserunname in os.listdir( self.resultsPath):
                caserunname_path = os.path.join(self.resultsPath, caserunname)
                for carerunData in os.listdir( caserunname_path):
                    file_path = os.path.join(caserunname_path, carerunData)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Greška pri brisanju {file_path}: {e}")

            for filename in os.listdir( self.viewFolderPath):
                if filename !='resData.json':
                    file_path = os.path.join(self.viewFolderPath, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Greška pri brisanju {file_path}: {e}")

            #sad moramo napraviti defualt definitions file
            viewDefPath = Path(self.viewFolderPath, 'viewDefinitions.json')
            configPath = Path(Config.DATA_STORAGE, 'Variables.json')
            vars = File.readParamFile(configPath)
            viewDef = {}
            for group, lists in vars.items():
                for list in lists:
                    viewDef[list['id']] = []

            viewData = {
                    "osy-views": viewDef
                }
            File.writeFile( viewData, viewDefPath)


            response = {
                "message": "You have recycled results!",
                "status_code": "success"
            } 

            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError
        
    def saveView(self, data, param):
        try:

            viewDataPath = Path(Config.DATA_STORAGE,self.case,'view', 'viewDefinitions.json')

            viewData = File.readFile(viewDataPath)
            viewData["osy-views"][param].append(data)

            File.writeFile( viewData, viewDataPath)

            response = {
                "message": "You have created view!",
                "status_code": "success"
            }  

            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def updateViews(self, data, param):
        try:

            viewDataPath = Path(Config.DATA_STORAGE,self.case,'view', 'viewDefinitions.json')

            viewData = File.readFile(viewDataPath)
            viewData["osy-views"][param] = data

            File.writeFile( viewData, viewDataPath)

            response = {
                "message": "You have updated views!",
                "status_code": "success"
            }  

            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def readDataFile( self, caserunname ):
        try:
            
            #f = open(self.dataFile, mode="r")
            dataFilePath = Path(Config.DATA_STORAGE, self.case, 'res',caserunname,'data.txt')
            if os.path.exists(dataFilePath):
                f = open(dataFilePath, mode="r", encoding='utf-8-sig')
                data =  f.read()
                f.close
            else:
                data = None

            # f = open(self.dataFile, 'r')
            # file_contents = f.read()
            # f.close()
            return data
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def parseDataFile(self, dataFilePath):
        try:
            self.defaultValue = self.getParamDefaultValues()
            data = {}
            start_year = self.getYears()[0]
            with open(dataFilePath, 'r') as f:
                parsing = False
                for line in f:
                    line = line.rstrip().replace('\t', ' ')
                    if line.startswith(";"):
                        parsing = False
                    if parsing:
                        if line.startswith('['):
                            element = line.split(',')
                            region = element[0][1:]
                            tech = element[1]
                            fuel_emi = element[2]
                
                        elif line.startswith(start_year):
                            years = line.rstrip(':= ;\n').split(' ')[0:]
                            years = [i.strip(':=') for i in years]
                        
                        else:
                            values = line.rstrip().split(' ')[1:]
                            if param_current in ('DiscountRate'):
                                region = line.split(' ')[0]
                                dr = line.split(' ')[1]
                                data[param_current].append(tuple([region, dr]))
                            if param_current in ('OperationalLife', 'CapacityToActivityUnit', 'TotalTechnologyModelPeriodActivityLowerLimit', 'TotalTechnologyModelPeriodActivityUpperLimit', 'DiscountRateIdv'):
                                if firstRow:
                                    techs = line.rstrip(':= ;\n').split(' ')[0:]
                                    firstRow=False
                                else:
                                    region = line.split(' ')[0]
                                    for i, tech in enumerate(techs):
                                        data[param_current].append(tuple([region, tech, values[i]]))
                            if param_current in ('OutputActivityRatio','InputActivityRatio','EmissionActivityRatio'):
                                mode = line.split(' ')[0]
                                for i, year in enumerate(years):
                                    data[param_current].append(tuple([region, fuel_emi, tech, year, mode, values[i]]))

                            if param_current in ('CapacityFactor', 'SpecifiedDemandProfile'):
                                timeslice = line.split(' ')[0]
                                for i, year in enumerate(years):
                                    data[param_current].append(tuple([region, tech, year, timeslice, values[i]]))

                            if param_current in ('YearSplit'):
                                timeslice = line.split(' ')[0]
                                for i, year in enumerate(years):
                                    data[param_current].append(tuple([region, year, timeslice, values[i]]))
                            if param_current in ('TotalAnnualMaxCapacityInvestment','TotalAnnualMinCapacityInvestment','TotalTechnologyAnnualActivityUpperLimit', 'TotalTechnologyAnnualActivityLowerLimit', 'TotalAnnualMaxCapacity', 'ResidualCapacity', 'AvailabilityFactor', 'ResidualStorageCapacity'):
                                tech = line.split(' ')[0]
                                for i, year in enumerate(years):
                                    data[param_current].append(tuple([region, tech, year, values[i]]))   
                    if line.startswith(
                        
                        ('param DiscountRate',
                        'param OutputActivityRatio',
                        'param InputActivityRatio', 
                        'param EmissionActivityRatio',
                        'param TotalAnnualMaxCapacityInvestment',
                        'param TotalAnnualMinCapacityInvestment',
                        'param TotalTechnologyAnnualActivityUpperLimit',
                        'param TotalTechnologyAnnualActivityLowerLimit',
                        'param TotalAnnualMaxCapacity',
                        'param ResidualCapacity',
                        'param AvailabilityFactor',
                        'param CapacityToActivityUnit',
                        'param DiscountRateIdv',
                        'param TotalTechnologyModelPeriodActivityLowerLimit',
                        'param TotalTechnologyModelPeriodActivityUpperLimit',
                        'param CapacityFactor',
                        'param YearSplit',
                        'param SpecifiedDemandProfile',
                        'param OperationalLife',
                        'param ResidualStorageCapacity'
                        )):
                        
                        param_current = line.split(' ')[1]
                        data[param_current] = []
                        parsing = True
                        if line.startswith(
                            ('param OperationalLife',
                             'param CapacityToActivityUnit',
                             'param DiscountRateIdv',
                             'param TotalTechnologyModelPeriodActivityLowerLimit',
                             'param TotalTechnologyModelPeriodActivityUpperLimit'
                             )):
                            firstRow=True 
 
            return data
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def validateInputs(self, caserunname):
        try:
            self.defaultValue = self.getParamDefaultValues()
            data = {}
            start_year = self.getYears()[0]
            msg = ""

            dataFilePath = Path(Config.DATA_STORAGE, self.case, 'res',caserunname,'data.txt')
            if dataFilePath.is_file():
                # with open(dataFilePath, 'r') as f:

                #     parsing = False
                #     for line in f:
                #         line = line.rstrip().replace('\t', ' ')
                #         if line.startswith(";"):
                #             parsing = False

                #         if parsing:
                #             if line.startswith('['):

                #                 element = line.split(',')
                #                 region = element[0][1:]
                #                 tech = element[1]
                #                 fuel_emi = element[2]
                    
                #             elif line.startswith(start_year):
                #                 years = line.rstrip(':= ;\n').split(' ')[0:]
                #                 years = [i.strip(':=') for i in years]
                            
                #             else:
                #                 values = line.rstrip().split(' ')[1:]

                #                 if param_current in ('DiscountRate'):
                #                     region = line.split(' ')[0]
                #                     dr = line.split(' ')[1]
                #                     data[param_current].append(tuple([region, dr]))

                #                 if param_current in ('CapacityToActivityUnit', 'TotalTechnologyModelPeriodActivityLowerLimit', 'TotalTechnologyModelPeriodActivityUpperLimit', 'DiscountRateIdv'):
                #                     if firstRow:
                #                         techs = line.rstrip(':= ;\n').split(' ')[0:]
                #                         firstRow=False
                #                     else:
                #                         region = line.split(' ')[0]
                #                         for i, tech in enumerate(techs):
                #                             data[param_current].append(tuple([region, tech, values[i]]))

                #                 if param_current in ('OutputActivityRatio','InputActivityRatio','EmissionActivityRatio'):
                #                     mode = line.split(' ')[0]
                #                     for i, year in enumerate(years):
                #                         data[param_current].append(tuple([region, fuel_emi, tech, year, mode, values[i]]))

                #                 if param_current in ('CapacityFactor', 'SpecifiedDemandProfile'):
                #                     timeslice = line.split(' ')[0]
                #                     for i, year in enumerate(years):
                #                         data[param_current].append(tuple([region, tech, year, timeslice, values[i]]))

                #                 if param_current in ('YearSplit'):
                #                     timeslice = line.split(' ')[0]
                #                     for i, year in enumerate(years):
                #                         data[param_current].append(tuple([region, year, timeslice, values[i]]))

                #                 if param_current in ('TotalAnnualMaxCapacityInvestment','TotalAnnualMinCapacityInvestment','TotalTechnologyAnnualActivityUpperLimit', 'TotalTechnologyAnnualActivityLowerLimit', 'TotalAnnualMaxCapacity', 'ResidualCapacity', 'AvailabilityFactor'):
                #                     tech = line.split(' ')[0]
                #                     for i, year in enumerate(years):
                #                         data[param_current].append(tuple([region, tech, year, values[i]]))   

                #         if line.startswith(
                            
                #             ('param DiscountRate',
                #             'param OutputActivityRatio',
                #             'param InputActivityRatio', 
                #             'param EmissionActivityRatio',
                #             'param TotalAnnualMaxCapacityInvestment',
                #             'param TotalAnnualMinCapacityInvestment',
                #             'param TotalTechnologyAnnualActivityUpperLimit',
                #             'param TotalTechnologyAnnualActivityLowerLimit',
                #             'param TotalAnnualMaxCapacity',
                #             'param ResidualCapacity',
                #             'param AvailabilityFactor',

                #             'param CapacityToActivityUnit',
                #             'param DiscountRateIdv',
                #             'param TotalTechnologyModelPeriodActivityLowerLimit',
                #             'param TotalTechnologyModelPeriodActivityUpperLimit',
                #             'param CapacityFactor',
                #             'param YearSplit',

                #             'param SpecifiedDemandProfile'
                #             )):
                            
                #             param_current = line.split(' ')[1]
                #             # params = Config.PARAMETERS_C[param_current].copy()
                #             # params.append(param_current)
                #             data[param_current] = []
                #             # data[param_current].append(tuple(params))
                #             parsing = True
                #             if line.startswith(('param CapacityToActivityUnit'))  or line.startswith(('param DiscountRateIdv')) or line.startswith(('param TotalTechnologyModelPeriodActivityLowerLimit')) or line.startswith(('param TotalTechnologyModelPeriodActivityUpperLimit')):
                #                 firstRow=True 
                data = self.parseDataFile(dataFilePath)
            else:
                response = {
                    "msg": 'Data file is not created for this case run!',
                    "status_code": 'error'
                }   
                return response


            ############################################### Create dataframes from data file
            # df_IAR = pd.DataFrame(df_IAR.values[1:], columns=df_IAR.iloc[0] )
            df_IAR = pd.DataFrame(data['InputActivityRatio'], columns=Config.PARAMETERS_C_full['InputActivityRatio'])
            df_IAR['InputActivityRatio'] = df_IAR['InputActivityRatio'].astype(float)

            df_TAMaxCI = pd.DataFrame(data['TotalAnnualMaxCapacityInvestment'], columns=Config.PARAMETERS_C_full['TotalAnnualMaxCapacityInvestment'])
            # headers = df_TAMaxCI.iloc[0]
            # df_TAMaxCI = pd.DataFrame(df_TAMaxCI.values[1:], columns=headers )
            df_TAMaxCI['TotalAnnualMaxCapacityInvestment'] = df_TAMaxCI['TotalAnnualMaxCapacityInvestment'].astype(float)

            df_TAMinCI = pd.DataFrame(data['TotalAnnualMinCapacityInvestment'], columns=Config.PARAMETERS_C_full['TotalAnnualMinCapacityInvestment'])
            # headers = df_TAMinCI.iloc[0]
            # df_TAMinCI = pd.DataFrame(df_TAMinCI.values[1:], columns=headers )
            df_TAMinCI['TotalAnnualMinCapacityInvestment'] = df_TAMinCI['TotalAnnualMinCapacityInvestment'].astype(float)

            df_TAAUL = pd.DataFrame(data['TotalTechnologyAnnualActivityUpperLimit'], columns=Config.PARAMETERS_C_full['TotalTechnologyAnnualActivityUpperLimit'])
            # headers = df_TAAUL.iloc[0]
            # df_TAAUL = pd.DataFrame(df_TAAUL.values[1:], columns=headers )
            df_TAAUL['TotalTechnologyAnnualActivityUpperLimit'] = df_TAAUL['TotalTechnologyAnnualActivityUpperLimit'].astype(float)

            df_TAALL = pd.DataFrame(data['TotalTechnologyAnnualActivityLowerLimit'], columns=Config.PARAMETERS_C_full['TotalTechnologyAnnualActivityLowerLimit'])
            # headers = df_TAALL.iloc[0]
            # df_TAALL = pd.DataFrame(df_TAALL.values[1:], columns=headers )
            df_TAALL['TotalTechnologyAnnualActivityLowerLimit'] = df_TAALL['TotalTechnologyAnnualActivityLowerLimit'].astype(float)

            df_TAMaxC = pd.DataFrame(data['TotalAnnualMaxCapacity'], columns=Config.PARAMETERS_C_full['TotalAnnualMaxCapacity'])
            # headers = df_TAMaxC.iloc[0]
            # df_TAMaxC = pd.DataFrame(df_TAMaxC.values[1:], columns=headers )
            df_TAMaxC['TotalAnnualMaxCapacity'] = df_TAMaxC['TotalAnnualMaxCapacity'].astype(float)

            df_RC = pd.DataFrame(data['ResidualCapacity'], columns=Config.PARAMETERS_C_full['ResidualCapacity'])
            # headers = df_RC.iloc[0]
            # df_RC = pd.DataFrame(df_RC.values[1:], columns=headers )
            df_RC['ResidualCapacity'] = df_RC['ResidualCapacity'].astype(float)

            df_AF = pd.DataFrame(data['AvailabilityFactor'], columns=Config.PARAMETERS_C_full['AvailabilityFactor'])
            # headers = df_AF.iloc[0]
            # df_AF = pd.DataFrame(df_AF.values[1:], columns=headers )
            df_AF['AvailabilityFactor'] = df_AF['AvailabilityFactor'].astype(float)

            df_CTAU = pd.DataFrame(data['CapacityToActivityUnit'], columns=Config.PARAMETERS_C_full['CapacityToActivityUnit'])
            # headers = df_CTAU.iloc[0]
            # df_CTAU = pd.DataFrame(df_CTAU.values[1:], columns=headers )
            df_CTAU['CapacityToActivityUnit'] = df_CTAU['CapacityToActivityUnit'].astype(float)

            df_TMPALL = pd.DataFrame(data['TotalTechnologyModelPeriodActivityLowerLimit'], columns=Config.PARAMETERS_C_full['TotalTechnologyModelPeriodActivityLowerLimit'])
            # headers = df_TMPALL.iloc[0]
            # df_TMPALL = pd.DataFrame(df_TMPALL.values[1:], columns=headers )
            df_TMPALL['TotalTechnologyModelPeriodActivityLowerLimit'] = df_TMPALL['TotalTechnologyModelPeriodActivityLowerLimit'].astype(float)


            df_TMPAUL = pd.DataFrame(data['TotalTechnologyModelPeriodActivityUpperLimit'], columns=Config.PARAMETERS_C_full['TotalTechnologyModelPeriodActivityUpperLimit'])
            # headers = df_TMPAUL.iloc[0]
            # df_TMPAUL = pd.DataFrame(df_TMPAUL.values[1:], columns=headers )
            df_TMPAUL['TotalTechnologyModelPeriodActivityUpperLimit'] = df_TMPAUL['TotalTechnologyModelPeriodActivityUpperLimit'].astype(float)

            df_CF = pd.DataFrame(data['CapacityFactor'], columns=Config.PARAMETERS_C_full['CapacityFactor'])
            # headers = df_CF.iloc[0]
            # df_CF = pd.DataFrame(df_CF.values[1:], columns=headers )
            df_CF['CapacityFactor'] = df_CF['CapacityFactor'].astype(float)

            df_YS = pd.DataFrame(data['YearSplit'], columns=Config.PARAMETERS_C_full['YearSplit'])
            # headers = df_YS.iloc[0]
            # df_YS = pd.DataFrame(df_YS.values[1:], columns=headers )
            df_YS['YearSplit'] = df_YS['YearSplit'].astype(float)

            df_SDP = pd.DataFrame(data['SpecifiedDemandProfile'], columns=Config.PARAMETERS_C_full['SpecifiedDemandProfile'])
            # headers = df_SDP.iloc[0]
            # df_SDP = pd.DataFrame(df_SDP.values[1:], columns=headers )
            df_SDP['SpecifiedDemandProfile'] = df_SDP['SpecifiedDemandProfile'].astype(float)

            df_DRI = pd.DataFrame(data['DiscountRateIdv'], columns=Config.PARAMETERS_C_full['DiscountRateIdv'])
            # headers = df_DRI.iloc[0]
            # df_DRI = pd.DataFrame(df_DRI.values[1:], columns=headers )
            df_DRI['DiscountRateIdv'] = df_DRI['DiscountRateIdv'].astype(float)

            df_DR = pd.DataFrame(data['DiscountRate'], columns=Config.PARAMETERS_C_full['DiscountRate'])
            # headers = df_DR.iloc[0]
            # df_DR = pd.DataFrame(df_DR.values[1:], columns=headers )
            df_DR['DiscountRate'] = df_DR['DiscountRate'].astype(float)

            ########################################################################################## df za provjeru 1
            df_merge1 = df_DRI.merge(df_DR, on=['r'])

            ########################################################################################## df za provjeru 3
            df_merge3 = df_TAMaxCI.merge(df_TAMinCI, on=['r','t','y'])

            ########################################################################################## df za provjeru 4
            df_merge4 = df_TAAUL.merge(df_TAALL, on=['r','t','y'])

            ########################################################################################## df za provjeru 5
            df_merge5 = df_TAMaxC.merge(df_RC, on=['r','t','y'],how='outer')
            df_merge5['ResidualCapacity'] = df_merge5['ResidualCapacity'].fillna(0)
            df_merge5['TotalAnnualMaxCapacity'] = df_merge5['TotalAnnualMaxCapacity'].fillna(self.defaultValue['TAMaxC'])

            ########################################################################################## df za provjeru 6
            df_merge6 = df_merge5.merge(df_TAMinCI, on=['r','t','y'], how='outer')
            df_merge6['TotalAnnualMinCapacityInvestment'] = df_merge6['TotalAnnualMinCapacityInvestment'].fillna(self.defaultValue['TAMinCI'])

            ########################################################################################## df za provjeru 7
            df_merge71 = df_TAALL.merge( df_TAMaxC, how='left', on=['r','t','y']).merge(df_AF, how='left', on=['r','t','y']).merge(df_CTAU, how='left', on=['r','t'])
            df_merge72 = df_CF.merge(df_YS, on=['r','y','l'], how='left')

            df_merge71['TotalTechnologyAnnualActivityLowerLimit'] = df_merge71['TotalTechnologyAnnualActivityLowerLimit'].fillna(value=self.defaultValue['TAL'])
            df_merge71['TotalAnnualMaxCapacity'] = df_merge71['TotalAnnualMaxCapacity'].fillna(value=self.defaultValue['TAMaxC'])
            df_merge71['AvailabilityFactor'] = df_merge71['AvailabilityFactor'].fillna(value=self.defaultValue['AF'])
            df_merge71['CapacityToActivityUnit'] = df_merge71['CapacityToActivityUnit'].fillna(value=self.defaultValue['CAU'])

            df_merge72['CapacityFactor*YearSplit'] = df_merge72['CapacityFactor'] * df_merge72['YearSplit']
            #df_merge52['Sum'] = df_merge52.groupby(['r','t','y'])['YearSplit'].transform('sum')
            df_merge72 = df_merge72.groupby(['r','t','y'])['CapacityFactor*YearSplit'].sum().reset_index().rename(columns={'CapacityFactor*YearSplit':'Sum'})
            df_merge7 = df_merge71.merge(df_merge72, on=['r','y','t'], how='left')
            df_YStmp = df_YS.groupby(['r','y'])['YearSplit'].sum().reset_index().rename(columns={'YearSplit':'Sum'})

            # df_merge7 = df_merge7.set_index(['r','y']).fillna(df_YStmp.set_index(['r','y'])).reset_index()
            df_merge7 = pd.merge(df_merge7, df_YStmp, on=['r','y'],  suffixes=("", "_y"), how="left")
            df_merge7['Sum'].fillna(df_merge7['Sum_y'], inplace=True)

            df_merge7.drop(columns=['Sum_y'],axis=1, inplace=True)

            ################################################################################################ df za provjeru 8
            df_TAALL = df_TAALL.groupby(['r','t'])['TotalTechnologyAnnualActivityLowerLimit'].sum().reset_index().rename(columns={'TotalTechnologyAnnualActivityLowerLimit':'Sum_TotalTechnologyAnnualActivityLowerLimit'})
            df_merge8 = df_TMPAUL.merge(df_TAALL, on=['r','t'], how='left')
            df_merge8['TotalTechnologyModelPeriodActivityUpperLimit'] = df_merge8['TotalTechnologyModelPeriodActivityUpperLimit'].fillna(self.defaultValue['TMPAU'])
            df_merge8 = df_merge8[df_merge8['Sum_TotalTechnologyAnnualActivityLowerLimit'].notna()]


            ################################################################################################ df za provjeru 10


            ########################################################################################### C H E C K S ###############################################################################

            ########################################################################################### C H E C K 1
            print("CHECK 1. Identifying technologies where Discount Rate idv is different from global Discount Rate  for (r, t)")
            msg+="CHECK 1. Identifying technologies where Discount Rate idv is different from global Discount Rate  for (r, t)\n"
            df_check1 = df_merge1[
                (df_merge1['DiscountRateIdv'] != df_merge1['DiscountRate'])
            ]
            if not df_check1.empty:
                print("CHECK 1: Error")
                print(df_check1)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 1: Error\n"
                msg+=df_check1.to_string()
                msg+="\n\n"
            else:
                print("CHECK 1: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 1: Success\n\n"

            ########################################################################################### C H E C K 2
            print("CHECK 2. Check if YearSplits sums to 1 for y in YEAR")
            msg+="CHECK 2. Check if YearSplits sums to 1 for y in YEAR\n"
            df_YS = df_YS.groupby(['r','y'])['YearSplit'].sum().reset_index()
            df_check2 = df_YS[(df_YS["YearSplit"] != 1)]
            if not df_check2.empty:
                print("CHECK 2: Error")
                print(df_check2)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 2: Error\n"
                msg+=df_check2.to_string()
                msg+="\n\n"
            else:
                print("CHECK 2: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 2: Success\n\n"

            ########################################################################################### C H E C K 3
            print("CHECK 3. Checking if MinCapacityInvestment bounds are greater the MaxCapacityInvestment bounds for (r, t, y)")
            msg+="CHECK 3. Checking if MinCapacityInvestment bounds are greater the MaxCapacityInvestment bounds for (r, t, y)\n"
            df_check3 = df_merge3[
                (df_merge3['TotalAnnualMaxCapacityInvestment'] != -1) &
                (df_merge3['TotalAnnualMinCapacityInvestment'] != 0) &
                (df_merge3['TotalAnnualMaxCapacityInvestment'] < df_merge3['TotalAnnualMinCapacityInvestment'])
            ]
            if not df_check3.empty:
                print("CHECK 3: Error")
                print(df_check3)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 3: Error\n"
                msg+=df_check3.to_string()
                msg+="\n\n"
            else:
                print("CHECK 3: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 3: Success\n\n"

            ########################################################################################### C H E C K 4
            print("CHECK 4. Checking if TotalTechnologyAnnualActivityLowerLimit bounds are greater than TotalTechnologyAnnualActivityUpperLimit bounds for (r, t, y)")
            msg+="CHECK 4. Checking if TotalTechnologyAnnualActivityLowerLimit bounds are greater than TotalTechnologyAnnualActivityUpperLimit bounds for (r, t, y)\n"
            df_check4 = df_merge4[
                (df_merge4['TotalTechnologyAnnualActivityUpperLimit'] != -1) &
                (df_merge4['TotalTechnologyAnnualActivityLowerLimit'] != 0) &
                (df_merge4['TotalTechnologyAnnualActivityUpperLimit'] < df_merge4['TotalTechnologyAnnualActivityLowerLimit'])
            ]
            if not df_check4.empty:
                print("CHECK 4: Error")
                print(df_check4)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 4: Error\n"
                msg+=df_check4.to_string()
                msg+="\n\n"
            else:
                print("CHECK 4: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 4: Success\n\n"

            ########################################################################################### C H E C K 5
            print("CHECK 5. Checking if ResidualCapacity is greater than TotalAnnualMaxCapacity for (r, t, y)")
            msg+="CHECK 5. Checking if ResidualCapacity is greater than TotalAnnualMaxCapacity for (r, t, y)\n"
            df_check5 = df_merge5[
                (df_merge5['TotalAnnualMaxCapacity'] != -1) & 
                (df_merge5['ResidualCapacity'] != 0) & 
                (df_merge5['TotalAnnualMaxCapacity'] < df_merge5['ResidualCapacity'])
                ]
            if not df_check5.empty:
                print("CHECK 5: Error")
                print(df_check5)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 5: Error\n"
                msg+=df_check5.to_string()
                msg+="\n\n"
            else:
                print("CHECK 5: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 5: Success\n\n"

            ########################################################################################### C H E C K 6
            print("CHECK 6. Checking if ResidualCapacity plus TotalAnnualMinCapacityInvestment is greater than TotalAnnualMaxCapacity for (r, t, y)")
            msg+="CHECK 6. Checking if ResidualCapacity plus TotalAnnualMinCapacityInvestment is greater than TotalAnnualMaxCapacity for (r, t, y)\n"
            df_check6 = df_merge6[
                (df_merge6['TotalAnnualMaxCapacity'] != -1) &
                (df_merge6['ResidualCapacity'] != 0) &
                (df_merge6['TotalAnnualMaxCapacity'] < df_merge6['ResidualCapacity'] + df_merge6['TotalAnnualMinCapacityInvestment'])
            ]
            if not df_check6.empty:
                print("CHECK 6: Error")
                print(df_check6)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 6: Error\n"
                msg+=df_check6.to_string()
                msg+="\n\n"
            else:
                print("CHECK 6: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 6: Success\n\n"

            ########################################################################################### C H E C K 7
            print("CHECK 7. Checking if there is sufficient available capacity to meet TotalTechnologyAnnualActivityLowerLimit for (r, t, y)")
            msg+="CHECK 7. Checking if there is sufficient available capacity to meet TotalTechnologyAnnualActivityLowerLimit for (r, t, y)\n"
            df_check7 = df_merge7[
                (df_merge7['TotalAnnualMaxCapacity'] != 0) &
                (df_merge7['TotalAnnualMaxCapacity'] != -1) &
                (df_merge7['TotalTechnologyAnnualActivityLowerLimit'] != 0) &
                (df_merge7['AvailabilityFactor'] != 0) &
                (df_merge7['CapacityToActivityUnit'] != 0) &
                (df_merge7['Sum'] * df_merge7['TotalAnnualMaxCapacity'] * df_merge7['AvailabilityFactor'] * df_merge7['CapacityToActivityUnit'] < df_merge7['TotalTechnologyAnnualActivityLowerLimit'])
            ]
            if not df_check7.empty:
                print("CHECK 7: Error")
                print(df_check7)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 7: Error\n"
                msg+=df_check7.to_string()
                msg+="\n\n"
            else:
                print("CHECK 7: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 7: Success\n\n"

            ########################################################################################### C H E C K 8
            print("CHECK 8. Checking if TotalTechnologyModelPeriodActivityUpperLimit is less than accumulative TotalTechnologyAnnualActivityLowerLimit for (r, t)")
            msg+="CHECK 8. Checking if TotalTechnologyModelPeriodActivityUpperLimit is less than accumulative TotalTechnologyAnnualActivityLowerLimit for (r, t)\n"
            df_check8 = df_merge8[
                (df_merge8['TotalTechnologyModelPeriodActivityUpperLimit'] != -1) &
                (df_merge8['TotalTechnologyModelPeriodActivityUpperLimit'] < df_merge8['Sum_TotalTechnologyAnnualActivityLowerLimit'])
            ]
            if not df_check8.empty:
                print("CHECK 8: Error")
                print(df_check8)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 8: Error\n"
                msg+=df_check8.to_string()
                msg+="\n\n"
            else:
                print("CHECK 8: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 8: Success\n\n"

            ########################################################################################### C H E C K 9
            print("CHECK 9. Checking if Specified Demand Profile sums to 1 for (f, y)")
            msg+="CHECK 9. Checking if Specified Demand Profile sums to 1 for (f, y)\n"
            df_SDP = df_SDP.groupby(['r','f','y'])['SpecifiedDemandProfile'].sum().reset_index()
            df_check9 = df_SDP[(df_SDP["SpecifiedDemandProfile"] > 1.001) | (df_SDP["SpecifiedDemandProfile"] < 0.999)]

            if not df_check9.empty:
                print("CHECK 9: Error")
                print(df_check9)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 9: Error\n"
                msg+=df_check9.to_string()
                msg+="\n\n"
            else:
                print("CHECK 9: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 9: Success\n\n"

            ########################################################################################### C H E C K 10
            print("CHECK 10. Checking if ResidualCapacity plus cumulative TotalAnnualMinCapacityInvestment is greater than TotalAnnualMaxCapacity for (r, t, y)")
            msg+="CHECK 10. Checking if ResidualCapacity plus cumulative TotalAnnualMinCapacityInvestment is greater than TotalAnnualMaxCapacity for (r, t, y)\n"
            df_merge101 = df_TAMinCI.merge(df_RC, on=['r','t','y'],  how='outer')
            df_merge101['TotalAnnualMinCapacityInvestment'] = df_merge101['TotalAnnualMinCapacityInvestment'].fillna(value=0)
            df_merge101['ResidualCapacity'] = df_merge101['ResidualCapacity'].fillna(value=0)
            tech_current = ''
            merge102 = []
            for index, row in df_merge101.iterrows():
                tmp = {}
                if tech_current != row['t']:
                    Sum = 0
                tmp['r'] = row['r']
                tmp['t'] = row['t']
                Sum += row['TotalAnnualMinCapacityInvestment'] #+ row['ResidualCapacity']
                tmp['y'] = row['y']
                tmp['Sum'] = Sum
                merge102.append(tmp)
                tech_current = row['t']

            if not merge102:
                df_merge102 = pd.DataFrame(columns=['r', 't', 'y', 'Sum'])
            else:
                df_merge102 = pd.DataFrame(merge102)

            df_merge10 = df_merge101.merge(df_merge102, on=['r','t','y'],  how='outer').merge(df_TAMaxC, on=['r','t','y'],  how='outer')
            df_merge10['TotalAnnualMaxCapacity'] = df_merge10['TotalAnnualMaxCapacity'].fillna(value=999999)
            df_merge10['TotalAnnualMinCapacityInvestment'] = df_merge10['TotalAnnualMinCapacityInvestment'].fillna(value=0)
            df_merge10['ResidualCapacity'] = df_merge10['ResidualCapacity'].fillna(value=0)
            df_merge10['Sum'] = df_merge10['Sum'].fillna(value=0)

            df_check10 = df_merge10[
                (df_merge10['TotalAnnualMaxCapacity'] != -1) & 
                (df_merge10['TotalAnnualMaxCapacity'] < df_merge10['Sum'] + df_merge10['ResidualCapacity'])
            ]
            if not df_check10.empty:
                print("CHECK 10: Error")
                print(df_check10)
                msg+="<i class='fa fa-exclamation-triangle danger' aria-hidden='true'></i>CHECK 10: Error\n"
                msg+=df_check10.to_string()
                msg+="\n\n"
            else:
                print("CHECK 10: Success")
                msg+="<i class='fa fa-check-square-o success' aria-hidden='true'></i>CHECK 10: Success\n\n"

            #print('msg \n', msg)

            response = {
                "msg": msg,
                "status_code": 'success'
            }   
            return response
        except(IOError, KeyError):
            response = {
                "msg": 'Some of the params are missing in data file (data file created before 4.9 ver). Please generate data file again and run check',
                "status_code": 'error'
            } 
            return response  
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError
        
    def preprocessData(self, data_infile, data_outfile):
        try:
            lines = []
            with open(data_infile, 'r') as f1:
                for line in f1:
                    if not line.startswith(('set MODEper','set MODEx', 'end;')):
                        lines.append(line)

            year_list = self.getYears()
            fuel_list = self.getCommNames()
            tech_list = self.getTechNames()
            emi_list = self.getEmiNames()
            stg_list = self.getStgNames()

            start_year = year_list[0]

            data_all = []
            input_fuel_list = []
            data = {}
            with open(data_infile, 'r') as f:
                parsing = False
                for line in f:
                    line = line.rstrip().replace('\t', ' ')
                    if line.startswith(";"):
                        parsing = False
                    if parsing:
                        if line.startswith('['):
                            element = line.split(',')
                            region = element[0][1:]
                            tech = element[1]
                            fuel_emi = element[2]
                
                        elif line.startswith(start_year):
                            years = line.rstrip(':= ;\n').split(' ')[0:]
                            years = [i.strip(':=') for i in years]
                        
                        else:
                            values = line.rstrip().split(' ')[1:]
                            if param_current in ('DiscountRate'):
                                region = line.split(' ')[0]
                                dr = line.split(' ')[1]
                                data[param_current].append(tuple([region, dr]))
                            if param_current in ('OperationalLife', 'DiscountRateIdv'):
                                if firstRow:
                                    techs = line.rstrip(':= ;\n').split(' ')[0:]
                                    firstRow=False
                                else:
                                    region = line.split(' ')[0]
                                    for i, tech in enumerate(techs):
                                        data[param_current].append(tuple([ region, tech, values[i]]))
                            if param_current in ('OutputActivityRatio','InputActivityRatio','EmissionActivityRatio', 'EmissionToActivityChangeRatio'):
                                mode = line.split(' ')[0]
                                data[param_current].append(tuple([ fuel_emi, tech, mode ]))
                                data_all.append(tuple([tech, mode]))
                            # version 5.4 16.12.2025.
                            if param_current in ('InputToNewCapacityRatio','InputToTotalCapacityRatio'):
                                fuel = line.split(' ')[0]
                                data[param_current].append(tuple([ fuel, tech ]))
                                if fuel not in input_fuel_list:
                                    input_fuel_list.append(fuel)

                            ################################
                            if param_current in ('TechnologyToStorage','TechnologyFromStorage'):
                                if firstRow:
                                    modes = line.rstrip(':= ;\n').split(' ')[0:]
                                    firstRow=False
                                else:
                                    stg = line.split(' ')[0]
                                    value = line.split(' ')[1:]
                                    data_all.append(tuple([tech, mode]))
                                    for i, mode in enumerate(modes):
                                        if(value[i] != '0'):
                                            data[param_current].append(tuple([ stg, tech, mode]))
                                        
                                        


                    if line.startswith(
                        (
                        'param OutputActivityRatio',
                        'param InputActivityRatio', 
                        'param EmissionActivityRatio',
                        'param EmissionToActivityChangeRatio',
                        'param OperationalLife',
                        'param DiscountRateIdv',
                        'param DiscountRate','param TechnologyToStorage','param TechnologyFromStorage',
                        'param InputToNewCapacityRatio',
                        'param InputToTotalCapacityRatio', 
                        )):
                        
                        param_current = line.split(' ')[1]
                        data[param_current] = []
                        parsing = True
                        if line.startswith(('param OperationalLife','param DiscountRateIdv','param TechnologyToStorage','param TechnologyFromStorage')):
                            firstRow=True


            data_out = data['OutputActivityRatio']
            data_inp = data['InputActivityRatio']
            data_emi = data['EmissionActivityRatio']
            data_emichange = data['EmissionToActivityChangeRatio']
            data_tts = data['TechnologyToStorage']
            data_tfs = data['TechnologyFromStorage']
            data_itnc = data['InputToNewCapacityRatio']
            data_ittc = data['InputToTotalCapacityRatio']
                            
            data_out = list(set(data_out))
            data_inp = list(set(data_inp))
            data_all = list(set(data_all))
            data_emi = list(set(data_emi))
            data_emichange = list(set(data_emichange))
            data_tts = list(set(data_tts))
            data_tfs = list(set(data_tfs))
            data_itnc = list(set(data_itnc))
            data_ittc = list(set(data_ittc))

            dict_out = defaultdict(list)
            dict_inp = defaultdict(list)
            dict_all = defaultdict(list)
            dict_emi = defaultdict(list)
            dict_emichange = defaultdict(list)
            dict_tts = defaultdict(list)
            dict_tfs = defaultdict(list)
            dict_itnc =defaultdict(list)
            dict_ittc =defaultdict(list)

            for fuel, tech, mode in data_out:
                dict_out[fuel].append((mode, tech))

            for fuel, tech, mode in data_inp:
                dict_inp[fuel].append((mode, tech))

            for emi, tech, mode in data_emi:
                dict_emi[emi].append((mode, tech))

            for emi, tech, mode in data_emichange:
                dict_emichange[emi].append((mode, tech))

            for stg, tech, mode in data_tts:
                dict_tts[stg].append((mode, tech))

            for stg, tech, mode in data_tfs:
                dict_tfs[stg].append((mode, tech))

            for fuel, tech in data_itnc:
                dict_itnc[fuel].append(tech)

            for fuel, tech in data_ittc:
                dict_ittc[fuel].append(tech)                            

            for tech, mode in data_all:
                if mode not in dict_all[tech]:
                    dict_all[tech].append(mode)

            #################################################### conversions ls/ld/lh

            # self.seIDs = self.getSeIds()
            # self.seMap = self.getSeMap()
            # self.dtIDs = self.getDtIds()
            # self.dtMap = self.getDtMap()
            # self.dtbIDs = self.getDtbIds()
            # self.dtbMap = self.getDtbMap()

            # self.seasons = ''
            # for seId in self.seIDs:
            #     self.seasons += '{} '.format(self.seMap[seId]) 

            # self.daytypes = ''
            # for dtId in self.dtIDs:
            #     self.daytypes += '{} '.format(self.dtMap[dtId]) 

            # self.dailytimebrackets = ''
            # for dtbId in self.dtbIDs:
            #     self.dailytimebrackets += '{} '.format(self.dtbMap[dtbId]) 

            # timeslices = self.genData["osy-ts"]
            # seasons = self.genData["osy-se"]
            # daytypes = self.genData["osy-dt"]
            # dailytypebrackets = self.genData["osy-dtb"]

            # seString = ''
            # dtString = ''
            # dtbString = ''
            # for ts in timeslices:           
            #     seString += '{} '.format(ts['Ts'])
            #     for se in seasons:
            #         if se['Se'] == ts['SE'][0]:
            #             seString += '{} '.format(1)
            #         else:
            #             seString += '{} '.format(0)

            #     dtString += '{} '.format(ts['Ts'])
            #     for dt in daytypes :
            #         if dt['Dt'] == ts['DT'][0]:
            #             dtString += '{} '.format(1)
            #         else:
            #             dtString += '{} '.format(0)


            #     dtbString += '{} '.format(ts['Ts'])
            #     for dtb in dailytypebrackets :
            #         if dtb['Dtb'] == ts['DTB'][0]:
            #             dtbString += '{} '.format(1)
            #         else:
            #             dtbString += '{} '.format(0)


            #     seString += '{}'.format('\n')
            #     dtString += '{}'.format('\n')
            #     dtbString += '{}'.format('\n')

            # seString += '{}{}'.format(";",'\n')
            # dtString += '{}{}'.format(";",'\n')            
            # dtbString += '{}{}'.format(";",'\n')

            # lines.append('{} {} {} {} {} {}'.format('param', 'Conversionls','default', 0, ':','\n'))
            # lines.append('{}{}{}'.format(self.seasons, ':=', '\n'))
            # lines.append('{}{}'.format(seString,'\n'))

            # lines.append('{} {} {} {} {} {}'.format('param', 'Conversionld','default', 0, ':','\n'))
            # lines.append('{}{}{}'.format(self.daytypes, ':=', '\n'))
            # lines.append('{}{}'.format(dtString,'\n'))

            # lines.append('{} {} {} {} {} {}'.format('param', 'Conversionlh','default', 0, ':','\n'))
            # lines.append('{}{}{}'.format(self.dailytimebrackets, ':=', '\n'))
            # lines.append('{}{}'.format(dtbString,'\n'))

            #     lines.append('{}{}'.format(seString,'\n'))
            # lines.append('{}{}'.format(";",'\n'))
            # lines.append('{}'.format('\n'))
            
            #################################################### CRF ANNUITY
            OL_data = data['OperationalLife']
            DRi_data = data['DiscountRateIdv']
            DR_data = data['DiscountRate']
            DR = float(DR_data[0][1])

            OL = {}
            DRi = {}
            for r, t, ol in OL_data:
                OL[t] = int(ol)
            for r, t, dri in DRi_data:
                DRi[t] = float(dri)
            techs_string = ''
            for tech in tech_list:
                techs_string += '{} '.format(tech) 

            #CRF calc
            CapitalRecoveryFactor = {}
            PvAnnuity = {}
            for tech in tech_list:
                if DRi[tech] == 0:
                    CapitalRecoveryFactor[tech] = None
                else:
                    CapitalRecoveryFactor[tech] = round((1 - pow( (1 + DRi[tech]), -1) ) / (1 - pow( (1+DRi[tech]), -OL[tech] ) ), 4)
                # PvAnnuity[tech] = (1 - pow((1 + DRi[tech]), -OL[tech])) * (1 + DRi[tech]) / DRi[tech]
                if DR == 0:
                    PvAnnuity[tech] = None
                else:
                    PvAnnuity[tech] = round((1 - pow((1 + DR), -OL[tech])) * (1 + DR) / DR, 4 )

                # CapitalRecoveryFactor[tech] = round((1 - pow( (1 + DRi[tech]), -1) ) / (1 - pow( (1+DRi[tech]), -OL[tech] ) ), 4)
                # PvAnnuity[tech] = round((1 - pow((1 + DR), -OL[tech])) * (1 + DR) / DR, 4 )

            lines.append('{} {} {} {} {} {}'.format('param', 'CapitalRecoveryFactor','default', 0, ':','\n'))
            lines.append('{}{}{}'.format(techs_string, ':=', '\n'))
            rtString = ''
            for tech in tech_list:
                tmp = CapitalRecoveryFactor[tech]
                rtString += '{} '.format(tmp)
            lines.append('{}{}{}'.format('RE1 ', rtString, '\n'))
            lines.append('{}{}'.format(';', '\n'))
                
            lines.append('{} {} {} {} {} {}'.format('param', 'PvAnnuity','default', 0, ':','\n'))
            lines.append('{}{}{}'.format(techs_string, ':=', '\n'))
            rtString = ''
            for tech in tech_list:
                tmp = PvAnnuity[tech]
                rtString += '{} '.format(tmp)
            lines.append('{}{}{}'.format('RE1 ', rtString, '\n'))
            lines.append('{}{}'.format(';', '\n'))

            #ispis linija iz originalnog data file
            with open(data_outfile, 'w') as f2:
                f2.writelines(lines)




            # df_OL = pd.DataFrame(data['OperationalLife'], columns=['r','t','OperationalLife'])
            # df_OL['OperationalLife'] = df_OL['OperationalLife'].astype(int)
            # df_DRi = pd.DataFrame(data['DiscountRateIdv'], columns=['r','t','DiscountRateIdv'])
            # df_DRi['DiscountRateIdv'] = df_DRi['DiscountRateIdv'].astype(float)
            # df_CRF = pd.merge(df_DRi, df_OL, on=['r', 't'])
            # df_CRF['CRF'] = (1 - pow( (1+df_CRF['DiscountRateIdv']), -1) ) / (1 - pow( (1+df_CRF['DiscountRateIdv']), -df_CRF['OperationalLife'] ) )



            #function for appending values in data file
            def file_output_function(dict, set_list, set_name, extra_char, type=None):
                for each in set_list:

                    if each in dict.keys():
                        line = set_name + str(each) + ']:=' + str(dict[each]) + extra_char
                        if set_list == tech_list:
                            line = line.replace(',', '').replace(':=[', ':= ').replace(']*', '').replace("'", "")
                        if type == 'input':
                            line = line.replace(',', '').replace(':=[', ':= ').replace("']", '').replace("'", "")
                        else:
                            line = line.replace('),', ')').replace('[(', ' (').replace(')]', ')').replace("'", "")
                    else:
                        line = set_name + str(each) + ']:='
                    file_out.write(line + ';' + '\n')

            # Append lines at the end of the data file
            with open(data_outfile, 'w') as file_out:  # 'a' to open in 'append' mode
                file_out.writelines(lines)
                file_output_function(dict_out, fuel_list, 'set MODExTECHNOLOGYperFUELout[', '')
                file_output_function(dict_inp, fuel_list, 'set MODExTECHNOLOGYperFUELin[', '')
                file_output_function(dict_emi, emi_list, 'set MODExTECHNOLOGYperEMISSION[', '')
                file_output_function(dict_emichange, emi_list, 'set MODExTECHNOLOGYperEMISSIONChange[', '')
                file_output_function(dict_tts, stg_list, 'set MODExTECHNOLOGYperSTORAGEto[', '')
                file_output_function(dict_tfs, stg_list, 'set MODExTECHNOLOGYperSTORAGEfrom[', '')
                #da li se ovaj mod po tech treba puniti i za emissijske tehnologije i sta to znaci u model file

                file_output_function(dict_itnc, input_fuel_list, 'set INPUTxNEWxCAPACITYperFUEL[', '', type='input')
                file_output_function(dict_ittc, input_fuel_list, 'set INPUTxTOTALxCAPACITYperFUEL[', '', type='input')

                file_output_function(dict_all, tech_list, 'set MODEperTECHNOLOGY[', '*')


                line = 'set INPUTxFUEL:=' + ', '.join(input_fuel_list)
                file_out.write(line + ';' + '\n')

                file_out.write('end;')

        except Exception as err:
            print(f"Unexpected error: {err}")
            print("An error occurred:")
            traceback.print_exc()  # Prints full traceback

    def batchRun(self, solver, cases):
        try:
            batchlog=""
            msg=""
            status = "Success"
            results = []

            ##################################Sequential code
            for caserun in cases:
                runout =self.run(solver, caserun)
                msg+="Case: {0}{1}{2}".format( runout["caserun"], runout["timer"],  '\n')
                # batchlog+="GLPK status {0}{1}{2}GLPK log {3}{4}{5}{6}CBC log {7}{8}{9}{10}{11}".format(runout["status_code"], runout["timer"],'\n',runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n\n')
                batchlog+="{0}{1}{2}{3}{4}{5}{6}{7}{8}".format(runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n')
                batchlog+="------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ {0}".format('\n')
                if runout["status_code"] != 'success':
                    status = "Error"

            ##################################Multiprocessing
            # m = multiprocessing.Manager()
            # lock = m.Lock()
            # with concurrent.futures.ProcessPoolExecutor() as executor:
            #     results = [executor.submit(self.run, solver, caserun, lock  ) for caserun in cases]
            #     #runout = [result.result() for result in results]

            #     # for caserun in cases:
            #     #     # lock[caserun] = threading.Lock() 
            #     #     #lock = threading.Lock() 
            #     #     t = executor.submit(self.run, solver, caserun)
            #     #     results.append(t)

            # for ft in concurrent.futures.as_completed(results):
            #     runout = ft.result()
            #     msg+="Case: {0}{1}{2}".format( runout["caserun"], runout["timer"],  '\n')
            #     # batchlog+="GLPK status {0}{1}{2}GLPK log {3}{4}{5}{6}CBC log {7}{8}{9}{10}{11}".format(runout["status_code"], runout["timer"],'\n',runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n\n')
            #     batchlog+="{0}{1}{2}{3}{4}{5}{6}{7}{8}".format(runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n')
            #     batchlog+="------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ {0}".format('\n')
            #     if runout["status_code"] != 'success':
            #         status = "Error"
            

            #####################################Threading
            # with concurrent.futures.ThreadPoolExecutor() as executor:
            #     results = [executor.submit(self.run, solver, caserun  ) for caserun in cases]

            #     # for caserun in cases:
            #     #     # lock[caserun] = threading.Lock() 
            #     #     #lock = threading.Lock() 
            #     #     t = executor.submit(self.run, solver, caserun)
            #     #     results.append(t)

            # for f in concurrent.futures.as_completed(results):
            #     runout = f.result()
            #     msg+="Case: {0}{1}{2}".format( runout["caserun"], runout["timer"],  '\n')
            #     # batchlog+="GLPK status {0}{1}{2}GLPK log {3}{4}{5}{6}CBC log {7}{8}{9}{10}{11}".format(runout["status_code"], runout["timer"],'\n',runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n\n')
            #     batchlog+="{0}{1}{2}{3}{4}{5}{6}{7}{8}".format(runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n')
            #     batchlog+="------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ {0}".format('\n')
            #     if runout["status_code"] != 'success':
            #         status = "Error"




            ##########################################CUSOM THREAD IMPLEMENATATION
            # for caserun in cases:
            #     # batchlog+="Run dor case {0}, started at {1}{2}".format(caserun,dt, '\n')
            #     batchlog+="Case: {0}{1}".format(caserun, '\n')
            #     batchlog+="------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ {0}".format('\n')
            #     #df = self.generateDatafile(caserun)
            #     #runout = self.run(solver, caserun)


            #     # thread = CustomThread(target=self.run, args=(solver, caserun ) )
            #     # thread.start()
            #     # threads.append(thread)



            # # for thread in threads:
            #     #runout = thread.join()
            #     #runout = threads[caserun].join()

            #     msg+="Case: {0}{1}{2}".format(caserun, runout["timer"], '\n')
            #     # batchlog+="GLPK status {0}{1}{2}GLPK log {3}{4}{5}{6}CBC log {7}{8}{9}{10}{11}".format(runout["status_code"], runout["timer"],'\n',runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n\n')
            #     batchlog+="{0}{1}{2}{3}{4}{5}{6}{7}{8}".format(runout["glpk_message"],'\n',runout["glpk_stdmsg"],'\n',runout["cbc_message"],'\n',runout["cbc_stdmsg"],'\n', '\n')
            #     batchlog+="------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ {0}".format('\n')
            #     if runout["status_code"] != 'success':
            #         status = "Error"
            response = {
                "log": batchlog,
                "msg": msg,
                "status": status
            }           
            return response

        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def run( self, solver, caserun, lock=None ):
        try:
            caserunname = caserun
            if lock is not None:
                # self.caserunname = caserunname
                # lock = {}
                # lock[caserunname] = threading.Lock() 
                lock.acquire()
                caserunname = caserun

            start_time = time.time()
            txtOut = ""
            self.dataFile = Path(Config.DATA_STORAGE, self.case, 'res',caserunname,'data.txt')
            self.dataFile_processed = Path(Config.DATA_STORAGE, self.case, 'res',caserunname,'data_processed.txt')
            self.resFile = Path(Config.DATA_STORAGE,self.case, 'res',caserunname,'results.txt')
            self.logFile = Path(Config.DATA_STORAGE,self.case, 'res',caserunname,'logfile.log')
            self.logFileTxt = Path(Config.DATA_STORAGE,self.case, 'res',caserunname,'logfile.txt')
            self.lpFile = Path(Config.DATA_STORAGE,self.case, 'res',caserunname,'lp.lp')
            self.resPath = Path(Config.DATA_STORAGE,self.case, 'res',caserunname)
            
            modelfile = '"{}"'.format(self.osemosysFile.resolve())
            modelfile_original = '"{}"'.format(self.osemosysFileOriginal.resolve())
            datafile = '"{}"'.format(self.dataFile.resolve())
            datafile_processed = '"{}"'.format(self.dataFile_processed.resolve())
            resultfile = '"{}"'.format(self.resFile.resolve())
            logfile = '"{}"'.format(self.logFile.resolve())
            logfiletxt = '"{}"'.format(self.logFileTxt.resolve())
            lpfile = '"{}"'.format(self.lpFile.resolve())


            

            glpfolder =self.glpkFolder.resolve()
            cbcfolder =self.cbcFolder.resolve()
            # respath = self.resPath.resolve()
            # resCBCPath = self.resCBCPath.resolve()

            self.deleteCaseResultsJSON(caserunname)

            if solver == 'glpk':
                out = subprocess.run('glpsol -m ' + modelfile +' -d ' + datafile +' -o ' + resultfile, cwd=glpfolder,  capture_output=True, text=True, shell=True)
            else:
                #Matrix generation (creates an LP file with GLPK): glpsol --check -m [model].txt -d [data].txt --wlp [LPfile].lp
                #Optimisation (solves LP file with CBC): cbc [LPfile].lp solve -solu [results].txt
                #PREPROCESS data.txt
                #subprocess.run('preprocess_data.py' + datafile + dataFile_processed)

                logger.debug("Starting preprocessing step for case %s", caserunname)
                self.preprocessData(self.dataFile, self.dataFile_processed)
                logger.info("PREPROCESSING DONE! --- %s seconds --- %s", time.time() - start_time, caserunname)
                txtOut = txtOut + ("Preprocessing time {:0.2f}s;{}".format(time.time() - start_time, '\n'))

                #return output to variable preprocessed data file
                glpk_out = subprocess.run('glpsol --check -m ' + modelfile +' -d ' + datafile_processed +' --wlp ' + lpfile, cwd=glpfolder,  capture_output=True, text=True, shell=True)
            

                #glpk_out = subprocess.run('glpsol --check -m ' + modelfile +' -d ' + datafile_processed +' --wlp ' + lpfile, cwd=cbcfolder,  capture_output=True, text=True, shell=True)
                

                #original data file without preprocessing
                #glpk_out = subprocess.run('glpsol --check -m ' + modelfile_original +' -d ' + datafile +' --wlp ' + lpfile, cwd=glpfolder,  capture_output=True, text=True, shell=True)
                
                logger.info("CREATINON OF LP FILE DONE! --- %s seconds --- %s", time.time() - start_time, caserunname)
                txtOut = txtOut + ("Creation of LP file time {:0.2f}s;{}".format(time.time() - start_time, '\n'))


                ####output to logfile.txt
                #subprocess.run('glpsol --check -m ' + modelfile +' -d ' + datafile_processed +' --wlp ' + lpfile +'>'+  logfiletxt+'2>&1', cwd=glpfolder, text=True, shell=True)

                # proc = subprocess.Popen('glpsol --check -m ' + modelfile +' -d ' + datafile_processed +' --wlp ' + lpfile, cwd=glpfolder, text=True, shell=True)
                # try:
                #     outs, errs = proc.communicate(timeout=25)
                # except:
                #     proc.kill()
                #     outs, errs = proc.communicate()

                #cbc_out = subprocess.run('cbc ' + lpfile +' -presolve off -postsolve on -logLevel 3 solve -printing all -solu '  + resultfile, cwd=cbcfolder,  capture_output=True, text=True, shell=True)
                # prin
                logger.debug("Running CBC solver in directory %s", cbcfolder)
                cbc_out = subprocess.run('cbc ' + lpfile +' solve -printing all -solu '  + resultfile, cwd=cbcfolder,  capture_output=True, text=True, shell=True)
                # -printing all prints all constraints to result.txt
                logger.info("SOLUTION DONE! --- %s seconds --- %s", time.time() - start_time, caserunname)
                txtOut = txtOut + ("Solution time {:0.2f}s;{}".format(time.time() - start_time, '\n'))
                ####output to lg file .log i .txt with errors
                # out = subprocess.run('cbc ' + lpfile +' solve -solu '  + resultfile +'>'+ logfile, cwd=cbcfolder,  capture_output=True, text=True, shell=True)
                #out = subprocess.run('cbc ' + lpfile +' solve -solu '  + resultfile +'>'+ logfiletxt +'2>&1', cwd=cbcfolder,  capture_output=True, text=True, shell=True)
                
            #CBC or GLPK return error
            if cbc_out.returncode != 0 or glpk_out.returncode != 0:
                response = {
                    "cbc_message": cbc_out.stdout,
                    "cbc_stdmsg": cbc_out.stderr,
                    "glpk_message": glpk_out.stdout,
                    "glpk_stdmsg": glpk_out.stderr,
                    "timer": "Error occured either during cration of LP file or solution! Please check CBC and GLPK logs.",
                    "status_code": "error",
                    "caserun": caserunname
                }
            else:
                msg = cbc_out.stdout.splitlines()

                statusFlag = "warning"
                customMsg = "   "
                if any("Optimal" in s for s in msg):
                    matching = [s for s in msg if "Optimal" in s]
                    customMsg = customMsg + matching[0] + " - "
                    times = [s for s in msg if "Total time (CPU seconds):" in s]
                    customMsg = customMsg + times[0]
                    statusFlag = "success"

                if any("infeasible" in s for s in msg):
                    matching = [s for s in msg if "infeasible" in s]
                    customMsg = customMsg + matching[0] + " - "
                    times = [s for s in msg if "Total time (CPU seconds):" in s]
                    customMsg = customMsg + times[0]
                    statusFlag = "warning"

                if any("ERROR" in s for s in msg):
                    matching = [s for s in msg if "ERROR" in s]
                    customMsg = customMsg + matching[0] + " - "
                    times = [s for s in msg if "Total time (CPU seconds):" in s]
                    customMsg = customMsg + times[0]
                    statusFlag = "error"

                if statusFlag == "success":
                    self.generateCSVfromCBC(self.dataFile, self.resFile, self.resPath)
                    logger.info("CSV DONE! --- %s seconds --- %s", time.time() - start_time, caserunname)
                    txtOut = txtOut + ("csv files extraction time {:0.2f} s;{}".format(time.time() - start_time, '\n'))
                    self.generateResultsViewer(caserunname)
                    logger.info("PIVOT TABLE DONE! --- %s seconds --- %s", time.time() - start_time, caserunname)
                    txtOut = txtOut + ("Pivot data preparation time {:0.2f}s;{}".format(time.time() - start_time, '\n'))


                logger.info("MESSAGES DONE! --- %s seconds --- %s", time.time() - start_time, caserunname)
                txtOut = txtOut + ("Message preparation time {:0.2f}s;{}".format(time.time() - start_time, '\n'))

                response = {
                    "cbc_message": cbc_out.stdout,
                    "cbc_stdmsg": cbc_out.stderr,
                    "glpk_message": glpk_out.stdout,
                    "glpk_stdmsg": glpk_out.stderr,
                    "timer": customMsg,
                    "status_code": statusFlag,
                    "caserun": caserunname
                } 

           
            if lock is not None:
                lock.release()

            return response
            # urllib.request.urlretrieve(self.dataFile, dataFile)

        except Exception:
            logger.exception("Unhandled exception during solver execution")
            raise
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError
    
    def generateCSVfromCBC(self, data_file, results_file, base_folder=os.getcwd()):
        try:
            #pd.options.mode.chained_assignment = None
            #pd.options.mode.chained_assignment = None

            data = {}
            year_list = self.getYears()
            tech_list = self.getTechNames()
            start_year = int(year_list[0])

            data = self.parseDataFile(data_file)

            try:
                os.makedirs(os.path.join(base_folder, 'csv'))
            except FileExistsError:
                pass
            
            #parsanje result.txt
            params = []
            df = pd.read_csv(results_file, sep='\t')            

            ###################################### parse optimal value from result.txt
            # Extract the optimal value from the header line
            optimal_value_header = df.columns[0]
            if 'Optimal - objective value' in optimal_value_header:
                # Extract the value from the header line
                optimal_value = float(optimal_value_header.split()[-1])

            ov = {
            "r": ['RE1'],
            "ObjectiveValue": [optimal_value]
            }

            #load data into a DataFrame object:
            dfOV = pd.DataFrame(ov)
            dfOV.to_csv(os.path.join(base_folder, 'csv', 'ObjectiveValue.csv'), index=None)
            ######################################## end optimal value parse    
            #                                      
            df.columns = ['temp']

            df['temp'] = df['temp'].str.lstrip(' *\n\t')
           
           
            if len(df) > 0:
                #ovdje parsa result.txt file
                df[['temp','value']] = df['temp'].str.split(')', expand=True)                

                df = df.applymap(lambda x: x.strip() if isinstance(x,str) else x)

                #error when moved to ython 3.11, Columns must have smae length as key
                # df['value'] = df['value'].str.split(' ', expand=True)
                # potrebno je extract i dual values
                #df['value'] = df['value'].str.split(' ', expand=True)[0]
                # print(df[['temp','value']].head())
                # print(df['temp'].loc[6853]) 
                # print(df['value'].loc[6853]) 

                #df[['primal','dual']] = df['value'].str.split('\t', expand=True)
                df[['value','dual']] = df['value'].str.split(expand=True)
                #print(df[['value','dual']].head())

                df[['parameter','id']] = df['temp'].str.split('(', expand=True)
                df['parameter'] = df['parameter'].str.split(' ', expand=True)[1]
                df = df.drop('temp', axis=1)
                df['value'] = df['value'].astype(float).round(4)
                df['dual'] = df['dual'].astype(float).round(4)

                #variables that are output form solver 19
                params = df.parameter.unique()
                all_params = {}

                for each in params:
                    if each in Config.VARIABLES_C:
                        result_cols = []

                        # radi problem izmjena da dataframe bez copije 20240118 vk
                        # df_p = df[df.parameter == each]
                        # df_p[Config.VARIABLES_C[each]] = df_p['id'].str.split(',',expand=True)

                        df_p = df[df.parameter == each].copy()
                        df_p[Config.VARIABLES_C[each]] = df_p['id'].str.split(',',expand=True)

                        result_cols = Config.VARIABLES_C[each].copy()

                        # if each in ('EBb4_EnergyBalanceEachYear4_ICR', 'E8_AnnualEmissionsLimit', 'UDC1_UserDefinedConstraintInequality', 'UDC2_UserDefinedConstraintEquality'):
                        if each in Config.DUALS.keys():
                            result_cols.append('dual')
                        else:
                            result_cols.append('value')
                        #result_cols.append(each)
                        df_p = df_p[result_cols] # Reorder dataframe to include 'value' as last column
                        all_params[each] = pd.DataFrame(df_p) # Create a dataframe for each parameter

                        #napravi csv
                        #if each in ('EBb4_EnergyBalanceEachYear4_ICR', 'E8_AnnualEmissionsLimit', 'UDC1_UserDefinedConstraintInequality', 'UDC2_UserDefinedConstraintEquality'):
                        if each in Config.DUALS.keys():
                            all_params[each] = all_params[each].rename(columns={'dual':each})
                        else:
                            all_params[each] = all_params[each].rename(columns={'value':each})
                            all_params[each].to_csv(os.path.join(base_folder, 'csv', each+'.csv'), index=None)

                ########################################Vars koje se izracunavaju u ovoj script nisu izlaz iz solvera###########
                ################################################################################################################
                #duals
                for dual in Config.DUALS.keys():
                    # if 'EBb4_EnergyBalanceEachYear4_ICR' in all_params:
                    #     df_DR = pd.DataFrame(data['DiscountRate'], columns=Config.PARAMETERS_C_full['DiscountRate'])
                    #     df_DR['DiscountRate'] = df_DR['DiscountRate'].astype(float)
                    #     df_EB = all_params['EBb4_EnergyBalanceEachYear4_ICR']
                    #     df_EB['y'] = df_EB['y'].astype(int)
                    #     df_EB_d = pd.merge(df_EB, df_DR, on=['r'], how='outer')
                    #     df_EB_d['EBb4_EnergyBalanceEachYear4_ICR'] = df_EB_d['EBb4_EnergyBalanceEachYear4_ICR'] * pow((1 + df_EB_d['DiscountRate']), df_EB_d['y'] - start_year + 0.5)
                    #     df_EB_d.to_csv(os.path.join(base_folder, 'csv', 'EBb4_EnergyBalanceEachYear4_ICR.csv'), index=None)
                    if dual in all_params:
                        df_DR = pd.DataFrame(data['DiscountRate'], columns=Config.PARAMETERS_C_full['DiscountRate'])
                        df_DR['DiscountRate'] = df_DR['DiscountRate'].astype(float)
                        df_EB = all_params[dual]
                        df_EB['y'] = df_EB['y'].astype(int)
                        df_EB_d = pd.merge(df_EB, df_DR, on=['r'], how='outer')
                        df_EB_d[dual] = df_EB_d[dual] * pow((1 + df_EB_d['DiscountRate']), df_EB_d['y'] - start_year + 0.5)
                        df_EB_d.to_csv(os.path.join(base_folder, 'csv', dual+'.csv'), index=None)

                if 'AccumulatedNewStorageCapacity' in all_params:
                    df_ANSC = all_params['AccumulatedNewStorageCapacity'].rename(columns={'value':'AccumulatedNewStorageCapacity'})
                    df_RSC = pd.DataFrame(data['ResidualStorageCapacity'], columns=Config.PARAMETERS_C_full['ResidualStorageCapacity'])
                    df_RSC['ResidualStorageCapacity'] = df_RSC['ResidualStorageCapacity'].astype(float)

                    # print('AccumulatedNewStorageCapacity')
                    # print(df_ANSC.head())
                    # print('ResidualStorageCapacity')
                    # print(df_RSC.head())

                    df_TSC_tmp =  pd.merge(df_ANSC, df_RSC, on=['y', 's'] ,  how='outer')
                    df_TSC_tmp['ResidualStorageCapacity'] = df_TSC_tmp['ResidualStorageCapacity'].fillna(0)
                    df_TSC_tmp['TotalStorageCapacity'] = df_TSC_tmp['AccumulatedNewStorageCapacity'] + df_TSC_tmp['ResidualStorageCapacity']
                    df_TSC_tmp.sort_values(['s','y'], inplace=True)
                    
                    # print('TotalStorageCapacity')
                    # print(df_TSC_tmp.head())

                    df_TSC = df_TSC_tmp[['s','y','TotalStorageCapacity']]
                    df_TSC = df_TSC[df_TSC['TotalStorageCapacity']!=0]
                    df_TSC.to_csv(os.path.join(base_folder, 'csv', 'TotalStorageCapacity.csv'), index=None)
            
                if 'RateOfActivity' in all_params:
                    #year split data frame
                    df_yearsplit = pd.DataFrame(data['YearSplit'], columns=['r','y', 'l','YearSplit'])
                    df_activity = all_params['RateOfActivity'].rename(columns={'value':'RateOfActivity'})

                    # df_output = pd.DataFrame(data['OutputActivityRatio'], columns=['r','f','t','y','m','OutputActivityRatio'])
                    df_output = pd.DataFrame(data['OutputActivityRatio'], columns=Config.PARAMETERS_C_full['OutputActivityRatio'])
                    df_out_ys = pd.merge(df_output, df_yearsplit, on='y')
                    df_out_ys['OutputActivityRatio'] = df_out_ys['OutputActivityRatio'].astype(float)
                    df_out_ys['YearSplit'] = df_out_ys['YearSplit'].astype(float)
                    
                    # df_input = pd.DataFrame(data['InputActivityRatio'], columns=['r', 'f','t','y','m','InputActivityRatio'])
                    df_input = pd.DataFrame(data['InputActivityRatio'], columns=Config.PARAMETERS_C_full['InputActivityRatio'])
                    df_in_ys = pd.merge(df_input, df_yearsplit, on='y')
                    df_in_ys['InputActivityRatio'] = df_in_ys['InputActivityRatio'].astype(float)
                    df_in_ys['YearSplit'] = df_in_ys['YearSplit'].astype(float)
                    
                    # df_emi = pd.DataFrame(data['EmissionActivityRatio'], columns=['r', 'e','t','y','m','EmissionActivityRatio'])
                    df_emi = pd.DataFrame(data['EmissionActivityRatio'], columns=Config.PARAMETERS_C_full['EmissionActivityRatio'])
                    df_emi['EmissionActivityRatio'] = df_emi['EmissionActivityRatio'].astype(float)
                    #df_emi.to_csv(os.path.join(base_folder, 'emi_table.csv'), index=None)

                    #########################################Demand#################################################################
                    #SpecifiedAnnualDemand[r,f,y]*SpecifiedDemandProfile[r,f,l,y]+ AccumulatedAnnualDemand[r,f,y]
                    # df_sad = data['SpecifiedAnnualDemand'].rename(columns={'value':'SpecifiedAnnualDemand'})
                    # df_sdp = data['SpecifiedDemandProfile'].rename(columns={'value':'SpecifiedDemandProfile'})
                    # df_aad = data['AccumulatedAnnualDemand'].rename(columns={'value':'AccumulatedAnnualDemand'})

                    if not df_out_ys.empty:
                        ########################################ProductionByTechnologyByMode############################################
                        df_prod = pd.merge(df_out_ys, df_activity, how='left', on=['t','m','l','y'])
                        region = [x for x in list(df_prod.r.unique()) if str(x) != 'nan']
                        df_prod['r'] = str(region[0])
                        df_prod['RateOfActivity'].fillna(0, inplace=True)
                        df_prod['ProductionByTechnologyByMode'] = df_prod['OutputActivityRatio']*df_prod['YearSplit']*df_prod['RateOfActivity']
                        df_prod = df_prod.drop(['OutputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                        df_prod['ProductionByTechnologyByMode'] = df_prod['ProductionByTechnologyByMode'].astype(float).round(4)
                        df_prod = df_prod.sort_values(by=['r','l','t','f','y'])
                        df_prod = df_prod[df_prod['ProductionByTechnologyByMode']!=0]
                        df_prod.to_csv(os.path.join(base_folder, 'csv', 'ProductionByTechnologyByMode.csv'), index=None)

                        ########################################RateOfProductionByTechnologyByMode############################################
                        df_ropbt = pd.merge(df_out_ys, df_activity, how='left', on=['t','m','l','y'])
                        region = [x for x in list(df_ropbt.r.unique()) if str(x) != 'nan']
                        df_ropbt['r'] = str(region[0])
                        df_ropbt['RateOfActivity'].fillna(0, inplace=True)

                        df_ropbt['RateOfProductionByTechnologyByMode'] = df_ropbt['OutputActivityRatio']*df_ropbt['RateOfActivity']
                        df_ropbt = df_ropbt.drop(['OutputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                        df_ropbt['RateOfProductionByTechnologyByMode'] = df_ropbt['RateOfProductionByTechnologyByMode'].astype(float).round(4)
                        df_ropbt = df_ropbt.sort_values(by=['r','l','t','f','y'])
                        df_ropbt = df_ropbt[df_ropbt['RateOfProductionByTechnologyByMode']!=0]
                        df_ropbt.to_csv(os.path.join(base_folder, 'csv', 'RateOfProductionByTechnologyByMode.csv'), index=None)

                    

                    if not df_in_ys.empty:
                        ######################################UseByTechnologyByMode##############################################
                        df_use = pd.merge(df_in_ys, df_activity, how='left', on=['t','m','l','y'])
                        region = [x for x in list(df_use.r.unique()) if str(x) != 'nan']
                        df_use['r'] = str(region[0])
                        df_use['RateOfActivity'].fillna(0, inplace=True)
            
                        df_use['UseByTechnologyByMode'] = df_use['InputActivityRatio']*df_use['YearSplit']*df_use['RateOfActivity']
                        df_use = df_use.drop(['InputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                        df_use['UseByTechnologyByMode'] = df_use['UseByTechnologyByMode'].astype(float).round(4)
                        df_use = df_use.sort_values(by=['r','l','t','f','y'])
                        df_use = df_use[df_use['UseByTechnologyByMode']!=0]
                        df_use.to_csv(os.path.join(base_folder, 'csv', 'UseByTechnologyByMode.csv'), index=None)

                        ######################################RateOfUseByTechnologyByMode##############################################
                        df_roubt = pd.merge(df_in_ys, df_activity, how='left', on=['t','m','l','y'])
                        region = [x for x in list(df_roubt.r.unique()) if str(x) != 'nan']
                        df_roubt['r'] = str(region[0])
                        df_roubt['RateOfActivity'].fillna(0, inplace=True)
            
                        df_roubt['RateOfUseByTechnologyByMode'] = df_roubt['InputActivityRatio']*df_roubt['RateOfActivity']
                        df_roubt = df_roubt.drop(['InputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                        df_roubt['RateOfUseByTechnologyByMode'] = df_roubt['RateOfUseByTechnologyByMode'].astype(float).round(4)
                        df_roubt = df_roubt.sort_values(by=['r','l','t','f','y'])
                        df_roubt = df_roubt[df_roubt['RateOfUseByTechnologyByMode']!=0]
                        df_roubt.to_csv(os.path.join(base_folder, 'csv', 'RateOfUseByTechnologyByMode.csv'), index=None)

                if 'CapitalInvestment' in all_params:
                    #########################################AnnualizedInvestmentCost################################################
                    df_OL = pd.DataFrame(data['OperationalLife'], columns=Config.PARAMETERS_C_full['OperationalLife'])
                    df_OL['OperationalLife'] = df_OL['OperationalLife'].astype(int)
                    df_DRi = pd.DataFrame(data['DiscountRateIdv'], columns=Config.PARAMETERS_C_full['DiscountRateIdv'])
                    df_DRi['DiscountRateIdv'] = df_DRi['DiscountRateIdv'].astype(float)
                    df_CRF = pd.merge(df_DRi, df_OL, on=['r', 't'])
                    df_CRF['CRF'] = (1 - pow( (1+df_CRF['DiscountRateIdv']), -1) ) / (1 - pow( (1+df_CRF['DiscountRateIdv']), -df_CRF['OperationalLife'] ) )

                    df_CI = all_params['CapitalInvestment']
                    full_df = pd.DataFrame([(i, s) for i in tech_list for s in year_list], columns=['t', 'y'])
    
                    df_ACI_temp = pd.merge(df_CI, full_df, on=['t','y'],  how='outer')
                    df_ACI_temp['CapitalInvestment'] = df_ACI_temp['CapitalInvestment'].fillna(0)
                    df_ACI_temp['r'] = df_ACI_temp['r'].fillna('RE1')
                    df_ACI_temp = pd.merge(df_ACI_temp, df_CRF, on=['r', 't'],  how='outer')
                    df_ACI_temp['CIxCRF'] = df_ACI_temp['CapitalInvestment'] * df_ACI_temp['CRF']
                    df_ACI_temp.sort_values(['t','y'], inplace=True)
                    tech_current = ''
                    cumulativeList = []
                    for index, row in df_ACI_temp.iterrows():
                        if tech_current != row['t']:
                            cumulativeList = []
                        cumulativeList.append(row['CIxCRF'])
                        df_ACI_temp.loc[index,'AnnualizedInvestmentCost'] = sum(cumulativeList[-row['OperationalLife']:])
                        tech_current = row['t']
                        # if int(start_year) + row['OperationalLife'] <= int(row['y']) or tech_current != row['t']:
                        #     Sum = 0
                        # Sum += row['CIxCRF']
                        # df_ACI_temp.loc[index,'AnnualizedInvestmentCost'] = Sum
                        # tech_current = row['t']

                    df_ACI = df_ACI_temp[['r','t','y','AnnualizedInvestmentCost']]
                    df_ACI = df_ACI[df_ACI['AnnualizedInvestmentCost']!=0]
                    df_ACI.to_csv(os.path.join(base_folder, 'csv', 'AnnualizedInvestmentCost.csv'), index=None)
        except Exception as ex:
            print(ex) # do whatever you want for debugging.
            raise    # re-raise exception.
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError
    
    def generateResultsViewer(self, caserunname):
        try:
            csvFolderPath = Path(Config.DATA_STORAGE,self.case,'res',caserunname, 'csv')

            #CSV
            csvs = [f.name for f in os.scandir(csvFolderPath) ]

            paramByName = {}
            for group, array in self.VARIABLES.items():
                for obj in array:
                    o = {}
                    o['id'] = obj['id']
                    o['group'] = group
                    paramByName[obj['name']] = o

            DATA = {}
            for csv in csvs:
                #read csv file
                csv_path = Path(Config.DATA_STORAGE,self.case,'res', caserunname, 'csv', csv)
                if csv_path.is_file():
                    df = pd.read_csv(csv_path)
                    data = df.to_json(orient='records', indent=2)
                    jsondata = json.loads(data)

                    if len(jsondata) != 0:
                        for param, paramobj in paramByName.items():

                            if param in jsondata[0]:

                                viewGroupPath = Path(Config.DATA_STORAGE,self.case,'view', paramobj['group']+ '.json')
                                if viewGroupPath.is_file():
                                    viewData = File.readFile(viewGroupPath)
                                else:
                                    viewData = {}

                                if paramobj['id'] not in viewData:
                                    viewData[paramobj['id']] = {}

                                # if caserunname not in viewData[paramobj['id']]:
                                #     viewData[paramobj['id']][caserunname] = []

                                #ovdje uvijek moramo napraviti novi niy jer je novi caserun i novi podaci
                                viewData[paramobj['id']][caserunname] = []

                                if paramobj['group'] == 'R':
                                    tmp = {}
                                    for obj in jsondata:
                                        tmp['ObjectiveValue'] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RT':
                                    tmp = {}
                                    for obj in jsondata:
                                        tmp[ obj['t']] =obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RYT':
                                    tech = jsondata[0]['t']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t']:
                                            tmp['Tech'] = obj['t']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)  

                                if paramobj['group'] == 'RYCn':
                                    con = jsondata[0]['cn']
                                    tmp = {}
                                    for obj in jsondata:
                                        if con == obj['cn']:
                                            tmp['Con'] = obj['cn']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            con = obj['cn']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Con'] = obj['cn']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)  

                                if paramobj['group'] == 'RYC':
                                    comm = jsondata[0]['f']
                                    tmp = {}
                                    for obj in jsondata:
                                        if comm == obj['f']:
                                            tmp['Comm'] = obj['f']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            comm = obj['f']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Comm'] = obj['f']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path) 

                                if paramobj['group'] == 'RYE':
                                    emi = jsondata[0]['e']
                                    tmp = {}
                                    for obj in jsondata:
                                        if emi == obj['e']:
                                            tmp['Emi'] = obj['e']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            emi = obj['e']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Emi'] = obj['e']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)  

                                if paramobj['group'] == 'RYS':
                                    stg = jsondata[0]['s']
                                    tmp = {}
                                    for obj in jsondata:
                                        if stg == obj['s']:
                                            tmp['Stg'] = obj['s']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            stg = obj['s']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Stg'] = obj['s']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path) 

                                if paramobj['group'] == 'RYTM':
                                    tech = jsondata[0]['t']
                                    mod = jsondata[0]['m']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and mod == obj['m']:
                                            tmp['Tech'] = obj['t']
                                            tmp['MoId'] = obj['m']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            mod = obj['m']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['MoId'] = obj['m']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RYTC':
                                    tech = jsondata[0]['t']
                                    comm = jsondata[0]['f']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and comm == obj['f']:
                                            tmp['Tech'] = obj['t']
                                            tmp['Comm'] = obj['f']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            comm = obj['f']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['Comm'] = obj['f']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RYTE':
                                    tech = jsondata[0]['t']
                                    emi = jsondata[0]['e']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and emi == obj['e']:
                                            tmp['Tech'] = obj['t']
                                            tmp['Emi'] = obj['e']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            emi = obj['e']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['Emi'] = obj['e']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RYTTs':
                                    tech = jsondata[0]['t']
                                    ts = jsondata[0]['l']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and ts == obj['l']:
                                            tmp['Tech'] = obj['t']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            ts = obj['l']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RYCTs':
                                    comm = jsondata[0]['f']
                                    ts = jsondata[0]['l']
                                    tmp = {}
                                    for obj in jsondata:
                                        if comm == obj['f'] and ts == obj['l']:
                                            tmp['Comm'] = obj['f']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            comm = obj['f']
                                            ts = obj['l']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Comm'] = obj['f']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RYTEM':
                                    tech = jsondata[0]['t']
                                    emi = jsondata[0]['e']
                                    mod = jsondata[0]['m']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and emi == obj['e'] and mod == obj['m']:
                                            tmp['Tech'] = obj['t']
                                            tmp['Emi'] = obj['e']
                                            tmp['MoId'] = obj['m']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            emi = obj['e']
                                            mod = obj['m']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['Emi'] = obj['e']
                                            tmp['MoId'] = obj['m']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                if paramobj['group'] == 'RYTCTs':
                                    tech = jsondata[0]['t']
                                    comm = jsondata[0]['f']
                                    ts = jsondata[0]['l']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and comm == obj['f'] and ts == obj['l']:
                                            tmp['Tech'] = obj['t']
                                            tmp['Comm'] = obj['f']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            comm = obj['f']
                                            ts = obj['l']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['Comm'] = obj['f']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)

                                # ne postoje vise varijable za ovaj dio Production By tecnology, Use By technology
                                if paramobj['group'] == 'RYTMTs':
                                    tech = jsondata[0]['t']
                                    mod = jsondata[0]['m']
                                    ts = jsondata[0]['l']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and mod == obj['m'] and ts == obj['l']:
                                            tmp['Tech'] = obj['t']
                                            tmp['MoId'] = obj['m']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            mod = obj['m']
                                            ts = obj['l'] 
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['MoId'] = obj['m']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)
                            
                                # ne koristi se jer smo izbrisali variajablu ROUBTBM Rate Of Use By Technology By Mode
                                #ponovo koristimo jer korisitmo Production By Technology by Mode, Use By Technology By Mode (isto i sa Rate of...)
                                if paramobj['group'] == 'RYTCMTs':
                                    tech = jsondata[0]['t']
                                    comm = jsondata[0]['f']
                                    mod = jsondata[0]['m']
                                    ts = jsondata[0]['l']
                                    tmp = {}
                                    for obj in jsondata:
                                        if tech == obj['t'] and comm == obj['f'] and mod == obj['m'] and ts == obj['l']:
                                            tmp['Tech'] = obj['t']
                                            tmp['Comm'] = obj['f']
                                            tmp['MoId'] = obj['m']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                        else:
                                            tech = obj['t']
                                            comm = obj['f']
                                            mod = obj['m']
                                            ts = obj['l']
                                            viewData[paramobj['id']][caserunname].append(tmp)
                                            tmp = {}
                                            tmp['Tech'] = obj['t']
                                            tmp['Comm'] = obj['f']
                                            tmp['MoId'] = obj['m']
                                            tmp['Ts'] = obj['l']
                                            tmp[obj['y']] = obj[param]
                                    viewData[paramobj['id']][caserunname].append(tmp)
                                    path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                    File.writeFile( viewData, path)
                                
                                break

        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError


    ############################################################################################### OBSOLETE METHODS 
    def generateResultsViewer_AllCases20240118(self, caserunname):
        try:
            csvFolderPath = Path(Config.DATA_STORAGE,self.case,'res',caserunname, 'csv')
            #viewFolderPath = Path(Config.DATA_STORAGE,self.case,'view')

            #CSV
            csvs = [f.name for f in os.scandir(csvFolderPath) ]
            # cases = [f.name for f in os.scandir(self.resultsPath) if not os.listdir(csvFolderPath) ]

            #uzeti samo caseRunove koji imaju csv fileve, sto znaci da su imalu success run
            cases = [f.name for f in os.scandir(self.resultsPath) if os.path.isdir(Path(self.resultsPath, f.name, 'csv')) and len(os.listdir(Path(self.resultsPath, f.name, 'csv'))) != 0 ]
            
            paramByName = {}
            for group, array in self.VARIABLES.items():
                for obj in array:
                    o = {}
                    o['id'] = obj['id']
                    o['group'] = group
                    paramByName[obj['name']] = o

            DATA = {}
            #updateje sve caserunove
            for case in cases:

                for csv in csvs:

                    #read csv file
                    csv_path = Path(Config.DATA_STORAGE,self.case,'res', case, 'csv', csv)
                    if csv_path.is_file():
                        df = pd.read_csv(csv_path)
                        data = df.to_json(orient='records', indent=2)
                        jsondata = json.loads(data)

                        if len(jsondata) != 0:
                            for param, paramobj in paramByName.items():
                                if param in jsondata[0]:
                                    if paramobj['group'] not in DATA:
                                        DATA[paramobj['group']] = {}

                                    if paramobj['group'] == 'RT':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tmp = {}
                                        for obj in jsondata:
                                            tmp[ obj['t']] =obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)
    
                                    if paramobj['group'] == 'RYT':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t']:
                                                tmp['Tech'] = obj['t']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)  

                                    if paramobj['group'] == 'RYE':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        emi = jsondata[0]['e']
                                        tmp = {}
                                        for obj in jsondata:
                                            if emi == obj['e']:
                                                tmp['Emi'] = obj['e']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                emi = obj['e']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Emi'] = obj['e']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)  

                                    if paramobj['group'] == 'RYTM':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        mod = jsondata[0]['m']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and mod == obj['m']:
                                                tmp['Tech'] = obj['t']
                                                tmp['MoId'] = obj['m']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                mod = obj['m']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['MoId'] = obj['m']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)
    
                                    if paramobj['group'] == 'RYTC':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        comm = jsondata[0]['f']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and comm == obj['f']:
                                                tmp['Tech'] = obj['t']
                                                tmp['Comm'] = obj['f']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                comm = obj['f']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['Comm'] = obj['f']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)

                                    if paramobj['group'] == 'RYTE':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        emi = jsondata[0]['e']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and emi == obj['e']:
                                                tmp['Tech'] = obj['t']
                                                tmp['Emi'] = obj['e']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                emi = obj['e']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['Emi'] = obj['e']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)
    
                                    if paramobj['group'] == 'RYTTs':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        ts = jsondata[0]['l']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and ts == obj['l']:
                                                tmp['Tech'] = obj['t']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                ts = obj['l']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)
    
                                    if paramobj['group'] == 'RYCTs':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        comm = jsondata[0]['f']
                                        ts = jsondata[0]['l']
                                        tmp = {}
                                        for obj in jsondata:
                                            if comm == obj['f'] and ts == obj['l']:
                                                tmp['Comm'] = obj['f']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                comm = obj['f']
                                                ts = obj['l']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Comm'] = obj['f']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)

                                    if paramobj['group'] == 'RYTEM':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        emi = jsondata[0]['e']
                                        mod = jsondata[0]['m']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and emi == obj['e'] and mod == obj['m']:
                                                tmp['Tech'] = obj['t']
                                                tmp['Emi'] = obj['e']
                                                tmp['MoId'] = obj['m']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                emi = obj['e']
                                                mod = obj['m']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['Emi'] = obj['e']
                                                tmp['MoId'] = obj['m']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)

                                    if paramobj['group'] == 'RYTCTs':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}

                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        comm = jsondata[0]['f']
                                        ts = jsondata[0]['l']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and comm == obj['f'] and ts == obj['l']:
                                                tmp['Tech'] = obj['t']
                                                tmp['Comm'] = obj['f']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                comm = obj['f']
                                                ts = obj['l']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['Comm'] = obj['f']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)

                                    # ne postoje vise varijable za ovaj dio Production By tecnology, Use By technology
                                    if paramobj['group'] == 'RYTMTs':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        mod = jsondata[0]['m']
                                        ts = jsondata[0]['l']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and mod == obj['m'] and ts == obj['l']:
                                                tmp['Tech'] = obj['t']
                                                tmp['MoId'] = obj['m']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                mod = obj['m']
                                                ts = obj['l'] 
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['MoId'] = obj['m']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)
                                
                                    #ne koristi se jer smo izbrisali variajablu ROUBTBM Rate Of Use By Technology By Mode
                                    #ponovo koristimo jer korisitmo Production By Technology by Mode, Use By Technology By Mode (isto i sa Rate of...)
                                    if paramobj['group'] == 'RYTCMTs':
                                        if paramobj['id'] not in DATA[paramobj['group']]:
                                            DATA[paramobj['group']][paramobj['id']] = {}
                                        DATA[paramobj['group']][paramobj['id']][case] = []
                                        tech = jsondata[0]['t']
                                        comm = jsondata[0]['f']
                                        mod = jsondata[0]['m']
                                        ts = jsondata[0]['l']
                                        tmp = {}
                                        for obj in jsondata:
                                            if tech == obj['t'] and comm == obj['f'] and mod == obj['m'] and ts == obj['l']:
                                                tmp['Tech'] = obj['t']
                                                tmp['Comm'] = obj['f']
                                                tmp['MoId'] = obj['m']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                            else:
                                                tech = obj['t']
                                                comm = obj['f']
                                                mod = obj['m']
                                                ts = obj['l']
                                                DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                                tmp = {}
                                                tmp['Tech'] = obj['t']
                                                tmp['Comm'] = obj['f']
                                                tmp['MoId'] = obj['m']
                                                tmp['Ts'] = obj['l']
                                                tmp[obj['y']] = obj[param]
                                        DATA[paramobj['group']][paramobj['id']][case].append(tmp)
                                        path = Path(self.viewFolderPath, paramobj['group']+'.json')
                                        File.writeFile( DATA[paramobj['group']], path)
                                    break

        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    # Dodali u postprocessing Annualized Investment Cost - potrebo dodati nove parametre
    def generateCSVfromCBC_20240228(self, data_file, results_file, base_folder=os.getcwd()):
        try:
            #pd.options.mode.chained_assignment = None
            #pd.options.mode.chained_assignment = None

            parsing = False
            output_table = []
            input_table = []
            emi_table = []
            year_split = []

            year_list = self.getYears()
            start_year = year_list[0]

            with open(data_file, 'r') as f:
                for line in f:
                    if line.startswith(";"):
                        parsing = False
                    if parsing:
                        if line.startswith('['):
                            fuel = line.split(',')[2]
                            tech = line.split(',')[1]                        
                        elif not line.startswith(start_year):
                            values = line.rstrip().split(' ')[1:]
                            mode = line.split(' ')[0] #mode ili time_slice
                            time_slice = line.rstrip().split(' ')[0]
   
                            if param_current=='OutputActivityRatio':
                                for i in range(0,len(year_list)):
                                    output_table.append(tuple([tech,fuel,mode,year_list[i],values[i]]))

                            if param_current=='InputActivityRatio':
                                for i in range(0,len(year_list)):
                                    input_table.append(tuple([tech,fuel,mode,year_list[i],values[i]]))
                            
                            if param_current == 'EmissionActivityRatio':
                                for i in range(0,len(year_list)):
                                    emi_table.append(tuple([tech,fuel,mode,year_list[i],values[i]]))
                        
                            if param_current == 'YearSplit':
                                for i in range(0,len(year_list)):
                                    year_split.append(tuple([time_slice,year_list[i],values[i]]))

                    if line.startswith(('param OutputActivityRatio','param InputActivityRatio','param TechnologyToStorage','param TechnologyFromStorage', 'param EmissionActivityRatio', 'param YearSplit')):
                        param_current = line.split(' ')[1]
                        parsing = True

            try:
                os.makedirs(os.path.join(base_folder, 'csv'))
            except FileExistsError:
                pass
            
            #parsanje result.txt
            params = []
            
            df = pd.read_csv(results_file, sep='\t')
            df.columns = ['temp']

            df['temp'] = df['temp'].str.lstrip(' *\n\t')
            #(df['temp'])
            
            if len(df) > 0:
                df[['temp','value']] = df['temp'].str.split(')', expand=True)
                df = df.applymap(lambda x: x.strip() if isinstance(x,str) else x)
                #error when moved to ython 3.11, Columns must have smae length as key
                # df['value'] = df['value'].str.split(' ', expand=True)
                df['value'] = df['value'].str.split(' ', expand=True)[0]
                df[['parameter','id']] = df['temp'].str.split('(', expand=True)
                df['parameter'] = df['parameter'].str.split(' ', expand=True)[1]
                df = df.drop('temp', axis=1)
                df['value'] = df['value'].astype(float).round(4)

                #variables that are output form solver 18
                params = df.parameter.unique()
                all_params = {}

                for each in params:
                    result_cols = []

                    # radi problem izmjena da dataframe bez copije 20240118 vk
                    # df_p = df[df.parameter == each]
                    # df_p[Config.VARIABLES_C[each]] = df_p['id'].str.split(',',expand=True)

                    df_p = df[df.parameter == each].copy()
                    df_p[Config.VARIABLES_C[each]] = df_p['id'].str.split(',',expand=True)

                    result_cols = Config.VARIABLES_C[each].copy()
                    result_cols.append('value')
                    #result_cols.append(each)
                    df_p = df_p[result_cols] # Reorder dataframe to include 'value' as last column
                    all_params[each] = pd.DataFrame(df_p) # Create a dataframe for each parameter

                    #napravi csv
                    all_params[each] = all_params[each].rename(columns={'value':each})
                    all_params[each].to_csv(os.path.join(base_folder, 'csv', each+'.csv'), index=None)

                ########################################Vars koje se izracunavaju u ovoj script nisu izlaz iz solvera###########
                ################################################################################################################

                #year split data frame
                df_yearsplit = pd.DataFrame(year_split, columns=['l','y','YearSplit'])
                df_activity = all_params['RateOfActivity'].rename(columns={'value':'RateOfActivity'})

                df_output = pd.DataFrame(output_table, columns=['t','f','m','y','OutputActivityRatio'])
                df_out_ys = pd.merge(df_output, df_yearsplit, on='y')
                df_out_ys['OutputActivityRatio'] = df_out_ys['OutputActivityRatio'].astype(float)
                df_out_ys['YearSplit'] = df_out_ys['YearSplit'].astype(float)
                
                df_input = pd.DataFrame(input_table, columns=['t','f','m','y','InputActivityRatio'])
                df_in_ys = pd.merge(df_input, df_yearsplit, on='y')
                df_in_ys['InputActivityRatio'] = df_in_ys['InputActivityRatio'].astype(float)
                df_in_ys['YearSplit'] = df_in_ys['YearSplit'].astype(float)
                
                df_emi = pd.DataFrame(emi_table, columns=['t','e','m','y','EmissionActivityRatio'])
                df_emi['EmissionActivityRatio'] = df_emi['EmissionActivityRatio'].astype(float)
                #df_emi.to_csv(os.path.join(base_folder, 'emi_table.csv'), index=None)
   
                ########################################ProductionByTechnologyByMode############################################
                df_prod = pd.merge(df_out_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_prod.r.unique()) if str(x) != 'nan']
                df_prod['r'] = str(region[0])
                df_prod['RateOfActivity'].fillna(0, inplace=True)

                df_prod['ProductionByTechnologyByMode'] = df_prod['OutputActivityRatio']*df_prod['YearSplit']*df_prod['RateOfActivity']
                df_prod = df_prod.drop(['OutputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_prod['ProductionByTechnologyByMode'] = df_prod['ProductionByTechnologyByMode'].astype(float).round(4)
                df_prod = df_prod.sort_values(by=['r','l','t','f','y'])
                df_prod.to_csv(os.path.join(base_folder, 'csv', 'ProductionByTechnologyByMode.csv'), index=None)

                ########################################RateOfProductionByTechnologyByMode############################################
                df_ropbt = pd.merge(df_out_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_ropbt.r.unique()) if str(x) != 'nan']
                df_ropbt['r'] = str(region[0])
                df_ropbt['RateOfActivity'].fillna(0, inplace=True)

                df_ropbt['RateOfProductionByTechnologyByMode'] = df_ropbt['OutputActivityRatio']*df_ropbt['RateOfActivity']
                df_ropbt = df_ropbt.drop(['OutputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_ropbt['RateOfProductionByTechnologyByMode'] = df_ropbt['RateOfProductionByTechnologyByMode'].astype(float).round(4)
                df_ropbt = df_ropbt.sort_values(by=['r','l','t','f','y'])
                df_ropbt.to_csv(os.path.join(base_folder, 'csv', 'RateOfProductionByTechnologyByMode.csv'), index=None)

                ######################################UseByTechnologyByMode##############################################

                df_use = pd.merge(df_in_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_use.r.unique()) if str(x) != 'nan']
                df_use['r'] = str(region[0])
                df_use['RateOfActivity'].fillna(0, inplace=True)
       
                df_use['UseByTechnologyByMode'] = df_use['InputActivityRatio']*df_use['YearSplit']*df_use['RateOfActivity']
                df_use = df_use.drop(['InputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_use['UseByTechnologyByMode'] = df_use['UseByTechnologyByMode'].astype(float).round(4)
                df_use = df_use.sort_values(by=['r','l','t','f','y'])
                df_use.to_csv(os.path.join(base_folder, 'csv', 'UseByTechnologyByMode.csv'), index=None)

                ######################################RateOfUseByTechnologyByMode##############################################

                df_roubt = pd.merge(df_in_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_roubt.r.unique()) if str(x) != 'nan']
                df_roubt['r'] = str(region[0])
                df_roubt['RateOfActivity'].fillna(0, inplace=True)
       
                df_roubt['RateOfUseByTechnologyByMode'] = df_roubt['InputActivityRatio']*df_roubt['RateOfActivity']
                df_roubt = df_roubt.drop(['InputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_roubt['RateOfUseByTechnologyByMode'] = df_roubt['RateOfUseByTechnologyByMode'].astype(float).round(4)
                df_roubt = df_roubt.sort_values(by=['r','l','t','f','y'])
                df_roubt.to_csv(os.path.join(base_folder, 'csv', 'RateOfUseByTechnologyByMode.csv'), index=None)

        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError
    
    ##izmjene da bi se napunili csv za InputToNewCapacity i InputToTotalCapacity
    def generateCSVfromCBC09122023(self, data_file, results_file, base_folder=os.getcwd()):
        try:
            #pd.options.mode.chained_assignment = None

            parsing = False
            output_table = []
            input_table = []
            emi_table = []
            year_split = []

            year_list = self.getYears()
            fuel_list = self.getCommNames()
            tech_list = self.getTechNames()
            emission_list = self.getEmiNames()
            ts_list = self.getTimeslices()
            mode_list = self.getMods()
            region_list = ['RE1']
            start_year = year_list[0]

            with open(data_file, 'r') as f:
                for line in f:
                    if line.startswith(";"):
                        parsing = False
                    if parsing:
                        if line.startswith('['):
                            fuel = line.split(',')[2]
                            tech = line.split(',')[1]                        
                        elif not line.startswith(start_year):
                            values = line.rstrip().split(' ')[1:]
                            mode = line.split(' ')[0] #mode ili time_slice
                            time_slice = line.rstrip().split(' ')[0]
   
                            if param_current=='OutputActivityRatio':
                                for i in range(0,len(year_list)):
                                    output_table.append(tuple([tech,fuel,mode,year_list[i],values[i]]))

                            if param_current=='InputActivityRatio':
                                for i in range(0,len(year_list)):
                                    input_table.append(tuple([tech,fuel,mode,year_list[i],values[i]]))
                            
                            if param_current == 'EmissionActivityRatio':
                                for i in range(0,len(year_list)):
                                    emi_table.append(tuple([tech,fuel,mode,year_list[i],values[i]]))
                        
                            if param_current == 'YearSplit':
                                for i in range(0,len(year_list)):
                                    year_split.append(tuple([time_slice,year_list[i],values[i]]))

                    if line.startswith(('param OutputActivityRatio','param InputActivityRatio','param TechnologyToStorage','param TechnologyFromStorage', 'param EmissionActivityRatio', 'param YearSplit')):
                        param_current = line.split(' ')[1]
                        parsing = True

            try:
                os.makedirs(os.path.join(base_folder, 'csv'))
            except FileExistsError:
                pass
            
            #parsanje result.txt
            params = []
            
            df = pd.read_csv(results_file, sep='\t')

            df.columns = ['temp']
            df['temp'] = df['temp'].str.lstrip(' *\n\t')
            
            if len(df) > 0:
                df[['temp','value']] = df['temp'].str.split(')', expand=True)
                df = df.applymap(lambda x: x.strip() if isinstance(x,str) else x)
                #error when moved to ython 3.11, Columns must have smae length as key
                # df['value'] = df['value'].str.split(' ', expand=True)
                df['value'] = df['value'].str.split(' ', expand=True)[0]
                df[['parameter','id']] = df['temp'].str.split('(', expand=True)
                df['parameter'] = df['parameter'].str.split(' ', expand=True)[1]
                df = df.drop('temp', axis=1)
                df['value'] = df['value'].astype(float).round(4)

                #variables that are output form solver 18
                params = df.parameter.unique()
                all_params = {}

    
                for each in params:
                    result_cols = []
                    df_p = df[df.parameter == each]
                    df_p[Config.VARIABLES_C[each]] = df_p['id'].str.split(',',expand=True)
                    result_cols = Config.VARIABLES_C[each].copy()
                    result_cols.append('value')
                    df_p = df_p[result_cols] # Reorder dataframe to include 'value' as last column
                    all_params[each] = pd.DataFrame(df_p) # Create a dataframe for each parameter
                    df_p = df_p.rename(columns={'value':each})
            
            
            #year split data frame
            df_yearsplit = pd.DataFrame(year_split, columns=['l','y','YearSplit'])

            if len(df) > 0:
                df_activity = all_params['RateOfActivity'].rename(columns={'value':'RateOfActivity'})
                #df_activity_total = all_params['TotalAnnualTechnologyActivityByMode'].rename(columns={'value':'TotalAnnualTechnologyActivityByMode'})

            ####################################################################################

            df_output = pd.DataFrame(output_table, columns=['t','f','m','y','OutputActivityRatio'])
            df_out_ys = pd.merge(df_output, df_yearsplit, on='y')
            df_out_ys['OutputActivityRatio'] = df_out_ys['OutputActivityRatio'].astype(float)
            df_out_ys['YearSplit'] = df_out_ys['YearSplit'].astype(float)
            
            df_input = pd.DataFrame(input_table, columns=['t','f','m','y','InputActivityRatio'])
            df_in_ys = pd.merge(df_input, df_yearsplit, on='y')
            df_in_ys['InputActivityRatio'] = df_in_ys['InputActivityRatio'].astype(float)
            df_in_ys['YearSplit'] = df_in_ys['YearSplit'].astype(float)
            
            df_emi = pd.DataFrame(emi_table, columns=['t','e','m','y','EmissionActivityRatio'])
            df_emi['EmissionActivityRatio'] = df_emi['EmissionActivityRatio'].astype(float)
            #df_emi.to_csv(os.path.join(base_folder, 'emi_table.csv'), index=None)
            
            ##################################################################################
            
            index_dict = {'r': region_list,
                        'rr': region_list,
                        'l': ts_list,
                        't': tech_list,
                        'f': fuel_list,
                        'm': mode_list,
                        'e': emission_list,
                        'y': year_list}
            
            def sort_df(df):
                if 'y' in df.columns:
                    sorted_df = df.sort_values(by=['y'])
                else:
                    sorted_df = df.copy()
                return sorted_df
            
            def tuple_to_dict(data_table):
                tuple_list = [[col1, col2, col3, col4, col5] for (col1, col2, col3, col4, col5) in data_table]
                df = pd.DataFrame(tuple_list, columns=['t','f','m','y','value']) 
                df = df[['t','f','m','y']].drop_duplicates()
                return df
            
            df_all = pd.concat([tuple_to_dict(input_table), tuple_to_dict(output_table)])

            combo_cols = list(df_all.columns)    

            # for each_result in results_list:
            for each_result in self.VARS:
                iter_list = []
                df_combinations = pd.DataFrame()
                cols_in_df = []
                cols_notin_df = []

                if any(x in combo_cols for x in Config.VARIABLES_C[each_result]):
                    cols_in_df = [v for v in Config.VARIABLES_C[each_result] if v in combo_cols]
                    cols_notin_df = [v for v in Config.VARIABLES_C[each_result] if v not in combo_cols]
                    
                df_combinations = df_all[cols_in_df].drop_duplicates()
   
                for each_index in cols_notin_df:
                    #print("index_dict[each_index] ", index_dict[each_index])  
                    iter_list.append(index_dict[each_index])
                
                # print("iter_list ", iter_list)
                df_combinations_2 = pd.DataFrame(product(*iter_list), columns=cols_notin_df)

                df_combinations['key'] = 1
                df_combinations_2['key'] = 1
                #In a future version of pandas all arguments of DataFrame.drop except for the argument 'labels' will be keyword-only.
                #df_combinations = pd.merge(df_combinations, df_combinations_2, on='key').drop('key', 1)
                #fixed by adding axis 0 is for columns 1 is for index vk 06.10.2023
                df_combinations = pd.merge(df_combinations, df_combinations_2, on='key').drop('key', axis=1)

                #df_combinations = pd.DataFrame(product(*iter_list),  columns=cols[each_result])
                
                ##08122023 VK InputToNewCapacity InputToTotalCapacityi zbrisali smo Output da bi ova dva parametra isli direktno iz results.txt
                #if any(substring in each_result for substring in ['Production', 'Output']):
                if any(substring in each_result for substring in ['Production']):
                    col_keep = []
                    for each_col in df_output.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)
                            
                    df_output_result = df_output[col_keep]
                    df_output_result.drop_duplicates(inplace=True)
                    df_combinations = pd.merge(df_output_result, df_combinations, how='left', on=col_keep)
                    df_combinations.drop_duplicates(inplace=True)
                     
                ##08122023 VK InputToNewCapacity InputToTotalCapacity izbrisali smo Input da bi ova dva parametra isli direktno iz results.txt
                # if any(substring in each_result for substring in ['Use', 'Input']):
                if any(substring in each_result for substring in ['Use']):
                    col_keep = []

                    for each_col in df_input.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)

                    df_input_result = df_input[col_keep]
                    df_input_result.drop_duplicates(inplace=True)
                    df_combinations = pd.merge(df_input_result, df_combinations, how='left', on=col_keep)
                    df_combinations.drop_duplicates(inplace=True)
                
                if 'Activity' in each_result:
                    col_keep = []
                    for each_col in df_input.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)
                    
                    if len(df) > 0:
                        df_input_output = pd.concat([df_input, df_output], sort=True)
                        df_input_output = df_input_output[col_keep]
                        df_input_output.drop_duplicates(inplace=True)
                        df_combinations = pd.merge(df_input_output, df_combinations, how='left', on=col_keep)
                        df_combinations.drop_duplicates(inplace=True)
                    
                if 'e' in Config.VARIABLES_C[each_result]:
                    col_keep = []
                    for each_col in df_emi.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)
                    
                    df_emi_result = df_emi[col_keep]
                    df_emi_result.drop_duplicates(inplace=True)
                    df_combinations = pd.merge(df_emi_result, df_combinations, how='left', on=col_keep)
                    df_combinations.drop_duplicates(inplace=True)
                
                # If result parameter in CBC results file, merge results from all_params.
                # Else, enter '0' for all rows.
                
                if each_result in params:
                    df_combinations = pd.merge(df_combinations, all_params[each_result], how='left', on=Config.VARIABLES_C[each_result])
                    df_combinations.rename(columns={'value':each_result}, inplace=True)
                    df_combinations.fillna(0, inplace=True)
                
                else:
                    df_combinations[each_result] = 0
                
                # For final dataframes, reorder columns based on original Config.VARIABLES_C dictionary          
                df_combinations = df_combinations.sort_values(by=Config.VARIABLES_C[each_result])
                
                final_cols = []
                final_cols = Config.VARIABLES_C[each_result].copy()
                final_cols.append(each_result)
                df_combinations = df_combinations[final_cols]
                
                
                df_combinations.to_csv(os.path.join(base_folder, 'csv', each_result+'.csv'), index=None)

            ##08122023 VK InputToNewCapacity InputToTotalCapacity
            # df_InputToNewCapacity = all_params['InputToNewCapacity'].rename(columns={'value':'InputToNewCapacity'})
            # df_InputToTotalCapacity = all_params['InputToTotalCapacity'].rename(columns={'value':'InputToTotalCapacity'})
            # df_InputToNewCapacity.to_csv(os.path.join(base_folder, 'csv', 'InputToNewCapacity.csv'), index=None)
            # df_InputToTotalCapacity.to_csv(os.path.join(base_folder, 'csv', 'InputToTotalCapacity.csv'), index=None)
            
            ########################################Vars koje se izracunavaju u ovoj script nisu izlaz iz solvera###########
            ########################################ProductionByTechnologyAnnual############################################
            
            if len(df) > 0:
                df_prod = pd.merge(df_out_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_prod.r.unique()) if str(x) != 'nan']
                df_prod['r'] = str(region[0])
                df_prod['RateOfActivity'].fillna(0, inplace=True)

                df_prod['ProductionByTechnology'] = df_prod['OutputActivityRatio']*df_prod['YearSplit']*df_prod['RateOfActivity']
                df_prod = df_prod.drop(['OutputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_prod['ProductionByTechnology'] = df_prod['ProductionByTechnology'].astype(float).round(4)
                df_prod = df_prod.sort_values(by=['r','l','t','f','y'])
                df_prod.to_csv(os.path.join(base_folder, 'csv', 'ProductionByTechnology.csv'), index=None)


                # df_prodAn = pd.merge(df_out_ys, df_activity, how='left', on=['t','m','l','y'])
                # _region = [x for x in list(df_prodAn.r.unique()) if str(x) != 'nan']
                # df_prodAn['r'] = str(region[0])
                # df_prodAn['RateOfActivity'].fillna(0, inplace=True)

                # df_prodAn['ProductionByTechnologyAnnual'] = df_prodAn['OutputActivityRatio']*df_prodAn['YearSplit']*df_prodAn['RateOfActivity']
                # df_prodAn = df_prodAn.drop(['OutputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                # df_prodAn = df_prodAn.groupby(['r','t','f','y'])['ProductionByTechnologyAnnual'].sum().reset_index()
                # df_prodAn['ProductionByTechnologyAnnual'] = df_prodAn['ProductionByTechnologyAnnual'].astype(float).round(4)
                # df_prodAn = df_prodAn.sort_values(by=['r','t','f','y'])
                # df_prodAn.to_csv(os.path.join(base_folder, 'csv', 'ProductionByTechnologyAnnual.csv'), index=None)


  

                ######################################UseByTechnologyAnnual##############################################

                df_use = pd.merge(df_in_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_use.r.unique()) if str(x) != 'nan']
                df_use['r'] = str(region[0])
                df_use['RateOfActivity'].fillna(0, inplace=True)

                
                df_use['UseByTechnology'] = df_use['InputActivityRatio']*df_use['YearSplit']*df_use['RateOfActivity']
                #df_use = df_use.drop(['InputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_use['UseByTechnology'] = df_use['UseByTechnology'].astype(float).round(4)
                df_use = df_use.sort_values(by=['r','l','t','f','y'])
                df_use.to_csv(os.path.join(base_folder, 'csv', 'UseByTechnology.csv'), index=None)

                # df_use['UseByTechnologyAnnual'] = df_use['InputActivityRatio']*df_use['YearSplit']*df_use['RateOfActivity']
                # df_use = df_use.drop(['InputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                # df_use = df_use.groupby(['r','t','f','y'])['UseByTechnologyAnnual'].sum().reset_index()
                # df_use['UseByTechnologyAnnual'] = df_use['UseByTechnologyAnnual'].astype(float).round(4)
                # df_use = df_use.sort_values(by=['r','t','f','y'])
                # df_use.to_csv(os.path.join(base_folder, 'csv', 'UseByTechnologyAnnual.csv'), index=None)

        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    def preprocessData_BKP(self, data_infile, data_outfile):

        lines = []

        with open(data_infile, 'r') as f1:
            for line in f1:
                if not line.startswith(('set MODEper','set MODEx', 'end;')):
                    lines.append(line)

        with open(data_outfile, 'w') as f2:
            f2.writelines(lines)

        parsing = False
        parsing_year = False
        parsing_tech = False
        parsing_fuel = False
        parsing_mode = False
        parsing_storage = False
        parsing_emission = False

        otoole = False

        year_list = []
        fuel_list = []
        tech_list = []
        storage_list = []
        mode_list = []
        emission_list = []

        data_all = []
        data_out = []
        data_inp = []
        output_table = []
        storage_to = []
        storage_from = []
        emission_table = []

        params_to_check = ['OutputActivityRatio', 
                        'InputActivityRatio', 
                        'TechnologyToStorage', 
                        'TechnologyFromStorage', 
                        'EmissionActivityRatio']

        with open(data_infile, 'r') as f:
            for line in f:
                line = line.rstrip().replace('\t', ' ')
                if line.startswith('# Model file written by *otoole*'):
                    otoole = True
                if parsing_year:
                    year_list += [line.strip()] if line.strip() not in ['', ';'] else []
                if parsing_fuel:
                    fuel_list += [line.strip()] if line.strip() not in ['', ';'] else []
                if parsing_tech:
                    tech_list += [line.strip()] if line.strip() not in ['', ';'] else []
                if parsing_storage:
                    storage_list += [line.strip()] if line.strip() not in ['', ';'] else []
                if parsing_mode:
                    mode_list += [line.strip()] if line.strip() not in ['', ';'] else []
                if parsing_emission:
                    emission_list += [line.strip()] if line.strip() not in ['', ';'] else []

                if line.startswith('set YEAR'):
                    if len(line.split('=')[1]) > 1:
                        year_list = line.split(' ')[3:-1]
                    else:
                        parsing_year = True
                if line.startswith('set COMMODITY'):  # Extracts list of COMMODITIES from data file. Some models use FUEL instead.
                    if len(line.split('=')[1]) > 1:
                        fuel_list = line.split(' ')[3:-1]
                    else:
                        parsing_fuel = True
                if line.startswith('set FUEL'):  # Extracts list of FUELS from data file. Some models use COMMODITIES instead.
                    if len(line.split('=')[1]) > 1:
                        fuel_list = line.split(' ')[3:-1]
                    else:
                        parsing_fuel = True
                if line.startswith('set TECHNOLOGY'):
                    if len(line.split('=')[1]) > 1:
                        tech_list = line.split(' ')[3:-1]
                    else:
                        parsing_tech = True
                if line.startswith('set STORAGE'):
                    if len(line.split('=')[1]) > 1:
                        storage_list = line.split(' ')[3:-1]
                    else:
                        parsing_storage = True
                if line.startswith('set MODE_OF_OPERATION'):
                    if len(line.split('=')[1]) > 1:
                        mode_list = line.split(' ')[3:-1]
                    else:
                        parsing_mode = True
                if line.startswith('set EMISSION'):
                    if len(line.split('=')[1]) > 1:
                        emission_list = line.split(' ')[3:-1]
                    else:
                        parsing_emission = True

                if line.startswith(";"):
                    parsing_year = False
                    parsing_tech = False
                    parsing_fuel = False
                    parsing_mode = False
                    parsing_storage = False
                    parsing_emission = False

        start_year = year_list[0]

        if not otoole:
            with open(data_infile, 'r') as f:
                for line in f:
                    line = line.rstrip().replace('\t', ' ')
                    if line.startswith(";"):
                        parsing = False

                    if parsing:
                        if line.startswith('['):
                            fuel = line.split(',')[2]
                            tech = line.split(',')[1]
                        elif line.startswith(start_year):
                            years = line.rstrip(':= ;\n').split(' ')[0:]
                            years = [i.strip(':=') for i in years]
                        else:
                            values = line.rstrip().split(' ')[1:]
                            mode = line.split(' ')[0]

                            if param_current =='OutputActivityRatio':
                                data_out.append(tuple([fuel, tech, mode]))
                                data_all.append(tuple([tech, mode]))
                                for i in range(0,len(years)):
                                    output_table.append(tuple([tech, fuel, mode, years[i], values[i]]))

                            if param_current =='InputActivityRatio':
                                data_inp.append(tuple([fuel, tech, mode]))
                                data_all.append(tuple([tech, mode]))

                            if param_current == 'TechnologyToStorage' or param_current == 'TechnologyFromStorage':
                                if not line.startswith(mode_list[0]):
                                    storage = line.split(' ')[0]
                                    values = line.rstrip().split(' ')[1:]
                                    for i in range(0, len(mode_list)):
                                        if values[i] != '0':
                                            if param_current == 'TechnologyToStorage':
                                                storage_to.append(tuple([storage, tech, mode_list[i]]))
                                                data_all.append(tuple([tech, mode_list[i]]))
                                            if param_current == 'TechnologyFromStorage':
                                                storage_from.append(tuple([storage, tech, mode_list[i]]))
                                                data_all.append(tuple([tech, mode_list[i]]))

                    if line.startswith(('param OutputActivityRatio',
                                        'param InputActivityRatio',
                                        'param TechnologyToStorage',
                                        'param TechnologyFromStorage')):
                        param_current = line.split(' ')[1]
                        parsing = True

        if otoole:
            with open(data_infile, 'r') as f:
                for line in f:
                    details = line.split(' ')
                    if line.startswith(";"):
                        parsing = False
                    if parsing:
                        if len(details) > 1:
                            if param_current == 'OutputActivityRatio':
                                tech = details[1].strip()
                                fuel = details[2].strip()
                                mode = details[3].strip()
                                year = details[4].strip()
                                value = details[5].strip()

                                if float(value) != 0.0:
                                    data_out.append(tuple([fuel, tech, mode]))
                                    output_table.append(tuple([tech, fuel, mode, year, value]))
                                    data_all.append(tuple([tech, mode]))

                            if param_current == 'InputActivityRatio':
                                tech = details[1].strip()
                                fuel = details[2].strip()
                                mode = details[3].strip()
                                value = details[5].strip()
                                if float(value) != 0.0:
                                    data_inp.append(tuple([fuel, tech, mode]))
                                    data_all.append(tuple([tech, mode]))

                            if param_current == 'TechnologyToStorage':
                                tech = details[1].strip()
                                storage = details[2].strip()
                                mode = details[3].strip()
                                value = details[4].strip()
                                if float(value) > 0.0:
                                    storage_to.append(tuple([storage, tech, mode]))
                                    data_all.append(tuple([storage, mode]))

                            if param_current == 'TechnologyFromStorage':
                                tech = details[1].strip()
                                storage = details[2].strip()
                                mode = details[3].strip()
                                value = details[4].strip()
                                if float(value) > 0.0:
                                    storage_from.append(tuple([storage, tech, mode]))
                                    data_all.append(tuple([storage, mode]))

                            if param_current == 'EmissionActivityRatio':
                                tech = details[1].strip()
                                emission = details[2].strip()
                                mode = details[3].strip()
                                value = details[5].strip()
                                if float(value) != 0.0:
                                    emission_table.append(tuple([emission, tech, mode]))
                                    data_all.append(tuple([tech, mode]))

                    if any(param in line for param in params_to_check):
                        param_current = details[-2]
                        parsing = True

        data_out = list(set(data_out))
        data_inp = list(set(data_inp))
        data_all = list(set(data_all))
        storage_to = list(set(storage_to))
        storage_from = list(set(storage_from))
        emission_table = list(set(emission_table))

        dict_out = defaultdict(list)
        dict_inp = defaultdict(list)
        dict_all = defaultdict(list)
        dict_stt = defaultdict(list)
        dict_stf = defaultdict(list)

        for fuel, tech, mode in data_out:
            dict_out[fuel].append((mode, tech))

        for fuel, tech, mode in data_inp:
            dict_inp[fuel].append((mode, tech))

        for tech, mode in data_all:
            if mode not in dict_all[tech]:
                dict_all[tech].append(mode)

        for storage, tech, mode in storage_to:
            dict_stt[storage].append((mode, tech))

        for storage, tech, mode in storage_from:
            dict_stf[storage].append((mode, tech))

        def file_output_function(if_dict, str_dict, set_list, set_name, extra_char):
            for each in set_list:
                if each in if_dict.keys():
                    line = set_name + str(each) + ']:=' + str(str_dict[each]) + extra_char
                    if set_list == tech_list:
                        line = line.replace(',', '').replace(':=[', ':= ').replace(']*', '').replace("'", "")
                    else:
                        line = line.replace('),', ')').replace('[(', ' (').replace(')]', ')').replace("'", "")
                else:
                    line = set_name + str(each) + ']:='
                file_out.write(line + ';' + '\n')

        # Append lines at the end of the data file
        with open(data_outfile, 'w') as file_out:  # 'a' to open in 'append' mode

            file_out.writelines(lines)

            file_output_function(dict_out, dict_out, fuel_list, 'set MODExTECHNOLOGYperFUELout[', '')
            file_output_function(dict_inp, dict_inp, fuel_list, 'set MODExTECHNOLOGYperFUELin[', '')
            file_output_function(dict_all, dict_all, tech_list, 'set MODEperTECHNOLOGY[', '*')

            if '' not in storage_list:
                file_output_function(dict_stt, dict_stt, storage_list, 'set MODExTECHNOLOGYperSTORAGEto[', '')
                file_output_function(dict_stf, dict_stf, storage_list, 'set MODExTECHNOLOGYperSTORAGEfrom[', '')

            file_out.write('end;')

    def generateCSVfromCBC_BKP(self, data_file, results_file, base_folder=os.getcwd()):
        try:
            pd.set_option('mode.chained_assignment', None)

            lines = []

            parsing = False

            data_all = []
            data_out = []
            data_inp = []
            output_table = []
            input_table = []
            storage_to = []
            storage_from = []
            emi_table = []

            with open(data_file, 'r') as f:
                for line in f:
                    if line.startswith('set YEAR'):
                        start_year = line.split(' ')[3]
                        year_list = line.split(' ')[3:-1]
                        #print(year_list)
                    if line.startswith('set COMMODITY'): # Extracts list of COMMODITIES from data file. Some models use FUEL instead.
                        fuel_list = line.split(' ')[3:-1]
                        #print(fuel_list)
                    if line.startswith('set FUEL'): # Extracts list of FUELS from data file. Some models use COMMODITIES instead.
                        fuel_list = line.split(' ')[3:-1]
                        #print(fuel_list)
                    if line.startswith('set TECHNOLOGY'):
                        tech_list = line.split(' ')[3:-1]
                        #print(tech_list)
                    if line.startswith('set STORAGE'):
                        storage_list = line.split(' ')[3:-1]
                        #print(storage_list)
                    if line.startswith('set MODE_OF_OPERATION'):
                        mode_list = line.split(' ')[3:-1]
                        #print(mode_list)
                    if line.startswith('set TIMESLICE'):
                        ts_list = line.split(' ')[3:-1]
                        #print(ts_list)
                    if line.startswith('set REGION'):
                        line = line.rstrip(' ;\n')
                        region_list = line.split(' ')[3:]
                        #print(region_list)
                    if line.startswith('set EMISSION'):
                        emission_list = line.split(' ')[3:-1]
                        #print(emission_list)

                    if line.startswith(";"):
                            parsing = False

                    if parsing:
                        if line.startswith('['):
                            fuel = line.split(',')[2]
                            tech = line.split(',')[1]
                        elif line.startswith(start_year):
                            years = line.rstrip(':= ;\n').split(' ')[0:]
                            years = [i.strip(':=') for i in years]
                        else:
                            values = line.rstrip().split(' ')[1:]
                            mode = line.split(' ')[0]

                            if param_current=='OutputActivityRatio':
                                #data_out.append(tuple([fuel,tech,mode]))
                                #data_all.append(tuple([tech,mode]))
                                for i in range(0,len(years)):
                                    output_table.append(tuple([tech,fuel,mode,years[i],values[i]]))

                            if param_current=='InputActivityRatio':
                                #data_inp.append(tuple([fuel,tech,mode]))
                                #data_all.append(tuple([tech,mode]))
                                for i in range(0,len(years)):
                                    input_table.append(tuple([tech,fuel,mode,years[i],values[i]]))

                            if param_current == 'TechnologyToStorage' or param_current == 'TechnologyFromStorage':
                                if not line.startswith(mode_list[0]):
                                    storage = line.split(' ')[0]
                                    values = line.rstrip().split(' ')[1:]
                                    for i in range(0,len(mode_list)):
                                        if values[i] != '0':
                                            if param_current == 'TechnologyToStorage':
                                                storage_to.append(tuple([storage,tech,mode_list[i]]))
                                                data_all.append(tuple([tech,mode_list[i]]))
                                            if param_current == 'TechnologyFromStorage':
                                                storage_from.append(tuple([storage,tech,mode_list[i]]))
                                                data_all.append(tuple([tech,mode_list[i]]))
                            
                            if param_current == 'EmissionActivityRatio':
                                for i in range(0,len(years)):
                                    emi_table.append(tuple([tech,fuel,mode,years[i],values[i]]))

                    if line.startswith(('param OutputActivityRatio','param InputActivityRatio','param TechnologyToStorage','param TechnologyFromStorage', 'param EmissionActivityRatio')):
                        param_current = line.split(' ')[1]
                        parsing = True

            try:
                os.makedirs(os.path.join(base_folder, 'csv'))
            except FileExistsError:
                pass

            #Read CBC output file
            
            cols = {'NewCapacity':['r','t','y'],
                    'AccumulatedNewCapacity':['r','t','y'],
                    'TotalCapacityAnnual':['r','t','y'],
                    'CapitalInvestment':['r','t','y'],
                    'AnnualVariableOperatingCost':['r','t','y'],
                    'AnnualFixedOperatingCost':['r','t','y'],
                    'SalvageValue':['r','t','y'],
                    'DiscountedSalvageValue':['r','t','y'],
                    'TotalTechnologyAnnualActivity':['r','t','y'],
                    'RateOfActivity':['r','l','t','m','y'],
                    'RateOfTotalActivity':['r','t','l','y'],
                    'Demand':['r','l','f','y'],
                    'TotalAnnualTechnologyActivityByMode':['r','t','m','y'],
                    'TotalTechnologyModelPeriodActivity':['r','t'],
                    'ProductionByTechnology':['r','l','t','f','y'],
                    'ProductionByTechnologyAnnual':['r','t','f','y'],
                    'AnnualTechnologyEmissionByMode':['r','t','e','m','y'],
                    'EmissionByActivityChange':['r','t','e','m','y'],
                    'AnnualTechnologyEmission':['r','t','e','y'],
                    'AnnualEmissions':['r','e','y'],
                    'DiscountedTechnologyEmissionsPenalty':['r','t','y'],
                    'RateOfProductionByTechnology':['r','l','t','f','y'],
                    'RateOfUseByTechnology':['r','l','t','f','y'],
                    'UseByTechnology':['r','l','t','f','y'],
                    'UseByTechnologyAnnual':['r','t','f','y'],
                    #'RateOfProductionByTechnologyByMode':['r','l','t','m','f','y'],
                    #'RateOfUseByTechnologyByMode':['r','l','t','m','f','y'],
                    'TechnologyActivityChangeByMode':['r','t','m','y'],
                    'TechnologyActivityChangeByModeCostTotal':['r','t','m','y'],
                    'InputToNewCapacity':['r','t','f','y'],
                    'InputToTotalCapacity':['r','t','f','y'],
                    'DiscountedCapitalInvestment':['r','t','y'],
                    'DiscountedOperatingCost':['r','t','y'],
                    'TotalDiscountedCostByTechnology':['r','t','y'],
                    'NewStorageCapacity':['r','s','y'],
                    'SalvageValueStorage':['r','s','y'],
                    'NumberOfNewTechnologyUnits':['r','t','y'],
                    'Trade':['r','rr','l','f','y']
                    }
            
            params = []
            
            df = pd.read_csv(results_file, sep='\t')

            df.columns = ['temp']
            df['temp'] = df['temp'].str.lstrip(' *\n\t')
            
            if len(df) > 0:
                df[['temp','value']] = df['temp'].str.split(')', expand=True)
                df = df.applymap(lambda x: x.strip() if isinstance(x,str) else x)
                #error when moved to ython 3.11, Columns must have smae length as key
                # df['value'] = df['value'].str.split(' ', expand=True)
                df['value'] = df['value'].str.split(' ', expand=True)[0]
                df[['parameter','id']] = df['temp'].str.split('(', expand=True)
                df['parameter'] = df['parameter'].str.split(' ', expand=True)[1]
                df = df.drop('temp', axis=1)
                df['value'] = df['value'].astype(float).round(4)

                params = df.parameter.unique()
                all_params = {}

                for each in params:
                    result_cols = []
                    df_p = df[df.parameter == each]
                    df_p[cols[each]] = df_p['id'].str.split(',',expand=True)
                    result_cols = cols[each].copy()
                    result_cols.append('value')
                    df_p = df_p[result_cols] # Reorder dataframe to include 'value' as last column
                    all_params[each] = pd.DataFrame(df_p) # Create a dataframe for each parameter
                    df_p = df_p.rename(columns={'value':each})
                    # df_p.to_csv(os.path.join(base_folder, 'csv', str(each) + '.csv'), index=None) # Print data for each parameter to a CSV file
            
            
            results_list = ['TotalTechnologyModelPeriodActivity',
                            'AnnualEmissions',
                            'NewStorageCapacity',
                            'SalvageValueStorage',
                            'AccumulatedNewCapacity',
                            'CapitalInvestment',
                            'AnnualFixedOperatingCost',
                            'AnnualVariableOperatingCost',
                            'DiscountedSalvageValue',
                            'DiscountedTechnologyEmissionsPenalty',
                            'NewCapacity',
                            'NumberOfNewTechnologyUnits',
                            'SalvageValue',
                            'TotalCapacityAnnual',
                            'TotalTechnologyAnnualActivity',
                            'TotalAnnualTechnologyActivityByMode',
                            'InputToNewCapacity',
                            'InputToTotalCapacity',
                            'ProductionByTechnologyAnnual',
                            'UseByTechnologyAnnual',
                            'AnnualTechnologyEmission',
                            'RateOfTotalActivity',
                            'Demand',
                            'Trade',
                            'AnnualTechnologyEmissionByMode',
                            'EmissionByActivityChange',
                            'ProductionByTechnology',
                            'RateOfProductionByTechnology',
                            'RateOfUseByTechnology',
                            'UseByTechnology',
                            'RateOfActivity'
                            #'RateOfProductionByTechnologyByMode',
                            #'RateOfUseByTechnologyByMode'
                            ]
            
            year_split = []
            parsing = False

            with open(data_file, 'r') as f:
                for line in f:
                    if line.startswith(";"):
                        parsing = False
                    if parsing:
                        if line.startswith(start_year):
                            years = line.rstrip().split(' ')[0:]
                            years = [i.strip(':=') for i in years]
                            years = list(filter(None, years))
                        elif not line.startswith(start_year):
                            time_slice = line.rstrip().split(' ')[0]
                            values = line.rstrip().split(' ')[1:]
                            for i in range(0,len(years)):
                                year_split.append(tuple([time_slice,years[i],values[i]]))
                    if line.startswith('param YearSplit'):
                        parsing = True

            df_yearsplit = pd.DataFrame(year_split, columns=['l','y','YearSplit'])
            if len(df) > 0:
                df_activity = all_params['RateOfActivity'].rename(columns={'value':'RateOfActivity'})
                df_activity_total = all_params['TotalAnnualTechnologyActivityByMode'].rename(columns={'value':'TotalAnnualTechnologyActivityByMode'})

            ####################################################################################

            df_output = pd.DataFrame(output_table, columns=['t','f','m','y','OutputActivityRatio'])
            df_out_ys = pd.merge(df_output, df_yearsplit, on='y')
            df_out_ys['OutputActivityRatio'] = df_out_ys['OutputActivityRatio'].astype(float)
            df_out_ys['YearSplit'] = df_out_ys['YearSplit'].astype(float)
            
            df_input = pd.DataFrame(input_table, columns=['t','f','m','y','InputActivityRatio'])
            df_in_ys = pd.merge(df_input, df_yearsplit, on='y')
            df_in_ys['InputActivityRatio'] = df_in_ys['InputActivityRatio'].astype(float)
            df_in_ys['YearSplit'] = df_in_ys['YearSplit'].astype(float)
            
            df_emi = pd.DataFrame(emi_table, columns=['t','e','m','y','EmissionActivityRatio'])
            df_emi['EmissionActivityRatio'] = df_emi['EmissionActivityRatio'].astype(float)
            #df_emi.to_csv(os.path.join(base_folder, 'emi_table.csv'), index=None)
            
            ##################################################################################
            
            index_dict = {'r': region_list,
                        'rr': region_list,
                        'l': ts_list,
                        't': tech_list,
                        'f': fuel_list,
                        'm': mode_list,
                        'e': emission_list,
                        'y': year_list,
                        's': storage_list}
            
            def sort_df(df):
                if 'y' in df.columns:
                    sorted_df = df.sort_values(by=['y'])
                else:
                    sorted_df = df.copy()
                return sorted_df
            
            def tuple_to_dict(data_table):
                
                tuple_list = [[col1, col2, col3, col4, col5] 
                            for (col1, col2, col3, col4, col5) 
                            in data_table]
                df = pd.DataFrame(tuple_list,
                                columns=['t','f','m','y','value']) 
                df = df[['t','f','m','y']].drop_duplicates()
                return df
            
            df_all = pd.concat([tuple_to_dict(input_table),
                                tuple_to_dict(output_table)])
            combo_cols = list(df_all.columns)    

            for each_result in results_list:
                iter_list = []
                df_combinations = pd.DataFrame()
                cols_in_df = []
                cols_notin_df = []
                if any(x in combo_cols for x in cols[each_result]):
                    cols_in_df = [v for v in cols[each_result]
                                if v in combo_cols]
                    cols_notin_df = [v for v in cols[each_result]
                                    if v not in combo_cols]
                    
                df_combinations = df_all[cols_in_df].drop_duplicates()
                                
                for each_index in cols_notin_df:
                    iter_list.append(index_dict[each_index])
                
                df_combinations_2 = pd.DataFrame(product(*iter_list),
                                                columns=cols_notin_df)
                
                df_combinations['key'] = 1
                df_combinations_2['key'] = 1
                #In a future version of pandas all arguments of DataFrame.drop except for the argument 'labels' will be keyword-only.
                df_combinations = pd.merge(df_combinations, df_combinations_2, on='key').drop('key', 1)
                
                #df_combinations = pd.DataFrame(product(*iter_list),
                #                                   columns=cols[each_result])
                if any(substring in each_result for substring in ['Production', 'Output']):
                    col_keep = []
                    for each_col in df_output.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)
                    df_output_result = df_output[col_keep]
                    df_output_result.drop_duplicates(inplace=True)
                    df_combinations = pd.merge(df_output_result,
                                            df_combinations,
                                            how='left',
                                            on=col_keep)
                    df_combinations.drop_duplicates(inplace=True)
                    
                if any(substring in each_result for substring in ['Use', 'Input']):
                    col_keep = []
                    for each_col in df_input.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)
                    df_input_result = df_input[col_keep]
                    df_input_result.drop_duplicates(inplace=True)
                    df_combinations = pd.merge(df_input_result,
                                            df_combinations,
                                            how='left',
                                            on=col_keep)
                    df_combinations.drop_duplicates(inplace=True)
                
                if 'Activity' in each_result:
                    col_keep = []
                    for each_col in df_input.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)
                    
                    if len(df) > 0:
                        df_input_output = pd.concat([df_input,
                                                    df_output],
                                                    sort=True)
                        df_input_output = df_input_output[col_keep]
                        df_input_output.drop_duplicates(inplace=True)
                        df_combinations = pd.merge(df_input_output,
                                                df_combinations,
                                                how='left',
                                                on=col_keep)
                        df_combinations.drop_duplicates(inplace=True)
                    
                if 'e' in cols[each_result]:
                    col_keep = []
                    for each_col in df_emi.columns:
                        if each_col in df_combinations:
                            col_keep.append(each_col)
                    
                    df_emi_result = df_emi[col_keep]
                    df_emi_result.drop_duplicates(inplace=True)
                    df_combinations = pd.merge(df_emi_result,
                                            df_combinations,
                                            how='left',
                                            on=col_keep)
                    df_combinations.drop_duplicates(inplace=True)
                
                # If result parameter in CBC results file, merge results from all_params.
                # Else, enter '0' for all rows.
                
                if each_result in params:
                    df_combinations = pd.merge(df_combinations,
                                            all_params[each_result],
                                            how='left',
                                            on=cols[each_result])
                    df_combinations.rename(columns={'value':each_result},
                                        inplace=True)
                    df_combinations.fillna(0,
                                        inplace=True)
                
                else:
                    df_combinations[each_result] = 0
                
                # For final dataframes, reorder columns based on original cols dictionary 
                
                df_combinations = df_combinations.sort_values(by=cols[each_result])
                
                final_cols = []
                final_cols = cols[each_result].copy()
                final_cols.append(each_result)
                df_combinations = df_combinations[final_cols]
                
                
                df_combinations.to_csv(os.path.join(base_folder, 'csv', each_result+'.csv'), index=None)
                
            ####################################################################################
            
            if len(df) > 0:
                #df_prod = pd.merge(df_out_ys, df_activity, on=['t','m','l','y'])
                df_prod = pd.merge(df_out_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_prod.r.unique()) if str(x) != 'nan']
                df_prod['r'] = str(region[0])
                df_prod['RateOfActivity'].fillna(0, inplace=True)
                #df_prod.to_csv(os.path.join(base_folder, 'output_table.csv'), index=None)
                
                df_prod['ProductionByTechnologyAnnual'] = df_prod['OutputActivityRatio']*df_prod['YearSplit']*df_prod['RateOfActivity']
                df_prod = df_prod.drop(['OutputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_prod = df_prod.groupby(['r','t','f','y'])['ProductionByTechnologyAnnual'].sum().reset_index()
                df_prod['ProductionByTechnologyAnnual'] = df_prod['ProductionByTechnologyAnnual'].astype(float).round(4)
                df_prod = df_prod.sort_values(by=['r','t','f','y'])
                df_prod.to_csv(os.path.join(base_folder, 'csv', 'ProductionByTechnologyAnnual.csv'), index=None)
                all_params['ProductionByTechnologyAnnual'] = df_prod.rename(columns={'ProductionByTechnologyAnnual':'value'})

                ####################################################################################

                #df_use = pd.merge(df_in_ys, df_activity, on=['t','m','l','y'])
                df_use = pd.merge(df_in_ys, df_activity, how='left', on=['t','m','l','y'])
                region = [x for x in list(df_use.r.unique()) if str(x) != 'nan']
                df_use['r'] = str(region[0])
                df_use['RateOfActivity'].fillna(0, inplace=True)
                #df_use.to_csv(os.path.join(base_folder, 'input_table.csv'), index=None)

                df_use['UseByTechnologyAnnual'] = df_use['InputActivityRatio']*df_use['YearSplit']*df_use['RateOfActivity']
                df_use = df_use.drop(['InputActivityRatio','YearSplit','RateOfActivity'], axis=1)
                df_use = df_use.groupby(['r','t','f','y'])['UseByTechnologyAnnual'].sum().reset_index()
                df_use['UseByTechnologyAnnual'] = df_use['UseByTechnologyAnnual'].astype(float).round(4)
                df_use = df_use.sort_values(by=['r','t','f','y'])
                df_use.to_csv(os.path.join(base_folder, 'csv', 'UseByTechnologyAnnual.csv'), index=None)
                all_params['UseByTechnologyAnnual'] = df_use.rename(columns={'UseByTechnologyAnnual':'value'})

                ###################################################################################
                
                df_emi = pd.merge(df_emi, df_activity_total, how='left', on=['t','m','y'])
                region = [x for x in list(df_prod.r.unique()) if str(x) != 'nan']
                df_emi['r'] = str(region[0])
                df_emi['TotalAnnualTechnologyActivityByMode'].fillna(0, inplace=True)

                #04042023 Annual Emisssions not sumed by technologies v.k.
                # df_emi['AnnualEmissions'] = df_emi['EmissionActivityRatio']*df_emi['TotalAnnualTechnologyActivityByMode']
                # df_emi = df_emi.drop(['EmissionActivityRatio','TotalAnnualTechnologyActivityByMode'], axis=1)
                # df_emi = df_emi.groupby(['r','t','e','y'])['AnnualEmissions'].sum().reset_index()
                # df_emi['AnnualEmissions'] = df_emi['AnnualEmissions'].astype(float).round(4)
                # df_emi = df_emi.sort_values(by=['r','t','e','y'])
                # df_emi.to_csv(os.path.join(base_folder, 'csv', 'AnnualEmissions.csv'), index=None)
                # all_params['AnnualEmissions'] = df_emi.rename(columns={'AnnualEmissions':'value'})

                ## 26052023 This variable is calculated in solver, added equation in model file for AnnuallEmisssions V.K.
                # df_emi['AnnualEmissions'] = df_emi['EmissionActivityRatio']*df_emi['TotalAnnualTechnologyActivityByMode']
                # df_emi = df_emi.drop(['EmissionActivityRatio','TotalAnnualTechnologyActivityByMode'], axis=1)
                # df_emi = df_emi.groupby(['r','e','y'])['AnnualEmissions'].sum().reset_index()
                # df_emi['AnnualEmissions'] = df_emi['AnnualEmissions'].astype(float).round(4)
                # df_emi = df_emi.sort_values(by=['r','e','y'])
                # df_emi.to_csv(os.path.join(base_folder, 'csv', 'AnnualEmissions.csv'), index=None)
                # all_params['AnnualEmissions'] = df_emi.rename(columns={'AnnualEmissions':'value'})
        except(IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError
    