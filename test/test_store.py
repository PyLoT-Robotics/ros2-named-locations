import math
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import pytest
from named_locations.store import Location,LocationStore,yaw_from_quaternion
from named_locations.cli import main


def add_file(args):
    path,name=args;LocationStore(path).put(name,Location(1.,2.,0.))


def test_roundtrip_and_explicit_replace(tmp_path):
    s=LocationStore(tmp_path/'world.yaml');p=Location(1.,2.,.5,'odom');s.put('door',p)
    assert s.get('door')==p
    with pytest.raises(ValueError):s.put('door',p)
    s.put('door',Location(3.,2.,.1),True);assert s.get('door').x==3
    s.delete('door');assert s.all()=={}


def test_corrupt_file_is_not_overwritten(tmp_path):
    path=tmp_path/'world.yaml';path.write_text('not-a-location-file')
    with pytest.raises(ValueError):LocationStore(path).put('door',Location(0.,0.,0.))
    assert path.read_text()=='not-a-location-file'


@pytest.mark.parametrize('name',['../x','', '_metadata','a/b'])
def test_invalid_names(tmp_path,name):
    with pytest.raises(ValueError):LocationStore(tmp_path/'x').put(name,Location(0.,0.,0.))


@pytest.mark.parametrize('value',[float('nan'),float('inf'),True])
def test_invalid_pose(value):
    with pytest.raises(ValueError):Location(value,0.,0.)


def test_concurrent_writers_preserve_both_locations(tmp_path):
    path=str(tmp_path/'world.yaml')
    with ProcessPoolExecutor(max_workers=2,mp_context=get_context("spawn")) as executor:list(executor.map(add_file,[(path,'a'),(path,'b')]))
    assert set(LocationStore(path).all())=={'a','b'}


def test_yaw_normalization():
    assert yaw_from_quaternion(0.,0.,2.,2.)==pytest.approx(math.pi/2)
    with pytest.raises(ValueError):yaw_from_quaternion(0,0,0,0)


def test_cli(tmp_path,capsys):
    args=['--file',str(tmp_path/'world.yaml')]
    assert main(args+['add','door','--x','1','--y','2','--yaw','0'])==0
    assert main(args+['show','door'])==0
    assert 'frame_id' in capsys.readouterr().out
