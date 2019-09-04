#!/usr/bin/env python3
import subprocess
import sys
import shutil
import os
import re
import pandas as pd


sys.dont_write_bytecode = True


#Function for use of KSNP3, appropriate parsing, and movement of files
def ksnpCall(faPath, ksnpPath, ksnpList, ksnpCpus):
    ksnpGenomes = ksnpPath + "ksnpGenomes.txt"
    with open(ksnpGenomes, "w") as outFile:
        for file in ksnpList:
            prefixKSNP = file.split(".")
            outFile.write(os.path.abspath(faPath + file) + "\t" + prefixKSNP[0] + "\n")
    subprocess.Popen(["MakeFasta", ksnpGenomes, ksnpPath + "ForKchoser"], close_fds=True).communicate()[0]
    subprocess.Popen(["Kchooser", ksnpPath + "ForKchoser"], close_fds=True).communicate()[0]
    shutil.move("Kchooser.report", ksnpPath + "Kchooser.report")
    with open(ksnpPath + "Kchooser.report", "r") as kOut:
        content = kOut.readlines()
        for line in content:
            if re.match(r'The optimum value of K is (.*)\.', line):
                tempInt = re.findall(r'The optimum value of K is (.*)\.', line)
                ksnpInt = tempInt[0]
                subprocess.Popen(["kSNP3", "-in", ksnpGenomes, "-k", str(ksnpInt), "-outdir", ksnpPath + "kSNP3_results", "-ML", "-CPU", str(ksnpCpus)], close_fds=True).communicate()[0]
                shutil.move("fasta_list", ksnpPath + "fasta_list")
            else:
                print("Unable to find optimum value of K")


#Function for routing needed data to R for parsing of various data sets
def ksnpParse(SCOARYfiles, Rfiles, scorFile, DISTALfiles, TRFfiles, ORTHOfiles, KSNP3files, RESULTSfiles, RVDfiles, faaDir):
    for file in os.listdir(SCOARYfiles):
        if file.endswith(".csv"):
            scoaryCSV = (SCOARYfiles + file)
    try:
        scoaryCSV
    except:
        print("scoary CSV doesn't exist, unable to continue process")
        sys.exit()
    else:
        repeatsCSV = Rfiles + "RepeatNames.csv"
        boundFile = Rfiles + "boundMatrix.csv"
        distalGroups = DISTALfiles + "Outputs/disTALOut.TALgroups.csv"
        parsedTRF = TRFfiles + "trfParsed.txt"
        orthogroupsTXT = ORTHOfiles + "Orthogroups.txt"
        treeFile = KSNP3files + "kSNP3_results/tree.ML.tre"
        comboFile = DISTALfiles + "rvdCombo.FASTA"
        concatenated = (RESULTSfiles + "rvdNucs.csv")
        faaFile = (RESULTSfiles + "faaConcatenated.faa")
        subprocess.Popen(["Rscript", "addScripts/IdunsSecondR.R", scoaryCSV, repeatsCSV, boundFile, scorFile, distalGroups, parsedTRF, orthogroupsTXT, treeFile, comboFile, RESULTSfiles, concatenated, faaFile], close_fds=True).communicate()[0]
