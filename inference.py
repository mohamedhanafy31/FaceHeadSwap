import logging
import os
import cv2
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF
import onnxruntime as ort
import pdb

from model.AlignModule.generator import FaceGenerator
from model.BlendModule.generator import Generator as Decoder
from model.AlignModule.config import Params as AlignParams
from model.BlendModule.config import Params as BlendParams 
from model.third.faceParsing.model import BiSeNet
from process.process_func import Process
from process.process_utils import *
from utils.utils import color_transfer2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


class Infer(Process):
    def __init__(self, align_path, blend_path, parsing_path, params_path, bfm_folder):
        logging.info("Initializing the Infer pipeline")
        Process.__init__(self, params_path, bfm_folder)
        
        align_params = AlignParams()
        blend_params = BlendParams()
        self.device = 'cpu'
        if torch.cuda.is_available():
            self.device = 'cuda'
        logging.info(f"Using device: {self.device}")
      
        logging.info("Initializing face parsing model (BiSeNet)")
        self.parsing = BiSeNet(n_classes=19).to(self.device)
        
        logging.info("Initializing face generator and blending decoder")
        self.netG = FaceGenerator(align_params).to(self.device)
        self.decoder = Decoder(blend_params).to(self.device)
        
        logging.info("Loading pretrained models")
        self.loadModel(align_path, blend_path, parsing_path)
        self.eval_model(self.netG, self.decoder, self.parsing)

        logging.info("Creating ONNX session for super resolution")
        self.ort_session_sr = ort.InferenceSession('app/HeadSwap/pretrained_models/sr_cf.onnx', providers=['CPUExecutionProvider'])

    def run(self, src_img_path_list, tgt_img_path_list, save_base, crop_align=False, cat=False):
        logging.info("Starting batch processing")
        os.makedirs(save_base, exist_ok=True)
        i = 0
        for src_img_path, tgt_img_path in zip(src_img_path_list, tgt_img_path_list):
            logging.info(f"Processing pair: {src_img_path} and {tgt_img_path}")
            gen = self.run_single(src_img_path, tgt_img_path, crop_align=crop_align, cat=cat)
            img_name = os.path.splitext(os.path.basename(src_img_path))[0] + '-' + \
                       os.path.splitext(os.path.basename(tgt_img_path))[0] + '.png'
            cv2.imwrite(os.path.join(save_base, img_name), gen)
            logging.info(f"Saved output: {os.path.join(save_base, img_name)}")
            print(f'\rProcessed {i:04d}', end='', flush=True)
            i += 1
        logging.info("Batch processing complete")

    def run_single(self, src_img_path, tgt_img_path, crop_align=False, cat=False):
        logging.info("Reading target image")
        tgt_img = cv2.imread(tgt_img_path)
        if tgt_img is None:
            logging.error("Failed to read target image")
            return None
        tgt_align = tgt_img.copy()
        
        logging.info("Preprocessing target image for alignment")
        tgt_align, info = self.preprocess_align(tgt_img)
        if tgt_align is None:
            logging.error("Preprocessing of target image failed")
            return None

        logging.info("Reading source image")
        src_img = cv2.imread(src_img_path)
        if src_img is None:
            logging.error("Failed to read source image")
            return None
        src_align = src_img
        if crop_align:
            logging.info("Applying cropping and alignment to source image")
            src_align, _ = self.preprocess_align(src_img, top_scale=0.55)
        
        logging.info("Preprocessing images for network input")
        src_inp = self.preprocess(src_align)
        tgt_inp = self.preprocess(tgt_align)

        logging.info("Calculating transformation parameters")
        tgt_params = self.get_params(cv2.resize(tgt_align, (256, 256)),
                                     info['rotated_lmk'] / 2.0).unsqueeze(0)
           
        logging.info("Performing forward pass through the network")
        gen = self.forward(src_inp, tgt_inp, tgt_params) 

        logging.info("Postprocessing generated image")
        gen = self.postprocess(gen[0])
        logging.info("Running super resolution")
        gen = self.run_sr(gen)
        mask = self.mask

        logging.info("Blending generated image with target image")
        RotateMatrix = info['im'][:2]
        mask = info['mask'][..., 0]
        rotate_gen = cv2.warpAffine(gen, RotateMatrix, (tgt_img.shape[1], tgt_img.shape[0]))
        mask = cv2.warpAffine(mask, RotateMatrix, (tgt_img.shape[1], tgt_img.shape[0])) * 1.0

        kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))
        mask = cv2.erode(mask * 1.0, kernel2)
        mask = cv2.blur(mask * 1.0, (15, 15), 0) / 255.0
        mask = np.clip(mask, 0, 1.0)[:, :, np.newaxis]

        final = rotate_gen * mask + tgt_img * (1 - mask)

        # Removed the concatenation block to ensure the final image contains only the swapped face.
        logging.info("run_single completed")
        return final
    
    def forward(self, xs, xt, params):
        logging.info("Starting forward pass computation")
        with torch.no_grad():
            xg = self.netG(
                F.adaptive_avg_pool2d(xs, 256),
                F.adaptive_avg_pool2d(xt, 256),
                params
            )['fake_image']
            logging.info("Generated initial fake image")
            xg = F.adaptive_avg_pool2d(xg, 512)
           
            M_a = self.parsing(self.preprocess_parsing(xg))
            M_t = self.parsing(self.preprocess_parsing(xt))
            
            M_a = self.postprocess_parsing(M_a)
            M_t = self.postprocess_parsing(M_t)
            logging.info("Postprocessed segmentation maps")
            
            xg_gray = TF.rgb_to_grayscale(xg, num_output_channels=1)
            fake = self.decoder(xg, xg_gray, xt, M_a, M_t, xt, train=False)
            logging.info("Decoded blended image")
            
            gen_mask = self.parsing(self.preprocess_parsing(fake))
            gen_mask = self.postprocess_parsing(gen_mask)
            gen_mask = gen_mask[0][0].cpu().numpy()
            mask_t = M_t[0][0].cpu().numpy()
            mask = np.zeros_like(gen_mask)
            for i in [1,2,3,4,5,6,7,8,9,10,11,12,13,17,18]:
                mask[gen_mask == i] = 1.0
                mask[mask_t == i] = 1.0
            
            self.mask = mask
            logging.info("Forward pass complete")
        return fake
    
    def run_sr(self, input_np):
        logging.info("Converting image for super resolution")
        input_np = cv2.cvtColor(input_np, cv2.COLOR_BGR2RGB)
        input_np = input_np.transpose((2, 0, 1))
        input_np = np.array(input_np[np.newaxis, :])
        logging.info("Running ONNX super resolution model")
        outputs_onnx = self.ort_session_sr.run(None, {'input_image': input_np.astype(np.uint8)})
        out_put_onnx = outputs_onnx[0]
        outimg = out_put_onnx[0, ...].transpose(1, 2, 0)
        outimg = cv2.cvtColor(outimg, cv2.COLOR_BGR2RGB)
        logging.info("Super resolution complete")
        return outimg

    def loadModel(self, align_path, blend_path, parsing_path):
        logging.info("Loading alignment generator model from: " + align_path)
        ckpt = torch.load(align_path, map_location=lambda storage, loc: storage)
        self.netG.load_state_dict(ckpt['net_G_ema'])

        logging.info("Loading blending decoder model from: " + blend_path)
        ckpt = torch.load(blend_path, map_location=lambda storage, loc: storage)
        self.decoder.load_state_dict(ckpt['G'], strict=False)

        logging.info("Loading face parsing model from: " + parsing_path)
        self.parsing.load_state_dict(torch.load(parsing_path))
        logging.info("All models loaded successfully")
    
    def eval_model(self, *args):
        logging.info("Setting models to evaluation mode")
        for arg in args:
            arg.eval()


if __name__ == "__main__":
    logging.info("Starting inference process from __main__")
    model = Infer(
        'pretrained_models/epoch_00190_iteration_000400000_checkpoint.pt',
        'pretrained_models/Blender-401-00012900.pth',
        'pretrained_models/parsing.pth',
        'pretrained_models/epoch_20.pth',
        'pretrained_models/BFM'
    )

    # Example usage with image paths:
    src_paths = ['../img2.jpg']
    tgt_paths = ['../img1.jpg']
    
    model.run(src_paths, tgt_paths, save_base='res-1125', crop_align=True, cat=False)
    
    logging.info("Inference process complete")
