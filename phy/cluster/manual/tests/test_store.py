# -*- coding: utf-8 -*-

"""Test cluster store."""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import numpy as np
from numpy.testing import assert_array_equal as ae
from numpy.testing import assert_allclose as ac

from ....utils._misc import Bunch
from ....utils.tempdir import TemporaryDirectory
from ....utils.logging import set_level
from ..store import MemoryStore, DiskStore, ClusterStore, StoreItem
from .._utils import _spikes_per_cluster, UpdateInfo


#------------------------------------------------------------------------------
# Test data stores
#------------------------------------------------------------------------------

def setup():
    set_level('debug')


def test_memory_store():
    ms = MemoryStore()
    assert ms.load(2) == {}

    assert ms.load(3).get('key', None) is None
    assert ms.load(3) == {}
    assert ms.load(3, ['key']) == {'key': None}
    assert ms.load(3) == {}
    assert ms.cluster_ids == []

    ms.store(3, key='a')
    assert ms.load(3) == {'key': 'a'}
    assert ms.load(3, ['key']) == {'key': 'a'}
    assert ms.load(3, 'key') == 'a'
    assert ms.cluster_ids == [3]

    ms.store(3, key_bis='b')
    assert ms.load(3) == {'key': 'a', 'key_bis': 'b'}
    assert ms.load(3, ['key']) == {'key': 'a'}
    assert ms.load(3, ['key_bis']) == {'key_bis': 'b'}
    assert ms.load(3, ['key', 'key_bis']) == {'key': 'a', 'key_bis': 'b'}
    assert ms.load(3, 'key_bis') == 'b'
    assert ms.cluster_ids == [3]

    ms.erase([2, 3])
    assert ms.load(3) == {}
    assert ms.load(3, ['key']) == {'key': None}
    assert ms.cluster_ids == []


def test_disk_store():

    dtype = np.float32
    sha = (2, 4)
    shb = (3, 5)
    a = np.random.rand(*sha).astype(dtype)
    b = np.random.rand(*shb).astype(dtype)

    def _assert_equal(d_0, d_1):
        """Test the equality of two dictionaries containing NumPy arrays."""
        assert sorted(d_0.keys()) == sorted(d_1.keys())
        for key in d_0.keys():
            ac(d_0[key], d_1[key])

    with TemporaryDirectory() as tempdir:
        ds = DiskStore(tempdir)

        ds.register_file_extensions(['key', 'key_bis'])
        assert ds.cluster_ids == []

        ds.store(3, key=a)
        _assert_equal(ds.load(3,
                              ['key'],
                              dtype=dtype,
                              shape=sha,
                              ),
                      {'key': a})
        loaded = ds.load(3, 'key', dtype=dtype, shape=sha)
        ac(loaded, a)

        # Loading a non-existing key returns None.
        assert ds.load(3, 'key_bis') is None
        assert ds.cluster_ids == [3]

        ds.store(3, key_bis=b)
        _assert_equal(ds.load(3, ['key'], dtype=dtype, shape=sha), {'key': a})
        _assert_equal(ds.load(3, ['key_bis'],
                              dtype=dtype,
                              shape=shb,
                              ),
                      {'key_bis': b})
        _assert_equal(ds.load(3,
                              ['key', 'key_bis'],
                              dtype=dtype,
                              ),
                      {'key': a.ravel(), 'key_bis': b.ravel()})
        ac(ds.load(3, 'key_bis', dtype=dtype, shape=shb), b)
        assert ds.cluster_ids == [3]

        ds.erase([2, 3])
        assert ds.load(3, ['key']) == {'key': None}
        assert ds.cluster_ids == []


def test_cluster_store_1():
    with TemporaryDirectory() as tempdir:

        # We define some data and a model.
        n_spikes = 100
        n_clusters = 10

        spike_ids = np.arange(n_spikes)
        spike_clusters = np.random.randint(size=n_spikes,
                                           low=0, high=n_clusters)
        spikes_per_cluster = _spikes_per_cluster(spike_ids, spike_clusters)

        model = {'spike_clusters': spike_clusters}

        # We initialize the ClusterStore.
        cs = ClusterStore(model=model, path=tempdir)

        # We create a n_spikes item to be stored in memory,
        # and we define how to generate it for a given cluster.
        class MyItem(StoreItem):
            name = 'my item'
            fields = [('n_spikes', 'memory')]

            def store_cluster(self, cluster, spikes, mode=None):
                self.memory_store.store(cluster, n_spikes=len(spikes))

            def on_cluster(self, up):
                if up.description == 'merge':
                    n = sum(len(up.old_spikes_per_cluster[cl])
                            for cl in up.deleted)
                    self.memory_store.store(up.added[0], n_spikes=n)
                else:
                    super(MyItem, self).on_cluster(up)

        cs.register_item(MyItem)

        # Now we generate the store.
        cs.generate(spikes_per_cluster)

        # We check that the n_spikes field has successfully been created.
        for cluster in sorted(spikes_per_cluster):
            assert cs.n_spikes(cluster) == len(spikes_per_cluster[cluster])

        # Merge.
        spc = spikes_per_cluster.copy()
        spikes = np.sort(np.concatenate([spc[0], spc[1]]))
        spc[20] = spikes
        del spc[0]
        del spc[1]
        up = UpdateInfo(description='merge',
                        added=[20],
                        deleted=[0, 1],
                        spikes=spikes,
                        new_spikes_per_cluster=spc,
                        old_spikes_per_cluster=spikes_per_cluster,)

        cs.on_cluster(up)

        # Check the list of clusters in the store.
        ae(cs.memory_store.cluster_ids, list(range(0, n_clusters)) + [20])
        ae(cs.disk_store.cluster_ids, [])
        assert cs.n_spikes(20) == len(spikes)

        # Recreate the cluster store.
        cs = ClusterStore(model=model, path=tempdir)
        cs.register_item(MyItem)
        cs.generate(spikes_per_cluster)
        ae(cs.memory_store.cluster_ids, list(range(n_clusters)))
        ae(cs.disk_store.cluster_ids, [])


