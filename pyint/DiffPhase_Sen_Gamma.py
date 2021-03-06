#! /usr/bin/env python
#'''
###################################################################################
#                                                                                 #
#            Author:   Yun-Meng Cao                                               #
#            Email :   ymcmrs@gmail.com                                           #
#            Date  :   FMarch, 2017                                               #
#                                                                                 #
#         Generating differential interferograms for sentinel-1A/B                #
#                                                                                 #
###################################################################################
#'''
import numpy as np
import os
import sys  
import subprocess
import getopt
import time
import glob

def check_variable_name(path):
    s=path.split("/")[0]
    if len(s)>0 and s[0]=="$":
        p0=os.getenv(s[1:])
        path=path.replace(path.split("/")[0],p0)
    return path

def read_template(File, delimiter='='):
    '''Reads the template file into a python dictionary structure.
    Input : string, full path to the template file
    Output: dictionary, pysar template content
    Example:
        tmpl = read_template(KyushuT424F610_640AlosA.template)
        tmpl = read_template(R1_54014_ST5_L0_F898.000.pi, ':')
    '''
    template_dict = {}
    for line in open(File):
        line = line.strip()
        c = [i.strip() for i in line.split(delimiter, 1)]  #split on the 1st occurrence of delimiter
        if len(c) < 2 or line.startswith('%') or line.startswith('#'):
            next #ignore commented lines or those without variables
        else:
            atrName  = c[0]
            atrValue = str.replace(c[1],'\n','').split("#")[0].strip()
            atrValue = check_variable_name(atrValue)
            template_dict[atrName] = atrValue
    return template_dict

def ras2jpg(input, strTitle):
    call_str = "convert " + input + ".ras " + input + ".jpg"
    os.system(call_str)
    call_str = "convert " + input + ".jpg -resize 250 " + input + ".thumb.jpg"
    os.system(call_str)
    call_str = "convert " + input + ".jpg -resize 500 " + input + ".bthumb.jpg"
    os.system(call_str)
    call_str = "$INT_SCR/addtitle2jpg.pl " + input + ".thumb.jpg 14 " + strTitle
    os.system(call_str)
    call_str = "$INT_SCR/addtitle2jpg.pl " + input + ".bthumb.jpg 24 " + strTitle
    os.system(call_str)

def UseGamma(inFile, task, keyword):
    if task == "read":
        f = open(inFile, "r")
        while 1:
            line = f.readline()
            if not line: break
            if line.count(keyword) == 1:
                strtemp = line.split(":")
                value = strtemp[1].strip()
                return value
        print "Keyword " + keyword + " doesn't exist in " + inFile
        f.close()
        
def geocode(inFile, outFile, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM):
    if inFile.rsplit('.')[1] == 'int':
        call_str = '$GAMMA_BIN/geocode_back ' + inFile + ' ' + nWidth + ' ' + UTMTORDC + ' ' + outFile + ' ' + nWidthUTMDEM + ' ' + nLineUTMDEM + ' 0 1'
    else:
        call_str = '$GAMMA_BIN/geocode_back ' + inFile + ' ' + nWidth + ' ' + UTMTORDC + ' ' + outFile + ' ' + nWidthUTMDEM + ' ' + nLineUTMDEM + ' 0 0'
    os.system(call_str)
    
def createBlankFile(strFile):
    f = open(strFile,'w')
    for i in range (10):
        f.write('\n')
    f.close()    
    
       

def usage():
    print '''
******************************************************************************************************
 
              Generating the differential interferograms for Sentinel-1A/B

   usage:
   
            DiffPhase_Sen_Gamma.py igramDir
      
      e.g.  DiffPhase_Sen_Gamma.py IFG_PacayaT163S1A_131021-131101_0011_-0007
      e.g.  DiffPhase_Sen_Gamma.py MAI_PacayaT163S1A_131021-131101_0011_-0007          
      e.g.  DiffPhase_Sen_Gamma.py RSI_PacayaT163S1A_131021-131101_0011_-0007            
*******************************************************************************************************
    '''   
    
