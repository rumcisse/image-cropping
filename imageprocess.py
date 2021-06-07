import cv2 as cv
from PIL import Image
import os
from numpy import where, array
import shutil

target_height_cm = 15.2
target_width_cm = 10.2
TARGET_OVERHEAD_PERCENT = 0.38
TARGET_UNDERHEAD_PERCENT = 0.92
PIC_TYPE=(".JPG",".jpg",".png")
haar_casc=cv.CascadeClassifier('haarcascade_frontalface_default.xml')

def MaxFace(face_scaled, typ):
    canny = cv.Canny(face_scaled, 120,230)
    indices = where(canny != [0])
    typ2 = typ

    if typ==2:
        typ2=1
    indices1 = list(indices[typ2])

    if typ==0:
        indx = indices1.index(min(indices1))

    elif typ==1:
        indx = indices1.index(max(indices1))

    elif typ==2:
        typ = 1
        indx = indices1.index(min(indices1))

    return indices[typ][indx]

def GetFace(face_source,grayscale2,i2,scale2):
    if len(face_source)==0:
        grayscale2 = cv.resize(grayscale2, (0,0), fx=0.75, fy=0.75, interpolation=cv.INTER_AREA)
        face_source = haar_casc.detectMultiScale(grayscale2, 1.1, i2, minSize=(int(0.12*grayscale2.shape[0]),int(0.12*grayscale2.shape[0])))
        scale2*=0.75

    while len(face_source)==0 and i2>4:
        i2-=1
        face_source = haar_casc.detectMultiScale(grayscale2, 1.1, i2, minSize=(int(0.15*grayscale2.shape[0]),int(0.15*grayscale2.shape[0])))
   
    if len(face_source)>1:
        dimensions=[]
        
        for (x,y,w,h) in face_source:
            dimensions.append(w*h)

        indx = dimensions.index(max(dimensions))
        face_source = array([face_source[indx]])
    return scale2,face_source

