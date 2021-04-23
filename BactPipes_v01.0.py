#!/usr/bin/python3.7
#Bioinformatics Pipeline
from addScripts import BactStart as BS
from addScripts import BactFunctions as BF
import os, shutil #Necessary for directory checks and file movements
import time #To breakup processes and make output readable
import sys #Allows exiting of code in case of irreconcilable error
import argparse #Allows use of command line style argument call
import subprocess #For execution of outside scripts
import multiprocessing as mp #Run run multiple processes at once
import pandas as pd

#Prevents writing of .pyc files when running
sys.dont_write_bytecode = True

#Parser from argparse for command line refinement
parserPS = argparse.ArgumentParser()
parserPS.add_argument("name", help="Name of project. Must be non-existant directory if running first half of pipeline. If just running the second half, must use project directory created by / in same format as Pipeline.")
parserPS.add_argument("processors", help="Number of processors to utilize for this job.", type=int)
parserPS.add_argument("-B","--beginning", nargs="?", help="Optional argument to run first half of pipeline. Must provide directory with FASTA files for processing.")
parserPS.add_argument("-S","--scoary", nargs='?', help="Optional argument to add a CSV for Scoary processing. Scoary, and second portion of pipeline, will not run without this, and columns must match boundmatrix.csv that is generated.")
parserPS.add_argument("-p", action='store_false', help="Optional flag to skip Prokka. If running Orthofinder, Prokka files must be present. Only applies to first half of pipeline.")
parserPS.add_argument("-o", action='store_false', help="Optional flag to skip Orthofinder. Only applies to first half of pipeline.")
parserPS.add_argument("-r", action='store_false', help="Optional flag to skip RVDMIner. If running DisTAL, RVDMiner files must be present. Only applies to first half of pipeline.")
parserPS.add_argument("-d", action='store_false', help="Optional flag to skip DisTAL. Only applies to first half of pipeline.")
parserPS.add_argument("-k", action='store_false', help="Optional flag to skip kSNP3. Only applies to first half of pipeline.")
parserPS.add_argument("-t", action='store_false', help="Optional flag to skip TandemRepeatsFinder. Only applies to first half of pipeline.")
parserPS.add_argument("-c", action='store_false', help="Skip creation of project directory, select if you are running select portions of the first half. Only applies to first half of pipeline.")
parserPS.add_argument("-i", action='store_true', help="Optional flag to run ISEScan")
args = parserPS.parse_args()

