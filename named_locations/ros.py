"""ROS operations, imported only by explicit record/go/initialpose commands."""
import math
import time
from .store import Location,yaw_from_quaternion


def record_from_tf(node,buffer,frame,base,max_age):
    from rclpy.time import Time
    t=buffer.lookup_transform(frame,base,Time())
    stamp=t.header.stamp.sec+t.header.stamp.nanosec*1e-9
    now=node.get_clock().now().nanoseconds*1e-9
    if stamp>0 and (now-stamp>max_age or stamp-now>.1):raise ValueError('TF is stale or future-dated')
    q=t.transform.rotation;p=t.transform.translation
    return Location(p.x,p.y,yaw_from_quaternion(q.x,q.y,q.z,q.w),frame)


def pose_message(node,location,initial=False):
    from geometry_msgs.msg import PoseStamped,PoseWithCovarianceStamped
    msg=PoseWithCovarianceStamped() if initial else PoseStamped()
    msg.header.frame_id=location.frame_id;msg.header.stamp=node.get_clock().now().to_msg()
    p=msg.pose.pose if initial else msg.pose
    p.position.x=float(location.x);p.position.y=float(location.y)
    p.orientation.z=math.sin(location.yaw/2);p.orientation.w=math.cos(location.yaw/2)
    if initial:msg.pose.covariance[0]=msg.pose.covariance[7]=.25;msg.pose.covariance[35]=.07
    return msg


def execute(command,store,name,frame='map',base='base_link',timeout=10.,replace=False):
    import rclpy
    from rclpy.node import Node
    from rclpy.action import ActionClient
    from tf2_ros import Buffer,TransformListener,TransformException
    from nav2_msgs.action import NavigateToPose
    from geometry_msgs.msg import PoseWithCovarianceStamped
    rclpy.init();node=Node('named_locations_client');deadline=time.monotonic()+timeout

    def wait(predicate):
        while not predicate() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.02)
        return predicate()

    try:
        if command=='record':
            buffer=Buffer();listener=TransformListener(buffer,node)
            value=None
            while value is None and time.monotonic()<deadline:
                rclpy.spin_once(node,timeout_sec=.02)
                try:value=record_from_tf(node,buffer,frame,base,1.)
                except (TransformException,ValueError):pass
            if value is None:raise TimeoutError('No fresh transform')
            store.put(name,value,replace);return
        location=store.get(name)
        if command=='initialpose':
            pub=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
            if not wait(lambda:pub.get_subscription_count()>0):raise TimeoutError('No initialpose subscriber')
            pub.publish(pose_message(node,location,True))
            # Give reliable DDS a bounded chance to flush the one-shot message.
            rclpy.spin_once(node,timeout_sec=.2);return
        client=ActionClient(node,NavigateToPose,'/navigate_to_pose')
        if not wait(client.server_is_ready):raise TimeoutError('Nav2 server unavailable')
        goal=NavigateToPose.Goal();goal.pose=pose_message(node,location)
        future=client.send_goal_async(goal)
        if not wait(future.done):raise TimeoutError('No goal acknowledgement')
        handle=future.result()
        if not handle.accepted:raise RuntimeError('Navigation goal rejected')
        result=handle.get_result_async()
        if not wait(result.done):
            cancel=handle.cancel_goal_async();cancel_deadline=time.monotonic()+2
            while not cancel.done() and time.monotonic()<cancel_deadline:rclpy.spin_once(node,timeout_sec=.02)
            raise TimeoutError('Navigation timed out; cancellation requested')
        if result.result().status!=4:raise RuntimeError('Navigation did not succeed')
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