def CropImage(reject_path, save_path, directory, dpi):

    dpcm = dpi/2.54
    target_height_px = round(target_height_cm*dpcm,0)
    target_width_px = round(target_width_cm*dpcm,0)
    target_ratio = round(target_height_px/target_width_px,8)

    for photo in os.listdir(directory):
        if photo.endswith(".JPG") or photo.endswith('.jpg'):
            i=5
            try:
                img=cv.imread(directory+'/'+photo)
                height, width = img.shape[:2]
            except:
                shutil.copy2(os.path.join(directory,photo), os.path.join(reject_path,photo))
                yield 1
                continue

            scale = round((200/width),6)
            img_scaled = cv.resize(img, (0,0), fx=scale, fy=scale, interpolation=cv.INTER_AREA)
            grayscale = cv.cvtColor(img_scaled, cv.COLOR_BGR2GRAY)
            face = haar_casc.detectMultiScale(grayscale, 1.1, i)
            scale2 ,face = GetFace(face, grayscale, i,scale)

            if scale2!=scale:
                scale = scale2
                img_scaled = cv.resize(img, (0,0), fx=scale, fy=scale, interpolation=cv.INTER_AREA)

            if len(face)==0 or (face[0][2]/(height*scale))<0.18:
                shutil.copy2(os.path.join(directory,photo), os.path.join(reject_path,photo))
                yield 1
                continue

            facex = face[0][0]
            facey = face[0][1]
            face_size = face[0][2]

            side = round(((img_scaled.shape[0]/target_ratio)-face_size)/2,0)
            tmp_c = facex-side
            tmp_d = facex+side+face_size

            if tmp_c<0:
                tmp_c = 0
            
            if tmp_d>img_scaled.shape[1]:
                tmp_d = img_scaled.shape[1]

            img_over = img_scaled[0:facey+face_size, int(facex*0.95):int((facex+face_size)*1.05)]
            img_side = img_scaled[facey:facey+int(face_size*0.65), int(tmp_c):int(tmp_d)]
            
            facex = round(facex/scale,0)
            facey = round(facey/scale,0)
            face_size = round(face_size/scale,0)

            max_facex = round(MaxFace(img_side, 1)/scale,0)+round(tmp_c/scale,0)
            min_facex = round(MaxFace(img_side,2)/scale,0)+round(tmp_c/scale,0)
            max_facey = round(MaxFace(img_over, 0)/scale,0)

            overhead_px = round((TARGET_OVERHEAD_PERCENT*face_size)+((facey-max_facey)/2),0)
            underhead_px = round(TARGET_UNDERHEAD_PERCENT*face_size,0)

            a = facey-overhead_px
            b = facey+face_size+underhead_px
            c = 0
            d = width

            if a<0:
                a = 0
            
            if b>height:
                b = height

            overhead_ratio=(max_facey-a)/(b-a)        

            if overhead_ratio<0.065:
                a = max_facey-round(0.068*(b-a))
                if a<0:
                    a=0
                
            if overhead_ratio>0.075:
                
                a = max_facey-round(0.075*(b-a))

                if a<0:
                    a = 0

            underhead_ratio = (b-((facey+face_size)))/(b-a)

            if underhead_ratio>0.33:
                b=(facey+face_size)+round(0.33*(b-a))
        
            face_width = max_facex-min_facex
            side = round(((b-a)-(target_ratio*face_width))/target_ratio,0)

            if b>height:
                b=height

            if side%2!=0:
                side = int(side/2)
                c = min_facex-(side+1)
                d = max_facex+side

            else:
                c = min_facex-(side/2)
                d = max_facex+(side/2)

            if c>facex:
                c = int(0.95*facex)
        
            if c>min_facex:
                c = int(0.95*min_facex)

            if c<0:
                c=0
            
            if d>width:
                d = width

            left_side = facex-c
            right_side = d-(facex+face_size)

            if left_side<right_side:
                if (left_side/right_side)<0.5:
                    diff = (facex/max_facex)/(b-a)
                    diff1 = round(left_side*(diff+(0.5-(left_side/right_side))),0)
                    diff2 = round(right_side*(diff+(0.5-(left_side/right_side))),0)
                    diff1+=int(diff2/2)

                    if c-diff1<0:
                        diff2+=int(abs(c-diff1))
                        c=0
                    
                    else:
                        c-=diff1
                    d-=diff2

            current_ratio = round((b-a)/(d-c),8)
            face_ratio = (face_width)/(d-c)

            if current_ratio<target_ratio: 
                if face_ratio<0.66:
                    wdiff = abs(round((((b-a))/target_ratio)-(d-c),0))

                    if (face_width)/((d-c)-wdiff)<0.66:
                        c+=int(wdiff/2)
                        d-=(int(wdiff/2)+1)
                    
                    else:
                        x = (d-c)-round(face_width/0.66,0)
                        hdiff = round(target_ratio*(wdiff-x),0)
                    
                        if (b+hdiff)>height:
                            x+=round(((b+hdiff)-height)/target_ratio,0)
                            b = height
                        
                        else:
                            b+=hdiff

                        c+=int(x/2)
                        d-=(int(x/2)+1)

                else:
                    hdiff=round((d-c)*target_ratio,0)-(b-a)

                    if (b+hdiff)>height:
                        y=round(((b+hdiff)-height)/target_ratio,0)

                        c+=int(y/2)
                        d-=(int(y/2)+1)
                        b = height
                    
                    else:
                        b+=hdiff
                
            elif current_ratio>target_ratio:
            
                if face_ratio>0.86:
                    wdiff = round(((b-a)/target_ratio)-(d-c),0)

                    if face_width/((d-c)+wdiff)>0.86:

                        if c-(int(wdiff/2)+1)<0:
                            wdiff = c*2

                            if (d+int(c/2)+1)>width:
                                wdiff = ((d+int(wdiff/2))-width)*2
                                
                        elif (d+int(wdiff/2)+1)>width:
                            wdiff = ((d+int(wdiff/2))-width)*2
        
                            if (c-int(wdiff/2))<0:
                                wdiff = c*2

                        c-=int(wdiff/2)
                        d+=int(wdiff/2)
                    
                    else:
                        x = round(face_width/0.86)-(d-c)

                        if c-int(x/2)<0:
                            x = c*2

                            if d+int(c/2)>width:
                                x = ((d+int(x/2))-width)*2
                        
                        elif d+int(x/2)>width:
                            x = ((d+int(x/2))-width)*2

                            if c-int(x/2)<0:
                                x=c*2
                        
                        c-=int(x/2)
                        d+=int(x/2)
                    
                hdiff = abs((b-a)-round((d-c)*target_ratio,0))
                b-=hdiff

            if (face_width/(d-c))<0.66:
                x = (d-c)-round(face_width/0.66,0)
                y = round(x*target_ratio,0)

                if ((b-y)-(facey+face_size))/((b-a)-y)<0.31:
                    y = abs(round((((facey+face_size)+(0.31*(b-a)))-b)/1.31,0))
                    x = round(y/target_ratio,0)
                
                b-=y
                if x%2==0:
                    c+=x/2
                    d-=x/2
                else:
                    c+=int(x/2)
                    d-=(int(x/2)+1)
            
            hdiff = round((d-c)*target_ratio,0)-(b-a)

            if (b+hdiff)>height:
                wdiff=(b+hdiff)-height
                wdiff=round(wdiff*target_ratio,0)
                d-=wdiff
                b=height

            else:
                b+=hdiff

            try:
                img=img[int(a):int(b), int(c):int(d)]
                img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
                img=cv.resize(img, (0,0), fx=target_width_px/(d-c), fy=target_height_px/(b-a), interpolation=cv.INTER_AREA)
                img = Image.fromarray(img)
                img.save(save_path+"/"+photo, dpi=(dpi,dpi), quality=100, subsampling=0)
            except:
                shutil.copy2(os.path.join(directory,photo), os.path.join(reject_path,photo))
            yield 1