def test_cluster_store_multi():
    """This tests the cluster store when a store item has several fields."""

    cs = ClusterStore()

    class MyItem(StoreItem):
        name = 'my item'
        fields = [('d', 'memory'),
                  ('m', 'memory')]

        def store_cluster(self, cluster, spikes, mode=None):
            self.memory_store.store(cluster, d=len(spikes), m=len(spikes)**2)

    cs.register_item(MyItem)

    cs.generate({0: [0, 2], 1: [1, 3, 4]})

    assert cs.memory_store.load(0, ['d', 'm']) == {'d': 2, 'm': 4}
    assert cs.d(0) == 2
    assert cs.m(0) == 4

    assert cs.memory_store.load(1, ['d', 'm']) == {'d': 3, 'm': 9}
    assert cs.d(1) == 3
    assert cs.m(1) == 9


def test_cluster_store_load():
    with TemporaryDirectory() as tempdir:

        # We define some data and a model.
        n_spikes = 100
        n_clusters = 10

        spike_ids = np.arange(n_spikes)
        spike_clusters = np.random.randint(size=n_spikes,
                                           low=0, high=n_clusters)
        spikes_per_cluster = _spikes_per_cluster(spike_ids, spike_clusters)

        model = {'spike_clusters': spike_clusters}

        # We initialize the ClusterStore.
        cs = ClusterStore(model=model, path=tempdir)

        # We create a n_spikes item to be stored in memory,
        # and we define how to generate it for a given cluster.
        class MyItem(StoreItem):
            name = 'my item'
            fields = [('spikes_square', 'disk', np.int32)]

            def store_cluster(self, cluster, spikes, mode=None):
                data = (spikes ** 2).astype(np.int32)
                self.disk_store.store(cluster, spikes_square=data)

        cs.register_item(MyItem)

        # Now we generate the store.
        cs.generate(spikes_per_cluster)

        # All spikes in cluster 1.
        cluster = 1
        spikes = spikes_per_cluster[cluster]
        ae(cs.load('spikes_square', [cluster], spikes), spikes ** 2)

        # Some spikes in cluster 1.
        spikes = spikes_per_cluster[cluster][1::2]
        ae(cs.load('spikes_square', [cluster], spikes), spikes ** 2)

        # All spikes in several clusters.
        clusters = [2, 3, 5]
        spikes = np.concatenate([spikes_per_cluster[cl]
                                 for cl in clusters])
        # Reverse the order of spikes.
        spikes = np.r_[spikes, spikes[::-1]]
        ae(cs.load('spikes_square', clusters, spikes), spikes ** 2)

        # Some spikes in several clusters.
        spikes = np.concatenate([spikes_per_cluster[cl][::3]
                                 for cl in clusters])
        ae(cs.load('spikes_square', clusters, spikes), spikes ** 2)


def test_cluster_store_management():
    with TemporaryDirectory() as tempdir:

        # We define some data and a model.
        n_spikes = 100
        n_clusters = 10

        spike_ids = np.arange(n_spikes)
        spike_clusters = np.random.randint(size=n_spikes,
                                           low=0, high=n_clusters)
        spikes_per_cluster = _spikes_per_cluster(spike_ids, spike_clusters)

        model = Bunch({'spike_clusters': spike_clusters,
                       'cluster_ids': np.arange(n_clusters),
                       })

        # We initialize the ClusterStore.
        cs = ClusterStore(model=model, path=tempdir)

        # We create a n_spikes item to be stored in memory,
        # and we define how to generate it for a given cluster.
        class MyItem(StoreItem):
            name = 'my item'
            fields = [('spikes_square', 'disk', np.int32)]

            def store_cluster(self, cluster, spikes, mode=None):
                if not self.is_consistent(cluster, spikes):
                    data = (spikes ** 2).astype(np.int32)
                    self.disk_store.store(cluster, spikes_square=data)

            def is_consistent(self, cluster, spikes):
                spikes = self.spikes_per_cluster[cluster]
                data = self.disk_store.load(cluster,
                                            'spikes_square',
                                            dtype=np.int32,
                                            )
                if data is None:
                    return False
                assert len(data) == len(spikes)
                expected = (spikes ** 2).astype(np.int32)
                return np.all(data == expected)

        cs.register_item(MyItem)

        # Now we generate the store.
        cs.generate(spikes_per_cluster)

        # Check the status.
        assert 'True' in cs.status

        # We re-initialize the ClusterStore.
        cs = ClusterStore(model=model, path=tempdir)
        cs.register_item(MyItem)
        cs.generate(spikes_per_cluster)
        cs.display_status()

        cs.files
