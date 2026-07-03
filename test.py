#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from rclpy.qos import QoSProfile, DurabilityPolicy, HistoryPolicy

class GlobalVariablePublisher(Node):
    def __init__(self):
        super().__init__('global_var_pub')

        # Define the QoS profile with TRANSIENT_LOCAL durability
        global_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        # Create the publisher using the special QoS
        self.publisher = self.create_publisher(String, 'global_rov_mode', global_qos)
        
        # Publish an initial value right away
        self.publish_global_state("AUTONOMOUS_DEPTH_HOLD")

    def publish_global_state(self, state_string):
        msg = String()
        msg.data = state_string
        self.publisher.publish(msg)
        self.get_logger().info(f'Published global variable value: "{msg.data}"')

def main(args=None):
    rclpy.init(args=args)
    node = GlobalVariablePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()