"""Persistent TF recorder with configured per-label Trigger services."""
import json
import yaml
import math
from dataclasses import asdict
from .store import LocationStore,valid_name
from .ros import record_from_tf,pose_message


def main(args=None):
    import rclpy
    from rclpy.node import Node
    from tf2_ros import Buffer,TransformListener,TransformException
    from std_srvs.srv import Trigger
    from geometry_msgs.msg import PoseWithCovarianceStamped

    class Recorder(Node):
        def __init__(self):
            super().__init__('named_locations')
            self.store=LocationStore(self.declare_parameter('file','~/.ros/locations.yaml').value)
            labels=self.declare_parameter('labels',['start','entrance']).value
            self.frame=self.declare_parameter('frame_id','map').value
            self.base=self.declare_parameter('base_frame','base_link').value
            self.age=float(self.declare_parameter('max_tf_age_sec',1.).value)
            self.replace=self.declare_parameter('replace_existing',False).value
            if not math.isfinite(self.age) or self.age<=0:raise ValueError('max_tf_age_sec must be positive')
            if not labels or len(set(labels))!=len(labels):raise ValueError('Unique labels are required')
            self.tf=Buffer();self.listener=TransformListener(self.tf,self)
            self.initial=self.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
            self.create_service(Trigger,'~/list',self.list_locations)
            for label in labels:
                valid_name(label)
                self.create_service(Trigger,'~/record_'+label,lambda req,res,n=label:self.record(res,n))
                self.create_service(Trigger,'~/initialpose_'+label,lambda req,res,n=label:self.initialpose(res,n))

        def list_locations(self,request,response):
            try:response.message=json.dumps({k:asdict(v) for k,v in self.store.all().items()});response.success=True
            except (OSError,ValueError,TypeError,yaml.YAMLError) as e:response.message=str(e);response.success=False
            return response

        def record(self,response,name):
            try:
                location=record_from_tf(self,self.tf,self.frame,self.base,self.age)
                self.store.put(name,location,self.replace);response.success=True;response.message=name
            except (OSError,ValueError,TypeError,yaml.YAMLError,TransformException) as e:response.success=False;response.message=str(e)
            return response

        def initialpose(self,response,name):
            try:
                if self.initial.get_subscription_count()==0:raise ValueError('No initialpose subscriber')
                self.initial.publish(pose_message(self,self.store.get(name),True))
                response.success=True;response.message=name
            except (OSError,ValueError,KeyError,yaml.YAMLError) as e:response.success=False;response.message=str(e)
            return response

    rclpy.init(args=args);node=None
    try:node=Recorder();rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if node:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
