"""
Created on Fri Dec 16 01:24:11 2017

@author: Utku Ozbulak - github.com/utkuozbulak
"""
import os
import numpy as np
import cv2

import torch
from torch import nn
from torch.autograd import Variable
# from torch.autograd.gradcheck import zero_gradients  # See processed_image.grad = None

from misc_functions import preprocess_image, recreate_image, get_params
from torchvision import models

class FastGradientSignTargeted():
    """
        Fast gradient sign untargeted adversarial attack, maximizes the target class activation
        with iterative grad sign updates
    """
    def __init__(self, model, alpha):
        self.model = model
        self.model.eval()
        # Movement multiplier per iteration
        self.alpha = alpha
        # Create the folder to export images if not exists
        if not os.path.exists('../generated'):
            os.makedirs('../generated')

    def generate(self, original_image, org_class, target_class, image_name):
        # I honestly dont know a better way to create a variable with specific value
        # Targeting the specific class
        im_label_as_var = Variable(torch.from_numpy(np.asarray([target_class])))
        # Define loss functions
        ce_loss = nn.CrossEntropyLoss()
        # Process image
        processed_image = preprocess_image(original_image)
        # Start iteration
        for i in range(10):
            #print('Iteration:', str(i))
            # zero_gradients(x)
            # Zero out previous gradients
            # Can also use zero_gradients(x)
            processed_image.grad = None
            # Forward pass
            out = self.model(processed_image)
            # Calculate CE loss
            pred_loss = ce_loss(out, im_label_as_var)
            # Do backward pass
            pred_loss.backward()
            # Create Noise
            # Here, processed_image.grad.data is also the same thing is the backward gradient from
            # the first layer, can use that with hooks as well
            adv_noise = self.alpha * torch.sign(processed_image.grad.data)
            # Add noise to processed image
            processed_image.data = processed_image.data - adv_noise

            # Confirming if the image is indeed adversarial with added noise
            # This is necessary (for some cases) because when we recreate image
            # the values become integers between 1 and 255 and sometimes the adversariality
            # is lost in the recreation process

            # Generate confirmation image
            recreated_image = recreate_image(processed_image)
            # Process confirmation image
            prep_confirmation_image = preprocess_image(recreated_image)
            # Forward pass
            confirmation_out = self.model(prep_confirmation_image)
            # Get prediction
            _, confirmation_prediction = confirmation_out.data.max(1)
            # Get Probability
            confirmation_confidence = \
                nn.functional.softmax(confirmation_out)[0][confirmation_prediction].data.numpy()[0]
            # Convert tensor to int
            confirmation_prediction = confirmation_prediction.numpy()[0]
            if (i < 9) & (confirmation_confidence < 0.5):
                continue
            # Check if the prediction is different than the original
            if confirmation_prediction == target_class:
                # print('Original image was predicted as:', org_class,
                #       'with adversarial noise converted to:', confirmation_prediction,
                #       'and predicted with confidence of:', confirmation_confidence)
                # Create the image for noise as: Original image - generated image
                # noise_image = original_image - recreated_image
                # cv2.imwrite('../generated_target/targeted_adv_noise_from_' + str(org_class) + '_to_' +
                #             str(confirmation_prediction) + '.jpg', noise_image)
                # Write image
                # cv2.imwrite('../generated_target/targeted_adv_img_from_' + str(org_class) + '_to_' +
                #             str(confirmation_prediction) + '.jpg', recreated_image)
                cv2.imwrite('./generated/adv_' + image_name, recreated_image)
                gampicpath = './generated/adv_' + image_name
                break

        return gampicpath

def generate_tar_ad_sample(img_path, img_label):
    """
    Args Type: str, int

    Result path: '../generated/adv_image_name'
    """
    #print(1)
    pretrained_model = models.resnet18(pretrained=True)
    FGS_untargeted = FastGradientSignTargeted(pretrained_model, 0.01)
    original_image, prep_img, org_class = get_params(img_path, img_label)
    #print(type(original_image), type(prep_img), type(org_class))
    target_class = org_class + 100
    if(target_class > 999):
        target_class = target_class % 1000
    
    img_name = img_path.split('/')[-1]
    #print(img_name)
    gampic = FGS_untargeted.generate(original_image, org_class ,target_class, img_name)
    #print(gampic)
    return gampic
