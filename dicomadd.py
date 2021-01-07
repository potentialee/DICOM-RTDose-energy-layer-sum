# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 16:55:12 2020

@author: Chanil
"""

################################# SMC_EneryLayerSum 0.0.1 #################################

#### Library import ####

# python dicom handling library
import pydicom
import numpy as np
from pydicom import dcmread
from pydicom.dataset import FileDataset, FileMetaDataset

# file systems and error handling
import os
import sys

# for writing dicom files
import datetime

#### Reading RT-dose dcm files in folders ####

# Get how many layers are there
fieldfolderPath_temp = os.listdir(os.getcwd())
layersInFieldFolder = []
for lists in fieldfolderPath_temp :
    if (os.path.isdir(lists)) :
        layersInFieldFolder.append(lists)
        
# list.sort(key=int) has error in some environments. use sort(key=lambda x:int(x))
layersInFieldFolder.sort(key=lambda x:int(x))

# Get dcm file information in each layer folders (Each energy layer)
# Generate dynamic variable by name RTDose_part_(Index of files)
layerCount = len(layersInFieldFolder)
RTdoseCount = 0
RTdoseForm = 'RTDose_part_{}'

for layer in layersInFieldFolder :
    currentLayer_temp = os.getcwd() + '\\' + layer
    os.chdir(currentLayer_temp)
    for files in os.listdir(os.getcwd()) :
        if (files.endswith('.dcm')):
            RTdoseCount+=1
            globals()[RTdoseForm.format(RTdoseCount)] = dcmread(files)
    os.chdir('..\\')


# If there is no RTdose dcm file or some folders don't have dcm file, notified and exit
# if file validity check is done, start to make integrated RT-dose file
if RTdoseCount == 0 :
    print("Warning ** There is no RT dose file! Check the file is in there. **")
    sys.exit()
elif layerCount != RTdoseCount :
    print("Warning ** Some folders don't have .dcm file. Check status. **")
    sys.exit()
else :
    print("Reading RT-Dose energy layer DCM files succeeded!")
    print("Information integration starts...")


#### RT-dose file information integration ####

# getting first energy layer's information for ~
# 1. integrating pixel data from each energy layer files
# 2. writing integrated file's meta data and making file


## 1. integrating pixel data from each energy layer files ##

RTdose_EnergyLayer_1 = globals()['RTDose_part_1']

# caculate axis for interpolation (not using because all dose grids' are same)
#RTdose_EnergyLayer_1.x_axis = np.arange(RTdose_EnergyLayer_1.Columns) * RTdose_EnergyLayer_1.PixelSpacing[0] + RTdose_EnergyLayer_1.ImagePositionPatient[0]
#RTdose_EnergyLayer_1.y_axis = np.arange(RTdose_EnergyLayer_1.Rows) * RTdose_EnergyLayer_1.PixelSpacing[1] + RTdose_EnergyLayer_1.ImagePositionPatient[1]
#RTdose_EnergyLayer_1.z_axis = np.array(RTdose_EnergyLayer_1.GridFrameOffsetVector) + RTdose_EnergyLayer_1.ImagePositionPatient[2]

RTdose_EnergyLayer_1_pixel_array = RTdose_EnergyLayer_1.pixel_array * RTdose_EnergyLayer_1.DoseGridScaling

# dose grid sum standard is first dose grid data
start_dose_grid = np.swapaxes(RTdose_EnergyLayer_1_pixel_array, 0, 2)

# Add global variable 
for variable in list(globals()) :
    if variable.startswith('RTDose_part_') and variable !='RTDose_part_1' :
        RTdose_temp = globals()[variable]
        # Check the file is RT-Dose file
        if RTdose_temp.Modality == 'RTDOSE' :
            # caculate axis for interpolation (not using because all dose grids' are same)
            #RTdose_temp.x_axis = np.arange(RTdose_temp.Columns) * RTdose_temp.PixelSpacing[0] + RTdose_temp.ImagePositionPatient[0]
            #RTdose_temp.y_axis = np.arange(RTdose_temp.Rows) * RTdose_temp.PixelSpacing[1] + RTdose_temp.ImagePositionPatient[1]
            #RTdose_temp.z_axis = np.array(RTdose_temp.GridFrameOffsetVector) + RTdose_temp.ImagePositionPatient[2]
            pixel_array_temp = RTdose_temp.pixel_array * RTdose_temp.DoseGridScaling
            dose_grid_temp = np.swapaxes(pixel_array_temp, 0, 2)
            # Direct sum becuase all file is same
            start_dose_grid += dose_grid_temp
        else:
            print("One or more Readed dcm file is not RT-dose file! check the dcm information - Modality.")
            print("Program exit : DCM file is not RT-dose file.")
            sys.exit()
        

# Convert to RT dose pixel data
DoseGridScalingFactor = np.max(start_dose_grid) / np.iinfo(np.uint32).max
pixelData_temp = np.swapaxes(start_dose_grid, 0, 2) / DoseGridScalingFactor
pixelDataSum = np.uint32(pixelData_temp).tobytes()

## 2. Writing integrated file's meta data and make file ##

filename_little_endian = os.getcwd() + '\\' + 'energylayersum.dcm'

# Writing meta-data information ----------------------------------------------------------
print("Setting file meta information...")

# Populate required values for file meta information
file_meta = FileMetaDataset()

# This means 'RT Dose Storage' in DICOM
file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'

# UID generated with randomly
# none prefix => pydicom.uid.generate_uid(prefix=None)
file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()

# This means 'Implicit VR little endian'
file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'
file_meta.ImplementationClassUID = pydicom.uid.generate_uid()
file_meta.ImplementationVersionName = 'SMC_EnergyLayerSum 0.0.1'
file_meta.SourceApplicationEntityTitle = 'SMC_EnergyLayerSum'

# Writing dataset information ------------------------------------------------------------
print("Setting dataset values...")

# Create the FileDataset instance (initially no data elements, but file_meta supplied)
ds = FileDataset(filename_little_endian, {},
                  file_meta=file_meta, preamble=b"\0" * 128)

# get current time information
dt = datetime.datetime.now()
timeStr_ymd = dt.strftime('%Y%m%d')
timeStr_short = dt.strftime('%H%M%S') # short format 
timeStr_long = dt.strftime('%H%M%S.%f')  # long format with micro seconds

# Add the data elements
ds.ImageType = 'DERIVED' # image is derived from one or more image's pixel value
ds.InstanceCreationDate = timeStr_ymd
ds.InstanceCreationTime = timeStr_short

# This means 'RT Dose Storage' in DICOM
ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
# UID generated with randomly
ds.SOPInstanceUID = pydicom.uid.generate_uid()

ds.StudyDate = timeStr_ymd
ds.SeriesDate = timeStr_ymd
ds.ContentDate = timeStr_ymd
ds.StudyTime = timeStr_long
ds.SeriesTime = timeStr_short
ds.ContentTime = timeStr_short
ds.AccessionNumber = ''
ds.Modality = 'RTDOSE'
ds.Manufacturer = 'SMC_EnergyLayerSum'
ds.ReferringPhysicianName = ''
ds.SeriesDescription = 'Dosemap [Gy]'
ds.ManufacturerModelName = 'SMC_EnergyLayerSum 0.0.1'
ds.PatientName = RTdose_EnergyLayer_1.PatientName
ds.PatientID = RTdose_EnergyLayer_1.PatientID
ds.PatientBirthDate = RTdose_EnergyLayer_1.PatientBirthDate
ds.PatientSex = RTdose_EnergyLayer_1.PatientSex

# UID generated with randomly
# prefix 1.2.826.0.1.3680043.8.498.~
ds.StudyInstanceUID = pydicom.uid.generate_uid()
ds.SeriesInstanceUID = pydicom.uid.generate_uid()

ds.StudyID = RTdose_EnergyLayer_1.StudyID
ds.SeriesNumber = RTdose_EnergyLayer_1.SeriesNumber
ds.InstanceNumber = RTdose_EnergyLayer_1.InstanceNumber
ds.ImagePositionPatient = RTdose_EnergyLayer_1.ImagePositionPatient
ds.ImageOrientationPatient = RTdose_EnergyLayer_1.ImageOrientationPatient

# UID generated with randomly
# prefix 1.2.826.0.1.3680043.8.498.~
ds.FrameOfReferenceUID = pydicom.uid.generate_uid()

ds.SamplesPerPixel = RTdose_EnergyLayer_1.SamplesPerPixel
ds.PhotometricInterpretation = RTdose_EnergyLayer_1.PhotometricInterpretation
ds.NumberOfFrames = RTdose_EnergyLayer_1.NumberOfFrames
ds.FrameIncrementPointer = RTdose_EnergyLayer_1.FrameIncrementPointer
ds.Rows = RTdose_EnergyLayer_1.Rows
ds.Columns = RTdose_EnergyLayer_1.Columns
ds.PixelSpacing = RTdose_EnergyLayer_1.PixelSpacing
#ds.BitsAllocated = RTdose_EnergyLayer_1.BitsAllocated
#ds.BitsStored = RTdose_EnergyLayer_1.BitsStored
#ds.HighBit = RTdose_EnergyLayer_1.HighBit
ds.BitsAllocated = 32
ds.BitsStored = 32
ds.HighBit = 31
ds.PixelRepresentation = RTdose_EnergyLayer_1.PixelRepresentation
ds.GridFrameOffsetVector = RTdose_EnergyLayer_1.GridFrameOffsetVector
ds.DoseUnits = 'GY'
ds.DoseType = 'PHYSICAL'
ds.DoseSummationType = 'PORT'

# Integrated Pixel Data and scaling factor
ds.DoseGridScaling = DoseGridScalingFactor
ds.PixelData = pixelDataSum

# # Set the transfer syntax
ds.is_little_endian = True
ds.is_implicit_VR = True

ds.save_as(filename_little_endian)
print("File saved successfully!")
