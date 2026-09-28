import numpy as np
import pytest
from avgface.models import checked
from avgface.engine import average
from test_engine import fixture_face


def test_model_tampering_is_rejected(tmp_path):
    (tmp_path/'yunet.onnx').write_bytes(b'bad model')
    with pytest.raises(RuntimeError):checked(tmp_path,'yunet.onnx')


def test_mixed_geometry_cannot_average():
    a,b=fixture_face(),fixture_face(); b.backend='insightface'
    with pytest.raises(ValueError,match='关键点'):average([a,b])
