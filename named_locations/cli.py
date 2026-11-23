import argparse
from dataclasses import asdict
import json
import math
import tempfile
from pathlib import Path
import yaml
from .store import Location,LocationStore


def main(argv=None):
    p=argparse.ArgumentParser(description='Named locations: metres, radians, explicit frames')
    p.add_argument('--file',default='~/.ros/locations.yaml')
    sub=p.add_subparsers(dest='command',required=True);sub.add_parser('demo');sub.add_parser('list')
    for command in ['show','delete','record','go','initialpose','add']:
        sp=sub.add_parser(command);sp.add_argument('name')
        if command in ['add','record']:sp.add_argument('--replace',action='store_true')
        if command=='add':
            for key in ['x','y','yaw']:sp.add_argument('--'+key,type=float,required=True)
            sp.add_argument('--frame',default='map')
        if command in ['record','go','initialpose']:sp.add_argument('--timeout',type=float,default=10.)
        if command=='record':sp.add_argument('--frame',default='map');sp.add_argument('--base',default='base_link')
    a=p.parse_args(argv)
    try:
        if a.command=='demo':
            with tempfile.TemporaryDirectory() as d:
                store=LocationStore(Path(d)/'locations.yaml');store.put('entrance',Location(1.,2.,.5))
                assert store.get('entrance').x==1.;print(asdict(store.get('entrance')))
            return 0
        store=LocationStore(a.file)
        if a.command=='add':store.put(a.name,Location(a.x,a.y,a.yaw,a.frame),a.replace)
        elif a.command=='delete':store.delete(a.name)
        elif a.command=='list':print(json.dumps({k:asdict(v) for k,v in store.all().items()},indent=2))
        elif a.command=='show':print(json.dumps(asdict(store.get(a.name)),indent=2))
        else:
            if not math.isfinite(a.timeout) or a.timeout<=0:raise ValueError('Timeout must be positive')
            from .ros import execute
            execute(a.command,store,a.name,getattr(a,'frame','map'),getattr(a,'base','base_link'),a.timeout,getattr(a,'replace',False))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,ImportError,yaml.YAMLError) as e:p.exit(2,str(e)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
