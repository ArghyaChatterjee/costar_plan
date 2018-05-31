from __future__ import print_function

import numpy as np
import os

from .image import *

class NpzGeneratorDataset(object):
    '''
    Get the list of objects from a folder full of NP arrays.
    '''

    def __init__(self, name, split=0.1, preload=False):
        '''
        Set name of directory to load files from

        Parameters:
        -----------
        name: the directory
        split: portion of the data files reserved for testing/validation
        preload: load all files into memory when starting up
        '''
        self.name = name
        self.split = split
        self.train = []
        self.test = []
        self.preload = preload
        self.preload_cache = {}
        self.load_jpeg = False

    def write(self, *args, **kwargs):
        raise NotImplementedError('this dataset does not save things')

    def load(self, success_only=False):
        '''
        Read the file; get the list of acceptable entries; split into train and
        test sets.
        '''
        files = os.listdir(self.name)
        files.sort()
        sample = {}
        i = 0
        acceptable_files = []
        for f in files:
            if f[0] == '.':
                continue

            if success_only and 'success' not in f:
                continue

            if i < 1:
                fsample = self._load(os.path.join(self.name, f))
                for key, value in fsample.items():

                    if self.load_jpeg and key in ["image", "goal_image"]:
                        value = ConvertImageListToNumpy(value)

                    if value.shape[0] == 0:
                        sample = {}
                        continue

                    if key not in sample:
                        sample[key] = value
                    else:
                        # Note: do not collect multiple samples anymore; this
                        # hould never be reached
                        sample[key] = np.concatenate([sample[key], value], axis=0)
            i += 1
            acceptable_files.append(f)

        idx = np.array(range(len(acceptable_files)))
        length = max(1, int(self.split*len(acceptable_files)))
        print("---------------------------------------------")
        print("Loaded data.")
        print("# Total examples:", len(acceptable_files))
        print("# Validation examples:", length)
        print("---------------------------------------------")
        self.test = [acceptable_files[i] for i in idx[:length]]
        self.train = [acceptable_files[i] for i in idx[length:]]
        for i, filename in enumerate(self.test):
            #print("%d:"%(i+1), filename)
            if filename in self.train:
                raise RuntimeError('error with test/train setup! ' + \
                                   filename + ' in training!')
        np.random.shuffle(self.test)
        np.random.shuffle(self.train)

        if self.preload:
            print("Preloading all files...")
            for f in self.test + self.train:
                nm = os.path.join(self.name, f)
                self.preload_cache[nm] = self._load(nm)

        return sample

    def sampleTrainFilename(self):
        return os.path.join(self.name,
                self.train[np.random.randint(len(self.train))])

    def sampleTestFilename(self):
        return os.path.join(self.name,
                self.test[np.random.randint(len(self.test))])

    def testFiles(self):
        return self.test

    def trainFiles(self):
        return self.train

    def numTest(self):
        return len(self.test)

    def loadTest(self, i):
        if i > len(self.test):
            raise RuntimeError('index %d greater than number of files'%i)
        filename = self.test[i]
        success = 'success' in filename
        nm = os.path.join(self.name, filename)
        if nm in self.preload_cache:
            return self.preload_cache[nm], success
        else:
            return self._load(nm), success

    def sampleTrain(self):
        filename = self.sampleTrainFilename()
        if filename in self.preload_cache:
            sample = self.preload_cache[filename]
        else:
            try:
                sample = self._load(filename)
            except Exception as e:
                raise RuntimeError("Could not load file " + filename + ": "
                        + str(e))
        return sample, filename

    def sampleTest(self):
        filename = self.sampleTestFilename()
        if filename in self.preload_cache:
            sample = self.preload_cache[filename]
        else:
            try:
                sample = self._load(filename)
            except Exception as e:
                raise RuntimeError("Could not load file " + filename + ": "
                        + str(e))
        return sample, filename

    def _load(self, filename):
        return np.load(filename)

    def loadFile(self, filename):
        full_filename = os.path.join(self.name, filename)
        return self._load(full_filename)

