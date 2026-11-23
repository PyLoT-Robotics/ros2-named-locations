"""Optional isolated DDS tests with synthetic publishers; no hardware access."""
import os
import signal
import subprocess
import sys
import time
import json
import pytest
rclpy=pytest.importorskip('rclpy')
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

class Harness:
    def __init__(self,package,domain,parameters):
        self.context=Context();rclpy.init(context=self.context,domain_id=domain)
        self.node=Node(package+'_test',context=self.context)
        self.executor=SingleThreadedExecutor(context=self.context);self.executor.add_node(self.node)
        self.env=dict(os.environ,ROS_DOMAIN_ID=str(domain))
        args=[sys.executable,'-c',f'from {package}.node import main; main()','--ros-args']
        for key,value in parameters.items():args+=['-p',f'{key}:={value}']
        self.process=subprocess.Popen(args,env=self.env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)

    def wait(self,predicate,publish=None,timeout=8.):
        end=time.monotonic()+timeout
        while not predicate() and time.monotonic()<end:
            assert self.process.poll() is None,self.process.stdout.read().decode()
            if publish:publish()
            self.executor.spin_once(timeout_sec=.025)
        assert predicate()

    def call(self,name):
        from std_srvs.srv import Trigger
        client=self.node.create_client(Trigger,name);self.wait(client.service_is_ready)
        future=client.call_async(Trigger.Request());self.wait(future.done)
        return future.result()

    def close(self):
        try:os.killpg(self.process.pid,signal.SIGINT)
        except ProcessLookupError:pass
        try:self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=2)
        output=self.process.stdout.read().decode();self.process.stdout.close()
        self.executor.shutdown();self.node.destroy_node();rclpy.shutdown(context=self.context)
        assert self.process.returncode==0,output

def test_real_tf_record_duplicate_and_query(tmp_path):
    from geometry_msgs.msg import TransformStamped
    from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
    from named_locations.store import LocationStore
    file=tmp_path/'locations.yaml'
    h=Harness('named_locations',82,{'file':str(file)})
    try:
        tf=StaticTransformBroadcaster(h.node);t=TransformStamped()
        t.header.frame_id='map';t.child_frame_id='base_link';t.transform.translation.x=1.5;t.transform.rotation.w=1.;tf.sendTransform(t)
        # Service discovery does not imply TF discovery; retry failed recordings only.
        response=None
        end=time.monotonic()+5
        while time.monotonic()<end:
            response=h.call('/named_locations/record_start')
            if response.success:break
        assert response.success,response.message
        assert LocationStore(file).get('start').x==1.5
        assert not h.call('/named_locations/record_start').success
        assert 'start' in json.loads(h.call('/named_locations/list').message)
        from rclpy.action import ActionServer
        from nav2_msgs.action import NavigateToPose
        goals=[]
        def execute(handle):
            goals.append(handle.request.pose);handle.succeed();return NavigateToPose.Result()
        server=ActionServer(h.node,NavigateToPose,'/navigate_to_pose',execute_callback=execute)
        child=subprocess.Popen([sys.executable,'-m','named_locations.cli','--file',str(file),'go','start','--timeout','5'],
                               env=h.env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:h.wait(lambda:child.poll() is not None,timeout=8.)
        finally:
            if child.poll() is None:child.kill();child.wait()
        output=child.communicate()[0].decode();assert child.returncode==0,output
        assert goals and goals[-1].header.frame_id=='map' and goals[-1].pose.position.x==1.5
        server.destroy()
    finally:h.close()