#Main section / execution of code
if __name__== '__main__':

    # Get path to folder with Biopipeline
    truePath = '/'.join(os.path.abspath(__file__).split('/')[0:-1]) + '/'

    #Assignment of pipe scope variables
    pipeStart = False
    pipeScoary = False
    if args.scoary is not None:
        pipeScoary = True
    if args.beginning is not None:
        pipeStart = True

    #Processor variable, halves if greater than 10 per project guidelines by Alvaro
    if int(args.processors) <= 10:
        CPUs = args.processors
    else:
        CPUs = (int(args.processors)//2)
    CPUs = str(CPUs)

    #If neither pipeStart or pipeScoary is initiated with True, pipeline won't run
    if pipeStart is False and pipeScoary is False:
        print("Neither start or end of pipe initialized. Exiting...")
        sys.exit()

    #Assignment of pipePath and FASTAlist, dependent on mode being run
    if pipeStart is True and args.c:
        if args.beginning is None:
            print("Must provide a directory with FASTA files when running initial section of pipeline.\nExiting...")
            sys.exit()
        pipePath, fastaPath = BS.pipeStart(args.name, args.beginning)
    else:
        pipePath, FASTAlist = BS.pipeDetour(args.name)

    #Initiate path variables and file location variables (created after start of main section)
    FASTAfiles = pipePath + "FASTAfiles/"
    TRFfiles = pipePath + "TRFfiles/"
    PROKKAfiles = pipePath + "PROKKAfiles/"
    ORTHOfiles = pipePath + "ORTHOfiles/"
    RVDfiles = pipePath + "RVDfiles/"
    DISTALfiles = pipePath + "DISTALfiles/"
    Rfiles = pipePath + "Rfiles/"
    KSNP3files = pipePath + "KSNP3files/"
    SCOARYfiles = pipePath + "SCOARYfiles/"
    BAYESfiles = pipePath + "BAYESfiles/"
    RESULTSfiles = pipePath + "Results/"
    LOGfiles = pipePath + "Logging/"
    providedCSV = args.scoary

    def tandemRepeatFinder(tanFile):
        subprocess.Popen(["TandemRepeatsFinder", FASTAfiles + tanFile, "2", "7", "7", "80", "10", "50", "500", "-f", "-h"], close_fds=True).communicate()[0]

    #Gather FASTA files, copy to project folder for further use
    if pipeStart is True:
        if args.c:
            FASTAlist = BS.collectFasta(fastaPath, FASTAfiles)


        if args.t:
            #Call to TandemRepeatsFinder, done individually to allow processing of large batches of Files
            workerPool = mp.Pool(processes=int(CPUs),)
            workerPool.map(tandemRepeatFinder, FASTAlist)
            workerPool.close()
            workerPool.join()

            #Parsing of TRF files
            BF.trfParse(TRFfiles, FASTAlist)

        #Establish first set of processes for the pipeline and pass their relevant parameters
        if args.p or args.o:
            prokkaProcess = mp.Process(target = BF.prokka, args =(FASTAlist, FASTAfiles, PROKKAfiles, ORTHOfiles, CPUs, args.p, args.o,))
        if args.r or args.d:
            RVDProcess = mp.Process(target = BF.RVDminer, args = (FASTAlist, FASTAfiles, RVDfiles, DISTALfiles, args.r, args.d,))
        if args.k:
            KSNP3Process = mp.Process(target = BF.ksnpCall, args = (FASTAfiles, KSNP3files, FASTAlist, CPUs,))
        if args.i:
            ISESProcess = mp.Process(target = BF.ISESCall, args = (FASTAfiles, RESULTSfiles, CPUs,))

        #Start processes
        if args.p or args.o:
            prokkaProcess.start()
        if args.r or args.d:
            RVDProcess.start()
        if args.k:
            KSNP3Process.start()
        if args.i:
            ISESProcess.start()

        #Rejoin processes with main thread, won't continue till each finishes
        if args.p or args.o:
            prokkaProcess.join()
        if args.r or args.d:
            RVDProcess.join()
        if args.k:
            KSNP3Process.join()
        if args.i:
            ISESProcess.join()

        #Creation of faaConcatenated and rvdNucs files for end Results
        BF.concatFaa(PROKKAfiles + "FAAs/", RESULTSfiles)
        BF.concatNuc(RVDfiles, RESULTSfiles)

    #Second section of pipeline, requires secondHalf to be True
    if pipeScoary is True:

        #Call R script for further parsing of data
        subprocess.Popen(["Rscript", truePath + "addScripts/BactROne.R", pipePath], close_fds=True).communicate()[0]
        BF.csvFix(Rfiles, FASTAlist)
        subprocess.Popen(["Rscript", truePath + "addScripts/BactRTwo.R", pipePath], close_fds=True).communicate()[0]

        #Call Scoary if it is supplied the necessary CSV, compares rows of CSV with colums of boundMatrix.csv first
        if providedCSV is not None:
            scorFile = BF.scoary(pipePath, providedCSV)
            boundFile = (pipePath + "Rfiles/boundMatrix.csv")
            if scorFile is not None and os.path.exists(boundFile):
               subprocess.Popen(["scoary", "-t", scorFile, "-g", boundFile, "-s", "2", "-o", pipePath + "SCOARYfiles/"], close_fds=True).communicate()[0]
               BF.scoaryParse(SCOARYfiles, Rfiles, DISTALfiles, TRFfiles, ORTHOfiles, RESULTSfiles, LOGfiles)
               subprocess.Popen(["Rscript", truePath + "addScripts/BactRFour.R", pipePath], close_fds=True).communicate()[0]

            #Call BayesTraitsV3 on prior results of pipeline
            BF.bayesPool(pipePath)
            BF.bayesParse(Rfiles, DISTALfiles, TRFfiles, ORTHOfiles, RESULTSfiles, LOGfiles)
