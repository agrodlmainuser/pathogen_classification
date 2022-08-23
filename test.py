import tensorflow as tf
from tensorflow import keras
import tensorflow_hub as hub
from tensorflow.keras import models, layers
import matplotlib.pyplot as plt
from IPython.display import HTML
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import datetime
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import shutil
import os
import cv2
import torch
import torchvision
from torchvision.io import read_image
from torchvision.utils import draw_bounding_boxes
import re
from ADL_classes import ADL_Read_XML
import xml.etree.ElementTree as ET


%cd /content/drive/MyDrive/Colab Notebooks
script_params = ADL_Read_XML("AgroDL_Original_Leaf_Classification_Detections_0000")
trained_model_name = script_params.get_params("trained_model_name")
trained_model_dir = script_params.get_params("trained_model_dir")
train_dir = script_params.get_params("train_dir")
images_dir = script_params.get_params("images_dir")
original_img_dir_root = script_params.get_params("original_img_dir_root")
output_root = script_params.get_params("output_root")

trained_model = keras.models.load_model(f"{trained_model_dir}/{trained_model_name}")
trained_model.summary()
class_names = []
for class_name in os.listdir(train_dir):
  class_names.append(class_name)

 # Testing images
def test_classification(model, folder_dir, IMAGE_SIZE):
  output_list = []
  conf_list = []
  class_list = []
  filenames_list = []
  #img_dir = "/content/drive/MyDrive/Agroml/Hagai/Hagai1/testC"
  for count,filename in enumerate(os.listdir(folder_dir)):
    if filename.endswith("mp4"):
      continue
    else:
      image_path = f'{folder_dir}/{filename}'
      new_img = tf.keras.preprocessing.image.load_img(image_path, target_size=(IMAGE_SIZE, IMAGE_SIZE))
      img = tf.keras.preprocessing.image.img_to_array(new_img)
      img = np.expand_dims(img, axis=0)
      #print("Following is our prediction:")
      prediction = model.predict(img)
      d = prediction.flatten()
      j = d.max()
      for index,item in enumerate(d):
          if item == j:
              class_name = class_names[index]
      confidence = round(100 * j, 3)
      conf_list.append(confidence)
      class_list.append(class_name)
      filenames_list.append(filename)
  output_list.append(filenames_list)
  output_list.append(class_list)
  output_list.append(conf_list)

  return output_list

# saving corresponded classification to every leaf
leaf_results = []
for leaf_folder in os.listdir(images_dir):
  leaf_result = test_classification(trained_model, f"{images_dir}/{leaf_folder}", 224)
  leaf_results.append(leaf_result)

for i, image in enumerate(os.listdir(images_dir)):
  if not image.endswith("jpg"):
    continue
  else:
    original_img_dir = f"{original_img_dir_root}/{image}"
    img_to_be_shown = cv2.imread(f"{original_img_dir}")
    image_name_only = os.path.splitext(image)[0]
    labels = pd.read_csv(f"{output_root}/{image_name_only}.txt", sep = " ", header = None)
    labels['leaf_class'] = leaf_results[i][1]
    labels['detection_confidence'] = leaf_results[i][2]
    # read input image from your computer - needed for torch 
    img = read_image(f"{original_img_dir}")

    b_boxes = []
    b_box_labels = []
    detection_indexes = [] 

    for i in range(len(labels)):
      if re.findall('healthy', labels['leaf_class'][i]) or re.findall('NonPlant', labels['leaf_class'][i]): 
        continue
      else: 
        detection_indexes.append(i) 
        x_center = labels[1][i]
        y_center = labels[2][i]
        x_l = labels[3][i]*img_to_be_shown.shape[1]
        y_l = labels[4][i]*img_to_be_shown.shape[0]
        x_c_img = x_center*(img_to_be_shown.shape[1])
        y_c_img = y_center*(img_to_be_shown.shape[0])
        x_start = int(x_c_img - x_l/2)
        x_end = int(x_c_img + x_l/2)
        y_start = int(y_c_img - y_l/2)
        y_end = int(y_c_img + y_l/2)
        # bounding box are xmin, ymin, xmax, ymax
        current_box = [x_start, y_start, x_end, y_end]
        b_boxes.append(current_box)
        b_box_labels.append(labels['leaf_class'][i] + " " + str(labels['detection_confidence'][i])+"%")

    b_boxes = torch.tensor(b_boxes, dtype=torch.int)
      
      
    # draw bounding box and fill color
    img = draw_bounding_boxes(img, b_boxes, width=5,
                              colors="white",
                              labels = b_box_labels ,
                              fill=False)
      
    # transform this image to PIL image
    img = torchvision.transforms.ToPILImage()(img)
    
    # save image to output
    image_output_path = "/content/drive/MyDrive/AgroDL/AgroDL_Data/Output/Leaf_classifications"
    img.save(f"{image_output_path}/{image}")
    # create corresponding csv file
    labels.drop([0,3,4], inplace=True, axis=1)
    labels = labels.rename(columns={1:"X", 2:"Y"})
    labels = labels.loc[detection_indexes]
    labels = labels.reset_index(drop=True)
    labels.to_csv(f'{image_output_path}/{image_name_only}.csv', index=None)

# delete sub folders from input
shutil.rmtree(f"{original_img_dir_root}/detected_images")
shutil.rmtree(f"{original_img_dir_root}/extracted_leafs")
    

    

    
