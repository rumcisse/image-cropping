import cv2 as cv
from PIL import Image
import os
from numpy import where, array
import shutil

#Target dimensions of result image in centimeters
TARGET_HEIGHT_CM = 15.2
TARGET_WIDTH_CM = 10.2

#Target DPI of photo
DPI = 300

#Target ratio of the face size to the height of the image in percentage
TARGET_OVERHEAD_PERCENT = 0.38
TARGET_UNDERHEAD_PERCENT = 0.92

haar_casc = cv.CascadeClassifier('haarcascade_frontalface_default.xml')

def MaxFace(face_scaled, typ):

    #Use canny to get black and white edges of body/face
    canny = cv.Canny(face_scaled, 120,230)

    #Using numpy to select all white pixels (edges)
    indices = where(canny != [0])
    typ2 = typ

    if typ==2:
        typ2=1
    indices1 = list(indices[typ2])

    #Get index of white pixel located furthest to the top
    if typ==0:
        indx = indices1.index(min(indices1))

    #Get index of white pixel located furthest to the right 
    elif typ==1:
        indx = indices1.index(max(indices1))

    #Get index of white pixel located furthest to the left
    elif typ==2:
        typ = 1
        indx = indices1.index(min(indices1))

    return indices[typ][indx]

def GetFace(face_source, grayscale2, i2, scale2):

    #Function used to detect face if it wasn't found at first attempt
    #or remove all extra smallest areas (potential faces) and leave the biggest one

    if len(face_source)==0:

        #If face wasn't found, resize image by 0.75
        grayscale2 = cv.resize(grayscale2, (0,0), fx=0.75, fy=0.75, interpolation=cv.INTER_AREA)
        face_source = haar_casc.detectMultiScale(grayscale2, 1.1, i2, minSize=(int(0.12*grayscale2.shape[0]), int(0.12*grayscale2.shape[0])))
        scale2 *= 0.75

    while len(face_source)==0 and i2>4:
        #If face was't found try to decrement minimun neighbours paremeter
        i2 -= 1
        face_source = haar_casc.detectMultiScale(grayscale2, 1.1, i2, minSize=(int(0.15*grayscale2.shape[0]),int(0.15*grayscale2.shape[0])))
   
    #Find biggest area and return it's coordinates with new scale
    if len(face_source)>1:
        dimensions=[]
        
        for (x,y,w,h) in face_source:
            dimensions.append(w*h)

        indx = dimensions.index(max(dimensions))
        face_source = array([face_source[indx]])
    return scale2, face_source

