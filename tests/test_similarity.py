import numpy as np
import pytest
from avgface.similarity import Similarity
from avgface.common import Cancelled
from test_engine import fixture_face


def sample(id, group='male', enabled=True):
    face=fixture_face(group=group); face.id=id; face.enabled=enabled
    return face


def test_ranking_compares_each_group_to_its_own_average_and_excludes_disabled():
    model=Similarity()
    faces=[sample('a'),sample('b'),sample('c','female'),sample('d','female'),sample('off',enabled=False),sample('review','review')]
    model.cache={'a':np.array([1.,0.]),'b':np.array([0.,1.]),'c':np.array([0.,1.]),'d':np.array([-1.,0.])}
    model.feature=lambda image,five:np.array(image)
    result=model.rank(faces,{'male':([1.,0.],None),'female':([0.,1.],None)})
    assert [x[0].id for x in result['male']]==['a','b']
    assert [x[0].id for x in result['female']]==['c','d']
    assert result['male'][0][1]==1
    result=model.rank([faces[0]],{'male':([1.,0.],None)})
    assert result['male'][0][0] is result['male'][1][0]


def test_compare_top_ten_descending_review_included_and_cancellation():
    model=Similarity(); faces=[sample(str(i),'review' if i==11 else 'male') for i in range(12)]
    model.cache={f.id:np.array([int(f.id)/12,0.]) for f in faces}
    model.feature=lambda image,five:np.array([1.,0.])
    result=model.compare(faces[0],faces)
    assert len(result)==10 and result[0][0].id=='11'
    assert [s for _,s in result]==sorted([s for _,s in result],reverse=True)
    faces[-1].enabled=False
    assert model.compare(faces[0],faces)[0][0].id=='10'
    with pytest.raises(Cancelled):model.compare(faces[0],faces,lambda:True)
    assert model.compare(faces[0],[])==[]
