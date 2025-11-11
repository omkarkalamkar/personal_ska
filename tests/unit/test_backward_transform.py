import json
import time
from copy import deepcopy

import pytest
from astropy.time import Time

import ska_tmc_dishleafnode.manager.component_manager as dln_cm_mod
from ska_tmc_dishleafnode import AzElConverter
from ska_tmc_dishleafnode.manager.component_manager import (
    DishLNComponentManager,
)
from tests.settings import ARRAY_LAYOUT, SKA_EPOCH, logger


@pytest.mark.parametrize(
    "timestamp, az, el, expected_ra, expected_dec",
    [
        (
            "2019-02-19 06:01:00",
            "322.8709276",
            "41.3703589",
            "15:31:50.9",
            "10:15:51.4",
        ),
        (
            "2022-03-19 18:21:50",
            "46.110779",
            "30.6631224",
            "10:14:56.82",
            "14:44:15.13",
        ),
    ],
)
def test_azel_to_radec(
    timestamp,
    az,
    el,
    expected_ra,
    expected_dec,
    cm_without_er_lp,
):
    """Test the backward transform method from AzElConverter."""
    # updated the test case as it doesn't require to preset the
    # observer separately now array layout is default set in component manager
    cm = cm_without_er_lp
    converter = AzElConverter(component_manager=cm)
    retry = 0
    while retry <= 3:
        try:
            converter.create_antenna_obj()
            break
        except Exception as e:
            logger.exception(
                "Exception occurred while creating antenna object: %s", e
            )
            if retry == 2:
                pytest.fail(f"{e}")
            retry += 1
        time.sleep(0.1)
    ra, dec = converter.azel_to_radec(az, el, timestamp)
    assert expected_ra == ra
    assert expected_dec == dec


def test_actual_pointing(cm_without_er_lp):
    """Test to check actual pointing is getting updated"""
    cm = cm_without_er_lp
    cm.array_layout = ARRAY_LAYOUT
    timestamp_str = "2019-02-19 06:01:00"
    epoch_time = Time(SKA_EPOCH, format="isot", scale="utc")
    timestamp_time = Time(timestamp_str, format="iso", scale="utc")
    ska_epoch_tai_timestamp = (timestamp_time - epoch_time).sec
    converter = AzElConverter(component_manager=cm)
    converter.create_antenna_obj()
    cm.perform_reverse_transform(
        [ska_epoch_tai_timestamp, 322.8709276, 41.3703589]
    )

    assert list(cm.actual_pointing) == [
        "2019-02-19 06:01:00",
        "15:31:50.9",
        "10:15:51.4",
    ]


def test_actual_pointing_matches_expected_strings_after_site_shift(
    cm_without_er_lp,
):
    cm = cm_without_er_lp
    cm.array_layout = ARRAY_LAYOUT

    timestamp_str = "2019-02-19 06:01:00"
    epoch_time = Time(SKA_EPOCH, format="isot", scale="utc")
    timestamp_time = Time(timestamp_str, format="iso", scale="utc")
    ska_epoch_tai_timestamp = (timestamp_time - epoch_time).sec

    AzElConverter(component_manager=cm).create_antenna_obj()

    # BASE at original site
    cm.perform_reverse_transform(
        [ska_epoch_tai_timestamp, 322.8709276, 41.3703589]
    )
    t0, ra0, dec0 = cm.actual_pointing

    EXPECTED_RA_BASE = "15:31:50.9"
    EXPECTED_DEC_BASE = "10:15:51.4"

    assert t0 == timestamp_str
    assert ra0 == EXPECTED_RA_BASE
    assert dec0 == EXPECTED_DEC_BASE

    # SHIFT: move site by +1 deg lat/lon
    changed = deepcopy(ARRAY_LAYOUT)
    changed["location"]["geodetic"]["lat"] = (
        ARRAY_LAYOUT["location"]["geodetic"]["lat"] + 1.0
    )
    changed["location"]["geodetic"]["lon"] = (
        ARRAY_LAYOUT["location"]["geodetic"]["lon"] + 1.0
    )
    cm.array_layout = changed

    AzElConverter(component_manager=cm).create_antenna_obj()

    cm.perform_reverse_transform(
        [ska_epoch_tai_timestamp, 322.8709276, 41.3703589]
    )
    t1, ra1, dec1 = cm.actual_pointing

    EXPECTED_RA_SHIFT = "15:35:30.5"
    EXPECTED_DEC_SHIFT = "11:09:01.37"

    assert t1 == timestamp_str
    assert ra1 == EXPECTED_RA_SHIFT
    assert dec1 == EXPECTED_DEC_SHIFT


class TestTMData:
    """TMData patch that returns a preconfigured layout via get_dict()."""

    layout_to_return = None

    def __init__(self, source_uris):
        # keep for debug / possible asserts later
        self.source_uris = source_uris

    def __getitem__(self, key):
        # In real TMData, __getitem__ returns an object with get_dict()
        self.key = key
        return self

    def get_dict(self):
        return type(self).layout_to_return