def main(argv):
    
    if len(sys.argv)==2:
        if argv[0] in ['-h','--help']: usage(); sys.exit(1)
        else: igramDir=sys.argv[1]        
    else:
        usage();sys.exit(1)
       
    INF = igramDir.split('_')[0]
    projectName = igramDir.split('_')[1]
    IFGPair = igramDir.split(projectName+'_')[1].split('_')[0]
    Mdate = IFGPair.split('-')[0]
    Sdate = IFGPair.split('-')[1]
    
    scratchDir = os.getenv('SCRATCHDIR')
    templateDir = os.getenv('TEMPLATEDIR')
    templateFile = templateDir + "/" + projectName + ".template"
    
    processDir = scratchDir + '/' + projectName + "/PROCESS"
    slcDir     = scratchDir + '/' + projectName + "/SLC"
    rslcDir     = scratchDir + '/' + projectName + "/RSLC"
    workDir    = processDir + '/' + igramDir   
    
    templateContents=read_template(templateFile)
    rlks = templateContents['Range_Looks']
    azlks = templateContents['Azimuth_Looks']

    
    if not os.path.isdir(processDir):
        call_str = 'mkdir ' + processDir
        os.system(call_str)
    
    simDir = scratchDir + '/' + projectName + "/PROCESS" + "/DEM" 
    #if not os.path.isdir(simDir):
    #    call_str='mkdir ' + simDir  
    #    os.system(call_str)
        
    #simDir = simDir + '/sim_' + Mdate + '-' + Sdate
    #if not os.path.isdir(simDir):
     #   call_str='mkdir ' + simDir  
     #   os.system(call_str)
    

        
    if 'Start_Swath' in templateContents: SW = templateContents['Start_Swath']
    else: SW = '1'    
    if 'End_Swath' in templateContents: EW = templateContents['End_Swath']
    else: EW = '3' 

#  Definition of file
    MslcDir     = rslcDir  + '/' + Mdate
    SslcDir     = rslcDir  + '/' + Sdate

    
    SLC1_INF_tab = MslcDir + '/' + Mdate + '_SLC_Tab'
    SLC2_INF_tab = SslcDir + '/' + Sdate + '_SLC_Tab'

    HGTSIM      = simDir + '/sim_' + Mdate + '_' + rlks + 'rlks.rdc.dem'
    if not os.path.isfile(HGTSIM):
        call_str = 'CreateRdcDem_Sen_Gamma.py ' + igramDir
        os.system(call_str)
    
    RSLC_tab = workDir + '/' + Sdate + '_RSLC_tab'
    if os.path.isfile(RSLC_tab):
        os.remove(RSLC_tab)
    
    BURST = SslcDir + '/' + Sdate + '_Burst_Tab'
    AA = np.loadtxt(BURST)
    if EW==SW:
        AA = AA.reshape([1,2])
    
    for kk in range(int(EW)-int(SW)+1):
        ii = int(int(kk) + 1)
        SB2=AA[ii-1,0]
        EB2=AA[ii-1,1]
        call_str = 'echo ' + workDir + '/'+ Sdate+ '_'+ str(int(SB2)) + str(int(EB2)) +'.IW'+str(int(SW)+kk)+ '.rslc' + ' ' + workDir + '/' + Sdate + '_'+ str(int(SB2)) + str(int(EB2)) +'.IW'+ str(int(SW)+kk)+ '.rslc.par' + ' ' + workDir + '/'+ Sdate+'_'+ str(int(SB2)) + str(int(EB2)) + '.IW'+str(int(SW)+kk)+ '.rslc.TOPS_par >>' + RSLC_tab
        os.system(call_str)
    
    
    os.chdir(workDir)
    call_str = 'S1_coreg_TOPS ' + SLC1_INF_tab + ' ' + Mdate + ' ' + SLC2_INF_tab + ' ' + Sdate + ' ' + RSLC_tab + ' ' + HGTSIM + ' ' + rlks + ' ' + azlks + ' - - 0.6 0.01 1.2 1'
    os.system(call_str)


    print "Generating differential S1 interferogram is done !!"
    sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[:])
