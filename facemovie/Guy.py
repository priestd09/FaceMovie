'''
Created on 29 mars 2012

@author: jll
'''
import cv

import os # needed only for main. Shall be removed

class Guy(object):
    '''
    Represents the user on the people at a fixed time. 
    All data found for this time may be found here.
    '''
    def __init__(self, image, image_id):
        '''
        Constructor
        '''
        self.in_x = None
        self.in_y = None

        self.out_x = None
        self.out_y = None
        
        self.in_channels = image.nChannels
        self.name = image_id # Name of the picture used as input
        self.out_im = None
        self.in_image = None # input image
        
        self.faces = [] # List of faces detected for this input 
        
        # Some operations on variables
        (self.in_x, self.in_y) = cv.GetSize(image) # image size in x, y
        
        # Two variables used to define the new center of interest of the image
        # they are defined as the middle of input image at first
        self.x_center = self.in_x / 2
        self.y_center = self.in_y / 2
        
        # Creation of the images
        self.in_image = cv.CreateImage((self.in_x, self.in_y),cv.IPL_DEPTH_8U, self.in_channels)
        cv.Copy(image, self.in_image)

    def search_face(self, face_params):
        """
        Search on the picture for a face. 
        Populates faces list. 
        This function is the only one containing scaling information
        """
        # Allocate the temporary images
        gray = cv.CreateImage((self.in_x, self.in_y), 
                              cv.IPL_DEPTH_8U, 
                              1)
        smallImage = cv.CreateImage((cv.Round(self.in_x / face_params.image_scale),
                                     cv.Round (self.in_y / face_params.image_scale)), 
                                    cv.IPL_DEPTH_8U ,
                                    1)        
        
        # Converts color input image to grayscale
        cv.CvtColor(self.in_image, gray, cv.CV_BGR2GRAY)
        # Scales input image for faster processing
        cv.Resize(gray, smallImage, cv.CV_INTER_LINEAR)
        # Equalizes the histogram
        cv.EqualizeHist(smallImage, smallImage)
        
        # Detect the faces
        small_faces = cv.HaarDetectObjects(smallImage, 
                                     face_params.face_cascade, 
                                     cv.CreateMemStorage(0),
                                     face_params.haar_scale, 
                                     face_params.min_neighbors, 
                                     face_params.haar_flags, 
                                     face_params.min_size)
        
        # Resizing faces to full_scale
        for face in small_faces:
            if len(face): # if faces have been found
                ((x, y, w, h), n) = face
                big_face = ((int(x * face_params.image_scale), 
                             int(y * face_params.image_scale), 
                             int(w * face_params.image_scale), 
                             int(h * face_params.image_scale)), n)
                self.faces.append(big_face)
        
        # sorting faces to keep only the most probable one
        self.sort_faces()
        self.update_center() # finds center of face in image
        
        del gray
        del smallImage
        
    def sort_faces(self):
        """
        sort faces by number of neighbours found, most probable one first
        """
        if self.has_face() : # needed ?
            self.faces.sort(key= lambda prob : prob[1], reverse=True)
        else : 
            self.faces = []
        
    def update_center(self):
        """
        Using sorted faces, defines the new center of interest of the output image
        """
        if self.has_face():
            ((x, y, w, h), n) = self.faces[0]
            self.x_center = x + w / 2
            self.y_center = y + h / 2
    
    def normalize_face(self, reference):
        """
        Creates intermediate image, whose face fits reference size
        """
        self.normalize = 1
        
        ratio = reference / float(self.faces[0][0][3])
        #defines the size of the image to have an equalized face
        norm_x = int(ratio * self.in_x)
        norm_y = int(ratio * self.in_y)
      
        norm_im = cv.CreateImage((norm_x, norm_y),cv.IPL_DEPTH_8U, self.in_channels)
        cv.Resize(self.in_image, norm_im)
        self.in_image = norm_im # overriding in_image
        # updates center
        self.in_x = norm_x
        self.in_y = norm_y
        self.x_center = self.in_x / 2
        self.y_center = self.in_y / 2

    def create_video_output(self, x_size, y_size, x_point, y_point):
        """
        Creates image output, centering the face center with the required position
        If eq_ratio is set to something different than one, input image is scaled
        so that face/size = eq_ratio
        """
        self.out_im = cv.CreateImage((x_size, y_size),cv.IPL_DEPTH_8U, self.in_channels)
        cv.Zero(self.out_im)   

        # We want to place the input image so that the center of the face matches
        # x_center and y_center        
        xtl = x_point - self.x_center
        ytl = y_point - self.y_center
        w = self.in_x
        h = self.in_y
            
        rect = (xtl, ytl, w, h)
        cv.SetImageROI(self.out_im, rect)
        
        cv.Copy(self.in_image, self.out_im)
            
        cv.ResetImageROI(self.out_im) 

    def create_debug_output(self):
        """
        Creates output image
        If debug is set to true, output image is the input image with a red
        box around the most probable face.
        """
        self.out_im = cv.CreateImage((self.in_x, self.in_y),cv.IPL_DEPTH_8U, self.in_channels)
        cv.Zero(self.out_im) # put everything to 0
        
        cv.Copy(self.in_image, self.out_im)
        if self.has_face():
            # some nice drawings
            ((x, y, w, h), n) = self.faces[0]
            # the input to cv.HaarDetectObjects was resized, so scale the
            # bounding box of each face and convert it to two CvPoints
            pt1 = (x, y)
            pt2 = ((x + w), (y + h))
            cv.Rectangle(self.out_im, 
                        pt1, 
                        pt2, 
                        cv.RGB(255, 0, 0), 
                        3, 8, 0)# surrounds face   
        
            # Adds point in the center
            pt3 = (self.x_center, self.y_center)
            cv.Line(self.out_im, 
                        pt3, 
                        pt3, 
                        cv.RGB(0, 255, 0), 
                        3, 8, 0)
            
    def in_display(self, time=1000, im_x=640, im_y=480):
        """
        Displays the input image, for time ms.
        Setting time to 0 causes the image to remains open.
        """
        cv.NamedWindow(self.name, cv.CV_WINDOW_NORMAL)
        cv.ResizeWindow(self.name, im_x, im_y) 
        cv.ShowImage(self.name, self.in_image)
        cv.WaitKey(time)    
        cv.DestroyWindow(self.name)
        
    def out_display(self, time=1000, im_x=640, im_y=480):
        """
        Displays the output image, for time ms.
        Setting time to 0 causes the image to remains open.
        Window name slightly changed to match output
        """
        win_name = self.name + " - out"
        cv.NamedWindow(win_name, cv.CV_WINDOW_NORMAL)
        cv.ResizeWindow(win_name, im_x, im_y) 
        cv.ShowImage(win_name, self.out_im)
        cv.WaitKey(time)
        cv.DestroyWindow(win_name)

    def save_result(self, out_folder, ext):
        """
        Saves output image to the given format (given in extension)
        """
        file_name = self.name + "." + ext
        out_name = os.path.join(out_folder, file_name)
        print "Saving %s" %(out_name)
        
        cv.SaveImage(out_name, self.out_im)

    def num_faces(self):
        """
        Returns the number of faces found for this guy
        """
        return len(self.faces)        

    def has_face(self):
        """
        Returns True if at least one face has been found
        """
        return (len(self.faces) > 0)
    