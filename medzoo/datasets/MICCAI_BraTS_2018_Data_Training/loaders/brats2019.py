import glob
import os

import numpy as np
import torch

import medzoo.common.augment3D as augment3D
import medzoo.utils as utils
from medzoo.common.medloaders import medical_image_process as img_loader
from medzoo.common.medloaders.medical_loader_utils import create_sub_volumes
from medzoo.datasets.dataset import MedzooDataset


class MICCAIBraTS2019(MedzooDataset):
    """
    Code for reading the infant brain MICCAIBraTS2019 challenge
    """

    def __init__(self, config, mode, dataset_path='./datasets'):
        """

        Args:
            mode: 'train','val','test'
            dataset_path: root dataset folder
            crop_dim: subvolume tuple
            split_idx: 1 to 10 values
            samples: number of sub-volumes that you want to create
        """
        super().__init__(config, mode, dataset_path)

        self.training_path = self.root_path + '/brats2019/MICCAI_BraTS_2019_Data_Training/'
        self.testing_path = self.root_path + '/brats2019/MICCAI_BraTS_2019_Data_Validation/'
        self.full_vol_dim = (240, 240, 155)  # slice, width, height

        self.list = []

        self.full_volume = None

        self.save_name = self.root_path + '/brats2019/brats2019-list-' + self.mode + '-samples-' + str(self.samples) + '.txt'

        self.sub_vol_path = self.root_path + '/brats2019/MICCAI_BraTS_2019_Data_Training/generated/' + mode + self.subvol + '/'

        self.split_idx = 260

        self.list_IDsT1 = None
        self.list_IDsT1ce = None
        self.list_IDsT2 = None
        self.list_IDsFlair = None
        self.labels = None

        self.load_dataset()


    def augment(self):
        self.transform = augment3D.RandomChoice(
            transforms=[augment3D.GaussianNoise(mean=0, std=0.01), augment3D.RandomFlip(),
                        augment3D.ElasticTransform()], p=0.5)
    def load(self):
        ## load pre-generated data
        self.list = utils.load_list(self.save_name)
        self.list_IDsT1 = sorted(glob.glob(os.path.join(self.training_path, '*GG/*/*t1.nii.gz')))
        self.affine = img_loader.load_affine_matrix(self.list_IDsT1[0])


    def preprocess(self):
        utils.make_dirs(self.sub_vol_path)

        self.list_IDsT1 = sorted(glob.glob(os.path.join(self.training_path, '*GG/*/*t1.nii.gz')))
        self.list_IDsT1ce = sorted(glob.glob(os.path.join(self.training_path, '*GG/*/*t1ce.nii.gz')))
        self.list_IDsT2 = sorted(glob.glob(os.path.join(self.training_path, '*GG/*/*t2.nii.gz')))
        self.list_IDsFlair = sorted(glob.glob(os.path.join(self.training_path, '*GG/*/*_flair.nii.gz')))
        self.labels = sorted(glob.glob(os.path.join(self.training_path, '*GG/*/*_seg.nii.gz')))
        self.list_IDsT1, self.list_IDsT1ce, self.list_IDsT2, self.list_IDsFlair, self.labels = utils.shuffle_lists(self.list_IDsT1, self.list_IDsT1ce,
                                                                                          self.list_IDsT2,
                                                                                          self.list_IDsFlair, self.labels,
                                                                                          seed=17)
        self.affine = img_loader.load_affine_matrix(self.list_IDsT1[0])

    def preprocess_train(self):
        print('Brats2019, Total data:', len(self.list_IDsT1))
        self.list_IDsT1 = self.list_IDsT1[:self.split_idx]
        self.list_IDsT1ce = self.list_IDsT1ce[:self.split_idx]
        self.list_IDsT2 = self.list_IDsT2[:self.split_idx]
        self.list_IDsFlair = self.list_IDsFlair[:self.split_idx]
        self.labels = self.labels[:self.split_idx]
        self.list = create_sub_volumes(self.list_IDsT1, self.list_IDsT1ce, self.list_IDsT2, self.list_IDsFlair, self.labels,
                                       dataset_name="brats2019", mode=self.mode, samples=self.samples,
                                       full_vol_dim=self.full_vol_dim, crop_size=self.crop_size,
                                       sub_vol_path=self.sub_vol_path, th_percent=self.threshold)

    def preprocess_val(self):
        list_IDsT1 = self.list_IDsT1[self.split_idx:]
        list_IDsT1ce = self.list_IDsT1ce[self.split_idx:]
        list_IDsT2 = self.list_IDsT2[self.split_idx:]
        list_IDsFlair = self.list_IDsFlair[self.split_idx:]
        labels = self.labels[self.split_idx:]
        self.list = create_sub_volumes(list_IDsT1, list_IDsT1ce, list_IDsT2, list_IDsFlair, labels,
                                       dataset_name="brats2019", mode=self.mode, samples=self.samples,
                                       full_vol_dim=self.full_vol_dim, crop_size=self.crop_size,
                                       sub_vol_path=self.sub_vol_path, th_percent=self.threshold)
    def preprocess_test(self):
        self.list_IDsT1 = sorted(glob.glob(os.path.join(self.testing_path, '*GG/*/*t1.nii.gz')))
        self.list_IDsT1ce = sorted(glob.glob(os.path.join(self.testing_path, '*GG/*/*t1ce.nii.gz')))
        self.list_IDsT2 = sorted(glob.glob(os.path.join(self.testing_path, '*GG/*/*t2.nii.gz')))
        self.list_IDsFlair = sorted(glob.glob(os.path.join(self.testing_path, '*GG/*/*_flair.nii.gz')))
        self.labels = None
        # Todo inference code here

    def save(self):
        utils.save_list(self.save_name, self.list)

    def __len__(self):
        return len(self.list)

    def __getitem__(self, index):
        f_t1, f_t1ce, f_t2, f_flair, f_seg = self.list[index]
        img_t1, img_t1ce, img_t2, img_flair, img_seg = np.load(f_t1), np.load(f_t1ce), np.load(f_t2), np.load(
            f_flair), np.load(f_seg)
        if self.mode == 'train' and self.augmentation:
            [img_t1, img_t1ce, img_t2, img_flair], img_seg = self.transform([img_t1, img_t1ce, img_t2, img_flair],
                                                                            img_seg)

            return torch.FloatTensor(img_t1.copy()).unsqueeze(0), torch.FloatTensor(img_t1ce.copy()).unsqueeze(
                0), torch.FloatTensor(img_t2.copy()).unsqueeze(0), torch.FloatTensor(img_flair.copy()).unsqueeze(
                0), torch.FloatTensor(img_seg.copy())

        return img_t1, img_t1ce, img_t2, img_flair, img_seg