import sys
import argparse
import logging
import traceback
import os
import pathlib
import numpy as np

import torch

from skimage.morphology import remove_small_objects
from skimage.io import imsave
from aicsimageio import AICSImage #, omeTifWriter
from aicsimageprocessing import resize

from aicsmlsegment.utils import load_config, load_single_image, input_normalization, image_normalization, simple_norm, get_logger, post_processing_2d
from aicsmlsegment.model_utils import build_model, load_checkpoint, model_inference, apply_on_image, apply_on_full_image, model_inference_full_img

def dl_inference(
    model_name = 'deeplabV3plus',
    model_path = '/allen/aics/assay-dev/users/Hyeonwoo/code/develop/trained_models/deeplab/deeplabV3plus_cont/checkpoint_epoch_125.pytorch',
    InputDir = '/allen/aics/assay-dev/computational/data/cardio_wga_2d/segmentations/raw',
    OutputDir = '/allen/aics/assay-dev/users/Hyeonwoo/scratch_data/cardio_seg_test',
    DataType = '.tif'
):

    # model structure and input 
    config = dict()

    # model configureation
    nested = {}; nested['name'] = model_name; config['model'] = nested
    config['model_path'] = model_path
    config['nchannel'] = 1 # number of input channels to the model
    config['nclass'] = [2] # number of output channels
    config['OutputCh'] = [0, 1] # the channel to extract from output tensors
    config['size_in'] = [0] # input patch size given to the network (adapt to fit in your GPU memory, generally bigger patches are better)
    config['size_out'] = [0] # prediction patch size from the network (change according to input size)

    # inference setting
    config['OutputDir'] = OutputDir # the path to output folder
    config['InputCh'] = [1] # the index of the input channel
    config['Normalization'] = 19 # the method to normalize your data
    config['Threshold'] = 0.8 # the threshold to be applied on your data
    config['RuntimeAug'] = False # whether to use run time augmentation (may improve the accuracy, but takes much longer to run)
    config['device'] = 'cuda:0' # it can be 'cpu' if gpu is not available

    # input setting (Folder)
    nested = {}
    nested['name'] = 'folder'
    nested['DataType'] = DataType
    nested['InputDir'] = InputDir # paths to the file
    nested['timelapse'] = False # is this file a timelapse image
    nested['apply_on_full_image'] = True # whether apply on full image or not
    nested['post_process'] = True # Use post processing step in utils.
    config['mode'] = nested

    # declare the model
    model = build_model(config)

    # load the trained model instance
    model_path = config['model_path']
    print(f'Loading model from {model_path}...')
    load_checkpoint(model_path, model)

    # extract the parameters for running the model inference
    args_inference=lambda:None
    args_inference.size_in = config['size_in']
    args_inference.size_out = config['size_out']
    args_inference.OutputCh = config['OutputCh']
    args_inference.nclass =  config['nclass'] 

    if config['RuntimeAug'] <=0:
        args_inference.RuntimeAug = False
    else:
        args_inference.RuntimeAug = True
    # run
    inf_config = config['mode']
    # file mode is not supported yet!!!
    if inf_config['name'] == 'file':
        print('file mode is not supported yet!!!')
        # fn = inf_config['InputFile']
        # data_reader = AICSImage(fn)
        # img0 = data_reader.data

        # if inf_config['timelapse']:
        #     assert img0.shape[0]>1

        #     for tt in range(img0.shape[0]):
        #         # Assume:  dimensions = TCZYX
        #         img = img0[tt, config['InputCh'],:,:,:].astype(float)
        #         img = image_normalization(img, config['Normalization'])

        #         if len(config['ResizeRatio'])>0:
        #             img = resize(img, (1, config['ResizeRatio'][0], config['ResizeRatio'][1], config['ResizeRatio'][2]), method='cubic')
        #             for ch_idx in range(img.shape[0]):
        #                 struct_img = img[ch_idx,:,:,:]
        #                 struct_img = (struct_img - struct_img.min())/(struct_img.max() - struct_img.min())
        #                 img[ch_idx,:,:,:] = struct_img

        #         # apply the model
        #         output_img = apply_on_image(model, img, model.final_activation, args_inference)

        #         # extract the result and write the output
        #         if len(config['OutputCh']) == 2:
        #             out = output_img[0]
        #             out = (out - out.min()) / (out.max()-out.min())
        #             if len(config['ResizeRatio'])>0:
        #                 out = resize(out, (1.0, 1/config['ResizeRatio'][0], 1/config['ResizeRatio'][1], 1/config['ResizeRatio'][2]), method='cubic')
        #             out = out.astype(np.float32)
        #             if config['Threshold']>0:
        #                 out = out > config['Threshold']
        #                 out = out.astype(np.uint8)
        #                 out[out>0]=255
        #             imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem + '_T_'+ f'{tt:03}' +'_struct_segmentation.tiff', out)
        #         else:
        #             for ch_idx in range(len(config['OutputCh'])//2):
        #                 out = output_img[ch_idx]
        #                 out = (out - out.min()) / (out.max()-out.min())
        #                 if len(config['ResizeRatio'])>0:
        #                     out = resize(out, (1.0, 1/config['ResizeRatio'][0], 1/config['ResizeRatio'][1], 1/config['ResizeRatio'][2]), method='cubic')
        #                 out = out.astype(np.float32)
        #                 if config['Threshold']>0:
        #                     out = out > config['Threshold']
        #                     out = out.astype(np.uint8)
        #                     out[out>0]=255
        #                 imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem + '_T_'+ f'{tt:03}' +'_seg_'+ str(config['OutputCh'][2*ch_idx])+'.tiff',out)
        # else:
        #     # If the model is 2D model
        #     if len(config['nclass']) == 1:
        #         if img0.shape[3] == 1: # when it is single channel
        #             img = img0[0,0,0,0,:,:]
        #         else:
        #             img = img0[0,0,0,config['InputCh'],:,:]
        #         img = image_normalization(img, config['Normalization'])
        #         print(f'processing one image of size {img.shape}')

        #         output_img = model_inference(model, img, model.final_activation, args_inference)

        #         out = output_img[0] > config['Threshold']
        #         out = out.astype(np.uint8)
        #         out[out>0]=255
        #         imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem +'_struct_segmentation.tiff',out)
        #         print(f'Image {fn} has been segmented')
        #     else:
        #         img = img0[0,:,:,:,:].astype(float)
        #         print(f'processing one image of size {img.shape}')
        #         if img.shape[1] < img.shape[0]:
        #             img = np.transpose(img,(1,0,2,3))
        #         img = img[config['InputCh'],:,:,:]
        #         # # img = image_normalization(img, config['Normalization'])

        #         if len(config['ResizeRatio'])>0:
        #             img = resize(img, (1, config['ResizeRatio'][0], config['ResizeRatio'][1], config['ResizeRatio'][2]), method='cubic')
        #             for ch_idx in range(img.shape[0]):
        #                 struct_img = img[ch_idx,:,:,:] # note that struct_img is only a view of img, so changes made on struct_img also affects img
        #                 struct_img = (struct_img - struct_img.min())/(struct_img.max() - struct_img.min())
        #                 img[ch_idx,:,:,:] = struct_img

        #         # apply the model
        #         output_img = apply_on_image(model, img, model.final_activation, args_inference)

        #         # extract the result and write the output
        #         if len(config['OutputCh']) == 2:
        #             out = output_img[0] 
        #             out = (out - out.min()) / (out.max()-out.min())
        #             if len(config['ResizeRatio'])>0:
        #                 out = resize(out, (1.0, 1/config['ResizeRatio'][0], 1/config['ResizeRatio'][1], 1/config['ResizeRatio'][2]), method='cubic')
        #             out = out.astype(np.float32)
        #             if config['Threshold']>0:
        #                 out = out > config['Threshold']
        #                 out = out.astype(np.uint8)
        #                 out[out>0]=255
        #             imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem +'_struct_segmentation.tiff', out)
        #         else:
        #             for ch_idx in range(len(config['OutputCh'])//2):
        #                 out = output_img[ch_idx] 
        #                 out = (out - out.min()) / (out.max()-out.min())
        #                 if len(config['ResizeRatio'])>0:
        #                     out = resize(out, (1.0, 1/config['ResizeRatio'][0], 1/config['ResizeRatio'][1], 1/config['ResizeRatio'][2]), method='cubic')
        #                 out = out.astype(np.float32)
        #                 if config['Threshold']>0:
        #                     out = out > config['Threshold']
        #                     out = out.astype(np.uint8)
        #                     out[out>0]=255
        #                 imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem +'_seg_'+ str(config['OutputCh'][2*ch_idx])+'.tiff', out)
        #         print(f'Image {fn} has been segmented')

    elif inf_config['name'] == 'folder':
        from glob import glob
        filenames = glob(inf_config['InputDir'] + '/*' + inf_config['DataType'])
        filenames.sort()
        print('files to be processed:')
        print(filenames)

        for _, fn in enumerate(filenames):

            # load data
            data_reader = AICSImage(fn)
            img0 = data_reader.data

            # If the model is 2D model run this script. This is for temp
            if len(config['nclass']) == 1:
                if img0.shape[3] == 1: # when it is single channel
                    img = img0[0,0,0,0,:,:]
                else:
                    img = img0[0,0,0,config['InputCh'][0],:,:]
                img = image_normalization(img, config['Normalization'])
                print(f'processing one image of size {img.shape}')
                
                # for full size testing
                if config['mode']['apply_on_full_image']:
                    output_img = apply_on_full_image(model, img, model.final_activation, args_inference)

                else:
                    output_img = model_inference(model, img, model.final_activation, args_inference)

                out = output_img[:,:,1] > config['Threshold']
                out = out.astype(np.uint8)
                out[out>0]=255
                if config["mode"]["post_process"]:
                    out = post_processing_2d(out).astype('uint8')
                else:
                    out.astype('uint8')
                imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem +'_struct_segmentation.tiff',out)
                print(f'Image {fn} has been segmented')
                continue
            
            # when image size is larger
            while len(img0.shape) > 5:
                img0 = np.squeeze(img0, axis = 0)

            img = img0[0,:,:,:,:].astype(float)
            if img.shape[1] < img.shape[0]:
                img = np.transpose(img,(1,0,2,3))

            img = img[config['InputCh'],:,:,:]
            
            # quick fix for each structure dual normalization
            # img = image_normalization(img, config['Normalization'])
            img = simple_norm(img, 2, 8)

            if len(img.shape) == 3:
                img = np.expand_dims(img, axis=0)
            
            # img1 = simple_norm(img, 2,8)
            # if len(img.shape) == 3:
            #     img1 = np.expand_dims(img1, axis=0)

            # import pdb; pdb.set_trace()
            # img = np.stack([img[0,:,:,:], img1[0,:,:,:]],axis=0)

            # if len(config['ResizeRatio'])>0:
            #     img = resize(img, (1, config['ResizeRatio'][0], config['ResizeRatio'][1], config['ResizeRatio'][2]), method='cubic')
                # for ch_idx in range(img.shape[0]):
                #     struct_img = img[ch_idx,:,:,:] # note that struct_img is only a view of img, so changes made on struct_img also affects img
                #     struct_img = (struct_img - struct_img.min())/(struct_img.max() - struct_img.min())
                #     img[ch_idx,:,:,:] = struct_img

            # apply the model
            # import pdb; pdb.set_trace()
            output_img = apply_on_image(model, img, model.final_activation, args_inference)

            # extract the result and write the output
            if len(config['OutputCh'])==2:
                if config['Threshold']<0:
                    out = output_img[0]
                    out = (out - out.min()) / (out.max()-out.min())
                    if len(config['ResizeRatio'])>0:
                        out = resize(out, (1.0, 1/config['ResizeRatio'][0], 1/config['ResizeRatio'][1], 1/config['ResizeRatio'][2]), method='cubic')
                    out = out.astype(np.float32)
                    out = (out - out.min()) / (out.max()-out.min())
                else:
                    out = remove_small_objects(output_img[0] > config['Threshold'], min_size=2, connectivity=1) 
                    out = out.astype(np.uint8)
                    out[out>0]=255
                imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem + '_struct_segmentation.tiff', out)
            else:
                for ch_idx in range(len(config['OutputCh'])//2):
                    if config['Threshold']<0:
                        out = output_img[ch_idx]
                        out = (out - out.min()) / (out.max()-out.min())
                        out = out.astype(np.float32)
                    else:
                        out = output_img[ch_idx] > config['Threshold']
                        out = out.astype(np.uint8)
                        out[out>0]=255
                    imsave(config['OutputDir'] + os.sep + pathlib.PurePosixPath(fn).stem + '_seg_'+ str(config['OutputCh'][2*ch_idx])+'.ome.tif', out)
            
            print(f'Image {fn} has been segmented')
