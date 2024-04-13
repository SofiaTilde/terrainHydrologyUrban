import argparse
import random
import matplotlib.pyplot as plt
import cv2 as cv
import numpy as np
from scipy.spatial import voronoi_plot_2d
import networkx as nx
from scipy import interpolate
import shapely.geometry as geom
import numpy as np
from shapely.geometry import LineString
from multiprocessing import Process, Pipe, Queue
from tqdm import trange
import math
import rasterio
from rasterio.transform import Affine
from PIL import Image
#todo get a real size for buildings and river width
def InitUrbanFunctions(res, shore1, imStretch1, outputDir1, seed):
    global inputResolution
    global shore
    global imStretch
    global outputDir
    global globalseed
    inputResolution = res
    shore = shore1
    imStretch = imStretch1
    outputDir = outputDir1
    globalseed = seed
    random.seed(seed)

def SetSize(inSize):
    global size
    size = inSize

def Generate_river_map(hydrology, normalizer):
    fig1 = plt.figure(10, figsize = (20, 20))
    fig2 = plt.figure(11, figsize = (20, 20))
    
    for mouth in hydrology.allMouthNodes():
        for leaf in hydrology.allLeaves(mouth.id):
            x = [coord[0] for coord in leaf.rivers[0].coords]
            y = [coord[1] for coord in leaf.rivers[0].coords]
            width = 6 * 30 * leaf.flow / normalizer
            plt.figure(10)
            plt.plot(x, y, linewidth = width, c = '#888888', solid_capstyle = 'round')
            plt.figure(11)
            plt.plot(x, y, linewidth = width * 2, c = '#888888', solid_capstyle = 'round')

    plt.figure(10)
    plt.axis('off')
    plt.imshow(shore, extent = imStretch, interpolation = 'none')
    plt.savefig(outputDir + 'out-rivers.png', dpi = fig1.dpi, bbox_inches = 'tight', pad_inches = 0.0)
    plt.axis('on')

    plt.figure(11)
    plt.axis('off')
    plt.imshow(shore, extent = imStretch, interpolation = 'none')
    plt.savefig(outputDir + 'out-rivers2.png', dpi = fig2.dpi, bbox_inches = 'tight', pad_inches = 0.0)
    plt.axis('on')

def AcceptProbabilityFunction(radius, delta):
    x = delta / radius
    #https://mycurvefit.com/
    #   0       1          
    #   1       0          
    #   0.4     0.9        
    #   0.7     0.1        
    #y = -0.007567003 + (1 + 0.007567003)/(1 + math.pow((x/0.5319382), 7.737233))
    y = 1.004701771/(1 + math.pow((x / 0.4259953), 6.281081)) - 0.004701771
    return y

def Accept(radius, primPos, centerPos):
    (primX, primY) = primPos
    (centerX, centerY) = centerPos
    deltaX = abs(primX - centerX)
    deltaY = abs(primY - centerY)
    deltaR = math.sqrt(math.pow(deltaX, 2) + math.pow(deltaY, 2))
    return random.random() <=  AcceptProbabilityFunction(radius, deltaR)

def IsRiver(primPos, picSize, pix):
    global size
    (primX, primY) = primPos
    scale = picSize / size
    picX = round(primX * scale) - 1
    picY = round(primY * scale) - 1
    if picX > (picSize - 1) or picY > (picSize - 1):
        #this should never happen
        #print(f'x: {primX}, y: {primY}, px: {picX}, py: {picY}, picSize: {picSize}, size: {size}')
        return True
    (r, _, _, _) = pix[picX, picY]
    if r == 0 or r == 255:
        return False
    else:
        return True

cityPointsGlobal = list()
cityPointsAll = list()

def GenerateCity(Ts, radius, minElevation, maxElevation):
    global cityPointsGlobal
    global cityPointsAll
    global inputResolution

    radius = radius * inputResolution
    primitives = Ts.allTs()
    centerIndex = random.randint(0, len(primitives) - 1)
    while primitives[centerIndex].elevation >=  maxElevation: #makes sure that the centerIndex is under maxElevation
        #todo max iterations to prevent locking program
        centerIndex = random.randint(0, len(primitives) - 1)
    
    selectedCenter = primitives[centerIndex]
    (centerX, centerY) = selectedCenter.position
    cityPoints = Ts.query_ball_point(selectedCenter.position, radius)
    im = Image.open(outputDir + 'out-rivers2.png')
    pix = im.load()
    picSize = max(im.size)
    
    for prim in cityPoints:
        cityPointsAll.append(prim)
        if Accept(radius, prim.position, selectedCenter.position) is not True:
            continue
        if IsRiver(prim.position, picSize, pix):
            continue
        if prim.elevation >=  minElevation and prim.elevation <=  maxElevation:
            #(x, y) = prim.position
            #print("X:", x, "|Y:", y)
            (x, y) = prim.position
            deltaX = abs(x - centerX)
            deltaY = abs(y - centerY)
            cityPointsGlobal.append(prim)
            #prim.elevation = highestRidgeElevation + 1200 #debug

def GenerateCities(Ts, numCities):
    print("Generating cities...")
    global cityPointsGlobal
    global cityPointsAll
    global globalseed

    for i in range(1, numCities + 1):
        random.seed(math.pow(globalseed, i + 1))
        print(f'\tGenerating city: {str(i)} of {numCities}\r', end = '')
        GenerateCity(Ts, radius = 120, minElevation = 300, maxElevation = 75000)
    print()
    print("Generating city points image with", len(cityPointsGlobal), "points...")
    plt.figure(figsize = (16, 16))
    #myAx = fig.add_subplot(111)
    plt.imshow(shore, extent = imStretch)
    #eleLambda = lambda a : a.elevation / highestRidgeElevation
    #eleLambda = lambda a : 0.2
    
    plt.scatter(*zip(*[t.position for t in cityPointsGlobal]), c = '#888888', s = 8, lw = 0, marker = "s")

    plt.gray()
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(outputDir + "city-primitives.png", dpi = 500, bbox_inches = 'tight', pad_inches = 0)
    plt.axis('on')

    # Create reject image
    plt.figure(figsize = (16, 16))
    #myAx = fig.add_subplot(111)
    plt.imshow(shore, extent = imStretch)
    #eleLambda = lambda a : a.elevation / highestRidgeElevation
    #eleLambda = lambda a : 0.2

    plt.scatter(*zip(*[t.position for t in cityPointsAll]), c = '#888888', s = 8, lw = 0, marker = "s")

    plt.gray()
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(outputDir + "city-primitives-reject.png", dpi = 500, bbox_inches = 'tight', pad_inches = 0)
    plt.axis('on')