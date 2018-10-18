import os
import numpy as np


class FeatureReader:
    def __init__(self, base_path, channel_first,
                 ndim=None, max_bboxes=None, image_feature=None):
        """Feature Reader class for reading features.

        Note: Deprecation: ndim and image_feature will be deprecated later
        and the format will be standardize using features from detectron.

        Parameters
        ----------
        ndim : int
            Number of expected dimensions in features
        channel_first : bool
            CHW vs HWC
        max_bboxes : int
            Number of maximum bboxes to keep
        image_feature : np.ndarray
            A sample feature used for figuring out type

        Returns
        -------
        type
            Description of returned object.

        """
        self.base_path = base_path
        if ndim is None:
            if image_feature is not None:
                ndim = image_feature.ndim
        self.feat_reader = None
        self.channel_first = channel_first
        self.max_bboxes = max_bboxes
        self.ndim = ndim
        self.image_feature = image_feature

    def _init_reader(self):
        if self.ndim == 2 or self.ndim == 0:
            if self.max_bboxes is None:
                self.feat_reader = FasterRCNNFeatureReader()
            else:
                if isinstance(self.image_feature.item(0), dict):
                    self.feat_reader = \
                        PaddedFeatureRCNNWithBBoxesFeatureReader(
                            self.max_bboxes
                        )
                else:
                    self.feat_reader = \
                        PaddedFasterRCNNFeatureReader(self.max_bboxes)
        elif self.ndim == 3 and not self.channel_first:
            self.feat_reader = Dim3FeatureReader()
        elif self.ndim == 4 and self.channel_first:
            self.feat_reader = CHWFeatureReader()
        elif self.ndim == 4 and not self.channel_first:
            self.feat_reader = HWCFeatureReader()
        else:
            raise TypeError("unkown image feature format")

    def read(self, image_feat_path):
        if not image_feat_path.endswith("npy"):
            return None
        image_feat_path = os.path.join(self.base_path, image_feat_path)

        if self.feat_reader is None:
            if self.ndim is None:
                feat = np.load(image_feat_path)
                self.ndim = feat.ndim
            self._init_reader()

        return self.feat_reader(image_feat_path)


class FasterRCNNFeatureReader:
    def read(self, image_feat_path):
        return np.load(image_feat_path)


class CHWFeatureReader:
    def read(self, image_feat_path):
        feat = np.load(image_feat_path)
        assert (feat.shape[0] == 1), "batch is not 1"
        feat = feat.squeeze(0)
        return feat


class Dim3FeatureReader:
    def read(self, image_feat_path):
        tmp = np.load(image_feat_path)
        _, _, c_dim = tmp.shape
        image_feature = np.reshape(tmp, (-1, c_dim))
        return image_feature


class HWCFeatureReader:
    def read(self, image_feat_path):
        tmp = np.load(image_feat_path)
        assert (tmp.shape[0] == 1), "batch is not 1"
        _, _, _, c_dim = tmp.shape
        image_feature = np.reshape(tmp, (-1, c_dim))
        return image_feature


class PaddedFasterRCNNFeatureReader:
    def __init__(self, max_loc):
        self.max_loc = max_loc

    def read(self, image_feat_path):
        image_feature = np.load(image_feat_path)
        image_loc, image_dim = image_feature.shape
        tmp_image_feat = np.zeros((self.max_loc, image_dim), dtype=np.float32)
        tmp_image_feat[0:image_loc, ] = image_feature
        image_feature = tmp_image_feat
        return (image_feature, image_loc)


class PaddedFeatureRCNNWithBBoxesFeatureReader:
    def __init__(self, max_loc):
        self.max_loc = max_loc

    def read(self, image_feat_path):
        image_feat_bbox = np.load(image_feat_path)
        image_boxes = image_feat_bbox.item().get('image_bboxes')
        tmp_image_feat = image_feat_bbox.item().get('image_feature')
        image_loc, image_dim = tmp_image_feat.shape
        tmp_image_feat_2 = np.zeros((self.max_loc, image_dim),
                                    dtype=np.float32)
        tmp_image_feat_2[0:image_loc, ] = tmp_image_feat
        tmp_image_box = np.zeros((self.max_loc, 4), dtype=np.int32)
        tmp_image_box[0:image_loc] = image_boxes

        return (tmp_image_feat_2, image_loc, tmp_image_box)