# Import the packages we need for drawing and displaying images
from PIL import Image, ImageDraw
import logging
logging.getLogger('').setLevel(logging.INFO)


# Imports the Google Cloud client packages we need
from google.cloud import vision
from google.cloud.vision.likelihood import Likelihood

from visionanalyzer import getSentimentWeightedByLevel, GOOD_SENTIMENT_THRESHOLD, BAD_SENTIMENT_THRESHOLD

# Import the packages we need for reading parameters and files
import io
import sys
COLOR_MEH = (0, 0, 127)
COLOR_BAD = (200, 0, 0)
COLOR_GOOD = (0, 200, 0)
COLOR_FEATURES = (255,255,255)

# first you have to authenticate for the default application: gcloud auth application-default login

# Instantiates a vision service client
vision_client = vision.Client()

def loadImageFile(filename):
# Loads the image into memory
# Return the image way content
    with io.open(filename, 'rb') as image_file:
        content = image_file.read()
    return content

def setImage(rawContent):
# Send the image to the cloud vision service to a analyze
# Return the Google Vision Image
    image = vision_client.image(content=rawContent)
    return image

def getFaces(image):
    # Tell the vision service to look for faces in the image
    faces = image.detect_faces(limit=30)
    return faces

def rankSentiment(face):
    return getSentimentWeightedByLevel(face)

def findFaceDetails(faces):
    face_details = []
    if faces:
        for face in faces:
            top = 9999
            left = 9999
            bottom = 0
            right = 0
            for point in face.bounds.vertices:
                top = min(top, point.y_coordinate)
                left = min(left, point.x_coordinate)
                bottom = max(bottom, point.y_coordinate)
                right = max(right, point.x_coordinate)
            sentiment = rankSentiment(face)
            face_details.append((sentiment, ((left, top), (right, bottom))))
    return face_details

def getColorForSentiment(sentiment):
    if sentiment < 0:
        return COLOR_BAD
    if sentiment > 0:
        return COLOR_GOOD
    return COLOR_MEH
    
if __name__ == '__main__':
    # Process the filenames specified on the command line
    if len(sys.argv) > 1:
        for image_filename in sys.argv[1:]:
            content = loadImageFile(image_filename)
            image = setImage(content)
            im = Image.open(io.BytesIO(content))
            canvas = ImageDraw.Draw(im)

            faces = getFaces(image)
    
            details = findFaceDetails(faces)

            for face_sentiment, face_boundary in details:
                sentiment_color = getColorForSentiment(face_sentiment)
                canvas.ellipse(face_boundary, fill=sentiment_color, outline=None)
                eye_size = max(1, (face_boundary[1][0] - face_boundary[0][0]) / 50) 
                nose_size = 2*eye_size
                eye_level = face_boundary[0][1] + (face_boundary[1][1] - face_boundary[0][1])/3.0
                nose_level = face_boundary[0][1] + (face_boundary[1][1] - face_boundary[0][1])/2.0
                mouth_size_h = (face_boundary[1][0] - face_boundary[0][0])/2.0
                mouth_size_v = (face_boundary[1][1] - nose_level)/2.0
                mouth_size=min(mouth_size_v, mouth_size_h)
                mouth_inset = ((face_boundary[1][0]-face_boundary[0][0])-mouth_size)/2

                canvas.ellipse((face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/3.0)-eye_size, eye_level-eye_size, face_boundary[0][0]+((face_boundary[1][0]-face_boundary[0][0])/3.0)+eye_size, eye_level + eye_size), None, outline=COLOR_FEATURES) 
                canvas.ellipse((face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/3.0)*2-eye_size, eye_level-eye_size, face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/3.0)*2+eye_size, eye_level+eye_size), None, outline=COLOR_FEATURES) 

                canvas.ellipse((face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/2.0)-nose_size, nose_level-nose_size, face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/2.0)+nose_size, nose_level+nose_size), COLOR_FEATURES, outline=COLOR_FEATURES) 

                if sentiment_color == COLOR_GOOD:
                    canvas.arc(( face_boundary[0][0]+mouth_inset, nose_level, face_boundary[0][0]+mouth_inset+mouth_size, nose_level+mouth_size), 35, 135, fill=COLOR_FEATURES)
                elif sentiment_color == COLOR_BAD:
                    canvas.arc(( face_boundary[0][0]+mouth_inset, face_boundary[1][1]-(face_boundary[1][1]-nose_level)*0.67, face_boundary[0][0]+mouth_inset+mouth_size, face_boundary[1][1]), 215, 335, fill=COLOR_FEATURES)

        im.show()
