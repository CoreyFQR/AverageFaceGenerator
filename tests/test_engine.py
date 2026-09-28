import numpy as np
import pytest
from avgface.engine import Face, average, similarity, transform_points, statistics, measure, read_image, write_image, Cancelled, WIDTH, HEIGHT


def fixture_face(color=100, group="male"):
    yy,xx=np.mgrid[120:400:40,120:400:40]
    pts=np.column_stack((xx.ravel(),yy.ravel())).astype(np.float32)
    five=np.array([[170,195],[340,195],[256,280],[200,350],[312,350]],np.float32)
    return Face("one","sample.jpg",1,np.full((HEIGHT,WIDTH,3),color,np.uint8),pts,five,group,measure(pts,five))


def test_similarity_preserves_shape_and_recovers_transform():
    source=np.array([[0,0],[1,0],[0,2],[2,3]],np.float32)
    expected=np.array([[0,-3,10],[3,0,20]],np.float32)
    target=transform_points(source,expected)
    np.testing.assert_allclose(similarity(source,target),expected,atol=1e-5)


def test_average_is_equal_weight_and_has_no_triangle_seams():
    out,_=average([fixture_face(40),fixture_face(200)],normalize=False)
    assert np.max(np.abs(out.astype(float)-120)) <= 1
    assert out.shape == (800,600,3)


def test_missing_shoulder_pixels_are_not_mirrored_or_counted():
    a,b=fixture_face(40),fixture_face(200)
    a.valid_mask=np.ones((HEIGHT,WIDTH),np.uint8)
    a.valid_mask[600:]=0
    out,_=average([a,b],normalize=False)
    assert abs(float(out[700,300,0])-200)<=1
    assert abs(float(out[100,300,0])-120)<=1


def test_stats_exclude_review_and_disabled_and_single_std():
    one=fixture_face(); off=fixture_face(); off.enabled=False
    stats=statistics([one,off,fixture_face(group="review")])
    assert stats["male"]["count"]==1
    assert stats["female"]["count"]==0
    assert stats["male"]["metrics"]["eye_px"]["std"]==0


def test_cancel_and_empty():
    with pytest.raises(ValueError):average([])
    with pytest.raises(Cancelled):average([fixture_face()],cancelled=lambda:True)


def test_unicode_png_roundtrip(tmp_path):
    img=np.zeros((31,47,3),np.uint8); img[:,:,2]=231
    path=tmp_path/"测试人脸.png"; write_image(path,img)
    np.testing.assert_array_equal(read_image(path),img)


def test_remap_preserves_identical_spatial_gradient_without_seams():
    a,b=fixture_face(),fixture_face()
    yy,xx=np.mgrid[:HEIGHT,:WIDTH]
    img=np.stack([xx*200/(WIDTH-1),yy*200/(HEIGHT-1),(xx+yy)*200/(WIDTH+HEIGHT-2)],axis=-1).astype(np.uint8)
    a.image=img; b.image=img.copy()
    out,_=average([a,b],normalize=False)
    np.testing.assert_allclose(out,img,atol=1)


@pytest.mark.parametrize('mode', ['LA', 'RGBA'])
def test_png_alpha_is_composited_on_white(tmp_path,mode):
    from PIL import Image
    pixels=np.array([[[40,0],[40,128],[40,255]]],dtype=np.uint8)
    source=Image.fromarray(pixels).convert(mode)
    path=tmp_path/'alpha.png'; source.save(path)
    # Check transparent, translucent and opaque pixels, including LA PNGs
    # whose alpha channel does not appear in Pillow's transparency metadata.
    expected=Image.alpha_composite(Image.new('RGBA',source.size,'white'),source.convert('RGBA')).convert('RGB')
    np.testing.assert_array_equal(read_image(path),np.asarray(expected)[:,:,::-1])
