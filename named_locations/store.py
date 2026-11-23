"""Validated named poses with locked, atomic YAML persistence."""
from contextlib import contextmanager
from dataclasses import asdict,dataclass
import fcntl
import math
import os
from pathlib import Path
import re
import tempfile
import yaml


def valid_name(name):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name):
        raise ValueError('Names must start with a letter and use letters, digits, _ or -')
    return name


@dataclass(frozen=True)
class Location:
    x:float
    y:float
    yaw:float
    frame_id:str='map'

    def __post_init__(self):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (self.x,self.y,self.yaw)):
            raise ValueError('Coordinates must be finite numbers in metres/radians')
        if not isinstance(self.frame_id,str) or not self.frame_id.strip():raise ValueError('frame_id is required')


class LocationStore:
    def __init__(self,path):self.path=Path(path).expanduser()

    @contextmanager
    def locked(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.with_name(self.path.name+'.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            try:yield
            finally:fcntl.flock(lock,fcntl.LOCK_UN)

    def _read(self):
        if not self.path.exists():return {}
        data=yaml.safe_load(self.path.read_text())
        if not isinstance(data,dict) or data.get('schema_version')!=1 or not isinstance(data.get('locations'),dict):
            raise ValueError('Invalid location file; refusing to overwrite it')
        return {valid_name(k):Location(**v) for k,v in data['locations'].items()}

    def _write(self,locations):
        data={'schema_version':1,'locations':{k:asdict(v) for k,v in sorted(locations.items())}}
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',dir=self.path.parent,delete=False) as stream:
                temporary=Path(stream.name);yaml.safe_dump(data,stream,sort_keys=False)
                stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        finally:
            if temporary and temporary.exists():temporary.unlink()

    def all(self):
        with self.locked():return self._read()

    def get(self,name):return self.all()[valid_name(name)]

    def put(self,name,location,replace=False):
        valid_name(name)
        if not isinstance(location,Location):raise ValueError('Expected Location')
        with self.locked():
            locations=self._read()
            if name in locations and not replace:raise ValueError('Location already exists; use --replace')
            locations[name]=location;self._write(locations)

    def delete(self,name):
        with self.locked():
            locations=self._read();del locations[valid_name(name)];self._write(locations)


def yaw_from_quaternion(x,y,z,w):
    norm=math.sqrt(x*x+y*y+z*z+w*w)
    if not math.isfinite(norm) or norm<1e-9:raise ValueError('Invalid quaternion')
    x,y,z,w=x/norm,y/norm,z/norm,w/norm
    return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