def test_load_array_layout_sets_matching_receptor(
    monkeypatch, cm_without_er_lp
):
    """
    When TelModel layout contains a receptor whose station_label matches
    dish_id (case-insensitive), that receptor is stored in array_layout.
    """
    TestTMData.layout_to_return = {
        "receptors": [
            {"station_label": "SKA000", "foo": "ignore"},
            {
                "station_label": "SKA001",
                "location": {"geodetic": {"lat": 1.0, "lon": 2.0}},
            },
        ]
    }
    monkeypatch.setattr(dln_cm_mod, "TMData", TestTMData)

    cm: DishLNComponentManager = cm_without_er_lp

    # Make sure we have non-empty defaults for this test branch
    cm.default_array_layout_source_uris = "tm://dummy"
    cm.default_array_layout_path = "dummy/layout/path"

    # Clear any previous update flags for a clean assertion
    if hasattr(cm, "layout_updated"):
        cm.layout_updated.clear()

    cm.load_array_layout_for_dish()

    expected = TestTMData.layout_to_return["receptors"][1]
    assert cm.array_layout == expected
    if hasattr(cm, "layout_updated"):
        assert cm.layout_updated.is_set()


def test_load_array_layout_accepts_json_string_layout(
    monkeypatch, cm_without_er_lp
):
    """
    If TelModel returns a JSON string for the layout, it is decoded and
    processed as expected.
    """
    layout_dict = {
        "receptors": [
            {"station_label": "ska001", "meta": "from-json-string"},
        ]
    }
    TestTMData.layout_to_return = json.dumps(layout_dict)
    monkeypatch.setattr(dln_cm_mod, "TMData", TestTMData)

    cm: DishLNComponentManager = cm_without_er_lp
    cm.default_array_layout_source_uris = "tm://dummy"
    cm.default_array_layout_path = "dummy/layout/path"

    cm.load_array_layout_for_dish()

    assert cm.array_layout == layout_dict["receptors"][0]


def test_load_array_layout_no_defaults_does_not_touch_array_layout(
    monkeypatch, cm_without_er_lp
):
    """
    If default_array_layout_source_uris or default_array_layout_path are
    missing/falsey, the method logs a warning and returns without calling
    TMData or modifying array_layout.
    """

    class ExplodingTMData:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("TMData should not be instantiated")

    monkeypatch.setattr(dln_cm_mod, "TMData", ExplodingTMData)

    cm: DishLNComponentManager = cm_without_er_lp

    # Ensure we have some existing layout to detect unwanted changes
    original_layout = cm.array_layout or ARRAY_LAYOUT
    cm.array_layout = original_layout

    # Force the early-return branch
    cm.default_array_layout_source_uris = ""
    cm.default_array_layout_path = ""

    if hasattr(cm, "layout_updated"):
        cm.layout_updated.clear()
        was_set_before = cm.layout_updated.is_set()
    else:
        was_set_before = False

    cm.load_array_layout_for_dish()

    assert cm.array_layout == original_layout
    if hasattr(cm, "layout_updated"):
        assert cm.layout_updated.is_set() == was_set_before


def test_load_array_layout_no_matching_receptor_keeps_existing_layout(
    monkeypatch, cm_without_er_lp
):
    """
    If no receptor matches dish_id, the method logs a warning and returns
    without modifying array_layout.
    """
    TestTMData.layout_to_return = {
        "receptors": [
            {"station_label": "SKA999"},
            {"station_label": "SKA998"},
        ]
    }
    monkeypatch.setattr(dln_cm_mod, "TMData", TestTMData)

    cm: DishLNComponentManager = cm_without_er_lp
    cm.default_array_layout_source_uris = "tm://dummy"
    cm.default_array_layout_path = "dummy/layout/path"

    # Set a known starting layout
    original_layout = {"existing": "layout-before-call"}
    cm.array_layout = original_layout

    if hasattr(cm, "layout_updated"):
        cm.layout_updated.clear()

    cm.load_array_layout_for_dish()

    # Should not change because no station_label matches dish_id
    assert cm.array_layout == original_layout
    if hasattr(cm, "layout_updated"):
        # No call to setter → no signal
        assert not cm.layout_updated.is_set()


def test_load_array_layout_raises_valueerror_on_tmdata_failure(
    monkeypatch, cm_without_er_lp
):
    """
    Any unexpected exception during loading/parsing is logged and re-raised
    as a ValueError, with the original exception as __cause__.
    """

    class FailingTMData:
        def __init__(self, *_args, **_kwargs):
            raise RuntimeError("TelModel access failed")

    monkeypatch.setattr(dln_cm_mod, "TMData", FailingTMData)

    cm: DishLNComponentManager = cm_without_er_lp
    cm.default_array_layout_source_uris = "tm://dummy"
    cm.default_array_layout_path = "dummy/layout/path"

    with pytest.raises(ValueError) as excinfo:
        cm.load_array_layout_for_dish()

    err = excinfo.value
    assert "Failed to load array layout for dish_id" in str(err)
    assert isinstance(err.__cause__, RuntimeError)
