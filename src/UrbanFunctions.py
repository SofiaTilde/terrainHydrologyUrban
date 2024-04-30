import random
import matplotlib.pyplot as plt
import math
from PIL import Image

#Initialize global variables
cityPointsGlobal = list()
cityPointsAll = list()
picScale = 0
inputResolution = 0
outputDir = ""
globalseed = 0
size = 0
#Images that aren't initialized before the function
#shore
#imStretch
#pix

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
            #when ri 280 then mult=2
            #when ri 87.5 then mult=1
            mult = 1
            if inputResolution > 87.5:
                mult = (0.0051948052 * inputResolution) + 0.545454545
            plt.plot(x, y, linewidth = width * mult, c = '#888888', solid_capstyle = 'round')

    plt.figure(10)
    plt.axis('off')
    plt.imshow(shore, extent = imStretch, interpolation = 'none')
    plt.savefig(outputDir + 'out-rivers.png', dpi = fig1.dpi, bbox_inches = 'tight', pad_inches = 0.0)
    plt.axis('on')

    plt.figure(11)
    plt.axis('off')
    plt.imshow(shore, extent = imStretch, interpolation = 'none')
    plt.savefig(outputDir + 'out-rivers-city-mask.png', dpi = fig2.dpi, bbox_inches = 'tight', pad_inches = 0.0)
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

def IsRiver(primPos):
    (primX, primY) = primPos
    #primX goes from 1 to n, but picX goes from 0 to (n-1)
    picX = round(primX * picScale) - 1
    picY = round(primY * picScale) - 1
    (r, _, _, _) = pix[picX, picY]
    if r == 0 or r == 255:
        return False
    else:
        return True

def GenerateCity(Ts, radius, minElevation, maxElevation):
    global cityPointsGlobal
    global cityPointsAll
    global pix
    global picScale

    radius = radius * inputResolution
    primitives = Ts.allTs()
    centerIndex = random.randint(0, len(primitives) - 1)
    iter = 0
    maxIter = 100000
    while primitives[centerIndex].elevation >=  maxElevation: #makes sure that the centerIndex is under maxElevation
        centerIndex = random.randint(0, len(primitives) - 1)
        if iter >= maxIter:
            print(f'Failed to generate city')
            return
        iter += 1
    
    selectedCenter = primitives[centerIndex]
    (centerX, centerY) = selectedCenter.position
    cityPoints = Ts.query_ball_point(selectedCenter.position, radius)

    #for IsRiver function
    im = Image.open(outputDir + 'out-rivers-city-mask.png')
    pix = im.load()
    picScale = max(im.size) / size
    
    for prim in cityPoints:
        cityPointsAll.append(prim)
        if Accept(radius, prim.position, selectedCenter.position) is not True:
            continue
        if IsRiver(prim.position): # If primitive is on top of a river
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

    for i in range(1, numCities + 1):
        random.seed(math.pow(globalseed, i + 1))
        print(f'\tGenerating city: {str(i)} of {numCities}\r', end = '')
        GenerateCity(Ts, radius = 120, minElevation = 300, maxElevation = 75000)
    print()
    print("Generating city points image with", len(cityPointsGlobal), "points...")
    fig = plt.figure(figsize = (16, 16))
    #myAx = fig.add_subplot(111)
    plt.imshow(shore, extent = imStretch)
    #eleLambda = lambda a : a.elevation / highestRidgeElevation
    #eleLambda = lambda a : 0.2
    
    pixelsPerBuilding = 3
    buildingSize = (pixelsPerBuilding*(72./fig.dpi))**2
    plt.scatter(*zip(*[t.position for t in cityPointsGlobal]), c = '#888888', s = buildingSize, lw = 0, marker = "s")

    plt.gray()
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(outputDir + "city-primitives.png", dpi = fig.dpi, bbox_inches = 'tight', pad_inches = 0)
    plt.axis('on')

    # Create reject image
    plt.figure(figsize = (16, 16))
    #myAx = fig.add_subplot(111)
    plt.imshow(shore, extent = imStretch)
    #eleLambda = lambda a : a.elevation / highestRidgeElevation
    #eleLambda = lambda a : 0.2

    plt.scatter(*zip(*[t.position for t in cityPointsAll]), c = '#888888', s = buildingSize, lw = 0, marker = "s")

    plt.gray()
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(outputDir + "city-primitives-reject.png", dpi = fig.dpi, bbox_inches = 'tight', pad_inches = 0)
    plt.axis('on')