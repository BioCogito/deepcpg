from __future__ import division
from __future__ import print_function

from collections import OrderedDict
import os

import h5py as h5
import numpy as np
from numpy import testing as npt
import six
from six.moves import range

from deepcpg.data import hdf


def test_hnames_to_names():
    hnames = OrderedDict.fromkeys(['a', 'b'])
    names = hdf.hnames_to_names(hnames)
    assert names == ['a', 'b']

    hnames = OrderedDict()
    hnames['a'] = ['a1', 'a2']
    hnames['b'] = ['b1', 'b2']
    names = hdf.hnames_to_names(hnames)
    assert names == ['a/a1', 'a/a2', 'b/b1', 'b/b2']

    hnames = OrderedDict()
    hnames['a'] = 'a1'
    hnames['b'] = ['b1', 'b2']
    hnames['c'] = None
    names = hdf.hnames_to_names(hnames)
    assert names == ['a/a1', 'b/b1', 'b/b2', 'c']


class TestReader(object):

    def setup(self):
        self.data_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '../../integration_tests/data/data/')
        self.data_files = [
            os.path.join(self.data_path, 'c18_000000-005000.h5'),
            os.path.join(self.data_path, 'c18_005000-008712.h5'),
            os.path.join(self.data_path, 'c19_000000-005000.h5'),
            os.path.join(self.data_path, 'c19_005000-008311.h5')
        ]

    def test_reader(self):
        names = ['pos', 'chromo', '/outputs/cpg/BS27_4_SER']
        data_files = [self.data_files[0], self.data_files[-1]]
        batch_size = 15
        reader = hdf.reader(data_files,
                            names,
                            batch_size=batch_size,
                            loop=False,
                            shuffle=False)
        data = next(reader)
        assert np.all(data['chromo'][:5] == b'18')
        npt.assert_equal(data['pos'][:5],
                         [3000023, 3000086, 3000092, 3000103, 3000163])
        npt.assert_equal(data['/outputs/cpg/BS27_4_SER'][:5],
                         [1, 1, 1, -1, 0])

        nb_smaller = 0
        for data in reader:
            size = len(data['pos'])
            assert size <= batch_size
            if size < batch_size:
                assert nb_smaller == 0
                nb_smaller += 1
            else:
                nb_smaller = 0

        assert np.all(data['chromo'][-5:] == b'19')
        npt.assert_equal(data['pos'][-5:],
                         [4447803, 4447814, 4447818, 4447821, 4447847])
        npt.assert_equal(data['/outputs/cpg/BS27_4_SER'][-5:],
                         [1, 1, 1, 1, 1])

    def test_read(self):
        data_files = [self.data_files[0], self.data_files[-1]]
        names = ['pos', 'chromo', '/outputs/cpg/BS27_4_SER']
        data = hdf.read(data_files, names, shuffle=False)

        assert np.all(data['chromo'][:5] == b'18')
        npt.assert_equal(data['pos'][:5],
                         [3000023, 3000086, 3000092, 3000103, 3000163])
        npt.assert_equal(data['/outputs/cpg/BS27_4_SER'][:5],
                         [1, 1, 1, -1, 0])

        assert np.all(data['chromo'][-5:] == b'19')
        npt.assert_equal(data['pos'][-5:],
                         [4447803, 4447814, 4447818, 4447821, 4447847])
        npt.assert_equal(data['/outputs/cpg/BS27_4_SER'][-5:],
                         [1, 1, 1, 1, 1])

    def test_nb_sample(self):
        """Test nb_sample together with shuffle. Should always return the same
        data, if nb_sample = size of first data file."""

        names = ['pos', '/outputs/cpg/BS27_4_SER']
        h5_file = h5.File(self.data_files[0], 'r')
        nb_sample = len(h5_file[names[0]])
        h5_file.close()

        data_ref = None
        for i in range(2):
            data = hdf.read(self.data_files, names, shuffle=True,
                            nb_sample=nb_sample)
            if not data_ref:
                data_ref = data
                idx_ref = np.argsort(data_ref['pos'])
                continue
            idx_data = np.argsort(data['pos'])
            for name in names:
                assert len(data_ref[name]) == nb_sample
                assert np.all(data_ref[name][idx_ref] == data[name][idx_data])

    def test_read_reader(self):
        """Test if read and reader yield the same data."""
        nb_sample = 7777
        nb_loop = 10
        names = ['pos', 'chromo', '/outputs/cpg/BS27_4_SER']

        data = hdf.read(self.data_files, names, nb_sample=nb_sample)
        reader = hdf.reader(self.data_files, names, nb_sample=nb_sample,
                            loop=True)
        for loop in range(nb_loop):
            data_loop = dict()
            nb_sample_loop = 0
            while nb_sample_loop < nb_sample:
                data_batch = next(reader)
                for key, value in six.iteritems(data_batch):
                    data_loop.setdefault(key, []).append(value)
                nb_sample_loop += len(value)
            assert nb_sample_loop == nb_sample
            for key, value in six.iteritems(data_loop):
                fun = np.vstack if value[0].ndim > 1 else np.hstack
                data_loop[key] = fun(value)
                assert np.all(data[key] == data_loop[key])

    def test_read_from(self):
        data_files = self.data_files[:2]
        names = ['pos', '/outputs/cpg/BS27_4_SER']
        data = hdf.read(data_files, names)
        for nb_sample in [99, 9999, 99999999999]:
            reader = hdf.reader(data_files, names)
            data_read = hdf.read_from(reader, nb_sample)
            for name in names:
                assert np.all(data[name][:nb_sample] == data_read[name])