def CropImage(reject_path, save_path, directory):

    #Replace DPI to Dots Per Centimeter 
    DPCM = DPI / 2.54
    
    #Calculate target height and width of final picture in pixels
    target_height_px = round(TARGET_HEIGHT_CM * DPCM,0)
    target_width_px = round(TARGET_WIDTH_CM * DPCM,0)

    #Calculate target ratio that final image should have
    target_ratio = round(target_height_px / target_width_px,8)

    for photo in os.listdir(directory):
        if photo.endswith(".JPG") or photo.endswith(".jpg"):
            
            #Read every picture with .jpg extenstion from directory
            #If picture couldn't be read, copy it to rejected photos directory
            try:
                img = cv.imread(directory+'/'+photo)
                height, width = img.shape[:2]

            except:
                shutil.copy2(os.path.join(directory,photo), os.path.join(reject_path,photo))
                yield 1
                continue

            #Scale original picture (200px width) to detect the face faster and convert to grayscale
            scale = round((200/width),6)
            img_scaled = cv.resize(img, (0,0), fx=scale, fy=scale, interpolation=cv.INTER_AREA)
            grayscale = cv.cvtColor(img_scaled, cv.COLOR_BGR2GRAY)

            #Detect face using Haar Cascade and pass it to function GetFace
            #variable face contains array of found conrdinates (x, y, width, height)
            face = haar_casc.detectMultiScale(grayscale, 1.1, 5)
            scale2 ,face = GetFace(face, grayscale, 5,scale)

            #Assign new scale value and resize original image if scale value was changed
            if scale2!=scale:
                scale = scale2
                img_scaled = cv.resize(img, (0,0), fx=scale, fy=scale, interpolation=cv.INTER_AREA)

            #Copy photo to rejected directory if the face was still not detected
            if len(face)==0 or (face[0][2]/(height*scale))<0.18:
                shutil.copy2(os.path.join(directory,photo), os.path.join(reject_path,photo))
                yield 1
                continue
            
            #Get position of face and its size (width == height)
            face_x = face[0][0]
            face_y = face[0][1]
            face_size = face[0][2]

            #Remove extra free space (on the left and right) to meet the ratio 
            #ALso removes all unnecessary gradients or shadows
            side = round(((img_scaled.shape[0]/target_ratio) - face_size)/2, 0)
            tmp_c = face_x - side
            tmp_d = face_x + side + face_size

            if tmp_c<0:
                tmp_c = 0
            
            if tmp_d>img_scaled.shape[1]:
                tmp_d = img_scaled.shape[1]

            #Create two separate fragments of scaled image
            #Get face with above free space and 5% extra on both sides
            img_over = img_scaled[0 : face_y+face_size, int(face_x*0.95) : int((face_x+face_size)*1.05)]

            #Get 65% of face and whole width of the image
            img_side = img_scaled[face_y : face_y+int(face_size*0.65), int(tmp_c) : int(tmp_d)]
            
            #Get x value of face (edge of the face - furthest to the left) 
            max_face_x = round(MaxFace(img_side, 1)/scale,0) + round(tmp_c/scale,0)

            #Get x value of face (edge of the face - furthest to the right) 
            min_face_x = round(MaxFace(img_side,2)/scale,0) + round(tmp_c/scale,0)

            #Get y value of face (top of the head) 
            max_face_y = round(MaxFace(img_over, 0)/scale,0)

            #Divide each scaled value to fit original picture
            face_x = round(face_x/scale,0)
            face_y = round(face_y/scale,0)
            face_size = round(face_size/scale,0)
            
            #Amount of pixels that should be left above the head
            overhead_px = round((TARGET_OVERHEAD_PERCENT*face_size) + ((face_y - max_face_y)/2),0)

            #Amount of pixels that should be left at the bottom of the head
            underhead_px = round(TARGET_UNDERHEAD_PERCENT*face_size,0)

            #a - amount of pixels which should be cut from the top (of the image)
            #b - amout of pixels which should be cut from the bottom
            #c - amout of pixels which should be cut from the left side
            #d - amout of pixels which should be cut from the right side
            a = face_y - overhead_px
            b = face_y + face_size + underhead_px
            c = 0
            d = width

            if a<0:
                a = 0
            
            if b>height:
                b = height

            #Get percentage of the space above the head in relation to height of the image
            overhead_ratio = (max_face_y - a)/(b - a)        

            #Increase space if it's too low
            if overhead_ratio<0.065:
                a = max_face_y-round(0.068*(b - a))
                if a<0:
                    a = 0

            #Decrease space if it's too big
            if overhead_ratio>0.075:
                a = max_face_y-round(0.075*(b - a))

                if a<0:
                    a = 0

            #Get percentage of the space under the head in relation to height of the image
            underhead_ratio = (b - ((face_y + face_size)))/(b - a)

            if underhead_ratio>0.33:
                b=(face_y + face_size) + round(0.33*(b - a))

            if b>height:
                b = height

            face_width = max_face_x - min_face_x

            #Remove extra space on the left and right 
            side = round(((b - a) - (target_ratio*face_width))/target_ratio,0)

            if side%2!=0:
                side = int(side/2)
                c = min_face_x - (side + 1)
                d = max_face_x + side

            else:
                c = min_face_x - (side/2)
                d = max_face_x + (side/2)

            #Increase c if it's to small
            if c>face_x:
                c = int(0.95*face_x)
        
            if c>min_face_x:
                c = int(0.95*min_face_x)

            #Check values
            if c<0:
                c = 0
            
            if d>width:
                d = width

            #Get width of left side of the image
            left_side = face_x - c

            #Get width of right side of the image
            right_side = d - (face_x + face_size)

            #Center the face if positioned too much to the right
            #Face can't be right in the middle of the image
            #Often head in the picture is turned to the left or right

            if left_side<right_side:
                if (left_side/right_side)<0.5:

                    #Calculate diffrences proportionally
                    diff = (face_x/max_face_x)/(b - a)
                    diff1 = round(left_side*(diff + (0.5 - (left_side/right_side))),0)
                    diff2 = round(right_side*(diff + (0.5 - (left_side/right_side))),0)
                    diff1 += int(diff2/2)

                    #Check if values aren't incorrect and could cause errors
                    if c-diff1<0:
                        diff2 += int(abs(c - diff1))
                        c=0
                    
                    else:
                        c -= diff1

                    d -= diff2

            current_ratio = round((b - a)/(d - c), 8)
            face_ratio = (face_width)/(d - c)

            #Current height to width ratio is too small
            #Increase height or decrease width depending on size of the face in final picture
            if current_ratio<target_ratio: 
              
                if face_ratio<0.66:
                    #Decrease width if face ratio is to small
                    #Face width should be from 66% to 86% of whole width of the picture

                    #Width diffrence - amount to be removed from width to match the ratio
                    wdiff = abs(round((((b - a))/target_ratio) - (d - c), 0))
                    
                    #Adjust width if face ratio is still correct
                    if (face_width)/((d - c) - wdiff)<0.86:
                        c += int(wdiff/2)
                        d -= (int(wdiff/2)+1)
                    
                    else:
                        #Get amount of pixels (width) needed to match 0.76 face ratio
                        x = (d - c) - round(face_width/0.76, 0)
                        
                        #Get amount of height needed after decreasing the width
                        hdiff = round(target_ratio*(wdiff - x), 0)
                    
                        #Adjust height and check incorrect values
                        if (b+hdiff)>height:
                            #If adding the diffrence creates incorrect value then adjust the width
                            x += round(((b + hdiff) - height)/target_ratio, 0)
                            b = height
                        
                        else:
                            b += hdiff

                        c += int(x/2)
                        d -= (int(x/2) + 1)

                else:
                    #Get amount of pixels (height) needed to match target ratio
                    hdiff = round((d - c)*target_ratio, 0) - (b - a)

                    #If adding the diffrence creates incorrect value then adjust the width
                    if (b+hdiff)>height:
                        y = round(((b + hdiff) - height)/target_ratio, 0)
                        c += int(y/2)
                        d -= (int(y/2) + 1)
                        b = height
                    
                    else:
                        b += hdiff
            
            #Current height to width ratio is too big
            #Decrease height or increase width depending on size of the face in final picture
            elif current_ratio>target_ratio:
            
                if face_ratio>0.86:
                    #Increase width if face size is too big
                    #Face width should be from 66% to 86% of the whole width

                    #Get difference of width needed to be added
                    wdiff = round(((b - a)/target_ratio) - (d - c), 0)

                    if face_width/((d - c) + wdiff)>0.86:

                        if c - (int(wdiff/2)+1)<0:
                            wdiff = c*2

                            if (d + int(c/2) + 1)>width:
                                wdiff = ((d + int(wdiff/2)) - width)*2
                                
                        elif (d + int(wdiff/2) + 1)>width:
                            wdiff = ((d + int(wdiff/2)) - width)*2
        
                            if (c - int(wdiff/2))<0:
                                wdiff = c*2

                        c -= int(wdiff/2)
                        d += int(wdiff/2)
  
                    else:
                        x = round(face_width/0.86) - (d - c)

                        if c-int(x/2)<0:
                            x = c*2

                            if d+int(c/2)>width:
                                x = ((d + int(x/2)) - width)*2
                        
                        elif d+int(x/2)>width:
                            x = ((d + int(x/2)) - width)*2

                            if c-int(x/2)<0:
                                x = c*2
                        
                        c -= int(x/2)
                        d += int(x/2)

                #Adjust only height if face ratio is ok    
                hdiff = abs((b - a) - round((d - c)*target_ratio, 0))
                b -= hdiff

            #Final adjustments to face ratio
            if (face_width/(d-c))<0.66:
                x = (d - c) - round(face_width/0.66,0)
                y = round(x*target_ratio, 0)

                if ((b - y) - (face_y + face_size))/((b - a) - y)<0.31:
                    y = abs(round((((face_y + face_size) + (0.31*(b - a))) - b)/1.31,0))
                    x = round(y/target_ratio,0)
                
                b -= y

                if x%2==0:
                    c += x/2
                    d -= x/2

                else:
                    c += int(x/2)
                    d -= (int(x/2) + 1)
            
            #Final adjustments to meet final ratio
            #Usually it's few pixels. <1% of whole height
            hdiff = round((d - c)*target_ratio, 0) - (b - a)

            if (b+hdiff)>height:
                wdiff = (b + hdiff) - height
                wdiff = round(wdiff*target_ratio, 0)

                c += wdiff
                b = height

            else:
                b += hdiff

            try:
                #Cut the image
                img = img[int(a):int(b), int(c):int(d)]

                #Convert from BGR to RGB 
                img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
                
                #Resize image to meet targets dimensions
                img = cv.resize(img, (0,0), fx=target_width_px/(d-c), fy=target_height_px/(b-a), interpolation=cv.INTER_AREA)

                #Convert image from OpenCV to PIL and save
                img = Image.fromarray(img)
                img.save(save_path+"/"+photo, dpi=(DPI,DPI), quality=100, subsampling=0)

            except:
                #Copy photo to reject directory
                shutil.copy2(os.path.join(directory,photo), os.path.join(reject_path,photo))
            yield 1